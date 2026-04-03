# 032 - Passenger Field & Dead Units Research Findings

## 1. Executive Summary

**Can the `passengers` field replace the distance heuristic?**
**PARTIALLY -- for non-gas buildings/transports with `cargo_space_max > 0`, YES. For gas refineries, NO.**

The `passengers` field exists on the Unit proto and is accessible via pysc2
(`unit.passengers`). However, gas refineries are a special case: the SC2 engine does not
model gas mining workers as "passengers" at all. Workers literally despawn from the game
world during the gas harvesting animation and reappear when done. Gas refineries have
`cargo_space_max=0`, confirming the engine doesn't treat them as containers.

For units that DO have `cargo_space_max > 0` (Medivacs=8, Bunkers=4, Command Centers=5),
the `passengers` field should be used as the primary detection method when units are loaded.
The test replay did not contain any actual loading events (the Medivac was never loaded),
so we could not directly confirm `passengers` populates during replay playback for these
units. However, the fact that `cargo_space_max` is correctly populated for these unit types
(and NOT for gas buildings) strongly suggests the engine does track passenger state for
them. If this assumption proves wrong, the distance heuristic catches it as a fallback.

`dead_units` works reliably as the sole authoritative source for unit death.

## 2. Passengers Field Analysis

### Accessibility
- **Attribute exists**: `has_passengers_attr = True` in both observer and player modes
- **Proto DESCRIPTOR confirms**: `passengers`, `cargo_space_taken`, `cargo_space_max` are
  all present in `Unit.DESCRIPTOR.fields`
- **Exact attribute path**: `raw_data.units[i].passengers` (repeated PassengerUnit),
  `raw_data.units[i].cargo_space_taken`, `raw_data.units[i].cargo_space_max`

### cargo_space_max Population (Key Finding)

Units that CAN carry other units have `cargo_space_max` correctly populated:

| Unit Type | Type ID | cargo_space_max | Conclusion |
|---|---|---|---|
| Medivac | 54 | 8 | Engine models as container |
| CommandCenter | 18 | 5 | Engine models as container |
| Bunker | 24 | 4 | Engine models as container |
| Refinery | 20 | **0** | Engine does NOT model as container |

This is the critical distinction: **gas refineries are not containers in the engine's data
model**. Workers mining gas are not "passengers" -- they are despawned entirely.

### Gas Refinery Behavior (Confirmed)
- Gas refineries have `cargo_space_max=0` in all frames
- Workers literally vanish from `raw_data.units` during gas harvesting
- They reappear with the same tag when the harvest cycle completes
- The `assigned_harvesters` field on the refinery correctly tracks how many workers are
  assigned (e.g., `harv=3/3`) even when workers are mid-harvest and invisible
- Workers returning from gas carry a buff (`CarryHarvestableVespeneGeyserGas` or race-specific
  variants) on the first frame they reappear, which could be used as additional confirmation
  but is overkill for production logic

### Passengers on Transports/Bunkers (Unconfirmed but Expected)
The test replay (TvT match 4184936) did not contain any actual unit-loading events:
- The Medivac (45 observations, loops 8176-8880) was never loaded with troops
- No Bunker was loaded with marines
- No CC was loaded with SCVs

Therefore `passengers` was `[]` across the board, but this is expected behavior for empty
containers. The correct `cargo_space_max` values strongly suggest `passengers` WILL populate
when units are actually loaded. Implementation should use `passengers` as primary detection
for `cargo_space_max > 0` units, with the distance heuristic as fallback if the assumption
proves wrong.

## 3. Dead Units Analysis

### Correct Exclusion of Building-Entry Units
**YES** - `dead_units` correctly excludes units that enter buildings.

Evidence:
- **452 frames** had units that disappeared from `raw_data.units` but were NOT in
  `dead_units` (observer mode)
- **459 frames** in player mode (slightly different due to visibility)
- 6 worker tags disappeared 73-77 times each throughout the replay, consistent with gas
  mining cycles (enter refinery, disappear, exit, reappear, repeat)
