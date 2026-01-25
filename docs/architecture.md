# System Architecture

Complete architecture documentation for the SC2 Replay Ground Truth Extraction Pipeline.

## Table of Contents

- [Overview](#overview)
- [Component Diagram](#component-diagram)
- [Data Flow](#data-flow)
- [Module Descriptions](#module-descriptions)
- [Design Decisions](#design-decisions)
- [Extension Points](#extension-points)

---

## Overview

The SC2 Replay Ground Truth Extraction Pipeline is a production-ready system that processes StarCraft II replay files to extract complete ground truth game state data in wide-format parquet files.

### Key Architectural Principles

1. **Modularity**: Each component has a single, well-defined responsibility
2. **Composability**: Components can be used independently or together
3. **Configurability**: Behavior controlled through configuration dictionaries
4. **Robustness**: Comprehensive error handling at all levels
5. **Performance**: Parallel processing with efficient memory management
6. **Testability**: Components designed for easy unit testing with mocks

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   ParallelReplayProcessor                        │
│  (Batch processing with multiprocessing)                         │
│                                                                  │
│  - process_replay_batch()                                       │
│  - process_replay_directory()                                   │
│  - Manages worker pool                                          │
│  - Aggregates results                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Creates multiple instances
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ReplayExtractionPipeline                        │
│  (Main end-to-end orchestrator)                                 │
│                                                                  │
│  - process_replay()                                             │
│  - _two_pass_processing()                                       │
│  - _single_pass_processing()                                    │
└─────────┬───────────────────────────────────────────────────────┘
          │
          │ Coordinates these components:
          │
          ├─────────────────────────────────────────┐
          │                                         │
          ▼                                         ▼
┌─────────────────────┐                  ┌─────────────────────┐
│   ReplayLoader      │                  │  StateExtractor     │
│                     │                  │                     │
│ - load_replay()     │                  │ - extract_obs()     │
│ - start_sc2()       │                  │                     │
│ - get_replay_info() │                  │ Uses:               │
│                     │                  │ - UnitExtractor     │
│                     │                  │ - BuildingExtractor │
│                     │                  │ - EconomyExtractor  │
│                     │                  │ - UpgradeExtractor  │
└─────────────────────┘                  └─────────────────────┘
          │                                         │
          │                                         │
          └────────────┬────────────────────────────┘
                       │
                       │ State data flows to:
                       │
                       ▼
          ┌────────────────────────┐
          │   SchemaManager        │
          │                        │
          │ - build_schema()       │
          │ - get_column_list()    │
          │ - save_schema()        │
          └────────┬───────────────┘
                   │
                   │ Schema defines structure for:
                   │
                   ▼
          ┌────────────────────────┐
          │  WideTableBuilder      │
          │                        │
          │ - build_row()          │
          │ - add_unit_to_row()    │
          │ - add_building_to_row()│
          └────────┬───────────────┘
                   │
                   │ Wide-format rows go to:
                   │
                   ▼
          ┌────────────────────────┐
          │   ParquetWriter        │
          │                        │
          │ - write_game_state()   │
          │ - write_messages()     │
          └────────┬───────────────┘
                   │
                   ▼
          ┌────────────────────────┐
          │   OutputValidator      │
          │                        │
          │ - validate_parquet()   │
          │ - generate_report()    │
          └────────┬───────────────┘
                   │
                   ▼
          ┌────────────────────────┐
          │   Output Files         │
          │                        │
          │ - game_state.parquet   │
          │ - messages.parquet     │
          │ - schema.json          │
          └────────────────────────┘
```

---

## Data Flow

### Two-Pass Processing Mode (Recommended)

**Pass 1: Schema Discovery**

```
Replay File
    │
    ▼
ReplayLoader.load_replay()
    │
    ▼
ReplayLoader.start_sc2_instance()
    │
    ▼
For each game loop:
    controller.step()
    │
    ▼
    controller.observe()
    │
    ▼
    StateExtractor.extract_observation()
    │
    ▼
    SchemaManager._discover_entities_from_state()
    │
    └─> Builds complete column list

Result: Complete schema with all units/buildings
```

**Pass 2: Data Extraction**

```
ReplayLoader.load_replay() (reload)
    │
    ▼
StateExtractor.reset() (clear state)
    │
    ▼
For each game loop:
    controller.observe()
    │
    ▼
    StateExtractor.extract_observation()
    │
    ▼
    WideTableBuilder.build_row()
    │   (uses complete schema from Pass 1)
    │
    └─> Consistent wide-format rows
    │
    ▼
ParquetWriter.write_game_state()
    │
    ▼
OutputValidator.validate_parquet()
    │
    ▼
Output files created + validation report
```

### Single-Pass Processing Mode (Faster)

```
Replay File
    │
    ▼
ReplayLoader.load_replay()
    │
    ▼
For each game loop:
    controller.observe()
    │
    ▼
    StateExtractor.extract_observation()
    │
    ├─> SchemaManager._discover_entities_from_state()
    │   (updates schema dynamically as units appear)
    │
    ▼
    WideTableBuilder.build_row()
    │   (may have different columns per row - "ragged")
    │
    └─> Wide-format rows
    │
    ▼
ParquetWriter.write_game_state()
    │
    ▼
Output files created
```

---

## Module Descriptions

### src_new/pipeline/

#### ReplayExtractionPipeline

**Purpose**: Orchestrates end-to-end extraction for a single replay

**Responsibilities**:
- Load replay and start SC2 instance
- Choose processing mode (two-pass vs single-pass)
- Coordinate all extraction components
- Handle errors and generate result reports
- Validate output

**Key Methods**:
```python
def process_replay(replay_path: Path, output_dir: Path) -> dict:
    """Process single replay end-to-end."""

def _two_pass_processing(replay_path: Path, output_dir: Path) -> dict:
    """Two-pass mode: schema discovery then extraction."""

def _single_pass_processing(replay_path: Path, output_dir: Path) -> dict:
    """Single-pass mode: extract as you go."""
```

#### ParallelReplayProcessor

**Purpose**: Process multiple replays in parallel using multiprocessing

**Responsibilities**:
- Manage process pool
- Distribute replay jobs to workers
- Aggregate results from all workers
- Handle worker failures
- Provide retry mechanism

**Key Methods**:
```python
def process_replay_batch(replay_paths: List[Path], output_dir: Path) -> dict:
    """Process list of replays in parallel."""

def process_replay_directory(replay_dir: Path, output_dir: Path) -> dict:
    """Process all replays in a directory."""

def retry_failed_replays(failed_results, output_dir: Path) -> dict:
    """Retry replays that failed in previous batch."""
```

#### ReplayLoader

**Purpose**: Load replays and provide access to SC2 game state

**Responsibilities**:
- Load replay file
- Start SC2 instance with proper settings
- Extract replay metadata
- Provide controller for iteration

**Key Methods**:
```python
def load_replay(replay_path: Path) -> None:
    """Load replay file and validate."""

def start_sc2_instance() -> ContextManager[SC2Controller]:
    """Start SC2 instance with proper settings."""

def get_replay_info(controller) -> dict:
    """Extract replay metadata."""
```

#### GameLoopIterator

**Purpose**: Iterate through game loops efficiently

**Responsibilities**:
- Control game step size
- Track current game loop
- Yield observations
- Handle end-of-replay

**Key Methods**:
```python
def __iter__() -> Iterator[Observation]:
    """Iterate through game loops."""

def __next__() -> Observation:
    """Get next observation."""
```

### src_new/extraction/

#### StateExtractor

**Purpose**: Extract complete game state from SC2 observations

**Responsibilities**:
- Delegate to specialized extractors
- Combine all extracted data
- Track unit/building lifecycles
- Handle missing data

**Key Methods**:
```python
def extract_observation(obs) -> dict:
    """Extract complete state from observation."""

def reset() -> None:
    """Reset all internal state (for two-pass mode)."""
```

**Uses**:
- `UnitExtractor` - Track units
- `BuildingExtractor` - Track buildings
- `EconomyExtractor` - Extract resources/supply
- `UpgradeExtractor` - Track upgrades

#### SchemaManager

**Purpose**: Define and manage wide-table column schema

**Responsibilities**:
- Build schema from extracted states
- Track all columns dynamically
- Generate column documentation
- Save/load schema JSON

**Key Methods**:
```python
def build_schema_from_states(states: List[dict]) -> None:
    """Build complete schema from state sequence."""

def get_column_list() -> List[str]:
    """Get ordered list of all columns."""

def generate_documentation() -> dict:
    """Generate data dictionary."""
```

#### WideTableBuilder

**Purpose**: Transform hierarchical game state to wide-format rows

**Responsibilities**:
- Flatten nested state dictionaries
- Fill missing values with NaN
- Calculate aggregates (unit counts)
- Validate row structure

**Key Methods**:
```python
def build_row(state: dict) -> dict:
    """Transform state to wide-format row."""

def add_unit_to_row(row: dict, player: str, unit_id: str, data: dict) -> None:
    """Add unit columns to row."""

def calculate_unit_counts(units: dict) -> dict:
    """Calculate unit type counts."""
```

#### ParquetWriter

**Purpose**: Write data to parquet files with proper formatting

**Responsibilities**:
- Convert Python types to Arrow types
- Handle compression
- Write game state and messages
- Maintain file metadata

**Key Methods**:
```python
def write_game_state(rows: List[dict], output_path: Path, schema) -> None:
    """Write game state to parquet."""

def write_messages(messages: List[dict], output_path: Path) -> None:
    """Write messages to parquet."""
```

### src_new/extractors/

#### UnitExtractor

**Purpose**: Extract and track military units

**Responsibilities**:
- Filter units (exclude buildings)
- Assign consistent IDs (e.g., marine_001)
- Detect unit states (built/existing/killed)
- Track unit tags across frames

#### BuildingExtractor

**Purpose**: Extract and track buildings

**Responsibilities**:
- Filter buildings
- Track construction lifecycle
- Monitor build progress (0-100%)
- Detect status (started/building/completed/destroyed)

#### EconomyExtractor

**Purpose**: Extract economy metrics

**Responsibilities**:
- Extract minerals, vespene
- Extract supply (used/cap/army/workers)
- Extract collection rates
- Extract worker counts

#### UpgradeExtractor

**Purpose**: Track completed upgrades

**Responsibilities**:
- Detect new upgrades
- Track completion times
- Generate boolean flags

### src_new/utils/

#### OutputValidator

**Purpose**: Validate extracted parquet files

**Responsibilities**:
- Check data integrity
- Detect anomalies
- Validate schema consistency
- Generate validation reports

**Key Methods**:
```python
def validate_game_state_parquet(parquet_path: Path) -> dict:
    """Validate game state parquet."""

def generate_validation_report(validations: List[dict]) -> str:
    """Generate human-readable report."""
```

---

## Design Decisions

### 1. Two-Pass vs Single-Pass Processing

**Decision**: Support both modes, recommend two-pass

**Rationale**:
- **Two-pass**: Ensures consistent schema across all rows (critical for ML)
- **Single-pass**: Faster for exploration or when schema doesn't matter
- **Trade-off**: Speed vs consistency

### 2. Wide-Format Output

**Decision**: Use wide-format tables with one row per timestep

**Rationale**:
- ML-friendly (each feature is a column)
- Easy to load into pandas/numpy
- Efficient for time-series analysis
- Trade-off: Many columns (potentially thousands)

### 3. Parquet File Format

**Decision**: Use Apache Parquet for output

**Rationale**:
- Columnar format (efficient for analytics)
- Built-in compression
- Type-safe schema
- Industry standard for ML data

### 4. Unit ID Assignment Strategy

**Decision**: Assign IDs by type + counter (e.g., marine_001, marine_002)

**Rationale**:
- Consistent across frames
- Human-readable
- Deterministic (same replay = same IDs)
- Easy to reference in analysis

### 5. Parallel Processing with Multiprocessing

**Decision**: Use `concurrent.futures.ProcessPoolExecutor`

**Rationale**:
- True parallelism (not limited by GIL)
- Process isolation (one failure doesn't crash batch)
- Built-in Python, no external dependencies
- Simple API

### 6. Configuration via Dictionaries

**Decision**: Pass config as dicts, not config files

**Rationale**:
- Programmatic configuration
- Easy to override in code
- No file parsing overhead
- Simple to serialize/deserialize

### 7. State Tracking in Extractors

**Decision**: Extractors maintain internal state (previous frame tags)

**Rationale**:
- Required for lifecycle detection
- Enables state transitions (built/existing/killed)
- Must be reset between replays (done in two-pass mode)

### 8. Error Handling Strategy

**Decision**: Never crash - always return error in result dict

**Rationale**:
- Batch processing continues even if one replay fails
- Errors are structured and parseable
- Easy to retry failed replays
- Production-friendly

---

## Extension Points

### Adding New Extractors

To extract additional game state (e.g., camera position, APM):

1. Create new extractor in `src_new/extractors/`:
```python
class CameraExtractor:
    def extract(self, obs) -> dict:
        return {
            'camera_x': obs.observation.camera_position.x,
            'camera_y': obs.observation.camera_position.y,
        }
```

2. Add to `StateExtractor`:
```python
self.camera_extractor = CameraExtractor()

def extract_observation(self, obs):
    state['p1_camera'] = self.camera_extractor.extract(obs)
```

3. Add to `WideTableBuilder`:
```python
def add_camera_to_row(self, row: dict, player: str, camera_data: dict):
    row[f'{player}_camera_x'] = camera_data['camera_x']
    row[f'{player}_camera_y'] = camera_data['camera_y']
```

### Adding New Output Formats

To support additional output formats (e.g., CSV, HDF5):

1. Create new writer in `src_new/extraction/`:
```python
class CSVWriter:
    def write_game_state(self, rows: List[dict], output_path: Path):
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
```

2. Add option to config:
```python
config = {
    'output_format': 'csv'  # or 'parquet', 'hdf5'
}
```

3. Use in pipeline:
```python
if config['output_format'] == 'csv':
    writer = CSVWriter()
else:
    writer = ParquetWriter()
```

### Adding New Validation Rules

To add custom validation checks:

1. Extend `OutputValidator`:
```python
def validate_army_counts(self, df: pd.DataFrame) -> dict:
    """Check that army counts are reasonable."""
    errors = []

    max_army = df['p1_army_count'].max()
    if max_army > 200:  # Unreasonably high
        errors.append(f"Unrealistic army count: {max_army}")

    return {
        'check_name': 'army_counts',
        'errors': errors,
        'valid': len(errors) == 0
    }
```

2. Call in validation:
```python
def validate_game_state_parquet(self, parquet_path: Path) -> dict:
    # ... existing checks ...
    results.append(self.validate_army_counts(df))
```

### Adding New Processing Modes

To implement a new processing mode (e.g., streaming):

1. Add method to `ReplayExtractionPipeline`:
```python
def _streaming_processing(self, replay_path: Path, output_dir: Path) -> dict:
    """Process replay in streaming mode (write as you go)."""
    # Open parquet file for streaming writes
    # Process loop by loop
    # Append rows incrementally
```

2. Add to config:
```python
config = {
    'processing_mode': 'streaming'  # or 'two_pass', 'single_pass'
}
```

3. Route in `process_replay()`:
```python
if mode == 'streaming':
    return self._streaming_processing(replay_path, output_dir)
```

---

## Performance Characteristics

### Processing Speed
- **Two-pass mode**: ~2x slower than single-pass
- **Single-pass mode**: ~0.5-2 seconds per 1000 game loops
- **Parallel scaling**: Nearly linear with CPU cores

### Memory Usage
- **Two-pass mode, Pass 1**: ~100 KB - 1 MB (schema only)
- **Two-pass mode, Pass 2**: ~100-500 MB (accumulate rows)
- **Single-pass mode**: ~100-500 MB (accumulate rows)
- **Per worker (parallel)**: 100-500 MB

### Output Size
- **Game state parquet**: ~1-5 MB per 1000 rows (with compression)
- **10-minute game**: ~10-50 MB parquet file
- **Schema JSON**: ~100 KB - 1 MB

---

## Summary

The SC2 Replay Ground Truth Extraction Pipeline is designed as a modular, composable system that balances:

- **Flexibility**: Multiple processing modes and configuration options
- **Performance**: Parallel processing with efficient memory management
- **Robustness**: Comprehensive error handling and validation
- **Usability**: Simple APIs for common use cases, advanced APIs for power users
- **Extensibility**: Clear extension points for new features

The architecture follows established design patterns (Strategy, Builder, Factory) and leverages proven technologies (pysc2, Parquet, multiprocessing) to provide a production-ready ML data extraction pipeline.

---

**Next**: See [data_dictionary.md](data_dictionary.md) for complete output schema documentation.
