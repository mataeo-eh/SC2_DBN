# SC2 Replay Data Extraction System

Extract frame-by-frame game state data from StarCraft II replay files for Dynamic Bayesian Network (DBN) training and strategy prediction.

## Features

- ✅ Comprehensive data extraction (units, buildings, upgrades, resources, messages)
- ✅ Frame-by-frame state reconstruction
- ✅ Support for both ladder and AI Arena bot replays
- ✅ Multiple output formats (JSON, Parquet)
- ✅ Configurable sampling intervals
- ✅ Building state differentiation (started/existing/destroyed/cancelled)
- ✅ Tech tier calculation
- ✅ Batch processing support

## Quick Start

### Installation

```bash
# Install dependencies
pip install sc2reader==1.8.0 pandas>=2.0.0 pyarrow>=10.0.0
```

### Basic Usage

#### Extract a Single Replay

```bash
python extract_single_replay.py
```

Or using the API:

```python
from src.main import ReplayExtractor

# Initialize extractor
extractor = ReplayExtractor(
    output_format='json',
    frame_interval=112,  # 5 seconds @ Faster speed
    verbose=True
)

# Extract replay
result = extractor.extract('path/to/replay.SC2Replay')
```

#### Batch Processing

```bash
python extract_batch.py
```

Or using the API:

```python
extractor = ReplayExtractor(output_format='parquet')

results = extractor.extract_batch([
    'replay1.SC2Replay',
    'replay2.SC2Replay',
    'replay3.SC2Replay'
])
```

#### Command-Line Interface

```bash
# Extract single replay
python -m src.main replay.SC2Replay -o data/processed -f json

# Batch process directory
python -m src.main replays/ -o data/processed -f parquet

# Custom sampling interval (10 seconds)
python -m src.main replay.SC2Replay -i 224 -v
```

## Extracted Data

### Frame-by-Frame Data

**Units:**
- Unit name, position, ownership, lifecycle (born/alive/dead)

**Buildings:**
- Building name, position, ownership
- States: started, existing, constructing, destroyed, cancelled

**Upgrades:**
- Upgrade completion events
- Current upgrades per player

**Resources:**
- Minerals, vespene (current and collection rates)
- Supply used/made
- Worker counts
- Army value

**Derived Features:**
- Tech tier (1/2/3)
- Base count
- Production capacity

**Messages:**
- All game messages with timestamps

### Output Formats

#### JSON Output
```
data/processed/
├── {replay_hash}_metadata.json
└── {replay_hash}_frames.json
```

#### Parquet Output (Recommended for Large Datasets)
```
data/processed/
├── replay_metadata.parquet
├── frame_states.parquet
├── unit_counts.parquet
├── building_counts.parquet
└── upgrades.parquet
```

## Configuration

### Frame Sampling Interval

- **Default:** 112 frames (5 seconds @ Faster speed)
- **Faster (1 sec):** 22.4 frames
- **Medium (10 sec):** 224 frames

```python
extractor = ReplayExtractor(frame_interval=224)  # 10-second intervals
```

### Output Format

```python
# JSON (human-readable, debugging)
extractor = ReplayExtractor(output_format='json')

# Parquet (efficient, large datasets)
extractor = ReplayExtractor(output_format='parquet')
```

## AI Arena Bot Replay Compatibility

This system fully supports AI Arena bot replays thanks to the `sc2reader_patch.py` module:

- ✅ Handles empty `cache_handles` in bot replays
- ✅ Uses `load_level=3` (tracker events only) for compatibility
- ✅ All required data available from tracker events

**Note:** The patch is automatically applied when importing the replay parser.

## Architecture

```
┌─────────────────┐
│  .SC2Replay     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   sc2reader     │
│  (with patch)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Event Processor │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  State Tracker  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Frame Sampler   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Output Writer   │
└─────────────────┘
```

## Project Structure

```
local-play-bootstrap-main/
├── src/
│   ├── models/          # Data models
│   ├── parser/          # Replay loading and validation
│   ├── processors/      # Event processing
│   ├── state/           # State tracking and sampling
│   ├── output/          # Output formatters
│   └── utils/           # Utilities
├── research/            # Research documentation
├── plan/                # Implementation plan
├── replays/             # Input replays (place your replays here)
├── data/processed/      # Output data
├── sc2reader_patch.py   # Bot replay compatibility patch
├── extract_single_replay.py
├── extract_batch.py
└── EXTRACTION_README.md (this file)
```

## Performance

- **Parsing:** ~25+ replays/second (single-threaded)
- **Memory:** ~1-2 GB for 1,000 replays
- **Output Size:** ~50 KB per replay (Parquet) or ~500 KB (JSON)

## Research & Planning

See the `/research` and `/plan` directories for:
- **SC2_EXTRACTION_RESEARCH.md:** Library evaluation and data availability analysis
- **AI_ARENA_COMPATIBILITY.md:** Bot replay compatibility solution
- **SC2_EXTRACTION_PLAN.md:** Detailed implementation plan

## License

Copyright (c) 2022
Licensed under the [GPLv3 license](LICENSE).
