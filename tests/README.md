# SC2 Replay Extraction Pipeline - Test Suite

## Overview

This test suite provides comprehensive testing for the SC2 Replay Ground Truth Extraction Pipeline. The tests are designed to run **without requiring pysc2 to be installed**, using mock observations and data structures.

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                     # Pytest configuration
├── fixtures/                      # Test data and mocks
│   ├── mock_observations.py       # Mock pysc2 observations
│   ├── sample_game_states.py      # Sample extracted states
│   └── sample_schemas.py          # Sample schema definitions
├── test_extraction/               # Extraction component tests
│   ├── test_state_extractor.py    # StateExtractor tests
│   └── test_wide_table_builder.py # WideTableBuilder tests
├── test_utils/                    # Utility component tests
│   └── test_validation.py         # OutputValidator tests
├── test_integration.py            # Integration tests
└── test_performance.py            # Performance benchmarks
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
Fast, isolated tests that verify individual components work correctly.

- **StateExtractor tests**: Unit tracking, building tracking, state extraction
- **WideTableBuilder tests**: Row building, data transformation
- **Validation tests**: Parquet validation, error detection

### Integration Tests (`@pytest.mark.integration`)
Tests that verify components work together correctly.

- **End-to-end extraction**: Complete extraction workflow
- **Pipeline integration**: Component orchestration
- **Error handling**: Graceful error recovery

### Performance Tests (`@pytest.mark.slow`)
Tests that verify performance characteristics and scalability.

- **Throughput benchmarks**: Units/buildings processed per second
- **Memory usage**: Memory consumption with large datasets
- **Scalability**: Linear scaling verification

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run only fast unit tests
pytest -m "unit"

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_extraction/test_state_extractor.py

# Run specific test
pytest tests/test_extraction/test_state_extractor.py::TestUnitTracker::test_assign_unit_id_new_unit
```

### Using the Test Runner Script

```bash
# Run all tests
python run_tests.py

# Run only fast tests (skip slow/integration)
python run_tests.py --fast

# Run with coverage report
python run_tests.py --coverage

# Run tests for specific component
python run_tests.py --markers extraction

# Run tests in parallel (requires pytest-xdist)
python run_tests.py --parallel 4

# Verbose output
python run_tests.py --verbose
```

### Test Markers

- `unit`: Fast unit tests (isolated, no I/O)
- `integration`: Integration tests (component interaction)
- `slow`: Slow tests (>1 second)
- `extraction`: Tests for extraction components
- `pipeline`: Tests for pipeline components
- `utils`: Tests for utility components
- `validation`: Tests for validation functionality
- `performance`: Performance benchmarks

### Examples

```bash
# Run only unit tests for extraction components
pytest -m "unit and extraction"

# Run all tests except slow ones
pytest -m "not slow"

# Run integration and validation tests
pytest -m "integration or validation"

# Run all extraction tests (unit + integration)
pytest -m "extraction"
```

## Coverage Reports

Generate coverage reports to see which code is tested:

```bash
# Generate HTML coverage report
pytest --cov=src_new --cov-report=html tests/

# View report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

## Test Data and Fixtures

### Mock Observations

The `fixtures/mock_observations.py` module provides realistic mock pysc2 observations:

```python
from tests.fixtures.mock_observations import (
    create_mock_unit,
    create_mock_observation,
    create_marine_rush_sequence,
    create_building_construction_sequence,
)

# Create a single mock observation
obs = create_mock_observation(game_loop=100, units=[...])

# Create a sequence showing unit lifecycle
sequence = create_marine_rush_sequence()
```

### Sample Game States

The `fixtures/sample_game_states.py` module provides extracted game states:

```python
from tests.fixtures.sample_game_states import (
    create_sample_game_state,
    create_game_state_with_killed_unit,
    create_complex_game_state,
)

state = create_sample_game_state(game_loop=1000)
```

### Shared Fixtures

Common fixtures are defined in `conftest.py`:

- `temp_output_dir`: Temporary directory for test outputs
- `mock_config`: Sample configuration dictionary
- `mock_observation`: Basic mock observation
- `sample_extracted_state`: Sample extracted state
- `sample_parquet_dataframe`: Sample DataFrame for testing

## Writing New Tests

### Test Structure

```python
import pytest
from src_new.extraction.your_module import YourClass

@pytest.mark.unit  # Add appropriate markers
@pytest.mark.extraction
class TestYourClass:
    """Test suite for YourClass."""

    def test_initialization(self):
        """Test that YourClass initializes correctly."""
        obj = YourClass()
        assert obj is not None

    def test_specific_behavior(self):
        """Test specific behavior with descriptive name."""
        obj = YourClass()
        result = obj.some_method()
        assert result == expected_value
```

### Best Practices

1. **Use descriptive test names**: Test names should describe what they test
2. **Test one thing**: Each test should verify one specific behavior
3. **Use fixtures**: Reuse common setup via fixtures
4. **Mock external dependencies**: Don't rely on pysc2 or real replays
5. **Add markers**: Tag tests with appropriate markers
6. **Document complex tests**: Add docstrings explaining what's being tested

### Mocking pysc2

Since pysc2 is not installed, always mock it:

```python
from unittest.mock import Mock, patch

# Create mock observation
obs = Mock()
obs.observation.game_loop = 100
obs.observation.raw_data.units = []

# Or use provided fixtures
from tests.fixtures.mock_observations import create_mock_observation

obs = create_mock_observation(game_loop=100, units=[])
```

## Continuous Integration

The test suite is designed to run in CI environments:

```yaml
# Example GitHub Actions configuration
- name: Run tests
  run: |
    pytest tests/ --cov=src_new --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Tests Fail with ImportError

If you see import errors for `pysc2`, the test is trying to import it directly. Use mocks instead:

```python
# Bad
from pysc2.lib import units

# Good
from unittest.mock import Mock
mock_units = Mock()
```

### Tests Are Slow

Run only fast tests:

```bash
pytest -m "not slow"
```

Or run tests in parallel:

```bash
pytest -n 4  # Requires pytest-xdist
```

### Coverage is Low

Check which files are not covered:

```bash
pytest --cov=src_new --cov-report=term-missing
```

Then add tests for uncovered code.

## Test Statistics

Current test suite includes:

- **Unit Tests**: ~50+ tests covering core components
- **Integration Tests**: ~15+ tests covering workflows
- **Performance Tests**: ~10+ benchmarks
- **Total Test Coverage**: Target >80%

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure tests pass: `pytest`
3. Check coverage: `pytest --cov=src_new`
4. Add integration tests if needed
5. Update this README if adding new test categories

## Support

For questions about tests:
- Check test docstrings for details
- Review `conftest.py` for available fixtures
- Look at existing tests as examples
- Consult pytest documentation: https://docs.pytest.org/
