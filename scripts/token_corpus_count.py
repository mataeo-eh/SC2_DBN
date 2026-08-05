"""Corpus-wide token-frequency counter for SC2 replay parquet files.

ROLE IN THE LARGER SYSTEM
-------------------------
The `Thesis_ML` package turns each replay parquet into a stream of "content
tokens" that a masked-diffusion model reconstructs.  A replay parquet is a very
WIDE table: one row per sampled game-state snapshot, and many columns that all
describe the SAME entity (its position, health, upgrades, etc.).  Only a small
part of that table is actually a token.  This script answers a single question:

    "Across every replay in a directory, how many times does the model see
     each distinct content token?"

To stay faithful to what the model actually sees, this script does NOT invent
its own parsing rules.  It imports and reuses the exact functions the
`Thesis_ML` serializer uses when it builds token canvases:

    * `thesis_ml.serialize.parse_entity_columns` - groups the wide
      `{player}_{bot}_{type}_{id}_{attribute}` columns back into one entity per
      (player, bot, entity_type, instance_id), and normalizes the entity-type
      name exactly as the vocabulary does.
    * `thesis_ml.serialize.parse_upgrades` - normalizes one `{player}_upgrades`
      cell into the same cumulative-upgrade token names the model counts.

WHAT COUNTS AS ONE TOKEN (must match Thesis_ML)
-----------------------------------------------
This mirrors the "token_accounting" contract documented in
`Thesis_ML/scripts/estimate_context_window.py`:

    * entity token : one occurrence per entity instance that has AT LEAST ONE
                     non-null attribute at a given timestep (row).  An entity
                     that is alive for 500 rows therefore contributes 500
                     occurrences of its entity-type token - because the model's
                     reconstruction canvas re-emits it at every timestep.
    * upgrade token: one occurrence per listed cumulative upgrade per timestep
                     (row), for each player.

THE "RUN TWICE, ONCE PER PLAYER" SCHEMA (why there is no double counting)
------------------------------------------------------------------------
Every replay is served to the model from two perspectives (p1 as self, p2 as
self).  In each perspective the reconstruction/target canvas contains only the
OTHER player's ("enemy") tokens.  So across the two passes combined, each
player's tokens are reconstructed exactly ONCE.  Counting every entity/upgrade
occurrence once - regardless of which player owns it - is therefore already the
correct total model exposure across both per-player passes.  We do NOT multiply
content counts by two.

STRUCTURAL TOKENS
-----------------
The canvas also carries structural special tokens.  The two that are
mode-independent and derivable from the parquet alone are reported separately:

    * [DELIMITER]: one per timestep in EACH perspective canvas -> 2 * timesteps.
    * [END]      : one per perspective per replay            -> 2 * replays.

[MASK] and [PAD] are deliberately excluded: their counts depend on the training
noise schedule and the padding budget, not on the data corpus.  The [WIN]/[LOSS]
outcome token (one per perspective sample -> 2 * replays) is reported as a
combined total without a win/loss split, because splitting it would require the
sibling replay metadata JSON files.

USAGE
-----
See the sibling `Run_Scripts.txt` for the exact command.  In short:

    uv run --project Thesis_ML python scripts/token_corpus_count.py \
        --input-dir data/quickstart/parquet \
        --output-dir scripts/Outputs

The `--project Thesis_ML` part runs the script inside the Thesis_ML uv
environment, which is where pandas / pyarrow / the thesis_ml package live.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Make the `thesis_ml` package importable no matter where this script is run
# from.  The package lives in the `Thesis_ML/src` submodule next to this repo's
# root.  We add that directory to the front of sys.path so the real serializer
# functions can be imported (guaranteeing our counting matches the model).
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent          # .../local-play-bootstrap-main/scripts
REPO_ROOT = SCRIPT_DIR.parent                          # .../local-play-bootstrap-main
THESIS_SRC = REPO_ROOT / "Thesis_ML" / "src"           # .../Thesis_ML/src
if str(THESIS_SRC) not in sys.path:
    sys.path.insert(0, str(THESIS_SRC))

from thesis_ml.serialize import (  # noqa: E402  (import after sys.path tweak)
    EntityColumnGroup,
    parse_entity_columns,
    parse_upgrades,
)

# Defaults chosen so the example command in Run_Scripts.txt "just works".
DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "quickstart" / "parquet"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "Outputs"
DEFAULT_OUTPUT_NAME = "token_corpus_counts.json"
DEFAULT_PATTERN = "*.parquet"
# The two per-player cumulative-upgrade columns in every replay parquet.
UPGRADE_OWNERS = ("p1", "p2")


# ---------------------------------------------------------------------------
# Per-entity occurrence counting.
#
# These two helpers are copied (with light adaptation) from
# `Thesis_ML/scripts/estimate_context_window.py` so that our per-timestep
# "is this entity present?" decision is byte-for-byte the same one that script
# uses.  The fast path reads only the entity's `health` column and uses parquet
# row-group NULL statistics, so we never have to materialize the tens of
# thousands of wide columns in a replay table.
# ---------------------------------------------------------------------------
def _metadata_non_null_count(
    parquet: pq.ParquetFile,
    column_name: str,
    leaf_indexes: dict[str, int],
) -> int | None:
    """Return a column's non-null row count from parquet metadata alone.

    Returns None (meaning "metadata was insufficient, fall back to reading the
    column") if the column is absent or any row group lacks null statistics.

    Parameters:
        parquet: The opened parquet file.
        column_name: Name of the leaf column to count.
        leaf_indexes: Map from column name to its physical leaf index (built
            once per file by the caller).

    Called by: `_count_present_entity_rows`.
    """
    column_index = leaf_indexes.get(column_name)
    if column_index is None:
        return None

    non_null = 0
    for row_group_index in range(parquet.metadata.num_row_groups):
        row_group = parquet.metadata.row_group(row_group_index)
        statistics = row_group.column(column_index).statistics
        if statistics is None or not statistics.has_null_count:
            return None
        non_null += row_group.num_rows - statistics.null_count
    return non_null


def _count_present_entity_rows(
    parquet: pq.ParquetFile,
    group: EntityColumnGroup,
    leaf_indexes: dict[str, int],
) -> int:
    """Count timesteps (rows) where an entity has >=1 non-null attribute.

    Current extractor schemas always include a `health` attribute that is
    populated whenever the entity exists, so counting non-null `health` rows is
    both correct and cheap.  If `health` is missing we fall back to the exact
    "any attribute is non-null" calculation over all of the entity's columns.

    Parameters:
        parquet: The opened parquet file.
        group: One parsed entity (its `attributes` maps attribute-name ->
            column-name).
        leaf_indexes: Map from column name to physical leaf index.

    Returns: number of rows in which this entity instance is present.
    Called by: `count_replay_tokens`.
    """
    health_column = group.attributes.get("health")
    if health_column is not None:
        count = _metadata_non_null_count(parquet, health_column, leaf_indexes)
        if count is not None:
            return count
        # Metadata lacked null stats: read just the health column and count.
        health = parquet.read(columns=[health_column]).column(health_column)
        return len(health) - health.null_count

    # No health attribute: OR together the validity masks of every attribute
    # column so a row counts as "present" if ANY attribute is non-null.
    columns = list(group.attributes.values())
    table = parquet.read(columns=columns)
    present = None
    for column in columns:
        valid = pc.is_valid(table.column(column))
        present = valid if present is None else pc.or_(present, valid)
    return int(pc.sum(present).as_py()) if present is not None else 0


def _count_upgrade_tokens_by_name(parquet: pq.ParquetFile) -> Counter[str]:
    """Count cumulative-upgrade token occurrences, bucketed by upgrade name.

    For each player's `{owner}_upgrades` column, every row's cell is normalized
    with the real `parse_upgrades` into zero or more upgrade token names, and
    each name occurrence is counted.  A long-lived upgrade is therefore counted
    once per timestep, matching the entity accounting above.

    Returns: Counter mapping upgrade token name -> occurrence count.
    Called by: `count_replay_tokens`.
    """
    available = set(parquet.schema_arrow.names)
    columns = [f"{owner}_upgrades" for owner in UPGRADE_OWNERS if f"{owner}_upgrades" in available]
    counts: Counter[str] = Counter()
    if not columns:
        return counts

    table = parquet.read(columns=columns)
    for column_name in columns:
        for cell in table.column(column_name).to_pylist():
            for upgrade_name in parse_upgrades(cell):
                counts[upgrade_name] += 1
    return counts


def count_replay_tokens(parquet_path: Path) -> tuple[Counter[str], Counter[str], int]:
    """Count content-token occurrences in one replay parquet.

    Parameters:
        parquet_path: Path to a single `*_game_state.parquet` replay file.

    Returns a 3-tuple:
        entity_counts : Counter of entity-type token name -> occurrences.
        upgrade_counts: Counter of upgrade token name -> occurrences.
        timesteps     : number of rows (snapshots) in the replay.

    Calls: `parse_entity_columns`, `_count_present_entity_rows`,
    `_count_upgrade_tokens_by_name`.
    """
    parquet = pq.ParquetFile(parquet_path)
    timesteps = parquet.metadata.num_rows

    # Group the wide entity columns back into one entity per instance, using the
    # model's own parser (this also normalizes each entity-type name).
    groups = parse_entity_columns(parquet.schema_arrow.names)

    # Build the name -> physical leaf index map once (used by the fast path).
    leaf_indexes = {
        parquet.metadata.schema.column(index).path: index
        for index in range(parquet.metadata.num_columns)
    }

    entity_counts: Counter[str] = Counter()
    for group in groups:
        present_rows = _count_present_entity_rows(parquet, group, leaf_indexes)
        if present_rows:
            entity_counts[group.entity_type] += present_rows

    upgrade_counts = _count_upgrade_tokens_by_name(parquet)
    return entity_counts, upgrade_counts, timesteps


def count_directory(input_dir: Path, pattern: str) -> dict[str, object]:
    """Count tokens across every matching parquet file in a directory.

    Parameters:
        input_dir: Directory containing replay parquet files.
        pattern  : Glob used to select files (default `*.parquet`).

    Returns: the fully-assembled report dictionary (see `build_report`).
    Calls: `count_replay_tokens`, `build_report`.
    """
    paths = sorted(input_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"no parquet files matched {pattern!r} in {input_dir}")

    entity_totals: Counter[str] = Counter()
    upgrade_totals: Counter[str] = Counter()
    total_timesteps = 0

    for index, path in enumerate(paths, start=1):
        entity_counts, upgrade_counts, timesteps = count_replay_tokens(path)
        entity_totals.update(entity_counts)
        upgrade_totals.update(upgrade_counts)
        total_timesteps += timesteps
        # Light progress output so a 900+ file run is not a silent black box.
        if index == 1 or index % 50 == 0 or index == len(paths):
            print(f"Processed {index}/{len(paths)} files (latest: {path.name})", flush=True)

    return build_report(
        input_dir=input_dir,
        pattern=pattern,
        num_files=len(paths),
        total_timesteps=total_timesteps,
        entity_totals=entity_totals,
        upgrade_totals=upgrade_totals,
    )


def build_report(
    *,
    input_dir: Path,
    pattern: str,
    num_files: int,
    total_timesteps: int,
    entity_totals: Counter[str],
    upgrade_totals: Counter[str],
) -> dict[str, object]:
    """Assemble the JSON-serializable report from aggregated counters.

    The combined `content_token_counts` map is sorted by descending count (then
    by name) so the most-seen tokens appear first when the file is read by a
    human.  Entity and upgrade names live in separate vocab namespaces; on the
    off chance a name exists in both, the combined map sums them and the
    by-kind breakdown keeps them distinct.
    """
    # Merge entity + upgrade into one "every content token" map.
    combined: Counter[str] = Counter()
    combined.update(entity_totals)
    combined.update(upgrade_totals)

    def sorted_map(counter: Counter[str]) -> dict[str, int]:
        """Return a plain dict ordered by descending count, then name."""
        return {
            name: count
            for name, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        }

    content_occurrences = sum(combined.values())

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "file_pattern": pattern,
        "parquet_files": num_files,
        "total_timesteps": total_timesteps,
        "methodology": {
            "source_of_truth": (
                "Uses thesis_ml.serialize.parse_entity_columns and parse_upgrades "
                "so counts match the model's token canvases."
            ),
            "entity_token": (
                "one occurrence per entity instance with >=1 non-null attribute "
                "at a timestep (row); a persistent entity is counted once per row"
            ),
            "upgrade_token": (
                "one occurrence per listed cumulative upgrade per timestep (row), "
                "per player"
            ),
            "per_player_passes": (
                "each replay is served from both player perspectives; each pass "
                "reconstructs only the OTHER player's tokens, so counting every "
                "occurrence once already reflects total exposure across both "
                "passes (no doubling of content tokens)"
            ),
            "excluded": (
                "[MASK] and [PAD] are excluded (they depend on the noise "
                "schedule and padding budget, not the data)"
            ),
        },
        "totals": {
            "content_token_occurrences": content_occurrences,
            "unique_content_tokens": len(combined),
            "unique_entity_tokens": len(entity_totals),
            "unique_upgrade_tokens": len(upgrade_totals),
        },
        # THE MAIN DELIVERABLE: every content token and how many times it appears.
        "content_token_counts": sorted_map(combined),
        "content_token_counts_by_kind": {
            "entity": sorted_map(entity_totals),
            "upgrade": sorted_map(upgrade_totals),
        },
        # Mode-independent structural special tokens, derivable from the parquet.
        "structural_token_counts": {
            "[DELIMITER]": 2 * total_timesteps,
            "[END]": 2 * num_files,
            "[WIN]+[LOSS] (outcome, combined)": 2 * num_files,
        },
    }


def write_report(report: dict[str, object], output_path: Path) -> None:
    """Write the report to JSON atomically (temp file + rename)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temp_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(output_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments (see module docstring / Run_Scripts.txt)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing replay .parquet files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory the JSON report is written to.",
    )
    parser.add_argument(
        "--output-name",
        default=DEFAULT_OUTPUT_NAME,
        help="Filename for the JSON report inside --output-dir.",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="Glob used to select parquet files in --input-dir.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point: count tokens in the input dir and write the JSON report."""
    args = parse_args(argv)
    report = count_directory(args.input_dir, args.pattern)
    output_path = args.output_dir / args.output_name
    write_report(report, output_path)
    totals = report["totals"]
    print(
        f"Done. {totals['unique_content_tokens']} unique content tokens, "
        f"{totals['content_token_occurrences']} total occurrences across "
        f"{report['parquet_files']} files.\nWrote: {output_path}"
    )


if __name__ == "__main__":
    main()
