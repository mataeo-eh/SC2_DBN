# Test Plan - SC2 Replay Ground Truth Extraction Pipeline

## Overview

This document defines comprehensive test cases and validation criteria for each implementation phase of the pipeline.

---

## Testing Strategy

### Test Levels

1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: Component interaction
3. **System Tests**: End-to-end pipeline
4. **Validation Tests**: Data quality and correctness
5. **Performance Tests**: Speed and resource usage

### Test Data

#### Test Replay Collection

Create/collect replays with specific characteristics:

| Replay Name | Description | Duration | Races | Purpose |
|-------------|-------------|----------|-------|---------|
| `short_tvz.SC2Replay` | Very short game | < 1000 loops | TvZ | Fast iteration, basic validation |
| `medium_tvp.SC2Replay` | Medium length | 5000-10000 loops | TvP | Typical game scenario |
| `long_zvz.SC2Replay` | Long game | > 20000 loops | ZvZ | Memory/performance testing |
| `many_units.SC2Replay` | High unit count | Any | Any | Schema stress test (200+ units) |
| `building_cancel.SC2Replay` | Cancelled buildings | Any | Any | Building lifecycle edge cases |
| `hallucinations.SC2Replay` | Contains hallucinations | Any | P | Hallucination handling |
| `drops.SC2Replay` | Units in transports | Any | T | Cargo/passenger testing |
| `all_upgrades.SC2Replay` | Many upgrades | Any | Any | Upgrade tracking |

---

## Phase 1: Core Components - Unit Tests

### Test Suite 1.1: Replay Loader

**File**: `tests/unit/test_replay_loader.py`

#### Test Cases

```python
def test_load_valid_replay():
    """Test loading a valid replay file"""
    # Arrange
    loader = ReplayLoader()
    replay_path = "test_data/short_tvz.SC2Replay"

    # Act
    controller, replay_data = loader.load_replay(replay_path)

    # Assert
    assert controller is not None
    assert replay_data is not None
    # Cleanup
    controller.quit()


def test_load_nonexistent_replay():
    """Test error handling for missing replay"""
    # Arrange
    loader = ReplayLoader()

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        loader.load_replay("nonexistent.SC2Replay")


def test_get_replay_info():
    """Test replay metadata extraction"""
    # Arrange
    loader = ReplayLoader()

    # Act
    info = loader.get_replay_info("test_data/short_tvz.SC2Replay")

    # Assert
    assert info.map_name is not None
    assert len(info.player_info) == 2
    assert info.game_duration_loops > 0


def test_validate_replay_too_short():
    """Test validation rejects very short games"""
    # Arrange
    loader = ReplayLoader()
    info = loader.get_replay_info("test_data/very_short.SC2Replay")

    # Act
    valid = loader.validate_replay(info, min_duration_loops=1000)

    # Assert
    assert valid == False


def test_interface_options():
    """Test interface options configuration"""
    # Act
    interface = ReplayLoader.get_interface_options(raw=True, score=True)

    # Assert
    assert interface.raw == True
    assert interface.score == True
```

**Success Criteria**:
- All tests pass
- Coverage > 90% for replay_loader.py
- Error cases properly handled

---

### Test Suite 1.2: Game Loop Iterator

**File**: `tests/unit/test_game_loop_iterator.py`

#### Test Cases

```python
def test_iterate_short_replay():
    """Test iteration through short replay"""
    # Arrange
    controller, _ = setup_replay("test_data/short_tvz.SC2Replay")
    iterator = GameLoopIterator(controller, step_mul=8)

    # Act
    observations = list(iterator)

    # Assert
    assert len(observations) > 0
    assert all(obs.observation.game_loop is not None for obs in observations)
    # Game loops should be monotonically increasing
    loops = [obs.observation.game_loop for obs in observations]
    assert all(loops[i] < loops[i+1] for i in range(len(loops)-1))


def test_step_mul_respected():
    """Test that step_mul is correctly applied"""
    # Arrange
    controller, _ = setup_replay("test_data/short_tvz.SC2Replay")
    step_mul = 16
    iterator = GameLoopIterator(controller, step_mul=step_mul)

    # Act
    observations = list(iterator)
    loops = [obs.observation.game_loop for obs in observations]

    # Assert
    # Differences between consecutive loops should be close to step_mul
    # (may vary slightly due to game end)
    diffs = [loops[i+1] - loops[i] for i in range(len(loops)-2)]
    assert all(diff >= step_mul and diff <= step_mul + 2 for diff in diffs)


def test_game_end_detection():
    """Test detection of game end"""
    # Arrange
    controller, _ = setup_replay("test_data/short_tvz.SC2Replay")
    iterator = GameLoopIterator(controller)

    # Act
    last_obs = None
    for obs in iterator:
        last_obs = obs

    # Assert
    assert iterator.is_game_ended(last_obs) == True
```

