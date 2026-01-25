# API Specifications - SC2 Replay Ground Truth Extraction Pipeline

## Overview

This document provides complete function signatures and interfaces for all pipeline components with type hints, parameter descriptions, return values, and usage examples.

---

## Module: `replay_loader.py`

### Class: `ReplayLoader`

Loads and initializes SC2 replays through pysc2 interface.

```python
from typing import Optional, Tuple
from pysc2.lib import run_configs, replay
from s2clientprotocol import sc2api_pb2 as sc_pb

class ReplayLoader:
    """Handles loading and validation of SC2 replay files."""

    def __init__(self, sc2_version: Optional[str] = None):
        """
        Initialize replay loader.

        Args:
            sc2_version: Specific SC2 version to use (e.g., "5.0.12").
                        If None, uses latest available version.
        """
        pass

    def load_replay(
        self,
        replay_path: str,
        player_id: int = 1,
        step_mul: int = 8
    ) -> Tuple['Controller', 'ReplayData']:
        """
        Load replay file and start SC2 controller.

        Args:
            replay_path: Path to .SC2Replay file
            player_id: Player perspective (1 or 2) for observations
            step_mul: Number of game loops per observation (default: 8)

        Returns:
            Tuple of (controller, replay_data):
                - controller: SC2 controller instance for stepping/observing
                - replay_data: Loaded replay data object

        Raises:
            FileNotFoundError: If replay file doesn't exist
            ValueError: If replay is invalid or corrupted
            VersionMismatchError: If SC2 version doesn't match replay

        Example:
            >>> loader = ReplayLoader()
            >>> controller, replay_data = loader.load_replay(
            ...     "replays/game.SC2Replay",
            ...     player_id=1,
            ...     step_mul=8
            ... )
        """
        pass

    def get_replay_info(
        self,
        replay_path: str
    ) -> sc_pb.ResponseReplayInfo:
        """
        Get replay metadata without loading full replay.

        Args:
            replay_path: Path to .SC2Replay file

        Returns:
            ResponseReplayInfo proto containing:
                - map_name
                - player_info (names, races, MMR)
                - game_duration_loops
                - base_build (SC2 version)

        Example:
            >>> info = loader.get_replay_info("replays/game.SC2Replay")
            >>> print(f"Map: {info.map_name}")
            >>> print(f"Duration: {info.game_duration_loops} loops")
        """
        pass

    def validate_replay(
        self,
        replay_info: sc_pb.ResponseReplayInfo,
        min_duration_loops: int = 1000,
        min_mmr: int = 0,
        require_1v1: bool = True
    ) -> bool:
        """
        Validate replay meets criteria for processing.

        Args:
            replay_info: Replay info from get_replay_info()
            min_duration_loops: Minimum game length in loops
            min_mmr: Minimum player MMR
            require_1v1: If True, only accept 1v1 games

        Returns:
            True if replay is valid, False otherwise

        Example:
            >>> info = loader.get_replay_info("replays/game.SC2Replay")
            >>> if loader.validate_replay(info, min_duration_loops=2000):
            ...     # Process replay
        """
        pass

    @staticmethod
    def get_interface_options(
        raw: bool = True,
        score: bool = True
    ) -> sc_pb.InterfaceOptions:
        """
        Create InterfaceOptions for maximum observation detail.

        Args:
            raw: Enable raw data interface (REQUIRED for ground truth)
            score: Enable detailed score data

        Returns:
            InterfaceOptions configured for ground truth extraction

        Example:
            >>> interface = ReplayLoader.get_interface_options()
            >>> # Use with controller.start_replay(options=interface)
        """
        pass
```

---

## Module: `game_loop_iterator.py`

### Class: `GameLoopIterator`

Iterates through replay game loops and yields observations.

