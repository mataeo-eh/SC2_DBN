# src_new Pipeline Diagnostics: Extraction Methods & Schema Consistency

**Date:** 2026-02-26
**Auditor:** Claude (orchestrated diagnostics task with 5 parallel worker agents)

## Executive Summary

| Metric | Value |
|--------|-------|
| Total .py files audited | 32 |
| Files with definite issues (Cat A/B) | 13 |
| Files needing user review only (Cat C) | 2 |
| Clean files (Cat D) | 17 |
| Total Category A findings (Schema Mismatch) | 12 |
| Total Category B findings (Pattern Searching) | 21 |
| Total Category C findings (Needs User Review) | 17 |

### Critical: Schema Naming Incompatibility

The `data_processing/` files (`create_unit_counts.py`, `engineer_army_features.py`) were written before `schema_manager.py` adopted bot-name-based column naming. They expect:

```
p{n}_p{n}_{entitytype}_{id}_{attribute}   (e.g., p1_p1_marine_001_health)
```

But the current schema produces:

```
p{n}_{botname}_{entitytype}_{id}_{attribute}   (e.g., p1_really_marine_001_health)
```

**Impact:** Both data processing scripts are completely non-functional with current schema output. The `ENTITY_COL_RE` regex matches zero entity columns, causing all engineered features (unit counts, army direction, army size, complexity ratio) to be zero or default values. The downstream `discretize.py` also fails because it depends on these features.

Additionally, `wide_table_builder.py` has a **data flow bug** where `add_upgrades_to_row()` looks for keys (`attack_level`, `armor_level`, `shield_level`) that the `UpgradeExtractor` never produces, making all upgrade columns permanently zero.

---

## Section 1: DEFINITE ISSUES -- Schema Mismatches (Category A)

### create_unit_counts.py (2 findings)

**Path:** `./src_new/data_processing/create_unit_counts.py`

#### Finding A-1: ENTITY_COL_RE regex uses old naming pattern
- **Line(s):** 44-45
- **Code:**
  ```python
  # Entity column pattern: p{player}_p{player}_{type}_{id}_{attribute}
  ENTITY_COL_RE = re.compile(r"^(p[12])_p[12]_(.+?)_(\d+)_(.+)$")
  ```
- **Issue:** Regex expects `p{n}_p{n}_` prefix but current schema produces `p{n}_{botname}_`.
- **Impact:** `parse_entity_columns()` matches zero entity columns. All count features will be zero or missing. The entire file produces useless output.
- **Suggested Fix:** Update regex to `r"^(p[12])_([^_]+)_(.+?)_(\d+)_(.+)$"` to capture bot_name as a group, or import parsing logic from a shared utility.

#### Finding A-2: col_prefix construction uses old pattern
- **Line(s):** 146
- **Code:**
  ```python
  col_prefix = f"{player}_{player}_{entity_type}_{entity_id}"
  ```
- **Issue:** Constructs `p1_p1_marine_001` but schema produces `p1_really_marine_001`.
- **Impact:** All constructed column names fail to match actual columns. Alive counts always zero.
- **Suggested Fix:** Store bot_name from regex parse and use `f"{player}_{bot_name}_{entity_type}_{entity_id}"`.

---

### engineer_army_features.py (7 findings)

**Path:** `./src_new/data_processing/engineer_army_features.py`

#### Finding A-3: ENTITY_COL_RE regex uses old naming pattern
- **Line(s):** 46-47
- **Code:**
  ```python
  ENTITY_COL_RE = re.compile(r"^(p[12])_p[12]_(.+?)_(\d+)_(.+)$")
  ```
- **Issue:** Same regex mismatch as create_unit_counts.py.
- **Impact:** `parse_entity_columns()` matches nothing. All army features (direction, size, count, complexity ratio) will be defaults for every row.
- **Suggested Fix:** Same as A-1.

#### Finding A-4: find_base_positions() col construction
- **Line(s):** 145-146
- **Code:**
  ```python
  x_col = f"{player}_{player}_{etype}_{eid}_x"
  y_col = f"{player}_{player}_{etype}_{eid}_y"
  ```
- **Issue:** Uses `{player}_{player}_` prefix.
- **Impact:** Base positions can never be found, so `determine_movement_direction()` always returns "neutral".
- **Suggested Fix:** Use bot_name from regex or entity metadata.

