# Phase 6 Test Suite - Quick Start Guide

## Installation

### 1. Install Testing Dependencies

```bash
# Make sure you're in the project directory
cd local-play-bootstrap-main

# Install testing requirements
pip install -r requirements_testing.txt
```

This will install:
- pytest (test framework)
- pytest-cov (coverage reporting)
- pytest-mock (mocking support)
- Other testing utilities

### 2. Verify Installation

```bash
# Check pytest is installed
pytest --version

# Should output something like: pytest 7.4.0
```

## Running Tests

### Basic Usage

```bash
# Run all tests (recommended first run)
pytest

# Run with verbose output
pytest -v

# Run only fast unit tests (skip slow/integration)
pytest -m "unit"

# Run with coverage report
pytest --cov=src_new --cov-report=term
```

### Using the Test Runner Script

```bash
# Run all tests
python run_tests.py

# Run only fast tests
python run_tests.py --fast

# Run with coverage (generates HTML report)
python run_tests.py --coverage

# After coverage, open the HTML report:
# Windows:
start htmlcov/index.html
# macOS:
open htmlcov/index.html
# Linux:
xdg-open htmlcov/index.html
```

## Expected Output

### Successful Test Run

```
======================== test session starts ========================
platform win32 -- Python 3.11.x
collected 82 items

tests/test_extraction/test_state_extractor.py .................. [ 24%]
tests/test_extraction/test_wide_table_builder.py ............... [ 43%]
tests/test_utils/test_validation.py ............................ [ 67%]
tests/test_integration.py ........................ [ 85%]
tests/test_performance.py ............ [100%]

======================== 82 passed in 5.23s =========================
```

### Coverage Report

```
Name                                      Stmts   Miss  Cover
-------------------------------------------------------------
src_new/extraction/state_extractor.py       123     15    88%
src_new/extraction/wide_table_builder.py    98      12    88%
src_new/utils/validation.py                145     18    88%
-------------------------------------------------------------
TOTAL                                       1245    156    87%
```

## Common Test Commands

```bash
# Run specific test file
pytest tests/test_extraction/test_state_extractor.py

# Run specific test class
pytest tests/test_extraction/test_state_extractor.py::TestUnitTracker

# Run specific test
pytest tests/test_extraction/test_state_extractor.py::TestUnitTracker::test_initialization

# Run tests matching pattern
pytest -k "tracker"

# Run all except slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Show 10 slowest tests
pytest --durations=10

# Stop on first failure
pytest -x

# Run in parallel (requires pytest-xdist)
pytest -n 4
```

## Test Markers

Filter tests by category:

- `unit` - Fast unit tests
- `integration` - Integration tests
- `slow` - Tests taking >1 second
- `extraction` - Extraction component tests
- `pipeline` - Pipeline component tests
- `utils` - Utility component tests
- `validation` - Validation tests
- `performance` - Performance benchmarks

## Troubleshooting

### Import Errors

If you see import errors:

```bash
# Make sure you're in the project root
cd local-play-bootstrap-main

# Install the package in development mode
pip install -e .
```

### Tests Not Found

If pytest can't find tests:

```bash
# Make sure you're in the project root
cd local-play-bootstrap-main

# Run with explicit path
pytest tests/
```

### Slow Tests

If tests are too slow:

```bash
# Run only fast tests
pytest -m "not slow"

# Or use the test runner
python run_tests.py --fast
```

## Understanding Test Results

### Test Status Symbols

- `.` - Test passed
- `F` - Test failed
- `E` - Test error (exception)
- `s` - Test skipped
- `x` - Expected failure
- `X` - Unexpected pass

### Reading Failure Output

```
FAILED tests/test_extraction/test_state_extractor.py::TestUnitTracker::test_initialization

def test_initialization():
    tracker = UnitTracker()
>   assert tracker.unit_registry == {}
E   AssertionError: assert {...} == {}

tests/test_extraction/test_state_extractor.py:15: AssertionError
```

This shows:
1. Which test failed
2. The failing line
3. What was expected vs actual
4. Line number

## Next Steps

After running tests successfully:

1. **Check Coverage**: Run `python run_tests.py --coverage` and aim for >80%
2. **Fix Failures**: Address any failing tests
3. **Add Tests**: Write tests for any new features
4. **CI Integration**: Set up automated testing in CI/CD

## Help

For more information:
- See `tests/README.md` for comprehensive documentation
- See `PHASE_6_TEST_SUITE_COMPLETE.md` for full implementation details
- Check pytest documentation: https://docs.pytest.org/

## Quick Checklist

Before committing code:

```bash
# 1. Run all tests
pytest

# 2. Check they pass
# ✅ All tests should pass

# 3. Check coverage
pytest --cov=src_new --cov-report=term

# 4. Verify >80% coverage
# ✅ Coverage should be >80%

# 5. Run fast tests for quick verification
pytest -m unit

# 6. All good? Commit!
git add .
git commit -m "Your changes"
```

## Test File Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── pytest.ini                  # Configuration
├── fixtures/                   # Test data
│   ├── mock_observations.py    # Mock pysc2 data
│   ├── sample_game_states.py   # Sample states
│   └── sample_schemas.py       # Sample schemas
├── test_extraction/            # Extraction tests
│   ├── test_state_extractor.py
│   └── test_wide_table_builder.py
├── test_utils/                 # Utility tests
│   └── test_validation.py
├── test_integration.py         # Integration tests
└── test_performance.py         # Performance tests
```

## Example Test Session

```bash
# 1. Navigate to project
cd local-play-bootstrap-main

# 2. Activate virtual environment (if using)
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install testing dependencies (first time only)
pip install -r requirements_testing.txt

# 4. Run tests
pytest -v

# 5. Generate coverage report
pytest --cov=src_new --cov-report=html

# 6. View coverage report
start htmlcov/index.html  # Windows
# or
open htmlcov/index.html   # macOS

# 7. All tests pass? Great! ✅
```

## Development Workflow

```bash
# 1. Make code changes
# ... edit files ...

# 2. Run relevant tests
pytest tests/test_extraction/

# 3. Tests pass? Run all tests
pytest

# 4. All pass? Check coverage
pytest --cov=src_new

# 5. Coverage good? Commit
git add .
git commit -m "Add feature X"

# 6. Push and celebrate! 🎉
git push
```
