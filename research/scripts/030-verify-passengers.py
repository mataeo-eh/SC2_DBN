"""
030-verify-passengers.py: Verify passengers field availability in observer mode.

This script launches SC2 via pysc2, loads a replay in observer mode
(observed_player_id=0, disable_fog=True), and steps through the replay
checking whether the `passengers` repeated field on building/transport
protobufs is populated.

Research goal: Determine if UNIT_CONTAINING_BUILDINGS can be replaced with
direct passengers field reads (FN-3 from audit 029).

Dependencies:
    - pysc2 (with SC2 installed)
    - s2clientprotocol
    - absl-py (for pysc2 flags)
    - SC2-gamestate-extractor/src_new/pipeline/replay_loader.py (for SC2 launch)
    - pysc2.lib.units (for unit type name lookup)

Usage:
    .venv-3_11/Scripts/python research/scripts/030-verify-passengers.py
"""

import sys
import os
from pathlib import Path

# Ensure project root is on sys.path so we can import pipeline modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "SC2-gamestate-extractor"))

from absl import flags
# Parse absl flags before any pysc2 imports that depend on them
FLAGS = flags.FLAGS
FLAGS([''])  # Initialize with empty args

from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import raw_pb2

from src_new.pipeline.replay_loader import ReplayLoader
from pysc2.lib import units as pysc2_units


def get_unit_name(unit_type_id: int) -> str:
    """
    Look up human-readable unit type name from pysc2.lib.units.

    Args:
        unit_type_id: Integer unit type ID from the protobuf.

    Returns:
        String name like "Refinery" or "Unknown(1234)" if not found.
    """
    result = pysc2_units.get_unit_type(unit_type_id)
    if result is not None:
        return result.name
    return f"Unknown({unit_type_id})"


