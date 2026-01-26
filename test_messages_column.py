#!/usr/bin/env python3
"""
Unit test to verify the Messages column implementation without requiring SC2.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import only the modules we need, avoiding circular imports
import importlib.util

def import_module_from_file(module_name, file_path):
    """Import a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import schema_manager directly
schema_manager_path = project_root / "src_new" / "extraction" / "schema_manager.py"
schema_manager = import_module_from_file("schema_manager", schema_manager_path)
SchemaManager = schema_manager.SchemaManager

# Import wide_table_builder directly
wide_table_builder_path = project_root / "src_new" / "extraction" / "wide_table_builder.py"
wide_table_builder = import_module_from_file("wide_table_builder", wide_table_builder_path)
WideTableBuilder = wide_table_builder.WideTableBuilder


def test_messages_column_in_schema():
    """Test that Messages column is added to schema."""
    print("Test 1: Checking if Messages column is in schema...")

    schema = SchemaManager()

    # Check if Messages column exists
    columns = schema.get_column_list()
    assert 'Messages' in columns, "Messages column not found in schema!"

    # Check dtype
    dtype = schema.get_dtype('Messages')
    assert dtype == 'object', f"Messages column dtype should be 'object', got '{dtype}'"

    # Check documentation
    docs = schema.generate_documentation()
    assert 'Messages' in docs, "Messages column not documented!"

    print("  ✓ Messages column exists in schema")
    print(f"  ✓ Column type: {dtype}")
    print(f"  ✓ Description: {docs['Messages']['description']}")
    print()


def test_messages_formatting():
    """Test the message formatting logic."""
    print("Test 2: Testing message formatting...")

    schema = SchemaManager()
    builder = WideTableBuilder(schema)

    # Test case 1: No messages
    result = builder._format_messages([])
    assert pd.isna(result), "Empty messages should return NaN"
    print("  ✓ Empty messages return NaN")

    # Test case 2: Single message
    messages = [{'game_loop': 100, 'player_id': 1, 'message': 'Hello world'}]
    result = builder._format_messages(messages)
    assert result == 'Hello world', f"Single message should return string, got {result}"
    print("  ✓ Single message returns string")

    # Test case 3: Multiple messages
    messages = [
        {'game_loop': 100, 'player_id': 1, 'message': 'Message 1'},
        {'game_loop': 100, 'player_id': 1, 'message': 'Message 2'},
        {'game_loop': 100, 'player_id': 1, 'message': 'Message 3'},
    ]
    result = builder._format_messages(messages)
    assert isinstance(result, list), f"Multiple messages should return list, got {type(result)}"
    assert len(result) == 3, f"Should have 3 messages, got {len(result)}"
    assert result == ['Message 1', 'Message 2', 'Message 3'], f"Messages content mismatch: {result}"
    print("  ✓ Multiple messages return list of strings")
    print()


