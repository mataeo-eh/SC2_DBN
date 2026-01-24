"""
Game state tracker - maintains current game state across all frames
"""
import logging
from collections import defaultdict
from typing import Dict, Set, List, Optional, Tuple

from src.models.event_data import UnitLifecycle, MessageEvent
from src.models.frame_data import FrameState, PlayerFrameState
from src.utils.unit_types import (
    is_map_unit, is_building, is_worker, count_bases, calculate_tech_tier
)

logger = logging.getLogger(__name__)


class GameStateTracker:
    """Maintains current game state across all frames"""

    def __init__(self):
        # Unit tracking (unit_id -> UnitLifecycle)
        self.units: Dict[int, UnitLifecycle] = {}

        # Upgrade tracking (player_id -> Set[upgrade_name])
        self.upgrades: Dict[int, Set[str]] = defaultdict(set)

        # Upgrade completion frames ((player_id, upgrade_name) -> frame)
        self.upgrade_frames: Dict[Tuple[int, str], int] = {}

        # Player stats tracking (sorted list of (frame, player_id, stats_event))
        self.stats_events: List[Tuple[int, int, any]] = []

        # Messages
        self.messages: List[MessageEvent] = []

        # Current frame
        self.current_frame: int = 0

    def add_unit_born(self, frame: int, unit_id: int, unit_type: str, player_id: int, x: int, y: int):
        """Record a unit birth event"""
        # Skip map units
        if is_map_unit(unit_type):
            return

        lifecycle = UnitLifecycle(
            unit_id=unit_id,
            unit_type=unit_type,
            player_id=player_id,
            born_frame=frame,
            x=x,
            y=y
        )
        self.units[unit_id] = lifecycle

    def add_unit_init(self, frame: int, unit_id: int, unit_type: str, player_id: int, x: int, y: int):
        """Record a unit/building construction start event"""
        # Skip map units
        if is_map_unit(unit_type):
            return

        lifecycle = UnitLifecycle(
            unit_id=unit_id,
            unit_type=unit_type,
            player_id=player_id,
            init_frame=frame,
            x=x,
            y=y
        )
        self.units[unit_id] = lifecycle

    def add_unit_done(self, frame: int, unit_id: int):
        """Record a unit/building construction completion event"""
        if unit_id in self.units:
            self.units[unit_id].done_frame = frame

    def add_unit_died(self, frame: int, unit_id: int, killer_player_id: Optional[int] = None):
        """Record a unit/building death event"""
        if unit_id in self.units:
            self.units[unit_id].died_frame = frame
            self.units[unit_id].killer_player_id = killer_player_id

    def add_upgrade(self, frame: int, player_id: int, upgrade_name: str):
        """Record an upgrade completion event"""
        self.upgrades[player_id].add(upgrade_name)
        self.upgrade_frames[(player_id, upgrade_name)] = frame

    def add_player_stats(self, frame: int, player_id: int, stats_event):
        """Record a player stats event"""
        self.stats_events.append((frame, player_id, stats_event))

    def add_message(self, frame: int, player_id: int, text: str, target: str):
        """Record a chat message"""
        message = MessageEvent(
            frame=frame,
            game_time_seconds=frame / 22.4,
            player_id=player_id,
            text=text,
            target=target
        )
        self.messages.append(message)

    def get_state_at_frame(self, frame: int) -> FrameState:
        """
        Get complete game state at specified frame

        Args:
            frame: Frame number to reconstruct state for

        Returns:
            FrameState object with all player states
        """
        # Get all player IDs from units
        player_ids = set()
        for lifecycle in self.units.values():
            player_ids.add(lifecycle.player_id)

        # Build player states
        player_states = {}
        for player_id in player_ids:
            player_states[player_id] = self._build_player_state(player_id, frame)

        return FrameState(
            frame=frame,
            game_time_seconds=frame / 22.4,
            player_states=player_states
        )

    def _build_player_state(self, player_id: int, frame: int) -> PlayerFrameState:
        """Build player state at specific frame"""

        # Count units alive at this frame
        unit_counts = self._count_units(player_id, frame)

        # Count buildings by state
        buildings_existing, buildings_constructing = self._count_buildings(player_id, frame)

        # Get upgrades completed by this frame
        upgrades = self._get_upgrades(player_id, frame)

        # Get latest player stats before this frame
        stats = self._get_latest_stats(player_id, frame)

        # Calculate derived features
        tech_tier = calculate_tech_tier(buildings_existing)
        base_count = count_bases(buildings_existing)

        # Count production buildings
        production_buildings = ['Gateway', 'WarpGate', 'RoboticsFacility', 'Stargate',
                               'Barracks', 'Factory', 'Starport',
                               'Hatchery', 'Lair', 'Hive']
        production_capacity = sum(buildings_existing.get(b, 0) for b in production_buildings)

        # Count workers
        workers_total = sum(unit_counts.get(worker, 0) for worker in ['Probe', 'SCV', 'Drone'])

        return PlayerFrameState(
            player_id=player_id,
            minerals=stats.minerals_current if stats else 0,
            vespene=stats.vespene_current if stats else 0,
            minerals_collection_rate=stats.minerals_collection_rate if stats else 0.0,
            vespene_collection_rate=stats.vespene_collection_rate if stats else 0.0,
            supply_used=stats.food_used if stats else 0.0,
            supply_made=stats.food_made if stats else 0.0,
            workers_active=stats.workers_active_count if stats else 0,
            workers_total=workers_total,
            minerals_spent_economy=stats.minerals_used_current_economy if stats else 0,
            vespene_spent_economy=stats.vespene_used_current_economy if stats else 0,
            army_value_minerals=stats.minerals_used_current_army if stats else 0,
            army_value_vespene=stats.vespene_used_current_army if stats else 0,
            minerals_spent_technology=stats.minerals_used_current_technology if stats else 0,
            vespene_spent_technology=stats.vespene_used_current_technology if stats else 0,
            minerals_lost=stats.minerals_lost if stats else 0,
            vespene_lost=stats.vespene_lost if stats else 0,
            minerals_killed=stats.minerals_killed if stats else 0,
            vespene_killed=stats.vespene_killed if stats else 0,
            unit_counts=unit_counts,
            buildings_existing=buildings_existing,
            buildings_constructing=buildings_constructing,
            upgrades_completed=upgrades,
            tech_tier=tech_tier,
            base_count=base_count,
            production_capacity=production_capacity
        )

    def _count_units(self, player_id: int, frame: int) -> Dict[str, int]:
        """Count units alive at specific frame for a player"""
        counts = defaultdict(int)

        for unit_id, lifecycle in self.units.items():
            # Skip if not owned by this player
            if lifecycle.player_id != player_id:
                continue

            # Skip buildings
            if is_building(lifecycle.unit_type):
                continue

            # Check if alive at this frame
            if lifecycle.is_alive_at_frame(frame):
                counts[lifecycle.unit_type] += 1

        return dict(counts)

    def _count_buildings(self, player_id: int, frame: int) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Count buildings by state for a player at specific frame

        Returns:
            (buildings_existing, buildings_constructing)
        """
        existing = defaultdict(int)
        constructing = defaultdict(int)

        for unit_id, lifecycle in self.units.items():
            # Skip if not owned by this player
            if lifecycle.player_id != player_id:
                continue

            # Skip non-buildings
            if not is_building(lifecycle.unit_type):
                continue

            # Get building state
            state = lifecycle.get_building_state(frame)

            if state == "existing":
                existing[lifecycle.unit_type] += 1
            elif state == "constructing":
                constructing[lifecycle.unit_type] += 1

        return dict(existing), dict(constructing)

    def _get_upgrades(self, player_id: int, frame: int) -> Set[str]:
        """Get all upgrades completed by this frame"""
        result = set()
        for upgrade_name in self.upgrades[player_id]:
            completion_frame = self.upgrade_frames.get((player_id, upgrade_name))
            if completion_frame is not None and completion_frame <= frame:
                result.add(upgrade_name)
        return result

    def _get_latest_stats(self, player_id: int, frame: int):
        """Get most recent PlayerStatsEvent before target frame"""
        latest = None
        latest_frame = -1

        for event_frame, pid, stats in self.stats_events:
            if pid == player_id and event_frame <= frame and event_frame > latest_frame:
                latest = stats
                latest_frame = event_frame

        return latest
