# Data Dictionary

Complete reference for the SC2 Replay Ground Truth Extraction Pipeline output schema.

## Table of Contents

- [Overview](#overview)
- [Game State Parquet Schema](#game-state-parquet-schema)
- [Messages Parquet Schema](#messages-parquet-schema)
- [Schema JSON Format](#schema-json-format)
- [Column Naming Conventions](#column-naming-conventions)
- [Data Types](#data-types)
- [Missing Value Handling](#missing-value-handling)
- [Use Cases for ML](#use-cases-for-ml)

---

## Overview

The pipeline generates three files per replay:

1. **`{replay_name}_game_state.parquet`** - Wide-format game state (main output)
2. **`{replay_name}_messages.parquet`** - Chat messages
3. **`{replay_name}_schema.json`** - Column metadata and documentation

---

## Game State Parquet Schema

### Core Columns

#### Temporal Columns

| Column | Type | Description | Example | Missing Value |
|--------|------|-------------|---------|---------------|
| `game_loop` | int64 | Game loop number (increases by step_size) | 1234 | Never missing |
| `timestamp_seconds` | float64 | Real-time timestamp in seconds (game_loop / 22.4) | 55.09 | Never missing |

#### Player Economy Columns

| Column | Type | Description | Example | Missing Value |
|--------|------|-------------|---------|---------------|
| `p1_minerals` | int64 | Player 1 current minerals | 450 | 0 if data unavailable |
| `p1_vespene` | int64 | Player 1 current vespene gas | 150 | 0 if data unavailable |
| `p1_supply_used` | int64 | Player 1 supply used | 120 | 0 if data unavailable |
| `p1_supply_cap` | int64 | Player 1 supply cap | 200 | 0 if data unavailable |
| `p1_supply_army` | int64 | Player 1 army supply | 100 | 0 if data unavailable |
| `p1_supply_workers` | int64 | Player 1 worker supply | 20 | 0 if data unavailable |
| `p1_workers_idle` | int64 | Player 1 idle worker count | 2 | 0 if data unavailable |
| `p1_army_count` | int64 | Player 1 total army units | 50 | 0 if data unavailable |
| `p1_minerals_collected` | int64 | Player 1 total minerals collected (lifetime) | 12500 | 0 if data unavailable |
| `p1_vespene_collected` | int64 | Player 1 total vespene collected (lifetime) | 4200 | 0 if data unavailable |
| `p1_mineral_rate` | float64 | Player 1 mineral collection rate (per minute) | 850.5 | 0.0 if data unavailable |
| `p1_vespene_rate` | float64 | Player 1 vespene collection rate (per minute) | 350.2 | 0.0 if data unavailable |

Same columns exist for Player 2 (`p2_*`).

#### Unit Count Columns

| Column | Type | Description | Example | Missing Value |
|--------|------|-------------|---------|---------------|
| `p1_marine_count` | int64 | Number of living marines for player 1 | 25 | 0 |
| `p1_medivac_count` | int64 | Number of living medivacs for player 1 | 3 | 0 |
| `p1_tank_count` | int64 | Number of living siege tanks for player 1 | 8 | 0 |
| ... | ... | One column per unit type that appears | ... | ... |

Same for Player 2 (`p2_*_count`).

### Unit Columns

For each unit that appears in the replay, there are columns tracking its position and state.

**Naming**: `{player}_{unit_type}_{id}_{attribute}`

**Example**: `p1_marine_001_x` = X-coordinate of player 1's first marine

#### Position Columns

| Column Pattern | Type | Description | Example | Missing Value |
|----------------|------|-------------|---------|---------------|
| `p{n}_{unit_type}_{id}_x` | float64 | X-coordinate on map | 45.25 | NaN when unit doesn't exist |
| `p{n}_{unit_type}_{id}_y` | float64 | Y-coordinate on map | 128.75 | NaN when unit doesn't exist |
| `p{n}_{unit_type}_{id}_z` | float64 | Z-coordinate (height) | 8.5 | NaN when unit doesn't exist |

#### State Columns

| Column Pattern | Type | Description | Example | Missing Value |
|----------------|------|-------------|---------|---------------|
| `p{n}_{unit_type}_{id}_state` | str | Unit lifecycle state | "built", "existing", "killed" | NaN when unit doesn't exist |

**State Values**:
- `"built"`: Unit appeared this frame (newly created)
- `"existing"`: Unit existed in previous frame and still exists
- `"killed"`: Unit was killed this frame (last appearance)

#### Health Columns (Optional)

| Column Pattern | Type | Description | Example | Missing Value |
|----------------|------|-------------|---------|---------------|
| `p{n}_{unit_type}_{id}_health` | int64 | Current health points | 45 | NaN when unit doesn't exist |
| `p{n}_{unit_type}_{id}_health_max` | int64 | Maximum health points | 45 | NaN when unit doesn't exist |
| `p{n}_{unit_type}_{id}_shield` | int64 | Current shield points (Protoss) | 0 | NaN when unit doesn't exist |
| `p{n}_{unit_type}_{id}_shield_max` | int64 | Maximum shield points | 0 | NaN when unit doesn't exist |

### Building Columns

For each building, similar to units but with construction tracking.

**Naming**: `{player}_{building_type}_{id}_{attribute}`

#### Position Columns

| Column Pattern | Type | Description | Example | Missing Value |
|----------------|------|-------------|---------|---------------|
| `p{n}_{building_type}_{id}_x` | float64 | X-coordinate | 32.5 | NaN when building doesn't exist |
| `p{n}_{building_type}_{id}_y` | float64 | Y-coordinate | 64.75 | NaN when building doesn't exist |
| `p{n}_{building_type}_{id}_z` | float64 | Z-coordinate | 0.0 | NaN when building doesn't exist |

#### Construction Columns

| Column Pattern | Type | Description | Example | Missing Value |
|----------------|------|-------------|---------|---------------|
| `p{n}_{building_type}_{id}_status` | str | Building lifecycle status | "building", "completed", "destroyed" | NaN when building doesn't exist |
| `p{n}_{building_type}_{id}_progress` | int64 | Construction progress (0-100) | 75 | NaN when building doesn't exist |
| `p{n}_{building_type}_{id}_started_loop` | int64 | Game loop when construction started | 500 | NaN when building doesn't exist |
| `p{n}_{building_type}_{id}_completed_loop` | int64 | Game loop when completed | 750 | NaN until completed |
| `p{n}_{building_type}_{id}_destroyed_loop` | int64 | Game loop when destroyed | 1200 | NaN until destroyed |

**Status Values**:
- `"started"`: Construction just began this frame
- `"building"`: Currently under construction
- `"completed"`: Construction finished
- `"destroyed"`: Building was destroyed

### Upgrade Columns

For each upgrade researched by a player.

**Naming**: `{player}_upgrade_{upgrade_name}`

| Column Pattern | Type | Description | Example | Missing Value |
|----------------|------|-------------|---------|---------------|
| `p{n}_upgrade_{name}` | bool | Whether upgrade is completed | True | False until researched |
| `p{n}_upgrade_{name}_loop` | int64 | Game loop when completed | 3500 | NaN until researched |

**Example Upgrades**:
- `p1_upgrade_stim`: Stimpack for marines
- `p1_upgrade_combatshield`: Combat shields for marines
- `p1_upgrade_infantryweaponslevel1`: Infantry weapons +1

---

## Messages Parquet Schema

| Column | Type | Description | Example | Missing Value |
|--------|------|-------------|---------|---------------|
| `game_loop` | int64 | Game loop when message sent | 450 | Never missing |
| `player_id` | int64 | Player who sent message (1 or 2) | 1 | Never missing |
| `message` | str | Message text | "glhf" | Empty string if corrupted |

---

## Schema JSON Format

The schema JSON file documents all columns in the game state parquet.

```json
{
  "columns": [
    "game_loop",
    "timestamp_seconds",
    "p1_minerals",
    "p1_marine_001_x",
    ...
  ],
  "documentation": {
    "game_loop": {
      "description": "Game loop number (increases by step_size each row)",
      "type": "int64",
      "example": 1234,
      "missing_value": "Never missing",
      "notes": "22.4 game loops ≈ 1 second on Faster game speed"
    },
    "p1_marine_001_x": {
      "description": "X-coordinate of player 1's marine #001",
      "type": "float64",
      "example": 45.25,
      "missing_value": "NaN when unit doesn't exist at this timestep",
      "notes": "Position on map, typically 0-200 depending on map size"
    },
    ...
  },
  "metadata": {
    "replay_name": "game1",
    "replay_path": "/path/to/game1.SC2Replay",
    "processing_date": "2026-01-25",
    "processing_mode": "two_pass",
    "step_size": 22,
    "total_rows": 1234,
    "total_columns": 567,
    "players": {
      "player_1": "PlayerName1",
      "player_2": "PlayerName2"
    },
    "map": "AcropolisLE",
    "game_duration_seconds": 610.5
  }
}
```

---

## Column Naming Conventions

### Pattern Structure

```
{player}_{entity_type}_{id}_{attribute}
```

**Components**:
- `player`: `p1` or `p2`
- `entity_type`: `marine`, `tank`, `barracks`, `commandcenter`, etc.
- `id`: Three-digit number (e.g., `001`, `002`, `123`)
- `attribute`: `x`, `y`, `z`, `state`, `health`, `status`, `progress`, etc.

### Examples

```python
# Unit position
p1_marine_001_x         # Player 1, marine #1, X coordinate
p2_zealot_025_y         # Player 2, zealot #25, Y coordinate

# Unit state
p1_marine_001_state     # "built", "existing", or "killed"

# Building construction
p1_barracks_003_status  # "started", "building", "completed", "destroyed"
p1_barracks_003_progress  # 0-100 (percentage)

# Economy
p1_minerals             # Player 1 current minerals
p2_supply_used          # Player 2 supply used

# Unit counts
p1_marine_count         # Total living marines for player 1

# Upgrades
p1_upgrade_stim         # True if stimpack researched
```

### ID Assignment

IDs are assigned **per unit type** in order of first appearance:

```python
# First marine that appears gets 001
p1_marine_001_x

# Second marine gets 002
p1_marine_002_x

# First tank gets 001 (separate counter from marines)
p1_tank_001_x
```

IDs are **consistent** across frames for the same replay (deterministic).

---

## Data Types

### Parquet Data Types

| Python Type | Parquet Type | Used For | Example |
|-------------|--------------|----------|---------|
| int | int64 | Game loop, supply, counts | 1234 |
| float | float64 | Coordinates, rates | 45.25 |
| str | string | States, status, messages | "built" |
| bool | boolean | Upgrades | True |

### Type Guarantees

- **Integers**: Always int64 (never int32 or smaller)
- **Floats**: Always float64 (never float32)
- **Strings**: UTF-8 encoded
- **Missing Values**: NaN for floats, None for strings, 0 for counts

---

## Missing Value Handling

### When Values Are Missing

| Scenario | How Represented | Example |
|----------|----------------|---------|
| Unit doesn't exist yet | NaN (float columns), None (string columns) | Marine hasn't been built yet |
| Unit was killed | NaN after death, "killed" in state column on death frame | Marine died at loop 1000 |
| Building not started | NaN for all building columns | Barracks not built yet |
| Upgrade not researched | False (boolean columns) | Stimpack not researched yet |
| Optional data unavailable | NaN or 0 depending on column type | Health data not extracted |

### Interpreting NaN Values

**For position columns (x, y, z)**:
- `NaN` = Unit/building doesn't exist at this timestep
- Check corresponding `_state` or `_status` column to understand why

**For state columns**:
- `None` or missing = Unit never existed at this timestep
- `"built"` = Unit appeared this frame
- `"existing"` = Unit alive
- `"killed"` = Unit died this frame (last appearance)

**For counts**:
- `0` = No units of this type alive
- Never NaN for count columns

### Handling Missing Data in Analysis

```python
import pandas as pd

df = pd.read_parquet("game_state.parquet")

# Check if marine exists at any point
marine_exists = df['p1_marine_001_x'].notna().any()

# Get frames where marine is alive
marine_alive = df[df['p1_marine_001_state'].isin(['built', 'existing'])]

# Get marine lifespan
first_appearance = df[df['p1_marine_001_state'] == 'built']['game_loop'].iloc[0]
last_appearance = df[df['p1_marine_001_state'] == 'killed']['game_loop'].iloc[0]
lifespan = last_appearance - first_appearance

# Forward fill positions (interpolate between observations)
df['p1_marine_001_x'] = df['p1_marine_001_x'].fillna(method='ffill')

# Drop rows where key units don't exist
df_filtered = df.dropna(subset=['p1_marine_001_x', 'p1_tank_001_x'])
```

---

## Use Cases for ML

### Time Series Prediction

**Predict future game state from current state**:

```python
# Features: current state (row t)
X = df[['p1_minerals', 'p1_supply_used', 'p1_marine_count']]

# Labels: future state (row t+10)
y = df[['p1_minerals', 'p1_supply_used', 'p1_marine_count']].shift(-10)

# Train model
model.fit(X, y)
```

### Outcome Prediction

**Predict winner from early game state**:

```python
# Features: state at 5 minutes
early_game = df[df['timestamp_seconds'] == 300]
X = early_game[['p1_minerals', 'p1_marine_count', 'p2_minerals', 'p2_marine_count']]

# Label: winner (1 or 2)
y = winner  # From replay metadata

model.fit(X, y)
```

### Unit Behavior Analysis

**Analyze unit movements and states**:

```python
# Extract marine trajectories
marine_positions = df[['game_loop', 'p1_marine_001_x', 'p1_marine_001_y']].dropna()

# Calculate velocity
marine_positions['vx'] = marine_positions['p1_marine_001_x'].diff()
marine_positions['vy'] = marine_positions['p1_marine_001_y'].diff()

# Detect engagements (rapid position changes)
speed = (marine_positions['vx']**2 + marine_positions['vy']**2)**0.5
engagements = marine_positions[speed > threshold]
```

### Build Order Recognition

**Classify build orders from building timestamps**:

```python
# Extract building completion times
barracks_time = df[df['p1_barracks_001_status'] == 'completed']['timestamp_seconds'].iloc[0]
factory_time = df[df['p1_factory_001_status'] == 'completed']['timestamp_seconds'].iloc[0]

# Features: building timings
X = [barracks_time, factory_time, ...]

# Label: build order name
y = "1-1-1 opener"

# Train classifier
classifier.fit(X, y)
```

### Resource Management Analysis

**Study resource collection efficiency**:

```python
# Calculate collection efficiency
df['p1_mineral_efficiency'] = df['p1_minerals_collected'] / df['timestamp_seconds']

# Compare against benchmarks
df['p1_ahead_benchmark'] = df['p1_mineral_efficiency'] > benchmark_rate

# Visualize
df.plot(x='timestamp_seconds', y='p1_mineral_efficiency')
```

### Feature Engineering

**Common feature engineering patterns**:

```python
# Delta features (changes over time)
df['p1_minerals_delta'] = df['p1_minerals'].diff()

# Ratio features
df['p1_army_supply_ratio'] = df['p1_supply_army'] / df['p1_supply_used']

# Boolean features
df['p1_has_stim'] = df['p1_upgrade_stim'].fillna(False)

# Aggregate features (rolling windows)
df['p1_marines_created_last_minute'] = (
    df['p1_marine_count'].rolling(window=60).max() -
    df['p1_marine_count'].rolling(window=60).min()
)

# Interaction features
df['p1_production_capacity'] = df['p1_barracks_count'] + df['p1_factory_count']
```

---

## Column Count Estimates

For a typical 10-minute 1v1 game:

- **Core columns**: ~30 (temporal, economy, counts)
- **Unit columns**: ~100-500 (depends on army size)
  - Per unit: 3-4 columns (x, y, z, state)
  - Example: 50 units × 4 columns = 200 columns
- **Building columns**: ~50-150 (depends on base count)
  - Per building: 5-8 columns (position, status, progress, timestamps)
  - Example: 20 buildings × 6 columns = 120 columns
- **Upgrade columns**: ~20-40 (depends on upgrades researched)

**Total**: ~200-800 columns per game state parquet

---

## Schema Validation

The `schema.json` file can be used to validate parquet files:

```python
import json
import pandas as pd

# Load schema
with open('schema.json', 'r') as f:
    schema = json.load(f)

# Load parquet
df = pd.read_parquet('game_state.parquet')

# Validate columns
expected_columns = set(schema['columns'])
actual_columns = set(df.columns)

missing = expected_columns - actual_columns
extra = actual_columns - expected_columns

if missing:
    print(f"Missing columns: {missing}")
if extra:
    print(f"Extra columns: {extra}")

# Validate types
for col in schema['documentation']:
    expected_type = schema['documentation'][col]['type']
    actual_type = str(df[col].dtype)
    if expected_type not in actual_type:
        print(f"Type mismatch for {col}: expected {expected_type}, got {actual_type}")
```

---

## Summary

The SC2 Replay Ground Truth Extraction Pipeline produces comprehensive, ML-ready datasets with:

- **Complete game state** at each timestep
- **Consistent schema** across all frames (in two-pass mode)
- **Rich metadata** in schema JSON
- **Proper missing value handling** for lifecycle events
- **Wide-format structure** optimized for ML workflows

For usage examples, see [usage.md](usage.md). For architecture details, see [architecture.md](architecture.md).
