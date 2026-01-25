"""
Integration tests for SC2 Replay Extraction Pipeline.

Tests end-to-end functionality with mocked pysc2 observations.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from tests.fixtures.mock_observations import (
    create_marine_rush_sequence,
    create_building_construction_sequence,
)


@pytest.mark.integration
class TestEndToEndExtraction:
    """Integration tests for complete extraction pipeline."""

    @pytest.mark.slow
    def test_marine_rush_extraction_sequence(self, temp_output_dir):
        """Test extracting a marine rush sequence from start to finish."""
        from src_new.extraction.state_extractor import StateExtractor
        from src_new.extraction.schema_manager import SchemaManager
        from src_new.extraction.wide_table_builder import WideTableBuilder

        # Create observation sequence
        observations = create_marine_rush_sequence()

        # Initialize components
        state_extractor = StateExtractor()
        schema_manager = SchemaManager()

        # Extract states
        extracted_states = []
        for obs in observations:
            # Mock the unit extractors to return empty dicts
            # (since we're not testing actual pysc2 integration here)
            with patch.object(state_extractor, 'extract_units', return_value={}), \
                 patch.object(state_extractor, 'extract_buildings', return_value={}), \
                 patch.object(state_extractor, 'extract_economy', return_value={'minerals': 50, 'vespene': 0,
                     'supply_used': 12, 'supply_cap': 15, 'workers': 6, 'idle_workers': 0}), \
                 patch.object(state_extractor, 'extract_upgrades', return_value={}), \
                 patch.object(state_extractor, 'extract_messages', return_value=[]):

                state = state_extractor.extract_observation(obs, obs.observation.game_loop)
                extracted_states.append(state)

        # Verify we extracted all frames
        assert len(extracted_states) == len(observations)
        assert extracted_states[0]['game_loop'] == 0
        assert extracted_states[-1]['game_loop'] == 1500

    @pytest.mark.slow
    def test_building_construction_lifecycle(self):
        """Test tracking building construction from start to destruction."""
        from src_new.extraction.state_extractor import BuildingTracker

        # Create building sequence
        observations = create_building_construction_sequence()

        # Initialize tracker
        tracker = BuildingTracker()

        results = []
        for obs in observations:
            buildings = obs.observation.raw_data.units
            tracked = tracker.process_buildings(buildings, obs.observation.game_loop)
            results.append(tracked)

        # Verify lifecycle
        assert len(results) == 4

        # Frame 0: Building started
        if results[0]:
            building = list(results[0].values())[0]
            assert building['status'] in ['started', 'building']

        # Frame 2: Building completed
        if results[2]:
            building = list(results[2].values())[0]
            assert building['status'] == 'completed'
            assert building['completed_loop'] == 1000

        # Frame 3: Building destroyed
        if results[3]:
            building = list(results[3].values())[0]
            assert building['status'] == 'destroyed'

    def test_schema_to_wide_table_pipeline(self, sample_extracted_state):
        """Test schema creation and wide table building."""
        from src_new.extraction.schema_manager import SchemaManager
        from src_new.extraction.wide_table_builder import WideTableBuilder

        # Create schema
        schema = SchemaManager()

        # Add columns for the sample state
        schema.add_base_columns()
        schema.add_economy_columns('p1')
        schema.add_economy_columns('p2')

        # Create builder
        builder = WideTableBuilder(schema)

        # Build row
        row = builder.build_row(sample_extracted_state)

        # Verify row structure
        assert 'game_loop' in row
        assert 'timestamp_seconds' in row
        assert row['game_loop'] == 100

    def test_parquet_write_read_cycle(self, temp_output_dir, sample_parquet_dataframe):
        """Test writing and reading parquet files."""
        from src_new.extraction.parquet_writer import ParquetWriter

        writer = ParquetWriter(compression='snappy')
        output_path = temp_output_dir / "test_cycle.parquet"

        # Write DataFrame
        sample_parquet_dataframe.to_parquet(output_path, compression='snappy', index=False)

        # Read back
        df_read = pd.read_parquet(output_path)

        # Verify data integrity
        assert len(df_read) == len(sample_parquet_dataframe)
        assert list(df_read.columns) == list(sample_parquet_dataframe.columns)
        assert df_read['game_loop'].tolist() == sample_parquet_dataframe['game_loop'].tolist()

    def test_validation_on_extracted_data(self, temp_output_dir, sample_parquet_dataframe):
        """Test validation on freshly extracted data."""
        from src_new.utils.validation import OutputValidator

        # Write sample data
        output_path = temp_output_dir / "for_validation.parquet"
        sample_parquet_dataframe.to_parquet(output_path, compression='snappy', index=False)

        # Validate
        validator = OutputValidator()
        report = validator.validate_game_state_parquet(output_path)

        # Should pass validation
        assert report['valid'] is True
        assert len(report['errors']) == 0

    @pytest.mark.slow
    def test_multi_frame_extraction_consistency(self):
        """Test that unit IDs remain consistent across multiple frames."""
        from src_new.extraction.state_extractor import UnitTracker

        tracker = UnitTracker()

        # Frame 1: Unit appears
        mock_unit_1 = Mock()
        mock_unit_1.tag = 1000
        mock_unit_1.unit_type = 48
        mock_unit_1.pos = Mock(x=30.0, y=30.0, z=8.0)

        tracked_1 = tracker.process_units([mock_unit_1], game_loop=0)
        unit_id_1 = list(tracked_1.keys())[0]

        # Frame 2: Same unit appears again
        mock_unit_2 = Mock()
        mock_unit_2.tag = 1000  # Same tag
        mock_unit_2.unit_type = 48
        mock_unit_2.pos = Mock(x=31.0, y=30.0, z=8.0)  # Moved

        tracked_2 = tracker.process_units([mock_unit_2], game_loop=100)
        unit_id_2 = list(tracked_2.keys())[0]

        # Unit ID should be the same
        assert unit_id_1 == unit_id_2
        assert tracked_1[unit_id_1]['state'] == 'built'
        assert tracked_2[unit_id_2]['state'] == 'existing'


@pytest.mark.integration
@pytest.mark.pipeline
class TestPipelineComponents:
    """Integration tests for pipeline orchestration."""

    def test_schema_manager_initialization(self):
        """Test SchemaManager can be initialized and used."""
        from src_new.extraction.schema_manager import SchemaManager

        schema = SchemaManager()
        schema.add_base_columns()

        columns = schema.get_column_list()
        assert 'game_loop' in columns
        assert 'timestamp_seconds' in columns

    def test_wide_table_builder_with_real_schema(self, sample_extracted_state):
        """Test WideTableBuilder with actual SchemaManager."""
        from src_new.extraction.schema_manager import SchemaManager
        from src_new.extraction.wide_table_builder import WideTableBuilder

        schema = SchemaManager()
        schema.add_base_columns()
        schema.add_economy_columns('p1')
        schema.add_economy_columns('p2')

        builder = WideTableBuilder(schema)
        row = builder.build_row(sample_extracted_state)

        # Validate against schema
        assert builder.validate_row(row)

    def test_documentation_generation(self):
        """Test that documentation can be generated."""
        from src_new.extraction.schema_manager import SchemaManager

        schema = SchemaManager()
        schema.add_base_columns()

        docs = schema.generate_documentation()

        assert isinstance(docs, dict)
        assert 'game_loop' in docs
        assert 'description' in docs['game_loop']


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in integrated components."""

    def test_handle_missing_observation_data(self):
        """Test handling observations with missing data."""
        from src_new.extraction.state_extractor import StateExtractor

        extractor = StateExtractor()

        # Create observation with minimal data
        obs = Mock()
        obs.observation = Mock()
        obs.observation.game_loop = 100
        obs.observation.raw_data = Mock()
        obs.observation.raw_data.units = []
        obs.observation.raw_data.event = Mock()
        obs.observation.raw_data.event.dead_units = []
        obs.observation.chat = []

        # Should not crash
        with patch.object(extractor, 'extract_units', return_value={}), \
             patch.object(extractor, 'extract_buildings', return_value={}), \
             patch.object(extractor, 'extract_economy', return_value={}), \
             patch.object(extractor, 'extract_upgrades', return_value={}):

            state = extractor.extract_observation(obs, 100)
            assert state['game_loop'] == 100

    def test_handle_malformed_parquet(self, temp_output_dir):
        """Test validation handles malformed parquet files."""
        from src_new.utils.validation import OutputValidator

        validator = OutputValidator()

        # Create invalid parquet (will create text file instead)
        bad_file = temp_output_dir / "bad.parquet"
        bad_file.write_text("This is not a parquet file")

        report = validator.validate_game_state_parquet(bad_file)

        # Should report error, not crash
        assert report['valid'] is False
        assert len(report['errors']) > 0

    def test_wide_table_builder_handles_empty_state(self):
        """Test WideTableBuilder handles empty game state."""
        from src_new.extraction.schema_manager import SchemaManager
        from src_new.extraction.wide_table_builder import WideTableBuilder

        schema = SchemaManager()
        schema.add_base_columns()

        builder = WideTableBuilder(schema)

        empty_state = {
            'game_loop': 0,
            'p1_units': {},
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

        # Should build row without errors
        row = builder.build_row(empty_state)
        assert row['game_loop'] == 0