```python
from typing import Iterator, Optional
from s2clientprotocol import sc2api_pb2 as sc_pb

class GameLoopIterator:
    """Iterates through game loops in a replay."""

    def __init__(
        self,
        controller: 'Controller',
        step_mul: int = 8,
        start_loop: int = 0,
        end_loop: Optional[int] = None
    ):
        """
        Initialize game loop iterator.

        Args:
            controller: SC2 controller instance
            step_mul: Number of loops to advance per step
            start_loop: Starting game loop (for resuming)
            end_loop: Ending game loop (None = until game ends)
        """
        pass

    def __iter__(self) -> Iterator[sc_pb.ResponseObservation]:
        """
        Iterate through game loops.

        Yields:
            ResponseObservation proto for each game loop

        Example:
            >>> iterator = GameLoopIterator(controller, step_mul=8)
            >>> for obs in iterator:
            ...     game_loop = obs.observation.game_loop
            ...     # Extract data from obs
        """
        pass

    def iterate_with_callback(
        self,
        callback: callable,
        error_handler: Optional[callable] = None
    ) -> int:
        """
        Iterate and call callback for each observation.

        Args:
            callback: Function called with (obs, game_loop) for each step
                     Should return True to continue, False to stop
            error_handler: Optional function called on errors with (error, game_loop)

        Returns:
            Number of loops processed

        Example:
            >>> def process_obs(obs, loop):
            ...     # Extract data
            ...     return True  # Continue
            >>>
            >>> count = iterator.iterate_with_callback(process_obs)
            >>> print(f"Processed {count} loops")
        """
        pass

    def get_current_loop(self) -> int:
        """Get current game loop number."""
        pass

    def is_game_ended(
        self,
        obs: sc_pb.ResponseObservation
    ) -> bool:
        """
        Check if game has ended.

        Args:
            obs: Current observation

        Returns:
            True if game has ended
        """
        pass
```

---

## Module: `state_extractor.py`

### Class: `StateExtractor`

Main orchestrator for extracting all game state components.

```python
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ExtractedState:
    """Container for extracted state at a single game loop."""
    game_loop: int
    units: Dict[str, Dict[str, Any]]
    buildings: Dict[str, Dict[str, Any]]
    economy: Dict[str, Any]
    upgrades: Dict[str, bool]
    metadata: Dict[str, Any]

class StateExtractor:
    """Extracts complete game state from observation."""

    def __init__(
        self,
        player_id: int = 1,
        track_hallucinations: bool = False
    ):
        """
        Initialize state extractor.

        Args:
            player_id: Player to extract data for (1 or 2)
            track_hallucinations: If True, track hallucination units separately
        """
        self.player_id = player_id
        self.unit_extractor = UnitExtractor(player_id)
        self.building_extractor = BuildingExtractor(player_id)
        self.economy_extractor = EconomyExtractor()
        self.upgrade_extractor = UpgradeExtractor()

    def extract(
        self,
        obs: 'ResponseObservation'
    ) -> ExtractedState:
        """
        Extract complete game state from observation.

        Args:
            obs: ResponseObservation from pysc2

        Returns:
            ExtractedState containing all game state data

        Example:
            >>> extractor = StateExtractor(player_id=1)
            >>> for obs in game_loop_iterator:
            ...     state = extractor.extract(obs)
            ...     print(f"Loop {state.game_loop}: {len(state.units)} units")
        """
        pass

    def reset(self):
        """Reset all sub-extractors (for new replay)."""
        pass
```

---

## Module: `unit_extractor.py`

### Class: `UnitExtractor`

Extracts unit information from observations.

```python
from typing import Dict, Set, Any
from dataclasses import dataclass

@dataclass
class UnitData:
    """Data for a single unit."""
    tag: int
    readable_id: str
    unit_type: int
    unit_name: str
    x: float
    y: float
    z: float
    health: float
    health_max: float
    shields: float
    shields_max: float
    energy: float
    energy_max: float
    state: str  # 'built', 'existing', 'killed'
    owner: int
    alliance: int

class UnitExtractor:
    """Extracts unit data from observations."""

    def __init__(self, player_id: int):
        """
        Initialize unit extractor.

        Args:
            player_id: Player to extract units for
        """
        self.player_id = player_id
        self.tag_to_id: Dict[int, str] = {}
        self.type_counters: Dict[int, int] = {}
        self.previous_tags: Set[int] = set()

    def extract_units(
        self,
        obs: 'ResponseObservation'
    ) -> Dict[str, UnitData]:
        """
        Extract all units from observation.

        Args:
            obs: ResponseObservation from pysc2

        Returns:
            Dictionary mapping readable_id to UnitData

        Example:
            >>> units = extractor.extract_units(obs)
            >>> for unit_id, unit_data in units.items():
            ...     print(f"{unit_id}: ({unit_data.x}, {unit_data.y})")
        """
        pass

    def get_unit_state(
        self,
        tag: int,
        current_tags: Set[int],
        dead_tags: Set[int]
    ) -> str:
        """
        Determine unit state (built/existing/killed).

        Args:
            tag: Unit tag to check
            current_tags: Set of all tags in current frame
            dead_tags: Set of tags that died this frame

        Returns:
            'built', 'existing', or 'killed'
        """
        pass

    def assign_readable_id(
        self,
        tag: int,
        unit_type: int
    ) -> str:
        """
        Assign human-readable ID to unit tag.

        Args:
            tag: Unit tag
            unit_type: Unit type ID

        Returns:
            Readable ID (e.g., "p1_marine_001")
        """
        pass

    def reset(self):
        """Reset tracking for new replay."""
        pass
```

