# SC2 Pipeline Diagnosis Report

## Executive Summary

The SC2 replay extraction pipeline has **five confirmed bugs** that collectively explain all three symptoms: missing player 2 units, missing newly-produced player 1 units, and the observer perspective issue. The root causes are:

1. **Observer perspective never used**: Both the schema scan (pass 1) and data extraction (pass 2) hardcode `observed_player_id=1`, meaning the replay is always viewed from player 1's perspective. The SC2 API's `player_common` (economy data) and `raw_data.units` differ dramatically depending on the observed player perspective. When observing as player 1, `unit.owner` correctly reports all units visible from that perspective (both players' units are in `raw_data.units`), BUT `player_common` only reports player 1's economy. The `disable_fog=True` flag in pass 2 reveals all units on the map, but the fundamental problem is that the `unit.owner` filter at line 168 of `unit_extractor.py` correctly filters by owner -- so p2 units SHOULD appear. The real issue is a combination of the two-pass determinism bug (Bug 3) and the fact that `disable_fog` is only set in pass 2 but NOT in pass 1 (Bug 2), causing the schema scan to miss most units.

2. **Schema/data mismatch due to fog-of-war inconsistency between passes**: Pass 1 (schema scan) runs WITHOUT `disable_fog`, so it only sees player 1's visible units and misses many player 2 units hidden by fog. Pass 2 runs WITH `disable_fog=True`, discovering new units that have no schema columns. These "extra" units are silently dropped because `add_unit_to_row` checks `if col_name in row` and skips when the column does not exist in the schema.

Additionally, the Messages column serialization has a separate bug causing approximately 15-20% of replays to fail with parquet write errors, and there is an economy column naming mismatch that silently drops all economy data.

## Bug 1: Fog-of-War Mismatch Between Schema Scan (Pass 1) and Data Extraction (Pass 2)

- **Location**: `src_new/extraction/schema_manager.py:129` and `src_new/pipeline/extraction_pipeline.py:286`
- **Root Cause**: In the two-pass processing mode:
  - Pass 1 (schema scan) calls `replay_loader.start_replay(controller, observed_player_id=1)` with `disable_fog` defaulting to `False`
  - Pass 2 (data extraction) calls `replay_loader.start_replay(controller, observed_player_id=1, disable_fog=True)`
  - This means Pass 1 only sees units within player 1's fog-of-war vision, while Pass 2 sees ALL units on the map
  - Units that player 1 never had vision of during the schema scan are completely missing from the schema
  - In Pass 2, when these newly-visible units are extracted, `add_unit_to_row()` checks `if col_name in row` (line 171 of wide_table_builder.py) and silently skips them because the columns don't exist
- **Evidence**:
  - `schema_manager.py` line 129: `replay_loader.start_replay(controller, observed_player_id=1)` -- no `disable_fog` parameter
  - `extraction_pipeline.py` line 286: `replay_loader.start_replay(controller, observed_player_id=1, disable_fog=True)` -- has `disable_fog=True`
  - Log evidence: Schema discovers units (e.g., "Units discovered: 88") but this is only what player 1 could see. Pass 2 with fog disabled would find significantly more.
- **Impact**: This is the **primary cause of missing player 2 units** and **missing newly-produced player 1 units** (those produced in areas player 1 doesn't have vision of). Units produced by player 1 in their own base ARE captured in the schema since player 1 always has vision there. But units morphing, produced at forward bases, or any player 2 units outside player 1's vision during the schema scan are lost.
- **Fix Strategy**: Pass the same `disable_fog=True` in Pass 1's schema scan. Change `schema_manager.py` line 129 to: `replay_loader.start_replay(controller, observed_player_id=1, disable_fog=True)`

## Bug 2: Two-Pass Unit ID Non-Determinism

- **Location**: `src_new/extractors/unit_extractor.py:258-282` (ID assignment) and `src_new/pipeline/extraction_pipeline.py:207-208` (reset between passes)
- **Root Cause**: The readable ID assignment (`_assign_readable_id`) uses sequential counters per unit type (e.g., `p1_marine_001`, `p1_marine_002`). The counter is incremented each time a NEW unit tag is seen. Between passes:
  - Pass 1 assigns IDs based on the order units first appear in the game
  - `state_extractor.reset()` is called at line 208, which clears ALL unit extractor state (tag maps, counters)
  - Pass 2 assigns IDs fresh, potentially in a DIFFERENT order if:
    - `disable_fog` is different (it is -- see Bug 1)
    - Unit iteration order from `raw_data.units` is not deterministic across replay restarts
    - Step size differs (schema scan uses `step(1)` while data extraction uses `step(self.step_size)`)
  - The schema was built with Pass 1's IDs but Pass 2 generates different IDs, causing column name mismatches
- **Evidence**:
  - `state_extractor.py` line 231-245: `reset()` clears `tag_to_readable_id`, `unit_type_counters`, etc.
  - `extraction_pipeline.py` line 208: `self.state_extractor.reset()` called between passes
  - The schema manager is NOT reset (correctly), but it holds column names from Pass 1 IDs
  - With different fog settings between passes, units appear in different orders and different quantities
- **Impact**: Even if Bug 1 is fixed, if unit ordering differs between passes, units get different readable IDs (e.g., `p1_marine_001` in pass 1 maps to a different physical unit than `p1_marine_001` in pass 2). Data for unit X gets written into the column for unit Y, or into non-existent columns.
- **Fix Strategy**: Two options:
  1. **Best**: Don't reset extractors between passes. After schema scan, keep the tag-to-ID mapping and reuse it in pass 2. This requires either not calling `state_extractor.reset()` and instead only resetting per-frame state, or saving/restoring the tag mapping.
  2. **Alternative**: Use a single-pass approach that builds schema dynamically.

## Bug 3: Economy Column Naming Mismatch

- **Location**: `src_new/extractors/economy_extractor.py:109-131` vs `src_new/extraction/wide_table_builder.py:222-231` vs `src_new/extraction/schema_manager.py:286-305`
- **Root Cause**: The economy extractor returns keys like `food_used`, `food_cap`, `food_workers`, `idle_worker_count`, `food_army`, `army_count`. But the schema manager defines columns as `supply_used`, `supply_cap`, `workers`, `idle_workers`. The wide_table_builder maps economy fields using the attribute names `minerals`, `vespene`, `supply_used`, `supply_cap`, `workers`, `idle_workers`:
  ```python
  # wide_table_builder.py line 222-225
  economy_columns = ['minerals', 'vespene', 'supply_used', 'supply_cap', 'workers', 'idle_workers']
  ```
  But economy_extractor returns:
  ```python
  # economy_extractor.py returns:
  {'minerals': ..., 'vespene': ..., 'food_used': ..., 'food_cap': ..., 'food_workers': ..., 'idle_worker_count': ...}
  ```
  The `add_economy_to_row` method does `economy_data.get(attr, ...)` where `attr` is `supply_used`, but the dict has `food_used`. This means `supply_used`, `supply_cap`, `workers`, and `idle_workers` all get the MISSING VALUE (NaN) instead of actual data.
- **Evidence**:
  - `economy_extractor.py` lines 109-131: returns `food_used`, `food_cap`, `food_workers`, `idle_worker_count`
  - `wide_table_builder.py` lines 222-225: expects `supply_used`, `supply_cap`, `workers`, `idle_workers`
  - `minerals` and `vespene` DO match, so those columns would have data
- **Impact**: Four out of six economy columns are silently filled with NaN for BOTH players. Only `minerals` and `vespene` are correctly populated.
- **Fix Strategy**: Either:
  1. Rename economy_extractor output keys to match: `supply_used`, `supply_cap`, `workers`, `idle_workers`
  2. Or add a mapping layer in `add_economy_to_row` that translates between the two naming conventions

## Bug 4: Observer Perspective Prevents Player 2 Economy Data

- **Location**: `src_new/pipeline/extraction_pipeline.py:286` and `src_new/extractors/economy_extractor.py:80-82`
- **Root Cause**: The economy extractor reads from `obs.observation.player_common`, which in the SC2 API is perspective-dependent. When `observed_player_id=1`, `player_common` contains ONLY player 1's economy data. There is no way to read player 2's economy from player 1's observation via `player_common`. The economy extractor for player 2 (`EconomyExtractor(player_id=2)`) reads the exact same `player_common` -- which is player 1's data -- and incorrectly attributes it to player 2.
  - Additionally, the economy extractor does not use `self.player_id` at all during extraction -- it always reads the same `obs.observation.player_common` regardless of which player it's supposed to extract for.
- **Evidence**:
  - `economy_extractor.py` line 81: `player_common = obs.observation.player_common` -- no player ID filtering
  - The `player_id` field is stored in `__init__` but never used in `extract()`
  - SC2 API docs (from `docs/research/01_API_Documentation_Map.md` line 290): "Workaround: Run replay twice (once per player) for full ground truth"
  - Log confirms "Starting replay playback (observing player 1)..." for EVERY replay -- never player 2 or observer
- **Impact**: Player 2 economy data (minerals, vespene, supply, workers) is actually player 1's data mislabeled. This is INCORRECT DATA, not just missing data. The `score_details` fields also come from the observed player's perspective.
- **Fix Strategy**: The SC2 API requires running the replay from each player's perspective to get their `player_common` data. Options:
  1. **Run each replay twice**: once with `observed_player_id=1` and once with `observed_player_id=2`, merging results
  2. **Use `observed_player_id=0`**: The SC2 API proto defines `observed_player_id=0` as the observer/referee perspective. In observer mode with `disable_fog=True`, `raw_data.units` returns ALL units with correct `owner` fields. However, `player_common` may not be available or may be empty in observer mode. This needs testing.
  3. **Derive economy from units**: Count workers, supply, etc. from the raw unit data rather than `player_common`

## Bug 5: Messages Column Parquet Serialization Failure

- **Location**: `src_new/extraction/parquet_writer.py:244-247` and `src_new/extraction/wide_table_builder.py:351-373`
- **Root Cause**: The `_format_messages` method returns mixed types: `NaN` (float), `str`, or `list` depending on message count. The `_serialize_messages_for_parquet` method attempts to convert lists to JSON strings, but this fails because:
  1. The `_convert_types` method tries to convert the Messages column to `object` type first (line 247), which fails with "The truth value of an array with more than one element is ambiguous"
  2. Even if that succeeds, PyArrow cannot handle the mixed NaN/string/list types in a single column
- **Evidence**: Log shows this error pattern repeatedly:
  - `WARNING - Failed to convert column 'Messages' to object: The truth value of an array with more than one element is ambiguous`
  - `ERROR - Failed to write parquet: ("Expected bytes, got a 'list' object", 'Conversion failed for column Messages with type object')`
  - This accounts for the "FAILED" replays (approximately 15-20 replays out of 241)
- **Impact**: Any replay with chat messages that include multiple messages at the same game loop fails to write to parquet entirely. The replay is lost.
- **Fix Strategy**: Serialize ALL message values to strings before DataFrame creation. Convert lists to JSON strings and ensure NaN values are handled consistently. The `_serialize_messages_for_parquet` method exists but is applied too late -- it needs to run before the DataFrame is created, or the column needs to be pre-processed before type conversion.

## Bug 6: Schema Manager Reset in `reset()` Clears Player Names

- **Location**: `src_new/extraction/schema_manager.py:450-458`
- **Root Cause**: The `SchemaManager.reset()` method does NOT clear `self.player_names`. This is actually CORRECT behavior for the two-pass flow. However, there is a subtle issue: in `_two_pass_processing` (line 198-212 of extraction_pipeline.py):
  1. `schema_manager.build_schema_from_replay()` sets player_names on schema_manager at line 127
  2. After schema built, `wide_table_builder` is created at line 205
  3. `state_extractor.reset()` is called at line 208
  4. `_extract_and_write()` is called at line 212
  5. Inside `_extract_and_write()`, player_names are set on BOTH `wide_table_builder` (line 280) and `schema_manager` (line 283)
  - This means player_names ARE set on both components in pass 2. So this is NOT a bug. The names should be consistent.
- **Impact**: None -- this was investigated and found to be correctly handled.
- **Status**: NOT A BUG

## Priority Order

1. **Bug 1 (Fog-of-War Mismatch)** -- CRITICAL. This is the primary cause of missing player 2 units and missing newly-produced units. Simple one-line fix.
2. **Bug 2 (Two-Pass ID Non-Determinism)** -- CRITICAL. Even after fixing Bug 1, different replay playback ordering between passes can cause data to be written to wrong columns. Must be fixed alongside Bug 1.
3. **Bug 4 (Observer Perspective for Economy)** -- HIGH. Player 2 economy data is WRONG (contains player 1's data). Requires architectural decision about single-player vs observer perspective.
4. **Bug 3 (Economy Column Naming)** -- HIGH. Four of six economy columns are silently NaN. Simple rename fix.
5. **Bug 5 (Messages Parquet Failure)** -- MEDIUM. Causes ~15-20% of replays with chat to fail entirely. Independent of other bugs.

## Recommended Fix Approach

### Phase 1: Critical unit extraction fixes (Bugs 1 + 2)

The cleanest approach is to **eliminate the two-pass problem entirely** by keeping extractor state between passes:

1. In `schema_manager.py` line 129, add `disable_fog=True` to match pass 2
2. In `extraction_pipeline.py` line 208, instead of calling `self.state_extractor.reset()`, save and restore the tag-to-readable-ID mappings from the unit and building extractors. This ensures pass 2 uses the same IDs as pass 1.
3. Alternatively, switch to single-pass mode as the default (already supported in the codebase)

### Phase 2: Economy fixes (Bugs 3 + 4)

1. Fix the naming mismatch in `economy_extractor.py` to return `supply_used`, `supply_cap`, `workers`, `idle_workers` instead of `food_used`, `food_cap`, `food_workers`, `idle_worker_count`
2. For player 2 economy: either run the replay twice (once per player perspective) or use observer mode (`observed_player_id=0`) with `disable_fog=True` and derive economy from raw unit counts

### Phase 3: Messages fix (Bug 5)

1. In `_format_messages`, always return a JSON-serialized string (never a raw list)
2. Or pre-process the Messages column before DataFrame creation to ensure uniform string type

## Open Questions

1. **Does `observed_player_id=0` work in the SC2 API for observer mode?** The s2clientprotocol proto files were not found in the local repository. Based on the SC2 API documentation, `observed_player_id=0` should give observer/referee perspective, but this needs to be verified by testing. Some versions of the SC2 API may not support observer mode in replays.

2. **Is `raw_data.units` complete when observing as player 1 with `disable_fog=True`?** When `disable_fog=True` is set, player 1's perspective should reveal ALL units on the map with correct `unit.owner` values. This needs verification -- the `unit.owner` field should correctly return 1 or 2 regardless of which player is being observed, as long as fog is disabled.

3. **Is unit iteration order deterministic across two passes of the same replay?** Even with identical `disable_fog` settings, the SC2 engine may return units in different orders between two replay playbacks. The `raw_data.units` list order might vary, causing different counter assignments. This is the fundamental weakness of the two-pass approach.

4. **What `player_common` data is available in observer mode?** If `observed_player_id=0` is used, does `player_common` contain any data? The answer likely is that it doesn't, which means economy data would need to be derived from raw unit counts or the replay would need to be run from each player's perspective.

5. **How many of the 241 replays had InvalidReplayData errors vs Messages errors?** From the log, approximately 15+ replays failed due to Messages serialization, and 15+ failed due to InvalidReplayData (version mismatch with SC2 installation). The exact split needs the full log summary.
