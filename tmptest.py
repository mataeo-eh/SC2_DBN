"""
Economy diagnostic: loads one replay via the controller API (using the
pipeline's version-matched approach), steps forward, and dumps economy-related
fields for both players.

Key insight being tested: in observer mode (observed_player_id=0),
player_common and score are EMPTY unless you switch perspective to a
specific player via RequestObserverAction before each observe() call.
The game engine computes economy for both players, but the API only
surfaces it when you ask from a specific player's point of view.
"""

import sys
from pathlib import Path

from pysc2 import run_configs
from pysc2.lib import replay
from s2clientprotocol import sc2api_pb2 as sc_pb, common_pb2

# ---------- CONFIG ----------
REPLAY_PATH = "replays/match_4184936.SC2Replay"
STEPS_TO_SAMPLE = {10, 50, 100}
# -----------------------------


def dump_economy(label, obs):
    """
    Print economy-related fields from an observation protobuf.

    Args:
        label: A string label for this dump (e.g. "Observer" or "Player 1")
        obs: The observation protobuf (obs_response.observation)
    """
    pc = obs.player_common
    print(f"\n  [{label}] player_common:")
    print(f"    player_id : {pc.player_id}")
    print(f"    minerals  : {pc.minerals}")
    print(f"    vespene   : {pc.vespene}")
    print(f"    food_used : {pc.food_used}")
    print(f"    food_cap  : {pc.food_cap}")
    print(f"    food_army : {pc.food_army}")
    print(f"    food_workers: {pc.food_workers}")
    print(f"    idle_worker_count: {pc.idle_worker_count}")
    print(f"    army_count: {pc.army_count}")

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


def switch_perspective(controller, player_id):
    """
    Switch the observer's perspective to a specific player.

    After switching, the next observe() call will return that player's
    player_common, score, and upgrade_ids.

    Args:
        controller: SC2 controller instance
        player_id: Player ID to switch to (1 or 2)
    """
    obs_action = sc_pb.RequestObserverAction(
        actions=[sc_pb.ObserverAction(
            player_perspective=sc_pb.ActionObserverPlayerPerspective(
                player_id=player_id
            )
        )]
    )
    controller.observer_actions(obs_action)


def main():
    # absl flags init required by pysc2
    from absl import flags
    flags.FLAGS(["tmptest.py"])

    # --- Step 1: Version-matched replay loading (same as pipeline) ---
    replay_path_abs = str(Path(REPLAY_PATH).resolve())
    print(f"Loading replay: {replay_path_abs}")

    # Get initial run_config to read the replay file
    initial_config = run_configs.get()
    replay_data = initial_config.replay_data(replay_path_abs)

    # Detect replay version and get a version-matched run_config
    replay_version = replay.get_replay_version(replay_data)
    print(f"Replay version: {replay_version.game_version} "
          f"(build {replay_version.build_version})")
    run_config = run_configs.get(version=replay_version)

    # --- Step 2: Interface options for ground truth access ---
    interface = sc_pb.InterfaceOptions(
        raw=True,
        score=True,
        show_cloaked=True,
        show_burrowed_shadows=True,
        show_placeholders=True,
    )

    # --- Step 3: Start SC2 and replay in observer mode ---
    with run_config.start(want_rgb=False) as controller:
        # Get replay info (metadata)
        info = controller.replay_info(replay_data)
        print(f"Map: {info.map_name}")
        print(f"Duration: {info.game_duration_loops} loops")
        for i, pi in enumerate(info.player_info):
            race = common_pb2.Race.Name(pi.player_info.race_actual)
            print(f"  Player {i+1}: {race}, MMR: {pi.player_mmr}")

        # Start in observer mode (observed_player_id=0 on the wire)
        controller.start_replay(sc_pb.RequestStartReplay(
            replay_data=replay_data,
            options=interface,
            observed_player_id=0,   # 0 = observer mode (must be explicit on wire)
            disable_fog=True,
            realtime=False,
        ))

        # --- Step 4: Step through and dump economy at sample points ---
        step = 0
        max_step = max(STEPS_TO_SAMPLE)
        while step <= max_step:
            controller.step(1)

            if step in STEPS_TO_SAMPLE:
                print(f"\n{'='*60}")
                print(f"STEP {step}")
                print(f"{'='*60}")

                # A) Raw observer observe (no perspective switch) — expect empty economy
                obs_response = controller.observe()
                obs = obs_response.observation
                dump_economy("Observer (no perspective)", obs)

                # Raw units — confirm we see units from both players
                owners = set(u.owner for u in obs.raw_data.units)
                print(f"\n  [raw units] unique owner values: {owners}")

                # B) Switch to Player 1, then observe — should get P1 economy
                switch_perspective(controller, 1)
                obs_p1 = controller.observe().observation
                dump_economy("After switch to Player 1 (no step)", obs_p1)

                # C) Switch to Player 1, STEP, then observe
                switch_perspective(controller, 1)
                controller.step(1)
                obs_p1b = controller.observe().observation
                dump_economy("After switch to Player 1 (with step)", obs_p1b)

                # D) Switch to Player 2, STEP, then observe
                switch_perspective(controller, 2)
                controller.step(1)
                obs_p2b = controller.observe().observation
                dump_economy("After switch to Player 2 (with step)", obs_p2b)

                # E) List all top-level field names for further exploration
                print(f"\n  [obs_response field names]: "
                      f"{[f.name for f in obs_response.DESCRIPTOR.fields]}")
                print(f"  [obs field names]: "
                      f"{[f.name for f in obs.DESCRIPTOR.fields]}")

            step += 1

        # --- Step 5: Re-run the replay in PLAYER mode to compare ---
        print(f"\n{'='*60}")
        print("RE-RUNNING IN PLAYER-PERSPECTIVE MODE (observed_player_id=1)")
        print(f"{'='*60}")

        controller.start_replay(sc_pb.RequestStartReplay(
            replay_data=replay_data,
            options=interface,
            observed_player_id=1,
            disable_fog=True,
            realtime=False,
        ))

        step = 0
        while step <= max_step:
            controller.step(1)
            if step in STEPS_TO_SAMPLE:
                obs = controller.observe().observation
                print(f"\n--- STEP {step} (Player 1 perspective) ---")
                dump_economy("Player 1 perspective", obs)
            step += 1

        # Now restart as Player 2
        print(f"\n{'='*60}")
        print("RE-RUNNING IN PLAYER-PERSPECTIVE MODE (observed_player_id=2)")
        print(f"{'='*60}")

        controller.start_replay(sc_pb.RequestStartReplay(
            replay_data=replay_data,
            options=interface,
            observed_player_id=2,
            disable_fog=True,
            realtime=False,
        ))

        step = 0
        while step <= max_step:
            controller.step(1)
            if step in STEPS_TO_SAMPLE:
                obs = controller.observe().observation
                print(f"\n--- STEP {step} (Player 2 perspective) ---")
                dump_economy("Player 2 perspective", obs)
            step += 1

        print("\nDiagnostic complete.")


if __name__ == "__main__":
    main()
