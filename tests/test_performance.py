"""
Performance tests for SC2 Replay Extraction Pipeline.

Tests performance characteristics, memory usage, and scalability.
"""

import pytest
import time
import sys
from unittest.mock import Mock, patch


@pytest.mark.slow
@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks for pipeline components."""

    def test_unit_tracker_performance(self):
        """Test UnitTracker performance with many units."""
        from src_new.extraction.state_extractor import UnitTracker

        tracker = UnitTracker()

        # Create 1000 mock units
        mock_units = []
        for i in range(1000):
            unit = Mock()
            unit.tag = i
            unit.unit_type = 48
            unit.pos = Mock(x=float(i % 100), y=float(i // 100), z=8.0)
            mock_units.append(unit)

        # Measure processing time
        start_time = time.time()
        tracker.process_units(mock_units, game_loop=0)
        elapsed = time.time() - start_time

        # Should process 1000 units quickly (< 100ms)
        assert elapsed < 0.1, f"UnitTracker too slow: {elapsed:.3f}s for 1000 units"

    def test_wide_table_builder_performance(self):
        """Test WideTableBuilder performance with large state."""
        from src_new.extraction.schema_manager import SchemaManager
        from src_new.extraction.wide_table_builder import WideTableBuilder

        schema = SchemaManager()
        schema.add_base_columns()

        # Add many unit columns
        for i in range(100):
            for attr in ['x', 'y', 'z', 'health', 'state']:
                schema.columns.append(f'p1_marine_{i:03d}_{attr}')

        builder = WideTableBuilder(schema)

        # Create large state
        state = {
            'game_loop': 1000,
            'p1_units': {
                f'p1_marine_{i:03d}': {
                    'x': float(i), 'y': float(i), 'z': 8.0,
                    'health': 45.0, 'state': 'existing'
                }
                for i in range(100)
            },
            'p2_units': {},
            'p1_buildings': {},
            'p2_buildings': {},
            'p1_economy': {'minerals': 500, 'vespene': 250, 'supply_used': 100, 'supply_cap': 100,
                          'workers': 20, 'idle_workers': 0},
            'p2_economy': {'minerals': 500, 'vespene': 250, 'supply_used': 100, 'supply_cap': 100,
                          'workers': 20, 'idle_workers': 0},
            'p1_upgrades': {},
            'p2_upgrades': {},
            'messages': [],
        }

        # Measure build time
        start_time = time.time()
        row = builder.build_row(state)
        elapsed = time.time() - start_time

        # Should build row quickly (< 50ms)
        assert elapsed < 0.05, f"WideTableBuilder too slow: {elapsed:.3f}s"

    def test_validation_performance(self, create_mock_parquet):
        """Test validation performance on large parquet."""
        from src_new.utils.validation import OutputValidator

        # Create large parquet
        data = {
            'game_loop': list(range(0, 10000, 10)),  # 1000 rows
            'timestamp_seconds': [i / 22.4 for i in range(0, 10000, 10)],
            'p1_minerals': [50 + i for i in range(1000)],
            'p1_vespene': [i for i in range(1000)],
            'p1_supply_used': [12 + (i % 88) for i in range(1000)],
            'p1_supply_cap': [15 + (i % 85) for i in range(1000)],
        }
        parquet = create_mock_parquet('large.parquet', data)

        validator = OutputValidator()

        # Measure validation time
        start_time = time.time()
        report = validator.validate_game_state_parquet(parquet)
        elapsed = time.time() - start_time

        # Should validate quickly (< 500ms)
        assert elapsed < 0.5, f"Validation too slow: {elapsed:.3f}s for 1000 rows"
        assert report['valid'] is True

    def test_schema_building_performance(self):
        """Test SchemaManager performance with many columns."""
        from src_new.extraction.schema_manager import SchemaManager

        schema = SchemaManager()

        # Measure time to add many columns
        start_time = time.time()
        schema.add_base_columns()
        for player in [1, 2]:
            schema.add_economy_columns(f'p{player}')
            schema.add_upgrade_columns(f'p{player}')

            # Add 100 units per player
            for i in range(100):
                schema.add_unit_columns(f'p{player}', 'Marine', f'{i:03d}')

        elapsed = time.time() - start_time

        # Should build schema quickly
        assert elapsed < 1.0, f"Schema building too slow: {elapsed:.3f}s"

        # Verify schema size
        columns = schema.get_column_list()
        assert len(columns) > 100  # At least base + economy + some units

    def test_memory_usage_unit_tracker(self):
        """Test memory usage of UnitTracker with many units."""
        from src_new.extraction.state_extractor import UnitTracker

        tracker = UnitTracker()

        # Track 10000 units
        for i in range(10000):
            tracker.assign_unit_id(tag=i, unit_type=48)

        # Check memory usage is reasonable
        registry_size = sys.getsizeof(tracker.unit_registry)
        counters_size = sys.getsizeof(tracker.unit_counters)
        total_size = registry_size + counters_size

        # Should use < 10MB for 10000 units
        assert total_size < 10 * 1024 * 1024, f"UnitTracker uses too much memory: {total_size / 1024 / 1024:.2f}MB"

    @pytest.mark.slow
    def test_batch_row_building_performance(self):
        """Test performance of building multiple rows."""
        from src_new.extraction.schema_manager import SchemaManager
        from src_new.extraction.wide_table_builder import WideTableBuilder

        schema = SchemaManager()
        schema.add_base_columns()
        schema.add_economy_columns('p1')
        schema.add_economy_columns('p2')

        builder = WideTableBuilder(schema)

        # Create 1000 states
        states = []
        for i in range(1000):
            state = {
                'game_loop': i * 10,
                'p1_units': {},
                'p2_units': {},
                'p1_buildings': {},
                'p2_buildings': {},
                'p1_economy': {'minerals': 50 + i, 'vespene': i, 'supply_used': 12, 'supply_cap': 15,
                              'workers': 6, 'idle_workers': 0},
                'p2_economy': {'minerals': 50 + i, 'vespene': i, 'supply_used': 12, 'supply_cap': 15,
                              'workers': 6, 'idle_workers': 0},
                'p1_upgrades': {},
                'p2_upgrades': {},
                'messages': [],
            }
            states.append(state)

        # Measure batch building time
        start_time = time.time()
        rows = builder.build_rows_batch(states)
        elapsed = time.time() - start_time

        # Should process 1000 states quickly (< 1 second)
        assert elapsed < 1.0, f"Batch building too slow: {elapsed:.3f}s for 1000 states"
        assert len(rows) == 1000

        # Calculate throughput
        throughput = len(rows) / elapsed
        print(f"\nBatch building throughput: {throughput:.0f} rows/second")


@pytest.mark.performance
class TestScalability:
    """Test scalability characteristics."""

    def test_unit_tracker_scales_linearly(self):
        """Test that UnitTracker processing time scales linearly."""
        from src_new.extraction.state_extractor import UnitTracker

        sizes = [100, 500, 1000]
        times = []

        for size in sizes:
            tracker = UnitTracker()

            # Create units
            mock_units = []
            for i in range(size):
                unit = Mock()
                unit.tag = i
                unit.unit_type = 48
                unit.pos = Mock(x=float(i), y=float(i), z=8.0)
                mock_units.append(unit)

            # Measure time
            start_time = time.time()
            tracker.process_units(mock_units, game_loop=0)
            elapsed = time.time() - start_time
            times.append(elapsed)

        # Check that doubling size roughly doubles time (within 3x tolerance)
        # times[1] / times[0] should be close to sizes[1] / sizes[0]
        ratio_time = times[1] / times[0] if times[0] > 0 else 0
        ratio_size = sizes[1] / sizes[0]

        # Allow 3x tolerance for variation
        assert ratio_time < ratio_size * 3, "UnitTracker does not scale linearly"

    def test_wide_table_builder_scales_with_columns(self):
        """Test that WideTableBuilder scales with column count."""
        from src_new.extraction.schema_manager import SchemaManager
        from src_new.extraction.wide_table_builder import WideTableBuilder

        column_counts = [50, 100, 200]
        times = []

        for col_count in column_counts:
            schema = SchemaManager()
            schema.columns = [f'col_{i}' for i in range(col_count)]

            builder = WideTableBuilder(schema)

            state = {
                'game_loop': 1000,
                'p1_units': {},
                'p2_units': {},
                'p1_buildings': {},
                'p2_buildings': {},
                'p1_economy': {'minerals': 500, 'vespene': 250, 'supply_used': 100, 'supply_cap': 100,
                              'workers': 20, 'idle_workers': 0},
                'p2_economy': {'minerals': 500, 'vespene': 250, 'supply_used': 100, 'supply_cap': 100,
                              'workers': 20, 'idle_workers': 0},
                'p1_upgrades': {},
                'p2_upgrades': {},
                'messages': [],
            }

            start_time = time.time()
            builder.build_row(state)
            elapsed = time.time() - start_time
            times.append(elapsed)

        # All times should be reasonably fast
        for t in times:
            assert t < 0.1, f"WideTableBuilder too slow: {t:.3f}s"
