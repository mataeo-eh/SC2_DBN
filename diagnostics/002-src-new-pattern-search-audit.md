# src_new Pattern-Search Audit

**Date:** 2026-02-18
**Auditor:** Claude (automated research task)

---

## Summary

| Metric | Value |
|--------|-------|
| Total .py files scanned | 32 |
| Files with issues | 6 |
| Files clean | 26 |
| Total findings | 12 |

### Files with Issues
- `src_new/extractors/upgrade_extractor.py`
- `src_new/extraction/wide_table_builder.py`
- `src_new/data_processing/create_unit_counts.py`
- `src_new/data_processing/engineer_army_features.py`
- `src_new/extraction/schema_manager.py`
- `src_new/utils/validation.py`

### Clean Files
- `src_new/__init__.py`
- `src_new/batch/__init__.py`
- `src_new/extraction/__init__.py`
- `src_new/extraction/parquet_writer.py`
- `src_new/extraction/replay_loader.py`
- `src_new/extraction/state_extractor.py`
- `src_new/extractors/__init__.py`
- `src_new/extractors/building_extractor.py`
- `src_new/extractors/economy_extractor.py`
- `src_new/extractors/unit_extractor.py`
- `src_new/pipeline/__init__.py`
- `src_new/pipeline/dataset_pipeline.py`
- `src_new/pipeline/extraction_pipeline.py`
- `src_new/pipeline/game_loop_iterator.py`
- `src_new/pipeline/integration_check.py`
- `src_new/pipeline/logging_config.py`
- `src_new/pipeline/parallel_processor.py`
- `src_new/pipeline/QUICKSTART.py`
- `src_new/pipeline/replay_loader.py`
- `src_new/utils/__init__.py`
- `src_new/utils/documentation.py`
- `src_new/utils/example_validation_workflow.py`
- `src_new/utils/needs_processing.py`
- `src_new/utils/validation_check.py`
- `src_new/data_processing/discretize.py`
- `src_new/data_processing/fetch_bot_replays.py`

---

## API Reference: What s2client-proto Actually Provides

This section documents what the s2client-proto API unambiguously provides for the event types used by this codebase. All fields below are **deterministic** — the SC2 engine fills them in; the code does not need to guess or search.

### Unit Fields (`raw.proto` — `message Unit`)

Every unit in `obs.observation.raw_data.units` carries:

| Field | Type | Meaning |
|-------|------|---------|
| `tag` | `uint64` | Unique persistent identifier for this unit across frames |
| `unit_type` | `uint32` | Numeric ID that unambiguously identifies the unit type |
| `owner` | `int32` | **Player ID (1 or 2) who owns this unit.** This is the direct attribution field. |
| `alliance` | `Alliance` enum | Perspective-relative relationship (Self=1, Ally=2, Neutral=3, Enemy=4) |
| `display_type` | `DisplayType` enum | Visible=1, Snapshot=2, Hidden=3, Placeholder=4 |
| `pos` | `Point` | x/y/z world coordinates |
| `build_progress` | `float` | 0.0–1.0 construction progress |
| `health` / `health_max` | `float` | Current and maximum health |
| `shield` / `shield_max` | `float` | Current and maximum shields (Protoss only; 0 for non-Protoss) |
| `energy` / `energy_max` | `float` | Current and maximum energy (casters only; 0 otherwise) |
| `attack_upgrade_level` | `int32` | Attack upgrade level (0–3) |
| `armor_upgrade_level` | `int32` | Armor upgrade level (0–3) |
| `shield_upgrade_level` | `int32` | Shield upgrade level (0–3, Protoss only) |
| `is_flying`, `is_burrowed`, `is_hallucination` | `bool` | Unit state flags |

**Key point for player attribution:** `unit.owner` is the **definitive** player attribution. It is set by the SC2 engine to the player ID (1, 2, etc.) who controls the unit. There is never a reason to search across both players' data structures to determine who owns a unit.

### Upgrade Fields (`raw.proto` — `message PlayerRaw`)

In **player-perspective mode**, `obs.observation.raw_data.player` is a `PlayerRaw` message scoped to the observed player. It contains:

