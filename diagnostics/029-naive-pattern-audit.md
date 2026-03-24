# 029 - Naive Pattern Matching Audit

**Date:** 2026-03-23
**Scope:** All files in SC2-gamestate-extractor/src_new/ extraction pipeline
**Methodology:** Systematic file-by-file review against SC2 protobuf API (raw.proto, data.proto)

## Executive Summary

| Category       | Count | Description                                              |
|----------------|-------|----------------------------------------------------------|
| FIX-NOW        | 3     | Hardcoded heuristics where a programmatic API field exists |
| FIX-LATER      | 3     | Heuristics where a better approach likely exists but needs research |
| ACCEPTABLE     | 4     | Heuristics that are the best available approach            |
| ENHANCEMENT    | 8     | Missing data opportunities from available proto fields     |

**Overall assessment:** The pipeline has three significant instances of the same anti-pattern
that afflicted the inside-building detection: hardcoded frozensets of type names that duplicate
information already available programmatically from the SC2 API. The most impactful is
`BUILDING_TYPES`, which is a manually curated frozenset of ~65 building names used as the
primary building-vs-unit classifier throughout the pipeline. The SC2 API provides a
`UnitTypeData.attributes` field containing `Attribute.Structure` for exactly this purpose.
Similarly, `AIR_UNIT_TYPES` duplicates the `is_flying` proto field already extracted per-unit,
and `UNIT_CONTAINING_BUILDINGS` was the original instance of this anti-pattern (partially
addressed but still hardcoded).

The economy extraction via s2protocol and the upgrade extraction via perspective switching are
both acceptable workarounds for real observer-mode limitations in the SC2 engine.

---

## FIX-NOW Findings

### FN-1: BUILDING_TYPES frozenset duplicates `Attribute.Structure` from UnitTypeData

**Location:** `shared_constants.py` lines 33-165; consumed by `unit_extractor.py:is_building()`,
`building_extractor.py:is_building()`, `metadata_writer.py:_split_units_and_buildings()`,
`engineer_army_features.py` (via `NON_ARMY_TYPES`)

**Current approach:** A manually curated frozenset of ~65 lowercase building type name strings.
Every unit in every frame is checked against this set via string name lookup:
```python
def is_building(unit_type_id: int) -> bool:
    name = get_unit_type_name(unit_type_id).lower()
    return name in BUILDING_TYPES
```
This requires manually adding every new building for every SC2 patch, including morphed
variants, flying variants, add-on variants, and edge cases (creep tumors, uprooted crawlers).
The list already has historical bugs (ID collision comments in the file header about IDs 133,
138, 142).

**Better approach:** The SC2 API provides `UnitTypeData.attributes` which is a repeated field
of the `Attribute` enum. One of the enum values is `Attribute.Structure` (value 8). This is
the authoritative, engine-provided classification.

**How to implement:**
1. At pipeline startup (after `controller.start_replay()`), call `controller.data_raw()` which
   returns `ResponseData` containing `repeated UnitTypeData units`.
2. Build a `Set[int]` of unit_type_ids where `Attribute.Structure` is in `attributes`:
   ```python
   data = controller.data_raw()
   BUILDING_TYPE_IDS = frozenset(
       u.unit_id for u in data.units
       if data_pb2.Attribute.Structure in u.attributes
   )
   ```
3. Replace `is_building(unit_type_id)` with `unit_type_id in BUILDING_TYPE_IDS` -- a direct
   integer set lookup, no string conversion needed.
4. The `BUILDING_TYPES` frozenset of strings can be retained as a fallback or for
   post-extraction analysis (e.g., `metadata_writer.py` which parses column names), but the
   runtime extraction should use the API-derived set.

**Risk assessment:** LOW. The `data_raw()` call is already available on pysc2's
`RemoteController` and returns `UnitTypeData` with `attributes`. The only risk is that the
call must happen after `start_replay()` (controller must be in `in_game` or `in_replay`
status). The pipeline already has this lifecycle -- the call can be inserted between
`start_replay()` and the game loop.