def main():
    """
    Main entry point: load replay, step through game loop, check passengers field.

    Steps through the replay observing all units. For any unit/building with
    cargo_space_max > 0, checks if the passengers repeated field is populated.
    Reports findings per game loop until passengers are found or replay ends.
    """
    # Find a replay file to use
    replays_dir = PROJECT_ROOT / "replays"
    replay_files = list(replays_dir.glob("*.SC2Replay"))
    if not replay_files:
        print("ERROR: No replay files found in ./replays/")
        sys.exit(1)

    replay_path = str(replay_files[0])
    print(f"Using replay: {replay_path}")
    print()

    # --- Launch SC2 and start replay ---
    loader = ReplayLoader()
    loader.load_replay(replay_path)

    with loader.start_sc2_instance() as controller:
        # Get replay info (required before start_replay)
        info = loader.get_replay_info(controller)
        print(f"Map: {info.map_name}")
        print(f"Duration: {info.game_duration_loops} loops")
        print()

        # Start replay in observer mode (same as extraction pipeline)
        loader.start_replay(controller, observer_mode=True)

        # --- Step through the replay ---
        step_size = 100  # Step 100 game loops at a time (~4.5 seconds real-time at Faster)
        max_loops = info.game_duration_loops
        game_loop = 0

        # Track findings
        passengers_found = False
        cargo_buildings_seen = set()  # Track unit types with cargo_space_max > 0
        passengers_log = []           # Log of all passenger sightings
        # Track all fields availability
        fields_checked = {
            'passengers': False,
            'cargo_space_max': False,
            'cargo_space_taken': False,
            'buff_ids': False,
            'buff_duration_remain': False,
            'buff_duration_max': False,
            'rally_targets': False,
            'assigned_harvesters': False,
            'ideal_harvesters': False,
            'engaged_target_tag': False,
            'detect_range': False,
            'radar_range': False,
            'is_powered': False,
            'is_active': False,
            'add_on_tag': False,
        }

        print("Stepping through replay, checking passengers field...")
        print("=" * 80)

        while game_loop < max_loops:
            try:
                controller.step(step_size)

                # Observe in observer mode (player perspective doesn't matter for
                # raw_data.units which contains all units from both players)
                loader.switch_player_perspective(controller, player_id=1)
                obs = controller.observe()

                if obs.player_result:
                    print(f"\nReplay ended at loop {game_loop}")
                    break

                game_loop = obs.observation.game_loop
                raw_units = obs.observation.raw_data.units

                for unit in raw_units:
                    unit_name = get_unit_name(unit.unit_type)

                    # --- Check cargo_space_max > 0 ---
                    if unit.cargo_space_max > 0:
                        cargo_key = f"{unit_name}(owner={unit.owner})"
                        if cargo_key not in cargo_buildings_seen:
                            cargo_buildings_seen.add(cargo_key)
                            print(f"  Loop {game_loop:>7}: Found cargo-capable: "
                                  f"{unit_name} (ID={unit.unit_type}, owner={unit.owner}, "
                                  f"tag={unit.tag}, cargo_max={unit.cargo_space_max}, "
                                  f"cargo_taken={unit.cargo_space_taken})")

                        # --- Check passengers ---
                        if len(unit.passengers) > 0:
                            passengers_found = True
                            fields_checked['passengers'] = True
                            passenger_details = []
                            for p in unit.passengers:
                                p_name = get_unit_name(p.unit_type)
                                passenger_details.append(
                                    f"{p_name}(tag={p.tag}, hp={p.health:.0f}/{p.health_max:.0f})"
                                )
                            log_entry = (
                                f"  Loop {game_loop:>7}: PASSENGERS FOUND in "
                                f"{unit_name} (tag={unit.tag}, owner={unit.owner}): "
                                f"{', '.join(passenger_details)}"
                            )
                            print(log_entry)
                            passengers_log.append(log_entry)

                    # --- Check other enhancement fields (EN-2 through EN-8) ---

                    # buff_ids
                    if len(unit.buff_ids) > 0 and not fields_checked['buff_ids']:
                        fields_checked['buff_ids'] = True
                        print(f"  Loop {game_loop:>7}: buff_ids populated on "
                              f"{unit_name}: {list(unit.buff_ids)}")

                    # buff_duration_remain / buff_duration_max
                    if unit.buff_duration_remain > 0 and not fields_checked['buff_duration_remain']:
                        fields_checked['buff_duration_remain'] = True
                        fields_checked['buff_duration_max'] = True
                        print(f"  Loop {game_loop:>7}: buff_duration on "
                              f"{unit_name}: remain={unit.buff_duration_remain}, "
                              f"max={unit.buff_duration_max}")

                    # rally_targets
                    if len(unit.rally_targets) > 0 and not fields_checked['rally_targets']:
                        fields_checked['rally_targets'] = True
                        rt = unit.rally_targets[0]
                        print(f"  Loop {game_loop:>7}: rally_targets populated on "
                              f"{unit_name}: point=({rt.point.x:.1f}, {rt.point.y:.1f}), "
                              f"tag={rt.tag}")

                    # assigned_harvesters / ideal_harvesters
                    if unit.assigned_harvesters > 0 and not fields_checked['assigned_harvesters']:
                        fields_checked['assigned_harvesters'] = True
                        fields_checked['ideal_harvesters'] = True
                        print(f"  Loop {game_loop:>7}: harvesters on "
                              f"{unit_name}: assigned={unit.assigned_harvesters}, "
                              f"ideal={unit.ideal_harvesters}")

                    # engaged_target_tag
                    if unit.engaged_target_tag != 0 and not fields_checked['engaged_target_tag']:
                        fields_checked['engaged_target_tag'] = True
                        print(f"  Loop {game_loop:>7}: engaged_target_tag on "
                              f"{unit_name}: {unit.engaged_target_tag}")

                    # detect_range / radar_range
                    if unit.detect_range > 0 and not fields_checked['detect_range']:
                        fields_checked['detect_range'] = True
                        print(f"  Loop {game_loop:>7}: detect_range on "
                              f"{unit_name}: {unit.detect_range}")
                    if unit.radar_range > 0 and not fields_checked['radar_range']:
                        fields_checked['radar_range'] = True
                        print(f"  Loop {game_loop:>7}: radar_range on "
                              f"{unit_name}: {unit.radar_range}")

                    # is_powered
                    if unit.is_powered and not fields_checked['is_powered']:
                        fields_checked['is_powered'] = True
                        print(f"  Loop {game_loop:>7}: is_powered=True on "
                              f"{unit_name}")

                    # is_active
                    if unit.is_active and not fields_checked['is_active']:
                        fields_checked['is_active'] = True
                        print(f"  Loop {game_loop:>7}: is_active=True on "
                              f"{unit_name}")

                    # add_on_tag
                    if unit.add_on_tag != 0 and not fields_checked['add_on_tag']:
                        fields_checked['add_on_tag'] = True
                        print(f"  Loop {game_loop:>7}: add_on_tag on "
                              f"{unit_name}: {unit.add_on_tag}")

                # Print progress every 5000 loops
                if game_loop % 5000 < step_size:
                    pct = (game_loop / max_loops) * 100
                    print(f"  --- Progress: loop {game_loop}/{max_loops} ({pct:.1f}%) ---")

            except Exception as e:
                print(f"  ERROR at loop {game_loop}: {e}")
                # Continue despite errors
                game_loop += step_size

        # --- Final report ---
        print()
        print("=" * 80)
        print("FINAL REPORT")
        print("=" * 80)

        print(f"\nCargo-capable unit types seen: {len(cargo_buildings_seen)}")
        for name in sorted(cargo_buildings_seen):
            print(f"  - {name}")

        print(f"\nTotal passenger sightings logged: {len(passengers_log)}")
        if passengers_found:
            print("\n*** PASSENGERS FIELD WORKS IN OBSERVER MODE ***")
            print("The `passengers` repeated field IS populated when using")
            print("observed_player_id=0, disable_fog=True.")
        else:
            print("\n*** PASSENGERS FIELD EMPTY IN OBSERVER MODE ***")
            print("The `passengers` repeated field was NOT populated in any")
            print("cargo-capable building/transport across the entire replay.")

        print()
        print("Enhancement field availability summary:")
        for field_name, available in sorted(fields_checked.items()):
            status = "POPULATED" if available else "NOT SEEN"
            print(f"  {field_name:<30}  {status}")

    print()
    print("Script completed successfully.")


if __name__ == "__main__":
    main()
