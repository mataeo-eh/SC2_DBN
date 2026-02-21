# Two-Pass Schema Audit: Complete Touchpoint Map and Dissolution Plan

**Date:** 2026-02-21
**Scope:** `src_new/` — all Python files and documentation
**Goal:** Identify every place the two-pass/pre-scan schema pattern exists and specify exactly what must change to eliminate it from the observer-mode path.

---

## 1. Complete Touchpoint Map

Every reference to the two-pass schema pattern found across `src_new/`, grouped by file.

| File | Line | Reference | Type | Action Required |
|------|------|-----------|------|-----------------|
| `src_new/pipeline/extraction_pipeline.py` | 11 | `'two_pass': Legacy fallback...` (module docstring) | doc (code file) | Update docstring after removal |
| `src_new/pipeline/extraction_pipeline.py` | 13 | `'single_pass': Dynamic schema mode...` (module docstring) | doc (code file) | Update docstring after removal |
| `src_new/pipeline/extraction_pipeline.py` | 48 | `The legacy 'two_pass' mode is retained as a fallback.` | doc (code file) | Update class docstring |
| `src_new/pipeline/extraction_pipeline.py` | 60 | `processing_mode (str): 'observer', 'two_pass', or 'single_pass'` | doc (code file) | Update `__init__` docstring |
| `src_new/pipeline/extraction_pipeline.py` | 77-78 | `# Pipeline configuration — 'observer' is preferred over legacy 'two_pass'` / `self.processing_mode = self.config.get(...)` | code | Keep `processing_mode` attribute; update comment |
| `src_new/pipeline/extraction_pipeline.py` | 81 | `logger.info(f"ReplayExtractionPipeline initialized (mode: {self.processing_mode})")` | code | Keep as-is |
| `src_new/pipeline/extraction_pipeline.py` | 135 | `logger.info(f"  Processing mode: {self.processing_mode}")` | code | Keep as-is |
| `src_new/pipeline/extraction_pipeline.py` | 154-161 | `if self.processing_mode == 'observer':` / `elif 'two_pass'` / `elif 'single_pass'` dispatch | code | Remove `two_pass` and `single_pass` branches; keep `observer` branch |
| `src_new/pipeline/extraction_pipeline.py` | 186-386 | `_observer_mode_processing()` — contains pre-scan call | code | **PRIMARY TARGET**: Remove pre-scan block (lines 228-243); add `build_base_schema()` call; add dynamic `ensure_unit/building_columns()` calls inside loop |
| `src_new/pipeline/extraction_pipeline.py` | 217 | `schema_manager.build_schema_from_replay()` (docstring of `_observer_mode_processing`) | doc (code file) | Update docstring |
| `src_new/pipeline/extraction_pipeline.py` | 228-236 | `# --- Schema pre-scan ---` block calling `build_schema_from_replay()` | code | **DELETE**: This is the core Form 1 pre-scan in observer mode |
| `src_new/pipeline/extraction_pipeline.py` | 239 | `self.wide_table_builder = WideTableBuilder(self.schema_manager)` (after pre-scan) | code | Move earlier; create WideTableBuilder after `build_base_schema()` instead |
| `src_new/pipeline/extraction_pipeline.py` | 241-243 | `self.state_extractor.reset_frame_state()` (pre-scan-to-extraction reset) | code | **DELETE**: No longer needed when pre-scan is removed |
| `src_new/pipeline/extraction_pipeline.py` | 388-437 | `_two_pass_processing()` entire method | code | **DELETE** entire method (legacy fallback) |
| `src_new/pipeline/extraction_pipeline.py` | 419-425 | `build_schema_from_replay()` call inside `_two_pass_processing()` | code | Deleted with enclosing method |
| `src_new/pipeline/extraction_pipeline.py` | 433 | `self.state_extractor.reset_frame_state()` inside `_two_pass_processing()` | code | Deleted with enclosing method |
| `src_new/pipeline/extraction_pipeline.py` | 437 | `return self._extract_and_write(...)` inside `_two_pass_processing()` | code | Deleted with enclosing method |
| `src_new/pipeline/extraction_pipeline.py` | 439-467 | `_single_pass_processing()` entire method | code | **DELETE** entire method (superseded by observer mode) |
| `src_new/pipeline/extraction_pipeline.py` | 469-629 | `_extract_and_write()` entire method | code | **DELETE** entire method (contains Pass A + Pass B logic) |
| `src_new/pipeline/extraction_pipeline.py` | 516-522 | Pass A block header comment | code | Deleted with enclosing method |
| `src_new/pipeline/extraction_pipeline.py` | 552-553 | `if self.processing_mode == 'single_pass': self.schema_manager._discover_entities_from_state(state)` | code | Deleted with enclosing method |
| `src_new/pipeline/extraction_pipeline.py` | 575-581 | Pass B comment + `self._patch_p2_economy(...)` call | code | Deleted with enclosing method |
| `src_new/pipeline/extraction_pipeline.py` | 631-726 | `_patch_p2_economy()` entire method | code | **DELETE** entire method (Pass B is eliminated in observer mode) |
| `src_new/pipeline/extraction_pipeline.py` | 747-749 | `if 'processing_mode' in config: self.processing_mode = ...` in `set_config()` | code | Keep for future extensibility (observer mode is still a mode) |
| `src_new/pipeline/extraction_pipeline.py` | 829 | `'processing_mode': 'observer',  # preferred; fallback: 'two_pass'` | code | Remove fallback comment |
| `src_new/extraction/schema_manager.py` | 165-241 | `build_schema_from_replay()` entire method | code | **DELETE** entire method; replace with `build_base_schema()` |
| `src_new/extraction/schema_manager.py` | 244-284 | `_build_columns_from_extractors()` entire method | code | **DELETE** entire method |
| `src_new/extraction/schema_manager.py` | 123-124 | `self._seen_units: Set[str]` and `self._seen_buildings: Set[str]` | code | Keep (still needed by `ensure_unit_columns()` / `ensure_building_columns()` to avoid duplicate column creation) |
| `src_new/extraction/state_extractor.py` | 356-372 | `reset_frame_state()` method | code | **DELETE** (used exclusively to bridge pre-scan and extraction pass) |
| `src_new/extractors/unit_extractor.py` | 661-669 | `reset_frame_state()` method | code | **DELETE** (called only by `StateExtractor.reset_frame_state()`) |
| `src_new/extractors/building_extractor.py` | 596-605 | `reset_frame_state()` method | code | **DELETE** (called only by `StateExtractor.reset_frame_state()`) |
| `src_new/pipeline/parallel_processor.py` | 439 | `'processing_mode': 'two_pass'` in `process_directory_quick()` default config | code | Change to `'observer'` |
| `src_new/pipeline/QUICKSTART.py` | 128 | `'processing_mode': 'single_pass'` in example 3 | doc (Python script) | Change to `'observer'` |
| `src_new/pipeline/QUICKSTART.py` | 166 | `config={'processing_mode': 'two_pass'}` in example 4 | doc (Python script) | Change to `'observer'` |
| `src_new/pipeline/ARCHITECTURE.md` | 22-24 | `_two_pass_processing()` and `_single_pass_processing()` in component diagram | doc | Update diagram to show `_observer_mode_processing()` only |
| `src_new/pipeline/ARCHITECTURE.md` | 96-192 | "Two-Pass Processing Mode" and "Single-Pass Processing Mode" flow diagrams | doc | Replace with "Observer Mode" diagram; remove legacy diagrams |
| `src_new/pipeline/ARCHITECTURE.md` | 253 | `Input: Extracted states (Pass 1) or pre-built schema` | doc | Update to reflect dynamic column building |
| `src_new/pipeline/ARCHITECTURE.md` | 289-290 | `processing_mode: two_pass / single_pass` | doc | Update to `observer` |
| `src_new/pipeline/ARCHITECTURE.md` | 336-339 | "Two-Pass Mode" memory section | doc | Update to "Observer Mode" |
| `src_new/pipeline/USAGE_EXAMPLES.md` | 70 | `'processing_mode': 'two_pass'` in example config | doc | Change to `'observer'` |
| `src_new/pipeline/USAGE_EXAMPLES.md` | 86-105 | "Two-Pass vs Single-Pass" section | doc | Replace with "Observer Mode" description |
| `src_new/pipeline/USAGE_EXAMPLES.md` | 117 | `config={'processing_mode': 'two_pass'}` | doc | Change to `'observer'` |
| `src_new/pipeline/USAGE_EXAMPLES.md` | 337-352 | Single-pass memory config example | doc | Update or remove |
| `src_new/pipeline/PHASE3_IMPLEMENTATION_SUMMARY.md` | 25-27 | Lists `_two_pass_processing()`, `_single_pass_processing()`, `_extract_and_write()` as key methods | doc | Update method list |
| `src_new/pipeline/PHASE3_IMPLEMENTATION_SUMMARY.md` | 36 | `'processing_mode': 'two_pass'` | doc | Update |
| `src_new/pipeline/PHASE3_IMPLEMENTATION_SUMMARY.md` | 125-149 | "Two-Pass Mode" and "Single-Pass Mode" workflow descriptions | doc | Update to Observer Mode |
| `src_new/utils/example_validation_workflow.py` | 228 | `'processing_mode': 'two_pass'` in simulated batch results | doc (Python script) | Change to `'observer'` |
| `src_new/utils/USAGE_EXAMPLES.md` | 190 | `'processing_mode': 'two_pass'` | doc | Change to `'observer'` |