---

## Module: `building_extractor.py`

### Class: `BuildingExtractor`

Extracts building information from observations.

```python
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class BuildingData:
    """Data for a single building."""
    tag: int
    readable_id: str
    building_type: int
    building_name: str
    x: float
    y: float
    z: float
    status: str  # 'started', 'building', 'completed', 'destroyed'
    progress: float  # 0.0 to 100.0
    started_loop: Optional[int]
    completed_loop: Optional[int]
    destroyed_loop: Optional[int]

class BuildingExtractor:
    """Extracts building data from observations."""

    def __init__(self, player_id: int):
        """
        Initialize building extractor.

        Args:
            player_id: Player to extract buildings for
        """
        self.player_id = player_id
        self.tag_to_id: Dict[int, str] = {}
        self.type_counters: Dict[int, int] = {}
        self.building_metadata: Dict[int, Dict[str, Any]] = {}

    def extract_buildings(
        self,
        obs: 'ResponseObservation',
        game_loop: int
    ) -> Dict[str, BuildingData]:
        """
        Extract all buildings from observation.

        Args:
            obs: ResponseObservation from pysc2
            game_loop: Current game loop (for timestamp tracking)

        Returns:
            Dictionary mapping readable_id to BuildingData

        Example:
            >>> buildings = extractor.extract_buildings(obs, game_loop=1000)
            >>> for building_id, data in buildings.items():
            ...     if data.status == 'completed':
            ...         print(f"{building_id} completed at loop {data.completed_loop}")
        """
        pass

    def track_building_lifecycle(
        self,
        tag: int,
        build_progress: float,
        game_loop: int,
        is_dead: bool
    ) -> str:
        """
        Track building lifecycle and determine status.

        Args:
            tag: Building tag
            build_progress: Current build progress (0.0-1.0)
            game_loop: Current game loop
            is_dead: If building died this frame

        Returns:
            Status: 'started', 'building', 'completed', 'destroyed'
        """
        pass

    def reset(self):
        """Reset tracking for new replay."""
        pass
```

---

## Module: `economy_extractor.py`

### Class: `EconomyExtractor`

Extracts economy data from observations.

```python
from dataclasses import dataclass

@dataclass
class EconomyData:
    """Economy data for a player."""
    minerals: int
    vespene: int
    supply_used: int
    supply_cap: int
    supply_workers: int
    supply_army: int
    idle_workers: int
    army_count: int

class EconomyExtractor:
    """Extracts economy data from observations."""

    def extract_economy(
        self,
        obs: 'ResponseObservation'
    ) -> EconomyData:
        """
        Extract economy data from observation.

        Args:
            obs: ResponseObservation from pysc2

        Returns:
            EconomyData with all economy metrics

        Example:
            >>> economy = extractor.extract_economy(obs)
            >>> print(f"Resources: {economy.minerals}m / {economy.vespene}g")
            >>> print(f"Supply: {economy.supply_used}/{economy.supply_cap}")
        """
        pass
```

---

## Module: `upgrade_extractor.py`

### Class: `UpgradeExtractor`

Extracts upgrade data from observations.

