# API Documentation Map: Required Features to pysc2 API

This document maps each required data category for Ground Truth Game State extraction to the corresponding pysc2 API paths, data types, and extraction methods.

## Summary
pysc2 provides **complete ground truth access** to all required game state information through its raw observation interface (`obs.observation.raw_data`). Unlike traditional replay parsers, pysc2 runs replays through the actual SC2 game engine, providing perfect information at every game loop.

---

## 1. Units (Per Player, Per Game Loop)

### Unit Type
- **pysc2 API Path**: `obs.observation.raw_data.units[i].unit_type`
- **Data Type**: `int` (unit type ID)
- **Extraction Method**: Direct access, iterate through `raw.units` list
- **Unit Name Lookup**: `pysc2.lib.units.get_unit_type(unit_id)` or `pysc2.lib.static_data.StaticData.units`
- **Filter by Player**: Use `unit.alliance` field (Self=1, Ally=2, Neutral=3, Enemy=4)

```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Unit type → obs.observation.raw_data.units[i].unit_type → int → direct access
Unit name → pysc2.lib.units.get_unit_type(unit_id) → enum → lookup function
```

### Position (x, y, z coordinates)
- **pysc2 API Path**: `obs.observation.raw_data.units[i].pos`
- **Data Type**: `Point` protobuf (fields: x, y, z)
- **Extraction Method**: Access `pos.x`, `pos.y`, `pos.z` (floats in world units)
- **Coordinate System**: World coordinates (origin varies by map)

```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Position X → obs.observation.raw_data.units[i].pos.x → float → direct access
Position Y → obs.observation.raw_data.units[i].pos.y → float → direct access
Position Z → obs.observation.raw_data.units[i].pos.z → float → direct access
```

### Unit State (built/existing/killed)
- **Built/Existing Detection**: Compare `tag` values across frames (persistent unit ID)
- **Killed Detection**: `obs.observation.raw_data.event.dead_units` (list of tags)
- **New Units**: Tags appearing for first time in `raw.units`
- **Data Type**: `uint64` for tag, list of `uint64` for dead_units

```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Unit tag (persistent ID) → obs.observation.raw_data.units[i].tag → uint64 → direct access
Dead units → obs.observation.raw_data.event.dead_units → list[uint64] → check if tag in list
New units → compare tags frame-to-frame → set difference → track seen tags
```

### Unit Properties (health, shields, energy)
```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Health → obs.observation.raw_data.units[i].health → float → direct access
Health Max → obs.observation.raw_data.units[i].health_max → float → direct access
Shields → obs.observation.raw_data.units[i].shield → float → direct access
Shields Max → obs.observation.raw_data.units[i].shield_max → float → direct access
Energy → obs.observation.raw_data.units[i].energy → float → direct access
Energy Max → obs.observation.raw_data.units[i].energy_max → float → direct access
```

### Additional Unit Properties
```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Facing → obs.observation.raw_data.units[i].facing → float → direct access (radians)
Radius → obs.observation.raw_data.units[i].radius → float → direct access
Cloak State → obs.observation.raw_data.units[i].cloak → enum → CloakState (0-4)
Is Flying → obs.observation.raw_data.units[i].is_flying → bool → direct access
Is Burrowed → obs.observation.raw_data.units[i].is_burrowed → bool → direct access
Is Selected → obs.observation.raw_data.units[i].is_selected → bool → direct access
Owner → obs.observation.raw_data.units[i].owner → int → player ID (1-15, 16=neutral)
Display Type → obs.observation.raw_data.units[i].display_type → enum → Visible/Snapshot/Hidden
```

---

## 2. Buildings (Per Player, Per Game Loop)

**Note**: Buildings are units in SC2. Filter by checking if `unit_type` corresponds to a building.

### Building Type
- **Same as Unit Type**: Buildings are units with specific unit_type IDs
- **Filter Method**: Check `unit_type` against building lists in `pysc2.lib.units` (Terran/Protoss/Zerg enums)

### Position (x, y, z)
- **Same as Unit Position**: `obs.observation.raw_data.units[i].pos`

### Construction State
```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Build Progress → obs.observation.raw_data.units[i].build_progress → float → direct access (0.0-1.0)
Building/Complete → build_progress < 1.0 / == 1.0 → bool → comparison
Started → first appearance of tag → track new tags → frame-to-frame comparison
Destroyed → obs.observation.raw_data.event.dead_units → uint64 → check tag in list
```