**Note on `_discover_entities_from_state()`:** This method name appears in `ARCHITECTURE.md` (lines 120, 178) and is called in `extraction_pipeline.py` line 553, but it does **not exist** in `schema_manager.py`. It is a dead reference from an earlier design iteration. The existing code in `single_pass` mode calls this non-existent method and would raise an `AttributeError` at runtime. This confirms `single_pass` mode is effectively broken already.

---

## 2. Observer Mode Flow Analysis

Step-by-step analysis of the current `_observer_mode_processing()` method.

| Current Step | Code Location | What It Does | Depends on Pre-scan? | Action |
|---|---|---|---|---|
| 1. Log start | line 226 | Logs "Starting observer mode processing" | No | Keep unchanged |
| 2. Schema pre-scan | lines 228-236 | Calls `build_schema_from_replay()` — runs a full replay pass from P1 perspective to discover all unit/building IDs | YES — this IS the pre-scan | **DELETE**: Replaced by `build_base_schema()` call after metadata is available |
| 3. Create WideTableBuilder | line 239 | `self.wide_table_builder = WideTableBuilder(self.schema_manager)` | Yes (schema must exist) | **MOVE**: Create WideTableBuilder after `build_base_schema()` is called, before the loop |
| 4. `reset_frame_state()` | line 243 | Resets per-frame counters while preserving tag-to-ID maps from the pre-scan, so the extraction pass reuses the same readable IDs | YES — exists only to bridge pre-scan and extraction pass | **DELETE**: Not needed when there is no pre-scan; a fresh extractor handles IDs from scratch |
| 5. Load replay | line 247 | `self.replay_loader.load_replay(replay_path)` | No | Keep unchanged (but now this is the ONLY load, not the second load) |
| 6. Initialize storage | lines 250-251 | `rows = []`, `all_messages = []` | No | Keep unchanged |
| 7. Start SC2 instance | line 253 | Opens SC2 controller context | No | Keep unchanged |
| 8. Get replay metadata | line 255 | `metadata = self.replay_loader.get_replay_info(controller)` | No | Keep unchanged |
| 9. Extract player names | lines 258-264 | Builds `player_names` dict and sets it on `wide_table_builder` and `schema_manager` | No (metadata comes from replay, not the pre-scan) | **This is where `build_base_schema()` should be called** — player names are now available |
| 10. Start replay in observer mode | line 268 | `self.replay_loader.start_replay(controller, observer_mode=True)` | No | Keep unchanged |
| 11. Process each game loop | lines 282-332 | Steps replay, switches perspectives, extracts state | No | Keep loop structure; add `ensure_unit_columns()` and `ensure_building_columns()` calls before `build_row()` |
| 12. Call `build_row()` | line 314 | `self.wide_table_builder.build_row(state)` | YES in current code (schema must be complete) | **After refactor**: No longer requires pre-complete schema. Dynamic columns added on-demand via `ensure_*_columns()` before this call |
| 13. Write output files | lines 339-375 | Writes parquet and JSON | No | Keep unchanged |

