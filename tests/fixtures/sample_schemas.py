"""
Sample schema configurations for testing.

Provides realistic schema definitions and column lists.
"""

from typing import List, Dict, Any


def create_minimal_schema_columns() -> List[str]:
    """
    Create a minimal schema with base columns only.

    Returns:
        List of column names
    """
    return [
        # Base columns
        'game_loop',
        'timestamp_seconds',

        # Player 1 economy
        'p1_minerals',
        'p1_vespene',
        'p1_supply_used',
        'p1_supply_cap',
        'p1_workers',
        'p1_idle_workers',

        # Player 2 economy
        'p2_minerals',
        'p2_vespene',
        'p2_supply_used',
        'p2_supply_cap',
        'p2_workers',
        'p2_idle_workers',

        # Player 1 upgrades
        'p1_upgrade_attack_level',
        'p1_upgrade_armor_level',
        'p1_upgrade_shield_level',

        # Player 2 upgrades
        'p2_upgrade_attack_level',
        'p2_upgrade_armor_level',
        'p2_upgrade_shield_level',
    ]


def create_schema_with_units() -> List[str]:
    """
    Create a schema with units included.

    Returns:
        List of column names including unit columns
    """
    columns = create_minimal_schema_columns()

    # Add unit columns for P1
    unit_attrs = ['x', 'y', 'z', 'health', 'health_max', 'shields', 'shields_max',
                  'energy', 'energy_max', 'state']

    # Add marine columns
    for attr in unit_attrs:
        columns.append(f'p1_marine_001_{attr}')

    # Add unit count columns
    columns.append('p1_marine_count')
    columns.append('p2_marine_count')

    return columns


def create_full_schema() -> List[str]:
    """
    Create a full schema with units, buildings, and all attributes.

    Returns:
        Comprehensive list of column names
    """
    columns = create_minimal_schema_columns()

    # Unit attributes
    unit_attrs = [
        'x', 'y', 'z', 'facing',
        'health', 'health_max',
        'shields', 'shields_max',
        'energy', 'energy_max',
        'state', 'build_progress',
        'is_flying', 'is_burrowed', 'is_hallucination',
        'weapon_cooldown',
        'attack_upgrade_level', 'armor_upgrade_level', 'shield_upgrade_level',
        'radius', 'cargo_space_taken', 'cargo_space_max', 'order_count',
    ]

    # Add P1 units
    for unit_id in ['marine_001', 'marine_002', 'scv_001']:
        for attr in unit_attrs:
            columns.append(f'p1_{unit_id}_{attr}')

    # Add P2 units
    for unit_id in ['zealot_001', 'probe_001']:
        for attr in unit_attrs:
            columns.append(f'p2_{unit_id}_{attr}')

    # Building attributes
    building_attrs = [
        'x', 'y', 'z',
        'status', 'progress',
        'started_loop', 'completed_loop', 'destroyed_loop',
    ]

    # Add P1 buildings
    for building_id in ['building_5001', 'building_5002']:
        for attr in building_attrs:
            columns.append(f'p1_{building_id}_{attr}')

    # Add P2 buildings
    for building_id in ['building_6001']:
        for attr in building_attrs:
            columns.append(f'p2_{building_id}_{attr}')

    # Unit counts
    unit_types = ['marine', 'scv', 'marauder', 'zealot', 'probe', 'stalker']
    for player in [1, 2]:
        for unit_type in unit_types:
            columns.append(f'p{player}_{unit_type}_count')

    return columns


def create_schema_documentation() -> Dict[str, Dict[str, Any]]:
    """
    Create sample schema documentation.

    Returns:
        Dictionary mapping column names to metadata
    """
    return {
        'game_loop': {
            'description': 'Game loop number (22.4 loops per second)',
            'type': 'int64',
            'example': 1000,
            'missing_value': None,
        },
        'timestamp_seconds': {
            'description': 'Game time in seconds (game_loop / 22.4)',
            'type': 'float64',
            'example': 44.64,
            'missing_value': None,
        },
        'p1_minerals': {
            'description': 'Player 1 mineral count',
            'type': 'int64',
            'example': 250,
            'missing_value': 0,
        },
        'p1_vespene': {
            'description': 'Player 1 vespene gas count',
            'type': 'int64',
            'example': 100,
            'missing_value': 0,
        },
        'p1_supply_used': {
            'description': 'Player 1 supply/food used',
            'type': 'int64',
            'example': 45,
            'missing_value': 0,
        },
        'p1_supply_cap': {
            'description': 'Player 1 supply/food cap',
            'type': 'int64',
            'example': 46,
            'missing_value': 0,
        },
        'p1_marine_001_x': {
            'description': 'X-coordinate of player 1 marine #1',
            'type': 'float64',
            'example': 50.5,
            'missing_value': 'NaN',
        },
        'p1_marine_001_y': {
            'description': 'Y-coordinate of player 1 marine #1',
            'type': 'float64',
            'example': 30.2,
            'missing_value': 'NaN',
        },
        'p1_marine_001_health': {
            'description': 'Current health of player 1 marine #1',
            'type': 'float64',
            'example': 35.0,
            'missing_value': 'NaN',
        },
        'p1_marine_001_state': {
            'description': 'State of player 1 marine #1 (built/existing/killed)',
            'type': 'string',
            'example': 'existing',
            'missing_value': 'NaN',
        },
        'p1_marine_count': {
            'description': 'Total number of active marines for player 1',
            'type': 'int64',
            'example': 10,
            'missing_value': 0,
        },
    }


def create_schema_config() -> Dict[str, Any]:
    """
    Create a sample schema configuration.

    Returns:
        Schema configuration dictionary
    """
    return {
        'version': '1.0.0',
        'game_version': '5.0.10',
        'extraction_date': '2024-01-25',
        'column_count': 150,
        'base_columns': 14,
        'unit_columns': 100,
        'building_columns': 30,
        'missing_value_indicators': {
            'numeric': float('nan'),
            'string': None,
            'int': -1,
        },
        'data_types': {
            'coordinates': 'float64',
            'vitals': 'float64',
            'resources': 'int64',
            'counts': 'int64',
            'states': 'string',
            'timestamps': 'int64',
        },
    }


def create_invalid_schema() -> List[str]:
    """
    Create an intentionally invalid schema for error testing.

    Returns:
        Schema with issues (duplicate columns, invalid names)
    """
    return [
        'game_loop',
        'game_loop',  # Duplicate
        'p1_minerals',
        'invalid column name with spaces',  # Invalid
        'p1_unit_@#$_x',  # Invalid characters
        '',  # Empty string
    ]