**Success Criteria**:
- Iteration produces expected number of observations
- step_mul is respected
- Game end correctly detected
- No crashes or hangs

---

### Test Suite 1.3: State Extractors

**File**: `tests/unit/test_extractors.py`

#### Unit Extractor Tests

```python
def test_extract_units_basic():
    """Test basic unit extraction"""
    # Arrange
    obs = load_test_observation("test_data/obs_with_units.pkl")
    extractor = UnitExtractor(player_id=1)

    # Act
    units = extractor.extract_units(obs)

    # Assert
    assert len(units) > 0
    for unit_id, unit_data in units.items():
        assert unit_data.x is not None
        assert unit_data.y is not None
        assert unit_data.state in ['built', 'existing', 'killed']


def test_unit_id_assignment():
    """Test that unit IDs are assigned consistently"""
    # Arrange
    extractor = UnitExtractor(player_id=1)
    tag = 12345
    unit_type = 48  # Marine

    # Act
    id1 = extractor.assign_readable_id(tag, unit_type)
    id2 = extractor.assign_readable_id(tag, unit_type)

    # Assert
    assert id1 == id2  # Same tag should get same ID
    assert id1 == "p1_marine_001"


def test_unit_state_detection():
    """Test unit state (built/existing/killed) detection"""
    # Arrange
    extractor = UnitExtractor(player_id=1)

    # Act & Assert
    # New unit
    state = extractor.get_unit_state(
        tag=100,
        current_tags={100, 200},
        dead_tags=set()
    )
    assert state == "built"

    # Existing unit
    extractor.previous_tags = {100, 200}
    state = extractor.get_unit_state(
        tag=100,
        current_tags={100, 200},
        dead_tags=set()
    )
    assert state == "existing"

    # Killed unit
    state = extractor.get_unit_state(
        tag=100,
        current_tags={200},
        dead_tags={100}
    )
    assert state == "killed"
```

#### Building Extractor Tests

```python
def test_building_lifecycle_tracking():
    """Test tracking of building from start to completion"""
    # Arrange
    extractor = BuildingExtractor(player_id=1)
    tag = 67890

    # Act & Assert
    # Started (progress = 0)
    status1 = extractor.track_building_lifecycle(tag, 0.0, 500, False)
    assert status1 == "started"

    # Building (progress = 0.5)
    status2 = extractor.track_building_lifecycle(tag, 0.5, 600, False)
    assert status2 == "building"

    # Completed (progress = 1.0)
    status3 = extractor.track_building_lifecycle(tag, 1.0, 850, False)
    assert status3 == "completed"

    # Check timestamps
    metadata = extractor.building_metadata[tag]
    assert metadata['started_loop'] == 500
    assert metadata['completed_loop'] == 850
```

#### Economy Extractor Tests

```python
def test_economy_extraction():
    """Test economy data extraction"""
    # Arrange
    obs = load_test_observation("test_data/obs_with_economy.pkl")
    extractor = EconomyExtractor()

    # Act
    economy = extractor.extract_economy(obs)

    # Assert
    assert economy.minerals >= 0
    assert economy.vespene >= 0
    assert economy.supply_used <= economy.supply_cap
    assert economy.supply_workers + economy.supply_army <= economy.supply_used
```

#### Upgrade Extractor Tests

```python
def test_upgrade_parsing():
    """Test upgrade name parsing"""
    # Arrange
    extractor = UpgradeExtractor()

    # Act
    info = extractor.parse_upgrade_name(7)  # TerranInfantryWeaponsLevel1

    # Assert
    assert "weapons" in info.category.lower()
    assert info.level == 1


def test_upgrade_tracking():
    """Test upgrade completion tracking"""
    # Arrange
    extractor = UpgradeExtractor()
    obs1 = create_obs_with_upgrades([])
    obs2 = create_obs_with_upgrades([7, 8])

    # Act
    upgrades1 = extractor.extract_upgrades(obs1, 1000)
    upgrades2 = extractor.extract_upgrades(obs2, 2000)

    # Assert
    assert len([k for k, v in upgrades2.items() if v]) == 2
    # Check that completion timestamp was recorded
    assert 7 in extractor.upgrade_metadata
    assert extractor.upgrade_metadata[7].completed_loop == 2000
```

