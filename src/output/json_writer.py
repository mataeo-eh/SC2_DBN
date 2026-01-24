"""
JSON output writer for replay data
"""
import json
import logging
from pathlib import Path
from typing import List
from dataclasses import asdict

from src.models.replay_data import ReplayMetadata
from src.models.frame_data import FrameState

logger = logging.getLogger(__name__)


class JSONWriter:
    """Writes extracted replay data to JSON format"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_all(self, metadata: ReplayMetadata, frame_states: List[FrameState]):
        """
        Write metadata and frame states to JSON files

        Args:
            metadata: Replay metadata
            frame_states: List of frame state snapshots
        """
        replay_hash = metadata.replay_hash

        # Write metadata
        metadata_file = self.output_dir / f"{replay_hash}_metadata.json"
        self._write_metadata(metadata, metadata_file)

        # Write frame states
        frames_file = self.output_dir / f"{replay_hash}_frames.json"
        self._write_frames(frame_states, frames_file)

        logger.info(f"JSON output written to {self.output_dir}")

    def _write_metadata(self, metadata: ReplayMetadata, output_file: Path):
        """Write metadata to JSON"""
        # Convert to dict, handling datetime and other non-JSON types
        metadata_dict = asdict(metadata)

        # Convert datetime to string
        if metadata_dict.get('end_time'):
            metadata_dict['end_time'] = metadata_dict['end_time'].isoformat()
        if metadata_dict.get('extraction_timestamp'):
            metadata_dict['extraction_timestamp'] = metadata_dict['extraction_timestamp'].isoformat()

        with open(output_file, 'w') as f:
            json.dump(metadata_dict, f, indent=2, default=str)

        logger.info(f"Metadata written to {output_file}")

    def _write_frames(self, frame_states: List[FrameState], output_file: Path):
        """Write frame states to JSON"""
        frames_data = []

        for frame_state in frame_states:
            frame_dict = {
                'frame': frame_state.frame,
                'game_time_seconds': frame_state.game_time_seconds,
                'player_states': {}
            }

            # Convert player states
            for player_id, player_state in frame_state.player_states.items():
                player_dict = asdict(player_state)
                # Convert set to list for JSON
                player_dict['upgrades_completed'] = list(player_dict['upgrades_completed'])
                frame_dict['player_states'][player_id] = player_dict

            frames_data.append(frame_dict)

        with open(output_file, 'w') as f:
            json.dump(frames_data, f, indent=2, default=str)

        logger.info(f"Frame states written to {output_file} ({len(frames_data)} frames)")
