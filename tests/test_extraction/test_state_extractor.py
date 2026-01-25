"""
Tests for StateExtractor component.

Tests the extraction of complete game state from pysc2 observations,
including units, buildings, economy, upgrades, and messages.
"""

import pytest
from unittest.mock import Mock, patch
from src_new.extraction.state_extractor import StateExtractor, UnitTracker, BuildingTracker


@pytest.mark.unit
@pytest.mark.extraction
class TestStateExtractor:
    """Test suite for StateExtractor class."""

    def test_initialization(self):
        """Test StateExtractor initializes correctly."""
        extractor = StateExtractor()

        assert extractor.unit_extractors is not None
        assert 1 in extractor.unit_extractors
        assert 2 in extractor.unit_extractors
        assert extractor.building_extractors is not None
        assert extractor.economy_extractors is not None
        assert extractor.upgrade_extractors is not None
        assert extractor.unit_tracker is not None
        assert extractor.building_tracker is not None

    def test_extract_observation_structure(self, mock_observation):
        """Test that extract_observation returns correct structure."""
        extractor = StateExtractor()

        with patch.object(extractor, 'extract_units', return_value={}), \
             patch.object(extractor, 'extract_buildings', return_value={}), \
             patch.object(extractor, 'extract_economy', return_value={}), \
             patch.object(extractor, 'extract_upgrades', return_value={}), \
             patch.object(extractor, 'extract_messages', return_value=[]):

            state = extractor.extract_observation(mock_observation, game_loop=100)

            # Check structure
            assert 'game_loop' in state
            assert state['game_loop'] == 100
            assert 'p1_units' in state
            assert 'p2_units' in state
            assert 'p1_buildings' in state
            assert 'p2_buildings' in state
            assert 'p1_economy' in state
            assert 'p2_economy' in state
            assert 'p1_upgrades' in state
            assert 'p2_upgrades' in state
            assert 'messages' in state

    def test_extract_observation_calls_extractors(self, mock_observation):
        """Test that extract_observation calls all component extractors."""
        extractor = StateExtractor()

        # Mock the extractors
        with patch.object(extractor, 'extract_units', return_value={}) as mock_units, \
             patch.object(extractor, 'extract_buildings', return_value={}) as mock_buildings, \
             patch.object(extractor, 'extract_economy', return_value={}) as mock_economy, \
             patch.object(extractor, 'extract_upgrades', return_value={}) as mock_upgrades, \
             patch.object(extractor, 'extract_messages', return_value=[]) as mock_messages:

            extractor.extract_observation(mock_observation, game_loop=100)

            # Verify each extractor was called for both players
            assert mock_units.call_count == 2  # Called for p1 and p2
            assert mock_buildings.call_count == 2
            assert mock_economy.call_count == 2
            assert mock_upgrades.call_count == 2
            assert mock_messages.call_count == 1

    def test_reset_clears_state(self):
        """Test that reset() clears all internal state."""
        extractor = StateExtractor()

        # Mock the component extractors
        with patch.object(extractor.unit_extractors[1], 'reset') as mock_u1_reset, \
             patch.object(extractor.unit_extractors[2], 'reset') as mock_u2_reset, \
             patch.object(extractor.building_extractors[1], 'reset') as mock_b1_reset, \
             patch.object(extractor.unit_tracker, 'reset') as mock_ut_reset:

            extractor.reset()

            # Verify all reset methods were called
            mock_u1_reset.assert_called_once()
            mock_u2_reset.assert_called_once()
            mock_b1_reset.assert_called_once()
            mock_ut_reset.assert_called_once()