#### Finding A-5: Worker fallback base position lookup
- **Line(s):** 163-164
- **Code:**
  ```python
  x_col = f"{player}_{player}_{etype}_{eid}_x"
  y_col = f"{player}_{player}_{etype}_{eid}_y"
  ```
- **Issue:** Fallback also uses old prefix.
- **Impact:** Both primary and fallback base detection fail.
- **Suggested Fix:** Same as A-4.

#### Finding A-6: is_entity_alive() col construction
- **Line(s):** 195
- **Code:**
  ```python
  col_prefix = f"{player}_{player}_{entity_type}_{entity_id}"
  ```
- **Issue:** Uses old prefix pattern.
- **Impact:** Cannot look up any entity state. Always returns False.
- **Suggested Fix:** Pass bot_name and use `f"{player}_{bot_name}_{entity_type}_{entity_id}"`.

#### Finding A-7: get_entity_position() col construction
- **Line(s):** 237
- **Code:**
  ```python
  col_prefix = f"{player}_{player}_{entity_type}_{entity_id}"
  x_col = f"{col_prefix}_x"
  y_col = f"{col_prefix}_y"
  ```
- **Issue:** Uses old prefix. No entity positions retrievable.
- **Impact:** All army positions are empty.
- **Suggested Fix:** Same as A-6.

#### Finding A-8: precompute_alive_masks() col construction
- **Line(s):** 537
- **Code:**
  ```python
  col_prefix = f"{player}_{player}_{etype}_{eid}"
  ```
- **Issue:** Uses old prefix for all column lookups.
- **Impact:** All alive masks are zeroed out.
- **Suggested Fix:** Same pattern.

#### Finding A-9: precompute_position_arrays() col construction
- **Line(s):** 586
- **Code:**
  ```python
  col_prefix = f"{player}_{player}_{etype}_{eid}"
  ```
- **Issue:** Uses old prefix.
- **Impact:** No position arrays populated.
- **Suggested Fix:** Same pattern.

---

### wide_table_builder.py (1 finding)

**Path:** `./src_new/extraction/wide_table_builder.py`

#### Finding A-10: add_upgrades_to_row() key mismatch
- **Line(s):** 334-343
- **Code:**
  ```python
  upgrade_mapping = {
      'attack_level': f'{player}_upgrade_attack_level',
      'armor_level': f'{player}_upgrade_armor_level',
      'shield_level': f'{player}_upgrade_shield_level',
  }
  for upgrade_name, col_name in upgrade_mapping.items():
      if col_name in row:
          row[col_name] = upgrades_data.get(upgrade_name, 0)
  ```
- **Issue:** Looks for keys `attack_level`/`armor_level`/`shield_level` in `upgrades_data`, but `UpgradeExtractor.extract()` returns dicts keyed by full lowercase upgrade name (e.g., `'terraninfantryweaponslevel1'`). These keys never match.
- **Impact:** **All upgrade columns in the parquet output are always 0.** This is a definite data loss bug.
- **Suggested Fix:** Add a transformation step that iterates raw upgrade data, checks each entry's `category` field, and tracks the maximum `level` for weapons/armor/shields. Pass `{'attack_level': max_weapons, 'armor_level': max_armor, 'shield_level': max_shields}` to this method.

---

### state_extractor.py (1 finding)

**Path:** `./src_new/extraction/state_extractor.py`

#### Finding A-11: BuildingTracker uses incompatible ID format (dead code)
- **Line(s):** 505
- **Code:**
  ```python
  building_id = f"building_{tag}"
  ```
- **Issue:** `BuildingTracker.process_buildings()` generates IDs like `building_4294967297` (raw SC2 tag), not the readable format `p{n}_{name}_{counter}`. If this tracker's output were fed to WideTableBuilder, column prefix construction would fail.
- **Impact:** Dead code -- not used in the active pipeline. But could cause confusion if someone tries to use it.
- **Suggested Fix:** Remove BuildingTracker and UnitTracker if unused, or align to readable ID format.

---

### QUICKSTART.py (1 finding)

**Path:** `./src_new/pipeline/QUICKSTART.py`

