"""
032_passenger_diagnostic.py: Diagnostic script to investigate SC2 proto passengers & dead_units.

PURPOSE:
    Determine whether the s2clientprotocol `passengers` field on Unit messages
    is populated by the SC2 engine during replay playback. If it is, it could
    replace the distance-based heuristic currently used in resolve_hidden_units()
    for detecting units inside buildings/transports.

    Also investigates dead_units event behavior for building-entry vs actual death.

APPROACH:
    1. Load a replay using the same pysc2 pipeline approach as the extraction code.
    2. Test both OBSERVER MODE (observed_player_id=0) and PLAYER PERSPECTIVE
       (observed_player_id=1) since prior research (prompt 030) suggested
       passengers might only populate in player-perspective mode.
    3. For each mode, iterate game steps and log:
       - Gas building passengers/cargo fields
       - Transport/bunker passengers/cargo fields
       - dead_units events
       - Unit tag appearance/disappearance patterns

USAGE:
    python scripts/032_passenger_diagnostic.py

DEPENDS ON:
    - pysc2, s2clientprotocol (installed in the project venv)
    - SC2-gamestate-extractor/src_new/pipeline/replay_loader.py (ReplayLoader)
    - replays/match_4184936.SC2Replay (test replay with gas mining)
"""

import sys
import os
import logging
from pathlib import Path
from collections import defaultdict

# Ensure project root is on sys.path so we can import from SC2-gamestate-extractor
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "SC2-gamestate-extractor"))

from absl import flags

# Parse absl flags early (required by pysc2 internals)
if not flags.FLAGS.is_parsed():
    flags.FLAGS.mark_as_parsed()

from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import common_pb2
from pysc2 import run_configs
from pysc2.lib import replay as replay_lib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPLAY_PATH = PROJECT_ROOT / "replays" / "match_4184936.SC2Replay"

# SC2 unit type IDs for buildings and transports we care about.
# Sourced from pysc2.lib.units enums.
GAS_BUILDING_IDS = {
    20: "Refinery",
    1960: "RefineryRich",
    61: "Assimilator",
    1955: "AssimilatorRich",
    88: "Extractor",
    1956: "ExtractorRich",
}

TRANSPORT_IDS = {
    24: "Bunker",
    18: "CommandCenter",
    132: "OrbitalCommand",
    130: "PlanetaryFortress",
    54: "Medivac",
    106: "Overlord",         # OverlordTransport is 893
    893: "OverlordTransport",
    81: "WarpPrism",
    95: "NydusNetwork",
    142: "NydusCanal",
}

# All building/transport IDs we want to inspect
ALL_CONTAINER_IDS = {**GAS_BUILDING_IDS, **TRANSPORT_IDS}

# How many game loops to step between observations
STEP_SIZE = 8

# Max frames to process (0 = all)
MAX_FRAMES = 0

# How many frames of detailed logging to print
DETAIL_LOG_LIMIT = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def inspect_unit_fields(unit):
    """
    Inspect what passenger/cargo-related attributes exist on a unit proto object.

    Args:
        unit: A unit proto message from raw_data.units

    Returns:
        Dict describing available fields and their values.
    """
    result = {}

    # Check passengers field (repeated PassengerUnit in the proto)
    if hasattr(unit, 'passengers'):
        result['has_passengers_attr'] = True
        passengers = list(unit.passengers)
        result['passengers_count'] = len(passengers)
        result['passengers'] = []
        for p in passengers:
            pdata = {}
            for field_name in ['tag', 'health', 'health_max', 'shield', 'shield_max',
                               'energy', 'energy_max', 'unit_type']:
                if hasattr(p, field_name):
                    pdata[field_name] = getattr(p, field_name)
            result['passengers'].append(pdata)
    else:
        result['has_passengers_attr'] = False

    # Check cargo fields
    for field in ['cargo_space_taken', 'cargo_space_max']:
        if hasattr(unit, field):
            result[field] = getattr(unit, field)
        else:
            result[f'has_{field}'] = False

    return result


def get_unit_type_name_safe(unit_type_id):
    """
    Try to get the unit type name from pysc2. Falls back to the integer ID.

    Args:
        unit_type_id: Integer unit type ID from the proto.

    Returns:
        String name or "unknown_<id>".
    """
    try:
        from pysc2.lib import units as pysc2_units
        for race in [pysc2_units.Terran, pysc2_units.Protoss, pysc2_units.Zerg, pysc2_units.Neutral]:
            for member in race:
                if member.value == unit_type_id:
                    return member.name
    except Exception:
        pass
    return f"unknown_{unit_type_id}"


