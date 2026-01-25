"""
Pytest configuration and shared fixtures for SC2 Replay Extraction Pipeline tests.

This module provides:
- Mock pysc2 observation structures
- Temporary directory fixtures
- Sample data fixtures
- Test configuration
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock, Mock
import pandas as pd
import numpy as np


# ============================================================================
# Session-level fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Create a temporary directory for test data that persists for the session."""
    temp_dir = Path(tempfile.mkdtemp(prefix="sc2_test_"))
    yield temp_dir
    # Cleanup after all tests
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture(scope="session")
def sample_replay_path(test_data_dir) -> Path:
    """Create a fake replay path for testing (file doesn't actually exist)."""
    replay_path = test_data_dir / "sample_game.SC2Replay"
    # Don't create the file - tests should mock the loading
    return replay_path


# ============================================================================
# Function-level fixtures
# ============================================================================

@pytest.fixture
def temp_output_dir(tmp_path) -> Path:
    """Create a temporary output directory for test artifacts."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Sample configuration dictionary for pipeline components."""
    return {
        'show_cloaked': True,
        'show_burrowed_shadows': True,
        'show_placeholders': True,
        'processing_mode': 'two_pass',
        'step_size': 1,
        'compression': 'snappy',
        'output_format': 'standard',
    }


# ============================================================================
# Mock pysc2 observation fixtures
# ============================================================================

class MockUnit:
    """Mock SC2 unit for testing."""

    def __init__(
        self,
        tag: int,
        unit_type: int,
        owner: int,
        x: float = 50.0,
        y: float = 50.0,
        z: float = 8.0,
        health: float = 100.0,
        health_max: float = 100.0,
        shield: float = 0.0,
        shield_max: float = 0.0,
        energy: float = 0.0,
        energy_max: float = 0.0,
        build_progress: float = 1.0,
        **kwargs
    ):
        self.tag = tag
        self.unit_type = unit_type
        self.owner = owner

        # Position
        self.pos = Mock()
        self.pos.x = x
        self.pos.y = y
        self.pos.z = z
        self.facing = kwargs.get('facing', 0.0)

        # Vitals
        self.health = health
        self.health_max = health_max
        self.shield = shield
        self.shield_max = shield_max
        self.energy = energy
        self.energy_max = energy_max

        # State
        self.build_progress = build_progress
        self.is_flying = kwargs.get('is_flying', False)
        self.is_burrowed = kwargs.get('is_burrowed', False)
        self.is_hallucination = kwargs.get('is_hallucination', False)

        # Combat
        self.weapon_cooldown = kwargs.get('weapon_cooldown', 0.0)
        self.attack_upgrade_level = kwargs.get('attack_upgrade_level', 0)
        self.armor_upgrade_level = kwargs.get('armor_upgrade_level', 0)
        self.shield_upgrade_level = kwargs.get('shield_upgrade_level', 0)

        # Additional
        self.radius = kwargs.get('radius', 0.5)
        self.cargo_space_taken = kwargs.get('cargo_space_taken', 0)
        self.cargo_space_max = kwargs.get('cargo_space_max', 0)
        self.orders = kwargs.get('orders', [])


class MockRawData:
    """Mock raw data from SC2 observation."""

    def __init__(self, units: List[MockUnit] = None, player_minerals: int = 50,
                 player_vespene: int = 0):
        self.units = units or []

        # Player resources
        self.player = Mock()
        self.player.minerals = player_minerals
        self.player.vespene = player_vespene
        self.player.food_used = 12
        self.player.food_cap = 15
        self.player.food_army = 6
        self.player.food_workers = 6
        self.player.idle_worker_count = 0
        self.player.army_count = 3
        self.player.warp_gate_count = 0
        self.player.larva_count = 0

        # Event data
        self.event = Mock()
        self.event.dead_units = []


class MockObservation:
    """Mock SC2 observation for testing."""

    def __init__(
        self,
        game_loop: int = 0,
        units: List[MockUnit] = None,
        player_minerals: int = 50,
        player_vespene: int = 0
    ):
        self.observation = Mock()
        self.observation.game_loop = game_loop
        self.observation.raw_data = MockRawData(units, player_minerals, player_vespene)
        self.observation.chat = []
        self.observation.player_common = Mock()
        self.observation.player_common.player_id = 1


@pytest.fixture
def mock_observation() -> MockObservation:
    """Create a basic mock observation with a few units."""
    units = [
        MockUnit(tag=1000, unit_type=48, owner=1, x=30.0, y=30.0),  # Marine
        MockUnit(tag=1001, unit_type=48, owner=1, x=32.0, y=30.0),  # Marine
        MockUnit(tag=1002, unit_type=45, owner=1, x=35.0, y=35.0),  # SCV
    ]
    return MockObservation(game_loop=100, units=units)


