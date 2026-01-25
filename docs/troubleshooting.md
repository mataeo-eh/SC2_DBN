# Troubleshooting Guide

Common issues and solutions for the SC2 Replay Ground Truth Extraction Pipeline.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Runtime Errors](#runtime-errors)
- [Performance Problems](#performance-problems)
- [Data Quality Issues](#data-quality-issues)
- [FAQ](#faq)
- [Getting Help](#getting-help)

---

## Installation Issues

### Python Version Too Old

**Symptoms**:
```
ERROR: This package requires Python 3.9 or higher
```

**Solution**:
```bash
# Check Python version
python --version

# Install Python 3.9+ from python.org
# Then create new virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### pysc2 Import Fails

**Symptoms**:
```python
ModuleNotFoundError: No module named 'pysc2'
```

**Solution**:
```bash
# Ensure virtual environment is activated
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install pysc2
pip install pysc2

# Verify installation
python -c "import pysc2; print(pysc2.__version__)"
```

### SC2 Not Found

**Symptoms**:
```
RuntimeError: StarCraft II executable not found
```

**Solutions**:

**Windows**:
```bash
# Set environment variable
set SC2PATH=C:\Program Files (x86)\StarCraft II

# Or in PowerShell
$env:SC2PATH = "C:\Program Files (x86)\StarCraft II"

# Verify SC2 installation
dir "C:\Program Files (x86)\StarCraft II\SC2_x64.exe"
```

**macOS**:
```bash
# Set environment variable
export SC2PATH="/Applications/StarCraft II"

# Add to ~/.bash_profile or ~/.zshrc
echo 'export SC2PATH="/Applications/StarCraft II"' >> ~/.zshrc

# Verify
ls "/Applications/StarCraft II/StarCraft II.app"
```

**Linux**:
```bash
# Set environment variable
export SC2PATH="/path/to/StarCraft II"

# Add to ~/.bashrc
echo 'export SC2PATH="/path/to/StarCraft II"' >> ~/.bashrc

# Verify
ls "$SC2PATH"
```

### Permission Errors

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied
```

**Solutions**:

**Windows** (PowerShell execution policy):
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**macOS/Linux** (file permissions):
```bash
# Make scripts executable
chmod +x run_tests.py
chmod +x verify_installation.py

# Fix ownership
sudo chown -R $USER:$USER .venv
```

### Dependency Conflicts

**Symptoms**:
```
ERROR: pip's dependency resolver does not currently take into account all the packages
```

**Solution**:
```bash
# Create fresh virtual environment
python -m venv .venv-fresh --clear
source .venv-fresh/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies one by one
pip install pandas
pip install pyarrow
pip install numpy
pip install pysc2

# Or use requirements file
pip install -r requirements_extraction.txt
```

---

## Runtime Errors

### Replay Loading Fails

**Symptoms**:
```
Error: Failed to load replay: /path/to/replay.SC2Replay
```

**Causes and Solutions**:

**1. Corrupted Replay File**
```bash
# Try to open replay in SC2 client
# If it doesn't work there, file is corrupted

# Try with different replay
python -c "
from pathlib import Path
from src_new.pipeline import process_replay_quick
result = process_replay_quick(Path('replays/other_game.SC2Replay'), Path('data/test'))
print(result)
"
```

**2. Replay Version Incompatibility**
```python
# Some very old or very new replays may not be compatible
# Check replay version
from pysc2.run_configs import get
from s2clientprotocol import sc2api_pb2 as sc_pb

run_config = get()
with run_config.start() as controller:
    replay_data = run_config.replay_data(Path("replay.SC2Replay"))
    info = controller.replay_info(replay_data)
    print(f"Game version: {info.game_version}")
```

**3. Path Issues**
```python
# Use absolute paths
from pathlib import Path
replay_path = Path("replays/game.SC2Replay").resolve()
print(f"Absolute path: {replay_path}")
print(f"Exists: {replay_path.exists()}")
```

### SC2 Instance Crashes

**Symptoms**:
```
RuntimeError: SC2 instance crashed during replay
```

**Solutions**:

**1. Close Other SC2 Instances**
```bash
# Windows
taskkill /F /IM SC2_x64.exe
taskkill /F /IM SC2.exe

# macOS/Linux
pkill -9 SC2
```

**2. Reduce Memory Usage**
```python
# Use single-pass mode
config = {
    'processing_mode': 'single_pass',
    'step_size': 44  # Sample less frequently
}

result = process_replay_quick(replay_path, output_dir, config=config)
```

**3. Increase Step Size**
```python
# Process fewer frames
config = {
    'step_size': 22 * 5  # Every 5 seconds instead of every second
}
```

### Memory Errors

**Symptoms**:
```
MemoryError: Unable to allocate array
```

**Solutions**:

**1. Close Other Applications**
```bash
# Free up RAM before processing
```

**2. Process Shorter Replays**
```python
# Limit processing duration
config = {
    'max_loops': 6720  # Only first 5 minutes (6720 loops ≈ 300 seconds)
}
```

**3. Use Streaming Mode (if implemented)**
```python
# Process and write incrementally
# (requires streaming mode implementation)
```

**4. Reduce Parallel Workers**
```python
# Use fewer workers
from src_new.pipeline import ParallelReplayProcessor

processor = ParallelReplayProcessor(num_workers=2)  # Instead of 8
```

### Import Errors

**Symptoms**:
```python
ModuleNotFoundError: No module named 'src_new'
```

**Solutions**:

**1. Run from Project Root**
```bash
# Ensure you're in the correct directory
cd /path/to/local-play-bootstrap-main

# Then run
python -m src_new.pipeline.QUICKSTART
```

**2. Set PYTHONPATH**
```bash
# Windows (CMD)
set PYTHONPATH=%PYTHONPATH%;C:\path\to\local-play-bootstrap-main

# Windows (PowerShell)
$env:PYTHONPATH += ";C:\path\to\local-play-bootstrap-main"

# macOS/Linux
export PYTHONPATH="${PYTHONPATH}:/path/to/local-play-bootstrap-main"
```

**3. Install in Development Mode**
```bash
# From project root
pip install -e .
```

---

## Performance Problems

### Processing Too Slow

**Symptoms**:
- Processing takes > 5 seconds per 1000 game loops
- Batch processing not utilizing all CPUs

**Solutions**:

**1. Use Single-Pass Mode**
```python
config = {
    'processing_mode': 'single_pass'  # ~2x faster than two-pass
}
```

**2. Increase Step Size**
```python
config = {
    'step_size': 44  # Sample every 2 seconds instead of every second
}
```

**3. Optimize Parallel Workers**
```python
import os

# Use all available CPUs
num_cpus = os.cpu_count()
processor = ParallelReplayProcessor(num_workers=num_cpus)
```

**4. Disable Validation**
```python
config = {
    'run_validation': False  # Skip validation for faster processing
}
```

**5. Use Faster Compression**
```python
config = {
    'compression': 'snappy'  # Faster than 'gzip' or 'brotli'
}
```

### High Memory Usage

**Symptoms**:
- Process uses > 2GB RAM per replay
- System becomes unresponsive during processing

**Solutions**:

**1. Reduce Worker Count**
```python
# Each worker uses ~500MB-1GB
processor = ParallelReplayProcessor(num_workers=4)  # Instead of 8
```

**2. Process Smaller Batches**
```python
# Process replays in smaller groups
replay_paths = list(Path("replays/").glob("*.SC2Replay"))

# Process 10 at a time
for i in range(0, len(replay_paths), 10):
    batch = replay_paths[i:i+10]
    results = processor.process_replay_batch(batch, output_dir)
```

**3. Clear Memory Between Replays**
```python
import gc

for replay_path in replay_paths:
    result = process_replay_quick(replay_path, output_dir)
    gc.collect()  # Force garbage collection
```

### Disk I/O Bottleneck

**Symptoms**:
- Disk at 100% during processing
- Processing slower on HDD than SSD

**Solutions**:

**1. Use SSD for Output**
```python
# Write to SSD location
output_dir = Path("/ssd/data/processed")
```

**2. Reduce Compression**
```python
config = {
    'compression': 'snappy'  # or None for no compression
}
```

**3. Buffer Writes**
```python
# Process in larger batches before writing
# (implementation-dependent)
```

---

## Data Quality Issues

### Missing Columns in Output

**Symptoms**:
- Expected columns not in parquet file
- Columns appear in some files but not others

**Solutions**:

**1. Use Two-Pass Mode**
```python
# Ensures consistent schema
config = {
    'processing_mode': 'two_pass'
}
```

**2. Check Schema JSON**
```python
import json

with open('output_schema.json', 'r') as f:
    schema = json.load(f)

print("Columns:", len(schema['columns']))
print("First 10:", schema['columns'][:10])
```

**3. Verify Extraction**
```python
# Check what's being extracted
from src_new.extraction import StateExtractor

extractor = StateExtractor()
# ... extract from observation ...
state = extractor.extract_observation(obs)
print(state.keys())
```

### NaN Values Everywhere

**Symptoms**:
- Most columns are NaN
- Data looks empty

**Causes and Solutions**:

**1. Wrong Player ID**
```python
# Make sure you're observing the right player
loader.start_replay(controller, observed_player_id=1)  # Try 1 or 2
```

**2. Wrong Game Loop Range**
```python
# Check actual game duration
print(f"Game duration: {df['game_loop'].max()} loops")
print(f"In seconds: {df['timestamp_seconds'].max()}")
```

**3. Unit IDs Don't Match**
```python
# Check which units actually exist
unit_columns = [col for col in df.columns if '_x' in col]
for col in unit_columns:
    if df[col].notna().any():
        print(f"Found: {col}")
```

### Validation Errors

**Symptoms**:
```
Validation failed: Duplicate game_loops detected
```

**Solutions**:

**1. Check for Bugs in Extraction**
```python
# Look at the duplicates
df = pd.read_parquet("output.parquet")
duplicates = df[df.duplicated(subset=['game_loop'], keep=False)]
print(duplicates)
```

**2. Re-process with Two-Pass Mode**
```python
config = {
    'processing_mode': 'two_pass',
    'run_validation': True
}
```

**3. Check for Replay Corruption**
```python
# Try a different replay
result = process_replay_quick(other_replay_path, output_dir)
```

### Incorrect Unit Counts

**Symptoms**:
- `p1_marine_count` doesn't match individual marines
- Counts seem wrong

**Solutions**:

**1. Verify Count Calculation**
```python
# Manually count from columns
marine_cols = [col for col in df.columns if 'marine' in col and '_state' in col]
for idx, row in df.iterrows():
    # Count marines that exist (not NaN and not 'killed')
    alive = sum(1 for col in marine_cols
                if pd.notna(row[col]) and row[col] != 'killed')
    count_col = row.get('p1_marine_count', 0)
    if alive != count_col:
        print(f"Loop {row['game_loop']}: manual={alive}, column={count_col}")
```

**2. Check State Transitions**
```python
# Look for state anomalies
for col in df.columns:
    if '_state' in col:
        states = df[col].dropna().unique()
        if set(states) - {'built', 'existing', 'killed'}:
            print(f"Unexpected states in {col}: {states}")
```

---

## FAQ

### Q: How do I process only the first 5 minutes of a replay?

**A:**
```python
config = {
    'max_loops': 6720  # 5 minutes * 60 seconds * 22.4 loops/second
}
result = process_replay_quick(replay_path, output_dir, config=config)
```

### Q: Can I process replays from different SC2 versions?

**A:** Yes, but very old replays (pre-2018) may not work. Try processing one replay from each version to test compatibility.

### Q: How do I reduce output file size?

**A:**
```python
config = {
    'step_size': 44,  # Sample every 2 seconds instead of 1
    'compression': 'gzip'  # Better compression than 'snappy'
}
```

### Q: Can I extract only specific units (e.g., only marines)?

**A:** Not directly, but you can filter after extraction:
```python
df = pd.read_parquet("output.parquet")

# Keep only marine columns
marine_cols = ['game_loop', 'timestamp_seconds'] + \
              [col for col in df.columns if 'marine' in col.lower()]
df_marines = df[marine_cols]
```

### Q: How do I combine multiple replay outputs for ML training?

**A:**
```python
import pandas as pd
from pathlib import Path

# Load all game state parquets
all_data = []
for parquet_file in Path("data/processed").glob("*_game_state.parquet"):
    df = pd.read_parquet(parquet_file)
    df['replay_name'] = parquet_file.stem.replace('_game_state', '')
    all_data.append(df)

# Concatenate
combined = pd.concat(all_data, ignore_index=True)

# Save
combined.to_parquet("data/combined_dataset.parquet")
```

### Q: Why are there gaps in unit IDs (marine_001, marine_003, no marine_002)?

**A:** Units are assigned IDs in order of appearance. If marine_002 never appears in the replay, it won't have columns. This is normal.

### Q: How do I handle replays that fail to process?

**A:**
```python
from pathlib import Path
from src_new.pipeline import process_directory_quick

results = process_directory_quick(replay_dir, output_dir, num_workers=4)

# Save failed list
with open("failed_replays.txt", "w") as f:
    for replay_path, error in results['failed']:
        f.write(f"{replay_path}: {error}\n")

# Retry later with different settings
config = {'processing_mode': 'single_pass'}
for replay_path, _ in results['failed']:
    result = process_replay_quick(replay_path, output_dir, config=config)
```

### Q: Can I run this on a server without a display?

**A:** Yes, but you need to configure a virtual display (Linux):
```bash
# Install Xvfb
sudo apt-get install xvfb

# Run with virtual display
xvfb-run -a python process_replays.py
```

### Q: How do I update the pipeline when new SC2 units are added?

**A:** The pipeline automatically detects new unit types. No code changes needed for new units. Re-process replays with the new units and they'll appear in the output.

---

## Getting Help

### Diagnostic Information to Collect

When reporting issues, include:

1. **System Information**:
```bash
python --version
pip list | grep -E "(pysc2|pandas|pyarrow|numpy)"
# Or on Windows: pip list | findstr /I "pysc2 pandas pyarrow numpy"
```

2. **Error Message**:
```bash
# Full error traceback
# Run with: python script.py 2> error.log
```

3. **Replay Information**:
```python
from src_new.pipeline.replay_loader import ReplayLoader

loader = ReplayLoader()
loader.load_replay(Path("problematic_replay.SC2Replay"))

with loader.start_sc2_instance() as controller:
    info = loader.get_replay_info(controller)
    print(info)
```

4. **Configuration**:
```python
import json
print(json.dumps(config, indent=2))
```

### Check Logs

```bash
# Pipeline logs
cat logs/extraction.log

# Recent errors
grep ERROR logs/extraction.log

# Tail logs in real-time
tail -f logs/extraction.log
```

### Run Validation

```python
from src_new.utils.validation import OutputValidator

validator = OutputValidator()
report = validator.validate_game_state_parquet(Path("output.parquet"))

print(report)
```

### Test Suite

```bash
# Run tests to verify installation
python run_tests.py --fast

# Run specific test
pytest tests/test_extraction/test_state_extractor.py -v

# Run with verbose output
pytest -v -s
```

### Where to Get Help

1. **Documentation**: Check [docs/](../)
2. **Examples**: See `examples/` notebooks
3. **Tests**: Look at `tests/` for usage patterns
4. **Issues**: Open a GitHub issue with diagnostic info
5. **Community**: (Add your community links here)

---

## Common Error Messages Reference

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| `SC2 not found` | SC2 not installed or SC2PATH not set | Install SC2, set SC2PATH |
| `ModuleNotFoundError: pysc2` | pysc2 not installed | `pip install pysc2` |
| `MemoryError` | Not enough RAM | Reduce workers, use single-pass mode |
| `Replay loading failed` | Corrupted replay or wrong version | Try different replay |
| `Permission denied` | File permissions issue | Check file permissions, run as admin if needed |
| `Validation failed` | Data quality issue | Re-process with two-pass mode |
| `Duplicate game_loops` | Bug in extraction | Report issue with replay |
| `Unit count mismatch` | State tracking issue | Check for bugs, report issue |

---

**Still having issues?** Open an issue on GitHub with your diagnostic information and error logs.