| Field | Type | Meaning |
|-------|------|---------|
| `upgrade_ids` | `repeated uint32` | List of upgrade IDs **completed by this specific player**. This list is perspective-dependent — it only contains the observed player's upgrades. |

**Key point for upgrade attribution:** When the replay is started with `observed_player_id=1`, `raw_data.player.upgrade_ids` contains **only player 1's upgrades**. There is no ambiguity about which player completed an upgrade — the entire `upgrade_ids` list belongs to exactly the player whose perspective is active.

In **observer mode** (no `observed_player_id`), the pipeline correctly switches perspective via `ActionObserverPlayerPerspective` before each `observe()` call, so `raw_data.player.upgrade_ids` still reflects only the active player's upgrades.

### Economy Fields (`sc2api.proto` — `message PlayerCommon`)

`obs.observation.player_common` is perspective-dependent and contains fields like `minerals`, `vespene`, `food_used`, `food_cap`, `army_count`, `warp_gate_count`, `larva_count`, etc. — all scoped to the observed player.

### Player Identification (Replay Info, `sc2api.proto`)

`controller.replay_info()` returns `ResponseReplayInfo`, which contains `player_info` entries. Each `PlayerInfoExtra` has:
- `player_info.player_id` — the player's numeric ID (1, 2, ...)
- `player_info.race_actual` — the race the player actually played as (`Race` enum: Terran=1, Zerg=2, Protoss=3, Random=4)

The race of a player is thus directly available as a typed enum value — there is no need to infer race from unit or upgrade names.

---

## Known Bug: Upgrade Attribution (Confirmed Example)

### Description

The `UpgradeExtractor` reads `obs.observation.raw_data.player.upgrade_ids` — which is correct **in isolation**. The confirmed bug arises from how the upgrade extractor is **called** in the legacy `extract_observation()` path inside `StateExtractor`.

In the legacy single-observation path (`extract_observation()`, used during the schema pre-scan pass in `SchemaManager.build_schema_from_replay()`), the code calls both:

```python
state['p1_upgrades'] = self.extract_upgrades(obs, player_id=1)
state['p2_upgrades'] = self.extract_upgrades(obs, player_id=2)
```

Both calls pass the **same single `obs`**. Since the replay is started with `observed_player_id=1`, the `raw_data.player.upgrade_ids` in that `obs` contains **only player 1's upgrades**. Player 2's extractor reads the same list and produces an identical copy — so both players are credited with all of player 1's upgrades.

### Concrete Example: Stim and Concussive Shells

- If player 1 is Terran and has researched Stimpack (upgrade ID 15) and Concussive Shells (upgrade ID 22), both appear in `raw_data.player.upgrade_ids` when observed from player 1's perspective.
- If player 2 is Protoss, they cannot research these upgrades and their `upgrade_ids` list should be empty for these IDs.
- But in the single-observation legacy path, `UpgradeExtractor(player_id=2).extract(obs)` reads the same `obs.raw_data.player.upgrade_ids` and **incorrectly** attributes Stimpack and Concussive Shells to player 2.

### Why the Observer Mode Path Fixes This

The observer mode pipeline (`_observer_mode_processing`) and the `extract_observation_observer_mode()` method correctly pass `obs_p1` for player 1's upgrades and `obs_p2` for player 2's upgrades — each observation collected after switching perspective. This is the correct approach.

The schema pre-scan in `SchemaManager.build_schema_from_replay()` still uses the single-observation path (player 1 perspective), so upgrade data during the schema scan is still incorrect for player 2 — though this only affects the pre-scan and not the final data extraction when using observer mode.

---

## Findings by File

---

### upgrade_extractor.py

**Path:** `src_new/extractors/upgrade_extractor.py`
**Status:** Issues Found

#### Finding 1 — Pattern B: String matching to categorize upgrade types

