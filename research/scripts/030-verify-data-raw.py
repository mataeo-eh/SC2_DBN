"""
030-verify-data-raw.py: Verify data_raw() availability and Attribute.Structure classification.

This script launches SC2 via pysc2, loads a replay, calls controller.data_raw()
AFTER start_replay(), and inspects the UnitTypeData entries for all unit types.
It checks which unit types have Attribute.Structure and compares against the
hardcoded BUILDING_TYPES frozenset in shared_constants.py.

Research goal: Confirm that BUILDING_TYPES can be replaced with an API-derived
set built from Attribute.Structure at runtime.

Dependencies:
    - pysc2 (with SC2 installed)
    - s2clientprotocol
    - absl-py (for pysc2 flags)
    - SC2-gamestate-extractor/src_new/shared_constants.py (for BUILDING_TYPES)
    - SC2-gamestate-extractor/src_new/pipeline/replay_loader.py (for SC2 launch)

Usage:
    .venv-3_11/Scripts/python research/scripts/030-verify-data-raw.py
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
from s2clientprotocol import data_pb2

from src_new.pipeline.replay_loader import ReplayLoader
from src_new.shared_constants import BUILDING_TYPES

# --- Attribute enum name mapping ---
# Maps integer attribute values to human-readable names from data_pb2
ATTRIBUTE_NAMES = {
    1: "Light",
    2: "Armored",
    3: "Biological",
    4: "Mechanical",
    5: "Robotic",
    6: "Psionic",
    7: "Massive",
    8: "Structure",
    9: "Hover",
    10: "Heroic",
    11: "Summoned",
}


def main():
    """
    Main entry point: load replay, call data_raw(), inspect UnitTypeData attributes.

    Prints all unit types with their attributes, then compares Structure-attributed
    types against the hardcoded BUILDING_TYPES set.
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

        # --- Call data_raw() AFTER start_replay() ---
        print("Calling controller.data_raw()...")
        data = controller.data_raw()

        # data is a ResponseData protobuf message
        # data.units is a repeated UnitTypeData
        unit_types = data.units
        print(f"Total UnitTypeData entries: {len(unit_types)}")
        print()

        # --- Collect all attribute values found across all unit types ---
        all_attributes_found = set()
        # Track which unit types have Attribute.Structure
        structure_types_by_id = {}   # unit_id -> name
        structure_types_by_name = set()  # lowercase names

        print("=" * 80)
        print("ALL UNIT TYPES WITH ATTRIBUTES")
        print("=" * 80)
        print(f"{'ID':>6}  {'Name':<40}  {'Attributes'}")
        print("-" * 80)

        for unit_type in unit_types:
            uid = unit_type.unit_id
            name = unit_type.name
            attrs = list(unit_type.attributes)
            attr_names = [ATTRIBUTE_NAMES.get(a, f"Unknown({a})") for a in attrs]

            # Track all attribute values encountered
            for a in attrs:
                all_attributes_found.add(a)

            has_structure = data_pb2.Structure in attrs
            marker = " [STRUCTURE]" if has_structure else ""

            if has_structure:
                structure_types_by_id[uid] = name
                structure_types_by_name.add(name.lower())

            # Only print entries that have at least one attribute (skip empty/placeholder entries)
            if attrs:
                print(f"{uid:>6}  {name:<40}  {', '.join(attr_names)}{marker}")

        print()
        print("=" * 80)
        print("ATTRIBUTE ENUM VALUES FOUND")
        print("=" * 80)
        for attr_val in sorted(all_attributes_found):
            print(f"  {attr_val:>3} = {ATTRIBUTE_NAMES.get(attr_val, f'UNKNOWN({attr_val})')}")
        print(f"\nTotal unique attribute values: {len(all_attributes_found)}")

        print()
        print("=" * 80)
        print("STRUCTURE-ATTRIBUTED TYPES (from data_raw)")
        print("=" * 80)
        for uid, name in sorted(structure_types_by_id.items(), key=lambda x: x[1]):
            print(f"  {uid:>6}  {name}")
        print(f"\nTotal Structure types from API: {len(structure_types_by_id)}")

        print()
        print("=" * 80)
        print("COMPARISON: API Structure types vs. hardcoded BUILDING_TYPES")
        print("=" * 80)
        print(f"Hardcoded BUILDING_TYPES count: {len(BUILDING_TYPES)}")
        print(f"API Structure types count:      {len(structure_types_by_name)}")

        # Types in API but NOT in hardcoded set
        api_only = structure_types_by_name - BUILDING_TYPES
        if api_only:
            print(f"\nIn API (Structure) but NOT in hardcoded BUILDING_TYPES ({len(api_only)}):")
            for name in sorted(api_only):
                # Find the ID for this name
                uid = [k for k, v in structure_types_by_id.items() if v.lower() == name]
                uid_str = str(uid[0]) if uid else "?"
                print(f"  - {name} (ID {uid_str})")
        else:
            print("\nNo types in API that are missing from hardcoded set.")

        # Types in hardcoded set but NOT in API
        hardcoded_only = BUILDING_TYPES - structure_types_by_name
        if hardcoded_only:
            print(f"\nIn hardcoded BUILDING_TYPES but NOT in API Structure ({len(hardcoded_only)}):")
            for name in sorted(hardcoded_only):
                print(f"  - {name}")
        else:
            print("\nNo types in hardcoded set that are missing from API.")

        # Exact match?
        if api_only or hardcoded_only:
            print("\nVERDICT: Sets DO NOT match exactly. Review discrepancies above.")
        else:
            print("\nVERDICT: Sets match EXACTLY. BUILDING_TYPES can be replaced with API-derived set.")

        print()
        print("=" * 80)
        print("FULL UNIT TYPE DUMP (all entries, including those with no attributes)")
        print("=" * 80)
        # Print a compact dump of ALL entries for reference
        entries_with_attrs = 0
        entries_without_attrs = 0
        for unit_type in unit_types:
            uid = unit_type.unit_id
            name = unit_type.name
            attrs = list(unit_type.attributes)
            if attrs:
                entries_with_attrs += 1
            else:
                entries_without_attrs += 1

        print(f"Entries with attributes:    {entries_with_attrs}")
        print(f"Entries without attributes: {entries_without_attrs}")
        print(f"Total entries:             {len(unit_types)}")

    print()
    print("Script completed successfully.")


if __name__ == "__main__":
    main()