### Build Progress Percentage
- **API Path**: `obs.observation.raw_data.units[i].build_progress`
- **Range**: 0.0 to 1.0 (multiply by 100 for percentage)

### Timestamps
- **Completion Timestamp**: Track game_loop when `build_progress` reaches 1.0
- **Destruction Timestamp**: Game loop when tag appears in `dead_units`
- **Game Loop**: `obs.observation.game_loop` (int)

```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Current game loop → obs.observation.game_loop → int → direct access
Completion time → track game_loop when build_progress == 1.0 → int → manual tracking
Destruction time → game_loop when tag in dead_units → int → manual tracking
```

---

## 3. Economy (Per Player, Per Game Loop)

### Player Resources
```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Minerals → obs.observation.raw_data.player.minerals (WRONG - see below) → N/A → N/A
Vespene → obs.observation.raw_data.player.vespene (WRONG - see below) → N/A → N/A
```

**CRITICAL UPDATE**: The raw_data.player proto only contains:
- `power_sources` (list of pylons)
- `camera` (camera position)
- `upgrade_ids` (list of completed upgrades)

**Actual Location for Resources**:
```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Minerals → obs.observation.player_common.minerals → int → direct access
Vespene → obs.observation.player_common.vespene → int → direct access
Food Used → obs.observation.player_common.food_used → int → direct access
Food Cap → obs.observation.player_common.food_cap → int → direct access
Food Army → obs.observation.player_common.food_army → int → direct access
Food Workers → obs.observation.player_common.food_workers → int → direct access
Idle Worker Count → obs.observation.player_common.idle_worker_count → int → direct access
Army Count → obs.observation.player_common.army_count → int → direct access
```

### Worker Count
- **Direct Field**: `obs.observation.player_common.food_workers`
- **Alternative**: Count units where `unit_type` is a worker (SCV=45, Probe=84, Drone=104)

### Supply
```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Supply Used → obs.observation.player_common.food_used → int → direct access
Supply Cap → obs.observation.player_common.food_cap → int → direct access
```

---

## 4. Upgrades (Per Player, Per Game Loop)

### All Completed Upgrades
```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Upgrade IDs → obs.observation.raw_data.player.upgrade_ids → list[int] → direct access
Upgrade Names → pysc2.lib.upgrades.Upgrades(upgrade_id) → enum → lookup function
```

### Upgrade Categories
- **Weapons**: Identified by name pattern (contains "Weapons")
- **Armor**: Identified by name pattern (contains "Armor")
- **Shields**: Identified by name pattern (contains "Shields")
- **Data Source**: `pysc2.lib.upgrades.Upgrades` enum

### Upgrade Levels (1, 2, 3)
- **Detection**: Parse upgrade name (e.g., "TerranInfantryWeaponsLevel1")
- **API provides**: Complete list of all upgrades currently researched

### Research Completion Timestamps
- **Method**: Track game_loop when upgrade ID first appears in `upgrade_ids` list
- **Requires**: Frame-to-frame comparison

```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
New upgrades → compare upgrade_ids frame-to-frame → set difference → manual tracking
Completion time → game_loop when upgrade appears → int → manual tracking
```

### Unit-Specific Upgrade Levels
```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Attack Upgrade Level → obs.observation.raw_data.units[i].attack_upgrade_level → int → direct access
Armor Upgrade Level → obs.observation.raw_data.units[i].armor_upgrade_level → int → direct access
Shield Upgrade Level → obs.observation.raw_data.units[i].shield_upgrade_level → int → direct access
```

---

## 5. Communications

### In-Game Messages/Chat
- **NOT DIRECTLY EXPOSED** in observation proto
- **Workaround**: Use `controller.chat()` to send messages (for logging purposes)
- **Replay Limitations**: Chat may not be fully exposed in replay observation

```python
Required Feature → pysc2 API Path → Data Type → Extraction Method
Chat messages → NOT AVAILABLE IN OBSERVATIONS → N/A → N/A
Timestamp → N/A → N/A → N/A
Player → N/A → N/A → N/A
```

**Gap Identified**: Chat messages are not exposed in the observation API. This is a known limitation.

---

## 6. Additional Available Data

