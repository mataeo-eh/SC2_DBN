"""
Data models for replay-level information
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class PlayerInfo:
    """Information about a single player in the replay"""
    player_id: int
    name: str
    race: str  # Protoss/Terran/Zerg/Random
    result: str  # Win/Loss/Tie/Unknown
    handicap: int = 100
    color: str = ""

    # MMR/Rating (if available)
    mmr: Optional[int] = None
    highest_league: Optional[str] = None

    # Final stats (from end of game)
    final_units: int = 0
    final_buildings: int = 0
    final_upgrades: int = 0
    final_minerals: int = 0
    final_vespene: int = 0
    final_supply_used: float = 0.0
    final_supply_made: float = 0.0


@dataclass
class ReplayMetadata:
    """Metadata for a single SC2 replay"""
    # Identifiers
    replay_hash: str  # Unique replay identifier (hash of file)
    file_path: str    # Path to replay file

    # Map info
    map_name: str
    map_hash: Optional[str] = None
    region: str = "local"  # us/eu/kr/local for bot replays

    # Game info
    game_version: str = ""
    expansion: str = "LotV"  # LotV/HotS/WoL
    game_mode: str = "1v1"    # 1v1/2v2/3v3/4v4/FFA
    speed: str = "Faster"

    # Temporal info
    game_length_frames: int = 0
    game_length_seconds: float = 0.0
    end_time: Optional[datetime] = None

    # Players
    player_count: int = 0
    players: List[PlayerInfo] = field(default_factory=list)

    # Outcome
    winner_id: Optional[int] = None

    # Processing info
    extraction_version: str = "1.0.0"
    extraction_timestamp: Optional[datetime] = None

    # Validation flags
    is_complete: bool = True
    is_valid: bool = True
    has_errors: bool = False
    error_messages: List[str] = field(default_factory=list)
