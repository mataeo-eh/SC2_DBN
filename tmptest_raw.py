"""
Raw protobuf API test: bypasses pysc2's RemoteController entirely.

Uses pysc2 ONLY to locate and launch the SC2 binary (version-matched).
All API communication goes through a raw websocket with hand-built
protobuf Request/Response messages.

Goal: determine which fields actually change with player perspective in
replay observer mode.

Key questions:
  1. In observer mode with observed_player_id=0 and disable_fog=True,
     is raw_data.units effectively identical regardless of perspective?
  2. If it is NOT identical, which parts differ?
     - player_common / score / score_details
     - raw_data.player.upgrade_ids
     - raw unit list membership / owner counts
     - per-unit "core" fields (type, pos, health, build_progress, etc.)
     - per-unit order fields
  3. Does observer-mode perspective switching match a direct replay load
     with observed_player_id=1 or observed_player_id=2?

This is intended to answer whether the extraction pipeline really needs
per-frame perspective switching, or whether a single observer-mode
observation is sufficient for the fields we care about.
"""

import time
import sys
from collections import Counter
from pathlib import Path

import websocket
from pysc2 import run_configs
from pysc2.lib import replay as replay_lib
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import common_pb2


# ---------- CONFIG ----------
REPLAY_PATH = "replays/match_4184936.SC2Replay"
REPLAY_DIR = "replays"
AUTO_FIND_BOTH_PLAYERS_UPGRADES = True
STEPS_TO_SAMPLE = [50, 200]
UPGRADE_SAMPLE_OFFSET = 100
COSMETIC_UPGRADE_PREFIXES = ("Spray",)
LOG_OUTPUT_PATH = Path(__file__).with_suffix(".txt")
# -----------------------------


class Tee:
    """
    Duplicate writes to multiple text streams.
    """
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


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

import mpyq
from s2protocol import versions

def list_completed_upgrades(replay_path: str):
    archive = mpyq.MPQArchive(replay_path)
    header_content = archive.header['user_data_header']['content']
    header = versions.latest().decode_replay_header(header_content)
    base_build = header['m_version']['m_baseBuild']
    protocol = versions.build(base_build)

    tracker_raw = archive.read_file('replay.tracker.events')

    upgrades = {}
    for event in protocol.decode_replay_tracker_events(tracker_raw):
        if event['_event'] == 'NNet.Replay.Tracker.SUpgradeEvent':
            pid = event['m_playerId']
            gl = event['_gameloop']
            name = event['m_upgradeTypeName']
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            upgrades.setdefault(pid, []).append((gl, name))

    return upgrades


def is_meaningful_upgrade(upgrade_name: str) -> bool:
    """
    Filter out cosmetic/non-tech tracker upgrades that are not useful for
    pipeline validation.
    """
    return not any(upgrade_name.startswith(prefix) for prefix in COSMETIC_UPGRADE_PREFIXES)


def filter_meaningful_upgrades(upgrades: dict) -> dict:
    """
    Keep only meaningful, non-cosmetic upgrade completions.
    """
    filtered = {}
    for pid, events in upgrades.items():
        kept = [(gl, name) for gl, name in events if is_meaningful_upgrade(name)]
        if kept:
            filtered[pid] = kept
    return filtered


def replay_has_both_players_upgrades(replay_path: str) -> tuple[bool, dict]:
    """
    Return whether both players completed at least one upgrade in this replay.
    """
    upgrades = filter_meaningful_upgrades(list_completed_upgrades(replay_path))
    p1_has = bool(upgrades.get(1))
    p2_has = bool(upgrades.get(2))
    return (p1_has and p2_has), upgrades


def find_replay_with_both_players_upgrades(replay_dir: str) -> tuple[Path | None, dict | None]:
    """
    Scan replay files and return the first replay where both players completed
    at least one upgrade.
    """
    replay_paths = sorted(Path(replay_dir).rglob("*.SC2Replay"))

    for replay_path in replay_paths:
        try:
            qualifies, upgrades = replay_has_both_players_upgrades(str(replay_path))
        except Exception as exc:
            print(f"Skipping {replay_path.name}: failed to parse tracker events ({exc})")
            continue

        if qualifies:
            return replay_path, upgrades

    return None, None


def extract_match_id(replay_path: Path) -> str:
    """
    Extract a human-readable match identifier from the replay filename.
    """
    stem = replay_path.stem
    if stem.startswith("match_"):
        return stem.removeprefix("match_")
    return stem