@pytest.mark.unit
@pytest.mark.extraction
class TestUnitTracker:
    """Test suite for UnitTracker class."""

    def test_initialization(self):
        """Test UnitTracker initializes with empty state."""
        tracker = UnitTracker()

        assert tracker.unit_registry == {}
        assert tracker.unit_counters == {}
        assert tracker.previous_frame_tags == set()

    def test_assign_unit_id_new_unit(self):
        """Test assigning ID to a new unit."""
        tracker = UnitTracker()

        unit_id = tracker.assign_unit_id(tag=1000, unit_type=48)

        assert unit_id == "unit_48_001"
        assert 1000 in tracker.unit_registry
        assert tracker.unit_counters[48] == 2  # Next ID will be 2

    def test_assign_unit_id_existing_unit(self):
        """Test assigning ID to an existing unit returns same ID."""
        tracker = UnitTracker()

        # First assignment
        id1 = tracker.assign_unit_id(tag=1000, unit_type=48)
        # Second assignment (same tag)
        id2 = tracker.assign_unit_id(tag=1000, unit_type=48)

        assert id1 == id2
        assert id1 == "unit_48_001"

    def test_assign_unit_id_increments_counter(self):
        """Test that IDs increment for each new unit of same type."""
        tracker = UnitTracker()

        id1 = tracker.assign_unit_id(tag=1000, unit_type=48)
        id2 = tracker.assign_unit_id(tag=1001, unit_type=48)
        id3 = tracker.assign_unit_id(tag=1002, unit_type=48)

        assert id1 == "unit_48_001"
        assert id2 == "unit_48_002"
        assert id3 == "unit_48_003"

    def test_detect_state_new_unit(self):
        """Test detecting state for a new unit."""
        tracker = UnitTracker()
        tracker.previous_frame_tags = set()

        state = tracker.detect_state(tag=1000, current_tags={1000})

        assert state == 'built'

    def test_detect_state_existing_unit(self):
        """Test detecting state for an existing unit."""
        tracker = UnitTracker()
        tracker.previous_frame_tags = {1000}

        state = tracker.detect_state(tag=1000, current_tags={1000})

        assert state == 'existing'

    def test_process_units_empty(self):
        """Test processing empty unit list."""
        tracker = UnitTracker()

        tracked = tracker.process_units([], game_loop=0)

        assert tracked == {}

    def test_process_units_detects_new_units(self):
        """Test that process_units detects newly created units."""
        tracker = UnitTracker()

        # Create mock unit
        mock_unit = Mock()
        mock_unit.tag = 1000
        mock_unit.unit_type = 48
        mock_unit.pos = Mock(x=30.0, y=30.0, z=8.0)

        tracked = tracker.process_units([mock_unit], game_loop=0)

        assert len(tracked) == 1
        unit_id = list(tracked.keys())[0]
        assert tracked[unit_id]['state'] == 'built'
        assert tracked[unit_id]['tag'] == 1000

    def test_process_units_detects_killed_units(self):
        """Test that process_units detects killed units."""
        tracker = UnitTracker()

        # First frame - unit exists
        mock_unit = Mock()
        mock_unit.tag = 1000
        mock_unit.unit_type = 48
        mock_unit.pos = Mock(x=30.0, y=30.0, z=8.0)

        tracker.process_units([mock_unit], game_loop=0)

        # Second frame - unit is gone
        tracked = tracker.process_units([], game_loop=100)

        # Should have one entry for the killed unit
        assert len(tracked) == 1
        unit_id = list(tracked.keys())[0]
        assert tracked[unit_id]['state'] == 'killed'
        assert tracked[unit_id]['tag'] == 1000

    def test_reset(self):
        """Test that reset clears all tracking state."""
        tracker = UnitTracker()

        # Add some state
        tracker.assign_unit_id(tag=1000, unit_type=48)
        tracker.previous_frame_tags = {1000}

        # Reset
        tracker.reset()

        # Verify cleared
        assert tracker.unit_registry == {}
        assert tracker.unit_counters == {}
        assert tracker.previous_frame_tags == set()


