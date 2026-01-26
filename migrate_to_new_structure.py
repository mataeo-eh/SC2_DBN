#!/usr/bin/env python3
"""
Migrate existing output files to new directory structure.

Old structure: data/quickstart/*.parquet and *.json
New structure: data/quickstart/parquet/*.parquet and data/quickstart/json/*.json
"""

import shutil
from pathlib import Path


def migrate_files():
    """Migrate files to new directory structure."""
    print()
    print("=" * 70)
    print("Migrating Files to New Directory Structure")
    print("=" * 70)
    print()

    data_dir = Path("data/quickstart")

    # Create new subdirectories
    parquet_dir = data_dir / "parquet"
    json_dir = data_dir / "json"

    parquet_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    print(f"Created directories:")
    print(f"  - {parquet_dir}")
    print(f"  - {json_dir}")
    print()

    # Find and move parquet files
    parquet_files = list(data_dir.glob("*.parquet"))
    print(f"Found {len(parquet_files)} parquet files to migrate:")

    for file in parquet_files:
        dest = parquet_dir / file.name
        print(f"  Moving: {file.name} -> parquet/{file.name}")
        shutil.move(str(file), str(dest))

    # Find and move json files (excluding dataset-metadata.json)
    json_files = [f for f in data_dir.glob("*.json") if f.name != "dataset-metadata.json"]
    print()
    print(f"Found {len(json_files)} json files to migrate:")

    for file in json_files:
        dest = json_dir / file.name
        print(f"  Moving: {file.name} -> json/{file.name}")
        shutil.move(str(file), str(dest))

    print()
    print("=" * 70)
    print("Migration complete!")
    print("=" * 70)
    print()
    print("NOTE: The migrated files DO NOT contain the Messages column.")
    print("You need to reprocess the replays with the updated pipeline to get")
    print("the Messages column in the output.")
    print()
    print("To reprocess:")
    print("  1. Ensure SC2 is installed")
    print("  2. Run: python quickstart.py")
    print()


if __name__ == "__main__":
    migrate_files()