### Key finding on `reset_frame_state()`

The purpose of `reset_frame_state()` in the current code is explicitly documented: it preserves tag-to-readable-ID mappings built during the pre-scan so that the extraction pass generates identical column names. If the pre-scan is eliminated, the extractor starts fresh with no prior state, and readable IDs are assigned in document order during the extraction pass. This is correct behavior — there is no second pass to sync with. **`reset_frame_state()` is only needed when there is a pre-scan, and it can be deleted along with the pre-scan.**

### Key finding on player names and pre-scan

Player names are extracted from `replay_loader.get_replay_info(controller)` at line 255, inside the main SC2 context. The pre-scan in `build_schema_from_replay()` also calls `get_replay_info()` internally (schema_manager.py line 195) to get player names for column naming. In the new design, player names are available at line 255 without any pre-scan, because `get_replay_info()` reads them directly from the replay file header — not from frame-by-frame observation.

---

## 3. Schema Building Analysis

### Column Classification

| Column Group | Static or Dynamic | Known Before Extraction? | Source |
|---|---|---|---|
| `game_loop` | Static | Yes | Always present |
| `timestamp_seconds` | Static | Yes | Always present |
| `Messages` | Static | Yes | Always present |
| `p1_minerals`, `p1_vespene`, `p1_supply_used`, `p1_supply_cap`, `p1_workers`, `p1_idle_workers` | Static | Yes | Fixed economy schema |
| `p2_minerals`, `p2_vespene`, `p2_supply_used`, `p2_supply_cap`, `p2_workers`, `p2_idle_workers` | Static | Yes | Fixed economy schema |
| `p1_upgrade_attack_level`, `p1_upgrade_armor_level`, `p1_upgrade_shield_level` | Static | Yes | Fixed upgrade schema |
| `p2_upgrade_attack_level`, `p2_upgrade_armor_level`, `p2_upgrade_shield_level` | Static | Yes | Fixed upgrade schema |
| Unit columns (`p{N}_{bot_name}_{unit_type}_{NNN}_{attr}`) | Dynamic | No — depend on which units appear in THIS specific replay | Added when first unit of that readable_id is seen with `build_progress >= 1.0` |
| Building columns (`p{N}_{bot_name}_{building_type}_{NNN}_{attr}`) | Dynamic | No — depend on which buildings appear in THIS specific replay | Added when first building of that readable_id is first seen |

### Player Name Availability

Player names are required to form column names for units and buildings. The column format is:
```
p{N}_{bot_sanitized_name}_{unit_type}_{sequence_num}_{attr_suffix}
```
For example: `p1_really_marine_001_health`

Player names are read from `replay_loader.get_replay_info(controller)` which parses the replay file's `ResponseReplayInfo` protobuf. This call is made inside the SC2 context manager (after `start_sc2_instance()`), not during pre-scan. This means player names are always available before the extraction loop begins, without any pre-scan.

**Critical implication:** The call to `set_player_names()` on both `schema_manager` and `wide_table_builder` at lines 258-264 of `_observer_mode_processing()` already happens in the right place. The only issue is that currently `build_schema_from_replay()` is called BEFORE `get_replay_info()`, so `build_schema_from_replay()` does its own internal call to `get_replay_info()`. This redundant call will be eliminated with the new design.

### `_seen_units` and `_seen_buildings` Usage

These sets are declared in `SchemaManager.__init__()` (lines 123-124) and used in:
- `_build_columns_from_extractors()` (lines 266-278): Checked to prevent duplicate column creation when iterating the extractor's discovered IDs
- `reset()` (lines 535-536): Cleared during a full reset

In the new design, `_build_columns_from_extractors()` is deleted. However, `_seen_units` and `_seen_buildings` are still needed by the new `ensure_unit_columns()` and `ensure_building_columns()` methods to check whether columns for a given readable_id already exist before calling `add_unit_columns()` or `add_building_columns()`. The sets must be kept and updated inside the new `ensure_*` methods.

---

## 4. WideTableBuilder and ParquetWriter Dependency Analysis

### WideTableBuilder: Does `build_row()` require a complete schema?

**Yes, in the current implementation.** At line 83 of `wide_table_builder.py`:
```python
for col in self.schema.get_column_list():
    row[col] = self.schema.get_missing_value(col)
```
This initializes the row dict with ALL schema columns set to NaN/missing values. If a unit column is not yet in the schema when `build_row()` is called, that column will simply not be initialized in the row.

However, the actual data-writing logic (lines 94-197) does NOT require the schema to be complete. It writes data by constructing column names from the entity's readable_id and checking `if col_name in row`. If the column is not in the row dict at all, no data is written and no error is raised.