def test_build_row_with_messages():
    """Test building a row with messages."""
    print("Test 3: Testing row building with messages...")

    schema = SchemaManager()

    # Add economy columns so we have a valid schema
    schema._add_economy_columns()

    builder = WideTableBuilder(schema)

    # Create a minimal extracted state with messages
    state_no_messages = {
        'game_loop': 100,
        'messages': [],
        'p1_economy': {'minerals': 50, 'vespene': 0},
        'p2_economy': {'minerals': 50, 'vespene': 0},
    }

    state_one_message = {
        'game_loop': 200,
        'messages': [{'game_loop': 200, 'player_id': 1, 'message': 'Test message'}],
        'p1_economy': {'minerals': 100, 'vespene': 25},
        'p2_economy': {'minerals': 75, 'vespene': 50},
    }

    state_multiple_messages = {
        'game_loop': 300,
        'messages': [
            {'game_loop': 300, 'player_id': 1, 'message': 'Bot tag: v1.0'},
            {'game_loop': 300, 'player_id': 1, 'message': 'Debug: Started attack'},
        ],
        'p1_economy': {'minerals': 200, 'vespene': 100},
        'p2_economy': {'minerals': 150, 'vespene': 75},
    }

    # Test no messages
    row1 = builder.build_row(state_no_messages)
    assert 'Messages' in row1, "Messages column should be in row"
    assert pd.isna(row1['Messages']), "Messages should be NaN when no messages"
    print("  ✓ Row with no messages has NaN in Messages column")

    # Test one message
    row2 = builder.build_row(state_one_message)
    assert 'Messages' in row2, "Messages column should be in row"
    assert row2['Messages'] == 'Test message', f"Expected 'Test message', got {row2['Messages']}"
    print("  ✓ Row with one message has string in Messages column")

    # Test multiple messages
    row3 = builder.build_row(state_multiple_messages)
    assert 'Messages' in row3, "Messages column should be in row"
    assert isinstance(row3['Messages'], list), f"Expected list, got {type(row3['Messages'])}"
    assert len(row3['Messages']) == 2, f"Expected 2 messages, got {len(row3['Messages'])}"
    print("  ✓ Row with multiple messages has list in Messages column")
    print(f"    Messages: {row3['Messages']}")
    print()


def test_parquet_compatibility():
    """Test that the Messages column can be written to parquet."""
    print("Test 4: Testing parquet compatibility...")

    schema = SchemaManager()
    schema._add_economy_columns()

    # Create sample rows with different message types
    rows = [
        {
            'game_loop': 100,
            'timestamp_seconds': 100 / 22.4,
            'Messages': np.nan,
            'p1_minerals': 50,
            'p2_minerals': 50,
        },
        {
            'game_loop': 200,
            'timestamp_seconds': 200 / 22.4,
            'Messages': 'Single message',
            'p1_minerals': 100,
            'p2_minerals': 75,
        },
        {
            'game_loop': 300,
            'timestamp_seconds': 300 / 22.4,
            'Messages': ['Message 1', 'Message 2'],
            'p1_minerals': 150,
            'p2_minerals': 125,
        },
    ]

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Ensure Messages column is object type (can hold mixed types)
    df['Messages'] = df['Messages'].astype('object')

    print(f"  ✓ Created DataFrame with {len(df)} rows")
    print(f"  ✓ Messages column dtype: {df['Messages'].dtype}")

    # Test writing to parquet
    test_file = Path("test_messages_output.parquet")
    try:
        df.to_parquet(test_file, engine='pyarrow', compression='snappy', index=False)
        print(f"  ✓ Successfully wrote DataFrame to {test_file}")

        # Read it back
        df_read = pd.read_parquet(test_file)
        print(f"  ✓ Successfully read DataFrame from {test_file}")

        # Verify Messages column
        assert 'Messages' in df_read.columns, "Messages column not in read DataFrame"
        assert len(df_read) == 3, f"Expected 3 rows, got {len(df_read)}"

        # Check values
        assert pd.isna(df_read.iloc[0]['Messages']), "First row should have NaN"
        assert df_read.iloc[1]['Messages'] == 'Single message', "Second row should have string"
        assert isinstance(df_read.iloc[2]['Messages'], list), "Third row should have list"

        print("  ✓ All values correctly preserved after parquet round-trip")

    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()
            print(f"  ✓ Cleaned up test file")

    print()


def main():
    """Run all tests."""
    print()
    print("=" * 70)
    print("Messages Column Implementation - Unit Tests")
    print("=" * 70)
    print()

    try:
        test_messages_column_in_schema()
        test_messages_formatting()
        test_build_row_with_messages()
        test_parquet_compatibility()

        print("=" * 70)
        print("All tests passed!")
        print("=" * 70)
        print()
        print("The Messages column implementation is working correctly.")
        print("Next step: Run quickstart.py to process actual replays.")
        print()
        return 0

    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        print()
        return 1

    except Exception as e:
        print()
        print("=" * 70)
        print(f"ERROR: {e}")
        print("=" * 70)
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
