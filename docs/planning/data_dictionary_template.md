# Data Dictionary Template

## Overview

This template defines the structure for auto-generated data dictionaries that explain the columns in extracted SC2 replay data.

---

## Template Structure

Each data dictionary should be generated automatically for each processed replay and include:

1. **File Information**
2. **Column Index**
3. **Detailed Column Descriptions**
4. **Data Types Reference**
5. **Usage Examples**

---

## Template: Data Dictionary for {REPLAY_NAME}

### File Information

```markdown
# Data Dictionary: {REPLAY_NAME}

**Generated**: {TIMESTAMP}
**Replay File**: {REPLAY_PATH}
**Output File**: {PARQUET_PATH}
**SC2 Version**: {SC2_VERSION}
**Map**: {MAP_NAME}
**Players**: {PLAYER_1_NAME} ({PLAYER_1_RACE}) vs {PLAYER_2_NAME} ({PLAYER_2_RACE})
**Game Duration**: {DURATION_LOOPS} loops ({DURATION_MINUTES} minutes)
**Observation Frequency**: Every {STEP_MUL} loops ({STEP_MUL_SECONDS} seconds)
**Total Rows**: {TOTAL_ROWS}
**Total Columns**: {TOTAL_COLUMNS}
```

### Column Index

```markdown
## Column Categories

### Core Columns (1)
- `game_loop` - Game loop number (time dimension)

### Player 1 ({PLAYER_1_RACE}) Columns ({P1_COLUMN_COUNT})

#### Units ({P1_UNIT_COLUMN_COUNT})
{FOR_EACH_P1_UNIT_TYPE}
- **{UNIT_NAME}** ({UNIT_COUNT} instances):
  - `p1_{unit_name}_001_x` to `p1_{unit_name}_{max:03d}_x` - X positions
  - `p1_{unit_name}_001_y` to `p1_{unit_name}_{max:03d}_y` - Y positions
  - `p1_{unit_name}_001_z` to `p1_{unit_name}_{max:03d}_z` - Z positions
  - `p1_{unit_name}_001_state` to `p1_{unit_name}_{max:03d}_state` - States
  - `p1_{unit_name}_001_health` to `p1_{unit_name}_{max:03d}_health` - Health
  - `p1_{unit_name}_count` - Total count
{END_FOR}

#### Buildings ({P1_BUILDING_COLUMN_COUNT})
{FOR_EACH_P1_BUILDING_TYPE}
- **{BUILDING_NAME}** ({BUILDING_COUNT} instances):
  - `p1_{building_name}_001_x` to `p1_{building_name}_{max:03d}_x` - X positions
  - `p1_{building_name}_001_status` to `p1_{building_name}_{max:03d}_status` - Status
  - `p1_{building_name}_001_progress` to `p1_{building_name}_{max:03d}_progress` - Progress
  - `p1_{building_name}_count` - Total count
{END_FOR}

#### Economy (8 columns)
- `p1_minerals` - Mineral count
- `p1_vespene` - Vespene gas count
- `p1_supply_used` - Supply used
- `p1_supply_cap` - Supply cap
- `p1_supply_workers` - Worker supply
- `p1_supply_army` - Army supply
- `p1_idle_workers` - Idle worker count
- `p1_army_count` - Total army count

#### Upgrades ({P1_UPGRADE_COUNT})
{FOR_EACH_P1_UPGRADE}
- `p1_upgrade_{upgrade_name}` - {UPGRADE_DESCRIPTION}
{END_FOR}

### Player 2 ({PLAYER_2_RACE}) Columns ({P2_COLUMN_COUNT})
{SIMILAR_STRUCTURE_FOR_PLAYER_2}

---

## Detailed Column Descriptions

### Core Columns

#### game_loop
- **Type**: int32
- **Description**: Game loop number, primary time dimension for the data
- **Range**: {MIN_LOOP} to {MAX_LOOP}
- **Unique**: Yes
- **Nullable**: No
- **Notes**:
  - At 22.4 loops per second, loop 1000 ≈ 44.6 seconds of game time
  - Observations occur every {STEP_MUL} loops
  - Missing loops indicate no observation was taken
- **Example Values**: 0, 8, 16, 24, ..., {MAX_LOOP}

---

### Player 1: {PLAYER_1_NAME} ({PLAYER_1_RACE})

---

#### Units

{FOR_EACH_UNIT_TYPE}

##### {UNIT_NAME} (Total: {MAX_COUNT})

**Position Columns**:

###### p1_{unit_name}_{id:03d}_x
- **Type**: float32
- **Description**: X-coordinate of {unit_name} #{id} in world coordinates
- **Range**: 0.0 to {MAP_WIDTH}
- **Nullable**: Yes
- **NaN Meaning**: Unit does not exist at this game loop
- **Unit**: Game world units
- **First Appearance**: Loop {FIRST_SEEN_LOOP}
- **Last Appearance**: Loop {LAST_SEEN_LOOP}
- **Example Values**: {EXAMPLE_VALUES}

###### p1_{unit_name}_{id:03d}_y
- **Type**: float32
- **Description**: Y-coordinate of {unit_name} #{id} in world coordinates
- **Range**: 0.0 to {MAP_HEIGHT}
- **Nullable**: Yes
- **NaN Meaning**: Unit does not exist at this game loop
- **Unit**: Game world units
- **Example Values**: {EXAMPLE_VALUES}

###### p1_{unit_name}_{id:03d}_z
- **Type**: float32
- **Description**: Z-coordinate (terrain height) of {unit_name} #{id}
- **Range**: 0.0 to ~20.0 (varies by map)
- **Nullable**: Yes
- **NaN Meaning**: Unit does not exist at this game loop
- **Unit**: Game world units
- **Example Values**: {EXAMPLE_VALUES}

**State Column**:

###### p1_{unit_name}_{id:03d}_state
- **Type**: string
- **Description**: State of {unit_name} #{id} at this game loop
- **Nullable**: Yes
- **NaN Meaning**: Unit does not exist at this game loop
- **Possible Values**:
  - `"built"` - Unit was created this game loop
  - `"existing"` - Unit is alive and present
  - `"killed"` - Unit died this game loop
- **Created Loop**: {CREATED_LOOP}
- **Killed Loop**: {KILLED_LOOP} (if applicable)
- **Example Values**: "existing", "existing", "killed", NaN

**Health Columns**:

###### p1_{unit_name}_{id:03d}_health
- **Type**: float32
- **Description**: Current health of {unit_name} #{id}
- **Range**: 0.0 to {HEALTH_MAX}
- **Nullable**: Yes
- **NaN Meaning**: Unit does not exist at this game loop
- **Unit**: Hit points
- **Example Values**: {EXAMPLE_VALUES}

###### p1_{unit_name}_{id:03d}_health_max
- **Type**: float32
- **Description**: Maximum health of {unit_name} #{id}
- **Range**: {HEALTH_MAX}
- **Nullable**: Yes
- **Constant**: Yes (same value when unit exists)
- **Example Values**: {HEALTH_MAX}

{IF_HAS_SHIELDS}
**Shield Columns** (Protoss units only):

###### p1_{unit_name}_{id:03d}_shields
- **Type**: float32
- **Description**: Current shields of {unit_name} #{id}
- **Range**: 0.0 to {SHIELDS_MAX}
- **Nullable**: Yes
- **Unit**: Shield points
- **Example Values**: {EXAMPLE_VALUES}

###### p1_{unit_name}_{id:03d}_shields_max
- **Type**: float32
- **Description**: Maximum shields of {unit_name} #{id}
- **Range**: {SHIELDS_MAX}
- **Nullable**: Yes
- **Constant**: Yes
- **Example Values**: {SHIELDS_MAX}
{END_IF}

{IF_HAS_ENERGY}
**Energy Columns** (Caster units):

###### p1_{unit_name}_{id:03d}_energy
- **Type**: float32
- **Description**: Current energy of {unit_name} #{id}
- **Range**: 0.0 to {ENERGY_MAX}
- **Nullable**: Yes
- **Unit**: Energy points
- **Example Values**: {EXAMPLE_VALUES}

###### p1_{unit_name}_{id:03d}_energy_max
- **Type**: float32
- **Description**: Maximum energy of {unit_name} #{id}
- **Range**: {ENERGY_MAX}
- **Nullable**: Yes
- **Constant**: Yes
- **Example Values**: {ENERGY_MAX}
{END_IF}

**Count Column**:

###### p1_{unit_name}_count
- **Type**: int16
- **Description**: Total count of {unit_name} units alive at this game loop
- **Range**: 0 to {MAX_COUNT}
- **Nullable**: No
- **Default**: 0
- **Peak Value**: {MAX_COUNT} at loop {PEAK_LOOP}
- **Example Values**: 0, 2, 5, 8, {MAX_COUNT}, 3, 0

{END_FOR_EACH_UNIT}

---

#### Buildings

{FOR_EACH_BUILDING_TYPE}

##### {BUILDING_NAME} (Total: {MAX_COUNT})

**Position Columns**:

###### p1_{building_name}_{id:03d}_x, _y, _z
- **Type**: float32
- **Description**: Position coordinates of {building_name} #{id}
- **Nullable**: Yes
- **NaN Meaning**: Building does not exist at this game loop
- **Notes**: Buildings don't move, so coordinates are constant when building exists
- **Example Values**: {EXAMPLE_VALUES}

**Status Column**:

###### p1_{building_name}_{id:03d}_status
- **Type**: string
- **Description**: Lifecycle status of {building_name} #{id}
- **Nullable**: Yes
- **NaN Meaning**: Building does not exist at this game loop
- **Possible Values**:
  - `"started"` - Construction started this loop
  - `"building"` - Under construction
  - `"completed"` - Construction finished, building operational
  - `"destroyed"` - Building destroyed this loop
- **Lifecycle**: started (loop {START_LOOP}) → building → completed (loop {COMPLETE_LOOP}) → destroyed (loop {DESTROY_LOOP})

**Progress Column**:

###### p1_{building_name}_{id:03d}_progress
- **Type**: float32
- **Description**: Construction progress percentage of {building_name} #{id}
- **Range**: 0.0 to 100.0
- **Nullable**: Yes
- **NaN Meaning**: Building does not exist
- **Notes**: Increases from 0.0 at start to 100.0 at completion
- **Example Values**: 0.0, 25.5, 50.0, 75.5, 100.0

**Timestamp Columns**:

###### p1_{building_name}_{id:03d}_started_loop
- **Type**: int32
- **Description**: Game loop when construction of {building_name} #{id} started
- **Nullable**: Yes
- **NaN Meaning**: Building never started or doesn't exist
- **Constant**: Yes (set once when building starts)
- **Value**: {STARTED_LOOP}

###### p1_{building_name}_{id:03d}_completed_loop
- **Type**: int32
- **Description**: Game loop when construction of {building_name} #{id} completed
- **Nullable**: Yes
- **NaN Meaning**: Building not yet completed or doesn't exist
- **Constant**: Yes (set once when building completes)
- **Value**: {COMPLETED_LOOP}

###### p1_{building_name}_{id:03d}_destroyed_loop
- **Type**: int32
- **Description**: Game loop when {building_name} #{id} was destroyed
- **Nullable**: Yes
- **NaN Meaning**: Building not destroyed or doesn't exist
- **Constant**: Yes (set once if/when building is destroyed)
- **Value**: {DESTROYED_LOOP} or NaN

**Count Column**:

###### p1_{building_name}_count
- **Type**: int16
- **Description**: Total count of {building_name} buildings for player 1
- **Range**: 0 to {MAX_COUNT}
- **Nullable**: No
- **Default**: 0
- **Peak Value**: {MAX_COUNT} at loop {PEAK_LOOP}

{END_FOR_EACH_BUILDING}

---

#### Economy

###### p1_minerals
- **Type**: int32
- **Description**: Current mineral count for Player 1
- **Range**: 0 to {MAX_MINERALS}
- **Nullable**: No
- **Default**: 50 (starting minerals)
- **Unit**: Minerals
- **Statistics**:
  - Mean: {MEAN_MINERALS}
  - Max: {MAX_MINERALS} at loop {MAX_MINERALS_LOOP}
  - Min: {MIN_MINERALS} at loop {MIN_MINERALS_LOOP}
- **Example Values**: 50, 200, 450, 680, 320

###### p1_vespene
- **Type**: int32
- **Description**: Current vespene gas count for Player 1
- **Range**: 0 to {MAX_VESPENE}
- **Nullable**: No
- **Default**: 0 (starting vespene)
- **Unit**: Vespene gas
- **Statistics**:
  - Mean: {MEAN_VESPENE}
  - Max: {MAX_VESPENE} at loop {MAX_VESPENE_LOOP}
  - Min: 0
- **Example Values**: 0, 50, 150, 300, 125

###### p1_supply_used
- **Type**: int16
- **Description**: Total supply used by Player 1
- **Range**: 0 to 200
- **Nullable**: No
- **Default**: 12 (starting workers)
- **Unit**: Supply
- **Notes**: supply_used = supply_workers + supply_army
- **Statistics**:
  - Mean: {MEAN_SUPPLY_USED}
  - Max: {MAX_SUPPLY_USED} at loop {MAX_SUPPLY_LOOP}
- **Example Values**: 12, 24, 45, 60, 88, 120

###### p1_supply_cap
- **Type**: int16
- **Description**: Supply cap for Player 1
- **Range**: 0 to 200
- **Nullable**: No
- **Default**: 15 (starting cap)
- **Unit**: Supply
- **Notes**: Must build supply structures to increase cap
- **Statistics**:
  - Max: {MAX_SUPPLY_CAP} at loop {MAX_CAP_LOOP}
- **Example Values**: 15, 23, 31, 47, 63, 95, 200

###### p1_supply_workers
- **Type**: int16
- **Description**: Supply used by worker units for Player 1
- **Range**: 0 to 200
- **Nullable**: No
- **Unit**: Supply
- **Notes**: Each worker uses 1 supply
- **Statistics**:
  - Mean: {MEAN_WORKERS}
  - Max: {MAX_WORKERS} at loop {MAX_WORKERS_LOOP}

###### p1_supply_army
- **Type**: int16
- **Description**: Supply used by army units for Player 1
- **Range**: 0 to 200
- **Nullable**: No
- **Unit**: Supply
- **Notes**: Different units use different supply (e.g., Marine=1, Thor=6)

###### p1_idle_workers
- **Type**: int16
- **Description**: Number of idle worker units for Player 1
- **Range**: 0 to {MAX_WORKERS}
- **Nullable**: No
- **Default**: 0
- **Notes**: High idle worker count indicates inefficient play
- **Statistics**:
  - Mean: {MEAN_IDLE_WORKERS}
  - Max: {MAX_IDLE_WORKERS}

###### p1_army_count
- **Type**: int16
- **Description**: Total count of army units for Player 1
- **Range**: 0 to {MAX_ARMY_COUNT}
- **Nullable**: No
- **Default**: 0
- **Notes**: Count of non-worker combat units
- **Statistics**:
  - Mean: {MEAN_ARMY_COUNT}
  - Max: {MAX_ARMY_COUNT} at loop {MAX_ARMY_LOOP}

---

#### Upgrades

{FOR_EACH_UPGRADE}

###### p1_upgrade_{upgrade_name}
- **Type**: bool
- **Description**: Whether {UPGRADE_DISPLAY_NAME} is completed
- **Nullable**: No
- **Default**: false
- **Possible Values**: false, true
- **Completed At**: Loop {COMPLETED_LOOP} (if completed)
- **Category**: {UPGRADE_CATEGORY} (weapons/armor/shields/other)
- **Level**: {UPGRADE_LEVEL} (if applicable)
- **Notes**: {UPGRADE_NOTES}

{END_FOR_EACH_UPGRADE}

---

### Player 2: {PLAYER_2_NAME} ({PLAYER_2_RACE})

{SAME_STRUCTURE_AS_PLAYER_1}

---

## Data Types Reference

### Numeric Types

- **int8**: 8-bit signed integer (-128 to 127)
- **int16**: 16-bit signed integer (-32,768 to 32,767)
- **int32**: 32-bit signed integer (-2.1B to 2.1B)
- **float32**: 32-bit floating point number

### Other Types

- **bool**: Boolean (true/false)
- **string**: Variable-length text string

### Nullable Columns

Nullable columns use NaN (Not a Number) or None to indicate missing data:
- **Units/Buildings**: NaN means the unit/building doesn't exist at this loop
- **Timestamps**: NaN means the event hasn't occurred
- **Economy/Upgrades**: Always have values (use 0 or false for "none")

---

## Usage Examples

### Loading the Data

```python
import pandas as pd