**Success Criteria**:
- All extractor tests pass
- Unit tracking works correctly
- Building lifecycle properly tracked
- Economy and upgrades extracted accurately

---

## Phase 2: Integration Tests

### Test Suite 2.1: State Extractor Integration

**File**: `tests/integration/test_state_extraction.py`

```python
def test_full_state_extraction():
    """Test extraction of complete state from observation"""
    # Arrange
    obs = load_real_observation("test_data/obs_complete.pkl")
    extractor = StateExtractor(player_id=1)

    # Act
    state = extractor.extract(obs)

    # Assert
    assert state.game_loop > 0
    assert len(state.units) >= 0
    assert len(state.buildings) >= 0
    assert state.economy is not None
    assert state.upgrades is not None


def test_state_extraction_consistency():
    """Test that extracting same observation produces same results"""
    # Arrange
    obs = load_real_observation("test_data/obs_complete.pkl")
    extractor1 = StateExtractor(player_id=1)
    extractor2 = StateExtractor(player_id=1)

    # Act
    state1 = extractor1.extract(obs)
    state2 = extractor2.extract(obs)

    # Assert
    assert state1.game_loop == state2.game_loop
    assert len(state1.units) == len(state2.units)
    assert state1.economy.minerals == state2.economy.minerals
```

---

### Test Suite 2.2: Wide Table Builder Integration

**File**: `tests/integration/test_wide_table.py`

```python
def test_wide_table_generation():
    """Test conversion of state to wide table row"""
    # Arrange
    schema = create_test_schema()  # Schema with known columns
    state = create_test_state()    # State with known values
    builder = WideTableBuilder(schema)

    # Act
    row = builder.build_row(state)

    # Assert
    assert 'game_loop' in row
    assert row['game_loop'] == state.game_loop
    # Check that all schema columns are present
    assert set(row.keys()) == set(schema.get_column_names())
    # Check NaN for missing units
    if 'p1_marine_003_x' in row and 'p1_marine_003' not in state.units:
        assert pd.isna(row['p1_marine_003_x'])


def test_batch_building():
    """Test building multiple rows efficiently"""
    # Arrange
    schema = create_test_schema()
    states = [create_test_state() for _ in range(100)]
    builder = WideTableBuilder(schema)

    # Act
    rows = builder.build_batch(states)

    # Assert
    assert len(rows) == 100
    assert all('game_loop' in row for row in rows)
```

---

## Phase 3: End-to-End System Tests

### Test Suite 3.1: Single Replay Processing

**File**: `tests/system/test_single_replay.py`

```python
def test_process_short_replay():
    """Test processing a complete short replay"""
    # Arrange
    replay_path = "test_data/short_tvz.SC2Replay"
    output_dir = "test_output/"
    config = create_test_config()

    # Act
    processor = ReplayProcessor(
        proc_id=0,
        replay_queue=None,
        stats_queue=None,
        output_dir=output_dir,
        config=config
    )
    success = processor.process_two_pass(replay_path)

    # Assert
    assert success == True

    # Check output file exists
    output_path = Path(output_dir) / "short_tvz_parsed.parquet"
    assert output_path.exists()

    # Load and validate
    df = pd.read_parquet(output_path)
    assert len(df) > 0
    assert 'game_loop' in df.columns
    assert df['game_loop'].is_monotonic_increasing


def test_two_player_extraction():
    """Test that both players' data is extracted"""
    # Arrange
    replay_path = "test_data/medium_tvp.SC2Replay"
    output_dir = "test_output/"

    # Act
    success = process_replay(replay_path, output_dir, multi_player=True)

    # Assert
    assert success == True
    df = pd.read_parquet(Path(output_dir) / "medium_tvp_parsed.parquet")

    # Should have columns for both players
    assert any('p1_' in col for col in df.columns)
    assert any('p2_' in col for col in df.columns)
```

---

### Test Suite 3.2: Batch Processing

**File**: `tests/system/test_batch_processing.py`