@pytest.mark.unit
@pytest.mark.extraction
class TestBuildingTracker:
    """Test suite for BuildingTracker class."""

    def test_initialization(self):
        """Test BuildingTracker initializes with empty state."""
        tracker = BuildingTracker()

        assert tracker.building_registry == {}
        assert tracker.previous_frame_tags == set()

    def test_process_buildings_empty(self):
        """Test processing empty building list."""
        tracker = BuildingTracker()

        tracked = tracker.process_buildings([], game_loop=0)

        assert tracked == {}

    def test_process_buildings_new_building(self):
        """Test tracking a new building."""
        tracker = BuildingTracker()

        # Create mock building
        mock_building = Mock()
        mock_building.tag = 5000
        mock_building.unit_type = 21  # Barracks
        mock_building.pos = Mock(x=40.0, y=40.0, z=8.0)
        mock_building.build_progress = 0.0

        tracked = tracker.process_buildings([mock_building], game_loop=0)

        assert len(tracked) == 1
        building_id = 'building_5000'
        assert building_id in tracked
        assert tracked[building_id]['status'] == 'started'
        assert tracked[building_id]['progress'] == 0
        assert tracked[building_id]['started_loop'] == 0

    def test_process_buildings_construction_progress(self):
        """Test tracking building construction progress."""
        tracker = BuildingTracker()

        # Frame 0: Building starts
        mock_building = Mock()
        mock_building.tag = 5000
        mock_building.unit_type = 21
        mock_building.pos = Mock(x=40.0, y=40.0, z=8.0)
        mock_building.build_progress = 0.0

        tracker.process_buildings([mock_building], game_loop=0)

        # Frame 500: Building in progress
        mock_building.build_progress = 0.5
        tracked = tracker.process_buildings([mock_building], game_loop=500)

        building_id = 'building_5000'
        assert tracked[building_id]['status'] == 'building'
        assert tracked[building_id]['progress'] == 50

    def test_process_buildings_completion(self):
        """Test detecting building completion."""
        tracker = BuildingTracker()

        # Start building
        mock_building = Mock()
        mock_building.tag = 5000
        mock_building.unit_type = 21
        mock_building.pos = Mock(x=40.0, y=40.0, z=8.0)
        mock_building.build_progress = 0.0

        tracker.process_buildings([mock_building], game_loop=0)

        # Complete building
        mock_building.build_progress = 1.0
        tracked = tracker.process_buildings([mock_building], game_loop=1000)

        building_id = 'building_5000'
        assert tracked[building_id]['status'] == 'completed'
        assert tracked[building_id]['progress'] == 100
        assert tracked[building_id]['completed_loop'] == 1000

    def test_process_buildings_destruction(self):
        """Test detecting building destruction."""
        tracker = BuildingTracker()

        # Frame 0: Building exists
        mock_building = Mock()
        mock_building.tag = 5000
        mock_building.unit_type = 21
        mock_building.pos = Mock(x=40.0, y=40.0, z=8.0)
        mock_building.build_progress = 1.0

        tracker.process_buildings([mock_building], game_loop=0)

        # Frame 1000: Building destroyed
        tracked = tracker.process_buildings([], game_loop=1000)

        building_id = 'building_5000'
        assert building_id in tracked
        assert tracked[building_id]['status'] == 'destroyed'
        assert tracked[building_id]['destroyed_loop'] == 1000

    def test_reset(self):
        """Test that reset clears all tracking state."""
        tracker = BuildingTracker()

        # Add some state
        mock_building = Mock()
        mock_building.tag = 5000
        mock_building.unit_type = 21
        mock_building.pos = Mock(x=40.0, y=40.0, z=8.0)
        mock_building.build_progress = 0.5

        tracker.process_buildings([mock_building], game_loop=0)

        # Reset
        tracker.reset()

        # Verify cleared
        assert tracker.building_registry == {}
        assert tracker.previous_frame_tags == set()


@pytest.mark.unit
@pytest.mark.extraction
class TestStateExtractorIntegration:
    """Integration tests for StateExtractor with mock observations."""

    def test_extract_from_mock_observation_sequence(self, mock_observation_sequence):
        """Test extracting state from a sequence of observations."""
        extractor = StateExtractor()
        states = []

        for obs in mock_observation_sequence:
            state = extractor.extract_observation(obs, obs.observation.game_loop)
            states.append(state)

        # Verify we got states for all frames
        assert len(states) == len(mock_observation_sequence)

        # Verify game loops are correct
        assert states[0]['game_loop'] == 0
        assert states[1]['game_loop'] == 100
        assert states[2]['game_loop'] == 200
        assert states[3]['game_loop'] == 300

    def test_extract_messages(self):
        """Test extracting chat messages from observation."""
        extractor = StateExtractor()

        # Create observation with messages
        obs = Mock()
        obs.observation = Mock()
        obs.observation.game_loop = 1000
        obs.observation.chat = []

        # Add mock messages
        msg1 = Mock()
        msg1.player_id = 1
        msg1.message = "glhf"
        obs.observation.chat.append(msg1)

        msg2 = Mock()
        msg2.player_id = 2
        msg2.message = "u2"
        obs.observation.chat.append(msg2)

        messages = extractor.extract_messages(obs)

        assert len(messages) == 2
        assert messages[0]['player_id'] == 1
        assert messages[0]['message'] == "glhf"
        assert messages[0]['game_loop'] == 1000
        assert messages[1]['player_id'] == 2
        assert messages[1]['message'] == "u2"

    def test_extract_no_messages(self, mock_observation):
        """Test extracting when there are no messages."""
        extractor = StateExtractor()

        messages = extractor.extract_messages(mock_observation)

        assert messages == []