### Effects (Map-wide AoE abilities)
```python
Feature → pysc2 API Path → Data Type → Extraction Method
Effect ID → obs.observation.raw_data.effects[i].effect_id → int → direct access
Position(s) → obs.observation.raw_data.effects[i].pos → list[Point2D] → iterate
Alliance → obs.observation.raw_data.effects[i].alliance → enum → Alliance (1-4)
Owner → obs.observation.raw_data.effects[i].owner → int → player ID
Radius → obs.observation.raw_data.effects[i].radius → float → direct access
```

### Buffs (Per Unit)
```python
Feature → pysc2 API Path → Data Type → Extraction Method
Buff IDs → obs.observation.raw_data.units[i].buff_ids → list[int] → direct access
Buff Duration Remain → obs.observation.raw_data.units[i].buff_duration_remain → int → direct access
Buff Duration Max → obs.observation.raw_data.units[i].buff_duration_max → int → direct access
```

### Unit Orders (Current Actions)
```python
Feature → pysc2 API Path → Data Type → Extraction Method
Order Count → len(obs.observation.raw_data.units[i].orders) → int → list length
Order Ability ID → obs.observation.raw_data.units[i].orders[j].ability_id → int → direct access
Order Target Pos → obs.observation.raw_data.units[i].orders[j].target_world_space_pos → Point → optional field
Order Target Tag → obs.observation.raw_data.units[i].orders[j].target_unit_tag → uint64 → optional field
Order Progress → obs.observation.raw_data.units[i].orders[j].progress → float → 0.0-1.0
```

---

## Data Type Reference

### Protobuf Message Types
- **Point**: `{x: float, y: float, z: float}`
- **Point2D**: `{x: float, y: float}`
- **Unit**: Full unit proto (see raw_pb2.py)
- **ObservationRaw**: Container for all raw data

### Enum Types
- **Alliance**: Self=1, Ally=2, Neutral=3, Enemy=4
- **DisplayType**: Visible=1, Snapshot=2, Hidden=3
- **CloakState**: CloakedUnknown=0, Cloaked=1, CloakedDetected=2, NotCloaked=3

### Scalar Types
- **int**: 32-bit integer
- **uint64**: 64-bit unsigned (used for tags)
- **float**: Floating point
- **bool**: Boolean

---

## Coordinate Systems

### World Coordinates
- **Used in**: `raw.units[i].pos`, effects, orders
- **Origin**: Varies by map
- **Units**: Game world units (1 unit ≈ 1 small unit radius)
- **Z-axis**: Terrain height

### Feature/Minimap Coordinates
- **Used in**: Transformed observations for agents
- **Origin**: (0, 0) at top-left
- **Units**: Pixels
- **Transformation**: Available via `features.Features` class

---

## Multi-Player Considerations

### Observed Player ID
- **Set when starting replay**: `observed_player_id` in `RequestStartReplay`
- **Affects**: What information is visible (fog of war)
- **Current Player**: `obs.observation.player_common.player_id`

### Accessing Other Players
- **Limitation**: Observations are from a single player's perspective
- **Workaround**: Run replay twice (once per player) for full ground truth
- **Units**: Filter by `alliance` and `owner` fields

---

## Summary Table

| Category | Complete? | API Path | Notes |
|----------|-----------|----------|-------|
| Units | ✅ Yes | `raw_data.units` | Full ground truth with persistent tags |
| Buildings | ✅ Yes | `raw_data.units` (filtered) | Same as units |
| Economy | ✅ Yes | `player_common` | Minerals, gas, supply, workers |
| Upgrades | ✅ Yes | `raw_data.player.upgrade_ids` | List of completed upgrades |
| Unit Upgrades | ✅ Yes | `units[i].*_upgrade_level` | Per-unit upgrade levels |
| Chat/Messages | ❌ No | Not exposed | Known limitation |
| Effects | ✅ Yes | `raw_data.effects` | Bonus data not originally requested |
| Buffs | ✅ Yes | `units[i].buff_ids` | Bonus data not originally requested |
| Orders | ✅ Yes | `units[i].orders` | Bonus data not originally requested |

## Conclusion

pysc2 provides **near-complete ground truth access** to all required game state information except chat messages. The raw observation interface gives perfect information at every game loop by running replays through the actual game engine.
