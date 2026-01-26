# Messages Column Implementation - Summary

## Overview
This document summarizes the implementation of the Messages column feature and the new directory structure for the StarCraft II replay parsing and extraction system.

## Changes Made

### 1. Schema Manager (`src_new/extraction/schema_manager.py`)
**Changes:**
- Added "Messages" column to the base schema
- Column type: `object` (to support NaN, strings, and lists)
- Column description: "Ally chat messages sent at this game loop (NaN if none, string if one, list of strings if multiple)"

**Why:** The Messages column needs to be part of the base schema so it's included in every extracted replay, regardless of what entities (units/buildings) are present.

### 2. Wide Table Builder (`src_new/extraction/wide_table_builder.py`)
**Changes:**
- Added `_format_messages()` method that formats messages based on count:
  - No messages → NaN
  - One message → string
  - Multiple messages → list of strings
- Updated `build_row()` method to extract messages from state and add to row

**Why:** This extracts messages from the observation state and formats them consistently for storage in the parquet file, aligned with the game loop timeline.

### 3. Extraction Pipeline (`src_new/pipeline/extraction_pipeline.py`)
**Changes:**
- Modified output file path generation in `_extract_and_write()` method
- Created subdirectories:
  - `output_dir/parquet/` for .parquet files
  - `output_dir/json/` for .json files
- Added directory creation logic

**Why:** Organizing output files into dedicated directories makes the codebase cleaner and easier to navigate, especially when processing many replays.

### 4. Parquet Writer (`src_new/extraction/parquet_writer.py`)
**Changes:**
- Added explicit handling for `object` dtype in `_convert_types()` method
- Ensures Messages column (and other object-type columns) maintain their mixed types

**Why:** The Messages column can contain NaN, strings, or lists, which requires the `object` dtype in pandas. This ensures proper type handling when writing to parquet.

### 5. Read Data Script (`quickstart_read_data.py`)
**Changes:**
- Updated to read from `data/quickstart/parquet/` instead of `data/quickstart/`
- Added comprehensive Messages column verification:
  - Checks if Messages column exists
  - Counts non-NaN messages
  - Displays sample messages
  - Handles both string and list types

**Why:** The verification script needs to confirm the Messages column is present and working correctly after processing replays.

## Implementation Details

### Messages Column Behavior

| Game Loop State | Messages Column Value | Type |
|----------------|----------------------|------|
| No messages | `NaN` | float (pandas NaN) |
| One message | `"message text"` | string |
| Multiple messages | `["msg1", "msg2", ...]` | list of strings |

### Example Data Structure

```python
# Row with no messages
{
    'game_loop': 100,
    'timestamp_seconds': 4.46,
    'Messages': np.nan,
    'p1_minerals': 50,
    'p2_minerals': 50,
}

# Row with one message
{
    'game_loop': 500,
    'timestamp_seconds': 22.32,
    'Messages': 'Bot tag: ArgoBot v1.0',
    'p1_minerals': 200,
    'p2_minerals': 175,
}

# Row with multiple messages
{
    'game_loop': 1000,
    'timestamp_seconds': 44.64,
    'Messages': ['Debug: Attack started', 'Debug: Unit count: 25'],
    'p1_minerals': 500,
    'p2_minerals': 450,
}
```

## Directory Structure

### Before
```
data/quickstart/
├── replay_name_game_state.parquet
├── replay_name_messages.parquet
└── replay_name_schema.json
```

### After
```
data/quickstart/
├── parquet/
│   ├── replay_name_game_state.parquet
│   └── replay_name_messages.parquet
└── json/
    └── replay_name_schema.json
```

## Testing & Verification

### Code Verification (Completed)
✓ All code changes verified with `test_messages_simple.py`
✓ Schema includes Messages column
✓ Wide table builder extracts and formats messages
✓ Extraction pipeline uses new directory structure
✓ Parquet writer handles object dtype
✓ Read script updated for new structure

### File Migration (Completed)
✓ Existing files migrated to new directory structure
✓ Migration script: `migrate_to_new_structure.py`

### End-to-End Testing (Requires SC2)
⚠️ Cannot complete without SC2 installation
- Need to run `quickstart.py` to process replays with new code
- Need to verify Messages column contains data from test replay
- Test replay: `replays/4533018_ArgoBot_what_UltraloveAIE_v2.SC2Replay`

## How to Complete Testing

1. **Install StarCraft II** (if not already installed)
   - Download from: https://starcraft2.com/

2. **Process Replays**
   ```bash
   python quickstart.py
   ```

3. **Verify Messages Column**
   ```bash
   python quickstart_read_data.py
   ```

4. **Expected Output**
   - Output files created in new directory structure
   - Messages column present in game_state.parquet
   - Test replay shows at least 1 non-NaN message (bot tags)

## Files Changed

1. `src_new/extraction/schema_manager.py`
2. `src_new/extraction/wide_table_builder.py`
3. `src_new/pipeline/extraction_pipeline.py`
4. `src_new/extraction/parquet_writer.py`
5. `quickstart_read_data.py`

## Files Created

1. `test_messages_simple.py` - Code verification script
2. `migrate_to_new_structure.py` - File migration utility
3. `IMPLEMENTATION_SUMMARY.md` - This document

## Technical Notes

### Why Object Dtype?
The Messages column uses pandas `object` dtype because it needs to hold three different types:
- `float` (NaN for no messages)
- `str` (single message)
- `list` (multiple messages)

### Why Not Separate Messages Table?
Messages are stored in the main game_state table (not the separate messages.parquet) because:
1. Alignment with game loops is critical for ML models
2. Each row represents a complete snapshot of game state at that loop
3. Messages are temporally aligned with other events
4. Easier to query: "What was the game state when this message was sent?"

### Message Extraction
Messages are extracted from the pysc2 observation object:
```python
# In state_extractor.py
if hasattr(obs.observation, 'chat'):
    for msg in obs.observation.chat:
        messages.append({
            'game_loop': obs.observation.game_loop,
            'player_id': msg.player_id,
            'message': msg.message,
        })
```

Only ally chat messages are visible in the observation, which is perfect for capturing bot tags and debugging information sent by the bot.

## Success Criteria

- [x] Messages column added to schema
- [x] Messages extracted from observations
- [x] Messages formatted correctly (NaN/string/list)
- [x] New directory structure implemented
- [x] Existing files migrated
- [x] Read script updated and working
- [ ] End-to-end test with SC2 (pending SC2 installation)
- [ ] Test replay shows messages in output

## Next Steps

1. Install SC2 on the development machine
2. Run `python quickstart.py` to process the test replay
3. Run `python quickstart_read_data.py` to verify Messages column
4. Confirm test replay contains bot tag messages
5. Process additional replays to verify system works at scale

## Contact

For questions about this implementation, refer to:
- Code: See files listed in "Files Changed" section
- Testing: See `test_messages_simple.py` and `quickstart_read_data.py`
- Migration: See `migrate_to_new_structure.py`
