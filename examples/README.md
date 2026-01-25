# Example Notebooks

This directory contains Jupyter notebooks demonstrating how to use the SC2 Replay Ground Truth Extraction Pipeline.

## Prerequisites

Install Jupyter and additional dependencies:

```bash
pip install jupyter matplotlib scikit-learn
```

## Notebooks

### 01_basic_extraction.ipynb (Planned)
Extract a single replay and explore the output.

**Topics covered**:
- Loading and processing a replay
- Examining game state parquet
- Reading messages
- Understanding the schema
- Basic data validation

**Estimated time**: 10 minutes

### 02_batch_processing.ipynb (Planned)
Process multiple replays in parallel.

**Topics covered**:
- Setting up batch processing
- Configuring workers
- Monitoring progress
- Handling errors
- Reviewing batch results

**Estimated time**: 15 minutes

### 03_data_analysis.ipynb (Planned)
Analyze extracted data with pandas and matplotlib.

**Topics covered**:
- Loading parquet files
- Basic statistics
- Resource collection over time
- Unit production analysis
- Visualizations

**Estimated time**: 20 minutes

### 04_ml_pipeline.ipynb (Planned)
Use extracted data in a machine learning pipeline.

**Topics covered**:
- Preparing data for ML
- Feature engineering
- Train/test split
- Training a simple model
- Evaluating predictions

**Estimated time**: 30 minutes

## Running Notebooks

```bash
# Start Jupyter
jupyter notebook

# Or use JupyterLab
jupyter lab
```

Then open the desired notebook from the file browser.

## Quick Start (Python Script)

If you prefer Python scripts over notebooks, check out:

- `quickstart.py` in the project root
- `src_new/pipeline/QUICKSTART.py` for advanced examples
- `docs/usage.md` for code examples

## Creating Your Own Notebooks

Template for a new analysis notebook:

```python
# 1. Import libraries
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from src_new.pipeline import process_replay_quick

# 2. Process replay (or load existing)
result = process_replay_quick(
    replay_path=Path("../replays/my_game.SC2Replay"),
    output_dir=Path("../data/processed")
)

# 3. Load data
df = pd.read_parquet(result['output_files']['game_state'])

# 4. Analyze
print(f"Duration: {df['timestamp_seconds'].max():.1f} seconds")
print(f"Final P1 minerals: {df.iloc[-1]['p1_minerals']}")

# 5. Visualize
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp_seconds'], df['p1_minerals'], label='P1')
plt.plot(df['timestamp_seconds'], df['p2_minerals'], label='P2')
plt.xlabel('Time (seconds)')
plt.ylabel('Minerals')
plt.legend()
plt.title('Mineral Collection Over Time')
plt.show()
```

## Data Files

Example notebooks expect replay files in `../replays/` and write output to `../data/processed/`.

You can modify paths as needed for your setup.

## Questions?

- See `docs/usage.md` for detailed usage patterns
- Check `docs/data_dictionary.md` for output schema
- Review `docs/troubleshooting.md` for common issues

---

**Note**: Full Jupyter notebooks will be created in a future update. For now, use the Python scripts and code examples in the documentation.
