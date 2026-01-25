"""
Tests for OutputValidator component.

Tests validation of extracted parquet files for quality assurance.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from src_new.utils.validation import OutputValidator


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.validation
class TestOutputValidator:
    """Test suite for OutputValidator class."""

    @pytest.fixture
    def validator(self):
        """Create OutputValidator instance."""
        return OutputValidator()

    @pytest.fixture
    def valid_parquet(self, create_mock_parquet):
        """Create a valid game state parquet for testing."""
        data = {
            'game_loop': [0, 100, 200, 300, 400],
            'timestamp_seconds': [0.0, 4.46, 8.93, 13.39, 17.86],
            'p1_minerals': [50, 150, 250, 350, 450],
            'p1_vespene': [0, 50, 100, 150, 200],
            'p1_supply_used': [12, 15, 18, 21, 24],
            'p1_supply_cap': [15, 23, 23, 31, 31],
            'p2_minerals': [50, 200, 300, 400, 500],
            'p2_vespene': [0, 75, 125, 175, 225],
            'p2_supply_used': [12, 14, 16, 18, 20],
            'p2_supply_cap': [15, 23, 23, 31, 31],
        }
        return create_mock_parquet('valid_game_state.parquet', data)

    def test_initialization(self, validator):
        """Test OutputValidator initializes correctly."""
        assert validator is not None

    def test_validate_nonexistent_file(self, validator, tmp_path):
        """Test validating a file that doesn't exist."""
        nonexistent = tmp_path / "nonexistent.parquet"

        report = validator.validate_game_state_parquet(nonexistent)

        assert report['valid'] is False
        assert len(report['errors']) > 0
        assert 'not found' in report['errors'][0].lower()

    def test_validate_valid_parquet(self, validator, valid_parquet):
        """Test validating a correct parquet file."""
        report = validator.validate_game_state_parquet(valid_parquet)

        assert report['valid'] is True
        assert len(report['errors']) == 0
        assert report['checks']['row_count'] is True
        assert report['checks']['required_columns'] is True
        assert report['checks']['no_duplicate_game_loops'] is True

    def test_validate_empty_parquet(self, validator, create_mock_parquet):
        """Test validating an empty parquet (0 rows)."""
        empty_parquet = create_mock_parquet('empty.parquet', {
            'game_loop': [],
            'timestamp_seconds': [],
        })

        report = validator.validate_game_state_parquet(empty_parquet)

        assert report['valid'] is False
        assert report['checks']['row_count'] is False
        assert 'empty' in str(report['errors']).lower()

    def test_detect_duplicate_game_loops(self, validator, create_mock_parquet):
        """Test detecting duplicate game_loop values."""
        duplicate_data = {
            'game_loop': [0, 100, 100, 200],  # Duplicate at 100
            'timestamp_seconds': [0.0, 4.46, 4.46, 8.93],
            'p1_minerals': [50, 150, 150, 250],
        }
        parquet = create_mock_parquet('duplicate_loops.parquet', duplicate_data)

        report = validator.validate_game_state_parquet(parquet)

        assert report['valid'] is False
        assert report['checks']['no_duplicate_game_loops'] is False
        assert any('duplicate' in err.lower() for err in report['errors'])

    def test_detect_negative_resources(self, validator, create_mock_parquet):
        """Test detecting negative resource values."""
        invalid_data = {
            'game_loop': [0, 100, 200],
            'timestamp_seconds': [0.0, 4.46, 8.93],
            'p1_minerals': [50, -100, 150],  # Negative minerals
            'p1_vespene': [0, 50, 100],
            'p1_supply_used': [12, 15, 18],
            'p1_supply_cap': [15, 23, 23],
        }
        parquet = create_mock_parquet('negative_resources.parquet', invalid_data)

        report = validator.validate_game_state_parquet(parquet)

        assert report['valid'] is False
        assert report['checks']['resource_validity'] is False
        assert any('negative' in err.lower() for err in report['errors'])

    def test_detect_supply_violation(self, validator, create_mock_parquet):
        """Test detecting supply_used > supply_cap."""
        invalid_data = {
            'game_loop': [0, 100],
            'timestamp_seconds': [0.0, 4.46],
            'p1_minerals': [50, 150],
            'p1_vespene': [0, 50],
            'p1_supply_used': [12, 25],  # Exceeds cap
            'p1_supply_cap': [15, 23],
        }
        parquet = create_mock_parquet('supply_violation.parquet', invalid_data)

        report = validator.validate_game_state_parquet(parquet)

        assert report['valid'] is False
        assert any('supply' in err.lower() for err in report['errors'])

    def test_detect_missing_required_columns(self, validator, create_mock_parquet):
        """Test detecting missing required columns."""
        incomplete_data = {
            'game_loop': [0, 100, 200],
            # Missing timestamp_seconds
        }
        parquet = create_mock_parquet('missing_columns.parquet', incomplete_data)

        report = validator.validate_game_state_parquet(parquet)

        assert report['valid'] is False
        assert report['checks']['required_columns'] is False
        assert any('missing' in err.lower() for err in report['errors'])

    def test_check_building_progress_monotonic(self, validator, create_mock_parquet):
        """Test checking building progress is monotonically increasing."""
        # Valid monotonic progress
        valid_data = {
            'game_loop': [0, 100, 200, 300],
            'timestamp_seconds': [0.0, 4.46, 8.93, 13.39],
            'p1_building_5001_progress': [0, 25, 75, 100],  # Monotonic
        }
        valid_parquet = create_mock_parquet('monotonic_progress.parquet', valid_data)

        report = validator.validate_game_state_parquet(valid_parquet)

        assert report['checks'].get('building_progress_monotonic', True) is True

    def test_detect_nonmonotonic_building_progress(self, validator, create_mock_parquet):
        """Test detecting building progress that decreases."""
        invalid_data = {
            'game_loop': [0, 100, 200, 300],
            'timestamp_seconds': [0.0, 4.46, 8.93, 13.39],
            'p1_building_5001_progress': [0, 50, 30, 100],  # Decreases from 50 to 30
        }
        invalid_parquet = create_mock_parquet('nonmonotonic_progress.parquet', invalid_data)

        report = validator.validate_game_state_parquet(invalid_parquet)

        assert report['valid'] is False
        assert report['checks']['building_progress_monotonic'] is False

    def test_validate_messages_parquet(self, validator, create_mock_parquet):
        """Test validating messages parquet."""
        messages_data = {
            'game_loop': [100, 200, 500],
            'player_id': [1, 2, 1],
            'message': ['glhf', 'u2', 'gg'],
        }
        messages_parquet = create_mock_parquet('messages.parquet', messages_data)

        report = validator.validate_messages_parquet(messages_parquet)

        assert report['valid'] is True
        assert report['checks']['required_columns'] is True
        assert report['checks']['has_messages'] is True
        assert report['stats']['total_messages'] == 3

    def test_validate_empty_messages(self, validator, create_mock_parquet):
        """Test validating empty messages file (no chat)."""
        empty_messages = create_mock_parquet('empty_messages.parquet', {
            'game_loop': [],
            'player_id': [],
            'message': [],
        })

        report = validator.validate_messages_parquet(empty_messages)

        # Empty messages is acceptable (no chat in game)
        assert report['valid'] is True
        assert report['checks']['has_messages'] is False
        assert 'acceptable' in str(report['warnings']).lower()

    def test_validate_messages_missing_file(self, validator, tmp_path):
        """Test validating missing messages file (optional)."""
        nonexistent = tmp_path / "missing_messages.parquet"

        report = validator.validate_messages_parquet(nonexistent)

        # Missing messages file is acceptable (generates warning, not error)
        assert 'optional' in str(report['warnings']).lower()

    def test_generate_validation_report_empty(self, validator):
        """Test generating report from empty validation list."""
        report = validator.generate_validation_report([])

        assert 'No validations performed' in report

    def test_generate_validation_report_single(self, validator):
        """Test generating report from single validation."""
        validations = [{
            'valid': True,
            'file_path': '/path/to/file.parquet',
            'errors': [],
            'warnings': [],
            'info': {'num_rows': 1000, 'num_columns': 50},
            'checks': {},
            'stats': {},
        }]

        report = validator.generate_validation_report(validations)

        assert 'Validation Report' in report
        assert 'PASS' in report
        assert '1000' in report  # Row count

    def test_generate_validation_report_with_errors(self, validator):
        """Test generating report with validation errors."""
        validations = [{
            'valid': False,
            'file_path': '/path/to/bad_file.parquet',
            'errors': ['Duplicate game_loops found', 'Negative minerals detected'],
            'warnings': ['High NaN rate'],
            'info': {'num_rows': 500},
            'checks': {},
            'stats': {},
        }]

        report = validator.generate_validation_report(validations)

        assert 'FAIL' in report
        assert 'Duplicate game_loops' in report
        assert 'Negative minerals' in report
        assert 'High NaN rate' in report

    def test_generate_validation_report_multiple(self, validator):
        """Test generating report from multiple validations."""
        validations = [
            {'valid': True, 'file_path': 'file1.parquet', 'errors': [],
             'warnings': [], 'info': {}, 'checks': {}, 'stats': {}},
            {'valid': False, 'file_path': 'file2.parquet', 'errors': ['Error'],
             'warnings': [], 'info': {}, 'checks': {}, 'stats': {}},
            {'valid': True, 'file_path': 'file3.parquet', 'errors': [],
             'warnings': ['Warning'], 'info': {}, 'checks': {}, 'stats': {}},
        ]

        report = validator.generate_validation_report(validations)

        assert '3' in report  # Total files
        assert '2' in report  # Valid files (2 out of 3)
        assert 'file1.parquet' in report
        assert 'file2.parquet' in report
        assert 'file3.parquet' in report

    def test_validation_includes_statistics(self, validator, valid_parquet):
        """Test that validation report includes data statistics."""
        report = validator.validate_game_state_parquet(valid_parquet)

        assert 'stats' in report
        assert 'total_rows' in report['stats']
        assert 'total_columns' in report['stats']
        assert 'game_loop_range' in report['stats']
        assert report['stats']['total_rows'] == 5

    def test_validation_report_includes_file_info(self, validator, valid_parquet):
        """Test that validation includes file metadata."""
        report = validator.validate_game_state_parquet(valid_parquet)

        assert 'info' in report
        assert 'num_rows' in report['info']
        assert 'num_columns' in report['info']
        assert 'file_size_kb' in report['info']
        assert report['info']['num_rows'] == 5