**Implication for dynamic columns:** If `ensure_unit_columns()` is called before `build_row()` for each entity, then by the time `build_row()` runs, the schema is correct for all currently-known entities. Rows built before a particular entity was first encountered will have NaN for that entity's columns (which is correct — the entity didn't exist yet).

### Behavior with ragged rows (pandas DataFrames from dicts)

When `pd.DataFrame(rows)` is called in `ParquetWriter.write_game_state()` (line 79), pandas constructs a DataFrame from a list of dicts where different dicts may have different keys. **Pandas handles this correctly by filling missing keys with NaN.** This is a documented and standard behavior: `pd.DataFrame([{'a': 1}, {'a': 2, 'b': 3}])` produces a 2x2 DataFrame with `NaN` for row 0, column `b`.

This is critical: it means that rows built BEFORE a new entity column was added to the schema will have NaN for that column in the final parquet output, which is the semantically correct result.

### Does `ParquetWriter.write_game_state()` require a pre-complete schema?

**Partially.** The schema is used for two things:
1. **Column ordering** (line 82-83): `df.reindex(columns=schema_columns)` reorders columns to match the schema. Any columns in the DataFrame that are NOT in the schema are dropped; any schema columns not in the DataFrame get NaN rows. In the dynamic approach, the schema is complete by the time `write_game_state()` is called (all entities have been encountered), so this works correctly.
2. **Type conversion** (line 86): `self._convert_types(df, schema)` iterates df columns and applies dtype conversions. This also works correctly post-extraction since the schema is complete.

**Conclusion:** `write_game_state()` does NOT require the schema to be pre-built before extraction. It only needs the schema to be complete at write time, after all rows have been collected.

### How `build_row()` handles rows built before a column existed

When a new entity column is added to the schema mid-extraction (via `ensure_unit_columns()`), the schema's `columns` list grows. Future calls to `build_row()` will include that column in the row-initialization loop (line 83). Earlier rows that were already built will NOT have that key at all.

When `pd.DataFrame(rows)` is called, pandas:
- Creates a column for every key that appears in ANY row dict
- Fills NaN for rows that do not have that key

This produces exactly the right result: early rows (before the entity existed) have NaN for that entity's columns, and later rows have real data or lifecycle strings. **No special handling is needed.**

---

## 5. Removal Safety Analysis

### `build_schema_from_replay()` in schema_manager.py

| Attribute | Detail |
|---|---|
| Direct callers | `_observer_mode_processing()` (line 232), `_two_pass_processing()` (line 421) |
| Instance state modified | Sets `self.player_names`, `self._seen_units`, `self._seen_buildings`, `self.columns`, `self.dtypes`, `self.column_docs` — all via `set_player_names()` and `_build_columns_from_extractors()` |
| If deleted, what breaks? | The two callers above both call `build_schema_from_replay()` and then immediately use the schema. Both callers are being restructured to use `build_base_schema()` instead. No other callers exist. |
| Safe to remove? | YES — after callers are updated to `build_base_schema()` |
| Notes | The method opens its own SC2 instance via `replay_loader`. Removing it eliminates the extra SC2 launch overhead. |

### `_build_columns_from_extractors()` in schema_manager.py

| Attribute | Detail |
|---|---|
| Direct callers | `build_schema_from_replay()` (line 238) only |
| Instance state modified | Populates `self._seen_units`, `self._seen_buildings`, `self.columns`, `self.dtypes`, `self.column_docs` — all entity columns plus economy and upgrade columns |
| If deleted, what breaks? | Only `build_schema_from_replay()` calls this. If `build_schema_from_replay()` is deleted, `_build_columns_from_extractors()` has no callers left. |
| Safe to remove? | YES — after `build_schema_from_replay()` is deleted |
| Notes | Economy and upgrade column creation currently happens inside this method (`_add_economy_columns()`, `_add_upgrade_columns()`). In the new design, `build_base_schema()` must call these directly. |

### `_two_pass_processing()` in extraction_pipeline.py

| Attribute | Detail |
|---|---|
| Direct callers | `process_replay()` (line 157), when `processing_mode == 'two_pass'` |
| Instance state modified | Sets `self.wide_table_builder`; leaves `state_extractor` in a reset-frame-state condition |
| If deleted, what breaks? | The `elif self.processing_mode == 'two_pass'` branch in `process_replay()` would become a dead elif that routes to the `else: raise ValueError` branch. |
| Safe to remove? | YES — after removing the `elif 'two_pass'` branch in `process_replay()` |
| Notes | Must also remove the `elif 'two_pass'` dispatch in `process_replay()` to avoid an unhandled mode error. |

### `_single_pass_processing()` in extraction_pipeline.py

| Attribute | Detail |
|---|---|
| Direct callers | `process_replay()` (line 159), when `processing_mode == 'single_pass'` |
| Instance state modified | Sets `self.wide_table_builder` with empty schema |
| If deleted, what breaks? | The `elif 'single_pass'` branch in `process_replay()`; also `_extract_and_write()` contains a live reference to `self.processing_mode == 'single_pass'` (line 552), which would become dead code once `_single_pass_processing()` is deleted. |
| Safe to remove? | YES — after removing `elif 'single_pass'` branch AND deleting `_extract_and_write()` |
| Notes | The call to `_discover_entities_from_state()` inside `_extract_and_write()` (line 553) references a method that does not exist in `schema_manager.py`. This is already broken. |

### `_extract_and_write()` in extraction_pipeline.py