#### Finding A-12: Hardcoded column names in example code
- **Line(s):** 215-217
- **Code:**
  ```python
  print(f"  Duration: {df['timestamp_seconds'].max():.1f}s")
  print(f"  P1 final minerals: {df.iloc[-1]['p1_minerals']}")
  print(f"  P2 final minerals: {df.iloc[-1]['p2_minerals']}")
  ```
- **Issue:** Hardcoded column name literals (`timestamp_seconds`, `p1_minerals`, `p2_minerals`). These currently match the schema but are fragile.
- **Impact:** Low -- example code. Would raise KeyError if economy naming changes.
- **Suggested Fix:** Acceptable for demo code. Add a comment noting these must match the schema.

---

## Section 2: DEFINITE ISSUES -- Pattern Searching (Category B)

### economy_extractor.py (2 findings)

**Path:** `./src_new/extractors/economy_extractor.py`

#### Finding B-1: Hardcoded field extraction map
- **Line(s):** 45-52
- **Code:**
  ```python
  _FIELD_MAP = {
      'm_scoreValueMineralsCurrent':        ('minerals',                   1),
      'm_scoreValueVespeneCurrent':         ('vespene',                    1),
      'm_scoreValueFoodUsed':               ('supply_used',             4096),
      'm_scoreValueFoodMade':               ('supply_cap',              4096),
      'm_scoreValueMineralsCollectionRate': ('collection_rate_minerals',   1),
      'm_scoreValueVespeneCollectionRate':  ('collection_rate_vespene',    1),
  }
  ```
- **Issue:** Only 6 fields extracted from SPlayerStatsEvent, which contains dozens more. Intentional curated subset, but must be kept in sync with schema_manager's `_add_economy_columns()`.
- **Impact:** Additional economy metrics silently dropped. Currently in sync with schema.
- **Suggested Fix:** Document as intentional. Consider deriving one from the other.

#### Finding B-2: Event type string matching
- **Line(s):** 138-139
- **Code:**
  ```python
  if event['_event'] != 'NNet.Replay.Tracker.SPlayerStatsEvent':
      continue
  ```
- **Issue:** String matching on s2protocol event type name.
- **Impact:** Unavoidable -- s2protocol event identification is string-based by design.
- **Suggested Fix:** Extract to a module-level constant for single-point-of-change.

---

### upgrade_extractor.py (1 finding)

**Path:** `./src_new/extractors/upgrade_extractor.py`

#### Finding B-3: Keyword-based upgrade categorization
- **Line(s):** 61-83
- **Code:**
  ```python
  if any(keyword in name_lower for keyword in ["weapon", "weapons", "melee", "missile", "ship", "attack"]):
      category = "weapons"
  elif "armor" in name_lower or "armour" in name_lower:
      category = "armor"
  elif "shield" in name_lower or "shields" in name_lower:
      category = "shields"
  ```
- **Issue:** Substring matching on upgrade names for categorization. The actual extraction in `extract()` is fully programmatic.
- **Impact:** Categorization is display-only, not affecting data capture. Some upgrades may be miscategorized (e.g., "ChitinousPlating" goes to "other" instead of "armor").
- **Suggested Fix:** Replace with a lookup table mapping upgrade_id to category, or accept as best-effort heuristic.

---

### state_extractor.py (1 finding)

**Path:** `./src_new/extraction/state_extractor.py`

#### Finding B-4: UnitTracker uses incompatible ID format (dead code)
- **Line(s):** 373-411
- **Code:**
  ```python
  return f"unit_{unit_type}_{id_num:03d}"
  ```
- **Issue:** UnitTracker generates IDs like `unit_48_001` (raw type int), not the readable format `p{n}_{name}_{counter}`.
- **Impact:** Dead code -- not used in active pipeline. Incompatible if someone tries to use it.
- **Suggested Fix:** Remove if unused.

---

### schema_manager.py (1 finding)

**Path:** `./src_new/extraction/schema_manager.py`

#### Finding B-5: add_unit_count_columns() unused method
- **Line(s):** 508-525
- **Code:**
  ```python
  col_name = f'p{player_num}_{unit_type.lower()}_count'
  ```
- **Issue:** Constructs count columns without bot name (follows economy pattern `p{n}_{suffix}`). Dead code -- not called anywhere in the pipeline.
- **Impact:** None currently. If used, creates inconsistency with entity column naming.
- **Suggested Fix:** Remove if unused, or document naming divergence.

