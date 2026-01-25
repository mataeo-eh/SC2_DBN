"""
Mock pysc2 observation structures for testing.

This module provides realistic mock observations without requiring pysc2 to be installed.
"""

from typing import List, Dict, Any
from unittest.mock import Mock


# SC2 Unit Type IDs (from pysc2)
UNIT_TYPES = {
    'Marine': 48,
    'Marauder': 51,
    'SCV': 45,
    'Zealot': 73,
    'Probe': 84,
    'Zergling': 105,
    'Drone': 104,
    'CommandCenter': 18,
    'Barracks': 21,
    'Nexus': 59,
    'Gateway': 62,
    'Hatchery': 86,
}


def create_mock_unit(
    tag: int,
    unit_type: str,
    owner: int,
    x: float,
    y: float,
    z: float = 8.0,
    health: float = None,
    health_max: float = None,
    shields: float = 0.0,
    shields_max: float = 0.0,
    energy: float = 0.0,
    energy_max: float = 0.0,
    build_progress: float = 1.0,
    is_flying: bool = False,
    is_burrowed: bool = False,
    **kwargs
) -> Mock:
    """
    Create a mock unit with realistic attributes.

    Args:
        tag: Unique unit tag
        unit_type: Unit type name (e.g., 'Marine', 'SCV')
        owner: Player ID (1 or 2)
        x, y, z: Position coordinates
        health: Current health (defaults to health_max)
        health_max: Maximum health
        shields: Current shields
        shields_max: Maximum shields
        energy: Current energy
        energy_max: Maximum energy
        build_progress: Build completion (0.0 to 1.0)
        is_flying: Is unit flying
        is_burrowed: Is unit burrowed
        **kwargs: Additional attributes

    Returns:
        Mock unit object
    """
    unit_type_id = UNIT_TYPES.get(unit_type, 1)

    # Set default health values based on unit type
    default_health = {
        'Marine': 45.0,
        'Marauder': 125.0,
        'SCV': 45.0,
        'Zealot': 100.0,
        'Probe': 20.0,
        'Zergling': 35.0,
        'Drone': 40.0,
    }

    if health_max is None:
        health_max = default_health.get(unit_type, 100.0)
    if health is None:
        health = health_max

    # Protoss units have shields
    if unit_type in ['Zealot', 'Probe'] and shields_max == 0.0:
        shields_max = 50.0 if unit_type == 'Zealot' else 20.0
        if shields == 0.0:
            shields = shields_max

    unit = Mock()
    unit.tag = tag
    unit.unit_type = unit_type_id
    unit.owner = owner

    # Position
    unit.pos = Mock()
    unit.pos.x = x
    unit.pos.y = y
    unit.pos.z = z
    unit.facing = kwargs.get('facing', 0.0)

    # Vitals
    unit.health = health
    unit.health_max = health_max
    unit.shield = shields
    unit.shield_max = shields_max
    unit.energy = energy
    unit.energy_max = energy_max

    # State
    unit.build_progress = build_progress
    unit.is_flying = is_flying
    unit.is_burrowed = is_burrowed
    unit.is_hallucination = kwargs.get('is_hallucination', False)

    # Combat
    unit.weapon_cooldown = kwargs.get('weapon_cooldown', 0.0)
    unit.attack_upgrade_level = kwargs.get('attack_upgrade_level', 0)
    unit.armor_upgrade_level = kwargs.get('armor_upgrade_level', 0)
    unit.shield_upgrade_level = kwargs.get('shield_upgrade_level', 0)

    # Additional
    unit.radius = kwargs.get('radius', 0.5)
    unit.cargo_space_taken = kwargs.get('cargo_space_taken', 0)
    unit.cargo_space_max = kwargs.get('cargo_space_max', 0)
    unit.orders = kwargs.get('orders', [])
    unit.alliance = kwargs.get('alliance', 1)  # ALLIANCE_SELF

    return unit


