# StarCraft 2 Real-Time Strategy Prediction using Dynamic Bayesian Networks

## Project Introduction & Scope

This project aims to build a machine learning system that predicts opponent strategies in real-time during StarCraft 2 bot vs bot matches. The system uses a **Dynamic Bayesian Network (DBN)** architecture to model the temporal dependencies and uncertainty inherent in competitive strategy games.

### Project Goals

- **Primary Goal**: Develop an ML model capable of predicting opponent build orders and strategic choices during live gameplay
- **Scope**: Train and test the DBN model using ground truth data extracted from thousands of StarCraft 2 replay files
- **Application**: Deploy the prediction system in bot vs bot matches to enable strategic counter-play and adaptive decision-making

### Why This Matters

Real-time strategy prediction in StarCraft 2 presents a challenging machine learning problem that combines:
- **Partial observability**: Players only see portions of the game state
- **Temporal reasoning**: Past actions inform future strategy predictions
- **High-dimensional state space**: Hundreds of units, buildings, and upgrades to track
- **Strategic depth**: Multiple valid paths to victory with complex interactions

Successfully solving this problem has applications in AI research, game theory, and sequential decision-making under uncertainty.

---

## Data Extraction Pipeline (IMPLEMENTED)

**Location**: `quickstart.py` and `./src_new/`

The data extraction pipeline is fully implemented and production-ready. It processes StarCraft 2 replay files using `pysc2` to generate comprehensive ground truth game state data.

### Output Data Format

The pipeline saves processed data as a **Kaggle-ready dataset** consisting of:

1. **Parquet files** containing raw game loop information
   - Wide-format tables with one row per timestep
   - Columns include: game_loop, timestamp_seconds, player resources, unit positions, building states, upgrades, etc.
   - Consistent unit IDs tracked across frames (e.g., `p1_marine_001`, `p1_marine_002`)

2. **JSON schema files** explaining the structure of the parquet files
   - Column metadata and descriptions
   - Data types and value ranges
   - Documentation of tracked entities

3. **Messages parquet files** containing chat/game messages
   - Timestamp, player_id, message content

### Using the Data Extraction Pipeline

#### Prerequisites

Before running the extraction pipeline, ensure you have:

- **Python 3.9+** installed
- **StarCraft II** game installed on your system
- Required dependencies:
  ```bash
  pip install pandas pyarrow numpy pysc2
  ```

#### Quick Start

The simplest way to get started is using the `quickstart.py` script:

```bash
# Process a sample replay (auto-detects from replays/ directory)
python quickstart.py

# Process a specific replay file
python quickstart.py --replay path/to/replay.SC2Replay

# Specify custom output directory
python quickstart.py --output data/my_output
```

#### Python API Usage

For programmatic access, use the pipeline API directly:

```python
from pathlib import Path
from src_new.pipeline import process_replay_quick

# Process a single replay
result = process_replay_quick(
    replay_path=Path("replays/game1.SC2Replay"),
    output_dir=Path("data/processed")
)

if result['success']:
    print(f"Processing time: {result['stats']['processing_time_seconds']:.2f}s")
    print(f"Rows written: {result['stats']['rows_written']:,}")
    print(f"Output file: {result['output_files']['game_state']}")
```

#### Batch Processing

To process multiple replays in parallel:

```python
from pathlib import Path
from src_new.pipeline import process_directory_quick

# Process all replays in a directory
results = process_directory_quick(
    replay_dir=Path("replays/"),
    output_dir=Path("data/processed"),
    num_workers=4  # Parallel processing with 4 workers
)

# Check results
for result in results:
    if result['success']:
        print(f"✓ {result['replay_name']}: {result['stats']['rows_written']} rows")
    else:
        print(f"✗ {result['replay_name']}: {result['error']}")
```

#### Reading Extracted Data

Load and analyze the parquet files using pandas:

```python
import pandas as pd

# Load game state data
df = pd.read_parquet("data/processed/game1_game_state.parquet")

# Basic statistics
print(f"Game duration: {df['timestamp_seconds'].max():.1f} seconds")
print(f"Total timesteps: {len(df):,}")
print(f"Tracked features: {len(df.columns):,}")

# Analyze player 1's economy over time
df[['timestamp_seconds', 'p1_minerals', 'p1_vespene', 'p1_supply_used']].plot(x='timestamp_seconds')

# Load messages
messages = pd.read_parquet("data/processed/game1_messages.parquet")
print(messages)

# Load schema documentation
import json
with open("data/processed/game1_schema.json") as f:
    schema = json.load(f)
    print(schema['columns']['p1_marine_001_x'])
```

#### Performance Characteristics

- **Processing Speed**: ~0.5-2 seconds per 1,000 game loops
- **Output Size**: ~10-50 MB parquet file per 10-minute game
- **Memory Usage**: 1-2 GB peak during processing
- **Parallel Scaling**: Nearly linear with CPU cores

For more detailed usage information, see:
- `docs/usage.md` - Comprehensive usage guide
- `docs/data_dictionary.md` - Complete schema reference
- `examples/` - Jupyter notebook examples

---

## Ground Truth Strategy Index (TO BE IMPLEMENTED)

---

## Data Discretization (TO BE IMPLEMENTED)

---

## Database Expansion (TO BE IMPLEMENTED)

---

## DBN Architecture (TO BE IMPLEMENTED)

---

