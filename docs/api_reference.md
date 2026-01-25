# API Reference

Complete reference for the SC2 Replay Ground Truth Extraction Pipeline public API.

## Table of Contents

- [Quick Functions](#quick-functions)
- [Pipeline Classes](#pipeline-classes)
- [Extraction Classes](#extraction-classes)
- [Utility Classes](#utility-classes)
- [Data Structures](#data-structures)

---

## Quick Functions

Convenient wrapper functions for common use cases.

### `process_replay_quick()`

Process a single replay with default settings.

```python
from pathlib import Path
from src_new.pipeline import process_replay_quick

result = process_replay_quick(
    replay_path: Path,
    output_dir: Path,
    config: Optional[Dict] = None
) -> Dict
```

**Parameters**:
- `replay_path` (Path): Path to .SC2Replay file
- `output_dir` (Path): Directory for output files (created if doesn't exist)
- `config` (Dict, optional): Configuration dictionary (see [Configuration](#configuration))

**Returns**: Dictionary with:
```python
{
    'success': bool,              # True if processing succeeded
    'stats': {
        'processing_time_seconds': float,
        'rows_written': int,
        'messages_written': int,
    },
    'output_files': {
        'game_state': Path,       # Path to game_state.parquet
        'messages': Path,         # Path to messages.parquet
        'schema': Path,           # Path to schema.json
    },
    'error': str or None,         # Error message if success=False
}
```

**Example**:
```python
result = process_replay_quick(
    replay_path=Path("replays/game1.SC2Replay"),
    output_dir=Path("data/processed")
)

if result['success']:
    print(f"Processed in {result['stats']['processing_time_seconds']:.2f}s")
else:
    print(f"Failed: {result['error']}")
```

### `process_directory_quick()`

Process all replays in a directory in parallel.

```python
from src_new.pipeline import process_directory_quick

results = process_directory_quick(
    replay_dir: Path,
    output_dir: Path,
    num_workers: Optional[int] = None,
    config: Optional[Dict] = None
) -> Dict
```

**Parameters**:
- `replay_dir` (Path): Directory containing .SC2Replay files
- `output_dir` (Path): Directory for output files
- `num_workers` (int, optional): Number of parallel workers (default: CPU count)
- `config` (Dict, optional): Configuration dictionary

**Returns**: Dictionary with:
```python
{
    'total_replays': int,
    'successful_count': int,
    'failed_count': int,
    'successful': List[Path],     # Paths of successful replays
    'failed': List[Tuple[Path, str]],  # (path, error) for failures
    'total_time_seconds': float,
    'average_time_per_replay': float,
}
```

**Example**:
```python
results = process_directory_quick(
    replay_dir=Path("replays/"),
    output_dir=Path("data/processed"),
    num_workers=4
)

print(f"Processed: {results['successful_count']}/{results['total_replays']}")
```

---

## Pipeline Classes

Main orchestration classes for replay processing.

### `ReplayExtractionPipeline`

End-to-end pipeline for processing a single replay.

```python
from src_new.pipeline import ReplayExtractionPipeline

pipeline = ReplayExtractionPipeline(config: Optional[Dict] = None)
```

**Methods**:

#### `process_replay()`

Process a single replay end-to-end.

```python
result = pipeline.process_replay(
    replay_path: Path,
    output_dir: Path
) -> Dict
```

Returns same structure as `process_replay_quick()`.

**Example**:
```python
pipeline = ReplayExtractionPipeline({
    'processing_mode': 'two_pass',
    'step_size': 22
})

result = pipeline.process_replay(
    replay_path=Path("game1.SC2Replay"),
    output_dir=Path("data/processed")
)
```

### `ParallelReplayProcessor`

Batch processing with multiprocessing.

```python
from src_new.pipeline import ParallelReplayProcessor

processor = ParallelReplayProcessor(
    config: Optional[Dict] = None,
    num_workers: Optional[int] = None
)
```

**Parameters**:
- `config` (Dict, optional): Configuration dictionary
- `num_workers` (int, optional): Number of worker processes (default: CPU count)

**Methods**:

#### `process_replay_batch()`

Process a list of replays in parallel.

```python
results = processor.process_replay_batch(
    replay_paths: List[Path],
    output_dir: Path
) -> Dict
```

**Parameters**:
- `replay_paths` (List[Path]): List of replay file paths
- `output_dir` (Path): Output directory

**Returns**: Same structure as `process_directory_quick()`

**Example**:
```python
processor = ParallelReplayProcessor(num_workers=8)

replay_paths = [
    Path("game1.SC2Replay"),
    Path("game2.SC2Replay"),
    Path("game3.SC2Replay"),
]

results = processor.process_replay_batch(replay_paths, Path("data/processed"))
```

#### `process_replay_directory()`

Process all replays in a directory.

```python
results = processor.process_replay_directory(
    replay_dir: Path,
    output_dir: Path,
    pattern: str = '*.SC2Replay'
) -> Dict
```

**Parameters**:
- `replay_dir` (Path): Directory to search
- `output_dir` (Path): Output directory
- `pattern` (str): Glob pattern for replay files

#### `retry_failed_replays()`

Retry replays that failed in a previous batch.

```python
retry_results = processor.retry_failed_replays(
    failed_results: List[Tuple[Path, str]],
    output_dir: Path
) -> Dict
```

**Parameters**:
- `failed_results` (List[Tuple[Path, str]]): List of (replay_path, error) from previous batch
- `output_dir` (Path): Output directory

---

## Extraction Classes

Components for extracting data from replays.

### `StateExtractor`

Extract complete game state from SC2 observations.

```python
from src_new.extraction import StateExtractor

extractor = StateExtractor()
```

**Methods**:

#### `extract_observation()`

Extract complete state from a single observation.

```python
state = extractor.extract_observation(obs) -> Dict
```

**Parameters**:
- `obs`: pysc2 observation object

**Returns**: Dictionary with:
```python
{
    'game_loop': int,
    'p1_units': Dict,          # unit_id -> unit_data
    'p2_units': Dict,
    'p1_buildings': Dict,      # building_id -> building_data
    'p2_buildings': Dict,
    'p1_economy': Dict,        # economy metrics
    'p2_economy': Dict,
    'p1_upgrades': Dict,       # upgrade_name -> bool
    'p2_upgrades': Dict,
    'messages': List[Dict],    # chat messages
}
```

#### `reset()`

Reset internal state (for two-pass mode).

```python
extractor.reset()
```

### `SchemaManager`

Manage wide-table column schema.

```python
from src_new.extraction import SchemaManager

schema = SchemaManager()
```

**Methods**:

#### `build_schema_from_states()`

Build schema from a sequence of states.

```python
schema.build_schema_from_states(states: List[Dict])
```

#### `get_column_list()`

Get ordered list of all columns.

```python
columns = schema.get_column_list() -> List[str]
```

#### `generate_documentation()`

Generate data dictionary.

```python
docs = schema.generate_documentation() -> Dict
```

Returns:
```python
{
    'column_name': {
        'description': str,
        'type': str,
        'example': Any,
        'missing_value': str,
    },
    ...
}
```

#### `save_schema()`

Save schema to JSON file.

```python
schema.save_schema(output_path: Path)
```

### `WideTableBuilder`

Transform hierarchical state to wide-format rows.

```python
from src_new.extraction import WideTableBuilder

builder = WideTableBuilder(schema: SchemaManager)
```

**Methods**:

#### `build_row()`

Transform state to wide-format row.

```python
row = builder.build_row(state: Dict) -> Dict
```

**Parameters**:
- `state` (Dict): State from `StateExtractor.extract_observation()`

**Returns**: Dictionary with one value per schema column.

#### `build_rows_batch()`

Transform multiple states in batch.

```python
rows = builder.build_rows_batch(states: List[Dict]) -> List[Dict]
```

### `ParquetWriter`

Write data to parquet files.

```python
from src_new.extraction import ParquetWriter

writer = ParquetWriter(compression: str = 'snappy')
```

**Parameters**:
- `compression` (str): Compression codec ('snappy', 'gzip', 'brotli', or None)

**Methods**:

#### `write_game_state()`

Write game state to parquet.

```python
writer.write_game_state(
    rows: List[Dict],
    output_path: Path,
    schema: SchemaManager
)
```

#### `write_messages()`

Write messages to parquet.

```python
writer.write_messages(
    messages: List[Dict],
    output_path: Path
)
```

**Message format**:
```python
{
    'game_loop': int,
    'player_id': int,
    'message': str,
}
```

---

## Utility Classes

Validation and helper utilities.

### `OutputValidator`

Validate extracted parquet files.

```python
from src_new.utils.validation import OutputValidator

validator = OutputValidator()
```

**Methods**:

#### `validate_game_state_parquet()`

Validate game state parquet file.

```python
report = validator.validate_game_state_parquet(parquet_path: Path) -> Dict
```

**Returns**:
```python
{
    'valid': bool,
    'errors': List[str],
    'warnings': List[str],
    'statistics': {
        'row_count': int,
        'column_count': int,
        'duplicate_game_loops': int,
        'negative_resources_count': int,
        ...
    }
}
```

**Checks performed**:
- No duplicate game_loops
- No negative resources
- Supply doesn't exceed cap
- Building progress is monotonic
- Unit counts match individual units
- No unexpected NaN patterns

#### `validate_messages_parquet()`

Validate messages parquet file.

```python
report = validator.validate_messages_parquet(parquet_path: Path) -> Dict
```

#### `generate_validation_report()`

Generate human-readable report.

```python
report_text = validator.generate_validation_report(
    validations: List[Dict]
) -> str
```

**Example**:
```python
validator = OutputValidator()

report = validator.validate_game_state_parquet(
    Path("data/processed/game1_game_state.parquet")
)

if report['valid']:
    print("✓ Validation passed")
else:
    print("✗ Validation failed:")
    for error in report['errors']:
        print(f"  - {error}")
```

---

## Data Structures

### Configuration

Configuration dictionary for customizing pipeline behavior.

```python
config = {
    # pysc2 observation settings
    'show_cloaked': bool,              # Show cloaked units (default: True)
    'show_burrowed_shadows': bool,     # Show burrowed units (default: True)
    'show_placeholders': bool,         # Show placeholder buildings (default: True)

    # Processing settings
    'processing_mode': str,            # 'two_pass' or 'single_pass' (default: 'two_pass')
    'step_size': int,                  # Game loops per sample (default: 22)
    'max_loops': int or None,          # Max loops to process (default: None = all)

    # Output settings
    'compression': str,                # 'snappy', 'gzip', 'brotli', or None (default: 'snappy')
    'parquet_version': str,            # Parquet file version (default: '2.6')

    # Validation settings
    'run_validation': bool,            # Validate output (default: True)
    'fail_on_validation_error': bool,  # Fail if validation errors (default: False)
}
```

### Result Dictionary

Standard result structure from processing functions.

```python
result = {
    'success': bool,                    # True if processing succeeded
    'stats': {
        'processing_time_seconds': float,
        'rows_written': int,
        'messages_written': int,
        'game_duration_seconds': float,
        'total_game_loops': int,
    },
    'output_files': {
        'game_state': Path,             # game_state.parquet
        'messages': Path,               # messages.parquet
        'schema': Path,                 # schema.json
    },
    'error': str or None,               # Error message if failed
    'validation_report': Dict or None,  # If run_validation=True
}
```

### Batch Results Dictionary

Result structure from batch processing.

```python
results = {
    'total_replays': int,
    'successful_count': int,
    'failed_count': int,
    'successful': List[Path],           # Successful replay paths
    'failed': List[Tuple[Path, str]],   # (replay_path, error_message)
    'processing_times': Dict[Path, float],  # replay_path -> seconds
    'total_time_seconds': float,
    'average_time_per_replay': float,
}
```

---

## Usage Examples

### Basic Single Replay

```python
from pathlib import Path
from src_new.pipeline import process_replay_quick

result = process_replay_quick(
    replay_path=Path("replays/game1.SC2Replay"),
    output_dir=Path("data/processed")
)

if result['success']:
    import pandas as pd
    df = pd.read_parquet(result['output_files']['game_state'])
    print(df.head())
```

### Custom Configuration

```python
from src_new.pipeline import ReplayExtractionPipeline

config = {
    'processing_mode': 'single_pass',
    'step_size': 44,  # Every 2 seconds
    'compression': 'gzip',
}

pipeline = ReplayExtractionPipeline(config)
result = pipeline.process_replay(replay_path, output_dir)
```

### Batch Processing

```python
from src_new.pipeline import ParallelReplayProcessor

processor = ParallelReplayProcessor(num_workers=8)

results = processor.process_replay_directory(
    replay_dir=Path("replays/"),
    output_dir=Path("data/processed")
)

print(f"Success: {results['successful_count']}/{results['total_replays']}")
```

### Validation

```python
from src_new.utils.validation import OutputValidator

validator = OutputValidator()

report = validator.validate_game_state_parquet(
    Path("data/processed/game1_game_state.parquet")
)

if not report['valid']:
    for error in report['errors']:
        print(f"Error: {error}")
```

### Manual Pipeline Construction

```python
from src_new.extraction import (
    StateExtractor,
    SchemaManager,
    WideTableBuilder,
    ParquetWriter
)

# Create components
extractor = StateExtractor()
schema = SchemaManager()
builder = WideTableBuilder(schema)
writer = ParquetWriter()

# Extract states (from replay iteration)
states = []
for obs in replay_iterator:
    state = extractor.extract_observation(obs)
    states.append(state)

# Build schema
schema.build_schema_from_states(states)

# Build rows
rows = builder.build_rows_batch(states)

# Write output
writer.write_game_state(rows, output_path, schema)
```

---

## Type Hints

All public functions use type hints. Import types from `typing`:

```python
from typing import Dict, List, Optional, Tuple
from pathlib import Path

def process_replay_quick(
    replay_path: Path,
    output_dir: Path,
    config: Optional[Dict] = None
) -> Dict:
    ...
```

---

## Error Handling

All public functions catch exceptions and return errors in result dictionaries:

```python
result = process_replay_quick(replay_path, output_dir)

if not result['success']:
    print(f"Error: {result['error']}")
    # Handle error...
```

For more control, use try/except:

```python
try:
    pipeline = ReplayExtractionPipeline()
    result = pipeline.process_replay(replay_path, output_dir)
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## See Also

- [Usage Guide](usage.md) - Detailed usage patterns
- [Architecture](architecture.md) - System design
- [Data Dictionary](data_dictionary.md) - Output schema
- [Troubleshooting](troubleshooting.md) - Common issues

---

**Questions?** Open an issue on GitHub or check the documentation.