def create_mock_observation(
    game_loop: int,
    units: List[Mock],
    player_id: int = 1,
    minerals: int = 50,
    vespene: int = 0,
    supply_used: int = 12,
    supply_cap: int = 15,
    workers: int = 6,
    idle_workers: int = 0,
    dead_units: List[int] = None,
    messages: List[Dict[str, Any]] = None
) -> Mock:
    """
    Create a mock observation with all required attributes.

    Args:
        game_loop: Current game loop number
        units: List of mock units
        player_id: Current player ID
        minerals: Player minerals
        vespene: Player vespene gas
        supply_used: Food/supply used
        supply_cap: Maximum food/supply
        workers: Worker count
        idle_workers: Idle worker count
        dead_units: List of dead unit tags
        messages: List of chat messages

    Returns:
        Mock observation object
    """
    obs = Mock()

    # Main observation wrapper
    obs.observation = Mock()
    obs.observation.game_loop = game_loop

    # Raw data
    obs.observation.raw_data = Mock()
    obs.observation.raw_data.units = units

    # Player data
    obs.observation.raw_data.player = Mock()
    obs.observation.raw_data.player.minerals = minerals
    obs.observation.raw_data.player.vespene = vespene
    obs.observation.raw_data.player.food_used = supply_used
    obs.observation.raw_data.player.food_cap = supply_cap
    obs.observation.raw_data.player.food_army = supply_used - workers
    obs.observation.raw_data.player.food_workers = workers
    obs.observation.raw_data.player.idle_worker_count = idle_workers
    obs.observation.raw_data.player.army_count = supply_used - workers
    obs.observation.raw_data.player.warp_gate_count = 0
    obs.observation.raw_data.player.larva_count = 0

    # Event data
    obs.observation.raw_data.event = Mock()
    obs.observation.raw_data.event.dead_units = dead_units or []

    # Chat messages
    obs.observation.chat = []
    if messages:
        for msg in messages:
            chat_msg = Mock()
            chat_msg.player_id = msg.get('player_id', player_id)
            chat_msg.message = msg.get('message', '')
            obs.observation.chat.append(chat_msg)

    # Player common info
    obs.observation.player_common = Mock()
    obs.observation.player_common.player_id = player_id

    return obs


def create_marine_rush_sequence() -> List[Mock]:
    """
    Create a realistic sequence of observations showing a marine rush.

    Returns:
        List of mock observations showing unit creation and combat
    """
    observations = []

    # Frame 0: Game start - 6 SCVs and 1 Marine
    units_0 = [
        create_mock_unit(1001, 'SCV', 1, 30.0, 30.0),
        create_mock_unit(1002, 'SCV', 1, 31.0, 30.0),
        create_mock_unit(1003, 'SCV', 1, 32.0, 30.0),
        create_mock_unit(1004, 'SCV', 1, 30.0, 31.0),
        create_mock_unit(1005, 'SCV', 1, 31.0, 31.0),
        create_mock_unit(1006, 'SCV', 1, 32.0, 31.0),
        create_mock_unit(2001, 'Marine', 1, 35.0, 35.0),
    ]
    observations.append(create_mock_observation(
        game_loop=0,
        units=units_0,
        minerals=50,
        workers=6,
    ))

    # Frame 500: Built 3 more marines
    units_500 = [
        create_mock_unit(1001, 'SCV', 1, 30.0, 30.0),
        create_mock_unit(1002, 'SCV', 1, 31.0, 30.0),
        create_mock_unit(1003, 'SCV', 1, 32.0, 30.0),
        create_mock_unit(1004, 'SCV', 1, 30.0, 31.0),
        create_mock_unit(1005, 'SCV', 1, 31.0, 31.0),
        create_mock_unit(1006, 'SCV', 1, 32.0, 31.0),
        create_mock_unit(2001, 'Marine', 1, 40.0, 40.0),
        create_mock_unit(2002, 'Marine', 1, 41.0, 40.0),
        create_mock_unit(2003, 'Marine', 1, 42.0, 40.0),
        create_mock_unit(2004, 'Marine', 1, 43.0, 40.0),
    ]
    observations.append(create_mock_observation(
        game_loop=500,
        units=units_500,
        minerals=200,
        supply_used=16,
        workers=6,
    ))

    # Frame 1000: Combat - one marine takes damage
    units_1000 = [
        create_mock_unit(1001, 'SCV', 1, 30.0, 30.0),
        create_mock_unit(1002, 'SCV', 1, 31.0, 30.0),
        create_mock_unit(1003, 'SCV', 1, 32.0, 30.0),
        create_mock_unit(1004, 'SCV', 1, 30.0, 31.0),
        create_mock_unit(1005, 'SCV', 1, 31.0, 31.0),
        create_mock_unit(1006, 'SCV', 1, 32.0, 31.0),
        create_mock_unit(2001, 'Marine', 1, 50.0, 50.0, health=30.0),  # Damaged
        create_mock_unit(2002, 'Marine', 1, 51.0, 50.0),
        create_mock_unit(2003, 'Marine', 1, 52.0, 50.0),
        create_mock_unit(2004, 'Marine', 1, 53.0, 50.0),
    ]
    observations.append(create_mock_observation(
        game_loop=1000,
        units=units_1000,
        minerals=350,
        supply_used=16,
        workers=6,
    ))

    # Frame 1500: Combat - marine dies
    units_1500 = [
        create_mock_unit(1001, 'SCV', 1, 30.0, 30.0),
        create_mock_unit(1002, 'SCV', 1, 31.0, 30.0),
        create_mock_unit(1003, 'SCV', 1, 32.0, 30.0),
        create_mock_unit(1004, 'SCV', 1, 30.0, 31.0),
        create_mock_unit(1005, 'SCV', 1, 31.0, 31.0),
        create_mock_unit(1006, 'SCV', 1, 32.0, 31.0),
        # Marine 2001 is dead
        create_mock_unit(2002, 'Marine', 1, 51.0, 50.0, health=35.0),  # Damaged
        create_mock_unit(2003, 'Marine', 1, 52.0, 50.0),
        create_mock_unit(2004, 'Marine', 1, 53.0, 50.0),
    ]
    observations.append(create_mock_observation(
        game_loop=1500,
        units=units_1500,
        minerals=500,
        supply_used=14,
        workers=6,
        dead_units=[2001],  # Marine 1 died
    ))

    return observations