---

### wide_table_builder.py (2 findings)

**Path:** `./src_new/extraction/wide_table_builder.py`

#### Finding B-6: Economy column names duplicated
- **Line(s):** 309-313
- **Code:**
  ```python
  economy_columns = [
      'minerals', 'vespene', 'supply_used', 'supply_cap',
      'collection_rate_minerals', 'collection_rate_vespene',
  ]
  ```
- **Issue:** Economy column suffixes duplicated from `schema_manager._add_economy_columns()`. Must be maintained in parallel.
- **Impact:** If schema adds/renames a column and this list isn't updated, that column stays NaN.
- **Suggested Fix:** Define in one place and import.

#### Finding B-7: get_row_summary() hardcoded column names
- **Line(s):** 460-481
- **Code:**
  ```python
  'p1_minerals': row.get('p1_minerals'),
  'p2_minerals': row.get('p2_minerals'),
  'p1_supply_used': row.get('p1_supply_used'),
  'p2_supply_used': row.get('p2_supply_used'),
  ```
- **Issue:** Hardcoded references to economy column names in debug summary method.
- **Impact:** Low -- debug utility. Returns None silently if columns renamed.
- **Suggested Fix:** Minor. Could reference from schema.

---

### parquet_writer.py (2 findings)

**Path:** `./src_new/extraction/parquet_writer.py`

#### Finding B-8: Hardcoded 'Messages' column name
- **Line(s):** 244
- **Code:**
  ```python
  if col == 'Messages':
      df[col] = df[col].apply(self._serialize_messages_for_parquet)
  ```
- **Issue:** Hardcoded string `'Messages'` for special serialization.
- **Impact:** Very low. Stable base column name.
- **Suggested Fix:** Extract to constant.

#### Finding B-9: startswith('[') content pattern matching
- **Line(s):** 307, 341
- **Code:**
  ```python
  if value.startswith('['):
      try:
          return json.loads(value)
  ```
- **Issue:** Pattern matching on data content to detect JSON arrays. Protected by try/except.
- **Impact:** Very low.
- **Suggested Fix:** Acceptable with the try/except guard.

---

### replay_loader.py (extraction)

**Path:** `./src_new/extraction/replay_loader.py`

#### Finding B-10: Case-sensitive file extension check
- **Line(s):** 89
- **Code:**
  ```python
  if not replay_path.suffix == '.SC2Replay':
  ```
- **Issue:** Case-sensitive check on `.SC2Replay` extension.
- **Impact:** Very low. SC2 consistently uses this extension.
- **Suggested Fix:** Use `.lower()` comparison for robustness.

---

### discretize.py (1 finding)

**Path:** `./src_new/data_processing/discretize.py`

#### Finding B-11: Hardcoded columns_to_keep list
- **Line(s):** 50-63
- **Code:**
  ```python
  columns_to_keep = [
      "p1_main_army_direction", "p1_army_complexity_ratio",
      "p1_main_army_size", "p1_army_count",
      "p1_supply_cap", "p1_supply_used",
      "p2_main_army_direction", "p2_main_army_size",
      "p2_army_count", "p2_army_complexity_ratio",
      "p2_supply_cap", "p2_supply_used",
  ]
  ```
- **Issue:** Hardcoded list of column names. Army feature columns depend on `engineer_army_features.py` (which is broken due to Cat A issues). Economy columns match current schema.
- **Impact:** Brittle coupling. Would raise KeyError on rename. Army features are non-functional upstream.
- **Suggested Fix:** Programmatically discover columns by suffix pattern.

---

### validation.py (5 findings)

**Path:** `./src_new/utils/validation.py`

#### Finding B-12: Economy column substring matching
- **Line(s):** 431-433
- **Code:**
  ```python
  economy_cols = [col for col in df.columns if any(
      x in col for x in ['minerals', 'vespene', 'supply_', 'workers', 'idle_workers']
  )]
  ```
- **Issue:** Substring matching for economy columns. Could false-positive on entity names containing "minerals".
- **Impact:** Low risk currently.
- **Suggested Fix:** Use precise regex matching on known economy format.