# Load the Parquet file
df = pd.read_parquet('{PARQUET_PATH}')

# View basic information
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"Game duration: {df['game_loop'].max()} loops")
```

### Accessing Specific Game Loops

```python
# Get state at a specific loop
loop_1000 = df[df['game_loop'] == 1000].iloc[0]

# Get state in a time range
early_game = df[(df['game_loop'] >= 0) & (df['game_loop'] <= 5000)]
```

### Working with Units

```python
# Check if a specific unit exists at each loop
marine_exists = df['p1_marine_001_x'].notna()

# Get positions of a unit over time
marine_path = df[['game_loop', 'p1_marine_001_x', 'p1_marine_001_y']]
marine_path = marine_path[marine_path['p1_marine_001_x'].notna()]

# Count units at each loop
marine_counts = df[['game_loop', 'p1_marine_count']]
```

### Analyzing Economy

```python
# Plot mineral count over time
import matplotlib.pyplot as plt
plt.plot(df['game_loop'], df['p1_minerals'])
plt.xlabel('Game Loop')
plt.ylabel('Minerals')
plt.title('Mineral Count Over Time')

# Calculate average resources
avg_minerals = df['p1_minerals'].mean()
avg_vespene = df['p1_vespene'].mean()
```

### Finding Key Events

```python
# Find when a unit was created
marine_created = df[df['p1_marine_001_state'] == 'built']['game_loop'].values[0]

