"""
Feature Engineering & Discretization Script for SC2 Replay Data

Reads raw game state parquet files from data/quickstart/parquet/
and produces engineered feature parquet files in data/engineered/

Phase 1: Scaffold + Spatial Data Profiling
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from collections import defaultdict


# ---------------------------------------------------------------------------
# Column Parsing
# ---------------------------------------------------------------------------

# Entity column pattern: p{player}_p{player}_{type}_{id}_{attribute}
ENTITY_COL_RE = re.compile(r"^(p[12])_p[12]_(.+?)_(\d+)_(.+)$")

# Base structure types (used to find starting positions)
BASE_TYPES = {"commandcenter", "nexus", "hatchery", "lair", "hive",
              "commandcenterflying", "orbitalcommand", "planetaryfortress"}

# Worker types per race (fallback for base position detection)
WORKER_TYPES = {"scv", "probe", "drone"}

# Minimum rows for a game to be considered valid (skip degenerate replays)
MIN_GAME_ROWS = 20

# Known building types (structures that don't move)
BUILDING_TYPES = {
    # Terran
    "commandcenter", "commandcenterflying", "orbitalcommand", "planetaryfortress",
    "supplydepot", "supplydepotlowered", "barracks", "barrackstechlab",
    "barracksreactor", "factory", "factorytechlab", "factoryreactor",
    "starport", "starporttechlab", "starportreactor", "engineeringbay",
    "armory", "ghostacademy", "fusioncore", "bunker", "missileturret",
    "sensortower", "refinery",
    # Protoss
    "nexus", "pylon", "gateway", "forge", "cyberneticscore",
    "assimilator", "twilightcouncil", "templararchive", "darkshrine",
    "roboticsfacility", "roboticsbay", "stargate", "fleetbeacon",
    "photoncannon", "shieldbattery",
    # Zerg
    "hatchery", "lair", "hive", "spawningpool", "evolutionchamber",
    "extractor", "roachwarren", "banelingnest", "hydraliskden",
    "lurkerden", "infestationpit", "spire", "greaterspire",
    "ultraliskcavern", "nydusnetwork", "nyduscanal",
    "spinecrawler", "sporecrawler",
}


def parse_entity_column(col_name):
    """Parse a column name into its components.

    Returns dict with keys: player, entity_type, entity_id, attribute
    or None if not an entity column.
    """
    m = ENTITY_COL_RE.match(col_name)
    if m:
        return {
            "player": m.group(1),
            "entity_type": m.group(2),
            "entity_id": m.group(3),
            "attribute": m.group(4),
        }
    return None


def categorize_columns(columns):
    """Categorize all columns in a dataframe.

    Returns dict with:
        entities: {(player, type, id): set of attributes}
        economy: list of economy column names
        upgrades: list of upgrade column names
        meta: list of non-player columns (game_loop, timestamp_seconds)
    """
    entities = defaultdict(set)
    economy = []
    upgrades = []
    meta = []

    for col in columns:
        parsed = parse_entity_column(col)
        if parsed:
            key = (parsed["player"], parsed["entity_type"], parsed["entity_id"])
            entities[key].add(parsed["attribute"])
        elif col.startswith("p1_") or col.startswith("p2_"):
            if "upgrade" in col:
                upgrades.append(col)
            else:
                economy.append(col)
        else:
            meta.append(col)

    return {
        "entities": dict(entities),
        "economy": sorted(economy),
        "upgrades": sorted(upgrades),
        "meta": sorted(meta),
    }


# ---------------------------------------------------------------------------
# Spatial Helpers
# ---------------------------------------------------------------------------

def find_base_positions(df, columns_info):
    """Find starting base position for each player.

    Strategy:
    1. Look for the first base building (commandcenter/nexus/hatchery, id=001)
    2. Fallback: use worker_001 position (scv/probe/drone) at earliest non-NaN row
    """
    bases = {}

    # Pass 1: base buildings
    for (player, etype, eid), attrs in columns_info["entities"].items():
        if etype in BASE_TYPES and eid == "001" and "x" in attrs and "y" in attrs:
            x_col = f"{player}_{player}_{etype}_{eid}_x"
            y_col = f"{player}_{player}_{etype}_{eid}_y"
            x_vals = df[x_col].dropna()
            y_vals = df[y_col].dropna()
            if len(x_vals) > 0 and len(y_vals) > 0:
                bases[player] = {
                    "type": etype,
                    "x": x_vals.iloc[0],
                    "y": y_vals.iloc[0],
                    "source": "building",
                }

    # Pass 2: fallback to worker_001 for any player still missing
    for player in ["p1", "p2"]:
        if player in bases:
            continue
        for (p, etype, eid), attrs in columns_info["entities"].items():
            if p == player and etype in WORKER_TYPES and eid == "001" and "x" in attrs and "y" in attrs:
                x_col = f"{player}_{player}_{etype}_{eid}_x"
                y_col = f"{player}_{player}_{etype}_{eid}_y"
                x_vals = df[x_col].dropna()
                y_vals = df[y_col].dropna()
                if len(x_vals) > 0 and len(y_vals) > 0:
                    bases[player] = {
                        "type": etype,
                        "x": x_vals.iloc[0],
                        "y": y_vals.iloc[0],
                        "source": "worker_fallback",
                    }
                    break

    return bases


def compute_bounding_box(df, columns):
    """Compute bounding box from all position columns + 10 padding.

    Returns dict: {min_x, max_x, min_y, max_y, width, height}
    """
    x_cols = [c for c in columns if c.endswith("_x")]
    y_cols = [c for c in columns if c.endswith("_y")]

    if not x_cols or not y_cols:
        return None

    all_x = df[x_cols].values.flatten()
    all_y = df[y_cols].values.flatten()
    all_x = all_x[~np.isnan(all_x)]
    all_y = all_y[~np.isnan(all_y)]

    if len(all_x) == 0 or len(all_y) == 0:
        return None

    min_x, max_x = float(all_x.min()), float(all_x.max())
    min_y, max_y = float(all_y.min()), float(all_y.max())

    # Add 10 padding per user spec
    min_x -= 10
    min_y -= 10
    max_x += 10
    max_y += 10

    return {
        "min_x": min_x, "max_x": max_x,
        "min_y": min_y, "max_y": max_y,
        "width": max_x - min_x,
        "height": max_y - min_y,
    }


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------

def profile_game(filepath):
    """Profile a single game's spatial and entity data.

    Returns a dict with all profiling info for this game.
    """
    df = pd.read_parquet(filepath)
    cols = list(df.columns)
    col_info = categorize_columns(cols)

    # Base positions
    bases = find_base_positions(df, col_info)

    # Bounding box
    bbox = compute_bounding_box(df, cols)

    # Entity type inventory
    entity_types_by_player = defaultdict(set)
    building_types_by_player = defaultdict(set)
    unit_types_by_player = defaultdict(set)
    entity_counts_by_player = defaultdict(lambda: defaultdict(int))

    for (player, etype, eid), attrs in col_info["entities"].items():
        entity_types_by_player[player].add(etype)
        entity_counts_by_player[player][etype] += 1
        if etype in BUILDING_TYPES:
            building_types_by_player[player].add(etype)
        else:
            unit_types_by_player[player].add(etype)

    # Position data quality: what fraction of position columns are non-NaN
    x_cols = [c for c in cols if c.endswith("_x")]
    if x_cols:
        non_nan_frac = df[x_cols].notna().mean().mean()
    else:
        non_nan_frac = 0.0

    # Game duration
    game_loops = int(df["game_loop"].max()) if "game_loop" in df.columns else 0
    duration_s = float(df["timestamp_seconds"].max()) if "timestamp_seconds" in df.columns else 0.0

    # Base-to-base distance
    base_distance = None
    if "p1" in bases and "p2" in bases:
        dx = bases["p1"]["x"] - bases["p2"]["x"]
        dy = bases["p1"]["y"] - bases["p2"]["y"]
        base_distance = float(np.sqrt(dx**2 + dy**2))

    return {
        "file": filepath.name,
        "rows": len(df),
        "columns": len(cols),
        "game_loops": game_loops,
        "duration_seconds": duration_s,
        "duration_minutes": duration_s / 60.0,
        "bases": bases,
        "base_distance": base_distance,
        "bounding_box": bbox,
        "entity_types_p1": sorted(entity_types_by_player.get("p1", set())),
        "entity_types_p2": sorted(entity_types_by_player.get("p2", set())),
        "building_types_p1": sorted(building_types_by_player.get("p1", set())),
        "building_types_p2": sorted(building_types_by_player.get("p2", set())),
        "unit_types_p1": sorted(unit_types_by_player.get("p1", set())),
        "unit_types_p2": sorted(unit_types_by_player.get("p2", set())),
        "entity_counts_p1": dict(entity_counts_by_player.get("p1", {})),
        "entity_counts_p2": dict(entity_counts_by_player.get("p2", {})),
        "position_non_nan_frac": non_nan_frac,
        "economy_cols": col_info["economy"],
        "upgrade_cols": col_info["upgrades"],
    }


def print_profile_report(profiles):
    """Print a concise spatial profile report across all games."""
    n = len(profiles)
    print("=" * 70)
    print(f"SPATIAL DATA PROFILE  ({n} games)")
    print("=" * 70)
    print()

    # --- Game summaries ---
    durations = [p["duration_minutes"] for p in profiles]
    rows = [p["rows"] for p in profiles]
    cols = [p["columns"] for p in profiles]
    print("GAME STATISTICS")
    print(f"  Games:    {n}")
    print(f"  Duration: {min(durations):.1f} - {max(durations):.1f} min  (mean {np.mean(durations):.1f})")
    print(f"  Rows:     {min(rows)} - {max(rows)}  (mean {int(np.mean(rows))})")
    print(f"  Columns:  {min(cols)} - {max(cols)}  (mean {int(np.mean(cols))})")
    print()

    # --- Bounding boxes ---
    print("BOUNDING BOXES (coordinate ranges + 10 padding)")
    bboxes = [p["bounding_box"] for p in profiles if p["bounding_box"]]
    if bboxes:
        widths = [b["width"] for b in bboxes]
        heights = [b["height"] for b in bboxes]
        min_xs = [b["min_x"] for b in bboxes]
        max_xs = [b["max_x"] for b in bboxes]
        min_ys = [b["min_y"] for b in bboxes]
        max_ys = [b["max_y"] for b in bboxes]
        print(f"  X range:  [{min(min_xs):.1f}, {max(max_xs):.1f}]")
        print(f"  Y range:  [{min(min_ys):.1f}, {max(max_ys):.1f}]")
        print(f"  Width:    {min(widths):.1f} - {max(widths):.1f}  (mean {np.mean(widths):.1f})")
        print(f"  Height:   {min(heights):.1f} - {max(heights):.1f}  (mean {np.mean(heights):.1f})")
    print()

    # --- Base positions ---
    print("BASE POSITIONS")
    p1_found = sum(1 for p in profiles if "p1" in p["bases"])
    p2_found = sum(1 for p in profiles if "p2" in p["bases"])
    both_found = sum(1 for p in profiles if "p1" in p["bases"] and "p2" in p["bases"])
    print(f"  P1 base found: {p1_found}/{n}")
    print(f"  P2 base found: {p2_found}/{n}")
    print(f"  Both found:    {both_found}/{n}")

    # Show base type breakdown and detection source
    base_type_counts = defaultdict(int)
    base_source_counts = defaultdict(int)
    for p in profiles:
        for player, info in p["bases"].items():
            base_type_counts[f"{player}:{info['type']}"] += 1
            base_source_counts[info.get("source", "building")] += 1
    print(f"  Base types: {dict(base_type_counts)}")
    print(f"  Detection source: {dict(base_source_counts)}")

    # Base distances
    distances = [p["base_distance"] for p in profiles if p["base_distance"] is not None]
    if distances:
        print(f"  Base-to-base distance: {min(distances):.1f} - {max(distances):.1f}  (mean {np.mean(distances):.1f})")

    # Show unique base positions
    unique_positions = set()
    for p in profiles:
        for player, info in p["bases"].items():
            unique_positions.add((info["x"], info["y"]))
    print(f"  Unique spawn positions: {sorted(unique_positions)}")
    print()

    # --- Missing bases ---
    missing_p1 = [p for p in profiles if "p1" not in p["bases"]]
    missing_p2 = [p for p in profiles if "p2" not in p["bases"]]
    if missing_p1 or missing_p2:
        print("MISSING BASES (games where base not detected)")
        for p in missing_p1:
            print(f"  P1 missing: {p['file']}")
            print(f"    P1 entity types: {p['entity_types_p1']}")
        for p in missing_p2:
            print(f"  P2 missing: {p['file']}")
            print(f"    P2 entity types: {p['entity_types_p2']}")
        print()

    # --- Entity types across all games ---
    all_building_types = set()
    all_unit_types = set()
    building_freq = defaultdict(int)
    unit_freq = defaultdict(int)

    for p in profiles:
        for bt in p["building_types_p1"] + p["building_types_p2"]:
            all_building_types.add(bt)
            building_freq[bt] += 1
        for ut in p["unit_types_p1"] + p["unit_types_p2"]:
            all_unit_types.add(ut)
            unit_freq[ut] += 1

    print(f"BUILDING TYPES ({len(all_building_types)} unique across all games)")
    for bt in sorted(building_freq, key=building_freq.get, reverse=True):
        print(f"  {bt:30s}  appears in {building_freq[bt]:>3d}/{n} games")
    print()

    print(f"UNIT TYPES ({len(all_unit_types)} unique across all games)")
    for ut in sorted(unit_freq, key=unit_freq.get, reverse=True):
        print(f"  {ut:30s}  appears in {unit_freq[ut]:>3d}/{n} games")
    print()

    # --- Position data quality ---
    fracs = [p["position_non_nan_frac"] for p in profiles]
    print("POSITION DATA QUALITY")
    print(f"  Non-NaN fraction: {min(fracs):.2%} - {max(fracs):.2%}  (mean {np.mean(fracs):.2%})")
    print()

    # --- Economy columns (should be consistent) ---
    econ_sets = [set(p["economy_cols"]) for p in profiles]
    common_econ = set.intersection(*econ_sets) if econ_sets else set()
    print(f"ECONOMY COLUMNS (common across all games: {len(common_econ)})")
    for c in sorted(common_econ):
        print(f"  {c}")
    print()

    # --- Per-game detail table ---
    print("PER-GAME SUMMARY")
    print(f"  {'File':<45s} {'Dur':>5s} {'Rows':>5s} {'P1 Base':>15s} {'P2 Base':>15s} {'BBox W':>7s} {'Dist':>6s}")
    print(f"  {'-'*45} {'-'*5} {'-'*5} {'-'*15} {'-'*15} {'-'*7} {'-'*6}")
    for p in profiles:
        p1_info = p["bases"].get("p1")
        p2_info = p["bases"].get("p2")
        p1_src = "*" if p1_info and p1_info.get("source") == "worker_fallback" else ""
        p2_src = "*" if p2_info and p2_info.get("source") == "worker_fallback" else ""
        p1b = f"({p1_info['x']:.0f},{p1_info['y']:.0f}){p1_src}" if p1_info else "MISSING"
        p2b = f"({p2_info['x']:.0f},{p2_info['y']:.0f}){p2_src}" if p2_info else "MISSING"
        bw = f"{p['bounding_box']['width']:.0f}" if p["bounding_box"] else "?"
        dist = f"{p['base_distance']:.0f}" if p["base_distance"] else "?"
        fname = p["file"][:45]
        print(f"  {fname:<45s} {p['duration_minutes']:>5.1f} {p['rows']:>5d} {p1b:>15s} {p2b:>15s} {bw:>7s} {dist:>6s}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    input_dir = Path("data/quickstart/parquet")
    if not input_dir.exists():
        print(f"Error: {input_dir} does not exist.")
        return

    parquet_files = sorted(input_dir.glob("*_game_state.parquet"))
    if not parquet_files:
        print(f"No game state parquet files found in {input_dir}")
        return

    print(f"Found {len(parquet_files)} game files. Profiling...")
    print()

    profiles = []
    skipped = []
    for i, f in enumerate(parquet_files):
        print(f"  [{i+1}/{len(parquet_files)}] {f.name}...", end="", flush=True)
        try:
            profile = profile_game(f)
            if profile["rows"] < MIN_GAME_ROWS:
                print(f" SKIPPED (only {profile['rows']} row(s), degenerate game)")
                skipped.append(f.name)
                continue
            profiles.append(profile)
            print(" OK")
        except Exception as e:
            print(f" ERROR: {e}")

    if skipped:
        print()
        print(f"Skipped {len(skipped)} degenerate games (<{MIN_GAME_ROWS} rows):")
        for s in skipped:
            print(f"  - {s}")

    print()
    print_profile_report(profiles)


if __name__ == "__main__":
    main()
