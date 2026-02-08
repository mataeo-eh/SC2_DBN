import pandas as pd
from pathlib import Path
import numpy as np

data_dir = Path("data/quickstart/parquet")

def check_for_messages_column(data_dir):
    if not data_dir.exists():
        print(f"Error: Directory {data_dir} does not exist.")
        print("Please run quickstart.py first to generate the data.")
        exit(1)

    parquet_files = list(data_dir.glob("*_game_state.parquet"))

    if not parquet_files:
        print(f"No game state parquet files found in {data_dir}")
        exit(1)

    print("=" * 70)
    print("Verifying Messages Column Implementation")
    print("=" * 70)
    print()

    for file in parquet_files:
        print(f"Loading {file.name}...")
        df = pd.read_parquet(file)

        # Check if Messages column exists
        if 'Messages' not in df.columns:
            print("  ERROR: Messages column not found!")
            print(f"  Available columns: {list(df.columns[:10])}...")
            continue

        print("  SUCCESS: Messages column exists!")

        # Count non-NaN messages
        messages_col = df['Messages']
        non_nan_count = messages_col.notna().sum()
        total_rows = len(df)

        print(f"  Total rows: {total_rows}")
        print(f"  Rows with messages: {non_nan_count}")
        print(f"  Rows without messages: {total_rows - non_nan_count}")

        if non_nan_count > 0:
            print(f"  SUCCESS: Found {non_nan_count} game loops with messages!")

            # Show some example messages
            message_rows = df[messages_col.notna()]
            print()
            print("  Sample messages:")
            for idx, row in message_rows.head(5).iterrows():
                game_loop = row['game_loop']
                timestamp = row['timestamp_seconds']
                messages = row['Messages']

                # Handle both string and list types
                if isinstance(messages, list):
                    print(f"    Loop {game_loop} ({timestamp:.1f}s): {len(messages)} messages")
                    for msg in messages[:3]:  # Show first 3 messages
                        print(f"      - {msg}")
                else:
                    print(f"    Loop {game_loop} ({timestamp:.1f}s): {messages}")
        else:
            print("  WARNING: No messages found in this replay.")
            print("  This could be normal if the replay has no ally chat messages.")

        print()
        print("  First 3 rows (selected columns):")
        display_cols = ['game_loop', 'timestamp_seconds', 'Messages', 'p1_minerals', 'p2_minerals']
        available_cols = [col for col in display_cols if col in df.columns]
        print(df[available_cols].head(3).to_string(index=False))
        print()
        print("-" * 70)
        print()

    print("Verification complete!")
    print()
    print("If you see 'SUCCESS: Found X game loops with messages' above,")
    print("the Messages column is working correctly!")
    print()

def messages_column_summary(data_dir):
    parquet_files = list(data_dir.glob("*_game_state.parquet"))
    messages_parsed = 0
    no_messages = 0
    null_files = 0
    for file in parquet_files:
        df = pd.read_parquet(file)
        if 'Messages' in df.columns:
            messages_col = df['Messages']
            non_nan_count = messages_col.notna().sum()
            if non_nan_count > 0:
                messages_parsed += 1
            else:
                no_messages += 1
        else:
            print(f"ERROR: Messages column not found in {file.name}")
            null_files += 1
    print("=" * 70)
    print(f"Total replays with Messages column and with messages extracted: {messages_parsed} out of {len(parquet_files)-null_files}")
    print("- " * 70)
    print(f"Total replays with Messages column but no messages extracted: {no_messages} out of {len(parquet_files)-null_files}")
    print("- " * 70)
    print(f"Total replays with no Messages column: {null_files}")

if __name__ == "__main__":
    messages_column_summary(data_dir)