"""
Raw protobuf API test: bypasses pysc2's RemoteController entirely.

Uses pysc2 ONLY to locate and launch the SC2 binary (version-matched).
All API communication goes through a raw websocket with hand-built
protobuf Request/Response messages.

Goal: determine if observer mode economy zeros are caused by pysc2's
wrapper layer or by the SC2 binary's API itself.
"""

import time
import struct
from pathlib import Path

import websocket
from pysc2 import run_configs
from pysc2.lib import replay as replay_lib
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import common_pb2


# ---------- CONFIG ----------
REPLAY_PATH = "replays/match_4184936.SC2Replay"
STEPS_TO_SAMPLE = [50, 200]
# -----------------------------


def send_request(ws, **kwargs):
    """
    Build a sc2api Request protobuf, serialize it, send it over the
    websocket, read the raw Response, and return the parsed Response.

    Args:
        ws: websocket connection to SC2
        **kwargs: field names on sc_pb.Request (e.g. start_replay=..., step=...)

    Returns:
        Parsed sc_pb.Response protobuf. Raises on websocket error.
    """
    req = sc_pb.Request(**kwargs)
    ws.send(req.SerializeToString(), opcode=websocket.ABNF.OPCODE_BINARY)

    # Read raw bytes back
    raw = ws.recv()
    resp = sc_pb.Response()
    resp.ParseFromString(raw)
    return resp


def dump_economy(label, obs):
    """
    Print economy fields from an Observation protobuf.

    Args:
        label: descriptive label for this dump
        obs: the Observation sub-message from ResponseObservation
    """
    pc = obs.player_common
    print(f"\n  [{label}] player_common:")
    print(f"    player_id        : {pc.player_id}")
    print(f"    minerals         : {pc.minerals}")
    print(f"    vespene          : {pc.vespene}")
    print(f"    food_used        : {pc.food_used}")
    print(f"    food_cap         : {pc.food_cap}")
    print(f"    food_army        : {pc.food_army}")
    print(f"    food_workers     : {pc.food_workers}")
    print(f"    idle_worker_count: {pc.idle_worker_count}")
    print(f"    army_count       : {pc.army_count}")

    sc = obs.score
    print(f"  [{label}] score:")
    print(f"    score_type : {sc.score_type}")
    print(f"    score      : {sc.score}")
    if sc.HasField("score_details"):
        scd = sc.score_details
        print(f"    collected_minerals       : {scd.collected_minerals}")
        print(f"    collected_vespene        : {scd.collected_vespene}")
        print(f"    collection_rate_minerals : {scd.collection_rate_minerals}")
        print(f"    collection_rate_vespene  : {scd.collection_rate_vespene}")
        print(f"    spent_minerals           : {scd.spent_minerals}")
        print(f"    spent_vespene            : {scd.spent_vespene}")
    else:
        print(f"    score_details: NOT PRESENT")