**Impact:** HIGH. This is the single most pervasive hardcoded set in the pipeline. It is the
root classifier that determines whether every entity goes to `UnitExtractor` or
`BuildingExtractor`. An incorrect or incomplete set causes entities to be classified wrong
(units treated as buildings or vice versa), silently corrupting the output data.

---

### FN-2: AIR_UNIT_TYPES frozenset duplicates `is_flying` proto field

**Location:** `shared_constants.py` lines 178-228

**Current approach:** A manually curated frozenset of ~25 lowercase air unit type names.
Currently used by downstream `data_processing/` scripts and potentially by future army
composition analysis.

**Better approach:** The SC2 protobuf `Unit` message already has an `is_flying` field (bool,
field #20) which the pipeline *already extracts* per-unit in `UNIT_FIELD_CONFIG`:
```python
{
    'column_suffix': 'is_flying',
    'extract': lambda unit: unit.is_flying,
    'always': True,
    ...
}
```
So the pipeline already has per-unit, per-frame flying status. The static frozenset is
redundant and less accurate -- it cannot account for units that change flying status
mid-game (Vikings landing/lifting, Terran buildings lifting/landing, Phoenixes using
Graviton Beam).

Additionally, `UnitTypeData.attributes` contains `Attribute.Hover` for inherently airborne
unit types, providing a static classification if needed.

**How to implement:**
1. For per-frame analysis: use the already-extracted `is_flying` field from the unit proto
   (already done in UNIT_FIELD_CONFIG).
2. For static classification: build the set from `UnitTypeData.attributes` containing
   `Attribute.Hover` at pipeline startup.
3. Remove or deprecate the hardcoded `AIR_UNIT_TYPES` frozenset.

**Risk assessment:** LOW. The `is_flying` field is already extracted. The frozenset is
currently only used by downstream processing scripts, not by the core extraction loop.

**Impact:** MEDIUM. The frozenset is wrong for units that change flight state (Vikings,
lifted buildings). Using the per-frame `is_flying` field is strictly more correct.

---

### FN-3: UNIT_CONTAINING_BUILDINGS hardcoded compatibility map

**Location:** `shared_constants.py` lines 346-383

**Current approach:** A manually curated dict mapping building type names to frozensets of
compatible unit type names. This was the original instance of the anti-pattern (the one that
prompted this audit). While the inside-building detection logic was improved, the
compatibility map itself is still hardcoded.

**Better approach:** The SC2 protobuf `Unit` message provides:
- `cargo_space_max` (int32, field #26): maximum cargo capacity of a building/transport.
  Buildings with `cargo_space_max > 0` can contain units.
- `cargo_space_taken` (int32, field #25): current cargo used. When this increases, units
  entered.
- `passengers` (repeated `PassengerUnit`, field #24): the actual list of units inside,
  including their `tag`, `unit_type`, `health`, etc.

The `passengers` field is the definitive answer -- it tells you exactly which units are
inside which building, with no heuristic matching needed.

**How to implement:**
1. For buildings with `cargo_space_max > 0`, read the `passengers` repeated field.
2. Each `PassengerUnit` contains `tag` (uint64) and `unit_type` (uint32), which can be
   cross-referenced with the unit extractor's tag tracking.
3. This eliminates the need for:
   - The `UNIT_CONTAINING_BUILDINGS` compatibility map
   - The `INSIDE_BUILDING_DISTANCE_THRESHOLD` proximity check
   - The `last_known_positions` / `last_known_unit_type` tracking
   - The entire `resolve_hidden_units()` method's heuristic matching

**Risk assessment:** MEDIUM. The `passengers` field availability in observer mode needs
verification. In some observation modes, the `passengers` field may be empty for buildings
not owned by the observed player. Since the pipeline uses observer mode with
`disable_fog=True`, it likely has access, but this needs empirical testing.

**Impact:** HIGH. The current approach uses position-based proximity matching with a 5.0
game-unit distance threshold, which can produce false positives (unit near a bunker but not
inside it) and false negatives (unit entered from further away). The `passengers` field
would be 100% accurate.

---

## FIX-LATER Findings

### FL-1: WORKER_TYPES frozenset -- could be derived from UnitTypeData

**Location:** `shared_constants.py` lines 169-177

**Current approach:** Hardcoded frozenset: `{"scv", "probe", "drone", "mule"}`.

**What research is needed:** There is no explicit `is_worker` attribute in the SC2 protobuf.
However, workers could potentially be identified by:
- `UnitTypeData.food_required == 1.0` + `UnitTypeData.mineral_cost == 50` + no weapons (for
  SCV/Probe/Drone), but MULE is special (no cost, temporary).
- Querying `UnitTypeData.ability_id` for the build/gather abilities.
- Using the `UnitTypeData.attributes` set (workers are Biological + Light for Terran/Protoss,
  Biological for Zerg).

None of these are a clean single-field check. The hardcoded set is small (4 entries) and
unlikely to change across patches. This is LOW priority.

**Classification rationale:** The set is small, stable, and there's no clean programmatic
alternative.

---

### FL-2: PRODUCTION_BUILDING_TYPES frozenset -- could be partially derived

**Location:** `shared_constants.py` lines 234-298

**Current approach:** Hardcoded frozenset of ~40 production/research building names.

**What research is needed:** The SC2 `UnitTypeData` does not have an `is_production_building`
field. However, production buildings could potentially be identified by:
- Having `orders` with ability_ids that correspond to unit training or research abilities.
- Cross-referencing `UnitTypeData.ability_id` fields (what ability creates this building).
- Checking if the building type appears as a `tech_requirement` for any unit type.

This would require building a dependency graph from the `UnitTypeData` and `AbilityData`
responses, which is non-trivial but feasible. The current hardcoded set includes both
production buildings and research buildings, which would need separate detection logic.

**Classification rationale:** Feasible but requires significant research into the ability_id
mapping and cross-referencing multiple data tables.

---

### FL-3: BASE_TYPES frozenset -- could be derived from UnitTypeData

**Location:** `shared_constants.py` lines 183-200

**Current approach:** Hardcoded frozenset of 10 town-hall building names (CommandCenter +
morphs, Nexus, Hatchery + morphs, plus flying variants).

**What research is needed:** Town-hall buildings could potentially be identified by:
- `UnitTypeData.food_provided > 0` (town halls provide supply) -- but SupplyDepots and
  Pylons also provide supply.
- `UnitTypeData.food_provided >= 6` (town halls provide 6+ supply in Zerg, 15 for CC/Nexus).
- Checking for `assigned_harvesters` and `ideal_harvesters` fields being non-zero at runtime
  (these fields are specific to resource-gathering buildings).

The `ideal_harvesters` approach is promising -- this field is only populated for town halls
and gas buildings, and town halls have `ideal_harvesters` of 16+ while gas buildings have 3.

**Classification rationale:** A heuristic based on `ideal_harvesters` or `food_provided`
thresholds might work but could be fragile. Needs empirical testing.

---

## ACCEPTABLE Heuristics

### AH-1: Economy extraction via s2protocol instead of SC2 engine

**Location:** `extractors/economy_extractor.py` (entire module)

**What it does:** Parses the replay file directly using s2protocol to extract
`SPlayerStatsEvent` tracker events, bypassing the SC2 engine entirely.

**Why no better approach exists:** In observer mode (`observed_player_id=0`), the SC2
engine's `player_common` and `score_details` protobuf messages return all zeros. This is a
confirmed engine limitation, not a bug in the pipeline. The s2protocol tracker events are the
only source of economy data in observer mode. The tracker events are emitted at ~160
game-loop intervals, which is the maximum resolution available.

The only alternative would be to run the replay twice (once per player perspective), which
would double processing time and was the previous approach before observer mode was adopted.

---

### AH-2: Upgrade extraction via perspective switching

**Location:** `extraction/state_extractor.py` lines 162-169, `pipeline/extraction_pipeline.py`
lines 303-308

**What it does:** Switches observer perspective to each player before calling
`controller.observe()` to get that player's `raw_data.player.upgrade_ids`. Two observe calls
per game step.

**Why no better approach exists:** In observer mode, `raw_data.player.upgrade_ids` reflects
the currently observed player. There is no way to get both players' upgrades from a single
observation. The perspective-switching approach is the canonical solution used by all SC2 API
consumers. The overhead of two observe calls per step is minimal compared to replay stepping.

---

### AH-3: Building cancelled vs. destroyed heuristic (disappeared_tags)

**Location:** `extractors/building_extractor.py` lines 285-310

**What it does:** When a building disappears from `raw_data.units`:
- If the tag is in `dead_units` event: `destroyed`
- If the building was under construction and NOT in `dead_units`: `cancelled`
- If the building was completed and NOT in `dead_units`: `destroyed`

**Why no better approach exists:** The SC2 protobuf does not provide a separate
"cancelled" event. The `dead_units` event fires for destruction (combat death, self-destruct)
but NOT for cancellation. The only signal for cancellation is the building disappearing from
the unit list while still under construction, without appearing in `dead_units`. This
heuristic correctly exploits the difference between these two disappearance modes. There is
no proto field or event that explicitly indicates cancellation.

Note: There is a theoretical edge case where a building under construction is destroyed by
combat AND disappears from the unit list in the same frame but is not in `dead_units` (e.g.,
due to observer mode timing). This would be misclassified as "cancelled". However, this is
extremely unlikely and not addressable without engine changes.

---

### AH-4: Upgrade category classification via keyword matching

**Location:** `extractors/upgrade_extractor.py` lines 52-94 (`parse_upgrade_details()`)

**What it does:** Classifies upgrades into categories (weapons, armor, shields, movement,
energy, other) by keyword-matching against the upgrade name string. E.g., if the name
contains "weapon" or "attack", classify as "weapons".

**Why no better approach exists:** The SC2 protobuf `UpgradeData` message does not include a
category field. The upgrade name is the only identifying information beyond the integer ID.
The code already documents this limitation (the NOTE B-3 comment about ChitinousPlating being
miscategorized). A complete fix would require a hardcoded lookup table mapping all ~90+
upgrade names to categories, which would be equally fragile across patches. The keyword
matching covers ~95% of cases correctly, and the remaining edge cases (ChitinousPlating,
etc.) are documented.

---

## Enhancement Opportunities

### EN-1: `passengers` field -- passenger unit tracking

**API field:** `Unit.passengers` (repeated `PassengerUnit`, field #24)

**What it provides:** List of units inside a transport/building. Each `PassengerUnit` has:
`tag`, `unit_type`, `health`, `health_max`, `shield`, `shield_max`, `energy`, `energy_max`.

**Potential value:** HIGH. Would enable:
- Exact inside-building detection (replaces the heuristic in FN-3)
- Transport load tracking (Medivacs, WarpPrisms, Overlords)
- Bunker composition tracking (which units are garrisoned)
- Nydus worm usage tracking

Note: Also listed under FN-3 as the fix for the hardcoded compatibility map.

---

### EN-2: `buff_ids` field -- buff/debuff tracking

**API field:** `Unit.buff_ids` (repeated uint32, field #27)

**What it provides:** List of active buff/debuff IDs on a unit. Buffs include: Stimpack,
Guardian Shield, Fungal Growth, Parasitic Bomb, Blinding Cloud, Chronoboost, Inject Larva,
etc.

**Potential value:** HIGH. Buff tracking enables:
- Detecting Stimpack usage (micro decisions)
- Guardian Shield / defensive ability usage
- Chronoboost / Inject Larva tracking (macro efficiency)
- Parasitic Bomb / Fungal Growth tracking (spellcaster impact)

Currently not extracted at all.

---

### EN-3: `buff_duration_remain` / `buff_duration_max` fields

**API fields:** `Unit.buff_duration_remain` (int32, #43), `Unit.buff_duration_max` (int32, #44)

**What it provides:** Remaining and maximum duration of the current buff/debuff.

**Potential value:** MEDIUM. Combined with `buff_ids`, enables tracking buff uptime and
timing precision.

---

### EN-4: `rally_targets` field -- rally point tracking

**API field:** `Unit.rally_targets` (repeated `RallyTarget`, field #45)

**What it provides:** Rally point(s) for production buildings. Each `RallyTarget` has a
`point` (always filled) and optional `tag` (if rallied to a unit).

**Potential value:** MEDIUM. Rally point tracking reveals:
- Where newly produced units will go (proxy for player intent)
- Whether rally is set to a unit (aggressive rally to army) vs. position (defensive rally)

Currently not extracted at all.

---

### EN-5: `assigned_harvesters` / `ideal_harvesters` fields

**API fields:** `Unit.assigned_harvesters` (int32, #28), `Unit.ideal_harvesters` (int32, #29)

**What it provides:** Number of workers mining at this building vs. the ideal number.

**Potential value:** MEDIUM. Enables:
- Mining efficiency calculation (assigned / ideal ratio)
- Over/under-saturation detection per base
- Worker distribution analysis

Currently not extracted at all.

---

### EN-6: `engaged_target_tag` field

**API field:** `Unit.engaged_target_tag` (uint64, field #34)

**What it provides:** Tag of the unit this unit is currently attacking/targeting.

**Potential value:** MEDIUM. Enables:
- Combat engagement mapping (who is fighting whom)
- Focus-fire detection (multiple units targeting the same enemy)
- Target priority analysis

Currently not extracted at all.

---

### EN-7: `detect_range` / `radar_range` fields

**API fields:** `Unit.detect_range` (float, #31), `Unit.radar_range` (float, #32)

**What it provides:** Detection radius (for detector units like Observers, Overseers,
Ravens) and radar/sensor range.

**Potential value:** LOW. Mostly static per unit type, but could reveal upgrade effects
or ability activations.

---

### EN-8: `is_powered` / `is_active` / `cloak` / `add_on_tag` / `display_type` fields

**API fields:**
- `Unit.is_powered` (bool, #35) -- whether a Protoss building is in a pylon power field
- `Unit.is_active` (bool, #39) -- whether the unit is currently active
- `Unit.cloak` (CloakState enum, #10) -- cloaking state (NotCloaked, Cloaked, CloakedDetected)
- `Unit.add_on_tag` (uint64, #23) -- tag of attached add-on (TechLab/Reactor)
- `Unit.display_type` (DisplayType enum, #1) -- Visible, Snapshot, Hidden, Placeholder

**What they provide:** Various unit state flags not currently extracted.

**Potential value:** MEDIUM collectively.
- `is_powered`: Protoss building functionality (unpowered buildings don't work)
- `cloak`: Cloaked unit tracking (Banshees, Dark Templar, Observers)
- `add_on_tag`: Tech Lab / Reactor attachment tracking (which production building has which
  add-on, important for Terran build orders)
- `display_type`: Could help distinguish real units from snapshots/placeholders

---

## Recommended Action Plan

### Priority 1: Quick Wins (Low Risk, High Impact)

1. **FN-1: Replace BUILDING_TYPES with API-derived set**
   - Call `controller.data_raw()` at pipeline startup
   - Build `BUILDING_TYPE_IDS: frozenset[int]` from `Attribute.Structure`
   - Replace `is_building()` to use integer ID lookup
   - Keep string frozenset as fallback for post-extraction tools
   - Estimated effort: 2-3 hours
   - Files to modify: `shared_constants.py`, `unit_extractor.py`, `building_extractor.py`,
     `extraction_pipeline.py` (to pass data to extractors)

2. **FN-2: Deprecate AIR_UNIT_TYPES in favor of `is_flying` proto field**
   - The field is already extracted per-unit per-frame
   - Update downstream consumers to use the per-frame field
   - Remove or mark the frozenset as deprecated
   - Estimated effort: 1 hour
   - Files to modify: `shared_constants.py`, `data_processing/engineer_army_features.py`

### Priority 2: Research Required (Medium Risk, High Impact)

3. **FN-3: Replace UNIT_CONTAINING_BUILDINGS with `passengers` field**
   - First: verify `passengers` field is populated in observer mode (empirical test)
   - If populated: refactor `resolve_hidden_units()` to read `passengers` directly
   - If not populated: document the limitation and keep the heuristic
   - Estimated effort: 4-6 hours (including testing)
   - Files to modify: `unit_extractor.py`, `shared_constants.py`

4. **EN-1 + EN-2: Extract `passengers` and `buff_ids`**
   - Add to UNIT_FIELD_CONFIG / BUILDING_FIELD_CONFIG
   - Design schema representation (lists need serialization strategy)
   - Estimated effort: 4-6 hours

### Priority 3: Deferred (Low Risk, Medium Value)

5. **FL-1/FL-2/FL-3: Derive remaining type sets from API** -- low priority, current sets work
6. **EN-3 through EN-8: Extract additional proto fields** -- add as needed by downstream
   analysis requirements

---

## Verification Checklist

| # | Check | Result | Status |
|---|-------|--------|--------|
| 1 | Audit document exists at `./diagnostics/029-naive-pattern-audit.md` | File created | PASS |
| 2 | `unit_extractor.py` examined | Full 815-line review: UNIT_FIELD_CONFIG, is_building(), resolve_hidden_units(), lifecycle logic | PASS |
| 3 | `building_extractor.py` examined | Full 547-line review: BUILDING_FIELD_CONFIG, is_building(), disappeared_tags heuristic | PASS |
| 4 | `economy_extractor.py` examined | Full 247-line review: s2protocol parsing, SPlayerStatsEvent extraction | PASS |
| 5 | `upgrade_extractor.py` examined | Full 405-line review: parse_upgrade_details() keyword matching, ability_id mapping gap | PASS |
| 6 | All extraction layer files examined | state_extractor.py (307 lines), schema_manager.py (571 lines), wide_table_builder.py (524 lines), parquet_writer.py (443 lines), metadata_writer.py (404 lines), replay_loader.py (494 lines) | PASS |
| 7 | `shared_constants.py` examined for all hardcoded type sets | Full 484-line review: BUILDING_TYPES, WORKER_TYPES, BASE_TYPES, AIR_UNIT_TYPES, PRODUCTION_BUILDING_TYPES, UNIT_CONTAINING_BUILDINGS, all lifecycle sets, ENTITY_COL_RE | PASS |
| 8 | Every finding has a clear classification | 3 FIX-NOW, 3 FIX-LATER, 4 ACCEPTABLE, 8 ENHANCEMENT | PASS |
| 9 | FIX-NOW findings include specific API field names | FN-1: `Attribute.Structure`, FN-2: `is_flying` + `Attribute.Hover`, FN-3: `passengers` | PASS |
| 10 | Pipeline layer files examined | extraction_pipeline.py (510 lines), game_loop_iterator.py (189 lines), pipeline/replay_loader.py (326 lines) | PASS |
| 11 | Data processing files examined for downstream usage | engineer_army_features.py (983 lines): uses NON_ARMY_TYPES, BUILDING_TYPES, WORKER_TYPES, BASE_TYPES | PASS |
| 12 | Research document checked | `./research/027-sc2-cargo-api-research.md` does NOT exist | PASS |
