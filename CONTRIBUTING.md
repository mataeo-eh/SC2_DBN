# Contributing to SC2 Replay Ground Truth Extraction Pipeline

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Code Style](#code-style)
- [Running Tests](#running-tests)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- StarCraft II installed
- Familiarity with pysc2

### Quick Start

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/local-play-bootstrap-main.git
cd local-play-bootstrap-main

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/local-play-bootstrap-main.git

# Create a branch for your changes
git checkout -b feature/your-feature-name
```

---

## Development Environment Setup

### 1. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements_extraction.txt

# Install development/testing dependencies
pip install -r requirements_testing.txt

# Install in development mode
pip install -e .
```

### 3. Verify Installation

```bash
# Run verification script
python verify_installation.py

# Run tests
python run_tests.py --fast
```

---

## Code Style

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Imports**: Grouped and sorted (stdlib, third-party, local)

### Formatting Tools

We use **Black** for code formatting:

```bash
# Format a file
black src_new/extraction/state_extractor.py

# Format all files
black src_new/ tests/

# Check formatting without making changes
black --check src_new/
```

### Import Sorting

Use **isort** for import organization:

```bash
# Sort imports in a file
isort src_new/extraction/state_extractor.py

# Sort all files
isort src_new/ tests/

# Check without making changes
isort --check src_new/
```

### Type Hints

Use type hints for function signatures:

```python
from pathlib import Path
from typing import List, Dict, Optional

def process_replay(
    replay_path: Path,
    output_dir: Path,
    config: Optional[Dict] = None
) -> Dict:
    """Process a single replay.

    Args:
        replay_path: Path to .SC2Replay file
        output_dir: Directory for output files
        config: Optional configuration dictionary

    Returns:
        Dictionary with processing results
    """
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def extract_units(self, obs, player_id: int) -> Dict:
    """Extract all units for a player.

    Args:
        obs: pysc2 observation object
        player_id: Player ID (1 or 2)

    Returns:
        Dictionary mapping unit IDs to unit data:
        {
            'marine_001': {
                'x': 45.2,
                'y': 128.5,
                'state': 'existing',
                ...
            },
            ...
        }

    Raises:
        ValueError: If player_id is not 1 or 2
    """
    pass
```

---

## Running Tests

### Basic Test Commands

```bash
# Run all tests
pytest

# Run fast tests only (unit tests)
pytest -m unit

# Run specific test file
pytest tests/test_extraction/test_state_extractor.py

# Run specific test
pytest tests/test_extraction/test_state_extractor.py::TestStateExtractor::test_initialization

# Run with verbose output
pytest -v

# Run with print statements shown
pytest -s
```

### Using the Test Runner Script

```bash
# Fast tests (unit only)
python run_tests.py --fast

# All tests with coverage
python run_tests.py --coverage

# Verbose output
python run_tests.py --verbose

# Specific file
python run_tests.py --file tests/test_extraction/test_state_extractor.py
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src_new --cov-report=html

# Open in browser
# Windows:
start htmlcov/index.html
# macOS:
open htmlcov/index.html
# Linux:
xdg-open htmlcov/index.html
```

### Writing Tests

Create tests in `tests/` directory:

```python
import pytest
from src_new.extraction import StateExtractor

class TestStateExtractor:
    """Tests for StateExtractor class."""

    def test_initialization(self):
        """Test StateExtractor initializes correctly."""
        extractor = StateExtractor()

        assert extractor.unit_extractor is not None
        assert extractor.building_extractor is not None
        assert extractor.economy_extractor is not None

    def test_extract_observation(self, mock_observation):
        """Test extracting observation returns correct structure."""
        extractor = StateExtractor()
        state = extractor.extract_observation(mock_observation)

        assert 'game_loop' in state
        assert 'p1_units' in state
        assert 'p1_economy' in state
```

Use fixtures from `tests/conftest.py`:

```python
def test_with_mock_observation(mock_observation):
    """Test using mock observation fixture."""
    assert mock_observation is not None

def test_with_temp_dir(temp_output_dir):
    """Test using temporary directory fixture."""
    output_path = temp_output_dir / "output.parquet"
    # ... write to output_path ...
    assert output_path.exists()
```

---

## Making Changes

### Creating a Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes:
git checkout -b fix/bug-description
```

### Making Commits

Write clear, concise commit messages:

```bash
# Good commit messages:
git commit -m "feat: add support for Protoss unit extraction"
git commit -m "fix: correct unit count calculation for killed units"
git commit -m "docs: update installation guide with macOS instructions"
git commit -m "test: add tests for BuildingExtractor lifecycle tracking"

# Commit message format:
# <type>: <description>
#
# Types:
# - feat: New feature
# - fix: Bug fix
# - docs: Documentation changes
# - test: Adding or updating tests
# - refactor: Code refactoring
# - perf: Performance improvement
# - chore: Maintenance tasks
```

### Code Review Checklist

Before submitting a pull request, ensure:

- [ ] Code follows style guidelines (run `black` and `isort`)
- [ ] All tests pass (`pytest`)
- [ ] New code has tests (aim for >80% coverage)
- [ ] Docstrings are complete and accurate
- [ ] Type hints are used for function signatures
- [ ] No debugging code (print statements, breakpoints)
- [ ] No commented-out code
- [ ] Update documentation if needed
- [ ] Update CHANGELOG.md with your changes

---

## Pull Request Process

### 1. Update Your Branch

```bash
# Fetch latest changes
git fetch upstream

# Rebase on main
git rebase upstream/main

# Resolve any conflicts
# Then:
git rebase --continue
```

### 2. Push Your Branch

```bash
git push origin feature/your-feature-name
```

### 3. Create Pull Request

On GitHub:

1. Click "New Pull Request"
2. Select your branch
3. Fill out the PR template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] All existing tests pass
- [ ] New tests added
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No breaking changes (or documented if necessary)
```

### 4. Code Review

- Address reviewer comments
- Make requested changes
- Push updates to your branch
- PR will update automatically

### 5. Merge

Once approved:
- Maintainer will merge your PR
- Delete your feature branch

```bash
# After merge, update local main
git checkout main
git pull upstream main

# Delete feature branch
git branch -d feature/your-feature-name
```

---

## Reporting Issues

### Before Reporting

1. Search existing issues
2. Check troubleshooting guide
3. Verify with latest version
4. Collect diagnostic information

### Issue Template

```markdown
## Description
Clear description of the issue

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- OS: Windows 10 / macOS 12 / Ubuntu 20.04
- Python version: 3.11.0
- pysc2 version: 4.0.0
- Pipeline version: (git commit hash)

## Error Messages
```
Full error traceback
```

## Diagnostic Information
```python
# Output from verification script
# Logs from extraction
```

## Additional Context
Any other relevant information
```

---

## Development Workflow

### Typical Development Cycle

1. **Plan**: Discuss feature/fix in an issue first
2. **Branch**: Create feature branch
3. **Code**: Implement changes
4. **Test**: Write/update tests
5. **Format**: Run `black` and `isort`
6. **Verify**: Run all tests
7. **Document**: Update docstrings and docs
8. **Commit**: Make clear commits
9. **PR**: Create pull request
10. **Review**: Address feedback
11. **Merge**: Maintainer merges

### Testing Strategy

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test components working together
- **Performance tests**: Benchmark critical paths
- **Mock external dependencies**: Don't require SC2 for tests

### Documentation Updates

When adding features, update:

- Docstrings in code
- `docs/api_reference.md` for public APIs
- `docs/usage.md` for usage examples
- `README_SC2_PIPELINE.md` if major feature
- `CHANGELOG.md` with changes

---

## Project Structure

```
local-play-bootstrap-main/
├── src_new/                 # Main source code
│   ├── extraction/          # Core extraction components
│   ├── extractors/          # Individual extractors
│   ├── pipeline/            # Pipeline orchestration
│   └── utils/               # Utilities and validation
├── tests/                   # Test suite
│   ├── conftest.py          # Shared fixtures
│   ├── fixtures/            # Test data and mocks
│   ├── test_extraction/     # Extraction tests
│   ├── test_utils/          # Utility tests
│   ├── test_integration.py  # Integration tests
│   └── test_performance.py  # Performance tests
├── docs/                    # Documentation
│   ├── installation.md
│   ├── usage.md
│   ├── architecture.md
│   ├── data_dictionary.md
│   └── troubleshooting.md
├── examples/                # Jupyter notebooks
├── run_tests.py             # Test runner script
├── requirements_extraction.txt    # Production dependencies
├── requirements_testing.txt       # Testing dependencies
├── CONTRIBUTING.md          # This file
├── CHANGELOG.md             # Version history
└── README_SC2_PIPELINE.md   # Main README
```

---

## Questions?

- **Documentation**: Read `docs/` directory
- **Examples**: Check `examples/` notebooks
- **Tests**: Look at `tests/` for patterns
- **Issues**: Open a GitHub issue
- **Discussion**: (Add discussion forum link if available)

---

## License

By contributing, you agree that your contributions will be licensed under the GPLv3 License.

---

**Thank you for contributing!** Your improvements help make this pipeline better for everyone.