- **Lines:** 65–76
- **Pattern Type:** B
- **Code:**
  ```python
  # Determine category
  if any(keyword in name_lower for keyword in ["weapon", "weapons", "melee", "missile", "ship", "attack"]):
      category = "weapons"
  elif "armor" in name_lower or "armour" in name_lower:
      category = "armor"
  elif "shield" in name_lower or "shields" in name_lower:
      category = "shields"
  elif "speed" in name_lower or "movement" in name_lower:
      category = "movement"
  elif "energy" in name_lower or "capacity" in name_lower:
      category = "energy"
  else:
      category = "other"
  ```
- **Problem:** This uses substring matching on the human-readable upgrade name string to determine upgrade category. The API provides upgrade IDs as typed integers from the `Upgrades` enum — which are stable, deterministic, and could be mapped directly to categories via a lookup table. String matching is fragile: if an upgrade is renamed, has a non-English name, or has a name that partially matches a keyword (e.g., a hypothetical upgrade named "Missile Defense" would be miscategorized as "weapons"), the categorization silently breaks. The match also relies on `pysc2_upgrades.Upgrades(upgrade_id).name`, which is a library-internal string representation.
- **API provides:** `upgrade_id` (uint32) — a stable numeric ID that uniquely identifies each upgrade. A dictionary mapping `upgrade_id -> category` would be deterministic and immune to string representation changes.

---

#### Finding 2 — Pattern B: Regex on upgrade name string to extract level

- **Lines:** 79–81
- **Pattern Type:** B
- **Code:**
  ```python
  # Extract level (look for patterns like "Level1", "Level2", etc.)
  level_match = re.search(r'level(\d)', name_lower)
  if level_match:
      level = int(level_match.group(1))
  ```
- **Problem:** Uses regex on the human-readable upgrade name to extract upgrade level. This is fragile: if an upgrade name format changes or does not follow the `LevelN` convention, the level is silently set to 0. The API provides stable upgrade IDs; a data-driven lookup table of `upgrade_id -> level` would be deterministic and not depend on string parsing.
- **API provides:** `upgrade_id` (uint32) — each specific upgrade level (e.g., TerranInfantryWeaponsLevel1 vs Level2 vs Level3) has its own distinct upgrade ID. A mapping from ID to level is unambiguous.

---

#### Finding 3 — Pattern C / Root of Confirmed Bug: Upgrade attribution via single observation

- **Lines:** 156–195 (the `extract()` method, specifically how it is called)
- **Pattern Type:** C (implicit attribution by assumption)
- **Code (in `extract()`, called from `StateExtractor.extract_observation()`):**
  ```python
  # In extract():
  raw_data = obs.observation.raw_data
  game_loop = obs.observation.game_loop
  # Get current upgrades from raw player data
  current_upgrades = set(raw_data.player.upgrade_ids)
  ```
  **Called from `state_extractor.py` lines 112–113:**
  ```python
  state['p1_upgrades'] = self.extract_upgrades(obs, player_id=1)
  state['p2_upgrades'] = self.extract_upgrades(obs, player_id=2)
  ```
- **Problem:** The `extract()` method unconditionally reads `raw_data.player.upgrade_ids` from whatever `obs` is passed in, without verifying that this observation is from the correct player's perspective. When both `extract_upgrades(obs, player_id=1)` and `extract_upgrades(obs, player_id=2)` are called with the **same single `obs`** (as happens in `extract_observation()`), both extractors read identical upgrade ID lists. This directly causes the Stimpack/Concussive Shells bug described in the Known Bug section above.
- **API provides:** `raw_data.player.upgrade_ids` is perspective-scoped — it only contains upgrades for the player whose perspective is active. To get correct per-player upgrade data, a separate observation must be made from each player's perspective. The observer mode pipeline already does this correctly; the single-observation path does not.

---

### wide_table_builder.py

**Path:** `src_new/extraction/wide_table_builder.py`
**Status:** Issues Found

#### Finding 4 — Pattern D: Schema lookup by filtering a list instead of direct field access

