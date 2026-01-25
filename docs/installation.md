# Installation Guide

Complete guide to installing and setting up the SC2 Replay Ground Truth Extraction Pipeline.

## Table of Contents

- [System Requirements](#system-requirements)
- [Python Environment Setup](#python-environment-setup)
- [Installing Dependencies](#installing-dependencies)
- [Installing pysc2](#installing-pysc2)
- [Setting Up StarCraft II](#setting-up-starcraft-ii)
- [Verifying Installation](#verifying-installation)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Operating System
- **Windows**: Windows 10 or higher
- **macOS**: macOS 10.14 (Mojave) or higher
- **Linux**: Ubuntu 18.04+ or equivalent

### Hardware
- **CPU**: 4+ cores recommended for parallel processing
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**:
  - ~500MB for pipeline code and dependencies
  - ~100GB for StarCraft II installation
  - ~10-50MB per processed replay

### Software
- **Python**: 3.9 or higher (3.11 recommended)
- **StarCraft II**: Full game installation required (Free to play)
- **Git**: For cloning the repository (optional)

---

## Python Environment Setup

### Option 1: Using venv (Recommended)

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on macOS/Linux
source .venv/bin/activate

# Verify Python version
python --version  # Should be 3.9+
```

### Option 2: Using conda

```bash
# Create conda environment
conda create -n sc2-pipeline python=3.11

# Activate environment
conda activate sc2-pipeline

# Verify installation
python --version
```

### Option 3: Using pyenv

```bash
# Install specific Python version
pyenv install 3.11.0
pyenv local 3.11.0

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

---

## Installing Dependencies

### Step 1: Clone the Repository

```bash
# Using git
git clone https://github.com/yourusername/local-play-bootstrap-main.git
cd local-play-bootstrap-main

# Or download and extract the ZIP file
```

### Step 2: Install Core Dependencies

```bash
# Install extraction pipeline dependencies
pip install -r requirements_extraction.txt

# This installs:
# - pandas (for DataFrames)
# - pyarrow (for Parquet files)
# - numpy (for numerical operations)
```

The `requirements_extraction.txt` file contains:

```
pandas>=2.0.0
pyarrow>=12.0.0
numpy>=1.24.0
```

### Step 3: Install Testing Dependencies (Optional)

If you want to run tests or contribute to development:

```bash
pip install -r requirements_testing.txt

# This installs:
# - pytest (testing framework)
# - pytest-cov (coverage reporting)
# - pytest-mock (mocking utilities)
# - and other testing tools
```

### Step 4: Verify Core Installation

```bash
python -c "import pandas, pyarrow, numpy; print('Core dependencies OK')"
```

---

## Installing pysc2

pysc2 is the Python interface to StarCraft II and is required for replay processing.

### Installation

```bash
pip install pysc2
```

### Verify pysc2 Installation

```bash
python -c "import pysc2; print(f'pysc2 version: {pysc2.__version__}')"
```

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'pysc2'`
**Solution**: Ensure you've activated your virtual environment and run `pip install pysc2`

**Issue**: pysc2 install fails with build errors
**Solution**:
- Ensure you have the latest pip: `pip install --upgrade pip`
- Install build tools for your platform (see below)

---

## Setting Up StarCraft II

pysc2 requires the StarCraft II game client to be installed.

### Windows Installation

1. **Download StarCraft II**
   - Visit: https://starcraft2.com/
   - Download the Battle.net launcher
   - Install StarCraft II (free to play)

2. **Default Installation Path**
   ```
   C:\Program Files (x86)\StarCraft II\
   ```

3. **Verify Installation**
   - Look for `SC2.exe` or `SC2_x64.exe` in the StarCraft II directory
   - The Maps folder should exist

### macOS Installation

1. **Download StarCraft II**
   - Visit: https://starcraft2.com/
   - Download and install via Battle.net

2. **Default Installation Path**
   ```
   /Applications/StarCraft II/
   ```

3. **Verify Installation**
   ```bash
   ls "/Applications/StarCraft II/StarCraft II.app"
   ```

### Linux Installation

1. **Install via Wine or Native Client**

   **Option A: Official Linux Client** (Recommended)
   ```bash
   # Download from Blizzard
   # Follow installation instructions at:
   # https://github.com/Blizzard/s2client-proto#downloads
   ```

   **Option B: Using Wine**
   ```bash
   # Install Wine
   sudo apt-get install wine64

   # Install StarCraft II via lutris or PlayOnLinux
   # See: https://lutris.net/games/starcraft-ii/
   ```

2. **Set Environment Variable**
   ```bash
   export SC2PATH="/path/to/StarCraft II"

   # Add to ~/.bashrc or ~/.zshrc for persistence:
   echo 'export SC2PATH="/path/to/StarCraft II"' >> ~/.bashrc
   ```

### Custom Installation Path

If SC2 is installed in a non-standard location, set the environment variable:

```bash
# Windows (PowerShell)
$env:SC2PATH = "D:\Games\StarCraft II"

# Windows (CMD)
set SC2PATH=D:\Games\StarCraft II

# macOS/Linux
export SC2PATH="/custom/path/to/StarCraft II"
```

Or create a configuration file `config.yaml`:

```yaml
sc2_path: "D:/Games/StarCraft II"
```

---

## Verifying Installation

### Quick Verification Script

Create a file `verify_installation.py`:

```python
#!/usr/bin/env python3
"""Verify SC2 Pipeline installation."""

import sys
from pathlib import Path

def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version >= (3, 9):
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor} (need 3.9+)")
        return False

def check_dependencies():
    """Check required packages."""
    packages = ['pandas', 'pyarrow', 'numpy', 'pysc2']
    all_ok = True

    for package in packages:
        try:
            mod = __import__(package)
            version = getattr(mod, '__version__', 'unknown')
            print(f"✓ {package} ({version})")
        except ImportError:
            print(f"✗ {package} (not installed)")
            all_ok = False

    return all_ok

def check_sc2_installation():
    """Check SC2 installation."""
    from pysc2.run_configs import get

    try:
        run_config = get()
        print(f"✓ SC2 found at: {run_config.exec_path}")
        return True
    except Exception as e:
        print(f"✗ SC2 not found: {e}")
        return False

def check_pipeline_structure():
    """Check pipeline files exist."""
    required_files = [
        'src_new/extraction/state_extractor.py',
        'src_new/extraction/wide_table_builder.py',
        'src_new/pipeline/extraction_pipeline.py',
        'src_new/utils/validation.py',
    ]

    all_ok = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (missing)")
            all_ok = False

    return all_ok

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("SC2 Replay Extraction Pipeline - Installation Verification")
    print("=" * 60)
    print()

    print("Checking Python version...")
    python_ok = check_python_version()
    print()

    print("Checking dependencies...")
    deps_ok = check_dependencies()
    print()

    print("Checking SC2 installation...")
    sc2_ok = check_sc2_installation()
    print()

    print("Checking pipeline structure...")
    structure_ok = check_pipeline_structure()
    print()

    print("=" * 60)
    if all([python_ok, deps_ok, sc2_ok, structure_ok]):
        print("✓ ALL CHECKS PASSED - Installation is complete!")
        print()
        print("Next steps:")
        print("  1. Run tests: python run_tests.py --fast")
        print("  2. Try the quickstart: python src_new/pipeline/QUICKSTART.py")
        print("  3. Read the usage guide: docs/usage.md")
    else:
        print("✗ SOME CHECKS FAILED - Please fix the issues above")
        print()
        print("For help, see: docs/troubleshooting.md")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

Run the verification:

```bash
python verify_installation.py
```

Expected output:

```
============================================================
SC2 Replay Extraction Pipeline - Installation Verification
============================================================

Checking Python version...
✓ Python 3.11.0

Checking dependencies...
✓ pandas (2.0.3)
✓ pyarrow (12.0.1)
✓ numpy (1.24.3)
✓ pysc2 (4.0.0)

Checking SC2 installation...
✓ SC2 found at: C:\Program Files (x86)\StarCraft II\Versions\...

Checking pipeline structure...
✓ src_new/extraction/state_extractor.py
✓ src_new/extraction/wide_table_builder.py
✓ src_new/pipeline/extraction_pipeline.py
✓ src_new/utils/validation.py

============================================================
✓ ALL CHECKS PASSED - Installation is complete!

Next steps:
  1. Run tests: python run_tests.py --fast
  2. Try the quickstart: python src_new/pipeline/QUICKSTART.py
  3. Read the usage guide: docs/usage.md
============================================================
```

### Running Tests

Verify everything works by running the test suite:

```bash
# Quick test (unit tests only, ~5 seconds)
python run_tests.py --fast

# Full test suite (~30 seconds)
python run_tests.py

# With coverage report
python run_tests.py --coverage
```

---

## Troubleshooting

### Python Version Issues

**Problem**: `python --version` shows 2.7 or 3.8

**Solution**:
```bash
# Try python3 explicitly
python3 --version

# Or install Python 3.9+ from python.org
# Then create alias:
alias python=python3.11
```

### Virtual Environment Not Activating

**Windows**:
```bash
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
.venv\Scripts\activate
```

**macOS/Linux**:
```bash
# Ensure venv was created correctly
python3 -m venv .venv --clear

# Activate
source .venv/bin/activate
```

### pip Install Fails

**Problem**: Permission errors or network issues

**Solution**:
```bash
# Use user install
pip install --user -r requirements_extraction.txt

# Or upgrade pip first
pip install --upgrade pip setuptools wheel

# Use a mirror if network is slow
pip install -r requirements_extraction.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### pysc2 Can't Find SC2

**Problem**: `SC2 not found` error

**Solution**:
```bash
# Set environment variable
export SC2PATH="/path/to/StarCraft II"

# Or on Windows
set SC2PATH=C:\Program Files (x86)\StarCraft II

# Verify path exists
ls "$SC2PATH"  # Should show SC2 installation
```

### Import Errors

**Problem**: `ModuleNotFoundError` when importing pipeline modules

**Solution**:
```bash
# Ensure you're in the project root
pwd  # Should show .../local-play-bootstrap-main

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in development mode
pip install -e .
```

### Platform-Specific Build Issues

**Windows - Missing Visual C++**:
```
Download and install:
Microsoft Visual C++ Build Tools
https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**Linux - Missing Build Tools**:
```bash
sudo apt-get update
sudo apt-get install build-essential python3-dev
```

**macOS - Missing Command Line Tools**:
```bash
xcode-select --install
```

---

## Next Steps

Once installation is complete:

1. **Read the Usage Guide**: [docs/usage.md](usage.md)
2. **Run the Quickstart**: `python src_new/pipeline/QUICKSTART.py`
3. **Explore Examples**: Check out Jupyter notebooks in `examples/`
4. **Process Your First Replay**: Follow the basic tutorial

---

## Getting Help

If you encounter issues not covered here:

1. **Check Troubleshooting Guide**: [docs/troubleshooting.md](troubleshooting.md)
2. **Review Test Output**: Run `python run_tests.py --verbose`
3. **Check Logs**: Look in `logs/` directory for detailed error messages
4. **Open an Issue**: Include your `verify_installation.py` output

---

**Installation complete? Great!** Head to the [Usage Guide](usage.md) to start processing replays.
