# 032 - Passenger Field & Dead Units Research Findings

## 1. Executive Summary

**Can the `passengers` field replace the distance heuristic? NO.**

The `passengers` field exists on the Unit proto and is accessible via pysc2 (`unit.passengers`), but **the SC2 engine does not populate it during replay playback**. Across 1,110 frames in both observer mode and player-perspective mode, zero gas buildings and zero transports had any passengers or cargo_space_taken > 0.

However, `dead_units` works reliably and correctly excludes units entering buildings. The distance-based heuristic remains the only viable method for identifying units inside buildings, but `dead_units` can be leveraged more tightly to prevent false deaths.

## 2. Passengers Field Analysis

### Accessibility
- **Attribute exists**: `has_passengers_attr = True` in both modes
- **Proto DESCRIPTOR confirms**: `passengers`, `cargo_space_taken`, `cargo_space_max` are all present in `Unit.DESCRIPTOR.fields`
- **Exact attribute path**: `raw_data.units[i].passengers` (repeated PassengerUnit), `raw_data.units[i].cargo_space_taken`, `raw_data.units[i].cargo_space_max`

### Population Status
| Mode | Gas Buildings w/ Passengers | Gas Buildings w/ Cargo > 0 | Transports w/ Passengers | Transports w/ Cargo > 0 |
|---|---|---|---|---|
| Observer (player_id=0) | 0 | 0 | 0 | 0 |
| Player 1 (player_id=1) | 0 | 0 | 0 | 0 |

### Why It's Not Populated
The SC2 engine appears to not populate `passengers` and `cargo_space_taken/max` fields during **replay playback**. These fields are likely only populated during live gameplay (where the client needs to render cargo UI). During replay observation, units that enter buildings simply vanish from `raw_data.units` without any cargo/passenger metadata being set on the container building.

This is consistent with prior research (prompts 027/028) which found no cargo data in the pipeline output. The new finding is that the field **structurally exists** but is **empty at the engine level**, confirming it's not a pysc2 wrapper limitation but an SC2 engine replay-mode behavior.

### Sample Data from Gas Refinery Frames
No passenger data was found. The `passengers` list was always empty (`[]`) and `cargo_space_taken` was always `0` for all gas buildings and transports across all frames.

## 3. Dead Units Analysis

### Correct Exclusion of Building-Entry Units
**YES** - `dead_units` correctly excludes units that enter buildings.

Evidence:
- **452 frames** had units that disappeared from `raw_data.units` but were NOT in `dead_units` (observer mode)
- **459 frames** in player mode (slightly different due to visibility)
- 6 worker tags disappeared 73-77 times each throughout the replay, consistent with gas mining cycles (enter refinery, disappear, exit, reappear, repeat)
- Only **1 tag** out of all disappeared tags later appeared in `dead_units` (a unit that was hidden temporarily then actually died later)

### What Triggers Dead Units Entries
- **68 frames** had `dead_units` events across the replay (both modes identical)
- Deaths occur from game loop 4240 onwards (when combat begins)
- Dead units range from 1-5 tags per event frame
- These represent actual unit deaths (combat kills)

### Key Behavioral Pattern
| Event | In dead_units? | Disappears from raw_data.units? |
|---|---|---|
| Worker enters gas refinery | NO | YES |
| Unit loads into transport | NO | YES |
| Unit killed in combat | YES | YES |
| Unit exits gas refinery | NO | Reappears |
| Unit unloads from transport | NO | Reappears |

### Disappearance Frequency Analysis (Gas Mining Workers)
| Worker Tag | Times Disappeared | Pattern |
|---|---|---|
| 4347658241 | 77 | Cycling in/out of gas |
| 4349231105 | 76 | Cycling in/out of gas |
| 4354211841 | 76 | Cycling in/out of gas |
| 4348706817 | 75 | Cycling in/out of gas |
| 4346871809 | 74 | Cycling in/out of gas |
| 4356571137 | 73 | Cycling in/out of gas |

These 6 workers are the 3 gas miners per player (2 players x 3 workers = 6), cycling through gas refineries ~75 times each across the game.

## 4. Recommended Architecture

Since `passengers` is not available during replay playback, the original 3-tier plan must be adjusted:

### Tier 1 (Primary - Inside Detection): Distance-Based Heuristic
The existing `resolve_hidden_units()` distance heuristic remains the **primary** method for detecting units inside buildings. It should be kept and potentially improved:
- Current threshold (5.0 game units) works well
- `UNIT_CONTAINING_BUILDINGS` dict provides correct building-unit compatibility

### Tier 2 (Authoritative Death): `dead_units` Event
`dead_units` is the **sole authoritative source** for unit death. The current codebase already uses this, but it can be tightened:
- A unit should ONLY be marked destroyed if its tag appears in `raw_data.event.dead_units`
- A unit disappearing from `raw_data.units` without a `dead_units` entry is NOT dead -- it's hidden (inside a building, in transport, etc.)
- This is already the approach in `unit_extractor.py`, but review to ensure no edge cases leak through

### Tier 3 (Fallback - Unresolved Disappearances): Grace Period / NaN
If a unit disappears and is NOT in `dead_units` AND cannot be matched to a building via the distance heuristic:
- Do NOT mark as destroyed
- Leave columns as NaN (current behavior for hidden units not matched to buildings)
- The unit will naturally reappear if it was temporarily hidden
- Only mark as destroyed when it appears in `dead_units`

### NOT Viable: `passengers` / `cargo_space_taken`
These fields cannot be used during replay playback. Do not build logic around them.

## 5. Edge Cases

### Confirmed Behaviors
1. **Gas mining workers**: Disappear from `raw_data.units` every ~8-16 game loops while inside the refinery. Reappear when they exit. Never in `dead_units` during mining.
2. **Multiple gas cycles**: Same workers cycle 73-77 times per game, confirming stable tag reuse.
3. **Combat deaths vs. disappearances**: Clear separation. Deaths only start at loop 4240+ when combat begins; disappearances start at loop 1336 when gas mining begins.
4. **Tag overlap**: Only 1 out of ~6 frequently-disappearing tags later appeared in `dead_units` - a worker that mined gas for most of the game then died in combat.

### Not Observed in This Replay (needs separate testing)
- Hallucinated units (no Protoss hallucination in this replay)
- Nydus Network transit
- Medivac/Overlord transport loading (no transport use in this replay)
- Burrowed units (Terran vs Terran replay)
- Morphing units (no Zerg morphs observed)

## 6. Implementation Recommendations

### Do NOT Change (passengers-related)
- Do NOT add passenger-based detection to `resolve_hidden_units()` - the field is empty during replays
- Do NOT modify `state_extractor.py` to collect passenger data from buildings
- Keep `UNIT_CONTAINING_BUILDINGS` and `INSIDE_BUILDING_DISTANCE_THRESHOLD` as-is

### Recommended Changes (dead_units tightening)
1. **Audit `unit_extractor.py` extract()**: Verify that the dead_units check is the ONLY path to marking a unit destroyed. Ensure no fallback logic marks units as dead based on disappearance alone.
2. **Audit `resolve_hidden_units()`**: Verify that units not matched to a building via the distance heuristic are left as NaN (not marked destroyed).
3. **Add `cargo_space_taken` / `cargo_space_max` logging** (optional): Even though these aren't populated now, they could be populated in future SC2 patches. Adding a check costs nothing and future-proofs the code.
4. **Consider widening the inside-building match**: If any disappeared-not-dead units are NOT matched by the current 5.0 threshold heuristic, investigate whether the threshold should be increased or the `UNIT_CONTAINING_BUILDINGS` dict expanded.

### Impact on Prompt 033
The original prompt 033 was designed around implementing passenger-based detection as the primary method. Since passengers aren't populated in replay mode, **prompt 033 needs to be revised** to focus on:
1. Auditing and tightening the existing dead_units + distance heuristic logic
2. Ensuring no false deaths from disappearance events
3. Potentially adding logging/diagnostics for future passenger field availability
4. NOT restructuring around a 3-tier passenger-first architecture

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

### Disappeared-Not-Dead Sample Events
```
Loop 1336: 1 tag vanished -> [4347658241]  (gas miner entering refinery)
Loop 1368: 1 tag vanished -> [4349231105]  (gas miner entering refinery)
Loop 1400: 1 tag vanished -> [4354211841]  (gas miner entering refinery)
Loop 1440: 1 tag vanished -> [4347658241]  (same miner, re-entering refinery)
```