- **Lines:** 258–268 (`_get_unit_attr_suffixes_in_schema`)
- **Pattern Type:** D
- **Code:**
  ```python
  def _get_unit_attr_suffixes_in_schema(self, prefix: str, row: Dict[str, Any]) -> List[str]:
      suffixes = []
      all_possible = (
          UNIT_BASE_ATTRIBUTES
          + UNIT_SHIELD_ATTRIBUTES
          + UNIT_ENERGY_ATTRIBUTES
      )
      for suffix, _, _ in all_possible:
          col_name = f'{prefix}_{suffix}'
          if col_name in row:
              suffixes.append(suffix)
      return suffixes
  ```
- **Problem:** This iterates over all possible unit attribute suffixes (including shield and energy attributes that only apply to specific races) and tests membership in the row dict on every call. While not a direct API misuse, it is a filtering-based lookup applied at every game loop for every unit — when the applicable attributes for each unit were already determined during the schema scan (pass 1) and stored in `unit_extractor.unit_attributes`. The schema could expose a direct lookup from `unit_prefix -> set_of_applicable_suffixes` rather than re-filtering through all possibilities.
- **API provides:** `unit.shield_max > 0` directly determines whether a unit has shields (Protoss). `unit.energy_max > 0` directly determines whether a unit has energy. These are already correctly used in `UNIT_FIELD_CONFIG` conditions — the issue is that this determination is re-derived by checking row membership rather than using the already-computed `unit_attributes` set stored by the extractor.

---

#### Finding 5 — Pattern D: Same filtering-based lookup for buildings

- **Lines:** 270–291 (`_get_building_attr_suffixes_in_schema`)
- **Pattern Type:** D
- **Code:**
  ```python
  def _get_building_attr_suffixes_in_schema(self, prefix: str, row: Dict[str, Any]) -> List[str]:
      suffixes = []
      all_possible = (
          BUILDING_BASE_ATTRIBUTES
          + BUILDING_SHIELD_ATTRIBUTES
          + BUILDING_ENERGY_ATTRIBUTES
      )
      for suffix, _, _ in all_possible:
          col_name = f'{prefix}_{suffix}'
          if col_name in row:
              suffixes.append(suffix)
      return suffixes
  ```
- **Problem:** Same issue as Finding 4, applied to buildings. Per-building applicable attributes are already stored in `building_extractor.building_attributes` after the schema scan. This code re-derives them by filtering through all possible attribute names on every row write.
- **API provides:** `unit.shield_max > 0` and `unit.energy_max > 0` are the deterministic API fields already used in `BUILDING_FIELD_CONFIG` conditions. The work has already been done; this method just doesn't use the result that was already stored.

---

### create_unit_counts.py

**Path:** `src_new/data_processing/create_unit_counts.py`
**Status:** Issues Found

#### Finding 6 — Pattern E: Hardcoded name lists for entity classification (buildings, air units, production buildings)

- **Lines:** 47–87
- **Pattern Type:** E
- **Code:**
  ```python
  BUILDING_TYPES = {
      "commandcenter", "commandcenterflying", "orbitalcommand", "planetaryfortress",
      "supplydepot", "supplydepotlowered", "barracks", "barrackstechlab",
      # ... (Terran, Protoss, Zerg buildings, ~40 entries total)
  }

  AIR_UNIT_TYPES = {
      "banshee", "battlecruiser", "liberator", "medivac", "raven", "viking", "vikingfighter",
      "carrier", "oracle", "phoenix", "tempest", "voidray", "warpprism", "mothership",
      "broodlord", "corruptor", "mutalisk", "overlord", "overseer", "viper",
  }

  PRODUCTION_BUILDING_TYPES = {
      "barracks", "factory", "starport", "commandcenter", "orbitalcommand", "planetaryfortress",
      "gateway", "roboticsfacility", "stargate", "nexus",
      "hatchery", "lair", "hive",
  }
  ```