- Only **1 tag** out of all disappeared tags later appeared in `dead_units` (a unit that
  was hidden temporarily then actually died later in combat)

### What Triggers Dead Units Entries
- **68 frames** had `dead_units` events across the replay (both modes identical)
- Deaths occur from game loop 4240 onwards (when combat begins)
- Dead units range from 1-5 tags per event frame
- These represent actual unit deaths (combat kills)

### Key Behavioral Pattern
| Event | In dead_units? | Disappears from raw_data.units? |
|---|---|---|
| Worker enters gas refinery | NO | YES |
| Unit loads into transport | NO | YES (expected) |
| Unit killed in combat | YES | YES |
| Unit exits gas refinery | NO | Reappears with same tag |
| Unit unloads from transport | NO | Reappears (expected) |

### Disappearance Frequency Analysis (Gas Mining Workers)
| Worker Tag | Times Disappeared | Pattern |
|---|---|---|
| 4347658241 | 77 | Cycling in/out of gas |
| 4349231105 | 76 | Cycling in/out of gas |
| 4354211841 | 76 | Cycling in/out of gas |
| 4348706817 | 75 | Cycling in/out of gas |
| 4346871809 | 74 | Cycling in/out of gas |
| 4356571137 | 73 | Cycling in/out of gas |

These 6 workers are the 3 gas miners per player (2 players x 3 workers = 6), cycling
through gas refineries ~75 times each across the game.

## 4. Recommended Architecture

### Tier 1 (Primary -- Non-Gas Containers): `passengers` Field
For buildings/transports with `cargo_space_max > 0` (Bunkers, Command Centers, Medivacs,
Overlord Transports, Warp Prisms, etc.):
- Check the container's `passengers` repeated field for the hidden unit's tag
- If found: unit is "inside <building_type>" with the container's coordinates
- This is the authoritative, API-driven detection for true container units

### Tier 2 (Gas Mining -- Special Case): Distance Heuristic
For gas refineries specifically (`cargo_space_max=0`, workers despawn entirely):
- If a unit disappears, is NOT in `dead_units`, and is within
  `INSIDE_BUILDING_DISTANCE_THRESHOLD` of a gas refinery, mark as "inside <refinery_type>"
- The `UNIT_CONTAINING_BUILDINGS` dict and distance threshold remain necessary for this case
- Optional: verify the worker carries a gas harvest buff on reappearance (overkill but
  available for debugging)

### Tier 3 (Authoritative Death): `dead_units` Event
- `dead_units` is the SOLE authoritative source for unit death
- A unit should ONLY be marked destroyed if its tag appears in `raw_data.event.dead_units`
- A unit disappearing from `raw_data.units` without a `dead_units` entry is NOT dead

### Tier 4 (Fallback -- Unresolved Disappearances): Distance Heuristic / NaN
If a unit disappears and is NOT in `dead_units` AND is NOT in any container's `passengers`
AND cannot be matched to a gas refinery via distance heuristic:
- Apply the general distance heuristic against all `UNIT_CONTAINING_BUILDINGS`
- If no match: leave columns as NaN (unit is in an unresolved hidden state)
- The unit will naturally reappear if it was temporarily hidden
- Only mark as destroyed when it appears in `dead_units`

## 5. Edge Cases

### Confirmed Behaviors (This Replay)
1. **Gas mining workers**: Disappear from `raw_data.units` every ~8-16 game loops while
   inside the refinery. Reappear with same tag when done. Never in `dead_units` during
   mining. Gas refineries have `cargo_space_max=0` and never populate `passengers`.
2. **Multiple gas cycles**: Same workers cycle 73-77 times per game, confirming stable
   tag reuse and no tag recycling during normal gas mining.
3. **Combat deaths vs. disappearances**: Clear separation. Deaths only start at loop 4240+
   when combat begins; disappearances start at loop 1336 when gas mining begins.
4. **Tag overlap**: Only 1 out of ~6 frequently-disappearing tags later appeared in
   `dead_units` -- a worker that mined gas for most of the game then died in combat.