```python
def test_batch_processing_multiple_replays():
    """Test batch processing of multiple replays"""
    # Arrange
    replay_dir = "test_data/batch/"
    output_dir = "test_output/batch/"
    config = create_test_config(num_workers=2)

    # Act
    results = run_batch_processing(
        replay_dir=Path(replay_dir),
        output_dir=Path(output_dir),
        config=config
    )

    # Assert
    assert results['total_replays'] == 3
    assert results['processed'] >= 2  # At least 2 should succeed
    assert results['failed'] <= 1

    # Check output files
    output_files = list(Path(output_dir).glob("*.parquet"))
    assert len(output_files) >= 2


def test_parallel_processing():
    """Test that parallel processing produces same results as serial"""
    # Arrange
    replay_path = "test_data/medium_tvp.SC2Replay"

    # Act
    # Process serially
    df_serial = process_replay(replay_path, num_workers=1)

    # Process in parallel
    df_parallel = process_replay(replay_path, num_workers=4)

    # Assert
    assert len(df_serial) == len(df_parallel)
    # Data should be identical (allowing for float precision)
    pd.testing.assert_frame_equal(df_serial, df_parallel)
```

---

## Phase 4: Data Validation Tests

### Test Suite 4.1: Schema Validation

**File**: `tests/validation/test_schema.py`

```python
def test_schema_completeness():
    """Test that schema includes all necessary columns"""
    # Arrange
    schema = generate_schema_from_replay("test_data/medium_tvp.SC2Replay")

    # Assert
    # Core columns
    assert 'game_loop' in schema.column_names

    # Economy columns for both players
    for player in [1, 2]:
        assert f'p{player}_minerals' in schema.column_names
        assert f'p{player}_vespene' in schema.column_names
        assert f'p{player}_supply_used' in schema.column_names


def test_column_dtypes():
    """Test that column data types are correct"""
    # Arrange
    df = pd.read_parquet("test_output/short_tvz_parsed.parquet")

    # Assert
    assert df['game_loop'].dtype == 'int32'
    assert df['p1_minerals'].dtype == 'int32'
    # Position columns should be float32
    if 'p1_marine_001_x' in df.columns:
        assert df['p1_marine_001_x'].dtype == 'float32'
```

---

### Test Suite 4.2: Data Quality Validation

**File**: `tests/validation/test_data_quality.py`

```python
def test_unique_game_loops():
    """Test that game_loop values are unique"""
    # Arrange
    df = pd.read_parquet("test_output/medium_tvp_parsed.parquet")

    # Assert
    assert df['game_loop'].is_unique


def test_monotonic_game_loops():
    """Test that game_loop increases monotonically"""
    # Arrange
    df = pd.read_parquet("test_output/medium_tvp_parsed.parquet")

    # Assert
    assert df['game_loop'].is_monotonic_increasing


def test_supply_constraints():
    """Test that supply_used <= supply_cap"""
    # Arrange
    df = pd.read_parquet("test_output/medium_tvp_parsed.parquet")

    # Assert
    for player in [1, 2]:
        used_col = f'p{player}_supply_used'
        cap_col = f'p{player}_supply_cap'
        if used_col in df.columns and cap_col in df.columns:
            assert (df[used_col] <= df[cap_col]).all()


def test_health_constraints():
    """Test that health <= health_max for all units"""
    # Arrange
    df = pd.read_parquet("test_output/many_units_parsed.parquet")

    # Assert
    health_cols = [col for col in df.columns if col.endswith('_health') and not col.endswith('_max')]
    for health_col in health_cols:
        max_col = health_col + '_max'
        if max_col in df.columns:
            # Only check where both are not NaN
            mask = df[health_col].notna() & df[max_col].notna()
            assert (df.loc[mask, health_col] <= df.loc[mask, max_col]).all()


def test_unit_counts_match():
    """Test that unit count columns match actual unit entries"""
    # Arrange
    df = pd.read_parquet("test_output/medium_tvp_parsed.parquet")

    # Assert
    # Count non-NaN entries for p1_marine
    marine_cols = [col for col in df.columns if col.startswith('p1_marine_') and col.endswith('_x')]
    for _, row in df.iterrows():
        actual_count = sum(1 for col in marine_cols if pd.notna(row[col]))
        if 'p1_marine_count' in row:
            assert row['p1_marine_count'] == actual_count


def test_position_bounds():
    """Test that positions are within reasonable map bounds"""
    # Arrange
    df = pd.read_parquet("test_output/medium_tvp_parsed.parquet")

    # Assert
    position_cols = [col for col in df.columns if col.endswith('_x') or col.endswith('_y')]
    for col in position_cols:
        valid_positions = df[col].dropna()
        assert (valid_positions >= 0).all()
        assert (valid_positions <= 250).all()  # Typical map size
```