```python
from typing import Dict, Set
from dataclasses import dataclass

@dataclass
class UpgradeInfo:
    """Information about a single upgrade."""
    upgrade_id: int
    name: str
    category: str  # 'weapons', 'armor', 'shields', 'other'
    level: int
    completed_loop: int

class UpgradeExtractor:
    """Extracts upgrade data from observations."""

    def __init__(self):
        self.previous_upgrades: Set[int] = set()
        self.upgrade_metadata: Dict[int, UpgradeInfo] = {}

    def extract_upgrades(
        self,
        obs: 'ResponseObservation',
        game_loop: int
    ) -> Dict[str, bool]:
        """
        Extract upgrades from observation.

        Args:
            obs: ResponseObservation from pysc2
            game_loop: Current game loop (for timestamp tracking)

        Returns:
            Dictionary mapping upgrade_name to completion status

        Example:
            >>> upgrades = extractor.extract_upgrades(obs, game_loop=5000)
            >>> if upgrades.get('ground_weapons_1'):
            ...     print("Weapons level 1 completed")
        """
        pass

    def parse_upgrade_name(
        self,
        upgrade_id: int
    ) -> UpgradeInfo:
        """
        Parse upgrade ID to extract category and level.

        Args:
            upgrade_id: Upgrade ID from observation

        Returns:
            UpgradeInfo with parsed data

        Example:
            >>> info = extractor.parse_upgrade_name(7)
            >>> print(f"{info.name}: {info.category} level {info.level}")
        """
        pass

    def reset(self):
        """Reset tracking for new replay."""
        pass
```

---

## Module: `wide_table_builder.py`

### Class: `WideTableBuilder`

Transforms extracted state into wide-format rows.

```python
from typing import Dict, List, Any
from .state_extractor import ExtractedState
from .schema_manager import Schema

class WideTableBuilder:
    """Builds wide-format table rows from extracted state."""

    def __init__(self, schema: Schema):
        """
        Initialize wide table builder.

        Args:
            schema: Column schema definition
        """
        self.schema = schema

    def build_row(
        self,
        state: ExtractedState
    ) -> Dict[str, Any]:
        """
        Build wide-format row from extracted state.

        Args:
            state: Extracted state for a single game loop

        Returns:
            Dictionary mapping column names to values (with NaN for missing)

        Example:
            >>> row = builder.build_row(state)
            >>> print(row.keys())  # All columns
            >>> print(row['p1_marine_001_x'])  # Specific value or NaN
        """
        pass

    def build_batch(
        self,
        states: List[ExtractedState]
    ) -> List[Dict[str, Any]]:
        """
        Build multiple rows efficiently.

        Args:
            states: List of extracted states

        Returns:
            List of wide-format row dictionaries

        Example:
            >>> rows = builder.build_batch(all_states)
            >>> df = pd.DataFrame(rows)
        """
        pass

    def get_column_names(self) -> List[str]:
        """Get list of all column names in order."""
        pass
```

---

## Module: `schema_manager.py`

### Class: `SchemaManager`

Manages column schema generation and documentation.

```python
from typing import Dict, List, Set, Any
from dataclasses import dataclass
import json

@dataclass
class ColumnDefinition:
    """Definition for a single column."""
    name: str
    dtype: str
    description: str
    nullable: bool = True
    default_value: Any = None

class Schema:
    """Column schema for wide table."""

    def __init__(self):
        self.columns: List[ColumnDefinition] = []
        self.metadata: Dict[str, Any] = {}

    def add_column(self, column: ColumnDefinition):
        """Add column to schema."""
        pass

    def to_dict(self) -> Dict:
        """Export schema as dictionary."""
        pass

    def to_json(self, path: str):
        """Save schema as JSON file."""
        pass

    @classmethod
    def from_json(cls, path: str) -> 'Schema':
        """Load schema from JSON file."""
        pass

class SchemaManager:
    """Generates and manages column schemas."""

    def __init__(self):
        self.max_unit_counts: Dict[int, int] = {}  # {unit_type: max_count}
        self.max_building_counts: Dict[int, int] = {}
        self.upgrade_set: Set[int] = set()

    def scan_replay_for_schema(
        self,
        controller: 'Controller',
        player_id: int
    ) -> Schema:
        """
        Scan replay to determine column schema.

        Args:
            controller: SC2 controller with loaded replay
            player_id: Player to scan for

        Returns:
            Schema with all columns defined

        Example:
            >>> manager = SchemaManager()
            >>> schema = manager.scan_replay_for_schema(controller, player_id=1)
            >>> print(f"Schema has {len(schema.columns)} columns")
        """
        pass

    def generate_schema(
        self,
        player_ids: List[int] = [1, 2]
    ) -> Schema:
        """
        Generate schema from accumulated max counts.

        Args:
            player_ids: Players to include in schema

        Returns:
            Complete Schema object

        Example:
            >>> schema = manager.generate_schema(player_ids=[1, 2])
            >>> schema.to_json('schemas/game_schema.json')
        """
        pass

    def update_max_counts(
        self,
        units: Dict[str, Any],
        buildings: Dict[str, Any],
        upgrades: Dict[str, bool]
    ):
        """
        Update max counts from extracted state.

        Args:
            units: Unit data
            buildings: Building data
            upgrades: Upgrade data
        """
        pass

    def reset(self):
        """Reset accumulated counts."""
        pass
```

