"""
Parquet output writer for replay data
"""
import logging
from pathlib import Path
from typing import List
import pandas as pd

from src.models.replay_data import ReplayMetadata
from src.models.frame_data import FrameState

logger = logging.getLogger(__name__)


class ParquetWriter:
    """Writes extracted replay data to Parquet format"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_all(self, metadata: ReplayMetadata, frame_states: List[FrameState]):
        """
        Write metadata and frame states to Parquet files

        Args:
            metadata: Replay metadata
            frame_states: List of frame state snapshots
        """
        replay_hash = metadata.replay_hash

        # Write metadata
        metadata_file = self.output_dir / "replay_metadata.parquet"
        self._write_metadata(metadata, metadata_file)

        # Write frame states (main table)
        frames_file = self.output_dir / "frame_states.parquet"
        self._write_frame_states(replay_hash, frame_states, frames_file)

        # Write unit counts (detailed table)
        units_file = self.output_dir / "unit_counts.parquet"
        self._write_unit_counts(replay_hash, frame_states, units_file)

        # Write building counts (detailed table)
        buildings_file = self.output_dir / "building_counts.parquet"
        self._write_building_counts(replay_hash, frame_states, buildings_file)

        # Write upgrades
        upgrades_file = self.output_dir / "upgrades.parquet"
        self._write_upgrades(replay_hash, frame_states, upgrades_file)

        logger.info(f"Parquet output written to {self.output_dir}")

    def _write_metadata(self, metadata: ReplayMetadata, output_file: Path):
        """Write metadata to Parquet"""
        # Convert to dict
        metadata_dict = {
            'replay_hash': metadata.replay_hash,
            'file_path': metadata.file_path,
            'map_name': metadata.map_name,
            'map_hash': metadata.map_hash,
            'region': metadata.region,
            'game_version': metadata.game_version,
            'expansion': metadata.expansion,
            'game_mode': metadata.game_mode,
            'speed': metadata.speed,
            'game_length_frames': metadata.game_length_frames,
            'game_length_seconds': metadata.game_length_seconds,
            'player_count': metadata.player_count,
            'winner_id': metadata.winner_id,
            'is_complete': metadata.is_complete,
            'is_valid': metadata.is_valid
        }

        df = pd.DataFrame([metadata_dict])

        # Append or write
        if output_file.exists():
            existing_df = pd.read_parquet(output_file)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"Metadata written to {output_file}")

    def _write_frame_states(self, replay_hash: str, frame_states: List[FrameState], output_file: Path):
        """Write main frame states table"""
        rows = []

        for state in frame_states:
            for player_id, player_state in state.player_states.items():
                rows.append({
                    'replay_hash': replay_hash,
                    'frame': state.frame,
                    'game_time_seconds': state.game_time_seconds,
                    'player_id': player_id,
                    'minerals': player_state.minerals,
                    'vespene': player_state.vespene,
                    'minerals_collection_rate': player_state.minerals_collection_rate,
                    'vespene_collection_rate': player_state.vespene_collection_rate,
                    'supply_used': player_state.supply_used,
                    'supply_made': player_state.supply_made,
                    'workers_active': player_state.workers_active,
                    'workers_total': player_state.workers_total,
                    'army_value_minerals': player_state.army_value_minerals,
                    'army_value_vespene': player_state.army_value_vespene,
                    'minerals_lost': player_state.minerals_lost,
                    'vespene_lost': player_state.vespene_lost,
                    'minerals_killed': player_state.minerals_killed,
                    'vespene_killed': player_state.vespene_killed,
                    'tech_tier': player_state.tech_tier,
                    'base_count': player_state.base_count,
                    'production_capacity': player_state.production_capacity
                })

        df = pd.DataFrame(rows)

        # Append or write
        if output_file.exists():
            existing_df = pd.read_parquet(output_file)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"Frame states written to {output_file} ({len(rows)} rows)")

    def _write_unit_counts(self, replay_hash: str, frame_states: List[FrameState], output_file: Path):
        """Write unit counts table"""
        rows = []

        for state in frame_states:
            for player_id, player_state in state.player_states.items():
                for unit_type, count in player_state.unit_counts.items():
                    rows.append({
                        'replay_hash': replay_hash,
                        'frame': state.frame,
                        'player_id': player_id,
                        'unit_type': unit_type,
                        'count': count
                    })

        if not rows:
            logger.warning("No unit counts to write")
            return

        df = pd.DataFrame(rows)

        # Append or write
        if output_file.exists():
            existing_df = pd.read_parquet(output_file)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"Unit counts written to {output_file} ({len(rows)} rows)")

    def _write_building_counts(self, replay_hash: str, frame_states: List[FrameState], output_file: Path):
        """Write building counts table"""
        rows = []

        for state in frame_states:
            for player_id, player_state in state.player_states.items():
                # Existing buildings
                for building_type, count in player_state.buildings_existing.items():
                    rows.append({
                        'replay_hash': replay_hash,
                        'frame': state.frame,
                        'player_id': player_id,
                        'building_type': building_type,
                        'state': 'existing',
                        'count': count
                    })

                # Constructing buildings
                for building_type, count in player_state.buildings_constructing.items():
                    rows.append({
                        'replay_hash': replay_hash,
                        'frame': state.frame,
                        'player_id': player_id,
                        'building_type': building_type,
                        'state': 'constructing',
                        'count': count
                    })

        if not rows:
            logger.warning("No building counts to write")
            return

        df = pd.DataFrame(rows)

        # Append or write
        if output_file.exists():
            existing_df = pd.read_parquet(output_file)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"Building counts written to {output_file} ({len(rows)} rows)")

    def _write_upgrades(self, replay_hash: str, frame_states: List[FrameState], output_file: Path):
        """Write upgrades table"""
        rows = []

        for state in frame_states:
            for player_id, player_state in state.player_states.items():
                for upgrade_name in player_state.upgrades_completed:
                    rows.append({
                        'replay_hash': replay_hash,
                        'frame': state.frame,
                        'player_id': player_id,
                        'upgrade_name': upgrade_name
                    })

        if not rows:
            logger.warning("No upgrades to write")
            return

        df = pd.DataFrame(rows)

        # Append or write
        if output_file.exists():
            existing_df = pd.read_parquet(output_file)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"Upgrades written to {output_file} ({len(rows)} rows)")