def build_upgrade_sample_steps(upgrades: dict, replay_duration_loops: int) -> list[int]:
    """
    Build sample steps 100 loops before and after each player's first meaningful
    completed upgrade.
    """
    first_events = []
    for pid in (1, 2):
        events = upgrades.get(pid, [])
        if events:
            first_events.append(events[0])

    steps = []
    for gl, _name in first_events:
        before = max(1, gl - UPGRADE_SAMPLE_OFFSET)
        after = min(replay_duration_loops, gl + UPGRADE_SAMPLE_OFFSET)
        steps.extend([before, after])

    return sorted(set(steps))


def dump_observation_summary(label, obs):
    """
    Print a compact summary of perspective-sensitive and raw-unit fields.

    Args:
        label: descriptive label for this observation
        obs: Observation sub-message from ResponseObservation
    """
    units = list(obs.raw_data.units)
    owner_counts = Counter(u.owner for u in units)
    owned_units = [u for u in units if u.owner in (1, 2)]
    upgrade_ids = list(obs.raw_data.player.upgrade_ids)
    order_counts = {
        1: sum(len(u.orders) for u in units if u.owner == 1),
        2: sum(len(u.orders) for u in units if u.owner == 2),
    }

    print(f"\n  [{label}] summary:")
    print(f"    game_loop            : {obs.game_loop}")
    print(f"    player_common.id     : {obs.player_common.player_id}")
    print(f"    upgrade_ids          : {upgrade_ids if upgrade_ids else '[]'}")
    print(f"    total raw units      : {len(units)}")
    print(f"    player-owned units   : {len(owned_units)}")
    print(f"    owner counts         : {dict(sorted(owner_counts.items()))}")
    print(f"    total orders by owner: P1={order_counts[1]}  P2={order_counts[2]}")


def order_signature(unit):
    """
    Build a compact, comparable signature for a unit's orders.
    """
    sig = []
    for order in unit.orders:
        target = None
        if order.HasField("target_world_space_pos"):
            target = (
                "pos",
                round(order.target_world_space_pos.x, 3),
                round(order.target_world_space_pos.y, 3),
                round(order.target_world_space_pos.z, 3),
            )
        elif order.target_unit_tag:
            target = ("tag", order.target_unit_tag)

        sig.append((
            order.ability_id,
            round(order.progress, 4),
            target,
        ))
    return tuple(sig)


def core_signature(unit):
    """
    Build a perspective-comparison signature for unit fields expected to be
    globally visible in observer mode.
    """
    return (
        unit.owner,
        unit.unit_type,
        round(unit.pos.x, 4),
        round(unit.pos.y, 4),
        round(unit.pos.z, 4),
        round(unit.facing, 4),
        round(unit.radius, 4),
        round(unit.build_progress, 4),
        round(unit.health, 4),
        round(unit.health_max, 4),
        round(unit.shield, 4),
        round(unit.shield_max, 4),
        round(unit.energy, 4),
        round(unit.energy_max, 4),
        round(unit.weapon_cooldown, 4),
        unit.cloak,
        unit.is_selected,
        unit.is_blip,
        unit.is_powered,
        unit.is_active,
        unit.attack_upgrade_level,
        unit.armor_upgrade_level,
        unit.shield_upgrade_level,
        tuple(unit.buff_ids),
        unit.cargo_space_taken,
        unit.cargo_space_max,
        len(unit.passengers),
    )


def compare_observations(label_a, obs_a, label_b, obs_b):
    """
    Compare two observations captured at the same replay frame.

    Highlights whether differences are limited to perspective-specific fields
    or whether raw unit data itself changes.
    """
    print(f"\n  [COMPARE] {label_a}  vs  {label_b}")
    print(f"    game_loop match      : {obs_a.game_loop == obs_b.game_loop} "
          f"({obs_a.game_loop} vs {obs_b.game_loop})")
    print(f"    player_common.id     : {obs_a.player_common.player_id} vs {obs_b.player_common.player_id}")
    print(f"    upgrade_ids          : {list(obs_a.raw_data.player.upgrade_ids)} "
          f"vs {list(obs_b.raw_data.player.upgrade_ids)}")

    units_a = {u.tag: u for u in obs_a.raw_data.units if u.owner in (1, 2)}
    units_b = {u.tag: u for u in obs_b.raw_data.units if u.owner in (1, 2)}

    only_a = sorted(set(units_a) - set(units_b))
    only_b = sorted(set(units_b) - set(units_a))
    shared_tags = sorted(set(units_a) & set(units_b))

    core_diffs = []
    order_diffs = []
    for tag in shared_tags:
        ua = units_a[tag]
        ub = units_b[tag]
        if core_signature(ua) != core_signature(ub):
            core_diffs.append((tag, ua.owner, ua.unit_type))
        if order_signature(ua) != order_signature(ub):
            order_diffs.append((tag, ua.owner, ua.unit_type, order_signature(ua), order_signature(ub)))

    order_diff_counts = Counter(owner for _, owner, _, _, _ in order_diffs)

    print(f"    player-owned unit tags: {len(units_a)} vs {len(units_b)}")
    print(f"    tags only in A        : {len(only_a)}")
    print(f"    tags only in B        : {len(only_b)}")
    print(f"    core-field diffs      : {len(core_diffs)}")
    print(f"    order-field diffs     : {len(order_diffs)} "
          f"(P1={order_diff_counts.get(1, 0)}, P2={order_diff_counts.get(2, 0)})")

    if only_a:
        print(f"    sample only-in-A tags : {only_a[:5]}")
    if only_b:
        print(f"    sample only-in-B tags : {only_b[:5]}")
    if core_diffs:
        sample = core_diffs[:5]
        print(f"    sample core diffs     : {sample}")
    if order_diffs:
        print("    sample order diffs    :")
        for tag, owner, unit_type, sig_a, sig_b in order_diffs[:3]:
            print(f"      tag={tag} owner={owner} unit_type={unit_type}")
            print(f"        A: {sig_a}")
            print(f"        B: {sig_b}")