| Attribute | Detail |
|---|---|
| Direct callers | `_two_pass_processing()` (line 437), `_single_pass_processing()` (line 467) |
| Instance state modified | Does not set instance state directly; reads `self.processing_mode`, `self.step_size`, `self.wide_table_builder`, `self.schema_manager` |
| If deleted, what breaks? | Both callers above, which are also being deleted. No other callers exist. |
| Safe to remove? | YES — after `_two_pass_processing()` and `_single_pass_processing()` are deleted |
| Notes | `_extract_and_write()` is the container for Pass A and Pass B logic. Deleting it removes the only place Pass B (`_patch_p2_economy`) is called. |

### `_patch_p2_economy()` in extraction_pipeline.py

| Attribute | Detail |
|---|---|
| Direct callers | `_extract_and_write()` (line 581) only |
| Instance state modified | None — modifies the `rows` list in-place, which is a local variable in `_extract_and_write()` |
| If deleted, what breaks? | Only `_extract_and_write()` calls it, and that method is also being deleted. |
| Safe to remove? | YES — after `_extract_and_write()` is deleted |
| Notes | This method was the primary motivation for the two-pass approach. Observer mode eliminates the need for P2 economy patching entirely. |

### `reset_frame_state()` in state_extractor.py, unit_extractor.py, building_extractor.py

| Attribute | Detail |
|---|---|
| Direct callers | `StateExtractor.reset_frame_state()`: called at `extraction_pipeline.py` lines 243 (observer mode) and 433 (two-pass mode). `UnitExtractor.reset_frame_state()`: called only by `StateExtractor.reset_frame_state()`. `BuildingExtractor.reset_frame_state()`: same. |
| Instance state modified | Clears `previous_tags`, `previous_build_progress`, `dead_tags`, `was_under_construction` — preserving `tag_to_readable_id` and counter dicts |
| If deleted, what breaks? | Two callers in extraction_pipeline.py, both of which are in code being deleted or modified. |
| Safe to remove? | YES — after both callers in `extraction_pipeline.py` are removed |
| Notes | These methods exist ONLY to bridge the pre-scan and extraction pass by preserving readable ID assignments. In the no-pre-scan design, extractors start fresh and there is nothing to preserve. |

---

## 6. New Design Specification

### New Method: `SchemaManager.build_base_schema(player_names: Dict[int, str])`

**Purpose:** Replace `build_schema_from_replay()`. Builds only the static columns (game metadata, economy, upgrades) using player names that are already available from replay metadata. Does NOT iterate the replay.

**Signature:**
```python
def build_base_schema(self, player_names: Dict[int, str]) -> None:
```

**What it calls internally (in order):**
1. `self.set_player_names(player_names)` — sanitizes and stores player names
2. `self._add_economy_columns()` — adds `p1_minerals`, `p1_vespene`, etc.
3. `self._add_upgrade_columns()` — adds `p1_upgrade_attack_level`, etc.

**Note:** `_add_base_columns()` is already called in `__init__()` and does NOT need to be called here. The static base columns (`game_loop`, `timestamp_seconds`, `Messages`) are present from object creation.

**When it is called in `_observer_mode_processing()`:** After `get_replay_info()` returns metadata and player names are extracted (currently lines 258-264). Specifically, it replaces the current pre-scan block AND happens before `WideTableBuilder` is instantiated.

### New Method: `SchemaManager.ensure_unit_columns(player: str, readable_id: str, extra_attrs: Set[str]) -> bool`

**Purpose:** Check whether columns for this unit's readable_id already exist; if not, call `add_unit_columns()`. Prevents duplicate column creation when the same unit appears in multiple frames.

**Signature:**
```python
def ensure_unit_columns(self, player: str, readable_id: str, extra_attrs: Set[str]) -> bool:
```

**Logic:**
```python
def ensure_unit_columns(self, player, readable_id, extra_attrs=None):
    if extra_attrs is None:
        extra_attrs = set()
    if readable_id not in self._seen_units:
        self._seen_units.add(readable_id)
        self.add_unit_columns(player, readable_id, extra_attrs)
        return True  # New columns were added
    return False  # Already existed
```

**Where called in `_observer_mode_processing()`:** Inside the game loop, for every unit in `state['p1_units']` and `state['p2_units']` that has `_lifecycle == 'completed'` (the first frame a unit completes), BEFORE `self.wide_table_builder.build_row(state)`. This is the trigger point for column creation.

**Important:** Units should only get columns when they reach `_lifecycle == 'completed'`, matching the current pre-scan rule that only columns for completed units are created.

### New Method: `SchemaManager.ensure_building_columns(player: str, readable_id: str, extra_attrs: Set[str]) -> bool`

**Purpose:** Same pattern for buildings. Buildings always get columns on first encounter (including cancelled ones), matching the existing rule.

**Signature:**
```python
def ensure_building_columns(self, player, readable_id, extra_attrs=None):
    if extra_attrs is None:
        extra_attrs = set()
    if readable_id not in self._seen_buildings:
        self._seen_buildings.add(readable_id)
        self.add_building_columns(player, readable_id, extra_attrs)
        return True
    return False
```

**Where called in `_observer_mode_processing()`:** Inside the game loop, for every building in `state['p1_buildings']` and `state['p2_buildings']` on its first appearance (when it has any lifecycle status), BEFORE `self.wide_table_builder.build_row(state)`.

### New `_observer_mode_processing()` — Complete Pseudocode