#### Finding B-13: Hardcoded economy column f-strings
- **Line(s):** 466-469
- **Code:**
  ```python
  minerals_col = f'p{player}_minerals'
  vespene_col = f'p{player}_vespene'
  supply_used_col = f'p{player}_supply_used'
  supply_cap_col = f'p{player}_supply_cap'
  ```
- **Issue:** Hardcoded economy column name construction. Currently matches schema.
- **Impact:** Low -- would break if economy naming changes.
- **Suggested Fix:** Import from shared constants.

#### Finding B-14: Unit column discovery uses old prefix assumption
- **Line(s):** 545-557
- **Code:**
  ```python
  common_units = ['marine', 'scv', 'zealot', 'probe', 'zergling', 'drone']
  unit_cols = [col for col in df.columns
              if col.startswith(f'p{player}_{unit_type}_')
              and col.endswith('_x')]
  ```
- **Issue:** `startswith(f'p{player}_{unit_type}_')` would match old pattern `p1_marine_*` but not current `p1_really_marine_*`.
- **Impact:** Unit count consistency check matches zero columns -- effectively a no-op.
- **Suggested Fix:** Account for bot_name in prefix.

#### Finding B-15: State column suffix matching
- **Line(s):** 591-592
- **Code:**
  ```python
  state_cols = [col for col in df.columns if col.endswith('_state') or col.endswith('_status')]
  ```
- **Issue:** Suffix-based pattern matching. Reasonable heuristic, low risk.
- **Impact:** Low.
- **Suggested Fix:** Minor -- could combine with prefix check.

#### Finding B-16: Column categorization by substring
- **Line(s):** 655-657
- **Code:**
  ```python
  unit_cols = [col for col in df.columns if any(x in col for x in ['_x', '_y', '_health', '_state'])]
  economy_cols = [col for col in df.columns if any(x in col for x in ['minerals', 'vespene', 'supply'])]
  ```
- **Issue:** Substring matching for stats generation. Display-only.
- **Impact:** Low.
- **Suggested Fix:** Low priority.

---

### documentation.py (3 findings)

**Path:** `./src_new/utils/documentation.py`

#### Finding B-17: Column categorization by substring
- **Line(s):** 91-105
- **Code:**
  ```python
  if col in ['game_loop', 'timestamp_seconds']:
      base_cols.append(col)
  elif '_count' in col and not any(x in col for x in ['_x', '_y', '_z']):
      count_cols.append(col)
  elif any(x in col for x in ['minerals', 'vespene', 'supply_', 'workers']):
      economy_cols.append(col)
  ```
- **Issue:** Heuristic column classification by substrings. Documentation generation only.
- **Impact:** Low. Could misclassify entity types containing keywords.
- **Suggested Fix:** Low priority. Could query SchemaManager for categories.

#### Finding B-18: Unit ID parsing assumes old column format
- **Line(s):** 187-189
- **Code:**
  ```python
  parts = col.split('_')
  if len(parts) >= 4:
      unit_id = '_'.join(parts[:3])  # p1_marine_001
  ```
- **Issue:** Takes first 3 underscore-separated parts for unit ID, but current schema has `p1_really_marine_001_x` (4 meaningful parts before attribute).
- **Impact:** Produces `p1_really_marine` instead of `p1_really_marine_001`. Documentation groupings incorrect.
- **Suggested Fix:** Use `parts[:4]` for current schema.

#### Finding B-19: Building ID parsing assumes old format
- **Line(s):** 239-242
- **Code:**
  ```python
  building_id = '_'.join(parts[:3])
  ```
- **Issue:** Same as B-18 but for buildings.
- **Impact:** Documentation groupings incorrect.
- **Suggested Fix:** Use `parts[:4]`.

---

### engineer_army_features.py (1 additional B finding)

#### Finding B-20: Hardcoded entity ID "001" for base detection
- **Line(s):** 144
- **Code:**
  ```python
  if etype in BASE_TYPES and eid == "001" and "x" in attrs and "y" in attrs:
  ```
- **Issue:** Assumes the first base always has ID `001`.
- **Impact:** If ID numbering changes, base detection fails.
- **Suggested Fix:** Find earliest-created base by checking first non-NaN position row.

---

### QUICKSTART.py (1 additional B finding)

#### Finding B-21: Messages schema keys hardcoded in example
- **Line(s):** 231
- **Code:**
  ```python
  print(f"    [{msg['game_loop']}] P{msg['player_id']}: {msg['message']}")
  ```
