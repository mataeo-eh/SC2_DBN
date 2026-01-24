"""
Replay parser for loading and validating SC2 replay files
"""
import os
import hashlib
from datetime import datetime
from typing import Tuple, List
import logging

# CRITICAL: Import patch BEFORE sc2reader
import sc2reader_patch  # noqa: F401
import sc2reader

from src.models.replay_data import ReplayMetadata, PlayerInfo

logger = logging.getLogger(__name__)


class ReplayParser:
    """Parser for SC2 replay files"""

    def __init__(self):
        self.min_version = "2.0.8"
        self.min_frames = 1792  # 2 minutes @ Faster speed

    def load_replay(self, file_path: str, load_level: int = 3) -> sc2reader.resources.Replay:
        """
        Load SC2 replay file with bot replay compatibility

        Args:
            file_path: Path to .SC2Replay file
            load_level: Data loading depth (3 = tracker events only, recommended)

        Returns:
            sc2reader.Replay object

        Raises:
            FileNotFoundError: Replay file not found
            Exception: Failed to parse replay
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Replay file not found: {file_path}")

        try:
            logger.info(f"Loading replay: {file_path}")
            replay = sc2reader.load_replay(file_path, load_level=load_level)
            logger.info(f"Loaded successfully ({len(replay.tracker_events)} tracker events)")
            return replay
        except Exception as e:
            logger.error(f"Failed to load replay: {e}")
            raise

    def validate_replay(self, replay: sc2reader.resources.Replay) -> Tuple[bool, List[str]]:
        """
        Validate replay meets quality requirements

        Args:
            replay: Loaded replay object

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # Check minimum game length
        if replay.frames < self.min_frames:
            errors.append(f"Game too short: {replay.frames} frames (< {self.min_frames})")

        # Check has tracker events
        if not hasattr(replay, 'tracker_events') or not replay.tracker_events:
            errors.append("No tracker events found")

        # Check SC2 version (should be >= 2.0.8 for tracker events)
        if hasattr(replay, 'release_string'):
            version = replay.release_string
            if version < self.min_version:
                errors.append(f"Version too old: {version} (< {self.min_version})")

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(f"Validation failed: {errors}")
        else:
            logger.info("Replay validation passed")

        return is_valid, errors

    def extract_metadata(self, replay: sc2reader.resources.Replay, file_path: str) -> ReplayMetadata:
        """
        Extract replay metadata

        Args:
            replay: Loaded replay object
            file_path: Path to replay file

        Returns:
            ReplayMetadata object
        """
        logger.info("Extracting metadata")

        # Generate replay hash (from file path)
        replay_hash = hashlib.md5(file_path.encode()).hexdigest()

        # Extract player information
        players = []
        for player in replay.players:
            player_info = PlayerInfo(
                player_id=player.pid,
                name=player.name if hasattr(player, 'name') else f"Player{player.pid}",
                race=player.play_race if hasattr(player, 'play_race') else "Unknown",
                result=player.result if hasattr(player, 'result') else "Unknown",
                handicap=player.handicap if hasattr(player, 'handicap') else 100,
                color=player.color if hasattr(player, 'color') else ""
            )
            players.append(player_info)

        # If no players (bot replay), infer from events
        if not players:
            logger.warning("No players in replay metadata (bot replay)")
            # Will infer player IDs from events later

        # Determine winner
        winner_id = None
        if hasattr(replay, 'winner'):
            if replay.winner and hasattr(replay.winner, 'pid'):
                winner_id = replay.winner.pid

        # Create metadata object
        metadata = ReplayMetadata(
            replay_hash=replay_hash,
            file_path=file_path,
            map_name=replay.map_name if hasattr(replay, 'map_name') else "Unknown",
            map_hash=replay.map_hash if hasattr(replay, 'map_hash') else None,
            region=replay.region if hasattr(replay, 'region') else "local",
            game_version=replay.release_string if hasattr(replay, 'release_string') else "",
            expansion=replay.expansion if hasattr(replay, 'expansion') else "LotV",
            game_mode=self._infer_game_mode(len(players)),
            speed=replay.speed if hasattr(replay, 'speed') else "Faster",
            game_length_frames=replay.frames,
            game_length_seconds=replay.frames / 22.4,  # Faster speed
            end_time=replay.end_time if hasattr(replay, 'end_time') else None,
            player_count=len(players),
            players=players,
            winner_id=winner_id,
            extraction_version="1.0.0",
            extraction_timestamp=datetime.utcnow(),
            is_complete=True,  # Assume complete if loaded
            is_valid=True,
            has_errors=False,
            error_messages=[]
        )

        logger.info(f"Metadata extracted: {metadata.map_name}, {metadata.game_length_seconds:.1f}s, {metadata.player_count} players")

        return metadata

    def _infer_game_mode(self, player_count: int) -> str:
        """Infer game mode from player count"""
        if player_count == 2:
            return "1v1"
        elif player_count == 4:
            return "2v2"
        elif player_count == 6:
            return "3v3"
        elif player_count == 8:
            return "4v4"
        else:
            return "Unknown"