---

## Module: `parquet_writer.py`

### Class: `ParquetWriter`

Writes data to Parquet files.

```python
from typing import List, Dict, Any, Optional
import pandas as pd
from pathlib import Path

class ParquetWriter:
    """Writes game state data to Parquet format."""

    def __init__(
        self,
        compression: str = 'snappy',
        use_dictionary: bool = True
    ):
        """
        Initialize Parquet writer.

        Args:
            compression: Compression codec ('snappy', 'gzip', 'zstd')
            use_dictionary: Use dictionary encoding for string columns
        """
        self.compression = compression
        self.use_dictionary = use_dictionary

    def write_game_state(
        self,
        rows: List[Dict[str, Any]],
        output_path: Path,
        metadata: Optional[Dict[str, str]] = None
    ):
        """
        Write game state to Parquet file.

        Args:
            rows: List of wide-format row dictionaries
            output_path: Path to output .parquet file
            metadata: Optional metadata to embed in file

        Example:
            >>> writer = ParquetWriter(compression='snappy')
            >>> writer.write_game_state(
            ...     rows=all_rows,
            ...     output_path=Path('data/processed/game_parsed.parquet'),
            ...     metadata={'replay_name': 'game.SC2Replay', 'sc2_version': '5.0.12'}
            ... )
        """
        pass

    def write_dataframe(
        self,
        df: pd.DataFrame,
        output_path: Path,
        metadata: Optional[Dict[str, str]] = None
    ):
        """
        Write DataFrame to Parquet file.

        Args:
            df: Pandas DataFrame
            output_path: Path to output .parquet file
            metadata: Optional metadata to embed in file
        """
        pass

    def append_to_parquet(
        self,
        rows: List[Dict[str, Any]],
        output_path: Path
    ):
        """
        Append rows to existing Parquet file.

        Args:
            rows: New rows to append
            output_path: Path to existing .parquet file

        Note:
            Schema must match existing file
        """
        pass

    @staticmethod
    def read_parquet_metadata(
        path: Path
    ) -> Dict[str, str]:
        """
        Read metadata from Parquet file.

        Args:
            path: Path to .parquet file

        Returns:
            Dictionary of metadata key-value pairs
        """
        pass
```

---

## Module: `replay_processor.py`

### Class: `ReplayProcessor`

Main worker process for processing replays.

```python
import multiprocessing
from pathlib import Path
from typing import Optional

class ReplayProcessor(multiprocessing.Process):
    """Worker process for processing replays in parallel."""

    def __init__(
        self,
        proc_id: int,
        replay_queue: multiprocessing.JoinableQueue,
        stats_queue: multiprocessing.Queue,
        output_dir: Path,
        step_mul: int = 8,
        two_pass: bool = True
    ):
        """
        Initialize replay processor.

        Args:
            proc_id: Unique process ID
            replay_queue: Queue of replay paths to process
            stats_queue: Queue for sending progress stats
            output_dir: Directory for output files
            step_mul: Game loops per observation
            two_pass: Use two-pass schema discovery
        """
        super().__init__()
        self.proc_id = proc_id
        self.replay_queue = replay_queue
        self.stats_queue = stats_queue
        self.output_dir = output_dir
        self.step_mul = step_mul
        self.two_pass = two_pass

    def run(self):
        """Main process loop - pulls replays and processes them."""
        pass

    def process_replay(
        self,
        replay_path: Path
    ) -> bool:
        """
        Process a single replay file.

        Args:
            replay_path: Path to replay file

        Returns:
            True if successful, False otherwise
        """
        pass

    def process_single_pass(
        self,
        replay_path: Path
    ):
        """Process replay in single pass (dynamic schema)."""
        pass

    def process_two_pass(
        self,
        replay_path: Path
    ):
        """Process replay in two passes (schema discovery + extraction)."""
        pass
```