- **Issue:** References hardcoded messages column names. Example/demo code.
- **Impact:** Low.
- **Suggested Fix:** Add comment noting dependency on messages output format.

---

## Section 3: NEEDS USER REVIEW -- Named Extraction (Category C)

### unit_extractor.py

**Path:** `./src_new/extractors/unit_extractor.py`

#### Finding C-1: BUILDING_TYPES set is out of sync with building_extractor.py
- **Line(s):** 32-80
- **What it contains:** Set of ~30 building type IDs (Terran, Protoss, Zerg)
- **What it's used for:** Filtering buildings out of unit extraction via `is_building()`
- **Issue:** This is a **subset** of building_extractor.py's `BUILDING_TYPES`. Missing ~15 entries: OrbitalCommand (22), SupplyDepotLowered (36), PlanetaryFortress (130), all Reactor/TechLab variants (132-143), FleetBeacon (64), GreaterSpire (101), Extractor (104), CreepTumors (87/137/138), LurkerDenMP (142).
- **Impact:** Buildings missing from this set slip through the unit extractor's filter and are extracted as units, creating duplicates.
- **Programmatic alternative:** Import `is_building` from `building_extractor.py` or extract both sets into a shared constants module.
- **Question:** Is maintaining a separate, smaller building set intentional (e.g., for performance or different classification needs), or should it be unified with building_extractor's list?

---

### building_extractor.py

**Path:** `./src_new/extractors/building_extractor.py`

#### Finding C-2: BUILDING_TYPES set with ID collisions in comments
- **Line(s):** 34-102
- **What it contains:** Set of ~50 building type IDs (all races + creep tumors)
- **What it's used for:** Identifying buildings from raw unit lists
- **Issue:** IDs 133, 138, and 142 each have two conflicting comment labels (e.g., 133 = TechLab AND WarpGate). Since SC2 cannot have two buildings sharing the same type ID, one comment per collision is wrong.
- **Programmatic alternative:** Cross-reference each ID against `pysc2.lib.units.get_unit_type()` to verify names. Or derive building classification programmatically from unit metadata.
- **Question:** Should the comments be verified and corrected? Should this list be auto-generated from pysc2's unit database?

---

### state_extractor.py

#### Finding C-3: Hardcoded player count {1, 2}
- **Line(s):** 78-195
- **What it contains:** Player numbers hardcoded throughout both extraction methods
- **What it's used for:** Iterating over players in a 1v1 game
- **Impact:** Cannot support FFA or team games without refactoring.
- **Question:** Is 1v1-only scope intentional and permanent, or should this be parameterized?

---

### schema_manager.py (3 findings)

#### Finding C-4: _add_upgrade_columns() hardcoded list
- **Line(s):** 397-417
- **What it contains:** Three upgrade names: `attack_level`, `armor_level`, `shield_level`
- **What it's used for:** Defining the upgrade columns in the schema
- **Issue:** Not derived from UpgradeExtractor. Combined with Finding A-10 (wide_table_builder key mismatch), the upgrade data flow is broken end-to-end.
- **Programmatic alternative:** Derive upgrade categories from UpgradeExtractor output.
- **Question:** Should upgrade columns be expanded to include individual upgrades, or should the summary approach be fixed?

#### Finding C-5: Column name parsing ambiguity with underscored bot names
- **Line(s):** 32-49, 293-301
- **What it contains:** `sanitize_name()` and `_`.join() split logic
- **Issue:** If bot names contain underscores (e.g., "Bot v2.0" -> "bot_v2_0"), column names like `p1_bot_v2_0_marine_001_health` become ambiguous to parse backwards.
- **Impact:** Low -- no current code reverse-parses entity columns.
- **Question:** Is this an acceptable trade-off, or should a different delimiter separate bot name from entity type?

#### Finding C-6: UNIT_BASE_ATTRIBUTES / BUILDING_BASE_ATTRIBUTES duplicated from FIELD_CONFIG
- **Line(s):** 55-107
- **What it contains:** Lists of (suffix, dtype, description) tuples mirroring FIELD_CONFIG entries
- **What it's used for:** Schema column registration
- **Issue:** Must be manually kept in sync with UNIT_FIELD_CONFIG and BUILDING_FIELD_CONFIG. Adding a field to one without the other causes silent data loss.
- **Programmatic alternative:** Generate dynamically: `[(entry['column_suffix'], 'object', entry['description']) for entry in UNIT_FIELD_CONFIG if entry['always']]`
- **Question:** Should this be auto-derived from FIELD_CONFIG to eliminate duplication?