- **Problem:** These hardcoded name sets are used to classify entities (parsed from column names) as buildings, air units, or production buildings. This is a downstream post-processing step on already-extracted data — the entity type names come from column name strings like `p1_marine_001`, which were themselves derived from pysc2's `get_unit_type(unit_type_id).name`. Any unit type not listed in these sets will be misclassified silently: a Lurker Den, for example, appears as `lurkerden` in column names but only `"lurkerden"` is included in BUILDING_TYPES — a mismatch in casing or naming convention would silently miscategorize it. More broadly, new units added in SC2 patches will not be recognized until these lists are manually updated.
- **API provides:** The SC2 API provides `unit.unit_type` (a `uint32` unit type ID) and `RequestData(unit_type_id=True)` returns `UnitTypeData` for each unit type, which includes structured attributes. However, this data is not available at the post-processing stage where these files operate (they work on already-extracted parquet files). The root fix would be to extract and store whether each unit is a building/air-unit/production-building at extraction time (from API fields) rather than re-inferring from string names in post-processing.

---

#### Finding 7 — Pattern B: String-based entity classification via column name parsing

- **Lines:** 44–109 (specifically `parse_entity_columns` and its regex)
- **Pattern Type:** B
- **Code:**
  ```python
  ENTITY_COL_RE = re.compile(r"^(p[12])_p[12]_(.+?)_(\d+)_(.+)$")

  def parse_entity_columns(columns):
      entities = defaultdict(set)
      for col in columns:
          m = ENTITY_COL_RE.match(col)
          if m:
              player, entity_type, entity_id, attribute = m.groups()
              entities[(player, entity_type, entity_id)].add(attribute)
      return dict(entities)
  ```
  Then used as:
  ```python
  if p == player and etype not in BUILDING_TYPES:
      # treat as unit
  if p == player and etype in AIR_UNIT_TYPES:
      # treat as air unit
  ```
- **Problem:** The entity type classification is performed entirely through string matching on column names. The column name string (e.g., `marine`, `barracks`) is compared to hardcoded name sets to determine the entity's game classification. This is inherently fragile because: (1) the column names are derived from `pysc2_units.get_unit_type(id).name` and any change to that library's naming could break the match, (2) the hardcoded sets are incomplete (see Finding 6), and (3) there is no way to add entity metadata (e.g., `is_building`, `can_fly`) at this stage without extending the column naming convention.
- **API provides:** At extraction time, `unit.unit_type` (uint32) combined with `RequestData(unit_type_id=True)` from the SC2 API provides structured `UnitTypeData` including whether a unit is a building, whether it can fly, etc. This information should be embedded in the extracted data (e.g., as boolean flag columns or as a side-channel lookup table) rather than inferred from column name strings in post-processing.

---

### engineer_army_features.py

**Path:** `src_new/data_processing/engineer_army_features.py`
**Status:** Issues Found

#### Finding 8 — Pattern E: Hardcoded name lists for entity classification (buildings, workers, base structures)

- **Lines:** 50–81
- **Pattern Type:** E
- **Code:**
  ```python
  BUILDING_TYPES = {
      "commandcenter", "commandcenterflying", "orbitalcommand", ...
      # same ~40-entry set as in create_unit_counts.py
  }

  WORKER_TYPES = {"scv", "probe", "drone", "mule"}

  BASE_TYPES = {
      "commandcenter", "nexus", "hatchery", "lair", "hive",
      "commandcenterflying", "orbitalcommand", "planetaryfortress",
  }

  NON_ARMY_TYPES = BUILDING_TYPES | WORKER_TYPES
  ```
- **Problem:** Same root problem as Finding 6 — entity classification for army feature computation (which units to include in army clustering, which to exclude) is done via hardcoded string name sets matched against column name–derived entity type strings. The WORKER_TYPES set notably includes "mule" (a Terran spell-summoned unit) but would miss any Zerg-equivalent non-combat unit not in the list. BASE_TYPES only covers main base structures and would miss tech buildings for base position estimation.
- **API provides:** Same as Finding 6 — `unit.unit_type` at extraction time, with `UnitTypeData` from `RequestData`, provides structured unit classification that would not require hardcoded name lists.

---

#### Finding 9 — Pattern B: String-based entity classification via column name parsing (duplicate of create_unit_counts.py approach)

