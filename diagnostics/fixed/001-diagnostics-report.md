# SC2 Pipeline Diagnostics Report

## Executive Summary

Three reported bugs in the SC2 replay data parsing pipeline (src_new/) were investigated by four parallel investigation agents. **Two of three bugs are confirmed**, and one is denied:

1. **Lifecycle Column Handling** - **CONFIRMED**: Buildings have 5 separate lifecycle columns (status, progress, started_loop, completed_loop, destroyed_loop) per building, and units have a separate `state` column. These should be embedded into existing attribute columns rather than being standalone columns.
2. **Unit ID Persistence** - **NOT A BUG**: The ID system is correctly designed. Counters only increment, tag-to-ID mappings are never removed mid-replay, and `reset_frame_state()` preserves mappings between Pass 1 and Pass 2. No code path exists for ID reuse.
3. **Attribute Column Bloat** - **CONFIRMED**: All units and buildings unconditionally receive shields, shields_max, energy, and energy_max columns regardless of race or unit type. Terran marines get shield columns, non-caster units get energy columns.

---

## Bug 1: Lifecycle Column Handling

### Status: CONFIRMED

### Current Behavior

**Units** get 1 lifecycle column each:
- `p{player}_{bot}_{type}_{num}_state` (string: 'built'/'existing'/'killed')

**Buildings** get 5 lifecycle columns each:
- `p{player}_{bot}_{type}_{num}_status` (string: 'started'/'building'/'completed'/'destroyed')
- `p{player}_{bot}_{type}_{num}_progress` (int64: 0-100)
- `p{player}_{bot}_{type}_{num}_started_loop` (int64 or NaN)
- `p{player}_{bot}_{type}_{num}_completed_loop` (int64 or NaN)
- `p{player}_{bot}_{type}_{num}_destroyed_loop` (int64 or NaN)

**Impact**: For a game with 100 units and 20 buildings, that's 200 lifecycle-only columns (100 unit state + 100 building lifecycle).

### Root Cause

**Schema creation** (`schema_manager.py`):
- `add_unit_columns()` (lines 196-239): Hardcoded `('state', 'string', ...)` in column list
- `add_building_columns()` (lines 241-281): Hardcoded all 5 lifecycle tuples in column list

**Data extraction** (`building_extractor.py`):
- `extract()` (lines 267-307): Returns `started_loop`, `completed_loop`, `destroyed_loop` as separate fields
- `_determine_state()` (lines 375-400): Computes state from build_progress

**Row writing** (`wide_table_builder.py`):
- `add_unit_to_row()` (lines 129-173): Writes state as a separate column; killed units ONLY set state='killed', all other attrs are NaN
- `add_building_to_row()` (lines 174-206): Writes all 5 lifecycle fields as separate columns

### Files Affected

| File | Functions |
|------|-----------|
| `src_new/extraction/schema_manager.py` | `add_unit_columns()`, `add_building_columns()` |
| `src_new/extraction/wide_table_builder.py` | `add_unit_to_row()`, `add_building_to_row()` |
| `src_new/extractors/unit_extractor.py` | `extract()`, `_determine_state()` |
| `src_new/extractors/building_extractor.py` | `extract()`, `_determine_state()` |

### Recommended Fix Approach

Embed lifecycle state into existing attribute columns using conventions:
- **Killed/Destroyed**: All attribute columns become NaN (already happens for units). The absence of data IS the signal.
- **build_progress**: Already exists as an attribute. Value < 1.0 implies "building/started". No separate status column needed.
- **Timestamps** (started_loop, completed_loop, destroyed_loop): These are per-entity metadata, not per-frame data. Consider storing them in a separate entity metadata table or encoding them differently.

### Edge Cases
- **Cancelled buildings**: Cannot distinguish from destroyed (API limitation). Both result in disappearance.
- **Units that never complete**: Morphing eggs/units with build_progress < 1.0 that get cancelled.
- **Killed units have NO attribute data**: Only state='killed' is set; position/health from previous frame is lost.

---

## Bug 2: Unit ID Persistence

### Status: NOT A BUG

### Current Behavior

The ID system works correctly:
1. `tag_to_readable_id` (Dict[int, str]) maps SC2 tags to readable IDs like "p1_marine_001"
2. `unit_type_counters` (Dict[int, int]) tracks the next number per unit type
3. Assignment only happens when `tag not in self.tag_to_readable_id` (write-once)
4. Counters only ever increment (`+= 1`), never decrement or reset mid-replay

### Safeguards That Prevent Reuse

| Safeguard | Location |
|-----------|----------|
| Persistent mapping: `tag_to_readable_id` never cleared mid-replay | `unit_extractor.py:337-343` |
| Monotonic counters: only increment, never decrement | `unit_extractor.py:273-277` |
| Tag-based lookup: assignment only for new tags | `unit_extractor.py:181-183` |
| Write-once mapping: once set, never overwritten | `unit_extractor.py:183` |
| Cross-pass preservation: `reset_frame_state()` keeps mappings | `unit_extractor.py:337-343` |

### What Actually Happens When a Unit Dies

1. Unit with tag 1001 dies (say "p1_probe_001")
2. Tag 1001 removed from `current_tags` set
3. Mapping `1001 → "p1_probe_001"` **remains** in `tag_to_readable_id`
4. Next probe gets a **new SC2 tag** (e.g., 1002)
5. New mapping: `1002 → "p1_probe_002"` (counter was already at 2)

### Morphed Units
When a unit morphs (e.g., Zergling → Baneling), SC2 assigns a **new tag**. The old mapping persists harmlessly; the new tag gets a new readable_id via the incrementing counter.

---

## Bug 3: Attribute Column Bloat