---

### wide_table_builder.py

#### Finding C-7: Lifecycle override state sets hardcoded
- **Line(s):** 30-34
- **What it contains:** `UNIT_LIFECYCLE_OVERRIDE_STATES = {'unit_started', 'building', 'completed', 'destroyed'}` and `BUILDING_LIFECYCLE_OVERRIDE_STATES = {'building_started', 'completed', 'destroyed', 'cancelled'}`
- **What it's used for:** Determining when to fill attribute columns with lifecycle string instead of real data
- **Issue:** Must stay in sync with lifecycle strings from UnitExtractor and BuildingExtractor.
- **Programmatic alternative:** Define constants in a shared module.
- **Question:** Should lifecycle state strings be centralized?

---

### QUICKSTART.py

#### Finding C-8: Schema JSON key assumptions
- **Line(s):** 239-247
- **What it contains:** Assumes `schema['columns']` and `schema['documentation'][col_name]['description']` keys
- **What it's used for:** Demo output reading example
- **Impact:** Would break if schema JSON format changes. Low risk for example code.

---

### create_unit_counts.py (4 findings)

#### Finding C-9: BUILDING_TYPES hardcoded set
- **Line(s):** 48-67
- **What it contains:** ~50 building type name strings (all races)
- **What it's used for:** Distinguishing buildings from units in count computation
- **Programmatic alternative:** Derive from entity attributes (e.g., presence of `build_progress` or building-specific fields).
- **Question:** Is this domain knowledge intentional, or should it be unified with the extractor-level building sets?

#### Finding C-10: AIR_UNIT_TYPES hardcoded set
- **Line(s):** 70-77
- **What it contains:** ~18 air unit type names (all races)
- **What it's used for:** Computing `has_air_units` feature
- **Programmatic alternative:** Could use `is_flying` attribute if tracked in the data.
- **Question:** Is this the correct approach, or should air detection use unit attributes?

#### Finding C-11: PRODUCTION_BUILDING_TYPES hardcoded set
- **Line(s):** 80-87
- **What it contains:** ~10 production building names
- **What it's used for:** Computing `production_building_count` feature
- **Issue:** Notably missing "warpgate" (Protoss production building).
- **Question:** Should "warpgate" be added? Should this be auto-derived?

#### Finding C-12: ALIVE_STATES hardcoded set
- **Line(s):** 90
- **What it contains:** `{"built", "existing"}`
- **What it's used for:** Determining alive units/buildings for counting
- **Issue:** Must match lifecycle strings from extractors. Duplicated in engineer_army_features.py.
- **Question:** Should this be centralized in a shared constants module?

---

### engineer_army_features.py (4 findings)

#### Finding C-13: BUILDING_TYPES duplicate set
- **Line(s):** 50-69
- **What it contains:** Same as C-9, duplicated across files
- **Impact:** Changes must be synchronized across both files.
- **Suggested Fix:** Centralize into shared constants module.

#### Finding C-14: WORKER_TYPES hardcoded set
- **Line(s):** 72
- **What it contains:** `{"scv", "probe", "drone", "mule"}`
- **What it's used for:** Excluding workers from army clustering
- **Programmatic alternative:** Could use unit role metadata if available.
- **Question:** Is MULE intentionally classified as a worker? Should this be centralized?

#### Finding C-15: BASE_TYPES hardcoded set
- **Line(s):** 75-78
- **What it contains:** Base structure names (CommandCenter variants, Nexus, Hatchery/Lair/Hive)
- **What it's used for:** Finding starting positions for army direction calculation
- **Programmatic alternative:** Could detect bases by highest supply-cap contribution or specific unit category.
- **Question:** Is this complete and correct?

#### Finding C-16: ALIVE_STATES duplicate set
- **Line(s):** 84
- **What it contains:** `{"built", "existing"}` -- duplicate of C-12
- **Impact:** Same maintenance burden.
- **Suggested Fix:** Centralize.

---

