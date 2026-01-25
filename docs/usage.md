# Usage Guide

Complete guide to using the SC2 Replay Ground Truth Extraction Pipeline.

## Table of Contents

- [Quick Start](#quick-start)
- [Basic Usage Patterns](#basic-usage-patterns)
- [Processing Single Replays](#processing-single-replays)
- [Batch Processing](#batch-processing)
- [Configuration Options](#configuration-options)
- [Output Formats](#output-formats)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)

---

## Quick Start

### Process Your First Replay

```python
from pathlib import Path
from src_new.pipeline import process_replay_quick

# Process a single replay
result = process_replay_quick(
    replay_path=Path("replays/game1.SC2Replay"),
    output_dir=Path("data/processed")
)

# Check result
if result['success']:
    print(f"Success! Processed in {result['stats']['processing_time_seconds']:.2f}s")
    print(f"Output: {result['output_files']['game_state']}")
else:
    print(f"Failed: {result['error']}")
```

---

## Basic Usage Patterns

### Pattern 1: Quick Single Replay

The simplest way to process a replay:

```python
from pathlib import Path
from src_new.pipeline import process_replay_quick

result = process_replay_quick(
    replay_path=Path("replays/my_game.SC2Replay"),
    output_dir=Path("data/processed")
)

print(result)
# {
#     'success': True,
#     'stats': {
#         'processing_time_seconds': 12.5,
#         'rows_written': 1234,
#         'messages_written': 15
#     },
#     'output_files': {
#         'game_state': Path('data/processed/my_game_game_state.parquet'),
#         'messages': Path('data/processed/my_game_messages.parquet'),
#         'schema': Path('data/processed/my_game_schema.json')
#     }
# }
```

### Pattern 2: Process Directory

Process all replays in a folder:

```python
from pathlib import Path
from src_new.pipeline import process_directory_quick

results = process_directory_quick(
    replay_dir=Path("replays/"),
    output_dir=Path("data/processed"),
    num_workers=4  # Use 4 CPU cores
)

print(f"Processed {results['successful_count']}/{results['total_replays']} replays")
print(f"Total time: {results['total_time_seconds']:.2f}s")
print(f"Average: {results['average_time_per_replay']:.2f}s per replay")

# Check failures
if results['failed']:
    print("\nFailed replays:")
    for replay_path, error in results['failed']:
        print(f"  {replay_path.name}: {error}")
```

### Pattern 3: Custom Configuration

Use custom settings:

```python
from pathlib import Path
from src_new.pipeline import ReplayExtractionPipeline

# Create pipeline with custom config
config = {
    'show_cloaked': True,           # Show cloaked units (perfect info)
    'show_burrowed_shadows': True,  # Show burrowed units
    'processing_mode': 'two_pass',  # Two-pass for consistent schema
    'step_size': 22,                # Sample every 22 game loops (~1 second)
    'compression': 'snappy',        # Parquet compression
}

pipeline = ReplayExtractionPipeline(config)

result = pipeline.process_replay(
    replay_path=Path("replays/game1.SC2Replay"),
    output_dir=Path("data/processed")
)
```

---

## Processing Single Replays

### Method 1: Quick Function (Recommended)

```python
from pathlib import Path
from src_new.pipeline import process_replay_quick

result = process_replay_quick(
    replay_path=Path("replays/game1.SC2Replay"),
    output_dir=Path("data/processed")
)

# Result contains:
# - success: bool
# - stats: dict with processing metrics
# - output_files: dict with paths to generated files
# - error: str (if success=False)
```

### Method 2: Pipeline Object

For more control:

```python
from pathlib import Path
from src_new.pipeline import ReplayExtractionPipeline

# Create pipeline
pipeline = ReplayExtractionPipeline()

# Process replay
result = pipeline.process_replay(
    replay_path=Path("replays/game1.SC2Replay"),
    output_dir=Path("data/processed")
)

# Access pipeline components
schema = pipeline.schema_manager
validator = pipeline.validator
```

### Method 3: Manual Control

For maximum flexibility:

```python
from pathlib import Path
from src_new.pipeline.replay_loader import ReplayLoader
from src_new.pipeline.game_loop_iterator import GameLoopIterator
from src_new.extraction.state_extractor import StateExtractor
from src_new.extraction.wide_table_builder import WideTableBuilder
from src_new.extraction.parquet_writer import ParquetWriter

# 1. Load replay
loader = ReplayLoader()
loader.load_replay(Path("replays/game1.SC2Replay"))

with loader.start_sc2_instance() as controller:
    info = loader.get_replay_info(controller)
    loader.start_replay(controller, observed_player_id=1)

    # 2. Create extractors
    state_extractor = StateExtractor()
    wide_table_builder = WideTableBuilder(schema_manager)

    # 3. Iterate and extract
    iterator = GameLoopIterator(controller, step_mul=22)
    rows = []

    for obs in iterator:
        # Extract state
        state = state_extractor.extract_observation(obs)

        # Build wide row
        row = wide_table_builder.build_row(state)
        rows.append(row)

    # 4. Write output
    writer = ParquetWriter()
    writer.write_game_state(rows, Path("output.parquet"), schema_manager)

    controller.quit()
```

---

## Batch Processing

### Basic Batch Processing

```python
from pathlib import Path
from src_new.pipeline import process_directory_quick

results = process_directory_quick(
    replay_dir=Path("replays/"),
    output_dir=Path("data/processed"),
    num_workers=4
)

print(f"Success: {results['successful_count']}")
print(f"Failed: {results['failed_count']}")
```

### Advanced Batch Processing

```python
from pathlib import Path
from src_new.pipeline import ParallelReplayProcessor

# Create processor
processor = ParallelReplayProcessor(
    config={
        'processing_mode': 'two_pass',
        'step_size': 22
    },
    num_workers=8  # Use 8 CPU cores
)

# Process directory
results = processor.process_replay_directory(
    replay_dir=Path("replays/"),
    output_dir=Path("data/processed")
)

# Get detailed summary
summary = processor.get_processing_summary(results)
print(summary)

# Retry failed replays
if results['failed']:
    print(f"\nRetrying {len(results['failed'])} failed replays...")
    retry_results = processor.retry_failed_replays(
        failed_results=results['failed'],
        output_dir=Path("data/processed")
    )
    print(f"Retry: {retry_results['successful_count']} successful")
```

### Processing Specific Replays

```python
from pathlib import Path
from src_new.pipeline import ParallelReplayProcessor

# Get replay paths
replay_paths = [
    Path("replays/game1.SC2Replay"),
    Path("replays/game2.SC2Replay"),
    Path("replays/game3.SC2Replay"),
]

processor = ParallelReplayProcessor(num_workers=3)

results = processor.process_replay_batch(
    replay_paths=replay_paths,
    output_dir=Path("data/processed")
)

# Check individual results
for replay_path in replay_paths:
    if replay_path in results['successful']:
        print(f"✓ {replay_path.name}")
    else:
        print(f"✗ {replay_path.name}")
```

---

## Configuration Options

### Configuration Dictionary

```python
config = {
    # pysc2 observation settings
    'show_cloaked': True,                # Show cloaked units (perfect info)
    'show_burrowed_shadows': True,       # Show burrowed units
    'show_placeholders': True,           # Show placeholder buildings

    # Processing settings
    'processing_mode': 'two_pass',       # 'two_pass' or 'single_pass'
    'step_size': 22,                     # Game loops per sample (22 ≈ 1 second)
    'max_loops': None,                   # Max loops to process (None = all)

    # Output settings
    'compression': 'snappy',             # 'snappy', 'gzip', 'brotli', or None
    'parquet_version': '2.6',           # Parquet file version

    # Validation settings
    'run_validation': True,              # Validate output after processing
    'fail_on_validation_error': False,   # Fail if validation finds issues
}
```

### Processing Modes

**Two-Pass Mode** (Recommended):
- First pass: Scan replay to build complete schema
- Second pass: Extract and write data with consistent columns
- Pros: Consistent schema, all units tracked
- Cons: Slower (processes replay twice)

```python
config = {'processing_mode': 'two_pass'}
```

**Single-Pass Mode**:
- Single pass: Extract and write as you go
- Pros: Faster, lower memory
- Cons: Schema may have "ragged" columns (units appearing late not in early rows)

```python
config = {'processing_mode': 'single_pass'}
```

### Step Size Configuration

Control temporal resolution:

```python
# High resolution (every ~0.5 seconds, large files)
config = {'step_size': 11}

# Standard resolution (every ~1 second, recommended)
config = {'step_size': 22}

# Low resolution (every ~2 seconds, smaller files)
config = {'step_size': 44}
```

Game loops to seconds: `seconds ≈ game_loops / 22.4`

### Compression Options

```python
# Snappy (default) - Fast, good compression
config = {'compression': 'snappy'}

# Gzip - Slower, better compression
config = {'compression': 'gzip'}

# Brotli - Best compression, slowest
config = {'compression': 'brotli'}

# None - No compression, largest files
config = {'compression': None}
```

---

## Output Formats

### Game State Parquet

**File**: `{replay_name}_game_state.parquet`

**Schema**:
- `game_loop` (int64): Game loop number
- `timestamp_seconds` (float64): Real-time timestamp
- `p1_minerals` (int64): Player 1 minerals
- `p1_vespene` (int64): Player 1 vespene
- `p1_supply_used` (int64): Player 1 supply used
- `p1_supply_cap` (int64): Player 1 supply cap
- `p1_marine_001_x` (float64): Marine #1 X coordinate
- `p1_marine_001_y` (float64): Marine #1 Y coordinate
- `p1_marine_001_state` (str): Marine #1 state (built/existing/killed)
- ... (one set of columns per unit/building)

**Example**:

```python
import pandas as pd

df = pd.read_parquet("data/processed/game1_game_state.parquet")

print(df.head())
#    game_loop  timestamp_seconds  p1_minerals  p1_marine_001_x  ...
# 0          0               0.00           50              NaN  ...
# 1         22               0.98           50              NaN  ...
# 2         44               1.96           75              NaN  ...
# 3         66               2.95          100             45.2  ...
# 4         88               3.93          125             46.8  ...
```

### Messages Parquet

**File**: `{replay_name}_messages.parquet`

**Schema**:
- `game_loop` (int64): When message was sent
- `player_id` (int64): Player who sent message (1 or 2)
- `message` (str): Message text

**Example**:

```python
messages = pd.read_parquet("data/processed/game1_messages.parquet")

print(messages)
#    game_loop  player_id        message
# 0        450          1         "glhf"
# 1       8920          2      "gg wp"
```

### Schema JSON

**File**: `{replay_name}_schema.json`

**Structure**:

```json
{
  "columns": [
    "game_loop",
    "timestamp_seconds",
    "p1_minerals",
    "p1_marine_001_x",
    ...
  ],
  "documentation": {
    "game_loop": {
      "description": "Game loop number (increases by step_size each row)",
      "type": "int64",
      "example": 1234,
      "missing_value": "Never missing"
    },
    "p1_marine_001_x": {
      "description": "X-coordinate of player 1's marine #1",
      "type": "float64",
      "example": 45.2,
      "missing_value": "NaN when unit doesn't exist"
    },
    ...
  },
  "metadata": {
    "replay_name": "game1",
    "processing_date": "2026-01-25",
    "step_size": 22,
    "total_rows": 1234
  }
}
```

---

## Advanced Features

### Validation

Automatically validate output:

```python
from pathlib import Path
from src_new.utils.validation import OutputValidator

validator = OutputValidator()

# Validate game state
report = validator.validate_game_state_parquet(
    Path("data/processed/game1_game_state.parquet")
)

if report['valid']:
    print("✓ Validation passed")
else:
    print("✗ Validation failed:")
    for error in report['errors']:
        print(f"  - {error}")

# Generate report
report_text = validator.generate_validation_report([report])
print(report_text)
```

### Custom Schema

Define your own column schema:

```python
from src_new.extraction.schema_manager import SchemaManager

# Create custom schema
schema = SchemaManager()

# Add only marines and minerals
schema.add_column('game_loop', 'int64', 'Game loop number')
schema.add_column('p1_minerals', 'int64', 'Player 1 minerals')
schema.add_unit_columns('p1', 'marine', 'marine_001')
schema.add_unit_columns('p1', 'marine', 'marine_002')

# Use in pipeline
pipeline = ReplayExtractionPipeline()
pipeline.schema_manager = schema
```

### Filtering Data

Process only specific players or time ranges:

```python
# Process only first 5 minutes (6720 game loops)
config = {
    'max_loops': 6720,
    'step_size': 22
}

pipeline = ReplayExtractionPipeline(config)
result = pipeline.process_replay(replay_path, output_dir)

# Then filter in pandas
df = pd.read_parquet(result['output_files']['game_state'])
early_game = df[df['timestamp_seconds'] <= 300]  # First 5 minutes
```

### Streaming Processing

For very large replays, use streaming:

```python
from src_new.extraction.parquet_writer import ParquetWriter

writer = ParquetWriter()
output_path = Path("data/processed/large_game_state.parquet")

# Process in chunks
chunk_size = 100
rows_buffer = []

for obs in iterator:
    row = wide_table_builder.build_row(state_extractor.extract_observation(obs))
    rows_buffer.append(row)

    if len(rows_buffer) >= chunk_size:
        writer.append_rows(rows_buffer, output_path)
        rows_buffer = []

# Write remaining rows
if rows_buffer:
    writer.append_rows(rows_buffer, output_path)
```

---

## Best Practices

### 1. Start Small

Begin with short replays to verify your setup:

```python
# Test with a 5-minute game first
result = process_replay_quick(
    replay_path=Path("replays/short_game.SC2Replay"),
    output_dir=Path("data/test")
)

# Examine output
df = pd.read_parquet(result['output_files']['game_state'])
print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
```

### 2. Use Two-Pass Mode for Analysis

For ML/analysis, use two-pass mode for consistent schemas:

```python
config = {
    'processing_mode': 'two_pass',  # Ensures consistent columns
    'step_size': 22                 # 1-second resolution
}
```

### 3. Optimize for Your Use Case

**For speed**:
```python
config = {
    'processing_mode': 'single_pass',
    'step_size': 44,  # 2-second resolution
    'compression': 'snappy'
}
```

**For quality**:
```python
config = {
    'processing_mode': 'two_pass',
    'step_size': 11,  # 0.5-second resolution
    'compression': 'gzip',
    'run_validation': True
}
```

### 4. Batch Process with Progress Tracking

```python
from pathlib import Path
from src_new.pipeline import ParallelReplayProcessor

processor = ParallelReplayProcessor(num_workers=4)

replay_dir = Path("replays/")
replays = list(replay_dir.glob("*.SC2Replay"))

print(f"Processing {len(replays)} replays...")

results = processor.process_replay_batch(
    replay_paths=replays,
    output_dir=Path("data/processed")
)

print(f"Done! {results['successful_count']}/{len(replays)} successful")
```

### 5. Handle Errors Gracefully

```python
from pathlib import Path
from src_new.pipeline import process_replay_quick

replay_paths = Path("replays/").glob("*.SC2Replay")

successful = []
failed = []

for replay_path in replay_paths:
    try:
        result = process_replay_quick(replay_path, Path("data/processed"))
        if result['success']:
            successful.append(replay_path)
        else:
            failed.append((replay_path, result['error']))
    except Exception as e:
        failed.append((replay_path, str(e)))

print(f"Successful: {len(successful)}, Failed: {len(failed)}")

# Save failed list for retry
with open("failed_replays.txt", "w") as f:
    for replay_path, error in failed:
        f.write(f"{replay_path}: {error}\n")
```

### 6. Monitor Resource Usage

```python
import psutil
import time

# Monitor processing
start_time = time.time()
start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

result = process_replay_quick(replay_path, output_dir)

end_time = time.time()
end_memory = psutil.Process().memory_info().rss / 1024 / 1024

print(f"Time: {end_time - start_time:.2f}s")
print(f"Memory: {end_memory - start_memory:.2f}MB")
```

---

## Code Examples

### Complete Example: Process and Analyze

```python
from pathlib import Path
import pandas as pd
from src_new.pipeline import process_replay_quick

# 1. Process replay
result = process_replay_quick(
    replay_path=Path("replays/game1.SC2Replay"),
    output_dir=Path("data/processed")
)

if not result['success']:
    print(f"Failed: {result['error']}")
    exit(1)

# 2. Load data
df = pd.read_parquet(result['output_files']['game_state'])
messages = pd.read_parquet(result['output_files']['messages'])

# 3. Analyze
print(f"Game duration: {df['timestamp_seconds'].max():.1f} seconds")
print(f"Total messages: {len(messages)}")

# Resource collection over time
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(df['timestamp_seconds'], df['p1_minerals'], label='P1 Minerals')
plt.plot(df['timestamp_seconds'], df['p2_minerals'], label='P2 Minerals')
plt.xlabel('Time (seconds)')
plt.ylabel('Minerals')
plt.legend()
plt.title('Mineral Collection Over Time')
plt.savefig('minerals_over_time.png')
```

### Complete Example: Batch Process with Retry

```python
from pathlib import Path
from src_new.pipeline import process_directory_quick, process_replay_quick

# First pass
results = process_directory_quick(
    replay_dir=Path("replays/"),
    output_dir=Path("data/processed"),
    num_workers=4
)

print(f"First pass: {results['successful_count']} successful")

# Retry failed with single-pass mode (faster, may work for corrupted replays)
if results['failed']:
    print(f"\nRetrying {len(results['failed'])} failed replays...")

    retry_successful = 0
    for replay_path, error in results['failed']:
        # Try with more lenient settings
        result = process_replay_quick(
            replay_path=replay_path,
            output_dir=Path("data/processed"),
            config={'processing_mode': 'single_pass'}
        )

        if result['success']:
            retry_successful += 1

    print(f"Retry: {retry_successful} now successful")
    print(f"Final: {results['successful_count'] + retry_successful} total successful")
```

---

## Next Steps

- **Data Analysis**: See [examples/03_data_analysis.ipynb](../examples/03_data_analysis.ipynb)
- **ML Pipeline**: See [examples/04_ml_pipeline.ipynb](../examples/04_ml_pipeline.ipynb)
- **Architecture**: Learn more in [architecture.md](architecture.md)
- **Data Dictionary**: Full schema reference in [data_dictionary.md](data_dictionary.md)

---

**Questions?** Check [troubleshooting.md](troubleshooting.md) or open an issue on GitHub.
