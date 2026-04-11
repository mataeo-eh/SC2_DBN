"""
Tokenization.py: Master entity list builder for the SC2 ML tokenization schema.

PURPOSE
-------
Derives the canonical set of SC2 entity names (units + buildings) from two
complementary sources, then writes them to two output files:

  1. Dataset scan  -- reads every parquet file in the project data directory,
                      parses column names with ENTITY_COL_RE, and collects every
                      entity type name observed in actual replay data.

  2. pysc2 enums   -- iterates pysc2.lib.units.Terran / Protoss / Zerg to catch
                      entities that exist in the game but haven't appeared in the
                      current dataset yet (e.g. rare units, late-game tech).

Entities found in EITHER source are included in both output files.  Entities
already in the JSONs that disappear from both sources are NOT removed -- both
files are append-only so token IDs remain stable across dataset updates.

UPDATING THE LIST
-----------------
Re-run this file directly whenever:
  - New parquet files have been added to the dataset.
  - pysc2 has been updated with renamed or new unit entries.

  python ML_PoC/Tokenization.py [--data-dir path/to/data]

The script merges new findings without disturbing existing entries, then prints
a summary of what was added.

OUTPUT SCHEMA (Entity_List.json)
---------------------------------
Human-readable entity list organised by category and race.  Useful as a
reference and for downstream code that needs race-aware lookups.

{
  "metadata": {
    "generated_at":        "<ISO timestamp of last update>",
    "parquet_files_scanned": <int>,
    "total_entities":        <int>
  },
  "buildings": {
    "terran":  [...sorted list of terran building names...],
    "protoss": [...],
    "zerg":    [...],
    "unclassified": [...]   // in data/pysc2 but not mappable to a race
  },
  "units": {
    "terran":  [...sorted list of terran unit names...],
    "protoss": [...],
    "zerg":    [...],
    "unclassified": [...]
  }
}

OUTPUT SCHEMA (Token_Dictionary.json)
--------------------------------------
Flat vocabulary mapping game-engine unit-type IDs (integers, used directly as
token IDs by the ML model) to their canonical string names.

The game engine already defines this mapping -- pysc2 enum members carry the
game engine ID as their .value.  This file is simply the reverse: ID -> name.

For unit-type IDs that pysc2 does not recognise (observed in replay data but
absent from all enums), the string name is "unknown_<ID>" so the token is still
uniquely identifiable without requiring human-readable context.

{
  "metadata": {
    "generated_at":        "<ISO timestamp of last update>",
    "total_tokens":          <int>
  },
  "tokens": {
    "<game_engine_id>": "<string_name>",   // e.g. "48": "marine"
    ...
    "1943": "unknown_1943",                // IDs not in pysc2 enums
    "1995": "unknown_1995"
  }
}

All string names are lowercase.

Dependencies:
  - pyarrow       (reads parquet column schemas without loading row data)
  - pysc2.lib.units
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
from pysc2.lib import units as sc2_units


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Project root is two levels up from ML_PoC/Tokenization.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default directory to search for parquet files (all subdirs under data/)
_DEFAULT_DATA_DIR = _PROJECT_ROOT / "data"

# Output JSONs live alongside this file
ENTITY_LIST_PATH   = Path(__file__).resolve().parent / "Entity_List.json"
TOKEN_DICT_PATH    = Path(__file__).resolve().parent / "Token_Dictionary.json"

# Pattern that matches unknown entity names produced by the extractor when it
# encounters a game-engine unit-type ID not present in the pysc2 enums.
# Example: "unknown(1943)" -> captured group = "1943"
_UNKNOWN_NAME_RE = re.compile(r"^unknown\((\d+)\)$")

# Column name regex -- matches {player}_{botname}_{entitytype}_{seq_id}_{attr}
# Group 2 is the combined botname+entitytype "middle"; entity type is the last
# underscore-delimited segment: middle.rsplit('_', 1)[-1]
_ENTITY_COL_RE = re.compile(r"^(p[12])_(.+)_(\d{3})_(.+)$")


# ---------------------------------------------------------------------------
# BUILDING_TYPES
# ---------------------------------------------------------------------------
# Authoritative frozenset of all SC2 building names across all three races.
# Copied from SC2-gamestate-extractor/src_new/shared_constants.py.
#
# Role here: used as the building/unit classifier. Any entity name in this set
# is a building; everything else is treated as a unit.
#
# Building ID cross-reference notes (from original shared_constants.py):
#   ID 133 --> WarpGate (Protoss)      [NOT TechLab; TechLab = ID 5]
#   ID 138 --> CreepTumorQueen (Zerg)  [NOT FactoryReactor; FactoryReactor = ID 40]
#   ID 142 --> NydusCanal (Zerg)       [NOT StarportReactor (ID 42)]

BUILDING_TYPES: frozenset = frozenset({

    # -----------------------------------------------------------------------
    # TERRAN BUILDINGS
    # -----------------------------------------------------------------------
    "commandcenter",          # ID 18
    "orbitalcommand",         # ID 132
    "planetaryfortress",      # ID 130
    "commandcenterflying",    # ID 36
    "orbitalcommandflying",   # ID 134
    "barracksflying",         # ID 46
    "factoryflying",          # ID 43
    "starportflying",         # ID 44
    "supplydepot",            # ID 19
    "supplydepotlowered",     # ID 47
    "refinery",               # ID 20
    "refineryrich",           # ID 1960
    "barracks",               # ID 21
    "factory",                # ID 27
    "starport",               # ID 28
    "engineeringbay",         # ID 22
    "missileturret",          # ID 23
    "bunker",                 # ID 24
    "sensortower",            # ID 25
    "ghostacademy",           # ID 26
    "armory",                 # ID 29
    "fusioncore",             # ID 30
    "techlab",                # ID 5
    "reactor",                # ID 6
    "barrackstechlab",        # ID 37
    "barracksreactor",        # ID 38
    "factorytechlab",         # ID 39
    "factoryreactor",         # ID 40
    "starporttechlab",        # ID 41
    "starportreactor",        # ID 42

    # -----------------------------------------------------------------------
    # PROTOSS BUILDINGS
    # -----------------------------------------------------------------------
    "nexus",                  # ID 59
    "pylon",                  # ID 60
    "assimilator",            # ID 61
    "assimilatorrich",        # ID 1955
    "gateway",                # ID 62
    "warpgate",               # ID 133
    "forge",                  # ID 63
    "fleetbeacon",            # ID 64
    "twilightcouncil",        # ID 65
    "photoncannon",           # ID 66
    "shieldbattery",          # ID 1910
    "stargate",               # ID 67
    "templararchive",         # ID 68
    "darkshrine",             # ID 69
    "roboticsbay",            # ID 70
    "roboticsfacility",       # ID 71
    "cyberneticscore",        # ID 72

    # -----------------------------------------------------------------------
    # ZERG BUILDINGS
    # -----------------------------------------------------------------------
    "hatchery",               # ID 86
    "lair",                   # ID 100
    "hive",                   # ID 101
    "extractor",              # ID 88
    "extractorrich",          # ID 1956
    "spawningpool",           # ID 89
    "evolutionchamber",       # ID 90
    "hydraliskden",           # ID 91
    "spire",                  # ID 92
    "greaterspire",           # ID 102
    "ultraliskcavern",        # ID 93
    "infestationpit",         # ID 94
    "banelingnest",           # ID 96
    "roachwarren",            # ID 97
    "lurkerden",              # ID 504
    "nydusnetwork",           # ID 95
    "nyduscanal",             # ID 142
    "spinecrawler",           # ID 98
    "spinecrawleruprooted",   # ID 139
    "sporecrawler",           # ID 99
    "sporecrawleruprooted",   # ID 140
    "creeptumor",             # ID 87
    "creeptumorburrowed",     # ID 137
    "creeptumorqueen",        # ID 138

})


# ---------------------------------------------------------------------------
# Race lookup tables (built once from pysc2 enums)
# ---------------------------------------------------------------------------
# Maps lowercase unit/building name -> race string.
# Used to classify entities found in the dataset by race.

def _build_race_map() -> dict[str, str]:
    """
    Build a name -> race mapping from pysc2 enums.

    Iterates Terran, Protoss, and Zerg enums and lowercases each member name.
    If a name appears in multiple races (shouldn't happen in SC2 but defensive),
    the last race wins -- this is intentional since the mapping is used purely
    for classification and collisions are not expected.

    Returns:
        dict[str, str]: {lowercase_name: "terran" | "protoss" | "zerg"}

    Called by: module-level _RACE_MAP constant.
    """
    race_map = {}
    for enum, race_label in (
        (sc2_units.Terran,  "terran"),
        (sc2_units.Protoss, "protoss"),
        (sc2_units.Zerg,    "zerg"),
    ):
        for member in enum:
            race_map[member.name.lower()] = race_label
    return race_map


_RACE_MAP: dict[str, str] = _build_race_map()


# ---------------------------------------------------------------------------
# Dataset scan
# ---------------------------------------------------------------------------

def scan_parquet_entities(data_dir: Path) -> tuple[set[str], int]:
    """
    Scan all parquet files under data_dir for entity type names.

    Reads only the column schema of each file (no row data loaded) for speed.
    Applies ENTITY_COL_RE to each column name and extracts entity type from
    the "middle" group via middle.rsplit('_', 1)[-1].

    Args:
        data_dir: Root directory to search recursively for *.parquet files.

    Returns:
        (entity_names, file_count): set of lowercase entity name strings found
        in the dataset, and the number of parquet files scanned.

    Called by: build_entity_list(), update_entity_list()
    """
    entity_names: set[str] = set()
    parquet_files = list(data_dir.rglob("*.parquet"))

    for path in parquet_files:
        try:
            schema = pq.read_schema(path)
        except Exception as exc:
            print(f"  [WARN] Could not read schema of {path.name}: {exc}", file=sys.stderr)
            continue

        for col in schema.names:
            match = _ENTITY_COL_RE.match(col)
            if match:
                middle = match.group(2)
                entity_names.add(middle.rsplit("_", 1)[-1])

    return entity_names, len(parquet_files)


# ---------------------------------------------------------------------------
# pysc2 entity scan
# ---------------------------------------------------------------------------

def scan_pysc2_entities() -> set[str]:
    """
    Collect all entity names from pysc2 Terran, Protoss, and Zerg enums.

    Returns:
        set[str]: Lowercase member names from all three race enums.

    Called by: build_entity_list(), update_entity_list()
    """
    names: set[str] = set()
    for enum in (sc2_units.Terran, sc2_units.Protoss, sc2_units.Zerg):
        for member in enum:
            names.add(member.name.lower())
    return names


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _classify(name: str) -> tuple[str, str]:
    """
    Classify an entity name into (category, race).

    Args:
        name: Lowercase entity name string.

    Returns:
        (category, race):
          category -- "buildings" if name is in BUILDING_TYPES, else "units"
          race     -- "terran", "protoss", "zerg", or "unclassified"

    Called by: build_entity_list(), update_entity_list()
    """
    category = "buildings" if name in BUILDING_TYPES else "units"
    race = _RACE_MAP.get(name, "unclassified")
    return category, race


# ---------------------------------------------------------------------------
# JSON read / write
# ---------------------------------------------------------------------------

def _empty_entity_list() -> dict:
    """Return the skeleton structure for a new Entity_List.json."""
    return {
        "metadata": {
            "generated_at": "",
            "parquet_files_scanned": 0,
            "total_entities": 0,
        },
        "buildings": {"terran": [], "protoss": [], "zerg": [], "unclassified": []},
        "units":     {"terran": [], "protoss": [], "zerg": [], "unclassified": []},
    }


def load_entity_list() -> dict:
    """
    Load Entity_List.json from disk.

    Returns:
        dict: Parsed JSON structure.  Returns a fresh empty structure if the
        file does not yet exist.

    Called by: update_entity_list(), and by external consumers that need the
    entity lists as Python data structures.
    """
    if ENTITY_LIST_PATH.exists():
        with open(ENTITY_LIST_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return _empty_entity_list()


def _save_entity_list(data: dict) -> None:
    """
    Write entity list dict to Entity_List.json (pretty-printed, sorted keys).

    Args:
        data: The entity list dict to serialise.

    Called by: build_entity_list(), update_entity_list()
    """
    with open(ENTITY_LIST_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=False, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Token dictionary helpers
# ---------------------------------------------------------------------------

def _build_pysc2_id_to_name() -> dict[int, str]:
    """
    Build a game-engine-ID -> lowercase-string-name mapping from pysc2 enums.

    Each pysc2 enum member stores:
      member.name  -- the human-readable string the engine uses (e.g. "Marine")
      member.value -- the integer unit-type ID the game engine uses internally

    Reversing that gives us the token vocabulary: ID -> name.

    If two enum members share the same value (aliases exist in pysc2 for a few
    units), the last one wins -- this is acceptable because the string names
    for aliases are equivalent for tokenisation purposes.

    Returns:
        dict[int, str]: {game_engine_id: lowercase_name}

    Called by: build_token_dictionary()
    """
    id_to_name: dict[int, str] = {}
    for enum in (sc2_units.Terran, sc2_units.Protoss, sc2_units.Zerg):
        for member in enum:
            id_to_name[member.value] = member.name.lower()
    return id_to_name


def load_token_dictionary() -> dict:
    """
    Load Token_Dictionary.json from disk.

    Returns:
        dict: Parsed JSON structure.  Returns a fresh empty structure if the
        file does not yet exist.

    Called by: build_token_dictionary(), and by external consumers that need
    the flat token vocabulary.
    """
    if TOKEN_DICT_PATH.exists():
        with open(TOKEN_DICT_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"metadata": {"generated_at": "", "total_tokens": 0}, "tokens": {}}


def _save_token_dictionary(data: dict) -> None:
    """
    Write token dictionary dict to Token_Dictionary.json (pretty-printed).

    Tokens are sorted numerically by game-engine ID so the file is stable and
    easy to inspect.

    Args:
        data: The token dictionary dict to serialise.

    Called by: build_token_dictionary()
    """
    # Sort tokens numerically by game-engine ID before writing
    data["tokens"] = {
        str(k): data["tokens"][str(k)]
        for k in sorted(int(k) for k in data["tokens"])
    }
    with open(TOKEN_DICT_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=False, ensure_ascii=False)


def build_token_dictionary(dataset_entity_names: set[str]) -> dict:
    """
    Build or update Token_Dictionary.json from pysc2 enums plus any unknowns
    observed in the dataset.

    The game engine defines unit-type IDs internally; pysc2 enums expose these
    as member.value.  This function reverses that mapping (ID -> name) and
    extends it with any unknown IDs seen in replay data that pysc2 does not
    cover.

    Steps:
      1. Reverse pysc2 enums -> {game_engine_id: lowercase_name}.
      2. Scan dataset_entity_names for "unknown(XXXX)" entries and add
         {XXXX: "unknown_XXXX"} for each one.
      3. Merge with existing Token_Dictionary.json (append-only: existing
         entries are never removed so token IDs stay stable).
      4. Write updated JSON to disk.

    Args:
        dataset_entity_names: Set of entity name strings found in the dataset
            (output of scan_parquet_entities).  Expected to contain any
            "unknown(XXXX)" strings produced by the extractor for unrecognised
            unit-type IDs.

    Returns:
        dict: The updated token dictionary structure (also written to disk).

    Called by: build_entity_list() (so both files are always updated together),
    and can be called standalone if only the token dictionary needs refreshing.
    """
    # Step 1: reverse pysc2 enums
    pysc2_map = _build_pysc2_id_to_name()

    # Step 2: parse unknowns from the dataset scan
    unknown_map: dict[int, str] = {}
    for name in dataset_entity_names:
        m = _UNKNOWN_NAME_RE.match(name)
        if m:
            uid = int(m.group(1))
            unknown_map[uid] = f"unknown_{uid}"

    # Step 3: merge into existing dictionary (append-only)
    existing = load_token_dictionary()
    tokens: dict[str, str] = existing["tokens"]

    added: list[tuple[int, str]] = []

    for uid, name in pysc2_map.items():
        key = str(uid)
        if key not in tokens:
            tokens[key] = name
            added.append((uid, name))

    for uid, name in unknown_map.items():
        key = str(uid)
        if key not in tokens:
            tokens[key] = name
            added.append((uid, name))

    # Step 4: update metadata and write
    existing["metadata"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    existing["metadata"]["total_tokens"]  = len(tokens)
    existing["tokens"] = tokens

    _save_token_dictionary(existing)

    if added:
        print(f"\n  Added {len(added)} new tokens to Token_Dictionary.json:")
        for uid, name in sorted(added):
            print(f"    + {uid}: \"{name}\"")
    else:
        print("\n  No new tokens found -- Token_Dictionary.json is already up to date.")

    print(f"\nToken_Dictionary.json written to: {TOKEN_DICT_PATH}")
    return existing


# ---------------------------------------------------------------------------
# Core build / update logic
# ---------------------------------------------------------------------------

def build_entity_list(data_dir: Path = _DEFAULT_DATA_DIR) -> dict:
    """
    Derive the full entity list from the dataset and pysc2 enums, then write
    Entity_List.json.

    If Entity_List.json already exists this function merges new findings into
    it without removing any existing entries (append-only to keep token IDs
    stable).  Call this function directly when you want a fresh or updated list.

    Steps:
      1. Scan all parquet files under data_dir for observed entity names.
      2. Scan pysc2 enums for all known entity names.
      3. Union both sets.
      4. Classify each name by category (building/unit) and race.
      5. Merge into existing Entity_List.json (or create fresh if absent).
      6. Write updated JSON to disk.

    Args:
        data_dir: Root directory to search for *.parquet files.
                  Defaults to <project_root>/data.

    Returns:
        dict: The updated entity list structure (also written to disk).

    Called by: __main__ block, and can be called programmatically by other
    ML pipeline scripts to ensure the list is current before consuming it.
    """
    print(f"Scanning dataset: {data_dir}")
    dataset_names, file_count = scan_parquet_entities(data_dir)
    print(f"  {file_count} parquet files scanned, {len(dataset_names)} entity types observed in data")

    pysc2_names = scan_pysc2_entities()
    print(f"  {len(pysc2_names)} entity types known to pysc2 enums")

    all_names = dataset_names | pysc2_names
    print(f"  {len(all_names)} total unique entity names (union)")

    # Load existing JSON to preserve any entries already there
    existing = load_entity_list()

    # Collect existing names per bucket to detect what's new
    existing_names: set[str] = set()
    for cat in ("buildings", "units"):
        for race_list in existing[cat].values():
            existing_names.update(race_list)

    # Insert new entities into the correct bucket
    added: list[str] = []
    for name in all_names:
        if name in existing_names:
            continue
        category, race = _classify(name)
        existing[category][race].append(name)
        added.append(name)

    # Sort each bucket for readability / stable diffs
    for cat in ("buildings", "units"):
        for race in existing[cat]:
            existing[cat][race].sort()

    # Update metadata
    total = sum(
        len(lst)
        for cat in ("buildings", "units")
        for lst in existing[cat].values()
    )
    existing["metadata"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    existing["metadata"]["parquet_files_scanned"] = file_count
    existing["metadata"]["total_entities"] = total

    _save_entity_list(existing)

    if added:
        print(f"\n  Added {len(added)} new entities:")
        for name in sorted(added):
            category, race = _classify(name)
            print(f"    + {name}  ({category} / {race})")
    else:
        print("\n  No new entities found -- Entity_List.json is already up to date.")

    print(f"\nEntity_List.json written to: {ENTITY_LIST_PATH}")

    # Also keep Token_Dictionary.json in sync -- pass the raw dataset names so
    # that any unknown(XXXX) entries can be harvested for the token vocab.
    print("\n--- Token Dictionary ---")
    build_token_dictionary(dataset_names)

    return existing


# ---------------------------------------------------------------------------
# Convenience accessors (for use by other ML pipeline modules)
# ---------------------------------------------------------------------------

def get_master_unit_frozenset() -> frozenset:
    """
    Load Entity_List.json and return all unit names as a single frozenset.

    Returns:
        frozenset[str]: Every unit name across all races.

    Called by: downstream ML pipeline modules that need a flat unit vocabulary.
    """
    data = load_entity_list()
    names: set[str] = set()
    for race_list in data["units"].values():
        names.update(race_list)
    return frozenset(names)


def get_master_building_frozenset() -> frozenset:
    """
    Load Entity_List.json and return all building names as a single frozenset.

    Returns:
        frozenset[str]: Every building name across all races.

    Called by: downstream ML pipeline modules that need a flat building vocabulary.
    """
    data = load_entity_list()
    names: set[str] = set()
    for race_list in data["buildings"].values():
        names.update(race_list)
    return frozenset(names)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build or update Entity_List.json from the SC2 dataset and pysc2 enums."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=_DEFAULT_DATA_DIR,
        help=f"Root directory to search for *.parquet files (default: {_DEFAULT_DATA_DIR})",
    )
    args = parser.parse_args()

    result = build_entity_list(data_dir=args.data_dir)
    token_dict = load_token_dictionary()

    print("\n--- Summary ---")
    print(f"  Buildings  terran       : {len(result['buildings']['terran'])}")
    print(f"  Buildings  protoss      : {len(result['buildings']['protoss'])}")
    print(f"  Buildings  zerg         : {len(result['buildings']['zerg'])}")
    print(f"  Buildings  unclassified : {len(result['buildings']['unclassified'])}")
    print(f"  Units      terran       : {len(result['units']['terran'])}")
    print(f"  Units      protoss      : {len(result['units']['protoss'])}")
    print(f"  Units      zerg         : {len(result['units']['zerg'])}")
    print(f"  Units      unclassified : {len(result['units']['unclassified'])}")
    print(f"  Total entities          : {result['metadata']['total_entities']}")
    print(f"  Token vocab size        : {token_dict['metadata']['total_tokens']}")