```python
def _observer_mode_processing(self, replay_path, output_dir):
    logger.info("Starting observer mode processing")

    # --- Load replay and get metadata first ---
    self.replay_loader.load_replay(replay_path)

    rows = []
    all_messages = []

    with self.replay_loader.start_sc2_instance() as controller:
        # Get replay metadata (player names, duration, etc.)
        metadata = self.replay_loader.get_replay_info(controller)

        # Extract player names — available from replay header, no pre-scan needed
        player_names = {
            p['player_id']: p.get('player_name', '')
            for p in metadata.get('players', [])
        }

        # Build static schema columns (game_loop, economy, upgrades) from metadata.
        # Entity columns (units, buildings) are added dynamically below.
        self.schema_manager.build_base_schema(player_names)

        # Create WideTableBuilder now that schema has static columns.
        # Entity columns will be added to schema_manager.columns dynamically;
        # WideTableBuilder reads schema.get_column_list() on each build_row() call,
        # so it automatically includes any columns added since its creation.
        self.wide_table_builder = WideTableBuilder(self.schema_manager)
        self.wide_table_builder.set_player_names(player_names)

        # Start replay in observer mode (no fixed player perspective)
        self.replay_loader.start_replay(controller, observer_mode=True)

        game_loop = 0
        max_loops = metadata['game_duration_loops']
        progress_interval = max(1, max_loops // 20)

        logger.info(
            f"Observer mode: Processing {max_loops} game loops "
            f"(step size: {self.step_size})..."
        )

        while game_loop < max_loops:
            try:
                # Step forward one unit
                controller.step(self.step_size)

                # Get P1-perspective observation
                self.replay_loader.switch_player_perspective(controller, player_id=1)
                obs_p1 = controller.observe()

                if obs_p1.player_result:
                    logger.info(f"Replay ended at loop {game_loop}")
                    break

                game_loop = obs_p1.observation.game_loop

                # Get P2-perspective observation (for correct P2 economy/upgrades)
                self.replay_loader.switch_player_perspective(controller, player_id=2)
                obs_p2 = controller.observe()

                # Extract complete state: P1 obs for units/buildings/P1 economy,
                # P2 obs for P2 economy/upgrades
                state = self.state_extractor.extract_observation_observer_mode(
                    obs_p1, obs_p2, game_loop
                )

                # --- Dynamic column creation ---
                # For each unit that just completed this frame, add its columns
                # to the schema before building the row. Units that appear but
                # have not yet completed (lifecycle == 'building', 'unit_started')
                # do NOT get columns — only completed units do.
                for player_num in [1, 2]:
                    player = f'p{player_num}'
                    units = state.get(f'{player}_units', {})
                    for readable_id, unit_data in units.items():
                        if unit_data.get('_lifecycle') == 'completed':
                            # Unit just completed — create its columns now
                            extra_attrs = (
                                self.state_extractor
                                    .unit_extractors[player_num]
                                    .get_unit_attributes_for_id(readable_id)
                            )
                            self.schema_manager.ensure_unit_columns(
                                player, readable_id, extra_attrs
                            )

                # For each building, add its columns on first appearance
                # (buildings always get columns, even cancelled ones)
                for player_num in [1, 2]:
                    player = f'p{player_num}'
                    buildings = state.get(f'{player}_buildings', {})
                    for readable_id, building_data in buildings.items():
                        extra_attrs = (
                            self.state_extractor
                                .building_extractors[player_num]
                                .get_building_attributes_for_id(readable_id)
                        )
                        self.schema_manager.ensure_building_columns(
                            player, readable_id, extra_attrs
                        )

                # Build wide-format row — schema is complete for all
                # entities seen SO FAR; new entity columns will be added
                # in future iterations as new entities are first seen.
                row = self.wide_table_builder.build_row(state)
                rows.append(row)

                # Collect messages
                messages = state.get('messages', [])
                all_messages.extend(messages)

                if game_loop % progress_interval == 0:
                    progress = (game_loop / max_loops) * 100
                    logger.info(
                        f"  Observer mode progress: {progress:.1f}% "
                        f"(loop {game_loop}/{max_loops})"
                    )

            except Exception as e:
                logger.warning(f"Error at game loop {game_loop} (observer mode): {e}")
                continue

        logger.info(
            f"Observer mode complete. Extracted {len(rows)} rows, "
            f"{len(all_messages)} messages"
        )

    # --- Write output files ---
    replay_name = replay_path.stem
    parquet_dir = output_dir / 'parquet'
    json_dir = output_dir / 'json'
    parquet_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    output_files = {
        'game_state': parquet_dir / f"{replay_name}_game_state.parquet",
        'messages': parquet_dir / f"{replay_name}_messages.parquet",
        'schema': json_dir / f"{replay_name}_schema.json",
    }

    logger.info(f"Writing game state to {output_files['game_state']}")
    self.parquet_writer.write_game_state(rows, output_files['game_state'], self.schema_manager)

    if all_messages:
        logger.info(f"Writing messages to {output_files['messages']}")
        self.parquet_writer.write_messages(all_messages, output_files['messages'])
    else:
        logger.info("No messages to write")

    logger.info(f"Writing schema to {output_files['schema']}")
    self.schema_manager.save_schema(output_files['schema'])

    return {
        'output_files': output_files,
        'metadata': metadata,
        'stats': {
            'total_loops': max_loops,
            'rows_written': len(rows),
            'messages_written': len(all_messages),
        },
    }
```

### When is `wide_table_builder` created?

In the new design, `self.wide_table_builder` is created INSIDE `_observer_mode_processing()`, AFTER `build_base_schema()` is called but BEFORE the game loop starts. Specifically, the creation order is:
1. `get_replay_info()` → player names available
2. `build_base_schema(player_names)` → static schema columns exist
3. `WideTableBuilder(self.schema_manager)` → builder initialized with current schema reference
4. `wide_table_builder.set_player_names(player_names)` → player names set on builder
5. Entity columns added dynamically during the loop

The `self.wide_table_builder = None` initialization in `__init__()` (line 72) remains correct.

### Is `reset_frame_state()` still needed?

