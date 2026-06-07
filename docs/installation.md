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

This project is managed with **[uv](https://docs.astral.sh/uv/)**. uv handles the
virtual environment, the Python interpreter, *and* all dependencies for you — there
is no manual `python -m venv` / `pip install` step, and you do not need to activate
anything. The exact dependency versions are locked in `uv.lock` for reproducibility.

### Step 1: Install uv

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

(Already have it? `uv --version` should print 0.9+.)

### Step 2: Clone the Repository (with submodules)

The extractor (`SC2-gamestate-extractor`) and ML repo (`Thesis_ML`) are git
submodules, so clone recursively:

```bash
git clone --recurse-submodules https://github.com/yourusername/local-play-bootstrap-main.git
cd local-play-bootstrap-main

# Already cloned without --recurse-submodules? Run:
git submodule update --init --recursive
```

### Step 3: Create the Environment

```bash
# Creates .venv, installs the locked dependencies (incl. pysc2 and the
# SC2-gamestate-extractor as an editable dependency), pinned to Python 3.11.
uv sync

# Include the dev/test/notebook tools (pytest, ruff, jupyterlab, ...):
uv sync --extra dev
```

uv reads the pinned interpreter from `.python-version` (3.11 for this repo) and
will download it automatically if it isn't already on your machine.

### Running things

Prefix any command with `uv run` and it executes inside the project environment —
no activation needed:

```bash
uv run python quickstart_read_data.py
uv run python -m pytest tests/
```

### Verify the Installation

```bash
uv run python -c "import pandas, pyarrow, numpy, pysc2; import src_new; print('Environment OK')"
```

> **Submodules have their own environments.** Operate on them with `--directory`,
> e.g. `uv sync --directory Thesis_ML` (Python 3.12) or
> `uv sync --directory SC2-gamestate-extractor` (Python 3.11). Each repo is an
> independent uv project with its own `.venv` and `uv.lock`.

### Adding / removing dependencies

Don't edit a requirements file — use uv, which updates both `pyproject.toml` and
`uv.lock`:

```bash
uv add <package>           # add a runtime dependency
uv add --optional dev <package>   # add to the dev extra
uv remove <package>        # remove a dependency
```

> **Legacy note:** the old `requirements*.txt` and `setup.py` files are superseded
> by `pyproject.toml` + `uv.lock`. They may still exist for reference but are no
> longer the source of truth.

---

## About pysc2

pysc2 (the Python interface to StarCraft II) is declared as a dependency in
`pyproject.toml`, so `uv sync` installs it for you — there is no separate
`pip install pysc2` step. Note that pysc2's PyPI metadata lists the obsolete
`enum34` package (a Python-2 backport that won't build on modern Python); the
project's `pyproject.toml` neutralizes it via uv `override-dependencies`, so you
don't have to do anything.

Verify it imported correctly:

```bash
uv run python -c "import pysc2; print(f'pysc2 version: {pysc2.__version__}')"
```

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

**Problem**: wrong Python version

**Solution**: You don't need to install a specific Python yourself — uv reads
`.python-version` (3.11 for this repo) and downloads the matching interpreter
automatically. If something looks off, force a clean rebuild:
```bash
uv sync --reinstall
```

### Stale Virtual Environment Warning

If uv prints `VIRTUAL_ENV=... does not match the project environment`, you have an
old venv activated in your shell. uv ignores it and uses its own `.venv`, so it's
harmless — but to silence it, open a fresh terminal or run `deactivate`.

### `uv sync` Fails

**Problem**: resolution or network errors

**Solution**:
```bash
# Rebuild from scratch
uv sync --reinstall

# Refresh uv's download cache if a package seems corrupted
uv cache clean

# Use a different index if the default is slow/blocked
uv sync --default-index https://pypi.tuna.tsinghua.edu.cn/simple
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
# Run through uv so the project environment (and the editable src_new
# dependency) is on the path — no manual PYTHONPATH needed:
uv run python your_script.py

# If imports still fail, resync (this also re-links the editable extractor):
uv sync
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
