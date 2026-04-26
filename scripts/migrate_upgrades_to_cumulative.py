"""
Migrate p1_upgrades / p2_upgrades columns from per-completion-loop comma-strings
to cumulative chronological lists.

Old format (one cell per row):
    NaN                              # no upgrade completed at this game_loop
    "Burrow"                         # one upgrade completed at this loop
    "Stimpack,TerranInfantryWeaponsLevel1"  # multiple completed at this loop

New format (one cell per row):
    None                             # no upgrade has completed yet
    ["Burrow"]                       # cumulative list at/after this loop
    ["Burrow", "Stimpack", "TerranInfantryWeaponsLevel1"]  # ...etc

The script:
  - operates only on data/quickstart/parquet/ in the main repo
  - rewrites each .parquet file in place (compression preserved as snappy)
  - is idempotent: files already migrated are detected and skipped
  - sorts each row by game_loop before walking forward, defensively

Run with:
    .venv-3_11/Scripts/python.exe scripts/migrate_upgrades_to_cumulative.py

The script depends on / calls:
    - pandas (read_parquet, to_parquet)
    - pyarrow (transitive, used by pandas for parquet IO)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

# Directory that holds the extracted game-state parquets to migrate.
# The user requested that ONLY this directory be touched.
PARQUET_DIR = Path("data/quickstart/parquet")

# Columns to migrate. Both must follow the same format conventions.
UPGRADE_COLUMNS = ("p1_upgrades", "p2_upgrades")


def _is_listlike(value) -> bool:
    """Return True if value is a list-like (list, tuple, ndarray)."""
    return isinstance(value, (list, tuple, np.ndarray))


def column_state(series: pd.Series) -> str:
    """
    Classify the format state of an upgrade column.

    Returns one of:
        "migrated"  -- column already contains list values (new format)
        "legacy"    -- column contains strings (old per-loop encoding)
        "empty"     -- column is entirely null; treat as already migrated
                       (no completion events to migrate, nothing to do)

    Depends on / calls:
        - pandas.Series.dropna for the first non-null lookup
        - _is_listlike for type discrimination
    """
    nn = series.dropna()
    if nn.empty:
        return "empty"
    first = nn.iloc[0]
    if _is_listlike(first):
        return "migrated"
    if isinstance(first, str):
        return "legacy"
    # Defensive: an unrecognized type. Treat as already-non-legacy so we
    # don't accidentally corrupt a column we don't understand.
    return "migrated"


def migrate_legacy_series(series: pd.Series) -> List[Optional[List[str]]]:
    """
    Convert a legacy per-loop comma-string column to a cumulative-list column.

    Walks the series in row order (caller must have sorted by game_loop)
    and accumulates each non-null comma-delimited entry into a running list.
    Within a single completion loop, names are alphabetically sorted to match
    the new extraction code's deterministic per-loop ordering.

    Cells before the first completion event are returned as None so pyarrow
    serializes them as nulls in a list<string> column.

    Args:
        series: The legacy column. Must be a pandas Series of str/NaN values.

    Returns:
        A list of length len(series). Each element is either None (no
        completion yet) or a fresh list[str] (cumulative names through that row).

    Depends on / calls:
        - Nothing beyond builtin str.split / sorted
    """
    result: List[Optional[List[str]]] = []
    running: Optional[List[str]] = None

    for value in series:
        # Skip NaN / None / empty-string entries — they're "no event this row".
        if value is None or (isinstance(value, float) and pd.isna(value)):
            new_event_names: List[str] = []
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                new_event_names = []
            else:
                # Sort within-loop names alphabetically. The legacy encoding
                # was already alphabetical, but sort defensively to be safe.
                new_event_names = sorted(n for n in stripped.split(",") if n)
        else:
            # Unexpected type — bail by treating as no event.
            new_event_names = []

        if new_event_names:
            if running is None:
                running = list(new_event_names)
            else:
                running = running + new_event_names

        # Append a fresh copy so each row owns an independent list.
        result.append(list(running) if running is not None else None)

    return result


def migrate_file(path: Path, dry_run: bool = False) -> dict:
    """
    Migrate a single parquet file in place.

    Reads the parquet, sorts by game_loop, classifies each upgrade column,
    rewrites legacy columns into cumulative-list form, and writes the result
    back to the same path with snappy compression. If no column needs work,
    the file is left untouched on disk.

    Args:
        path: Path to the .parquet file.
        dry_run: If True, do all the work in memory but do not write the
                 result back to disk. Useful for verifying behavior.

    Returns:
        Dict with per-column outcome:
        {
            "path": str,
            "p1_upgrades": "migrated" | "already" | "empty" | "missing",
            "p2_upgrades": ...,
            "wrote": bool,
        }

    Depends on / calls:
        - pandas.read_parquet / DataFrame.to_parquet
        - column_state, migrate_legacy_series
    """
    df = pd.read_parquet(path)

    if "game_loop" in df.columns:
        df = df.sort_values("game_loop").reset_index(drop=True)

    outcome = {"path": str(path), "wrote": False}
    any_changed = False

    for col in UPGRADE_COLUMNS:
        if col not in df.columns:
            outcome[col] = "missing"
            continue

        state = column_state(df[col])
        if state == "migrated":
            outcome[col] = "already"
        elif state == "empty":
            outcome[col] = "empty"
        elif state == "legacy":
            df[col] = migrate_legacy_series(df[col])
            outcome[col] = "migrated"
            any_changed = True
        else:
            outcome[col] = f"unknown({state})"

    if any_changed and not dry_run:
        df.to_parquet(path, compression="snappy", index=False)
        outcome["wrote"] = True

    return outcome


def main() -> int:
    """Walk PARQUET_DIR and migrate every .parquet file found."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the migration in memory without writing files back to disk.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on the number of files to process (for testing).",
    )
    args = parser.parse_args()

    if not PARQUET_DIR.is_dir():
        print(f"ERROR: directory not found: {PARQUET_DIR}", file=sys.stderr)
        return 1

    files = sorted(PARQUET_DIR.glob("*.parquet"))
    if args.limit is not None:
        files = files[: args.limit]

    if not files:
        print(f"No .parquet files found in {PARQUET_DIR}")
        return 0

    print(
        f"Migrating {len(files)} parquet file(s) in {PARQUET_DIR}"
        f"{' [DRY RUN]' if args.dry_run else ''}"
    )

    counts = {"migrated": 0, "already": 0, "empty": 0, "missing": 0, "wrote": 0}
    started = time.time()

    for i, path in enumerate(files, 1):
        try:
            outcome = migrate_file(path, dry_run=args.dry_run)
        except Exception as exc:
            print(f"  [{i}/{len(files)}] {path.name}: ERROR {exc}", file=sys.stderr)
            continue

        for col in UPGRADE_COLUMNS:
            counts[outcome.get(col, "missing")] = (
                counts.get(outcome.get(col, "missing"), 0) + 1
            )
        if outcome["wrote"]:
            counts["wrote"] += 1

        # Only print files that changed or had unusual states; keep noise low.
        notable = (
            outcome["wrote"]
            or any(outcome.get(c) not in ("already", "empty", "missing")
                   for c in UPGRADE_COLUMNS)
        )
        if notable:
            cols_str = ", ".join(
                f"{c}={outcome.get(c, 'missing')}" for c in UPGRADE_COLUMNS
            )
            print(f"  [{i}/{len(files)}] {path.name}: {cols_str}"
                  f"{' (wrote)' if outcome['wrote'] else ''}")

    elapsed = time.time() - started
    print()
    print("Summary (per-column counts across all files):")
    for k in ("migrated", "already", "empty", "missing"):
        print(f"  {k:>8}: {counts.get(k, 0)}")
    print(f"  files written: {counts['wrote']}")
    print(f"  elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