# Find when a building completed
barracks_complete = df['p1_barracks_001_completed_loop'].dropna().values[0]

# Find when an upgrade was researched
stim_completed = df[df['p1_upgrade_stim_pack'] == True]['game_loop'].min()
```

### Computing Derived Metrics

```python
# Calculate supply efficiency (used / cap)
df['p1_supply_efficiency'] = df['p1_supply_used'] / df['p1_supply_cap']

# Calculate resource accumulation rate
df['p1_mineral_rate'] = df['p1_minerals'].diff() / {STEP_MUL}

# Worker saturation
df['p1_worker_per_base'] = df['p1_supply_workers'] / df['p1_nexus_count']
```

---

## Data Quality Notes

### Validation Checks Performed

- ✅ game_loop is unique and monotonically increasing
- ✅ No duplicate game loop values
- ✅ Unit counts match number of non-NaN unit entries
- ✅ Supply used ≤ supply cap
- ✅ Health ≤ health_max
- ✅ Building progress is 0-100
- ✅ Positions are within map bounds

### Known Limitations

- Chat messages are not available (pysc2 limitation)
- Observations occur every {STEP_MUL} loops, not every loop
- Some fast micro events may be missed between observations
- Hallucination units {ARE/ARE_NOT} tracked separately

### Data Completeness

- **Total Loops**: {TOTAL_LOOPS}
- **Observed Loops**: {OBSERVED_LOOPS}
- **Coverage**: {COVERAGE_PERCENT}%
- **Missing Observations**: {MISSING_COUNT}

---

## Changelog

**Version 1.0** - {GENERATION_DATE}
- Initial extraction from replay
- {TOTAL_COLUMNS} columns generated
- {TOTAL_ROWS} rows extracted

---

## Contact & Support

For questions about this data or the extraction pipeline:
- Documentation: See `docs/planning/` directory
- Schema: See `schemas/column_schema.yaml`
- Issues: Contact the data extraction team

---

**Auto-generated by SC2 Replay Ground Truth Extraction Pipeline**
**Generation Time**: {GENERATION_TIMESTAMP}
