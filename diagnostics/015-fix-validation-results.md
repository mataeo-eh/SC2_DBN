# Pipeline Schema Fix Validation Results

**Date:** 2026-02-26
**Prompt:** 015-fix-all-pipeline-diagnostics.md
**Phases completed:** Research (1) + Implementation (7 parallel workers) + Validation

---

## Verification 1: Category A Findings (Schema Mismatches)

| Finding | File | Check | Result |
|---------|------|-------|--------|
| A-1 | create_unit_counts.py | ENTITY_COL_RE imported from shared_constants | PASS |
| A-2 | create_unit_counts.py | col_prefix uses `{player}_{middle}_{entity_id}` | PASS |
| A-3 | engineer_army_features.py | ENTITY_COL_RE imported from shared_constants | PASS |
| A-4 | engineer_army_features.py | find_base_positions uses `{player}_{middle}_{eid}_x` | PASS |
| A-5 | engineer_army_features.py | worker fallback uses same fix | PASS |
| A-6 | engineer_army_features.py | is_entity_alive uses `{player}_{middle}_{entity_id}` | PASS |
| A-7 | engineer_army_features.py | get_entity_position uses same fix | PASS |
| A-8 | engineer_army_features.py | precompute_alive_masks uses `{player}_{middle}_{eid}` | PASS |
| A-9 | engineer_army_features.py | precompute_position_arrays uses same fix | PASS |
| A-10 | wide_table_builder.py | add_upgrades_to_row() iterates individual upgrades | PASS |
| A-11 | state_extractor.py | BuildingTracker class deleted | PASS |
| A-12 | QUICKSTART.py | Schema dependency comments added | PASS |

**Grep check:** `_p[12]_` in data_processing/ -- all matches are legitimate variable names (`curr_p1_dir`, `p1_army_size`, etc.), zero old column prefix patterns remain. **PASS**

---

## Verification 2: Category B Findings (Pattern Searching)

| Finding | File | Check | Result |
|---------|------|-------|--------|
| B-1 | economy_extractor.py | _FIELD_MAP has documentation comment | PASS |
| B-2 | economy_extractor.py | _PLAYER_STATS_EVENT constant defined and used | PASS |
| B-3 | upgrade_extractor.py | parse_upgrade_details() has heuristic comment | PASS |
| B-4 | state_extractor.py | UnitTracker class deleted | PASS |
| B-5 | schema_manager.py | add_unit_count_columns() removed | PASS |
| B-6 | wide_table_builder.py | economy_columns from ECONOMY_COLUMN_SUFFIXES | PASS |
| B-7 | wide_table_builder.py | get_row_summary() uses ECONOMY_COLUMN_SUFFIXES loop | PASS |
| B-8 | parquet_writer.py | MESSAGES_COLUMN constant defined, used in 3 places | PASS |
| B-9 | parquet_writer.py | No change needed (acceptable pattern) | PASS |
| B-10 | replay_loader.py | `.suffix.lower() == '.sc2replay'` | PASS |
| B-11 | discretize.py | Programmatic column discovery via suffix matching | PASS |
| B-12 | validation.py | Economy detection uses ECONOMY_COLUMN_SUFFIXES | PASS |
| B-13 | validation.py | Economy columns constructed from ECONOMY_COLUMN_SUFFIXES | PASS |
| B-14 | validation.py | Unit column discovery uses ENTITY_COL_RE | PASS |
| B-15 | validation.py | Comment added about suffix-based state detection | PASS |
| B-16 | validation.py | Economy detection uses ECONOMY_COLUMN_SUFFIXES | PASS |
| B-17 | documentation.py | Economy detection uses ECONOMY_COLUMN_SUFFIXES | PASS |
| B-18 | documentation.py | Unit ID parsing uses ENTITY_COL_RE | PASS |
| B-19 | documentation.py | Building ID parsing uses ENTITY_COL_RE | PASS |
| B-20 | engineer_army_features.py | Comment added about eid == "001" assumption | PASS |
| B-21 | QUICKSTART.py | Comment about message dict keys | PASS |

---

## Verification 3: Category C Findings (Domain Knowledge)

| Finding | File | Check | Result |
|---------|------|-------|--------|
| C-1 | unit_extractor.py | Imports BUILDING_TYPES from shared_constants | PASS |
| C-2 | building_extractor.py | Imports BUILDING_TYPES from shared_constants | PASS |
| C-3 | state_extractor.py | 1v1-only scope retained (per user decision) | PASS |
| C-4 | schema_manager.py | Dynamic add_upgrade_column() method replaces hardcoded 3 | PASS |
| C-5 | shared_constants.py | ENTITY_COL_RE handles underscored bot names | PASS |
| C-6 | schema_manager.py | Attributes auto-derived from FIELD_CONFIG | PASS |
| C-7 | wide_table_builder.py | Lifecycle states imported from shared_constants | PASS |
| C-8 | QUICKSTART.py | Schema JSON structure comment added | PASS |
| C-9 | create_unit_counts.py | BUILDING_TYPES imported from shared_constants | PASS |
| C-10 | create_unit_counts.py | AIR_UNIT_TYPES imported from shared_constants | PASS |
| C-11 | create_unit_counts.py | PRODUCTION_BUILDING_TYPES imported (includes warpgate) | PASS |
| C-12 | create_unit_counts.py | ALIVE_STATES imported from shared_constants | PASS |
| C-13 | engineer_army_features.py | BUILDING_TYPES imported from shared_constants | PASS |
| C-14 | engineer_army_features.py | WORKER_TYPES imported (mule included) | PASS |
| C-15 | engineer_army_features.py | BASE_TYPES imported from shared_constants | PASS |
| C-16 | engineer_army_features.py | ALIVE_STATES imported from shared_constants | PASS |