## DBN Training & Testing (TO BE IMPLEMENTED)

---

## Mixture of Experts (Stretch Goal) (TO BE IMPLEMENTED)

---

## Repository Structure

This repository is organized into several key directories and files:

### Core Directories

- **`./src_new/`** - Current data extraction pipeline (PRODUCTION)
  - Uses `pysc2` for full game-state reconstruction
  - Complete ground truth extraction from replay files
  - Modular architecture with extractors, pipeline, and utilities
  - Subdirectories:
    - `extraction/` - Core extraction components (replay_loader, state_extractor, parquet_writer)
    - `extractors/` - Specialized extractors (units, buildings, economy, upgrades)
    - `pipeline/` - Pipeline orchestration and batch processing
    - `utils/` - Validation, documentation, and utility functions

- **`./Reference_Files/`** - Archive of old data pipeline and research
  - **`sc2reader_extraction/`** - Old data pipeline using `sc2reader` library
    - **Deprecated**: `sc2reader` is designed for event-based replay analysis, not full game-state reconstruction
    - **Why replaced**: Could not reliably extract complete frame-by-frame state needed for DBN training
    - **Migration**: Transitioned to `pysc2` (see `./src_new/`) for comprehensive state extraction
  - `pysc2_extraction/` - Research and prototypes leading to current pipeline
  - `research/` - Background research, API exploration, and proof-of-concepts

- **`./docs/`** - Comprehensive documentation
  - `installation.md` - Setup and installation guide
  - `usage.md` - Detailed usage examples and patterns
  - `architecture.md` - System design and component descriptions
  - `data_dictionary.md` - Complete schema reference for output data
  - `troubleshooting.md` - Common issues and solutions
  - `api_reference.md` - Public API documentation

- **`./examples/`** - Jupyter notebook tutorials
  - `01_basic_extraction.ipynb` - Extract a single replay
  - `02_batch_processing.ipynb` - Process multiple replays
  - `03_data_analysis.ipynb` - Analyze extracted data
  - `04_ml_pipeline.ipynb` - Use data for ML training

- **`./tests/`** - Comprehensive test suite (79+ tests)
  - Unit tests for all pipeline components
  - Integration tests for end-to-end workflows
  - Validation tests for output quality

- **`./replays/`** - Replay files for processing
  - Place `.SC2Replay` files here for batch processing
  - Auto-detected by `quickstart.py`

- **`./bots/`** - Bot implementations for live gameplay
  - StarCraft 2 bot code for testing strategy prediction

- **`./config/`** and **`./config_new/`** - Configuration files
  - Pipeline settings, output formats, and processing options

- **`./scripts/`** - Utility scripts
  - Helper scripts for data management and processing

### Key Files

- **`quickstart.py`** - Main entry point for data extraction
  - Easiest way to get started with the pipeline
  - Includes prerequisite checking and example workflows
  - Run with `python quickstart.py --help` for options

- **`quickstart_read_data.py`** - Example script for loading and analyzing extracted data

- **`requirements.txt`** - Full project dependencies

- **`requirements_extraction.txt`** - Dependencies for data extraction only

- **`requirements_testing.txt`** - Dependencies for running tests

- **`setup.py`** - Package installation configuration

- **`verify_installation.py`** - Installation verification script

- **`run_tests.py`** - Test runner for the test suite

### Documentation Files

- **`README_SC2_PIPELINE.md`** - Detailed pipeline documentation (more technical than this README)

- **`CHANGELOG.md`** - Project version history and changes

- **`CONTRIBUTING.md`** - Guidelines for contributing to the project

- **`IMPLEMENTATION_SUMMARY.md`** - Summary of implementation phases

- **`TESTING_AND_RESULTS.md`** - Test results and validation reports

### Excluded from Documentation

The following directories/files are excluded per `.gitignore` and not relevant to the public repository structure:

- Virtual environments (`.venv*`, `env/`, `venv/`)
- Python cache files (`__pycache__/`, `*.pyc`)
- IDE configurations (`.idea/`, `.vscode/`)
- Output data directories (`data/processed/`, `data/raw/`, `data/quickstart/`)
- Log files (`logs/`, `*.log`)
- Build artifacts (`build/`, `dist/`, `*.egg-info/`)
- Temporary files (`.claude/`, `prompts/`)

---

## Getting Started

1. **Install prerequisites**: Ensure Python 3.9+ and StarCraft II are installed
2. **Install dependencies**: `pip install -r requirements_extraction.txt`
3. **Verify installation**: `python verify_installation.py`
4. **Run quick start**: `python quickstart.py`
5. **Explore documentation**: See `docs/` for detailed guides
6. **Try examples**: Open Jupyter notebooks in `examples/`

---

## Project Status

**Current Phase**: Data Extraction Pipeline - COMPLETE ✅

**Next Phase**: Ground Truth Strategy Index (defining strategy labels for classification)

For detailed implementation status, see:
- `CHANGELOG.md` - Version history
- `README_SC2_PIPELINE.md` - Pipeline documentation
- `IMPLEMENTATION_SUMMARY.md` - Phase-by-phase summary

---

## License

This project is licensed under the GPLv3 License - see the `LICENSE` file for details.

---

## Acknowledgments

- **pysc2 team** - For the excellent StarCraft II API
- **SC2 Community** - For replay datasets and research
- **AI Arena** - For bot vs bot replay inspiration
