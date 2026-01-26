"""
Unit type classification and utilities
"""

# Map units to filter out (not player-controlled units)
MAP_UNITS = {
    'MineralField', 'MineralField750', 'MineralField450',
    'VespeneGeyser', 'SpacePlatformGeyser', 'RichVespeneGeyser',
    'DestructibleDebris', 'DestructibleRock',
    'UnbuildablePlates', 'UnbuildableRocks',
    'XelNagaTower', 'CleaningBot',
    'ProtossVespeneGeyser', 'PurifierVespeneGeyser',
    'ShakurasVespeneGeyser'
}

# Building types by race
PROTOSS_BUILDINGS = {
    'Nexus', 'Pylon', 'Assimilator',
    'Gateway', 'WarpGate', 'Forge', 'PhotonCannon', 'ShieldBattery',
    'CyberneticsCore', 'RoboticsFacility', 'Stargate',
    'TwilightCouncil', 'TemplarArchive', 'DarkShrine',
    'RoboticsBay', 'FleetBeacon'
}

TERRAN_BUILDINGS = {
    'CommandCenter', 'OrbitalCommand', 'PlanetaryFortress',
    'SupplyDepot', 'Refinery', 'Barracks', 'EngineeringBay',
    'MissileTurret', 'Bunker', 'SensorTower', 'GhostAcademy',
    'Factory', 'Starport', 'Armory', 'FusionCore',
    'TechLab', 'Reactor', 'AutoTurret'
}

ZERG_BUILDINGS = {
    'Hatchery', 'Lair', 'Hive',
    'Extractor', 'SpawningPool', 'EvolutionChamber',
    'RoachWarren', 'BanelingNest', 'SpineCrawler', 'SporeCrawler',
    'HydraliskDen', 'LurkerDen', 'InfestationPit',
    'Spire', 'GreaterSpire', 'NydusNetwork', 'NydusCanal',
    'UltraliskCavern', 'CreepTumor', 'CreepTumorBurrowed', 'CreepTumorQueen'
}

ALL_BUILDINGS = PROTOSS_BUILDINGS | TERRAN_BUILDINGS | ZERG_BUILDINGS

# Base building types
BASE_BUILDINGS = {'Nexus', 'CommandCenter', 'OrbitalCommand', 'PlanetaryFortress', 'Hatchery', 'Lair', 'Hive'}

# Tech tier indicators
TECH_TIER_2_BUILDINGS = {
    # Protoss
    'CyberneticsCore',
    # Terran
    'Factory',
    # Zerg
    'Lair'
}

TECH_TIER_3_BUILDINGS = {
    # Protoss
    'TwilightCouncil', 'DarkShrine', 'TemplarArchive', 'FleetBeacon',
    # Terran
    'Starport', 'FusionCore',
    # Zerg
    'Hive', 'InfestationPit', 'Spire', 'GreaterSpire'
}

# Worker units
WORKER_UNITS = {'Probe', 'SCV', 'Drone', 'MULE'}


def is_map_unit(unit_type: str) -> bool:
    """Check if unit type is a map unit (non-player-controlled)"""
    return any(map_unit in unit_type for map_unit in MAP_UNITS)


def is_building(unit_type: str) -> bool:
    """Check if unit type is a building"""
    return unit_type in ALL_BUILDINGS


def is_worker(unit_type: str) -> bool:
    """Check if unit type is a worker"""
    return unit_type in WORKER_UNITS


def is_base_building(unit_type: str) -> bool:
    """Check if unit type is a base building (Nexus/CC/Hatchery)"""
    return unit_type in BASE_BUILDINGS


def calculate_tech_tier(buildings_existing: dict) -> int:
    """
    Calculate tech tier based on completed buildings

    Args:
        buildings_existing: Dict of building_type -> count

    Returns:
        Tech tier (1, 2, or 3)
    """
    # Check for tier 3 buildings
    if any(building in buildings_existing for building in TECH_TIER_3_BUILDINGS):
        return 3

    # Check for tier 2 buildings
    if any(building in buildings_existing for building in TECH_TIER_2_BUILDINGS):
        return 2

    return 1


def count_bases(buildings_existing: dict) -> int:
    """Count number of base buildings"""
    total = 0
    for building_type in BASE_BUILDINGS:
        if building_type in buildings_existing:
            total += buildings_existing[building_type]
    return total