### NON_ARMY_TYPES (not found as a separate set)

Note: The prompt's verification step asked about `NON_ARMY_TYPES`. This does not exist as a named constant. Army exclusion is handled by combining `BUILDING_TYPES` + `WORKER_TYPES` in `engineer_army_features.py`.

---

## Section 4: Clean Files

| # | File | Notes |
|---|------|-------|
| 1 | `./src_new/__init__.py` | Package root. Version metadata only. |
| 2 | `./src_new/batch/__init__.py` | Batch package init. Re-exports ReplayProcessor, BatchController. |
| 3 | `./src_new/extractors/__init__.py` | Extractors package init. Re-exports all extractor classes/functions. |
| 4 | `./src_new/extraction/__init__.py` | Extraction package init. Re-exports all extraction classes. |
| 5 | `./src_new/pipeline/__init__.py` | Pipeline package init. Re-exports pipeline classes and convenience functions. |
| 6 | `./src_new/pipeline/extraction_pipeline.py` | Main pipeline orchestrator. All column naming delegated to SchemaManager. Fully programmatic entity iteration. |
| 7 | `./src_new/pipeline/game_loop_iterator.py` | Game loop stepping utility. No schema interaction. |
| 8 | `./src_new/pipeline/dataset_pipeline.py` | Kaggle dataset upload utility. No schema interaction. |
| 9 | `./src_new/pipeline/parallel_processor.py` | Batch replay processing with ProcessPoolExecutor. Delegates to pipeline. |
| 10 | `./src_new/pipeline/replay_loader.py` | SC2 engine interaction layer. No schema interaction. |
| 11 | `./src_new/pipeline/logging_config.py` | Logging infrastructure. No schema interaction. |
| 12 | `./src_new/pipeline/integration_check.py` | Import/structure verification diagnostic. No schema interaction. |
| 13 | `./src_new/data_processing/fetch_bot_replays.py` | AI Arena replay download client. No schema interaction. |
| 14 | `./src_new/utils/__init__.py` | Utils package init. Re-exports validation and documentation functions. |
| 15 | `./src_new/utils/validation_check.py` | Smoke test for validation module imports. No schema interaction. |
| 16 | `./src_new/utils/needs_processing.py` | File timestamp comparison utility (3 lines). No schema interaction. |
| 17 | `./src_new/utils/example_validation_workflow.py` | Demo script for validation/documentation usage. Delegates all schema work. |

---

## Appendix: Current Schema Reference

### Entity Columns (units and buildings)
- **Pattern:** `p{n}_{botname}_{entitytype}_{id}_{attribute}`
- **Example:** `p1_really_marine_001_health`, `p2_what_nexus_001_shields`
- **Construction:** `schema_manager.py` line 306: `f'{player}_{bot_name}_{stripped_id}_{col_suffix}'`
- **Bot name:** sanitized via `sanitize_name()` (lowercase, non-alphanumeric -> underscore)
- **Stripped ID:** readable_id minus leading `p{n}_` (e.g., `marine_001` from `p1_marine_001`)

### Economy Columns
- **Pattern:** `p{n}_{suffix}`
- **Examples:** `p1_minerals`, `p1_vespene`, `p1_supply_used`, `p1_supply_cap`, `p1_collection_rate_minerals`, `p1_collection_rate_vespene`
- **Construction:** `schema_manager.py` line 386: `f'p{player_num}_{col_suffix}'`

### Upgrade Columns
- **Pattern:** `p{n}_upgrade_{name}`
- **Examples:** `p1_upgrade_attack_level`, `p1_upgrade_armor_level`, `p1_upgrade_shield_level`
- **Construction:** `schema_manager.py` line 412: `f'p{player_num}_upgrade_{upgrade}'`

### Base Columns
- `game_loop` (int64)
- `timestamp_seconds` (float64)
- `Messages` (object)

### Engineered Feature Columns (from data_processing, currently non-functional)
- `p{n}_main_army_direction` (direction string)
- `p{n}_main_army_size` (int)
- `p{n}_army_count` (int)
- `p{n}_army_complexity_ratio` (float)
- `p{n}_{unittype}_count` (int, per unit type)
- `p{n}_total_unit_types` (int)
- `p{n}_production_building_count` (int)
- `p{n}_has_air_units` (bool)