- **Lines:** 46–108 (same ENTITY_COL_RE pattern as create_unit_counts.py)
- **Pattern Type:** B
- **Code:**
  ```python
  ENTITY_COL_RE = re.compile(r"^(p[12])_p[12]_(.+?)_(\d+)_(.+)$")
  # ... used identically to create_unit_counts.py
  ```
- **Problem:** This file duplicates the same string-parsing approach from `create_unit_counts.py` for a different feature computation. Every concern raised in Finding 7 applies equally here. Additionally, the `find_base_positions()` function (lines 126–175) relies on finding entities with specific type names ("commandcenter", "nexus", "hatchery", etc.) to locate starting positions — if any of these names drift from the column name convention, base position detection silently fails and movement direction features default to "neutral".
- **API provides:** Same as Finding 7.

---

### schema_manager.py

**Path:** `src_new/extraction/schema_manager.py`
**Status:** Issues Found

#### Finding 10 — Pattern E / Other: Hardcoded "common upgrades" list that does not reflect actual player upgrades

- **Lines:** 400–420 (`_add_upgrade_columns`)
- **Pattern Type:** E
- **Code:**
  ```python
  def _add_upgrade_columns(self) -> None:
      """Add upgrade columns for both players."""
      # Common upgrades across all races
      common_upgrades = [
          'attack_level',
          'armor_level',
          'shield_level',
      ]

      for player_num in [1, 2]:
          for upgrade in common_upgrades:
              col_name = f'p{player_num}_upgrade_{upgrade}'
              # ...
  ```
- **Problem:** The upgrade schema is hardcoded to exactly three upgrades (`attack_level`, `armor_level`, `shield_level`) for every player, regardless of what upgrades were actually researched in the replay. This is a static, race-agnostic approximation. No Terran-specific upgrades (Stimpack, Combat Shield, Concussive Shells, etc.), no Protoss-specific upgrades (Blink, Charge, Storm, etc.), and no Zerg-specific upgrades (Burrow, Metabolic Boost, etc.) are represented. Furthermore, `wide_table_builder.add_upgrades_to_row()` only writes to these three hardcoded column names, meaning the rich `upgrades_data` dict from `UpgradeExtractor` (which contains all actual researched upgrades by name) is almost entirely discarded.
- **API provides:** `raw_data.player.upgrade_ids` returns the **complete list** of upgrade IDs for the observed player. Combined with `pysc2.lib.upgrades.Upgrades(upgrade_id).name`, every individual upgrade can be identified and stored. The schema should dynamically discover all upgrades that appear in a replay (similar to how it discovers unit and building types) rather than using a static three-entry list.

---

### utils/validation.py

**Path:** `src_new/utils/validation.py`
**Status:** Issues Found

#### Finding 11 — Pattern B: String matching on column names to classify columns by type

- **Lines:** 431–444 (`_check_column_types`)
- **Pattern Type:** B
- **Code:**
  ```python
  # Check economy columns (should be int64 or Int64)
  economy_cols = [col for col in df.columns if any(
      x in col for x in ['minerals', 'vespene', 'supply_', 'workers', 'idle_workers']
  )]

  for col in economy_cols:
      if df[col].dtype not in ['int64', 'Int64']:
          type_issues.append(f"{col} should be int64")

  # Check coordinate columns (should be float64)
  coord_cols = [col for col in df.columns if col.endswith(('_x', '_y', '_z'))]
  ```
- **Problem:** Column classification for type validation is done by string matching on column names rather than reading from the schema's dtype dictionary, which already has exact type information for each column. For example, the check `col.endswith(('_x', '_y', '_z'))` assumes coordinate columns always end in `_x`, `_y`, or `_z` — but this codebase uses `pos_(X,Y,Z)` as a single combined column, not separate `_x`, `_y`, `_z` columns. The coordinate check would never match any column and its type check silently passes on zero columns.
- **API provides:** The `SchemaManager.get_dtype(column_name)` method and `SchemaManager.dtypes` dict provide exact dtype for each column, derived from the schema definition. The validator should use `schema.get_dtype(col)` rather than inferring dtype from column name substrings.

---

#### Finding 12 — Pattern B + E: Hardcoded unit type names in validation

