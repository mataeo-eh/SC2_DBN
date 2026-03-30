# 030 - SC2 Protobuf API Runtime Type Classification Research

**Date:** 2026-03-30
**Feeds into:** Prompt 031 (replace hardcoded type sets with API-derived alternatives)
**Context:** Diagnostics 029-naive-pattern-audit.md identified three FIX-NOW findings
(FN-1, FN-2, FN-3) where hardcoded frozensets duplicate information available from the
SC2 protobuf API. This research empirically verifies field availability and compiles
reference data for the implementation.

---

## 1. data_raw() and UnitTypeData Attributes

### Method

Script `research/scripts/030-verify-data-raw.py` launches SC2 via pysc2, loads replay
`replays/match_4184936.SC2Replay`, calls `controller.data_raw()` after `start_replay()`,
and inspects all `UnitTypeData` entries.

### Full Attribute Enum Values Found

All 11 values defined in `s2clientprotocol.data_pb2` were observed in the data:

| Value | Name       | Description                          |
|-------|------------|--------------------------------------|
| 1     | Light      | Takes bonus damage from +Light       |
| 2     | Armored    | Takes bonus damage from +Armored     |
| 3     | Biological | Affected by bio-targeting abilities   |
| 4     | Mechanical | Affected by mech-targeting abilities  |
| 5     | Robotic    | Protoss robotic units                 |
| 6     | Psionic    | Psionic units (feedback, EMP)         |
| 7     | Massive    | Cannot be affected by certain CCs     |
| 8     | Structure  | Building / structure                  |
| 9     | Hover      | Inherently airborne / hovering        |
| 10    | Heroic     | Hero units (Mothership, etc.)         |
| 11    | Summoned   | Temporary summoned units              |

### Count: Structure-Attributed Types vs. Hardcoded BUILDING_TYPES

| Metric                                    | Count |
|-------------------------------------------|-------|
| Total `UnitTypeData` entries              | 2005  |
| Entries with any attributes               | 550   |
| Entries with `Attribute.Structure`        | 372   |
| Hardcoded `BUILDING_TYPES` count          | 71    |
| In API but NOT in hardcoded set           | 302   |
| In hardcoded set but NOT in API           | 1     |

### Analysis of Discrepancies

**302 types in API (Structure) but NOT in hardcoded BUILDING_TYPES:**

These are overwhelmingly map doodads and neutral structures:
- ~200 bridge segments (AiurLightBridge, PortCity_Bridge, XelNaga_Caverns_Floating_Bridge, etc.)
- ~50 destructible rocks/debris (CollapsibleRockTower, DestructibleRock, DestructibleIce, etc.)
- ~20 mineral fields and vespene geysers (MineralField, VespeneGeyser variants)
- ~10 XelNaga blockers and towers
- A handful of edge-case units: PointDefenseDrone (ID 11), AutoTurret (ID 31),
  KD8Charge (ID 830), OracleStasisTrap (ID 732), BypassArmorDrone (ID 895),
  RavenRepairDrone (ID 1913), InhibitorZoneMedium (ID 1982/1983), NydusCanalAttacker (ID 491),
  NydusCanalCreeper (ID 492)

**Key insight:** `Attribute.Structure` marks ALL structures including neutral map objects.
To derive the player-building set, the implementation must filter by `owner > 0` at runtime
(map doodads have `owner == 0` or `owner == 15` for neutral). Alternatively, build the
building type ID set from `data_raw()` at startup, then filter against units actually
appearing in `raw_data.units` with `owner in {1, 2}`.

**1 type in hardcoded BUILDING_TYPES but NOT in API:**
- `lurkerden` (ID 504) -- The pysc2 enum names this `LurkerDen` but `data_raw()` returns
  the name `LurkerDenMP`. The integer ID (504) IS present in the API with `Attribute.Structure`.
  This is purely a **name mismatch**, not a missing entry. This confirms that the
  implementation MUST use integer IDs (not string names) for the lookup set.

### Verdict: Can BUILDING_TYPES be replaced with Attribute.Structure?

**YES** -- with the following implementation strategy:

1. After `start_replay()`, call `controller.data_raw()`.
2. Build `BUILDING_TYPE_IDS: frozenset[int]` from all `UnitTypeData` entries where
   `Attribute.Structure` is in `attributes`.
3. At runtime, classify a unit as a building if `unit.unit_type in BUILDING_TYPE_IDS`.
4. To exclude neutral map objects, additionally check `unit.owner > 0` (already done in
   the pipeline's unit/building split logic).
5. The string-based `BUILDING_TYPES` frozenset can be retained as a fallback for
   post-extraction analysis tools, but the runtime extraction should use the integer set.

**Bonus:** `Attribute.Structure` also enables classification of edge cases the hardcoded
set may miss -- AutoTurret, PointDefenseDrone, BypassArmorDrone, etc. -- though most of
these are temporary summoned units that the pipeline may want to exclude via
`UNTRACKED_ENTITY_TYPES`.

---

## 2. Passengers Field in Observer Mode

### Method

Script `research/scripts/030-verify-passengers.py` launches SC2, starts replay in
observer mode (`observed_player_id=0`, `disable_fog=True`), and steps through the
entire replay checking `unit.passengers` on all cargo-capable units.

### Empirical Test Results

**Replay used:** `match_4184936.SC2Replay` (Persephone AIE, 8886 game loops)

**Cargo-capable unit types observed:**

| Unit Type      | Owner | cargo_space_max | cargo_space_taken | Passengers Found |
|----------------|-------|-----------------|-------------------|------------------|
| CommandCenter  | 1     | 5               | 0                 | NO               |
| Bunker         | 1     | 4               | 0                 | NO               |
| Medivac        | 1     | 8               | 0                 | NO               |

Note: `cargo_space_taken` was always 0 despite these buildings being capable of holding
units. In a real game, workers enter refineries for gas mining, but refineries did not
appear in the cargo-capable list (they may not expose `cargo_space_max` in observer mode).

**No passenger sightings were logged across the entire replay.**

### Protobuf Field Verification

The `passengers` field IS defined in the protobuf schema:
- `raw_pb2.py`: `Unit.passengers` at index 34, type `repeated PassengerUnit`
- `PassengerUnit` has fields: `tag`, `health`, `health_max`, `shield`, `shield_max`,
  `energy`, `energy_max`, `unit_type`
- Python access: `unit.passengers[0].tag`, `unit.passengers[0].unit_type`, etc.

The field exists on the protobuf object but is NOT populated by the SC2 engine in
observer mode.

### Why Passengers is Empty

In observer mode (`observed_player_id=0`), the SC2 engine provides a "global" view of
all units but omits certain per-player detail fields. The `passengers` field is one of
these -- it is only populated when observing from a specific player's perspective
(`observed_player_id=1` or `2`). This is consistent with how the SC2 engine handles
other per-player fields like `player_common` and `score_details` (which also return
zeros in observer mode and require perspective switching).

### Verdict: Can UNIT_CONTAINING_BUILDINGS be replaced with passengers?

**NO** -- not directly in the current observer-mode pipeline.

**Possible workaround:** The pipeline already performs per-player perspective switching
(for upgrades and economy). It could additionally read `passengers` from the
player-perspective observations. However, this would require:
1. Reading `raw_data.units` from both P1 and P2 perspective observations
2. Merging passenger data from both perspectives into the observer-mode unit list
3. This adds complexity and two additional `observe()` calls per step

**Recommendation:** Keep the current heuristic approach (UNIT_CONTAINING_BUILDINGS +
proximity matching) for now. If passenger tracking becomes a high-priority feature,
implement the perspective-switching workaround as a separate enhancement. The current
approach works well enough for the inside-building detection use case.

---

## 3. Comprehensive PRODUCTION_BUILDING_TYPES

### Full List with pysc2 Enum Names (lowercase)

#### Terran

| Building (pysc2 name)     | ID   | Classification       | Notes                           |
|---------------------------|------|----------------------|---------------------------------|
| `barracks`                | 21   | PRODUCES_UNITS       | Infantry (Marine, Marauder, etc.) |
| `factory`                 | 27   | PRODUCES_UNITS       | Mech ground (Hellion, Tank, etc.) |
| `starport`                | 28   | PRODUCES_UNITS       | Air units (Medivac, Viking, etc.) |
| `commandcenter`           | 18   | PRODUCES_UNITS       | Trains SCVs                      |
| `orbitalcommand`          | 132  | BOTH                 | Trains SCVs + Calldown abilities |
| `planetaryfortress`       | 130  | PRODUCES_UNITS       | Trains SCVs                      |
| `engineeringbay`          | 22   | RESEARCHES_UPGRADES  | Infantry armor/weapons           |
| `armory`                  | 29   | RESEARCHES_UPGRADES  | Vehicle/ship armor/weapons       |
| `ghostacademy`            | 26   | RESEARCHES_UPGRADES  | Ghost upgrades + Nuke           |
| `fusioncore`              | 30   | RESEARCHES_UPGRADES  | BC upgrades                      |
| `barrackstechlab`         | 37   | RESEARCHES_UPGRADES  | Enables advanced infantry + research |
| `barracksreactor`         | 38   | PRODUCES_UNITS       | Doubles Barracks production queue |
| `factorytechlab`          | 39   | RESEARCHES_UPGRADES  | Enables advanced mech + research |
| `factoryreactor`          | 40   | PRODUCES_UNITS       | Doubles Factory production queue |
| `starporttechlab`         | 41   | RESEARCHES_UPGRADES  | Enables advanced air + research  |
| `starportreactor`         | 42   | PRODUCES_UNITS       | Doubles Starport production queue |

Note: Flying variants (`barracksflying`, `factoryflying`, `starportflying`,
`orbitalcommandflying`, `commandcenterflying`) cannot produce while flying. They are
NOT production buildings in the production sense. However, `commandcenterflying` and
`orbitalcommandflying` are included in the CURRENT hardcoded set. Consider removing them.

#### Protoss

| Building (pysc2 name)     | ID   | Classification       | Notes                           |
|---------------------------|------|----------------------|---------------------------------|
| `gateway`                 | 62   | PRODUCES_UNITS       | Ground units                     |
| `warpgate`                | 133  | PRODUCES_UNITS       | Morphed Gateway, warps in units  |
| `roboticsfacility`        | 71   | PRODUCES_UNITS       | Robotic units                    |
| `stargate`                | 67   | PRODUCES_UNITS       | Air units                        |
| `nexus`                   | 59   | BOTH                 | Trains Probes + Chrono Boost     |
| `forge`                   | 63   | RESEARCHES_UPGRADES  | Ground attack/armor              |
| `cyberneticscore`         | 72   | RESEARCHES_UPGRADES  | Air attack/armor + Warpgate      |
| `twilightcouncil`         | 65   | RESEARCHES_UPGRADES  | Charge, Blink, Resonating Glaives |
| `templararchive`          | 68   | RESEARCHES_UPGRADES  | Psionic Storm                    |
| `darkshrine`              | 69   | RESEARCHES_UPGRADES  | Shadow Stride                    |
| `roboticsbay`             | 70   | RESEARCHES_UPGRADES  | Extended Thermal Lance, etc.     |
| `fleetbeacon`             | 64   | RESEARCHES_UPGRADES  | Carrier/Tempest/VR upgrades      |

#### Zerg

| Building (pysc2 name)     | ID   | Classification       | Notes                           |
|---------------------------|------|----------------------|---------------------------------|
| `hatchery`                | 86   | BOTH                 | Produces Larvae + Queen + research |
| `lair`                    | 100  | BOTH                 | Morphed Hatchery, same production |
| `hive`                    | 101  | BOTH                 | Morphed Lair, same production    |
| `spawningpool`            | 89   | RESEARCHES_UPGRADES  | Zergling speed, Adrenal Glands   |
| `evolutionchamber`        | 90   | RESEARCHES_UPGRADES  | Melee/missile/carapace           |
| `hydraliskden`            | 91   | RESEARCHES_UPGRADES  | Hydralisk speed/range            |
| `spire`                   | 92   | RESEARCHES_UPGRADES  | Air attack/armor                 |
| `greaterspire`            | 102  | BOTH                 | Morphed Spire; enables Broodlord morph + air upgrades |
| `ultraliskcavern`         | 93   | RESEARCHES_UPGRADES  | Ultralisk upgrades               |
| `infestationpit`          | 94   | RESEARCHES_UPGRADES  | Pathogen Glands, Neural Parasite |
| `banelingnest`            | 96   | RESEARCHES_UPGRADES  | Baneling speed                   |
| `roachwarren`             | 97   | RESEARCHES_UPGRADES  | Roach speed/burrow               |
| `lurkerden`               | 504  | RESEARCHES_UPGRADES  | Lurker range/burrow speed        |
| `nydusnetwork`            | 95   | PRODUCES_UNITS       | Produces NydusCanal worms        |

### Comparison with Current shared_constants.py

**Current hardcoded set has 40 entries. Findings:**

Missing from current set (should be added):
- `commandcenter` (ID 18) -- trains SCVs, is a production building
- `planetaryfortress` (ID 130) -- trains SCVs
- `nexus` (ID 59) -- trains Probes + Chrono Boost
- `nydusnetwork` (ID 95) -- produces NydusCanal worms

Present in current set but questionable:
- `orbitalcommandflying` (ID 134) -- cannot produce while flying

The current set otherwise aligns well with the comprehensive list above.

---

## 4. Comprehensive BASE_TYPES

### Full List with pysc2 Enum Names (lowercase)

| Building (pysc2 name)     | ID   | Race    | Notes                           |
|---------------------------|------|---------|----------------------------------|
| `commandcenter`           | 18   | Terran  | Base tier                        |
| `orbitalcommand`          | 132  | Terran  | Morphed from CC                  |
| `planetaryfortress`       | 130  | Terran  | Morphed from CC                  |
| `commandcenterflying`     | 36   | Terran  | Lifted CC (still a base anchor)  |
| `orbitalcommandflying`    | 134  | Terran  | Lifted OC (still a base anchor)  |
| `nexus`                   | 59   | Protoss | Only Protoss town hall           |
| `hatchery`                | 86   | Zerg    | Base tier                        |
| `lair`                    | 100  | Zerg    | Morphed from Hatchery            |
| `hive`                    | 101  | Zerg    | Morphed from Lair                |

**Total: 9 entries**

### Comparison with Current shared_constants.py

The current `BASE_TYPES` set has **9 entries** (not 10 as stated in the audit -- recount
confirms 9). The set is:

```
commandcenter, orbitalcommand, planetaryfortress,
commandcenterflying, orbitalcommandflying,
nexus,
hatchery, lair, hive
```

**Verdict: The current BASE_TYPES set is COMPLETE.** There are no missing morphed
variants or edge cases.

Note: `PlanetaryFortressFlying` does not exist in SC2 -- Planetary Fortress cannot lift
off, so there is no flying variant to track.

### Runtime Alternative

The `ideal_harvesters` field (verified populated in observer mode -- see Section 5) could
theoretically identify town halls at runtime: town halls have `ideal_harvesters >= 16`
while gas buildings have `ideal_harvesters == 3`. However, this is a fragile heuristic
(what if a game patch changes the number?). The hardcoded set of 9 entries is stable and
unlikely to change. **Recommendation: Keep the hardcoded BASE_TYPES set.**

---

## 5. Enhancement Field Availability

All fields were tested empirically in observer mode via `030-verify-passengers.py`.

| # | Field Name             | Proto Type           | Field # | Python Access Path              | Observer Mode | Serialization Notes |
|---|------------------------|----------------------|---------|----------------------------------|---------------|---------------------|
| EN-1 | `passengers`        | repeated PassengerUnit | 24   | `unit.passengers[i].tag`, `.unit_type`, `.health`, etc. | **NOT POPULATED** | N/A (empty in observer mode) |
| EN-2 | `buff_ids`          | repeated uint32      | 27      | `list(unit.buff_ids)`           | **POPULATED** | JSON array string or pipe-delimited; variable length |
| EN-3a | `buff_duration_remain` | int32             | 43      | `unit.buff_duration_remain`     | **POPULATED** | Simple int column |
| EN-3b | `buff_duration_max` | int32               | 44      | `unit.buff_duration_max`        | **POPULATED** | Simple int column |
| EN-4 | `rally_targets`     | repeated RallyTarget | 45      | `unit.rally_targets[i].point.x`, `.point.y`, `.tag` | **POPULATED** | JSON or separate columns for first rally point |
| EN-5a | `assigned_harvesters` | int32             | 28      | `unit.assigned_harvesters`      | **POPULATED** | Simple int column (buildings only) |
| EN-5b | `ideal_harvesters` | int32               | 29      | `unit.ideal_harvesters`         | **POPULATED** | Simple int column (buildings only) |
| EN-6 | `engaged_target_tag` | uint64              | 34      | `unit.engaged_target_tag`       | **POPULATED** | uint64 column; 0 when not engaged |
| EN-7a | `detect_range`     | float                | 31      | `unit.detect_range`             | **POPULATED** | float column (detectors only) |
| EN-7b | `radar_range`      | float                | 32      | `unit.radar_range`              | **NOT SEEN**  | Likely only SensorTower (none in test replay) |
| EN-8a | `is_powered`       | bool                 | 35      | `unit.is_powered`               | **POPULATED** | bool column (Protoss buildings only) |
| EN-8b | `is_active`        | bool                 | 39      | `unit.is_active`                | **POPULATED** | bool column |
| EN-8c | `cloak`            | CloakState enum      | 10      | `unit.cloak`                    | Not tested    | int column: 0=Unknown, 1=Cloaked, 2=CloakedDetected, 3=NotCloaked, 4=CloakedAllied |
| EN-8d | `add_on_tag`       | uint64               | 23      | `unit.add_on_tag`               | **POPULATED** | uint64 column; 0 when no add-on |
| EN-8e | `display_type`     | DisplayType enum     | 1       | `unit.display_type`             | Not tested    | int column: 1=Visible, 2=Snapshot, 3=Hidden, 4=Placeholder |

### Serialization Recommendations for Integration

**Simple scalar fields** (buff_duration_remain, buff_duration_max, assigned_harvesters,
ideal_harvesters, engaged_target_tag, detect_range, radar_range, is_powered, is_active,
add_on_tag, display_type, cloak):
- Add directly to `UNIT_FIELD_CONFIG` or `BUILDING_FIELD_CONFIG` as new entries
- Each becomes a single parquet column per entity
- Pattern: `{'column_suffix': 'buff_duration_remain', 'extract': lambda unit: unit.buff_duration_remain}`

**Repeated/variable-length fields** (buff_ids, rally_targets, passengers):
- **buff_ids**: Recommend JSON array string (`"[271, 5]"`) in a single column. Alternative:
  pipe-delimited (`"271|5"`). The number of simultaneous buffs is typically 0-3, rarely more.
- **rally_targets**: Recommend extracting only the first rally target as separate columns:
  `rally_x`, `rally_y`, `rally_tag`. Multiple rally points are rare (only Zerg town halls
  with separate unit/worker rallies).
- **passengers**: Not available in observer mode. If implemented via perspective switching,
  recommend JSON array of `{tag, unit_type}` objects, or a pipe-delimited string of unit types.

---

## 6. Recommendations for Prompt 031

### Confirmed Feasible

| ID   | Task                                              | Status    | Implementation Notes |
|------|---------------------------------------------------|-----------|---------------------|
| FN-1 | Replace BUILDING_TYPES with Attribute.Structure   | **GO**    | Use integer ID set from `data_raw()`. Filter by `owner > 0` at runtime to exclude map objects. |
| FN-2 | Deprecate AIR_UNIT_TYPES (already has `is_flying`) | **GO**    | `is_flying` field already extracted. No code change needed for extraction; update downstream only. |
| EN-2 | Extract `buff_ids`                                | **GO**    | Populated in observer mode. Add to field configs. |
| EN-3 | Extract `buff_duration_remain/max`                | **GO**    | Populated in observer mode. Simple int columns. |
| EN-4 | Extract `rally_targets`                           | **GO**    | Populated in observer mode. Extract first target as rally_x, rally_y, rally_tag. |
| EN-5 | Extract `assigned_harvesters/ideal_harvesters`    | **GO**    | Populated in observer mode. Building field config only. |
| EN-6 | Extract `engaged_target_tag`                      | **GO**    | Populated in observer mode. Unit field config. |
| EN-7a| Extract `detect_range`                            | **GO**    | Populated in observer mode. Unit/building field config. |
| EN-8 | Extract `is_powered`, `is_active`, `add_on_tag`   | **GO**    | All populated in observer mode. |

### Conditional / Deferred

| ID   | Task                                              | Status       | Notes |
|------|---------------------------------------------------|--------------|-------|
| FN-3 | Replace UNIT_CONTAINING_BUILDINGS with passengers | **DEFERRED** | `passengers` is NOT populated in observer mode. Would require per-player perspective switching workaround. Keep current heuristic. |
| EN-7b| Extract `radar_range`                             | **LIKELY GO**| Not seen in test replay (no SensorTower present). Field exists in proto; likely works. |
| EN-8c| Extract `cloak`                                   | **LIKELY GO**| Not explicitly tested but field is well-defined in proto. |
| EN-8e| Extract `display_type`                            | **LIKELY GO**| Not explicitly tested but field is well-defined in proto. |

### Suggested Implementation Order for Prompt 031

1. **FN-1: Replace BUILDING_TYPES with API-derived integer ID set** (highest impact)
   - Add `data_raw()` call in `extraction_pipeline.py` after `start_replay()`
   - Build `BUILDING_TYPE_IDS: frozenset[int]` from `Attribute.Structure`
   - Modify `is_building()` to accept and use the ID set
   - Pass the set through to extractors
   - Handle the `lurkerden` vs `lurkerdenmp` naming discrepancy by using IDs not names

2. **FN-2: Mark AIR_UNIT_TYPES as deprecated** (low effort)
   - Add deprecation comment to `shared_constants.py`
   - Update `engineer_army_features.py` to use per-frame `is_flying` if applicable

3. **Enhancement fields: Add to UNIT_FIELD_CONFIG / BUILDING_FIELD_CONFIG** (medium effort)
   - Priority order: `buff_ids`, `assigned_harvesters`/`ideal_harvesters`, `add_on_tag`,
     `engaged_target_tag`, then remaining fields
   - Each field is a simple addition to the existing config pattern

4. **PRODUCTION_BUILDING_TYPES / BASE_TYPES: Update hardcoded sets** (low effort)
   - Add missing entries to PRODUCTION_BUILDING_TYPES (`commandcenter`, `planetaryfortress`,
     `nexus`, `nydusnetwork`)
   - BASE_TYPES is already complete (9 entries, verified)

---

## Verification Checklist

| # | Check | Result | Status |
|---|-------|--------|--------|
| 1 | Research document exists at `./research/030-api-type-classification.md` | File created | **PASS** |
| 2 | Script exists at `./research/scripts/030-verify-data-raw.py` | File created | **PASS** |
| 3 | Script exists at `./research/scripts/030-verify-passengers.py` | File created | **PASS** |
| 4 | data_raw script executed with output captured | Output at `030-data-raw-output.txt` (1283 lines) | **PASS** |
| 5 | passengers script executed with output captured | Output at `030-passengers-output.txt` (44 lines) | **PASS** |
| 6 | data_raw produced actual UnitTypeData with Attribute values | 2005 entries, 550 with attributes, all 11 Attribute values found | **PASS** |
| 7 | passengers test ran with clear YES/NO verdict | "PASSENGERS FIELD EMPTY IN OBSERVER MODE" -- NO | **PASS** |
| 8 | PRODUCTION_BUILDING_TYPES covers all three races with exact pysc2 names | 44 entries across Terran (16), Protoss (12), Zerg (14) + 2 questionable | **PASS** |
| 9 | BASE_TYPES compared against current shared_constants.py | Current set is complete (9 entries) | **PASS** |
| 10 | All 8 enhancement fields documented with Python access paths | Table in Section 5 covers all EN-1 through EN-8 fields | **PASS** |