@pytest.fixture
def mock_observation_sequence() -> List[MockObservation]:
    """Create a sequence of mock observations showing unit lifecycle."""
    observations = []

    # Frame 0: Initial units
    units_frame_0 = [
        MockUnit(tag=1000, unit_type=48, owner=1, x=30.0, y=30.0),  # Marine
    ]
    observations.append(MockObservation(game_loop=0, units=units_frame_0))

    # Frame 100: New unit appears
    units_frame_100 = [
        MockUnit(tag=1000, unit_type=48, owner=1, x=31.0, y=30.0),  # Marine (moved)
        MockUnit(tag=1001, unit_type=48, owner=1, x=32.0, y=30.0, build_progress=0.5),  # Marine (building)
    ]
    observations.append(MockObservation(game_loop=100, units=units_frame_100))

    # Frame 200: Unit completed
    units_frame_200 = [
        MockUnit(tag=1000, unit_type=48, owner=1, x=32.0, y=30.0),  # Marine
        MockUnit(tag=1001, unit_type=48, owner=1, x=32.0, y=30.0),  # Marine (completed)
    ]
    observations.append(MockObservation(game_loop=200, units=units_frame_200))

    # Frame 300: Unit dies
    units_frame_300 = [
        MockUnit(tag=1001, unit_type=48, owner=1, x=32.0, y=30.0),  # Marine (survivor)
    ]
    obs_300 = MockObservation(game_loop=300, units=units_frame_300)
    obs_300.observation.raw_data.event.dead_units = [1000]  # First marine died
    observations.append(obs_300)

    return observations


# ============================================================================
# Sample data fixtures
# ============================================================================

@pytest.fixture
def sample_extracted_state() -> Dict[str, Any]:
    """Sample extracted state dictionary from StateExtractor."""
    return {
        'game_loop': 100,
        'p1_units': {
            'p1_marine_001': {
                'tag': 1000,
                'unit_type_id': 48,
                'unit_type_name': 'Marine',
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
            },
        },
        'p2_units': {},
        'p1_buildings': {},
        'p2_buildings': {},
        'p1_economy': {
            'minerals': 150,
            'vespene': 50,
            'supply_used': 12,
            'supply_cap': 15,
            'workers': 6,
            'idle_workers': 0,
        },
        'p2_economy': {
            'minerals': 200,
            'vespene': 75,
            'supply_used': 10,
            'supply_cap': 15,
            'workers': 8,
            'idle_workers': 1,
        },
        'p1_upgrades': {
            'attack_level': 0,
            'armor_level': 0,
            'shield_level': 0,
        },
        'p2_upgrades': {
            'attack_level': 1,
            'armor_level': 0,
            'shield_level': 0,
        },
        'messages': [],
    }


@pytest.fixture
def sample_wide_row() -> Dict[str, Any]:
    """Sample wide-format row from WideTableBuilder."""
    return {
        'game_loop': 100,
        'timestamp_seconds': 4.464,  # 100 / 22.4
        'p1_minerals': 150,
        'p1_vespene': 50,
        'p1_supply_used': 12,
        'p1_supply_cap': 15,
        'p2_minerals': 200,
        'p2_vespene': 75,
        'p2_supply_used': 10,
        'p2_supply_cap': 15,
        'p1_marine_001_x': 30.0,
        'p1_marine_001_y': 30.0,
        'p1_marine_001_z': 8.0,
        'p1_marine_001_health': 45.0,
        'p1_marine_001_state': 'existing',
    }


@pytest.fixture
def sample_parquet_dataframe() -> pd.DataFrame:
    """Sample DataFrame for parquet writing tests."""
    data = {
        'game_loop': [0, 100, 200, 300],
        'timestamp_seconds': [0.0, 4.464, 8.929, 13.393],
        'p1_minerals': [50, 150, 250, 300],
        'p1_vespene': [0, 50, 100, 150],
        'p1_supply_used': [12, 12, 15, 18],
        'p1_supply_cap': [15, 15, 23, 23],
        'p2_minerals': [50, 200, 300, 400],
        'p2_vespene': [0, 75, 125, 175],
        'p1_marine_001_x': [30.0, 30.5, 31.0, np.nan],  # Marine dies at frame 300
        'p1_marine_001_health': [45.0, 40.0, 35.0, np.nan],
    }
    return pd.DataFrame(data)


# ============================================================================
# Mock schema fixtures
# ============================================================================

@pytest.fixture
def sample_schema_columns() -> List[str]:
    """Sample schema column list."""
    return [
        'game_loop',
        'timestamp_seconds',
        'p1_minerals',
        'p1_vespene',
        'p1_supply_used',
        'p1_supply_cap',
        'p1_workers',
        'p1_idle_workers',
        'p2_minerals',
        'p2_vespene',
        'p2_supply_used',
        'p2_supply_cap',
        'p2_workers',
        'p2_idle_workers',
        'p1_marine_001_x',
        'p1_marine_001_y',
        'p1_marine_001_z',
        'p1_marine_001_health',
        'p1_marine_001_health_max',
        'p1_marine_001_shields',
        'p1_marine_001_shields_max',
        'p1_marine_001_energy',
        'p1_marine_001_energy_max',
        'p1_marine_001_state',
    ]


# ============================================================================
# Helper utilities
# ============================================================================

@pytest.fixture
def assert_parquet_valid():
    """Helper function to validate parquet files."""
    def _validate(parquet_path: Path) -> bool:
        """Check if parquet file is valid and readable."""
        if not parquet_path.exists():
            return False

        try:
            df = pd.read_parquet(parquet_path)
            return len(df) > 0
        except Exception:
            return False

    return _validate


@pytest.fixture
def create_mock_parquet(temp_output_dir):
    """Helper to create mock parquet files for testing."""
    def _create(filename: str, data: Dict[str, list]) -> Path:
        """Create a parquet file with given data."""
        df = pd.DataFrame(data)
        output_path = temp_output_dir / filename
        df.to_parquet(output_path, compression='snappy', index=False)
        return output_path

    return _create