### Known Edge Cases -- Unit "Limbo" States (From External Research)

Even with full vision (observer mode) and fog of war disabled, several situations cause
units to vanish from `raw_data.units` without appearing in `dead_units`. These are
documented here for future handling.

#### 5.1 Morphing Transitions (Zerg & Protoss)
When a unit transforms into another unit, there is often a 1-frame gap where the original
tag is removed and the new tag has not yet registered.

- **Zerg Drones -> Buildings**: The Drone is destroyed (but may not appear in `dead_units`
  as a "kill"). The building is a new entity with a new tag. The drone tag may simply vanish.
- **Zerg Banelings**: Banelings that 'attack' reach their target and detonate. They disappear from the game.
  It is unknown/unconfirmed if they will appear in the dead_units list, but the consensus is they usually do not.
- **Archon Merge**: Two High Templar tags are removed. During the merge animation they are
  replaced by a "Power Overwhelming" cocoon entity. If the cocoon type isn't tracked, the
  Templar simply vanish from the unit list.
- **Ravagers/Lurkers/Brood Lords**: During the morphing egg stage, the original unit
  (Roach/Hydra/Corruptor) is gone. The egg unit type must be tracked to "see" them.

**Impact**: Units undergoing morphs could appear as perpetually hidden if their tag never
reappears and never shows in `dead_units`. Current pipeline would leave them as NaN.

**Future mitigation**: Track morph cocoon/egg unit types and map original tag -> new entity. (needs user confirmation for intended handling)

#### 5.2 Nydus Network Transit
When a unit enters a Nydus Worm, it is stored in a global buffer associated with the Nydus
Network. The unit is not a "passenger" of the entrance or exit worm -- it exists in an
invisible transport layer. Standard unit queries will not see it.

**Impact**: The distance heuristic may match the unit to a nearby Nydus Worm entrance, but
if the unit exits from a distant Nydus Canal, the position data would be wrong. This is a
known limitation.

**Future mitigation**: Track Nydus Network/Canal pairs and treat all Nydus units as a
special "in transit" state.

#### 5.3 Ability-Based Removal
Some abilities temporarily remove units from the game world:

- **Stasis Ward (Protoss)**: Units trapped in a Stasis Ward may be flagged as hidden.
  Depending on pipeline filters (e.g., `is_visible`), they may disappear from results
  because they are no longer interactable.
- **Graviton Beam (Phoenix)**: The lifted unit is still in `raw_data.units` but its state
  changes significantly (`is_flying` flips, height changes). Should not cause disappearance
  but could confuse spatial logic.

**Impact**: Low -- these are rare and brief. Stasis units would appear as NaN for a few
frames. Graviton Beam units stay in the unit list.

#### 5.4 Hallucination Timeout
When a Sentry's Hallucination expires, it does NOT always trigger a `dead_units` event
because it wasn't killed by damage -- it simply ceased to exist. The tag stops appearing
in `raw_data.units` with no death signal.

**Impact**: Hallucinated units would appear as perpetually hidden after their timer expires.
The `is_hallucination` field on the proto could be used to identify and handle these.

**Future mitigation**: Track `is_hallucination=True` units separately. When they disappear
without a `dead_units` entry, mark as "expired" rather than "hidden" or "destroyed".

#### 5.5 Blink / Tactical Jump (Non-Issue)
During the exact frame a Battlecruiser uses Tactical Jump or a Stalker Blinks, the unit
may reposition so fast that spatial queries fail to find it for one step. However, the unit
remains in `raw_data.units` -- it just changes coordinates. This is NOT a disappearance and
should not affect the pipeline.

### Not Tested in This Replay
- Actual transport loading (Medivac picking up marines, Bunker loading, CC loading)
- Zerg morphing transitions
- Protoss hallucinations
- Nydus Network usage
- Burrowed units (TvT replay -- no burrow)

## 6. Implementation Recommendations

### Changes to Make