# ---------------------------------------------------------------------------
# Main diagnostic runner
# ---------------------------------------------------------------------------

def run_diagnostic(mode: str):
    """
    Run the passenger/dead_units diagnostic in a given observation mode.

    Args:
        mode: Either "observer" (observed_player_id=0) or "player1"
              (observed_player_id=1).

    Returns:
        Dict of collected diagnostic data.
    """
    logger.info(f"{'='*70}")
    logger.info(f"RUNNING DIAGNOSTIC IN MODE: {mode}")
    logger.info(f"{'='*70}")

    # Load replay data and version (same approach as pipeline)
    run_config = run_configs.get()
    replay_data = run_config.replay_data(str(REPLAY_PATH.resolve()))
    replay_version = replay_lib.get_replay_version(replay_data)
    logger.info(f"Replay version: {replay_version.game_version}")

    # Get version-matched run_config
    run_config = run_configs.get(version=replay_version)

    # Interface options: raw=True, score=True, show everything
    interface = sc_pb.InterfaceOptions(
        raw=True,
        score=True,
        show_cloaked=True,
        show_burrowed_shadows=True,
        show_placeholders=True,
    )

    # Accumulators
    results = {
        'mode': mode,
        'gas_buildings_with_passengers': [],   # frames where gas building had passengers
        'gas_buildings_with_cargo': [],         # frames where gas building had cargo > 0
        'transports_with_passengers': [],
        'transports_with_cargo': [],
        'dead_units_events': [],                # (game_loop, [tags])
        'disappeared_not_dead': [],             # tags that vanished but weren't in dead_units
        'field_inspection': None,               # first unit's field inspection
        'all_container_observations': 0,
        'frames_processed': 0,
        'proto_field_names': None,              # DESCRIPTOR field names of a Unit message
    }

    previous_tags = set()
    detail_logged = 0

    with run_config.start(want_rgb=False) as controller:
        # Get replay info
        info = controller.replay_info(replay_data)
        logger.info(f"Map: {info.map_name}, Duration: {info.game_duration_loops} loops")

        # Configure replay start based on mode
        if mode == "observer":
            replay_request = sc_pb.RequestStartReplay(
                replay_data=replay_data,
                options=interface,
                observed_player_id=0,
                disable_fog=True,
                realtime=False,
            )
        else:
            replay_request = sc_pb.RequestStartReplay(
                replay_data=replay_data,
                options=interface,
                observed_player_id=1,
                disable_fog=True,
                realtime=False,
            )

        controller.start_replay(replay_request)
        logger.info("Replay started successfully")

        max_loops = info.game_duration_loops
        if MAX_FRAMES > 0:
            max_loops = min(max_loops, MAX_FRAMES * STEP_SIZE)

        frame_count = 0
        game_loop = 0

        while game_loop < max_loops:
            try:
                controller.step(STEP_SIZE)

                # If in observer mode, optionally switch perspective
                # (raw_data.units is global, but passengers might need perspective)
                if mode == "observer":
                    # Try switching to player 1 perspective to see if it helps
                    obs_action = sc_pb.RequestObserverAction(
                        actions=[sc_pb.ObserverAction(
                            player_perspective=sc_pb.ActionObserverPlayerPerspective(
                                player_id=1
                            )
                        )]
                    )
                    controller.observer_actions(obs_action)

                obs = controller.observe()

                if obs.player_result:
                    logger.info(f"Replay ended at loop {game_loop}")
                    break

                game_loop = obs.observation.game_loop
                raw_data = obs.observation.raw_data
                frame_count += 1

                # ---- One-time: inspect proto field names on the Unit message ----
                if results['proto_field_names'] is None and len(raw_data.units) > 0:
                    first_unit = raw_data.units[0]
                    # Get proto DESCRIPTOR fields
                    try:
                        descriptor_fields = [f.name for f in first_unit.DESCRIPTOR.fields]
                        results['proto_field_names'] = descriptor_fields
                        logger.info(f"Unit DESCRIPTOR fields: {descriptor_fields}")
                    except Exception as e:
                        logger.warning(f"Could not read DESCRIPTOR: {e}")
                        results['proto_field_names'] = []

                    # Also do a detailed field inspection
                    results['field_inspection'] = inspect_unit_fields(first_unit)
                    logger.info(f"First unit field inspection: {results['field_inspection']}")

                # ---- Collect current unit tags ----
                current_tags = set()
                current_owner_map = {}   # tag -> owner

                for unit in raw_data.units:
                    if unit.owner in {1, 2}:
                        current_tags.add(unit.tag)
                        current_owner_map[unit.tag] = unit.owner

                # ---- Check gas buildings and transports ----
                for unit in raw_data.units:
                    if unit.unit_type not in ALL_CONTAINER_IDS:
                        continue
                    if unit.owner not in {1, 2}:
                        continue

                    container_name = ALL_CONTAINER_IDS[unit.unit_type]
                    info_dict = inspect_unit_fields(unit)
                    info_dict['game_loop'] = game_loop
                    info_dict['unit_tag'] = unit.tag
                    info_dict['unit_type'] = container_name
                    info_dict['owner'] = unit.owner
                    results['all_container_observations'] += 1

                    is_gas = unit.unit_type in GAS_BUILDING_IDS
                    is_transport = unit.unit_type in TRANSPORT_IDS

                    # Check for non-empty passengers
                    passengers_count = info_dict.get('passengers_count', 0)
                    cargo_taken = info_dict.get('cargo_space_taken', 0)

                    if passengers_count > 0:
                        if is_gas:
                            results['gas_buildings_with_passengers'].append(info_dict)
                        if is_transport:
                            results['transports_with_passengers'].append(info_dict)

                        if detail_logged < DETAIL_LOG_LIMIT:
                            logger.info(
                                f"  [PASSENGERS FOUND] Loop {game_loop}: "
                                f"{container_name} (tag={unit.tag}, owner={unit.owner}) "
                                f"has {passengers_count} passenger(s): "
                                f"{info_dict.get('passengers', [])}"
                            )
                            detail_logged += 1

                    if cargo_taken > 0:
                        if is_gas:
                            results['gas_buildings_with_cargo'].append(info_dict)
                        if is_transport:
                            results['transports_with_cargo'].append(info_dict)

                        if detail_logged < DETAIL_LOG_LIMIT:
                            logger.info(
                                f"  [CARGO > 0] Loop {game_loop}: "
                                f"{container_name} (tag={unit.tag}, owner={unit.owner}) "
                                f"cargo_space_taken={cargo_taken}, "
                                f"cargo_space_max={info_dict.get('cargo_space_max', '?')}"
                            )
                            detail_logged += 1

                # ---- Check dead_units ----
                dead_tags = list(raw_data.event.dead_units)
                if dead_tags:
                    results['dead_units_events'].append((game_loop, dead_tags))
                    if detail_logged < DETAIL_LOG_LIMIT:
                        # Try to identify what died
                        tag_names = []
                        for dt in dead_tags:
                            tag_names.append(str(dt))
                        logger.info(
                            f"  [DEAD_UNITS] Loop {game_loop}: "
                            f"{len(dead_tags)} dead tag(s): {dead_tags[:10]}"
                        )
                        detail_logged += 1

                # ---- Check disappeared units (not in dead_units) ----
                if previous_tags:
                    dead_set = set(dead_tags)
                    disappeared = previous_tags - current_tags - dead_set
                    if disappeared:
                        results['disappeared_not_dead'].append(
                            (game_loop, list(disappeared)[:10])  # cap for log size
                        )
                        if detail_logged < DETAIL_LOG_LIMIT and len(disappeared) <= 5:
                            logger.info(
                                f"  [DISAPPEARED] Loop {game_loop}: "
                                f"{len(disappeared)} tag(s) vanished but NOT in dead_units"
                            )
                            detail_logged += 1

                previous_tags = current_tags

                # Progress logging
                if frame_count % 500 == 0:
                    progress = (game_loop / info.game_duration_loops) * 100
                    logger.info(f"Progress: {progress:.1f}% (loop {game_loop})")

            except Exception as e:
                logger.warning(f"Error at loop {game_loop}: {e}")
                game_loop += STEP_SIZE
                continue

        results['frames_processed'] = frame_count
        logger.info(f"Processed {frame_count} frames in {mode} mode")

    return results