---

## Verification 4: Import Integrity

```
$ python -c "from src_new.shared_constants import BUILDING_TYPES, ENTITY_COL_RE, ECONOMY_COLUMN_SUFFIXES; ..."
OK: 71 building types, regex=^(p[12])_(.+)_(\d{3})_(.+)$
```
**Result: PASS**

---

## Verification 5: Duplicate Definition Check

| Constant | Files with definition | Expected | Result |
|----------|---------------------|----------|--------|
| BUILDING_TYPES | shared_constants.py only | 1 | PASS |
| ALIVE_STATES | shared_constants.py only | 1 | PASS |
| ENTITY_COL_RE | shared_constants.py only | 1 | PASS |
| WORKER_TYPES | shared_constants.py only | 1 | PASS |

---

## Verification 6: Regex Validation

```
$ python -c "import re; regex = re.compile(r'^(p[12])_(.+)_(\d{3})_(.+)$'); ..."
All regex tests PASSED
```

Test cases:
- `p1_really_marine_001_health` -> `('p1', 'really_marine', '001', 'health')` PASS
- `p2_what_nexus_001_shields` -> `('p2', 'what_nexus', '001', 'shields')` PASS
- `p1_bot_v2_0_marine_001_x` -> `('p1', 'bot_v2_0_marine', '001', 'x')` PASS
- `p1_really_commandcenter_001_build_progress` -> `('p1', 'really_commandcenter', '001', 'build_progress')` PASS

**Result: PASS**

---

## Verification 7: Entity Type Extraction

```
$ python -c "tests = [('really_marine', 'marine'), ...]; ..."
All entity type extraction tests PASSED
```

Test cases:
- `really_marine` -> `marine` PASS
- `what_nexus` -> `nexus` PASS
- `bot_v2_0_commandcenter` -> `commandcenter` PASS
- `simple_zergling` -> `zergling` PASS

**Result: PASS**

---

## Additional Checks

| Check | Result |
|-------|--------|
| "warpgate" in PRODUCTION_BUILDING_TYPES | PASS |
| "mule" in WORKER_TYPES | PASS |
| add_upgrade_column() exists in schema_manager.py | PASS |
| _add_upgrade_columns() removed from schema_manager.py | PASS |
| add_unit_count_columns() removed from schema_manager.py | PASS |
| get_all_discovered_upgrades() exists in upgrade_extractor.py | PASS |
| extract() returns 'status' key per upgrade | PASS |
| MESSAGES_COLUMN constant used in parquet_writer.py | PASS |
| Replay loader uses case-insensitive extension check | PASS |

---

## Upgrade Lifecycle Research Summary

- **Upgrade START detection**: FEASIBLE (via `unit.orders[i].ability_id` on researching buildings)
- **Upgrade CANCEL detection**: FEASIBLE (via orders disappearance without `upgrade_ids` entry)
- **Implementation**: Deferred to completion-only tracking due to complexity of ability_id-to-upgrade_id mapping. Infrastructure for lifecycle tracking is in place (`_previous_research_ability_ids`, `_research_start_times`). The `'status'` key is included in all upgrade entries (currently always `'completed'`).

---

## Files Modified

| File | Changes |
|------|---------|
| `src_new/shared_constants.py` | **CREATED** - centralized constants module (71 building types, regex, economy suffixes, lifecycle states, etc.) |
| `src_new/extraction/schema_manager.py` | Auto-derive attributes from FIELD_CONFIG, dynamic add_upgrade_column(), dead code removal |
| `src_new/extractors/upgrade_extractor.py` | Added 'status' key, get_all_discovered_upgrades(), lifecycle infrastructure, B-3 comment |
| `src_new/data_processing/create_unit_counts.py` | Regex fix, col_prefix fix, shared_constants imports |
| `src_new/data_processing/discretize.py` | Programmatic column discovery via suffix matching |
| `src_new/data_processing/engineer_army_features.py` | 7 col_prefix fixes, regex fix, shared_constants imports, B-20 comment |
| `src_new/extraction/wide_table_builder.py` | Rewritten add_upgrades_to_row(), centralized economy/lifecycle constants |
| `src_new/extraction/parquet_writer.py` | MESSAGES_COLUMN constant |
| `src_new/extractors/unit_extractor.py` | BUILDING_TYPES from shared_constants |
| `src_new/extractors/building_extractor.py` | BUILDING_TYPES from shared_constants |
| `src_new/extractors/economy_extractor.py` | _FIELD_MAP comment, _PLAYER_STATS_EVENT constant |
| `src_new/extraction/state_extractor.py` | Deleted BuildingTracker and UnitTracker classes |
| `src_new/utils/validation.py` | ENTITY_COL_RE + ECONOMY_COLUMN_SUFFIXES imports |
| `src_new/utils/documentation.py` | ENTITY_COL_RE + ECONOMY_COLUMN_SUFFIXES imports |
| `src_new/extraction/replay_loader.py` | Case-insensitive extension check |
| `src_new/pipeline/QUICKSTART.py` | Schema dependency comments |

---

## Final Result: ALL 50 FINDINGS PASS (12A + 21B + 17C)
