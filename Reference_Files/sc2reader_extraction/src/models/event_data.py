"""
Data models for game events (units, buildings, upgrades, messages)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class UnitEvent:
    """Unit lifecycle event (birth or death)"""
    frame: int
    event_type: str  # "born" | "died"
    unit_id: int
    unit_type: str  # "Probe", "Marine", etc.
    player_id: int

    # Position
    x: int = 0
    y: int = 0

    # Death-specific
    killer_player_id: Optional[int] = None
    killer_unit_id: Optional[int] = None


@dataclass
class BuildingEvent:
    """Building lifecycle event (construction, completion, destruction)"""
    frame: int
    event_type: str  # "started" | "completed" | "destroyed" | "cancelled"
    unit_id: int
    building_type: str  # "Pylon", "Gateway", etc.
    player_id: int

    # Position
    x: int = 0
    y: int = 0

    # Destruction-specific
    killer_player_id: Optional[int] = None

    # Timing (for completed buildings)
    started_frame: Optional[int] = None
    build_time_frames: Optional[int] = None


@dataclass
class UpgradeEvent:
    """Upgrade completion event"""
    frame: int
    upgrade_name: str  # "WarpGateResearch", etc.
    player_id: int
    upgrade_level: int = 1  # For multi-level upgrades (1, 2, 3)


@dataclass
class MessageEvent:
    """Chat or game message"""
    frame: int
    game_time_seconds: float
    player_id: int
    text: str
    target: str = "all"  # "all" | "allies" | "observers"


@dataclass
class UnitLifecycle:
    """Complete lifecycle tracking for a unit/building"""
    unit_id: int
    unit_type: str
    player_id: int

    # Event frames
    born_frame: Optional[int] = None      # UnitBornEvent
    init_frame: Optional[int] = None      # UnitInitEvent (for buildings)
    done_frame: Optional[int] = None      # UnitDoneEvent
    died_frame: Optional[int] = None      # UnitDiedEvent

    # Position
    x: int = 0
    y: int = 0

    # Death info
    killer_player_id: Optional[int] = None
    killer_unit_id: Optional[int] = None

    def is_alive_at_frame(self, frame: int) -> bool:
        """Check if unit is alive at given frame"""
        # When unit becomes functional
        active_frame = self.done_frame or self.born_frame or self.init_frame
        if active_frame is None:
            return False

        # When unit stops existing
        death_frame = self.died_frame if self.died_frame is not None else float('inf')

        return active_frame <= frame < death_frame

    def is_building(self) -> bool:
        """Check if this is a building (has init_frame)"""
        return self.init_frame is not None

    def get_building_state(self, frame: int) -> str:
        """
        Determine building state at specific frame

        Returns: "not_started" | "constructing" | "existing" | "cancelled" | "destroyed"
        """
        if not self.is_building():
            return "not_applicable"  # Not a building

        if self.died_frame is not None and self.died_frame <= frame:
            # Building has died
            if self.done_frame is not None:
                return "destroyed"  # Died after completion
            else:
                return "cancelled"  # Died before completion

        if self.done_frame is not None and self.done_frame <= frame:
            return "existing"  # Completed and still alive

        if self.init_frame is not None and self.init_frame <= frame:
            return "constructing"  # Construction started but not done

        return "not_started"  # Construction hasn't begun