def print_summary(results_observer, results_player):
    """
    Print a comprehensive summary of findings from both modes.

    Args:
        results_observer: Results dict from observer mode run.
        results_player: Results dict from player-perspective mode run.
    """
    print("\n" + "=" * 80)
    print("PASSENGER & DEAD_UNITS DIAGNOSTIC SUMMARY")
    print("=" * 80)

    for label, results in [("OBSERVER MODE", results_observer),
                           ("PLAYER 1 MODE", results_player)]:
        print(f"\n{'-'*40}")
        print(f"  {label}")
        print(f"{'-'*40}")
        print(f"  Frames processed: {results['frames_processed']}")
        print(f"  Total container observations: {results['all_container_observations']}")

        # Proto fields
        if results['proto_field_names']:
            passenger_related = [f for f in results['proto_field_names']
                                 if 'passenger' in f.lower() or 'cargo' in f.lower()]
            print(f"  Passenger/cargo proto fields on Unit: {passenger_related}")
        else:
            print(f"  Proto field names: NOT AVAILABLE")

        # Field inspection
        fi = results.get('field_inspection', {})
        if fi:
            print(f"  has_passengers_attr: {fi.get('has_passengers_attr', 'N/A')}")
            print(f"  Field inspection sample: {fi}")

        # Gas buildings
        gas_p = results['gas_buildings_with_passengers']
        gas_c = results['gas_buildings_with_cargo']
        print(f"\n  Gas buildings with passengers > 0: {len(gas_p)} observations")
        print(f"  Gas buildings with cargo_space_taken > 0: {len(gas_c)} observations")

        if gas_p:
            print(f"  SAMPLE gas building with passengers:")
            for sample in gas_p[:3]:
                print(f"    Loop {sample['game_loop']}: {sample['unit_type']} "
                      f"(tag={sample['unit_tag']}) -> {sample.get('passengers', [])}")

        if gas_c:
            print(f"  SAMPLE gas building with cargo:")
            for sample in gas_c[:3]:
                print(f"    Loop {sample['game_loop']}: {sample['unit_type']} "
                      f"(tag={sample['unit_tag']}) -> cargo_taken={sample.get('cargo_space_taken', 0)}, "
                      f"cargo_max={sample.get('cargo_space_max', 0)}")

        # Transports
        trans_p = results['transports_with_passengers']
        trans_c = results['transports_with_cargo']
        print(f"\n  Transports with passengers > 0: {len(trans_p)} observations")
        print(f"  Transports with cargo_space_taken > 0: {len(trans_c)} observations")

        if trans_p:
            print(f"  SAMPLE transport with passengers:")
            for sample in trans_p[:3]:
                print(f"    Loop {sample['game_loop']}: {sample['unit_type']} "
                      f"(tag={sample['unit_tag']}) -> {sample.get('passengers', [])}")

        if trans_c:
            print(f"  SAMPLE transport with cargo:")
            for sample in trans_c[:3]:
                print(f"    Loop {sample['game_loop']}: {sample['unit_type']} "
                      f"(tag={sample['unit_tag']}) -> cargo_taken={sample.get('cargo_space_taken', 0)}")

        # Dead units
        dead_events = results['dead_units_events']
        total_dead = sum(len(tags) for _, tags in dead_events)
        print(f"\n  Dead_units events: {len(dead_events)} frames with deaths")
        print(f"  Total dead unit tags: {total_dead}")
        if dead_events:
            print(f"  First 3 dead_units events:")
            for loop, tags in dead_events[:3]:
                print(f"    Loop {loop}: {len(tags)} death(s) -> tags {tags[:5]}")

        # Disappeared but not dead
        disapp = results['disappeared_not_dead']
        print(f"\n  Frames with disappeared-but-not-dead units: {len(disapp)}")
        if disapp:
            total_disapp = sum(len(tags) for _, tags in disapp)
            print(f"  Total disappeared-not-dead tag instances: {total_disapp}")
            print(f"  First 3 examples:")
            for loop, tags in disapp[:3]:
                print(f"    Loop {loop}: {len(tags)} tag(s) vanished")

    # ---- Cross-mode comparison ----
    print(f"\n{'='*80}")
    print("CROSS-MODE COMPARISON")
    print(f"{'='*80}")

    obs_gas_p = len(results_observer['gas_buildings_with_passengers'])
    p1_gas_p = len(results_player['gas_buildings_with_passengers'])
    obs_gas_c = len(results_observer['gas_buildings_with_cargo'])
    p1_gas_c = len(results_player['gas_buildings_with_cargo'])
    obs_trans_p = len(results_observer['transports_with_passengers'])
    p1_trans_p = len(results_player['transports_with_passengers'])

    print(f"  Gas buildings with passengers:  Observer={obs_gas_p}  Player1={p1_gas_p}")
    print(f"  Gas buildings with cargo > 0:   Observer={obs_gas_c}  Player1={p1_gas_c}")
    print(f"  Transports with passengers:     Observer={obs_trans_p}  Player1={p1_trans_p}")

    if p1_gas_p > 0 and obs_gas_p == 0:
        print("\n  >> FINDING: Passengers populated in player mode but NOT observer mode!")
        print("  >> This confirms the prior research (prompt 030) hypothesis.")
    elif p1_gas_p > 0 and obs_gas_p > 0:
        print("\n  >> FINDING: Passengers populated in BOTH modes!")
        print("  >> Prior research (prompt 030) was wrong -- passengers IS available.")
    elif p1_gas_p == 0 and obs_gas_p == 0:
        print("\n  >> FINDING: Passengers NOT populated in EITHER mode.")
        print("  >> The SC2 engine does not populate passengers during replay playback.")
    else:
        print(f"\n  >> UNEXPECTED: Observer={obs_gas_p}, Player1={p1_gas_p}")

    # Definitive answer
    print(f"\n{'='*80}")
    print("DEFINITIVE ANSWERS")
    print(f"{'='*80}")

    any_passengers = (obs_gas_p + p1_gas_p + obs_trans_p + p1_trans_p) > 0
    any_cargo = (obs_gas_c + p1_gas_c) > 0

    print(f"  Q1: Does pysc2 expose the 'passengers' field?")
    has_attr = (results_observer.get('field_inspection', {}).get('has_passengers_attr', False)
                or results_player.get('field_inspection', {}).get('has_passengers_attr', False))
    print(f"      Attribute exists on proto: {has_attr}")
    print(f"      Populated with data:       {any_passengers}")

    print(f"\n  Q2: Do gas refineries populate passengers?")
    print(f"      Observer mode: {obs_gas_p > 0} ({obs_gas_p} observations)")
    print(f"      Player mode:   {p1_gas_p > 0} ({p1_gas_p} observations)")

    print(f"\n  Q3: Is cargo_space_taken populated on gas buildings?")
    print(f"      Observer mode: {obs_gas_c > 0} ({obs_gas_c} observations)")
    print(f"      Player mode:   {p1_gas_c > 0} ({p1_gas_c} observations)")

    print(f"\n  Q4: dead_units correctly excludes building-entry?")
    # If we see disappeared-not-dead events, dead_units is correctly excluding them
    obs_disapp = len(results_observer['disappeared_not_dead'])
    p1_disapp = len(results_player['disappeared_not_dead'])
    print(f"      Disappeared-not-dead events: Observer={obs_disapp}, Player1={p1_disapp}")
    if obs_disapp > 0 or p1_disapp > 0:
        print(f"      YES - units disappear from unit list without dead_units entry")
    else:
        print(f"      INCONCLUSIVE - no disappearance events observed")


def save_results_to_file(results_observer, results_player, output_path):
    """
    Save raw diagnostic results to a text file for the research report.

    Args:
        results_observer: Results dict from observer mode.
        results_player: Results dict from player-perspective mode.
        output_path: Path to write the output file.
    """
    import json

    # Make results JSON-serializable
    def sanitize(obj):
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [sanitize(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)

    data = {
        'observer_mode': sanitize(results_observer),
        'player1_mode': sanitize(results_player),
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Raw results saved to {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not REPLAY_PATH.exists():
        logger.error(f"Replay file not found: {REPLAY_PATH}")
        sys.exit(1)

    logger.info(f"Replay: {REPLAY_PATH}")
    logger.info(f"Step size: {STEP_SIZE}")

    # Run in both modes
    results_observer = run_diagnostic("observer")
    results_player = run_diagnostic("player1")

    # Print summary
    print_summary(results_observer, results_player)

    # Save raw results
    raw_output = PROJECT_ROOT / "scripts" / "032_diagnostic_raw_results.json"
    save_results_to_file(results_observer, results_player, raw_output)

    logger.info("Diagnostic complete.")