---

## Module: `batch_controller.py`

### Function: `run_batch_processing`

Main entry point for batch processing.

```python
from pathlib import Path
from typing import List, Optional
import multiprocessing

def run_batch_processing(
    replay_dir: Path,
    output_dir: Path,
    num_workers: int = 4,
    step_mul: int = 8,
    two_pass: bool = True,
    file_pattern: str = "*.SC2Replay",
    min_duration_loops: int = 1000
) -> Dict[str, Any]:
    """
    Process multiple replays in parallel.

    Args:
        replay_dir: Directory containing replay files
        output_dir: Directory for output Parquet files
        num_workers: Number of parallel worker processes
        step_mul: Game loops per observation
        two_pass: Use two-pass processing (recommended)
        file_pattern: Glob pattern for replay files
        min_duration_loops: Minimum replay length

    Returns:
        Dictionary with processing statistics:
            - total_replays: Number of replays found
            - processed: Number successfully processed
            - failed: Number that failed
            - skipped: Number skipped (too short, etc.)
            - total_time: Total processing time

    Example:
        >>> results = run_batch_processing(
        ...     replay_dir=Path('replays/'),
        ...     output_dir=Path('data/processed/'),
        ...     num_workers=4,
        ...     step_mul=8
        ... )
        >>> print(f"Processed {results['processed']} / {results['total_replays']}")
    """
    pass

def setup_queues(
    replay_paths: List[Path],
    num_workers: int
) -> tuple:
    """
    Set up multiprocessing queues.

    Returns:
        (replay_queue, stats_queue)
    """
    pass

def start_workers(
    num_workers: int,
    replay_queue: multiprocessing.JoinableQueue,
    stats_queue: multiprocessing.Queue,
    output_dir: Path,
    step_mul: int,
    two_pass: bool
) -> List[ReplayProcessor]:
    """
    Start worker processes.

    Returns:
        List of worker process instances
    """
    pass

def monitor_progress(
    stats_queue: multiprocessing.Queue,
    total_replays: int
):
    """
    Monitor and print progress from workers.

    Runs in separate thread.
    """
    pass
```

---

## Type Hints Reference

Common types used throughout the API:

```python
from typing import TypeAlias
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib import run_configs

# Type aliases for clarity
Controller: TypeAlias = 'run_configs.Controller'
ResponseObservation: TypeAlias = sc_pb.ResponseObservation
ReplayData: TypeAlias = 'run_configs.ReplayData'
Unit: TypeAlias = sc_pb.Unit
```

---

## Error Types

Custom exceptions for the pipeline:

```python
class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass

class ReplayLoadError(PipelineError):
    """Failed to load replay."""
    pass

class VersionMismatchError(PipelineError):
    """SC2 version doesn't match replay."""
    pass

class MapNotFoundError(PipelineError):
    """Replay map file not found."""
    pass

class ExtractionError(PipelineError):
    """Error during state extraction."""
    pass

class SchemaError(PipelineError):
    """Error in schema generation or validation."""
    pass

class WriteError(PipelineError):
    """Error writing output file."""
    pass
```

---

## Configuration

Configuration dataclass for pipeline settings:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PipelineConfig:
    """Configuration for extraction pipeline."""

    # Input/Output
    replay_dir: Path
    output_dir: Path
    file_pattern: str = "*.SC2Replay"

    # Processing
    num_workers: int = 4
    step_mul: int = 8
    two_pass: bool = True

    # Validation
    min_duration_loops: int = 1000
    min_mmr: int = 0
    require_1v1: bool = True

    # Output
    compression: str = 'snappy'
    include_metadata: bool = True

    # Performance
    max_memory_mb: int = 2000  # Per worker

    def validate(self):
        """Validate configuration values."""
        assert self.num_workers > 0
        assert self.step_mul > 0
        assert self.replay_dir.exists()
        self.output_dir.mkdir(parents=True, exist_ok=True)
```

---

## Summary

This API provides:
- **Type safety**: Full type hints for all functions
- **Clear contracts**: Explicit parameter descriptions and return types
- **Comprehensive**: Complete coverage of all pipeline components
- **Documented**: Examples for all major functions
- **Extensible**: Easy to add new extractors or processors

All components follow consistent patterns and are designed to work together seamlessly in the pipeline architecture.