**No.** With the pre-scan eliminated:
- There is no "first pass" whose state needs to be preserved into a "second pass"
- The `StateExtractor` starts with clean state (from the `self.state_extractor.reset()` call in `process_replay()` at line 151)
- Unit and building extractors build their `tag_to_readable_id` maps fresh during the single extraction pass
- Column names and readable IDs are generated consistently because extraction proceeds in the same forward-time order as always

`reset_frame_state()` can be deleted from `StateExtractor`, `UnitExtractor`, and `BuildingExtractor`.

---

## 7. Risk Assessment

| File | Risk Level | Reason | Mitigation |
|---|---|---|---|
| `src_new/pipeline/extraction_pipeline.py` | HIGH | Core orchestration file; removing four methods and restructuring the main observer mode loop is a large surgery. Mistakes here directly break all replay processing. | Test `_observer_mode_processing()` end-to-end on at least one known replay immediately after changes. Verify row count matches prior runs. |
| `src_new/extraction/schema_manager.py` | HIGH | Adding three new methods (`build_base_schema`, `ensure_unit_columns`, `ensure_building_columns`) and deleting two. The `_seen_units` / `_seen_buildings` sets must be correctly transitioned from pre-scan guards to dynamic guards. | Verify that `ensure_unit_columns()` is idempotent (calling it twice for the same `readable_id` does nothing), by checking the guard condition. |
| `src_new/extraction/state_extractor.py` | MEDIUM | Deleting `reset_frame_state()`. If any other caller (not found in the audit) references this method, it will raise `AttributeError` at runtime. | Run `grep -r "reset_frame_state" src_new/` before deleting to confirm no callers remain. |
| `src_new/extractors/unit_extractor.py` | MEDIUM | Deleting `reset_frame_state()`. Same risk as above. | Same grep verification. |
| `src_new/extractors/building_extractor.py` | MEDIUM | Deleting `reset_frame_state()`. Same risk as above. | Same grep verification. |
| `src_new/extraction/wide_table_builder.py` | LOW | No code changes required. The dynamic column approach relies on `build_row()` checking `col in row` rather than assuming complete column existence. This is the existing behavior — verified in the code audit. | No changes needed; no risk. |
| `src_new/extraction/parquet_writer.py` | LOW | No code changes required. `write_game_state()` uses `df.reindex(columns=schema_columns)` which handles the case where the final schema is complete even though individual rows may have had fewer columns when first built. | No changes needed; no risk. |
| `src_new/pipeline/parallel_processor.py` | LOW | Only the default config in `process_directory_quick()` changes (line 439: `'two_pass'` → `'observer'`). The parallel execution machinery is unchanged. | Verify config change; no other impact. |
| Documentation files (`ARCHITECTURE.md`, `USAGE_EXAMPLES.md`, `PHASE3_IMPLEMENTATION_SUMMARY.md`) | LOW | Stale docs describe deleted modes. Incorrect docs do not break runtime behavior but will confuse future maintainers. | Update after code changes are confirmed working. |
| `src_new/pipeline/QUICKSTART.py`, `src_new/utils/example_validation_workflow.py` | LOW | Example scripts reference `'two_pass'` and `'single_pass'` modes. These will produce a `ValueError` if actually executed after those modes are removed. | Update example configs to `'observer'`. |

### Hidden Dependencies

1. **`_discover_entities_from_state()` is a dead call.** Line 553 of `extraction_pipeline.py` calls `self.schema_manager._discover_entities_from_state(state)` inside `_single_pass_processing()` → `_extract_and_write()`. This method does not exist in `schema_manager.py`. The `single_pass` mode would raise `AttributeError` at runtime. This confirms `single_pass` mode is already broken and must be removed, not preserved.

2. **`get_replay_info()` is called twice in observer mode currently.** Once inside `build_schema_from_replay()` (for player names during pre-scan) and once inside the extraction pass. In the new design, it is called exactly once.

3. **`WideTableBuilder.build_row()` reads `schema.get_column_list()` on every call.** This means the schema's `columns` list is re-read fresh each frame. Adding columns to `schema_manager.columns` during the loop automatically makes them available to the next `build_row()` call without any additional wiring.

4. **`unit_extractor.unit_attributes` dict is populated on the first frame a unit is seen.** The `get_unit_attributes_for_id(readable_id)` method reads from this dict. In the new design, this is called at the moment the unit's lifecycle transitions to `'completed'`. This is the correct time because the conditional attributes (shields, energy) are determined from the unit proto on first encounter.

---

## 8. Implementation Checklist

Execute changes in this order to avoid breaking intermediate states.

### Step 1 — schema_manager.py

1. Add new method `build_base_schema(self, player_names: Dict[int, str]) -> None` that calls `set_player_names()`, `_add_economy_columns()`, `_add_upgrade_columns()` in that order.
2. Add new method `ensure_unit_columns(self, player: str, readable_id: str, extra_attrs: Set[str] = None) -> bool` that checks `_seen_units` and calls `add_unit_columns()` only if not seen.
3. Add new method `ensure_building_columns(self, player: str, readable_id: str, extra_attrs: Set[str] = None) -> bool` that checks `_seen_buildings` and calls `add_building_columns()` only if not seen.
4. Delete method `build_schema_from_replay()` (lines 165-241).
5. Delete method `_build_columns_from_extractors()` (lines 244-284).
6. Update class docstring to remove references to schema pre-scan and two-pass.

### Step 2 — extraction_pipeline.py: restructure `_observer_mode_processing()`

