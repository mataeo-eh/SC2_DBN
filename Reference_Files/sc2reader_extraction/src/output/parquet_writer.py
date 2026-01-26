"""
Parquet output writer for replay data - Wide format (one row per timestep)
"""
import logging
from pathlib import Path
from typing import List, Dict, Set
import pandas as pd

from src.models.replay_data import ReplayMetadata
from src.models.frame_data import FrameState

logger = logging.getLogger(__name__)


class ParquetWriter:
    """Writes extracted replay data to Parquet format - wide format for ML"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_all(self, metadata: ReplayMetadata, frame_states: List[FrameState], replay_name: str = None):
        """
        Write replay data to a single Parquet file with wide format

        Args:
            metadata: Replay metadata
            frame_states: List of frame state snapshots
            replay_name: Optional replay name for filename (uses metadata.replay_hash if not provided)
        """
        # Use replay_name if provided, otherwise fall back to replay_hash
        base_name = replay_name if replay_name else metadata.replay_hash
        output_file = self.output_dir / f"{base_name}_parsed.parquet"

        # Collect all unique column names across all frames
        all_unit_types = self._collect_all_unit_types(frame_states)
        all_building_types = self._collect_all_building_types(frame_states)
        all_upgrade_names = self._collect_all_upgrades(frame_states)

        # Build rows with wide format
        rows = []
        for state in frame_states:
            row = self._build_wide_row(
                state,
                all_unit_types,
                all_building_types,
                all_upgrade_names
            )
            rows.append(row)

        if not rows:
            logger.warning(f"No frames to write for replay {base_name}")
            return

        df = pd.DataFrame(rows)

        # Write to parquet (no append - each replay is self-contained)
        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"Wide format parquet written to {output_file} ({len(rows)} rows, {len(df.columns)} columns)")

    def _collect_all_unit_types(self, frame_states: List[FrameState]) -> Set[str]:
        """Collect all unique unit types across all frames"""
        unit_types = set()
        for state in frame_states:
            for player_state in state.player_states.values():
                unit_types.update(player_state.unit_counts.keys())
        return unit_types

    def _collect_all_building_types(self, frame_states: List[FrameState]) -> Set[str]:
        """Collect all unique building types across all frames"""
        building_types = set()
        for state in frame_states:
            for player_state in state.player_states.values():
                building_types.update(player_state.buildings_existing.keys())
                building_types.update(player_state.buildings_constructing.keys())
        return building_types

    def _collect_all_upgrades(self, frame_states: List[FrameState]) -> Set[str]:
        """Collect all unique upgrade names across all frames"""
        upgrades = set()
        for state in frame_states:
            for player_state in state.player_states.values():
                upgrades.update(player_state.upgrades_completed)
        return upgrades

    def _build_wide_row(
        self,
        state: FrameState,
        all_unit_types: Set[str],
        all_building_types: Set[str],
        all_upgrade_names: Set[str]
    ) -> Dict:
        """
        Build a single wide-format row for one timestep

        Column naming convention:
        - frame, game_time_seconds (global)
        - p1_*, p2_* (player prefixes)
        - p{n}_unit_{UnitType} (unit counts)
        - p{n}_bldg_{BuildingType} (existing buildings)
        - p{n}_bldg_constr_{BuildingType} (constructing buildings)
        - p{n}_upg_{UpgradeName} (upgrades, binary 0/1)
        """
        row = {
            'frame': state.frame,
            'game_time_seconds': state.game_time_seconds,
        }

        # Sort player IDs for consistent p1/p2 assignment
        player_ids = sorted(state.player_states.keys())

        for idx, player_id in enumerate(player_ids):
            prefix = f"p{idx + 1}"
            player_state = state.player_states[player_id]

            # Core resource/economy fields
            row[f'{prefix}_minerals'] = player_state.minerals
            row[f'{prefix}_vespene'] = player_state.vespene
            row[f'{prefix}_minerals_collection_rate'] = player_state.minerals_collection_rate
            row[f'{prefix}_vespene_collection_rate'] = player_state.vespene_collection_rate
            row[f'{prefix}_supply_used'] = player_state.supply_used
            row[f'{prefix}_supply_made'] = player_state.supply_made
            row[f'{prefix}_supply_cap'] = player_state.supply_cap
            row[f'{prefix}_workers_active'] = player_state.workers_active
            row[f'{prefix}_workers_total'] = player_state.workers_total

            # Spending breakdown
            row[f'{prefix}_minerals_spent_economy'] = player_state.minerals_spent_economy
            row[f'{prefix}_vespene_spent_economy'] = player_state.vespene_spent_economy
            row[f'{prefix}_army_value_minerals'] = player_state.army_value_minerals
            row[f'{prefix}_army_value_vespene'] = player_state.army_value_vespene
            row[f'{prefix}_minerals_spent_technology'] = player_state.minerals_spent_technology
            row[f'{prefix}_vespene_spent_technology'] = player_state.vespene_spent_technology

            # Combat stats
            row[f'{prefix}_minerals_lost'] = player_state.minerals_lost
            row[f'{prefix}_vespene_lost'] = player_state.vespene_lost
            row[f'{prefix}_minerals_killed'] = player_state.minerals_killed
            row[f'{prefix}_vespene_killed'] = player_state.vespene_killed

            # Derived features
            row[f'{prefix}_tech_tier'] = player_state.tech_tier
            row[f'{prefix}_base_count'] = player_state.base_count
            row[f'{prefix}_production_capacity'] = player_state.production_capacity

            # Army position data
            row[f'{prefix}_army_center_x'] = player_state.army_center_x
            row[f'{prefix}_army_center_y'] = player_state.army_center_y
            row[f'{prefix}_army_spread'] = player_state.army_spread

            # Message tracking
            row[f'{prefix}_message_sent'] = 1 if player_state.message_sent else 0
            row[f'{prefix}_last_message_frame'] = player_state.last_message_frame

            # Unit counts (dynamic columns)
            for unit_type in sorted(all_unit_types):
                col_name = f'{prefix}_unit_{unit_type}'
                row[col_name] = player_state.unit_counts.get(unit_type, 0)

            # Existing buildings (dynamic columns)
            for building_type in sorted(all_building_types):
                col_name = f'{prefix}_bldg_{building_type}'
                row[col_name] = player_state.buildings_existing.get(building_type, 0)

            # Constructing buildings (dynamic columns)
            for building_type in sorted(all_building_types):
                col_name = f'{prefix}_bldg_constr_{building_type}'
                row[col_name] = player_state.buildings_constructing.get(building_type, 0)

            # Upgrades (binary 0/1)
            for upgrade_name in sorted(all_upgrade_names):
                col_name = f'{prefix}_upg_{upgrade_name}'
                row[col_name] = 1 if upgrade_name in player_state.upgrades_completed else 0

        return row