### Status: CONFIRMED

### Current Behavior

ALL units and buildings receive these columns regardless of race or type:
- `shields` / `shields_max` (always extracted)
- `energy` / `energy_max` (always extracted)
- `shield_upgrade_level` (always extracted)

A Terran Marine gets: `p1_marine_001_shields`, `p1_marine_001_shields_max`, `p1_marine_001_energy`, `p1_marine_001_energy_max` — all filled with `0.0`.

### Root Cause

**Extractors** unconditionally extract all attributes:
- `unit_extractor.py` lines 205-208: `'shields': unit.shield, 'shields_max': unit.shield_max, 'energy': unit.energy, 'energy_max': unit.energy_max`
- `building_extractor.py` lines 281-284: Same unconditional extraction

**Schema Manager** uses hardcoded column lists:
- `schema_manager.py` lines 211-221: Always includes shields/energy columns

**Wide Table Builder** writes all hardcoded attributes:
- `wide_table_builder.py` lines 161-167: Always writes shields/energy

### Files Affected

| File | Functions |
|------|-----------|
| `src_new/extractors/unit_extractor.py` | `extract()` |
| `src_new/extractors/building_extractor.py` | `extract()` |
| `src_new/extraction/schema_manager.py` | `add_unit_columns()`, `add_building_columns()` |
| `src_new/extraction/wide_table_builder.py` | `add_unit_to_row()`, `add_building_to_row()` |

### Recommended Fix Approach

**Shields** — Conditional on race (Protoss only):
- Detection: `unit.shield_max > 0` (all Protoss units have shields, no other race does)
- Only include shields/shields_max columns for Protoss units

**Energy** — Conditional on unit type (casters only):
- Detection: `unit.energy_max > 0` (reliable across all races)
- Energy units: Ghost, Raven, Medivac, Banshee, Battlecruiser (Terran); Sentry, High Templar, Oracle, Phoenix, Mothership (Protoss); Queen, Infestor, Viper (Zerg)
- Energy buildings: Orbital Command, Nexus, Shield Battery

**Implementation**: Conditionally include attributes in the extractor data dict, then have schema_manager build columns based on what the extractor actually provides.

---

## SC2 API Reference

### Unit Lifecycle States

| State | Detection Method | build_progress |
|-------|-----------------|----------------|
| Queued (placeholder) | Requires `show_placeholders=True` | N/A |
| Started | New tag appears, `build_progress == 0.0` | 0.0 |
| Building | `0.0 < build_progress < 1.0` | 0.0–1.0 |
| Completed | `build_progress >= 1.0` | 1.0 |
| Destroyed | Tag in `raw_data.event.dead_units` OR tag disappears | N/A |
| Cancelled | Tag disappears, NOT in dead_units, was under construction | N/A (heuristic) |

**Key API fields:**
- `unit.build_progress`: float 0.0–1.0
- `raw_data.event.dead_units`: list of tags that died this frame
- No explicit `is_ready` property — check `build_progress >= 1.0`

### Attribute Detection

| Attribute | Detection | Notes |
|-----------|-----------|-------|
| Has shields | `unit.shield_max > 0` | All Protoss, no other race |
| Has energy | `unit.energy_max > 0` | Casters only, all races |
| Race | Infer from `unit.shield_max > 0` (Protoss) or unit_type_id ranges | No direct `unit.race` field |

### Edge Cases

| Case | Behavior |
|------|----------|
| **Morphed units (tag persists)** | Hatchery→Lair, Gateway→WarpGate: same tag, unit_type changes, build_progress resets |
| **Morphed units (new tag)** | Larva→unit, Drone→building, HT+HT→Archon: original dies, new tag appears |
| **Hallucinations** | `unit.is_hallucination = True`, behave like normal units |
| **Loaded units** | Disappear from observation (NOT in dead_units), reappear on unload |
| **Burrowed units** | Remain in observation with `is_burrowed = True` |
| **Lifted buildings** | Same tag, `is_flying = True`, position changes |
| **Cancelled vs destroyed** | API cannot distinguish — both result in disappearance. Heuristic: no damage taken + under construction = likely cancelled |

---

## Implementation Dependencies

### Recommended Fix Order

1. **Bug 3 (Attribute Bloat) — Fix FIRST**
   - Simpler change: add conditional logic to extractors
   - No architectural changes needed
   - Reduces column count immediately

2. **Bug 1 (Lifecycle Columns) — Fix SECOND**
   - More complex: requires rethinking how state is represented
   - Depends on understanding which attributes exist per unit (informed by Bug 3 fix)
   - Building timestamp columns need a design decision (drop, move to metadata, or keep)

### Dependencies Between Bugs
- Bug 3 fix informs Bug 1 fix: once attributes are conditional, the "which columns exist" logic is already dynamic, making lifecycle embedding easier
- Bug 2 is not a bug, no fix needed

---

## Additional Findings

1. **Killed units lose all attribute data**: When a unit dies, only `state='killed'` is recorded. Last known position, health, etc. from the previous frame is lost. This may be worth addressing — recording last-known values on the death frame.

2. **Building timestamps (started_loop, completed_loop, destroyed_loop)**: `started_loop` is not currently tracked (always None per investigation). Only `completed_loop` and `destroyed_loop` are populated. If lifecycle columns are removed, these timestamps need an alternative storage mechanism.

3. **No cancellation detection**: The pipeline cannot distinguish cancelled buildings from destroyed buildings. Both appear as the unit disappearing. This is an API limitation, not a code bug.

4. **Loaded unit false positives**: Units loaded into transports disappear from observations without appearing in `dead_units`. The current code may incorrectly mark these as "killed" via tag disappearance detection, though the `dead_units` event check provides some protection.