def start_replay(ws, replay_data, interface, observed_player_id):
    """
    Start a replay in either observer mode (0) or direct player mode (1/2).
    """
    req = sc_pb.RequestStartReplay(
        replay_data=replay_data,
        options=interface,
        observed_player_id=observed_player_id,
        disable_fog=True,
        realtime=False,
    )
    return send_request(ws, start_replay=req)


def switch_to_player(ws, player_id):
    """
    Switch observer-mode perspective to a specific player.
    """
    switch_req = sc_pb.RequestObserverAction(
        actions=[sc_pb.ObserverAction(
            player_perspective=sc_pb.ActionObserverPlayerPerspective(
                player_id=player_id
            )
        )]
    )
    return send_request(ws, obs_action=switch_req)


def observe_at_step(ws, step_count):
    """
    Step replay forward and return the resulting observation.
    """
    send_request(ws, step=sc_pb.RequestStep(count=step_count))
    resp = send_request(ws, observation=sc_pb.RequestObservation())
    return resp.observation.observation


def main():
    # --- absl flags init (required by pysc2 internals even for path lookup) ---
    from absl import flags
    flags.FLAGS(["tmptest_raw.py"])

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    log_handle = LOG_OUTPUT_PATH.open("w", encoding="utf-8")
    sys.stdout = Tee(original_stdout, log_handle)
    sys.stderr = Tee(original_stderr, log_handle)

    try:
        print(f"Writing diagnostic output to: {LOG_OUTPUT_PATH.resolve()}")
        print()

        selected_replay_path = Path(REPLAY_PATH)
        selected_upgrades = None

        if AUTO_FIND_BOTH_PLAYERS_UPGRADES:
            print(f"Scanning replay files in {Path(REPLAY_DIR).resolve()} for a replay where both players completed upgrades...")
            found_path, found_upgrades = find_replay_with_both_players_upgrades(REPLAY_DIR)
            if found_path is None:
                raise RuntimeError(
                    f"No replay found in {Path(REPLAY_DIR).resolve()} where both players completed at least one upgrade."
                )
            selected_replay_path = found_path
            selected_upgrades = found_upgrades
            print(f"Selected replay : {selected_replay_path.name}")
            print(f"Match ID        : {extract_match_id(selected_replay_path)}")
            print(f"P1 upgrades     : {len(selected_upgrades.get(1, []))}")
            print(f"P2 upgrades     : {len(selected_upgrades.get(2, []))}")
            print(f"First P1 upgrade : {selected_upgrades.get(1, [None])[0]}")
            print(f"First P2 upgrade : {selected_upgrades.get(2, [None])[0]}")
            print()
        else:
            qualifies, selected_upgrades = replay_has_both_players_upgrades(str(selected_replay_path))
            print(f"Using configured replay: {selected_replay_path.name}")
            print(f"Match ID              : {extract_match_id(selected_replay_path)}")
            print(f"Both players upgraded : {qualifies}")
            print(f"P1 upgrades           : {len(selected_upgrades.get(1, []))}")
            print(f"P2 upgrades           : {len(selected_upgrades.get(2, []))}")
            print()

        # --- Step 1: Load replay and detect version (need pysc2 for this) ---
        replay_path_abs = str(selected_replay_path.resolve())
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

            sample_steps = build_upgrade_sample_steps(
                selected_upgrades or {},
                info.game_duration_loops,
            )
            if sample_steps:
                print("Meaningful tracker upgrades:")
                for pid in (1, 2):
                    events = selected_upgrades.get(pid, [])
                    if events:
                        print(f"  P{pid}: {events}")
                print(f"Sampling steps : {sample_steps}")
                print(f"Sampling rule  : +/- {UPGRADE_SAMPLE_OFFSET} loops around each player's first meaningful completed upgrade")
            else:
                sample_steps = list(STEPS_TO_SAMPLE)
                print(f"Sampling steps : {sample_steps} (fallback default)")
            print()

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

            # Step and compare exact-frame observations across perspectives
            for target_step in sample_steps:
                print(f"\n--- TARGET STEP {target_step} (exact-frame perspective comparison) ---")

                # Fresh observer-mode replay for this sample so all comparisons are
                # against the same exact frame and not affected by earlier switches.
                resp = start_replay(ws, replay_data, interface, observed_player_id=0)
                print(f"  observer restart status: {sc_pb.Status.Name(resp.status)}")

                obs_base = observe_at_step(ws, target_step)
                dump_observation_summary("Observer raw (no switch)", obs_base)
                dump_economy("Observer raw (no switch)", obs_base)

                owners = sorted(set(u.owner for u in obs_base.raw_data.units))
                print(f"  [raw units] unique owners: {owners}")

                print(f"\n--- Switching to Player 1 perspective (same frame, no step) ---")
                switch_resp = switch_to_player(ws, 1)
                print(f"  observer_action response status: {sc_pb.Status.Name(switch_resp.status)}")
                print(f"  response type: {switch_resp.WhichOneof('response')}")
                obs_p1 = send_request(ws, observation=sc_pb.RequestObservation()).observation.observation
                dump_observation_summary("After raw switch to P1", obs_p1)
                dump_economy("After raw switch to P1", obs_p1)
                compare_observations("Observer raw (no switch)", obs_base, "Observer switched P1", obs_p1)

                print(f"\n--- Switching to Player 2 perspective (same frame, no step) ---")
                switch_resp2 = switch_to_player(ws, 2)
                print(f"  observer_action response status: {sc_pb.Status.Name(switch_resp2.status)}")
                print(f"  response type: {switch_resp2.WhichOneof('response')}")
                obs_p2 = send_request(ws, observation=sc_pb.RequestObservation()).observation.observation
                dump_observation_summary("After raw switch to P2", obs_p2)
                dump_economy("After raw switch to P2", obs_p2)
                compare_observations("Observer raw (no switch)", obs_base, "Observer switched P2", obs_p2)
                compare_observations("Observer switched P1", obs_p1, "Observer switched P2", obs_p2)

                # Compare the observer-mode switched snapshots to direct player-perspective loads.
                print(f"\n--- Direct replay load: Player 1 perspective at step {target_step} ---")
                resp = start_replay(ws, replay_data, interface, observed_player_id=1)
                print(f"  direct P1 start status: {sc_pb.Status.Name(resp.status)}")
                obs_direct_p1 = observe_at_step(ws, target_step)
                dump_observation_summary("Direct Player 1", obs_direct_p1)
                dump_economy("Direct Player 1", obs_direct_p1)
                compare_observations("Observer switched P1", obs_p1, "Direct Player 1", obs_direct_p1)

                print(f"\n--- Direct replay load: Player 2 perspective at step {target_step} ---")
                resp = start_replay(ws, replay_data, interface, observed_player_id=2)
                print(f"  direct P2 start status: {sc_pb.Status.Name(resp.status)}")
                obs_direct_p2 = observe_at_step(ws, target_step)
                dump_observation_summary("Direct Player 2", obs_direct_p2)
                dump_economy("Direct Player 2", obs_direct_p2)
                compare_observations("Observer switched P2", obs_p2, "Direct Player 2", obs_direct_p2)

            # =================================================================
            # TEST B: FINAL INTERPRETATION GUIDE
            # =================================================================
            print(f"\n{'='*60}")
            print("HOW TO INTERPRET THE DIAGNOSTIC")
            print(f"{'='*60}")
            print("  If 'core-field diffs' is 0 and 'tags only in A/B' is 0, then the")
            print("  raw unit list is effectively perspective-invariant for those fields.")
            print("  If 'order-field diffs' is non-zero, then unit.orders is perspective-")
            print("  sensitive even when the rest of raw_data.units is stable.")
            print("  If observer-switched P1 matches direct P1 (and same for P2), then")
            print("  RequestObserverAction is reproducing direct player perspective.")

            print("\n" + "="*60)
            print("DIAGNOSTIC COMPLETE")
            print("="*60)
            print("\nThis run should tell you exactly whether perspective switching")
            print("is needed for the fields your pipeline actually extracts.")

        finally:
            # Clean shutdown
            try:
                send_request(ws, quit=sc_pb.RequestQuit())
            except Exception:
                pass
            try:
                ws.close()
            except Exception:
                pass
            # Clean up the SC2 process
            try:
                sc2_proc.__exit__(None, None, None)
            except Exception:
                pass
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        log_handle.close()


if __name__ == "__main__":
    main()
