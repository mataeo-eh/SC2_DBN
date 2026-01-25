"""
Sample extracted game state data for testing.

Provides realistic game state dictionaries that would be output by StateExtractor.
"""

from typing import Dict, Any, List


def create_sample_game_state(game_loop: int = 100) -> Dict[str, Any]:
    """
    Create a sample game state dictionary.

    Args:
        game_loop: Game loop number

    Returns:
        Game state dictionary as output by StateExtractor
    """
    return {
        'game_loop': game_loop,
        'p1_units': {
            'p1_marine_001': {
                'tag': 1000,
                'unit_type_id': 48,
                'unit_type_name': 'Marine',
                'x': 30.0,
                'y': 30.0,
                'z': 8.0,
                'facing': 0.0,
                'health': 45.0,
                'health_max': 45.0,
                'shields': 0.0,
                'shields_max': 0.0,
                'energy': 0.0,
                'energy_max': 0.0,
                'state': 'existing',
                'build_progress': 1.0,
                'is_flying': False,
                'is_burrowed': False,
                'is_hallucination': False,
                'weapon_cooldown': 0.0,
                'attack_upgrade_level': 0,
                'armor_upgrade_level': 0,
                'shield_upgrade_level': 0,
                'radius': 0.5,
                'cargo_space_taken': 0,
                'cargo_space_max': 0,
                'order_count': 0,
            },
        },
        'p2_units': {
            'p2_zealot_001': {
                'tag': 2000,
                'unit_type_id': 73,
                'unit_type_name': 'Zealot',
                'x': 130.0,
                'y': 130.0,
                'z': 8.0,
                'facing': 3.14,
                'health': 100.0,
                'health_max': 100.0,
                'shields': 50.0,
                'shields_max': 50.0,
                'energy': 0.0,
                'energy_max': 0.0,
                'state': 'existing',
                'build_progress': 1.0,
                'is_flying': False,
                'is_burrowed': False,
                'is_hallucination': False,
                'weapon_cooldown': 0.0,
                'attack_upgrade_level': 0,
                'armor_upgrade_level': 0,
                'shield_upgrade_level': 0,
                'radius': 0.5,
                'cargo_space_taken': 0,
                'cargo_space_max': 0,
                'order_count': 1,
            },
        },
        'p1_buildings': {
            'building_5001': {
                'tag': 5001,
                'building_type': 21,
                'x': 40.0,
                'y': 40.0,
                'z': 8.0,
                'status': 'completed',
                'progress': 100,
                'started_loop': 0,
                'completed_loop': 500,
                'destroyed_loop': None,
                'game_loop': game_loop,
            },
        },
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


def create_game_state_with_killed_unit() -> Dict[str, Any]:
    """Create a game state showing a killed unit."""
    state = create_sample_game_state(game_loop=500)
    state['p1_units']['p1_marine_002'] = {
        'tag': 1001,
        'state': 'killed',
    }
    return state


def create_game_state_with_new_unit() -> Dict[str, Any]:
    """Create a game state showing a newly built unit."""
    state = create_sample_game_state(game_loop=500)
    state['p1_units']['p1_marine_002'] = {
        'tag': 1001,
        'unit_type_id': 48,
        'unit_type_name': 'Marine',
        'x': 32.0,
        'y': 30.0,
        'z': 8.0,
        'facing': 0.0,
        'health': 45.0,
        'health_max': 45.0,
        'shields': 0.0,
        'shields_max': 0.0,
        'energy': 0.0,
        'energy_max': 0.0,
        'state': 'built',  # Newly created
        'build_progress': 1.0,
        'is_flying': False,
        'is_burrowed': False,
        'is_hallucination': False,
        'weapon_cooldown': 0.0,
        'attack_upgrade_level': 0,
        'armor_upgrade_level': 0,
        'shield_upgrade_level': 0,
        'radius': 0.5,
        'cargo_space_taken': 0,
        'cargo_space_max': 0,
        'order_count': 0,
    }
    return state


def create_game_state_sequence() -> List[Dict[str, Any]]:
    """Create a sequence of game states showing progression."""
    states = []

    # Frame 0: Initial state
    states.append(create_sample_game_state(game_loop=0))

    # Frame 500: Unit built
    states.append(create_game_state_with_new_unit())

    # Frame 1000: Unit killed
    states.append(create_game_state_with_killed_unit())

    return states


def create_empty_game_state(game_loop: int = 0) -> Dict[str, Any]:
    """Create an empty game state (game start)."""
    return {
        'game_loop': game_loop,
        'p1_units': {},
        'p2_units': {},
        'p1_buildings': {},
        'p2_buildings': {},
        'p1_economy': {
            'minerals': 50,
            'vespene': 0,
            'supply_used': 12,
            'supply_cap': 15,
            'workers': 12,
            'idle_workers': 0,
        },
        'p2_economy': {
            'minerals': 50,
            'vespene': 0,
            'supply_used': 12,
            'supply_cap': 15,
            'workers': 12,
            'idle_workers': 0,
        },
        'p1_upgrades': {
            'attack_level': 0,
            'armor_level': 0,
            'shield_level': 0,
        },
        'p2_upgrades': {
            'attack_level': 0,
            'armor_level': 0,
            'shield_level': 0,
        },
        'messages': [],
    }


def create_game_state_with_messages() -> Dict[str, Any]:
    """Create a game state with chat messages."""
    state = create_sample_game_state(game_loop=1000)
    state['messages'] = [
        {
            'game_loop': 1000,
            'player_id': 1,
            'message': 'glhf',
        },
        {
            'game_loop': 1000,
            'player_id': 2,
            'message': 'u2',
        },
    ]
    return state


def create_complex_game_state() -> Dict[str, Any]:
    """
    Create a complex game state with multiple unit types.

    Useful for testing schema building and wide table conversion.
    """
    return {
        'game_loop': 2000,
        'p1_units': {
            'p1_marine_001': {
                'tag': 1001,
                'unit_type_id': 48,
                'unit_type_name': 'Marine',
                'x': 30.0, 'y': 30.0, 'z': 8.0,
                'health': 45.0, 'health_max': 45.0,
                'shields': 0.0, 'shields_max': 0.0,
                'energy': 0.0, 'energy_max': 0.0,
                'state': 'existing',
            },
            'p1_marine_002': {
                'tag': 1002,
                'unit_type_id': 48,
                'unit_type_name': 'Marine',
                'x': 31.0, 'y': 30.0, 'z': 8.0,
                'health': 40.0, 'health_max': 45.0,
                'shields': 0.0, 'shields_max': 0.0,
                'energy': 0.0, 'energy_max': 0.0,
                'state': 'existing',
            },
            'p1_marauder_001': {
                'tag': 1003,
                'unit_type_id': 51,
                'unit_type_name': 'Marauder',
                'x': 32.0, 'y': 30.0, 'z': 8.0,
                'health': 125.0, 'health_max': 125.0,
                'shields': 0.0, 'shields_max': 0.0,
                'energy': 0.0, 'energy_max': 0.0,
                'state': 'existing',
            },
            'p1_scv_001': {
                'tag': 1004,
                'unit_type_id': 45,
                'unit_type_name': 'SCV',
                'x': 25.0, 'y': 25.0, 'z': 8.0,
                'health': 45.0, 'health_max': 45.0,
                'shields': 0.0, 'shields_max': 0.0,
                'energy': 0.0, 'energy_max': 0.0,
                'state': 'existing',
            },
        },
        'p2_units': {
            'p2_zealot_001': {
                'tag': 2001,
                'unit_type_id': 73,
                'unit_type_name': 'Zealot',
                'x': 130.0, 'y': 130.0, 'z': 8.0,
                'health': 100.0, 'health_max': 100.0,
                'shields': 50.0, 'shields_max': 50.0,
                'energy': 0.0, 'energy_max': 0.0,
                'state': 'existing',
            },
            'p2_zealot_002': {
                'tag': 2002,
                'unit_type_id': 73,
                'unit_type_name': 'Zealot',
                'x': 131.0, 'y': 130.0, 'z': 8.0,
                'health': 80.0, 'health_max': 100.0,
                'shields': 30.0, 'shields_max': 50.0,
                'energy': 0.0, 'energy_max': 0.0,
                'state': 'existing',
            },
            'p2_probe_001': {
                'tag': 2003,
                'unit_type_id': 84,
                'unit_type_name': 'Probe',
                'x': 125.0, 'y': 125.0, 'z': 8.0,
                'health': 20.0, 'health_max': 20.0,
                'shields': 20.0, 'shields_max': 20.0,
                'energy': 0.0, 'energy_max': 0.0,
                'state': 'existing',
            },
        },
        'p1_buildings': {
            'building_5001': {
                'tag': 5001, 'building_type': 18,
                'x': 28.0, 'y': 28.0, 'z': 8.0,
                'status': 'completed', 'progress': 100,
                'started_loop': 0, 'completed_loop': 100, 'destroyed_loop': None,
                'game_loop': 2000,
            },
            'building_5002': {
                'tag': 5002, 'building_type': 21,
                'x': 35.0, 'y': 35.0, 'z': 8.0,
                'status': 'completed', 'progress': 100,
                'started_loop': 500, 'completed_loop': 1000, 'destroyed_loop': None,
                'game_loop': 2000,
            },
        },
        'p2_buildings': {
            'building_6001': {
                'tag': 6001, 'building_type': 59,
                'x': 128.0, 'y': 128.0, 'z': 8.0,
                'status': 'completed', 'progress': 100,
                'started_loop': 0, 'completed_loop': 100, 'destroyed_loop': None,
                'game_loop': 2000,
            },
        },
        'p1_economy': {
            'minerals': 500,
            'vespene': 250,
            'supply_used': 24,
            'supply_cap': 30,
            'workers': 16,
            'idle_workers': 2,
        },
        'p2_economy': {
            'minerals': 600,
            'vespene': 300,
            'supply_used': 22,
            'supply_cap': 30,
            'workers': 18,
            'idle_workers': 1,
        },
        'p1_upgrades': {
            'attack_level': 1,
            'armor_level': 1,
            'shield_level': 0,
        },
        'p2_upgrades': {
            'attack_level': 2,
            'armor_level': 1,
            'shield_level': 1,
        },
        'messages': [],
    }