- **Lines:** 545–576 (`_check_unit_count_consistency`)
- **Pattern Type:** B + E
- **Code:**
  ```python
  common_units = ['marine', 'scv', 'zealot', 'probe', 'zergling', 'drone']

  for player in [1, 2]:
      for unit_type in common_units:
          count_col = f'p{player}_{unit_type}_count'

          if count_col not in df.columns:
              continue

          # Find all individual unit columns for this type
          unit_cols = [col for col in df.columns
                      if col.startswith(f'p{player}_{unit_type}_')
                      and col.endswith('_x')]  # Use _x as proxy for unit existence
  ```
- **Problem:** Two issues in one place. First, the validation only checks six hardcoded unit types — this is an incomplete spot check rather than a systematic validation. Any game that is primarily Protoss vs. Protoss (no marines, no scvs) would have all six count checks skip (because the columns don't exist) and vacuously pass. Second, the check uses `col.endswith('_x')` as a proxy for unit existence, but this codebase uses `pos_(X,Y,Z)` as a single combined position column — so the `_x` suffix match will find zero columns in any file produced by this pipeline, making the count consistency check completely inert (it always passes because `unit_cols` is always empty).
- **API provides:** The schema already knows which unit types exist in each replay (populated by `SchemaManager._build_columns_from_extractors()`). Validation should iterate over dynamically discovered unit types from the schema rather than checking a static list of six unit names.

---

## Cross-Cutting Observations

### 1. The upgrade_ids Perspective Problem Is Partially Fixed, Partially Remains

The observer mode pipeline correctly handles upgrade attribution by obtaining per-player observations. However, the schema pre-scan (`SchemaManager.build_schema_from_replay()`) still calls `extract_observation()` with a single player-1-perspective observation. During this scan, `p2_upgrades` will always reflect player 1's upgrade IDs. Since `_add_upgrade_columns()` only adds three hardcoded columns anyway (not dynamic upgrade columns), the practical impact on the schema is limited — but any code that inspects `p2_upgrades` data during the pre-scan scan pass will receive incorrect data.

### 2. The BUILDING_TYPES Hardcoded List Is Duplicated in Three Places

`BUILDING_TYPES` as a set of lowercase string names appears in:
- `src_new/data_processing/create_unit_counts.py`
- `src_new/data_processing/engineer_army_features.py`

`BUILDING_TYPES` as a set of integer unit type IDs appears in:
- `src_new/extractors/unit_extractor.py`
- `src_new/extractors/building_extractor.py`

These two representations are not guaranteed to be in sync. New building types (added in SC2 patches) need to be added to all four locations separately.

### 3. The Upgrade Schema Is Severely Underpowered

The three hardcoded upgrade columns (`p1_upgrade_attack_level`, `p1_upgrade_armor_level`, `p1_upgrade_shield_level`) represent fewer than 3% of the upgrades actually available in SC2. The `UpgradeExtractor` correctly tracks all upgrades by ID and name — but `WideTableBuilder.add_upgrades_to_row()` only maps three hardcoded key names and discards everything else. This means that research into Stimpack, Blink, Burrow, Charge, Combat Shield, Concussive Shells, and dozens of other upgrades is extracted but then silently dropped before writing to parquet.

---

## Verification

1. **File count:** Glob identified 32 .py files in `src_new/` (excluding `__pycache__`). The report documents all 32 files (6 with issues, 26 clean). **PASS**

2. **Stimpack/ConcussiveShells bug documented:** The Known Bug section describes the exact mechanism — single-observation legacy path causes both player extractors to read player 1's `upgrade_ids`. Finding 3 pinpoints the exact lines in `upgrade_extractor.py` and `state_extractor.py`. **PASS**

3. **API Reference documents fields for upgrades, units, and player identification:** The API Reference section documents `raw_data.player.upgrade_ids` (upgrade attribution), `unit.owner` (unit attribution), `unit.unit_type` (unit identification), and `player_info.race_actual` (race identification). **PASS**

4. **Summary table numbers internally consistent:** 32 total = 6 with issues + 26 clean. 12 findings span 6 files. **PASS**