1. Delete the `# --- Schema pre-scan ---` block (lines 228-236): the three lines calling `logger.info(...)` and `self.schema_manager.build_schema_from_replay(...)`.
2. Delete the `self.wide_table_builder = WideTableBuilder(self.schema_manager)` line at 239 (will be moved).
3. Delete `self.state_extractor.reset_frame_state()` at line 243.
4. Delete `self.replay_loader.load_replay(replay_path)` from its current position at line 247 (replay loading is now the FIRST operation).
5. Move `self.replay_loader.load_replay(replay_path)` to be the very first line of `_observer_mode_processing()` before the `with` block.
6. After the `player_names` dict is extracted (currently lines 258-259), add the call: `self.schema_manager.build_base_schema(player_names)`.
7. After `build_base_schema()`, add: `self.wide_table_builder = WideTableBuilder(self.schema_manager)`.
8. After creating `wide_table_builder`, add: `self.wide_table_builder.set_player_names(player_names)`.
9. Remove the now-redundant `if self.wide_table_builder is not None: self.wide_table_builder.set_player_names(player_names)` guard at lines 262-263.
10. Remove the now-redundant `self.schema_manager.set_player_names(player_names)` call at line 264 (already done inside `build_base_schema()`).
11. Inside the game loop, after `state = self.state_extractor.extract_observation_observer_mode(...)`, add the dynamic column creation blocks (see pseudocode in Section 6) before `row = self.wide_table_builder.build_row(state)`.
12. Update the docstring of `_observer_mode_processing()` to remove references to pre-scan.

### Step 3 — extraction_pipeline.py: delete legacy methods

1. Delete method `_two_pass_processing()` (lines 388-437) entirely.
2. Delete method `_single_pass_processing()` (lines 439-467) entirely.
3. Delete method `_extract_and_write()` (lines 469-629) entirely.
4. Delete method `_patch_p2_economy()` (lines 631-726) entirely.

### Step 4 — extraction_pipeline.py: update `process_replay()` dispatch

1. Remove the `elif self.processing_mode == 'two_pass':` branch and its body (lines 156-157).
2. Remove the `elif self.processing_mode == 'single_pass':` branch and its body (lines 158-159).
3. Change the remaining `else: raise ValueError(f"Invalid processing mode: {self.processing_mode}")` to match — only `'observer'` is now valid.
4. Update the module-level docstring to remove `two_pass` and `single_pass` from the mode list.
5. Update the class docstring to remove references to `two_pass` and `single_pass`.
6. Update the `__init__` docstring: remove `two_pass` and `single_pass` from `processing_mode` description.
7. Update comment on line 829 (in `process_replay_quick()`): remove `# preferred; fallback: 'two_pass'`.

### Step 5 — state_extractor.py

1. Delete `reset_frame_state()` method (lines 356-372).
2. Update class docstring to remove references to `reset_frame_state` and two-pass.

### Step 6 — unit_extractor.py

1. Delete `reset_frame_state()` method (lines 661-669).
2. Update the docstring/comments that reference two-pass processing (line 663-665).

### Step 7 — building_extractor.py

1. Delete `reset_frame_state()` method (lines 596-605).
2. Update the docstring/comments that reference two-pass processing (lines 597-599).

### Step 8 — parallel_processor.py

1. Change `'processing_mode': 'two_pass'` to `'processing_mode': 'observer'` on line 439 in `process_directory_quick()` default config.

### Step 9 — Example/documentation files (lower priority)

1. `QUICKSTART.py` line 128: Change `'processing_mode': 'single_pass'` to `'observer'`.
2. `QUICKSTART.py` line 166: Change `config={'processing_mode': 'two_pass'}` to `'observer'`.
3. `utils/example_validation_workflow.py` line 228: Change `'processing_mode': 'two_pass'` to `'observer'`.
4. Update `ARCHITECTURE.md`: Replace two-pass flow diagram with observer-mode diagram; update component table; update config propagation section.
5. Update `USAGE_EXAMPLES.md`: Replace two-pass vs single-pass comparison with observer mode description; update all example configs.
6. Update `PHASE3_IMPLEMENTATION_SUMMARY.md`: Update key methods list; update workflow section.
7. Update `utils/USAGE_EXAMPLES.md` line 190: Change `'two_pass'` to `'observer'`.

---

## 9. Verification Commands

Run these grep commands after implementation to confirm the two-pass schema has been fully dissolved. Each command should return **zero matches** if the pattern has been successfully removed.

### Verify pre-scan calls are gone
```bash
grep -rn "build_schema_from_replay" src_new/
```
Expected: no matches.

### Verify column-build-from-extractors is gone
```bash
grep -rn "_build_columns_from_extractors" src_new/
```
Expected: no matches.

### Verify legacy processing modes are gone from code (docs may still have 'two_pass' temporarily)
```bash
grep -rn "two_pass\|single_pass" src_new/ --include="*.py"
```
Expected: no matches in `.py` files.

### Verify legacy methods are gone
```bash
grep -rn "_two_pass_processing\|_single_pass_processing\|_extract_and_write\|_patch_p2_economy" src_new/
```
Expected: no matches.

### Verify reset_frame_state is gone
```bash
grep -rn "reset_frame_state" src_new/
```
Expected: no matches.

### Verify the dead _discover_entities_from_state call is gone
```bash
grep -rn "_discover_entities_from_state" src_new/
```
Expected: no matches.

### Confirm new methods exist
```bash
grep -rn "build_base_schema\|ensure_unit_columns\|ensure_building_columns" src_new/
```
Expected: matches in `schema_manager.py` (definitions) and `extraction_pipeline.py` (calls).

### Confirm observer mode is the default everywhere
```bash
grep -rn "processing_mode" src_new/ --include="*.py"
```
Expected: all occurrences show `'observer'`; no occurrences show `'two_pass'` or `'single_pass'`.

### Confirm no stale Pass A / Pass B / schema scan log messages remain
```bash
grep -rn "Pass 1\|Pass 2\|Pass A\|Pass B\|Schema scan\|pre-scan\|schema pre-scan" src_new/ --include="*.py"
```
Expected: no matches in `.py` files.