1. **Add passenger-based detection for `cargo_space_max > 0` units**: In the extraction
   flow, collect `passengers` lists from buildings/transports that have `cargo_space_max > 0`.
   Pass a mapping of `{passenger_tag: building_info}` to the unit extractor. If a hidden
   unit's tag appears in this map, it is definitively "inside <building_type>".

2. **Keep distance heuristic as primary for gas refineries**: Gas buildings have
   `cargo_space_max=0` and never populate `passengers`. The existing distance-based
   heuristic in `resolve_hidden_units()` remains the correct approach for gas mining.

3. **Keep distance heuristic as fallback for everything else**: If `passengers` doesn't
   populate for loaded transports during replays (unconfirmed), the distance heuristic
   catches it. Low risk -- either we gain accuracy from `passengers`, or we fall back to
   current behavior with no regression.

4. **Ensure `dead_units` is the sole death authority**: Audit that no code path marks a
   unit as destroyed based on disappearance alone. Only `raw_data.event.dead_units` should
   trigger the "destroyed" lifecycle state.

5. **Update `shared_constants.py` comments**: Clarify that `UNIT_CONTAINING_BUILDINGS` and
   `INSIDE_BUILDING_DISTANCE_THRESHOLD` are now primarily for gas mining detection and as a
   fallback for non-gas containers.

### Impact on Prompt 033
Prompt 033 should be revised to implement this tiered architecture:
- Tier 1: `passengers` field for `cargo_space_max > 0` units (primary for non-gas)
- Tier 2: Distance heuristic for gas refineries (primary for gas mining)
- Tier 3: `dead_units` as sole death authority
- Tier 4: Distance heuristic as general fallback + NaN for unresolved

## 7. Raw Data Samples

### Unit Proto DESCRIPTOR Fields (complete list)
```
display_type, alliance, tag, unit_type, owner, pos, facing, radius, build_progress,
cloak, buff_ids, detect_range, radar_range, is_selected, is_on_screen, is_blip,
is_powered, is_active, attack_upgrade_level, armor_upgrade_level, shield_upgrade_level,
health, health_max, shield, shield_max, energy, energy_max, mineral_contents,
vespene_contents, is_flying, is_burrowed, is_hallucination, orders, add_on_tag,
passengers, cargo_space_taken, cargo_space_max, assigned_harvesters, ideal_harvesters,
weapon_cooldown, engaged_target_tag, buff_duration_remain, buff_duration_max, rally_targets
```

### cargo_space_max by Unit Type (Entire Game Scan)
```
type_id=54 (Medivac):         cargo_space_max=8
type_id=18 (CommandCenter):   cargo_space_max=5
type_id=24 (Bunker):          cargo_space_max=4
type_id=20 (Refinery):        cargo_space_max=0  <-- NOT a container
```

### Field Inspection Sample (first unit in frame)
```json
{
  "has_passengers_attr": true,
  "passengers_count": 0,
  "passengers": [],
  "cargo_space_taken": 0,
  "cargo_space_max": 0
}
```

### Dead Units Sample Events
```
Loop 4240: 1 death -> [4358406145]
Loop 4280: 1 death -> [4355522561]
Loop 4320: 1 death -> [4358930433]
Loop 5424: 2 deaths -> [4349755393, 4363649025]
Loop 5832: 5 deaths -> [4353163265, 4350541825, 4358930434, 4351590401, 4353949697]
```

### Disappeared-Not-Dead Sample Events (Gas Mining)
```
Loop 1336: 1 tag vanished -> [4347658241]  (gas miner entering refinery)
Loop 1368: 1 tag vanished -> [4349231105]  (gas miner entering refinery)
Loop 1400: 1 tag vanished -> [4354211841]  (gas miner entering refinery)
Loop 1440: 1 tag vanished -> [4347658241]  (same miner, re-entering refinery)
```

### Gas Refinery During Worker Disappearance (Loop 1336)
```
[GAS_BLDG] tag=4355260417 type_id=20 owner=1
  cargo_taken=0 cargo_max=0 passengers=0
  assigned_harvesters=3 ideal_harvesters=3 vespene=2250
  (Worker tag 4347658241 is hidden -- not in passengers, not in dead_units)
```