def main():
    # --- absl flags init (required by pysc2 internals even for path lookup) ---
    from absl import flags
    flags.FLAGS(["tmptest_raw.py"])

    # --- Step 1: Load replay and detect version (need pysc2 for this) ---
    replay_path_abs = str(Path(REPLAY_PATH).resolve())
    print(f"Loading replay: {replay_path_abs}")

    initial_config = run_configs.get()
    replay_data = initial_config.replay_data(replay_path_abs)

    replay_version = replay_lib.get_replay_version(replay_data)
    print(f"Replay version: {replay_version.game_version} "
          f"(build {replay_version.build_version})")
    run_config = run_configs.get(version=replay_version)

    # --- Step 2: Launch SC2 binary via pysc2 (just the process, not the controller) ---
    # run_config.start() returns a context manager that launches SC2 and gives us
    # a controller. We'll grab the connection info and make our own websocket.
    print("Launching SC2 binary...")
    sc2_proc = run_config.start(want_rgb=False)
    controller = sc2_proc.__enter__()

    # Get the host/port from pysc2's controller so we can connect ourselves
    # The controller wraps a StarcraftProtocol which wraps a websocket
    # We need to find the port SC2 is listening on
    host = controller._client._sock.sock.getpeername()
    port = host[1]
    addr = host[0]
    print(f"SC2 listening at {addr}:{port}")

    # Close pysc2's websocket so we own the connection exclusively
    # Actually, let's just use a SECOND websocket connection to the same port
    # No — SC2 only accepts one client. Let's close pysc2's and open our own.
    controller._client._sock.close()
    time.sleep(0.5)  # Let SC2 process the disconnect

    # Open our own raw websocket
    ws_url = f"ws://{addr}:{port}/sc2api"
    print(f"Connecting raw websocket to {ws_url}")
    ws = websocket.create_connection(ws_url, timeout=120)
    print("Raw websocket connected!")

    try:
        # --- Step 3: Ping to verify connection ---
        resp = send_request(ws, ping=sc_pb.RequestPing())
        print(f"Ping OK — game_version: {resp.ping.game_version}, "
              f"base_build: {resp.ping.base_build}")

        # --- Step 4: Interface options ---
        interface = sc_pb.InterfaceOptions(
            raw=True,
            score=True,
            show_cloaked=True,
            show_burrowed_shadows=True,
            show_placeholders=True,
        )

        # --- Step 5: Get replay info ---
        resp = send_request(ws, replay_info=sc_pb.RequestReplayInfo(
            replay_data=replay_data
        ))
        info = resp.replay_info
        print(f"Map: {info.map_name}")
        print(f"Duration: {info.game_duration_loops} loops")
        for i, pi in enumerate(info.player_info):
            race = common_pb2.Race.Name(pi.player_info.race_actual)
            print(f"  Player {i+1}: {race}, MMR: {pi.player_mmr}")

        # =================================================================
        # TEST A: OBSERVER MODE (observed_player_id=0) via raw protobuf
        # =================================================================
        print(f"\n{'='*60}")
        print("TEST A: OBSERVER MODE (raw protobuf, observed_player_id=0)")
        print(f"{'='*60}")

        req = sc_pb.RequestStartReplay(
            replay_data=replay_data,
            options=interface,
            observed_player_id=0,
            disable_fog=True,
            realtime=False,
        )

        # Verify the wire encoding actually has observed_player_id
        wire = req.SerializeToString()
        print(f"  RequestStartReplay wire bytes: {len(wire)} bytes")
        marker = b'\x10\x00'
        print(f"  Contains field-2 varint-0 on wire: {marker in wire}")

        resp = send_request(ws, start_replay=req)
        print(f"  start_replay response status: {sc_pb.Status.Name(resp.status)}")
        sr = resp.start_replay
        if sr.error:
            print(f"  start_replay error code: {sr.error}")
            print(f"  error_details: {sr.error_details}")
        else:
            print(f"  start_replay: OK (no error)")

        # Step and observe
        for target_step in STEPS_TO_SAMPLE:
            # Step to target
            send_request(ws, step=sc_pb.RequestStep(count=target_step))

            print(f"\n--- STEP ~{target_step} (Observer, no perspective switch) ---")

            # Observe WITHOUT any perspective switch
            resp = send_request(ws, observation=sc_pb.RequestObservation())
            obs = resp.observation.observation
            dump_economy("Observer raw (no switch)", obs)

            owners = set(u.owner for u in obs.raw_data.units)
            print(f"  [raw units] unique owners: {owners}")

            # Now try perspective switch via raw RequestObserverAction
            print(f"\n--- Switching to Player 1 perspective (raw protobuf) ---")
            switch_req = sc_pb.RequestObserverAction(
                actions=[sc_pb.ObserverAction(
                    player_perspective=sc_pb.ActionObserverPlayerPerspective(
                        player_id=1
                    )
                )]
            )
            switch_resp = send_request(ws, obs_action=switch_req)
            print(f"  observer_action response status: {sc_pb.Status.Name(switch_resp.status)}")
            # Show which oneof response field was set
            resp_type = switch_resp.WhichOneof("response")
            print(f"  response type: {resp_type}")

            # Observe after switch (no step in between)
            resp = send_request(ws, observation=sc_pb.RequestObservation())
            obs_p1 = resp.observation.observation
            dump_economy("After raw switch to P1 (no step)", obs_p1)

            # Step 1, then observe again
            send_request(ws, step=sc_pb.RequestStep(count=1))
            resp = send_request(ws, observation=sc_pb.RequestObservation())
            obs_p1s = resp.observation.observation
            dump_economy("After raw switch to P1 (with step)", obs_p1s)

            # Switch to Player 2
            print(f"\n--- Switching to Player 2 perspective (raw protobuf) ---")
            switch_req2 = sc_pb.RequestObserverAction(
                actions=[sc_pb.ObserverAction(
                    player_perspective=sc_pb.ActionObserverPlayerPerspective(
                        player_id=2
                    )
                )]
            )
            switch_resp2 = send_request(ws, obs_action=switch_req2)
            print(f"  observer_action response status: {sc_pb.Status.Name(switch_resp2.status)}")

            send_request(ws, step=sc_pb.RequestStep(count=1))
            resp = send_request(ws, observation=sc_pb.RequestObservation())
            obs_p2s = resp.observation.observation
            dump_economy("After raw switch to P2 (with step)", obs_p2s)

            # Reset back — restart replay for clean state for next sample
            # (only if more samples to go)

        # =================================================================
        # TEST B: PLAYER PERSPECTIVE MODE via raw protobuf
        # =================================================================
        print(f"\n{'='*60}")
        print("TEST B: PLAYER 1 PERSPECTIVE (raw protobuf, observed_player_id=1)")
        print(f"{'='*60}")

        resp = send_request(ws, start_replay=sc_pb.RequestStartReplay(
            replay_data=replay_data,
            options=interface,
            observed_player_id=1,
            disable_fog=True,
            realtime=False,
        ))
        print(f"  start_replay status: {sc_pb.Status.Name(resp.status)}")

        for target_step in STEPS_TO_SAMPLE:
            send_request(ws, step=sc_pb.RequestStep(count=target_step))
            resp = send_request(ws, observation=sc_pb.RequestObservation())
            obs = resp.observation.observation
            print(f"\n--- STEP ~{target_step} (Player 1 perspective, raw) ---")
            dump_economy("Player 1 raw", obs)

        # =================================================================
        # TEST C: PLAYER 2 PERSPECTIVE MODE via raw protobuf
        # =================================================================
        print(f"\n{'='*60}")
        print("TEST C: PLAYER 2 PERSPECTIVE (raw protobuf, observed_player_id=2)")
        print(f"{'='*60}")

        resp = send_request(ws, start_replay=sc_pb.RequestStartReplay(
            replay_data=replay_data,
            options=interface,
            observed_player_id=2,
            disable_fog=True,
            realtime=False,
        ))
        print(f"  start_replay status: {sc_pb.Status.Name(resp.status)}")

        for target_step in STEPS_TO_SAMPLE:
            send_request(ws, step=sc_pb.RequestStep(count=target_step))
            resp = send_request(ws, observation=sc_pb.RequestObservation())
            obs = resp.observation.observation
            print(f"\n--- STEP ~{target_step} (Player 2 perspective, raw) ---")
            dump_economy("Player 2 raw", obs)

        print("\n" + "="*60)
        print("DIAGNOSTIC COMPLETE")
        print("="*60)
        print("\nIf observer mode still shows zeros with raw protobufs,")
        print("the limitation is in the SC2 BINARY, not pysc2.")
        print("If it now shows data, pysc2 was filtering it.")

    finally:
        # Clean shutdown
        try:
            send_request(ws, quit=sc_pb.RequestQuit())
        except Exception:
            pass
        ws.close()
        # Clean up the SC2 process
        try:
            sc2_proc.__exit__(None, None, None)
        except Exception:
            pass


if __name__ == "__main__":
    main()
