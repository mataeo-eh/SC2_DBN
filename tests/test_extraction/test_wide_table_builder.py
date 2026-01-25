"""
Tests for WideTableBuilder component.

Tests the transformation of extracted state into wide-format rows.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from src_new.extraction.wide_table_builder import WideTableBuilder
from src_new.extraction.schema_manager import SchemaManager


@pytest.mark.unit
@pytest.mark.extraction
class TestWideTableBuilder:
    """Test suite for WideTableBuilder class."""

    @pytest.fixture
    def mock_schema(self, sample_schema_columns):
        """Create a mock schema manager."""
        schema = Mock(spec=SchemaManager)
        schema.get_column_list.return_value = sample_schema_columns
        schema.get_missing_value.return_value = np.nan
        return schema

    @pytest.fixture
    def builder(self, mock_schema):
        """Create WideTableBuilder instance."""
        return WideTableBuilder(mock_schema)

    def test_initialization(self, mock_schema):
        """Test WideTableBuilder initializes correctly."""
        builder = WideTableBuilder(mock_schema)

        assert builder.schema is mock_schema

    def test_build_row_structure(self, builder, sample_extracted_state):
        """Test that build_row returns correct structure."""
        row = builder.build_row(sample_extracted_state)

        assert isinstance(row, dict)
        assert 'game_loop' in row
        assert 'timestamp_seconds' in row
        assert row['game_loop'] == 100

    def test_build_row_timestamp_conversion(self, builder, sample_extracted_state):
        """Test that game_loop is converted to timestamp_seconds correctly."""
        row = builder.build_row(sample_extracted_state)

        expected_timestamp = 100 / 22.4
        assert 'timestamp_seconds' in row
        assert abs(row['timestamp_seconds'] - expected_timestamp) < 0.001

    def test_build_row_with_missing_units(self, builder):
        """Test that build_row handles missing units with NaN."""
        state = {
            'game_loop': 100,
            'p1_units': {},  # No units
            'p2_units': {},
            'p1_buildings': {},
            'p2_buildings': {},
            'p1_economy': {'minerals': 50, 'vespene': 0, 'supply_used': 12, 'supply_cap': 15,
                          'workers': 6, 'idle_workers': 0},
            'p2_economy': {'minerals': 50, 'vespene': 0, 'supply_used': 12, 'supply_cap': 15,
                          'workers': 6, 'idle_workers': 0},
            'p1_upgrades': {},
            'p2_upgrades': {},
            'messages': [],
        }

        row = builder.build_row(state)

        # Base columns should have values
        assert row['game_loop'] == 100
        assert row['p1_minerals'] == 50

    def test_add_unit_to_row(self, builder):
        """Test adding unit data to row."""
        row = {}
        unit_data = {
            'x': 30.0,
            'y': 30.0,
            'z': 8.0,
            'health': 45.0,
            'health_max': 45.0,
            'shields': 0.0,
            'shields_max': 0.0,
            'energy': 0.0,
            'energy_max': 0.0,
            'state': 'existing',
        }

        # Mock schema to include unit columns
        builder.schema.get_missing_value.return_value = np.nan
        for attr in ['x', 'y', 'z', 'health', 'health_max', 'shields',
                     'shields_max', 'energy', 'energy_max', 'state']:
            row[f'p1_marine_001_{attr}'] = np.nan

        builder.add_unit_to_row(row, 'p1', 'marine_001', unit_data)

        assert row['p1_marine_001_x'] == 30.0
        assert row['p1_marine_001_y'] == 30.0
        assert row['p1_marine_001_health'] == 45.0
        assert row['p1_marine_001_state'] == 'existing'

    def test_add_unit_to_row_killed(self, builder):
        """Test adding killed unit sets only state column."""
        row = {}
        unit_data = {
            'state': 'killed',
        }

        # Initialize row with NaN
        row['p1_marine_001_state'] = np.nan
        row['p1_marine_001_x'] = np.nan
        row['p1_marine_001_health'] = np.nan

        builder.add_unit_to_row(row, 'p1', 'marine_001', unit_data)

        assert row['p1_marine_001_state'] == 'killed'
        # Other columns should remain NaN
        assert np.isnan(row['p1_marine_001_x'])
        assert np.isnan(row['p1_marine_001_health'])

    def test_calculate_unit_counts(self, builder):
        """Test calculating unit counts by type."""
        units = {
            'p1_marine_001': {'unit_type_name': 'Marine', 'state': 'existing'},
            'p1_marine_002': {'unit_type_name': 'Marine', 'state': 'existing'},
            'p1_marine_003': {'unit_type_name': 'Marine', 'state': 'killed'},  # Should be excluded
            'p1_scv_001': {'unit_type_name': 'SCV', 'state': 'existing'},
        }

        counts = builder.calculate_unit_counts(units)

        assert counts['Marine'] == 2  # Two living marines
        assert counts['SCV'] == 1
        assert 'Marine' in counts  # Killed unit not counted separately

    def test_calculate_unit_counts_excludes_killed(self, builder):
        """Test that killed units are excluded from counts."""
        units = {
            'p1_marine_001': {'unit_type_name': 'Marine', 'state': 'killed'},
            'p1_marine_002': {'unit_type_name': 'Marine', 'state': 'killed'},
        }

        counts = builder.calculate_unit_counts(units)

        # No marines should be counted
        assert counts.get('Marine', 0) == 0

    def test_add_economy_to_row(self, builder):
        """Test adding economy data to row."""
        row = {
            'p1_minerals': np.nan,
            'p1_vespene': np.nan,
            'p1_supply_used': np.nan,
            'p1_supply_cap': np.nan,
            'p1_workers': np.nan,
            'p1_idle_workers': np.nan,
        }
        economy_data = {
            'minerals': 150,
            'vespene': 50,
            'supply_used': 12,
            'supply_cap': 15,
            'workers': 6,
            'idle_workers': 0,
        }

        builder.add_economy_to_row(row, 'p1', economy_data)

        assert row['p1_minerals'] == 150
        assert row['p1_vespene'] == 50
        assert row['p1_supply_used'] == 12
        assert row['p1_supply_cap'] == 15
        assert row['p1_workers'] == 6
        assert row['p1_idle_workers'] == 0

    def test_add_building_to_row(self, builder):
        """Test adding building data to row."""
        row = {
            'p1_building_5001_x': np.nan,
            'p1_building_5001_y': np.nan,
            'p1_building_5001_status': np.nan,
            'p1_building_5001_progress': np.nan,
        }
        building_data = {
            'x': 40.0,
            'y': 40.0,
            'z': 8.0,
            'status': 'completed',
            'progress': 100,
            'started_loop': 0,
            'completed_loop': 500,
            'destroyed_loop': None,
        }

        builder.add_building_to_row(row, 'p1', 'building_5001', building_data)

        assert row['p1_building_5001_x'] == 40.0
        assert row['p1_building_5001_y'] == 40.0
        assert row['p1_building_5001_status'] == 'completed'
        assert row['p1_building_5001_progress'] == 100

    def test_validate_row_success(self, builder, sample_schema_columns):
        """Test validating a correct row."""
        # Create row with all schema columns
        row = {col: 0 for col in sample_schema_columns}

        is_valid = builder.validate_row(row)

        assert is_valid is True

    def test_validate_row_missing_columns(self, builder, sample_schema_columns):
        """Test validating a row with missing columns."""
        # Create row missing some columns
        row = {col: 0 for col in sample_schema_columns[:10]}

        is_valid = builder.validate_row(row)

        assert is_valid is False

    def test_validate_row_extra_columns(self, builder, sample_schema_columns):
        """Test validating a row with extra columns."""
        # Create row with schema columns plus extras
        row = {col: 0 for col in sample_schema_columns}
        row['extra_column_1'] = 999
        row['extra_column_2'] = 888

        is_valid = builder.validate_row(row)

        assert is_valid is False

    def test_get_row_summary(self, builder):
        """Test getting row summary statistics."""
        row = {
            'game_loop': 1000,
            'timestamp_seconds': 44.64,
            'p1_minerals': 250,
            'p2_minerals': 300,
            'p1_supply_used': 45,
            'p2_supply_used': 50,
            'p1_marine_001_x': 30.0,
            'p1_marine_001_y': np.nan,  # Missing value
        }

        summary = builder.get_row_summary(row)

        assert summary['game_loop'] == 1000
        assert summary['timestamp_seconds'] == 44.64
        assert summary['total_columns'] == len(row)
        assert summary['missing_values'] >= 1  # At least the NaN we added
        assert summary['p1_minerals'] == 250
        assert summary['p2_minerals'] == 300

    def test_build_rows_batch(self, builder):
        """Test building multiple rows from batch of states."""
        states = [
            {'game_loop': i * 100, 'p1_units': {}, 'p2_units': {},
             'p1_buildings': {}, 'p2_buildings': {},
             'p1_economy': {'minerals': i * 50, 'vespene': 0, 'supply_used': 12,
                           'supply_cap': 15, 'workers': 6, 'idle_workers': 0},
             'p2_economy': {'minerals': i * 60, 'vespene': 0, 'supply_used': 12,
                           'supply_cap': 15, 'workers': 6, 'idle_workers': 0},
             'p1_upgrades': {}, 'p2_upgrades': {}, 'messages': []}
            for i in range(5)
        ]

        rows = builder.build_rows_batch(states)

        assert len(rows) == 5
        assert rows[0]['game_loop'] == 0
        assert rows[4]['game_loop'] == 400

    def test_build_rows_batch_handles_errors(self, builder, caplog):
        """Test that build_rows_batch continues on errors."""
        states = [
            {'game_loop': 0},  # Missing required keys - will error
            {'game_loop': 100, 'p1_units': {}, 'p2_units': {},
             'p1_buildings': {}, 'p2_buildings': {},
             'p1_economy': {'minerals': 50, 'vespene': 0, 'supply_used': 12,
                           'supply_cap': 15, 'workers': 6, 'idle_workers': 0},
             'p2_economy': {'minerals': 50, 'vespene': 0, 'supply_used': 12,
                           'supply_cap': 15, 'workers': 6, 'idle_workers': 0},
             'p1_upgrades': {}, 'p2_upgrades': {}, 'messages': []},  # Valid
        ]

        rows = builder.build_rows_batch(states)

        # Should continue past the error and process the valid state
        assert len(rows) >= 1