def create_building_construction_sequence() -> List[Mock]:
    """
    Create a sequence showing building construction lifecycle.

    Returns:
        List of mock observations showing building construction
    """
    observations = []

    # Frame 0: Construction starts
    units_0 = [
        create_mock_unit(1001, 'SCV', 1, 30.0, 30.0),
        create_mock_unit(5001, 'Barracks', 1, 40.0, 40.0, build_progress=0.0),  # Just started
    ]
    observations.append(create_mock_observation(
        game_loop=0,
        units=units_0,
        minerals=50,
    ))

    # Frame 500: Construction in progress
    units_500 = [
        create_mock_unit(1001, 'SCV', 1, 40.0, 40.0),  # Building
        create_mock_unit(5001, 'Barracks', 1, 40.0, 40.0, build_progress=0.5),  # 50%
    ]
    observations.append(create_mock_observation(
        game_loop=500,
        units=units_500,
        minerals=100,
    ))

    # Frame 1000: Construction complete
    units_1000 = [
        create_mock_unit(1001, 'SCV', 1, 41.0, 40.0),  # Moved away
        create_mock_unit(5001, 'Barracks', 1, 40.0, 40.0, build_progress=1.0),  # Complete
    ]
    observations.append(create_mock_observation(
        game_loop=1000,
        units=units_1000,
        minerals=200,
    ))

    # Frame 2000: Building destroyed
    units_2000 = [
        create_mock_unit(1001, 'SCV', 1, 41.0, 40.0),
        # Barracks is gone
    ]
    observations.append(create_mock_observation(
        game_loop=2000,
        units=units_2000,
        minerals=300,
        dead_units=[5001],
    ))

    return observations


def create_multi_race_observation() -> Mock:
    """
    Create an observation with units from all three races.

    Returns:
        Mock observation with diverse unit types
    """
    units = [
        # Terran (Player 1)
        create_mock_unit(1001, 'SCV', 1, 30.0, 30.0),
        create_mock_unit(1002, 'Marine', 1, 35.0, 35.0),
        create_mock_unit(1003, 'Marauder', 1, 36.0, 35.0),

        # Protoss (Player 2)
        create_mock_unit(2001, 'Probe', 2, 130.0, 130.0),
        create_mock_unit(2002, 'Zealot', 2, 135.0, 135.0),

        # Note: In a real game, you wouldn't have multiple races,
        # but this is useful for testing extractor flexibility
    ]

    return create_mock_observation(
        game_loop=1000,
        units=units,
        minerals=500,
        vespene=250,
        supply_used=20,
        supply_cap=30,
    )