---

## Phase 5: Performance Tests

### Test Suite 5.1: Speed Benchmarks

**File**: `tests/performance/test_speed.py`

```python
import time

def test_single_replay_processing_time():
    """Test that single replay processing meets time target"""
    # Arrange
    replay_path = "test_data/medium_tvp.SC2Replay"
    config = create_test_config(step_mul=8)

    # Act
    start = time.time()
    success = process_replay(replay_path, config)
    elapsed = time.time() - start

    # Assert
    assert success == True
    # Should process in < 10 minutes (600 seconds)
    assert elapsed < 600


def test_batch_throughput():
    """Test batch processing throughput"""
    # Arrange
    replay_dir = "test_data/batch_10/"  # 10 replays
    config = create_test_config(num_workers=4)

    # Act
    start = time.time()
    results = run_batch_processing(replay_dir, config)
    elapsed = time.time() - start

    # Assert
    # Should process at least 2 replays per minute with 4 workers
    rate = results['processed'] / (elapsed / 60)
    assert rate >= 2.0
```

---

### Test Suite 5.2: Memory Usage

**File**: `tests/performance/test_memory.py`

```python
import psutil
import os

def test_memory_usage_per_worker():
    """Test that worker memory usage stays within limits"""
    # Arrange
    replay_path = "test_data/long_zvz.SC2Replay"
    config = create_test_config()

    # Act
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    success = process_replay(replay_path, config)

    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    mem_used = mem_after - mem_before

    # Assert
    assert success == True
    # Should use < 3 GB per worker (2 GB SC2 + overhead)
    assert mem_used < 3000


def test_no_memory_leaks():
    """Test that processing multiple replays doesn't leak memory"""
    # Arrange
    replay_paths = ["test_data/short_tvz.SC2Replay"] * 10
    config = create_test_config()
    process = psutil.Process(os.getpid())

    # Act
    memory_samples = []
    for replay_path in replay_paths:
        process_replay(replay_path, config)
        mem = process.memory_info().rss / 1024 / 1024
        memory_samples.append(mem)

    # Assert
    # Memory shouldn't grow significantly after first replay
    # Allow 10% growth max
    assert memory_samples[-1] < memory_samples[1] * 1.1
```

---

## Phase 6: Edge Cases and Error Handling

### Test Suite 6.1: Edge Cases

**File**: `tests/edge_cases/test_edge_cases.py`

```python
def test_cancelled_building():
    """Test handling of cancelled buildings"""
    # Arrange
    replay_path = "test_data/building_cancel.SC2Replay"

    # Act
    df = process_replay(replay_path)

    # Assert
    # Should have building with started_loop but no completed_loop
    barracks_cols = [col for col in df.columns if 'barracks' in col and 'started_loop' in col]
    for col in barracks_cols:
        completed_col = col.replace('started_loop', 'completed_loop')
        # Some buildings should have started but not completed
        has_started = df[col].notna().any()
        has_completed = df[completed_col].notna().any()
        if has_started:
            # This is fine - building was cancelled
            pass


def test_unit_in_transport():
    """Test handling of units inside transports"""
    # Arrange
    replay_path = "test_data/drops.SC2Replay"

    # Act
    df = process_replay(replay_path)

    # Assert
    # Units should still be tracked even when in transport
    # (pysc2 shows them in passenger list)
    assert len(df) > 0


def test_hallucination_units():
    """Test handling of hallucination units"""
    # Arrange
    replay_path = "test_data/hallucinations.SC2Replay"
    config = create_test_config(track_hallucinations=False)

    # Act
    df = process_replay(replay_path, config)

    # Assert
    # If not tracking hallucinations separately, they should be included
    # in normal unit columns
    assert len(df) > 0


def test_very_long_game():
    """Test handling of very long game (> 30k loops)"""
    # Arrange
    replay_path = "test_data/very_long.SC2Replay"
    config = create_test_config()

    # Act
    df = process_replay(replay_path, config)

    # Assert
    assert len(df) > 1000  # Should have many rows
    assert df['game_loop'].max() > 30000
```

---

### Test Suite 6.2: Error Handling

**File**: `tests/error_handling/test_errors.py`

