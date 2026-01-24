"""
Data models for frame-by-frame game state
"""
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional
from src.models.event_data import UnitEvent, BuildingEvent, UpgradeEvent, MessageEvent


@dataclass
class PlayerFrameState:
    """State for one player at a specific frame"""
    player_id: int

    # Resources
    minerals: int = 0
    vespene: int = 0
    minerals_collection_rate: float = 0.0
    vespene_collection_rate: float = 0.0

    # Supply
    supply_used: float = 0.0
    supply_made: float = 0.0
    supply_cap: float = 200.0

    # Economy
    workers_active: int = 0
    workers_total: int = 0
    minerals_spent_economy: int = 0
    vespene_spent_economy: int = 0

    # Military
    army_value_minerals: int = 0
    army_value_vespene: int = 0
    army_supply: float = 0.0
    minerals_spent_army: int = 0
    vespene_spent_army: int = 0

    # Technology
    minerals_spent_technology: int = 0
    vespene_spent_technology: int = 0

    # Losses
    minerals_lost: int = 0
    vespene_lost: int = 0
    minerals_killed: int = 0  # Enemy value destroyed
    vespene_killed: int = 0

    # Units (counts by type)
    unit_counts: Dict[str, int] = field(default_factory=dict)

    # Buildings (counts by type and state)
    buildings_existing: Dict[str, int] = field(default_factory=dict)
    buildings_constructing: Dict[str, int] = field(default_factory=dict)

    # Upgrades (set of completed upgrade names)
    upgrades_completed: Set[str] = field(default_factory=set)

    # Derived features
    tech_tier: int = 1  # Tech tier (1/2/3) based on buildings
    base_count: int = 0  # Number of bases (Nexus/CC/Hatchery)
    production_capacity: int = 0  # Number of production buildings


@dataclass
class FrameState:
    """Complete game state at a specific frame"""
    frame: int
    game_time_seconds: float

    # Player states (keyed by player_id)
    player_states: Dict[int, PlayerFrameState] = field(default_factory=dict)

    # Optional: Recent events in this interval
    units_born: List[UnitEvent] = field(default_factory=list)
    units_died: List[UnitEvent] = field(default_factory=list)
    buildings_started: List[BuildingEvent] = field(default_factory=list)
    buildings_completed: List[BuildingEvent] = field(default_factory=list)
    buildings_destroyed: List[BuildingEvent] = field(default_factory=list)
    upgrades_completed: List[UpgradeEvent] = field(default_factory=list)
    messages: List[MessageEvent] = field(default_factory=list)