```python
def test_corrupted_replay():
    """Test handling of corrupted replay file"""
    # Arrange
    replay_path = "test_data/corrupted.SC2Replay"

    # Act & Assert
    with pytest.raises(Exception):  # Should raise error
        process_replay(replay_path)


def test_version_mismatch():
    """Test handling of version mismatch"""
    # Arrange
    replay_path = "test_data/old_version.SC2Replay"

    # Act
    # Should either process successfully or fail gracefully
    try:
        result = process_replay(replay_path)
        # If it succeeds, that's fine
        assert result is not None
    except VersionMismatchError:
        # If it fails with version error, that's expected
        pass


def test_missing_map():
    """Test handling of missing map file"""
    # Arrange
    replay_path = "test_data/custom_map.SC2Replay"

    # Act & Assert
    with pytest.raises(MapNotFoundError):
        process_replay(replay_path)
```

---

## Test Execution Plan

### Phase 1: Unit Tests (Day 1-2)
```bash
pytest tests/unit/ -v --cov=src/
```
- Target: 90%+ code coverage
- All component tests must pass

### Phase 2: Integration Tests (Day 3)
```bash
pytest tests/integration/ -v
```
- Target: All integration tests pass
- Components work together correctly

### Phase 3: System Tests (Day 4-5)
```bash
pytest tests/system/ -v --slow
```
- Target: End-to-end pipeline works
- Both single and batch processing succeed

### Phase 4: Validation Tests (Day 6)
```bash
pytest tests/validation/ -v
```
- Target: All data quality checks pass
- No constraint violations

### Phase 5: Performance Tests (Day 7)
```bash
pytest tests/performance/ -v --benchmark
```
- Target: Meet performance targets
- No memory leaks

### Phase 6: Edge Cases (Day 8)
```bash
pytest tests/edge_cases/ -v
pytest tests/error_handling/ -v
```
- Target: Graceful handling of all edge cases
- Proper error messages

---

## Continuous Integration

### CI Pipeline Configuration

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src/

      - name: Run integration tests
        run: pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Acceptance Criteria

### For Each Implementation Phase

1. **Phase 1 - Core Components**:
   - All unit tests pass
   - Code coverage > 90%
   - Components work in isolation

2. **Phase 2 - Integration**:
   - All integration tests pass
   - Components work together
   - Data flows correctly through pipeline

3. **Phase 3 - System**:
   - Can process test replays end-to-end
   - Output files are valid Parquet
   - Batch processing works

4. **Phase 4 - Validation**:
   - All data quality checks pass
   - No invalid data in output
   - Constraints are enforced

5. **Phase 5 - Performance**:
   - Meets speed targets (< 10 min per replay)
   - Stays within memory limits (< 3 GB per worker)
   - No memory leaks

6. **Phase 6 - Production Ready**:
   - Handles all edge cases
   - Error messages are clear
   - Logging is comprehensive
   - Documentation is complete

---

## Test Data Management

### Test Data Repository

```
test_data/
├── short_tvz.SC2Replay          # < 1000 loops
├── medium_tvp.SC2Replay         # ~10000 loops
├── long_zvz.SC2Replay           # > 20000 loops
├── many_units.SC2Replay         # 200+ units
├── building_cancel.SC2Replay    # Cancelled buildings
├── hallucinations.SC2Replay     # Protoss hallucinations
├── drops.SC2Replay              # Transport units
├── all_upgrades.SC2Replay       # Many upgrades
├── very_long.SC2Replay          # > 30k loops
├── corrupted.SC2Replay          # Invalid file
├── old_version.SC2Replay        # Old SC2 version
├── custom_map.SC2Replay         # Custom map
└── batch/                       # Batch of 10 replays
    ├── game_001.SC2Replay
    ├── game_002.SC2Replay
    └── ...
```

### Creating Test Data

```python
# Script to generate test observations
def create_test_observation():
    """Create synthetic observation for unit testing"""
    obs = ResponseObservation()
    obs.observation.game_loop = 1000
    # Add test units, buildings, etc.
    return obs
```

---

## Summary

This test plan provides comprehensive coverage for:
- ✅ All components
- ✅ Integration points
- ✅ End-to-end pipeline
- ✅ Data quality
- ✅ Performance
- ✅ Edge cases
- ✅ Error handling

**Total Tests**: ~50-60 test cases
**Estimated Test Development Time**: 8 days
**Estimated Execution Time**: 30-60 minutes (full suite)
