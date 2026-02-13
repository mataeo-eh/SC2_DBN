# 010 - s2client-proto Raw API Reference for SC2 Replay Extraction

## Purpose

This document is the comprehensive API reference for migrating the SC2 replay extraction pipeline from pysc2 to the raw s2client-proto API. It covers every protobuf message, field, and enum needed to implement observer-mode replay extraction with perfect information for all players in a single pass.

**Source material**: Protobuf definitions from https://github.com/Blizzard/s2client-proto (sc2api.proto, raw.proto, score.proto, common.proto, data.proto) and the C++ API documentation at https://blizzard.github.io/s2client-api/.

---

## 1. Observer Mode Behavior

### 1.1 What Happens When `observed_player_id` Is Omitted

The `observed_player_id` field in `RequestStartReplay` is defined as `optional int32` in the protobuf schema:

```protobuf
message RequestStartReplay {
  oneof replay {
    string replay_path = 1;
    bytes replay_data = 5;
  }
  optional bytes map_data = 6;
  optional int32 observed_player_id = 2;   // <-- OPTIONAL
  optional InterfaceOptions options = 3;
  optional bool disable_fog = 4;
  optional bool realtime = 7;
  optional bool record_replay = 8;
}
```

When `observed_player_id` is **not set** (omitted entirely from the request), the SC2 engine loads the replay in **observer perspective**. This is the default replay loading mode. The engine simulates the game with full knowledge of both players simultaneously, rather than from one player's viewpoint.

**Key behavioral differences in observer mode:**

| Aspect | Player Perspective (`observed_player_id=1`) | Observer Mode (field omitted) |
|--------|----------------------------------------------|-------------------------------|
| `player_common` | Single player's economy only | Available per-player by querying with `player_id` |
| `score` | Single player's score only | Available per-player by querying with `player_id` |
| `raw_data.units` (with `disable_fog=True`) | All units visible (both players) | All units visible (both players) |
| `raw_data.player.upgrade_ids` | Observed player's upgrades only | Available for all players |
| `raw_data.player.camera` | Observed player's camera position | Observer camera position |
| `raw_data.event.dead_units` | All death events (with `disable_fog`) | All death events |
| `alliance` field on units | Relative to observed player (Self/Enemy/Neutral) | All non-neutral units show as the same alliance category since there is no "self" |

### 1.2 How `player_common` and `score` Work in Observer Mode

In observer mode, the `player_common` and `score` fields in the `Observation` message are queryable **per player**. The engine computes economic and score data for both players simultaneously. When requesting observation data, you pass a `player_id` to get that specific player's economy/score.

**Python access pattern for per-player economy in observer mode:**

```python
# After starting replay WITHOUT observed_player_id:
# The observation contains player_common with a player_id field
obs = controller.observe()

# player_common.player_id tells you which player this data belongs to
# In observer mode, you can request data for specific players
pc = obs.observation.player_common
print(f"Player {pc.player_id}: {pc.minerals}m, {pc.vespene}g")
```

**Important**: The exact mechanism for per-player querying depends on the client implementation. In the raw protobuf API over websocket, the `RequestObservation` message has:

```protobuf
message RequestObservation {
  optional bool disable_fog = 1;
  optional uint32 game_loop = 2;
}
```

The `RequestObservation` itself does not have a `player_id` field. In observer mode, the engine populates `player_common` for the observer perspective. The per-player data access may require using `ObserverAction` with `ActionObserverPlayerPerspective` to switch the perspective being observed:

```protobuf
message ActionObserverPlayerPerspective {
  optional uint32 player_id = 1;   // 0 to observe "Everyone"
}
```

Setting `player_id = 0` observes "Everyone". Setting `player_id = 1` or `player_id = 2` switches the observation perspective to that player's economy/score data while remaining in observer mode.

### 1.3 Whether `disable_fog` Is Needed in Observer Mode

In observer mode, the engine already has full game state knowledge. However, `disable_fog` still controls whether the `raw_data.units` list includes units that would normally be hidden by fog of war. **Recommendation: still set `disable_fog=True`** to guarantee all units are returned with full attribute data (health, energy, shields, orders, etc.) regardless of vision state. Without it, units outside any player's vision may appear as `Snapshot` display type with limited data (no health, energy, orders, etc.).

The `disable_fog` field also exists on `RequestObservation` itself:

```protobuf
message RequestObservation {
  optional bool disable_fog = 1;
  optional uint32 game_loop = 2;
}
```

This allows toggling fog of war on a per-request basis during the replay, but for full extraction the simpler approach is to set it once in `RequestStartReplay`.

---

## 2. RequestStartReplay Configuration

### 2.1 Complete Field Reference

```protobuf
message RequestStartReplay {
  oneof replay {
    string replay_path = 1;    // Path to .SC2Replay file on disk
    bytes replay_data = 5;     // Raw bytes of the replay file
  }
  optional bytes map_data = 6;            // Override map data (if map is not in standard paths)
  optional int32 observed_player_id = 2;  // OMIT for observer mode
  optional InterfaceOptions options = 3;  // Which data interfaces to enable
  optional bool disable_fog = 4;          // Remove fog of war for full unit visibility
  optional bool realtime = 7;             // If false, replay advances only on RequestStep
  optional bool record_replay = 8;        // Allow RequestSaveReplay from a replay
}
```

### 2.2 Recommended Configuration for Observer Mode

```python
from s2clientprotocol import sc2api_pb2 as sc_pb

# Interface options: enable raw data + score, show hidden units
interface = sc_pb.InterfaceOptions(
    raw=True,                      # Enable raw unit data (ObservationRaw)
    score=True,                    # Enable score/economy data (Score)
    show_cloaked=True,             # Show cloaked units in raw_data.units
    show_burrowed_shadows=True,    # Show burrowed units in raw_data.units
    show_placeholders=True,        # Show queued/planned buildings
)

# Start replay in observer mode: DO NOT set observed_player_id
replay_request = sc_pb.RequestStartReplay(
    replay_data=replay_data,       # or replay_path="path/to/replay.SC2Replay"
    options=interface,
    disable_fog=True,              # Full unit visibility with complete attribute data
    # observed_player_id is intentionally OMITTED
    # realtime defaults to False (step mode - fastest processing)
)

controller.start_replay(replay_request)
```

### 2.3 ResponseStartReplay

```protobuf
message ResponseStartReplay {
  enum Error {
    MissingReplay = 1;
    InvalidReplayPath = 2;
    InvalidReplayData = 3;
    InvalidMapData = 4;
    InvalidObservedPlayerId = 5;
    MissingOptions = 6;
    LaunchError = 7;
  }
  optional Error error = 1;
  optional string error_details = 2;
}
```

If `observed_player_id` is set to an invalid value (e.g., 0, 3 in a 1v1), the error `InvalidObservedPlayerId` is returned. Omitting the field entirely is valid and enters observer mode.

### 2.4 InterfaceOptions - Complete Breakdown

```protobuf
message InterfaceOptions {
  optional bool raw = 1;                        // Enable raw data (ObservationRaw with units, effects, etc.)
  optional bool score = 2;                      // Enable score data (Score with ScoreDetails)
  optional SpatialCameraSetup feature_layer = 3; // Enable feature layer interface (omit to disable)
  optional SpatialCameraSetup render = 4;        // Enable rendered interface (omit to disable)
  optional bool show_cloaked = 5;               // Show cloaked units (default: hidden)
  optional bool show_burrowed_shadows = 9;      // Show burrowed units that produce shadows
  optional bool show_placeholders = 8;          // Show placeholder buildings (queued construction)
  optional bool raw_affects_selection = 6;      // Raw actions affect selection state (not relevant for replays)
  optional bool raw_crop_to_playable_area = 7;  // Coordinates relative to playable area instead of full map
}
```

**Fields relevant to replay extraction:**

| Field | Recommended | Effect |
|-------|-------------|--------|
| `raw` | `True` | Populates `observation.raw_data` with units, effects, events, player data |
| `score` | `True` | Populates `observation.score` with Score and ScoreDetails |
| `show_cloaked` | `True` | Cloaked units appear in `raw_data.units` (with `CloakState` indicating cloak status) |
| `show_burrowed_shadows` | `True` | Burrowed Zerg units appear in `raw_data.units` |
| `show_placeholders` | `True` | Buildings queued for construction (not yet started) appear in `raw_data.units` with `DisplayType.Placeholder` |
| `feature_layer` | Omit | Not needed for data extraction |
| `render` | Omit | Not needed for data extraction |
| `raw_affects_selection` | Omit | Only relevant for live games with agents |
| `raw_crop_to_playable_area` | `False` (default) | Keep full map coordinates for consistency |

---

## 3. Unit Proto - Complete Field Reference

The `Unit` message is defined in `raw.proto`. Below is every field, organized by population conditions.

### 3.1 Always-Present Fields

These fields are populated for all units regardless of display type or alliance.

| # | Field Name | Protobuf Type | Python Access | Description |
|---|-----------|---------------|---------------|-------------|
| 1 | `display_type` | `DisplayType` (enum) | `unit.display_type` | Visibility state: `Visible(1)`, `Snapshot(2)`, `Hidden(3)`, `Placeholder(4)` |
| 2 | `alliance` | `Alliance` (enum) | `unit.alliance` | Relationship to observer: `Self(1)`, `Ally(2)`, `Neutral(3)`, `Enemy(4)` |
| 3 | `tag` | `uint64` | `unit.tag` | Unique persistent identifier for this unit instance across frames |
| 4 | `unit_type` | `uint32` | `unit.unit_type` | Unit type ID (maps to UnitTypeData via RequestData) |
| 5 | `owner` | `int32` | `unit.owner` | Player ID who owns the unit (1, 2 for players; 0 for neutral) |
| 6 | `pos` | `Point` | `unit.pos` | Position in world coordinates (`unit.pos.x`, `unit.pos.y`, `unit.pos.z`) |
| 7 | `facing` | `float` | `unit.facing` | Direction the unit faces in radians (1 radian = 57.296 degrees) |
| 8 | `radius` | `float` | `unit.radius` | Physical radius of the unit |
| 9 | `build_progress` | `float` | `unit.build_progress` | Construction progress: `[0.0, 1.0]` where `1.0` = complete |
| 10 | `cloak` | `CloakState` (enum) | `unit.cloak` | Cloak state (see enum below) |
| 11 | `is_selected` | `bool` | `unit.is_selected` | Whether unit is in current selection |
| 12 | `is_on_screen` | `bool` | `unit.is_on_screen` | Whether unit is visible and within camera frustum |
| 13 | `is_blip` | `bool` | `unit.is_blip` | Whether unit is detected by sensor tower |
| 14 | `is_powered` | `bool` | `unit.is_powered` | Whether unit is powered by a pylon (Protoss buildings) |
| 15 | `is_active` | `bool` | `unit.is_active` | Whether building is actively training/researching (animated) |
| 16 | `buff_ids` | `repeated uint32` | `unit.buff_ids` | List of active buff IDs (maps to BuffData via RequestData) |
| 17 | `detect_range` | `float` | `unit.detect_range` | Detection range (for detector units like Observer, Overseer) |
| 18 | `radar_range` | `float` | `unit.radar_range` | Radar range (for sensor tower units) |
| 19 | `attack_upgrade_level` | `int32` | `unit.attack_upgrade_level` | Current attack upgrade level (0, 1, 2, or 3) |
| 20 | `armor_upgrade_level` | `int32` | `unit.armor_upgrade_level` | Current armor upgrade level (0, 1, 2, or 3) |
| 21 | `shield_upgrade_level` | `int32` | `unit.shield_upgrade_level` | Current shield upgrade level (Protoss only; 0, 1, 2, or 3) |

### 3.2 Fields NOT Populated for Snapshots

These fields are only present when `display_type` is `Visible` (not `Snapshot`). With `disable_fog=True` in observer mode, most units will be `Visible`, so these are generally available.

| # | Field Name | Protobuf Type | Python Access | Description |
|---|-----------|---------------|---------------|-------------|
| 22 | `health` | `float` | `unit.health` | Current health points |
| 23 | `health_max` | `float` | `unit.health_max` | Maximum health points |
| 24 | `shield` | `float` | `unit.shield` | Current shield points (Protoss units; 0 for non-Protoss) |
| 25 | `shield_max` | `float` | `unit.shield_max` | Maximum shield points |
| 26 | `energy` | `float` | `unit.energy` | Current energy (caster units only; 0 for non-casters) |
| 27 | `energy_max` | `float` | `unit.energy_max` | Maximum energy |
| 28 | `mineral_contents` | `int32` | `unit.mineral_contents` | Remaining minerals (mineral field units only) |
| 29 | `vespene_contents` | `int32` | `unit.vespene_contents` | Remaining vespene (geyser units only) |
| 30 | `is_flying` | `bool` | `unit.is_flying` | Whether the unit is currently airborne (e.g., lifted Terran building) |
| 31 | `is_burrowed` | `bool` | `unit.is_burrowed` | Whether the unit is burrowed (Zerg) |
| 32 | `is_hallucination` | `bool` | `unit.is_hallucination` | Whether unit is a hallucination (only for own units or detected hallucinations) |
| 33 | `weapon_cooldown` | `float` | `unit.weapon_cooldown` | Time remaining on weapon cooldown |

### 3.3 Fields NOT Populated for Enemy Units

These fields are only populated for units belonging to the observed player (or in observer mode, these may be populated for all players -- this is a key behavior to verify during implementation). In player-perspective mode, these are only for `alliance == Self`.

| # | Field Name | Protobuf Type | Python Access | Description |
|---|-----------|---------------|---------------|-------------|
| 34 | `orders` | `repeated UnitOrder` | `unit.orders` | Current command queue (see UnitOrder section) |
| 35 | `add_on_tag` | `uint64` | `unit.add_on_tag` | Tag of attached add-on (Tech Lab / Reactor; Terran only) |
| 36 | `passengers` | `repeated PassengerUnit` | `unit.passengers` | Units loaded in transport (Medivac, Warp Prism, etc.) |
| 37 | `cargo_space_taken` | `int32` | `unit.cargo_space_taken` | Cargo slots currently used |
| 38 | `cargo_space_max` | `int32` | `unit.cargo_space_max` | Maximum cargo slots |
| 39 | `assigned_harvesters` | `int32` | `unit.assigned_harvesters` | Workers assigned to this town hall / gas building |
| 40 | `ideal_harvesters` | `int32` | `unit.ideal_harvesters` | Ideal number of workers for this town hall / gas building |
| 41 | `engaged_target_tag` | `uint64` | `unit.engaged_target_tag` | Tag of the unit this unit is actively attacking |
| 42 | `buff_duration_remain` | `int32` | `unit.buff_duration_remain` | Remaining duration of buff/temporary unit (e.g., MULE, Broodling, Chronoboost) |
| 43 | `buff_duration_max` | `int32` | `unit.buff_duration_max` | Maximum duration of buff/temporary unit |
| 44 | `rally_targets` | `repeated RallyTarget` | `unit.rally_targets` | Rally point targets for production buildings |

**Total: 44 fields on the Unit proto message.**

### 3.4 Enum Definitions

**DisplayType:**
| Value | Name | Description |
|-------|------|-------------|
| 1 | `Visible` | Fully visible with all data populated |
| 2 | `Snapshot` | Dimmed remnant in fog of war; limited data (no health/energy/orders) |
| 3 | `Hidden` | Fully hidden (only appears with `show_cloaked` / `show_burrowed_shadows`) |
| 4 | `Placeholder` | Building queued but not started (only with `show_placeholders`) |

**Alliance:**
| Value | Name | Description |
|-------|------|-------------|
| 1 | `Self` | Belongs to the observed player |
| 2 | `Ally` | Allied player's unit |
| 3 | `Neutral` | Non-player unit (mineral fields, vespene geysers, destructible rocks, Xel'Naga towers) |
| 4 | `Enemy` | Enemy player's unit |

**CloakState:**
| Value | Name | Description |
|-------|------|-------------|
| 0 | `CloakedUnknown` | Under fog; cloak status unknown |
| 1 | `Cloaked` | Cloaked and invisible to enemies |
| 2 | `CloakedDetected` | Cloaked but detected (visible with shimmer) |
| 3 | `NotCloaked` | Not cloaked |
| 4 | `CloakedAllied` | Cloaked allied unit (visible to allies) |

### 3.5 Conditional Field Population Summary

| Condition | Fields Affected | Notes |
|-----------|----------------|-------|
| Protoss units only | `shield`, `shield_max`, `shield_upgrade_level` | Non-Protoss units will have these as 0 or unset |
| Caster units only | `energy`, `energy_max` | Non-caster units will have 0 or unset |
| Mineral fields only | `mineral_contents` | Only for neutral mineral patch unit types |
| Vespene geysers only | `vespene_contents` | Only for neutral geyser and built extractor/assimilator/refinery |
| Detector units only | `detect_range` | Observer, Overseer, Missile Turret, Photon Cannon, Spore Crawler |
| Sensor tower only | `radar_range` | Terran Sensor Tower |
| Transport units only | `passengers`, `cargo_space_taken`, `cargo_space_max` | Medivac, Warp Prism, Overlord (with transport upgrade), Nydus |
| Town hall / gas only | `assigned_harvesters`, `ideal_harvesters` | Command Center variants, Nexus, Hatchery variants, gas buildings |
| Terran buildings only | `add_on_tag` | Barracks, Factory, Starport (when add-on attached) |
| Production buildings | `rally_targets` | Buildings with rally point set |
| Temporary units/buffs | `buff_duration_remain`, `buff_duration_max` | MULEs, Broodlings, Chronoboost, Auto-Turrets |
| `display_type == Snapshot` | health, energy, shield, orders, etc. | NOT populated for snapshot units |
| Enemy units (player perspective) | orders, passengers, cargo, harvesters, engaged_target | NOT populated for enemy units |

---

## 4. PlayerCommon Fields

### 4.1 Complete Field List

```protobuf
message PlayerCommon {
  optional uint32 player_id = 1;       // Which player this data belongs to
  optional uint32 minerals = 2;        // Current unspent minerals
  optional uint32 vespene = 3;         // Current unspent vespene gas
  optional uint32 food_cap = 4;        // Total supply capacity
  optional uint32 food_used = 5;       // Total supply used
  optional uint32 food_army = 6;       // Supply used by army units
  optional uint32 food_workers = 7;    // Supply used by workers
  optional uint32 idle_worker_count = 8; // Number of idle workers
  optional uint32 army_count = 9;      // Number of army units
  optional uint32 warp_gate_count = 10; // Number of warp gates (Protoss only; 0 for others)
  optional uint32 larva_count = 11;    // Number of available larvae (Zerg only; 0 for others)
}
```

### 4.2 Field Details

| Field | Type | Description | Race-Specific |
|-------|------|-------------|---------------|
| `player_id` | `uint32` | Player ID this data belongs to (1 or 2 in standard 1v1) | No |
| `minerals` | `uint32` | Current unspent mineral count | No |
| `vespene` | `uint32` | Current unspent vespene gas count | No |
| `food_cap` | `uint32` | Total supply capacity (max 200) | No |
| `food_used` | `uint32` | Total supply currently in use | No |
| `food_army` | `uint32` | Supply consumed by non-worker military units | No |
| `food_workers` | `uint32` | Supply consumed by workers (SCV, Probe, Drone) | No |
| `idle_worker_count` | `uint32` | Workers not currently performing any task | No |
| `army_count` | `uint32` | Total number of non-worker military units | No |
| `warp_gate_count` | `uint32` | Number of Warp Gates available for warping in | Protoss |
| `larva_count` | `uint32` | Number of larvae available for morphing | Zerg |

### 4.3 Per-Player Access in Observer Mode

In observer mode (no `observed_player_id` set), the `player_common` field in the `Observation` message contains data for the observer perspective. To get per-player data, use the `ActionObserverPlayerPerspective` observer action to switch the viewed player:

```python
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import raw_pb2 as raw_pb

# Switch observation perspective to player 1
obs_action = sc_pb.RequestObserverAction(
    actions=[sc_pb.ObserverAction(
        player_perspective=sc_pb.ActionObserverPlayerPerspective(player_id=1)
    )]
)
controller.observer_action(obs_action)

# Now observe -- player_common will reflect player 1's economy
obs_p1 = controller.observe()
p1_minerals = obs_p1.observation.player_common.minerals

# Switch to player 2
obs_action = sc_pb.RequestObserverAction(
    actions=[sc_pb.ObserverAction(
        player_perspective=sc_pb.ActionObserverPlayerPerspective(player_id=2)
    )]
)
controller.observer_action(obs_action)

# Observe again -- player_common now reflects player 2's economy
obs_p2 = controller.observe()
p2_minerals = obs_p2.observation.player_common.minerals
```

**Note**: The `ActionObserverPlayerPerspective` is listed as "Not implemented" in some versions of the proto comments. If this is the case, an alternative is to observe once (getting one player's data), then the `player_common.player_id` field tells you which player's data you received. Testing is required to confirm exact behavior in observer mode. If perspective switching does not work, a fallback is to query the observation twice (the engine may automatically alternate or provide a combined view).

**Alternative approach if observer action is not available**: In observer mode, the engine may populate `player_common` with the observer's aggregated view, or it may cycle through players. The implementation should check `player_common.player_id` to determine which player's data was returned and handle accordingly.

---

## 5. Score / ScoreDetails Fields

### 5.1 Score Message

```protobuf
message Score {
  enum ScoreType {
    Curriculum = 1;   // Map-generated score (custom maps with special scoring)
    Melee = 2;        // Standard melee score: units/buildings value + minerals + vespene
  }
  optional ScoreType score_type = 6;
  optional int32 score = 7;               // Overall score value
  optional ScoreDetails score_details = 8; // Detailed breakdown
}
```

### 5.2 ScoreDetails - Complete Field List

| # | Field Name | Protobuf Type | Description |
|---|-----------|---------------|-------------|
| 1 | `idle_production_time` | `float` | Cumulative time production buildings have been idle (stacks for multiple buildings) |
| 2 | `idle_worker_time` | `float` | Cumulative time workers have been idle (stacks for multiple workers) |
| 3 | `total_value_units` | `float` | Sum of minerals + vespene spent on completed units |
| 4 | `total_value_structures` | `float` | Sum of minerals + vespene spent on completed structures |
| 5 | `killed_value_units` | `float` | Sum of minerals + vespene of enemy units destroyed |
| 6 | `killed_value_structures` | `float` | Sum of minerals + vespene of enemy structures destroyed |
| 7 | `collected_minerals` | `float` | Total minerals collected over the entire game |
| 8 | `collected_vespene` | `float` | Total vespene collected over the entire game |
| 9 | `collection_rate_minerals` | `float` | Estimated mineral income per minute (current rate) |
| 10 | `collection_rate_vespene` | `float` | Estimated vespene income per minute (current rate) |
| 11 | `spent_minerals` | `float` | Running total of minerals spent (decremented on cancel) |
| 12 | `spent_vespene` | `float` | Running total of vespene spent (decremented on cancel) |
| 13 | `food_used` | `CategoryScoreDetails` | Supply used, broken down by category |
| 14 | `killed_minerals` | `CategoryScoreDetails` | Enemy minerals destroyed, by category |
| 15 | `killed_vespene` | `CategoryScoreDetails` | Enemy vespene destroyed, by category |
| 16 | `lost_minerals` | `CategoryScoreDetails` | Own minerals lost, by category |
| 17 | `lost_vespene` | `CategoryScoreDetails` | Own vespene lost, by category |
| 18 | `friendly_fire_minerals` | `CategoryScoreDetails` | Minerals lost from destroying own units/buildings |
| 19 | `friendly_fire_vespene` | `CategoryScoreDetails` | Vespene lost from destroying own units/buildings |
| 20 | `used_minerals` | `CategoryScoreDetails` | Currently in-use minerals by category (decremented when unit dies) |
| 21 | `used_vespene` | `CategoryScoreDetails` | Currently in-use vespene by category (decremented when unit dies) |
| 22 | `total_used_minerals` | `CategoryScoreDetails` | Lifetime total minerals used by category (never decremented) |
| 23 | `total_used_vespene` | `CategoryScoreDetails` | Lifetime total vespene used by category (never decremented) |
| 24 | `total_damage_dealt` | `VitalScoreDetails` | Total damage dealt to opponent (life, shields, energy) |
| 25 | `total_damage_taken` | `VitalScoreDetails` | Total damage taken (life, shields, energy) |
| 26 | `total_healed` | `VitalScoreDetails` | Total health/shields/energy healed |
| 27 | `current_apm` | `float` | Recent raw Actions Per Minute |
| 28 | `current_effective_apm` | `float` | Recent Effective Actions Per Minute (filters redundant actions) |

### 5.3 CategoryScoreDetails

Each `CategoryScoreDetails` breaks down a value into game categories:

```protobuf
message CategoryScoreDetails {
  optional float none = 1;        // No category defined in game data
  optional float army = 2;        // Military units (not workers)
  optional float economy = 3;     // Town halls, supply, vespene buildings, workers
  optional float technology = 4;  // Production/upgrade structures (Barracks, Engineering Bay, etc.)
  optional float upgrade = 5;     // Upgrades (weapons, armor, warp gate, etc.)
}
```

### 5.4 VitalScoreDetails

```protobuf
message VitalScoreDetails {
  optional float life = 1;       // Health/hit points
  optional float shields = 2;    // Shield points
  optional float energy = 3;     // Energy points
}
```

### 5.5 Per-Player Access in Observer Mode

Score data follows the same pattern as `player_common` -- it is perspective-dependent and reflects the observed player's score. In observer mode, use the same `ActionObserverPlayerPerspective` mechanism described in Section 4.3 to switch between players before querying score data.

---

## 6. ObservationRaw Structure

### 6.1 Complete Structure

```protobuf
message ObservationRaw {
  optional PlayerRaw player = 1;       // Player-specific raw data
  repeated Unit units = 2;             // ALL units on the map
  optional MapState map_state = 3;     // Fog of war, creep layer
  optional Event event = 4;            // Units that died this frame
  repeated Effect effects = 5;         // Active map effects (storms, irradiate, etc.)
  repeated RadarRing radar = 6;        // Sensor tower radar rings
}
```

### 6.2 PlayerRaw

```protobuf
message PlayerRaw {
  repeated PowerSource power_sources = 1;   // Active pylon power fields (Protoss)
  optional Point camera = 2;                // Current camera position
  repeated uint32 upgrade_ids = 3;          // Completed upgrades for the observed player
}
```

**`power_sources`**: Each `PowerSource` contains:
```protobuf
message PowerSource {
  optional Point pos = 1;     // Center position of the power field
  optional float radius = 2;  // Radius of the power field
  optional uint64 tag = 3;    // Tag of the pylon providing power
}
```

**`upgrade_ids`**: List of upgrade IDs that have been completed. Maps to `UpgradeData` via `RequestData`. In observer mode, this reflects the observed perspective's upgrades. To get both players' upgrades, switch perspective using observer actions.

### 6.3 MapState

```protobuf
message MapState {
  optional ImageData visibility = 1;   // 1-byte visibility layer per cell
  optional ImageData creep = 2;        // 1-bit creep layer per cell (Zerg creep)
}
```

### 6.4 Event

```protobuf
message Event {
  repeated uint64 dead_units = 1;   // Tags of units that died this step
}
```

The `dead_units` list contains the `tag` values of units that were destroyed during the most recent game step. With `disable_fog=True`, this includes deaths of all units regardless of visibility. Cross-reference these tags with previously observed units to determine what died.

### 6.5 Effect

```protobuf
message Effect {
  optional uint32 effect_id = 1;     // Effect type ID (maps to EffectData via RequestData)
  repeated Point2D pos = 2;          // Positions affected (may be multiple, e.g., Lurker attack)
  optional Alliance alliance = 3;    // Who created the effect
  optional int32 owner = 4;          // Player ID of the effect creator
  optional float radius = 5;         // Area of effect radius
}
```

Effects include persistent map effects like Psionic Storm, Corrosive Bile, Lurker spines, Liberator zones, etc.

### 6.6 RadarRing

```protobuf
message RadarRing {
  optional Point pos = 1;
  optional float radius = 2;
}
```

Represents sensor tower detection rings on the map.

---

## 7. Supporting Types

### 7.1 Point / Position Data

The protobuf defines three point types:

```protobuf
// 3D point on the game board (used for unit positions)
message Point {
  optional float x = 1;
  optional float y = 2;
  optional float z = 3;
}

// 2D point on the game board (used for ability targets, effects)
message Point2D {
  optional float x = 1;
  optional float y = 2;
}

// Integer point (used for screen/minimap coordinates)
message PointI {
  optional int32 x = 1;
  optional int32 y = 2;
}
```

**Coordinate system**: The game board origin (0, 0) is at the **bottom-left** of the map. X increases to the right, Y increases upward. Z represents terrain height. All coordinates use floating-point map units (not pixels).

**Python access for unit position:**
```python
x = unit.pos.x   # float, horizontal position
y = unit.pos.y   # float, vertical position
z = unit.pos.z   # float, terrain height
```

### 7.2 UnitOrder

```protobuf
message UnitOrder {
  optional uint32 ability_id = 1;              // The ability being executed
  oneof target {
    Point target_world_space_pos = 2;          // Target ground position (for move, attack-move, build)
    uint64 target_unit_tag = 3;                // Target unit tag (for attack, repair, heal)
  }
  optional float progress = 4;                // Progress of train/research abilities: [0.0, 1.0]
}
```

**Python access:**
```python
for order in unit.orders:
    ability = order.ability_id                    # int: ability being executed
    progress = order.progress                     # float: training/research progress

    # Check which target type is set
    if order.HasField('target_world_space_pos'):
        target_pos = order.target_world_space_pos  # Point message
        tx, ty, tz = target_pos.x, target_pos.y, target_pos.z
    elif order.HasField('target_unit_tag'):
        target_tag = order.target_unit_tag         # uint64
```

**Note**: `orders` is a repeated field, so a unit can have multiple queued orders. The first order is the currently executing one.

### 7.3 PassengerUnit

Units loaded inside transports:

```protobuf
message PassengerUnit {
  optional uint64 tag = 1;
  optional float health = 2;
  optional float health_max = 3;
  optional float shield = 4;
  optional float shield_max = 7;
  optional float energy = 5;
  optional float energy_max = 8;
  optional uint32 unit_type = 6;
}
```

### 7.4 RallyTarget

Rally points set on production buildings:

```protobuf
message RallyTarget {
  optional Point point = 1;    // Position of the rally point (always filled)
  optional uint64 tag = 2;     // Tag of the target unit (only if rallied to a unit)
}
```

### 7.5 Buff IDs

Buffs are referenced by numeric ID in `unit.buff_ids`. To resolve the name of a buff, use `RequestData` with `buff_id=True`:

```python
# Request buff data from the game
data_request = sc_pb.RequestData(buff_id=True)
data_response = controller.data(data_request)

# Build lookup table: buff_id -> buff_name
buff_lookup = {}
for buff in data_response.buffs:
    buff_lookup[buff.buff_id] = buff.name

# Usage
for buff_id in unit.buff_ids:
    buff_name = buff_lookup.get(buff_id, f"Unknown({buff_id})")
```

**BuffData proto:**
```protobuf
message BuffData {
  optional uint32 buff_id = 1;   // Stable ID
  optional string name = 2;     // Human-readable name
}
```

### 7.6 EffectData

Static effect metadata (resolve `effect_id` from `Effect` messages):

```protobuf
message EffectData {
  optional uint32 effect_id = 1;       // Stable ID
  optional string name = 2;           // Internal name
  optional string friendly_name = 3;  // Human-readable name
  optional float radius = 4;          // Default radius
}
```

### 7.7 UnitTypeData

Static data about unit types (resolve `unit_type` from `Unit` messages):

```protobuf
message UnitTypeData {
  optional uint32 unit_id = 1;           // Stable ID
  optional string name = 2;             // Internal name (e.g., "Marine", "Zergling")
  optional bool available = 3;          // Whether this unit exists in the current mod/map
  optional uint32 cargo_size = 4;       // Cargo space this unit occupies in transports
  optional uint32 mineral_cost = 12;    // Mineral cost to build
  optional uint32 vespene_cost = 13;    // Vespene cost to build
  optional float food_required = 14;    // Supply required
  optional float food_provided = 18;    // Supply provided (overlords, pylons, etc.)
  optional uint32 ability_id = 15;      // Ability that builds this unit
  optional Race race = 16;             // Race: Terran(1), Zerg(2), Protoss(3)
  optional float build_time = 17;      // Build time in game seconds
  optional bool has_vespene = 19;      // Whether this unit contains vespene
  optional bool has_minerals = 20;     // Whether this unit contains minerals
  optional float sight_range = 25;     // Vision range
  repeated uint32 tech_alias = 21;     // Other units satisfying same tech requirement
  optional uint32 unit_alias = 22;     // Morphed variant of this unit
  optional uint32 tech_requirement = 23; // Required structure to build
  optional bool require_attached = 24;  // Whether tech_requirement must be an attached add-on
  repeated Attribute attributes = 8;   // Unit attributes (Light, Armored, Biological, etc.)
  optional float movement_speed = 9;   // Base movement speed
  optional float armor = 10;           // Base armor value
  repeated Weapon weapons = 11;        // Weapon data (damage, range, speed, bonuses)
}
```

### 7.8 UpgradeData

Static data about upgrades (resolve `upgrade_ids` from `PlayerRaw`):

```protobuf
message UpgradeData {
  optional uint32 upgrade_id = 1;    // Stable ID
  optional string name = 2;         // Internal name
  optional uint32 mineral_cost = 3;  // Mineral cost
  optional uint32 vespene_cost = 4;  // Vespene cost
  optional float research_time = 5;  // Research time in game seconds
  optional uint32 ability_id = 6;    // Ability that researches this upgrade
}
```

### 7.9 AbilityData

Static data about abilities (resolve `ability_id` from `UnitOrder`):

```protobuf
message AbilityData {
  optional uint32 ability_id = 1;         // Stable ID
  optional string link_name = 2;          // Catalog name
  optional uint32 link_index = 3;         // Catalog index
  optional string button_name = 4;        // Command card display name
  optional string friendly_name = 5;      // Human-friendly name
  optional string hotkey = 6;             // Keyboard hotkey
  optional uint32 remaps_to_ability_id = 7; // More generic ability ID this maps to
  optional bool available = 8;            // Whether ability exists in current mod/map
  optional Target target = 9;            // Target type: None, Point, Unit, PointOrUnit, PointOrNone
  optional bool allow_minimap = 10;       // Can be cast on minimap
  optional bool allow_autocast = 11;      // Supports autocast
  optional bool is_building = 12;         // Requires placement (building construction)
  optional float footprint_radius = 13;   // Estimated building footprint size
  optional bool is_instant_placement = 14; // Placed next to existing structure (add-on)
  optional float cast_range = 15;         // Ability cast range
}
```

### 7.10 RequestData - Getting All Static Data

```python
# Request all static game data at once
data_request = sc_pb.RequestData(
    ability_id=True,
    unit_type_id=True,
    upgrade_id=True,
    buff_id=True,
    effect_id=True,
)
data_response = controller.data(data_request)

# Build lookup tables
unit_type_lookup = {u.unit_id: u for u in data_response.units}
ability_lookup = {a.ability_id: a for a in data_response.abilities}
upgrade_lookup = {u.upgrade_id: u for u in data_response.upgrades}
buff_lookup = {b.buff_id: b for b in data_response.buffs}
effect_lookup = {e.effect_id: e for e in data_response.effects}
```

### 7.11 Attribute Enum

Unit type attributes used in `UnitTypeData.attributes`:

```protobuf
enum Attribute {
  Light = 1;
  Armored = 2;
  Biological = 3;
  Mechanical = 4;
  Robotic = 5;
  Psionic = 6;
  Massive = 7;
  Structure = 8;
  Hover = 9;
  Heroic = 10;
  Summoned = 11;
}
```

### 7.12 Race Enum

```protobuf
enum Race {
  NoRace = 0;
  Terran = 1;
  Zerg = 2;
  Protoss = 3;
  Random = 4;
}
```

---

## 8. Practical Implementation Notes

### 8.1 Python Access Patterns Using s2clientprotocol

The `s2clientprotocol` Python package provides generated protobuf classes. Import pattern:

```python
from s2clientprotocol import sc2api_pb2 as sc_pb    # Main API messages
from s2clientprotocol import raw_pb2 as raw_pb       # Raw observation types
from s2clientprotocol import score_pb2 as score_pb   # Score types
from s2clientprotocol import common_pb2 as common_pb # Point, Race, etc.
from s2clientprotocol import data_pb2 as data_pb     # UnitTypeData, AbilityData, etc.
```

### 8.2 Iterating Proto Fields Programmatically

For dynamic/generic field extraction (building dataframe columns automatically from proto fields):

```python
def extract_unit_fields(unit):
    """
    Dynamically extract all set fields from a Unit protobuf message.
    Returns a dict of field_name -> value for all populated fields.
    """
    result = {}
    # ListFields() returns only fields that are explicitly set (non-default)
    for field_descriptor, value in unit.ListFields():
        field_name = field_descriptor.name

        if field_descriptor.type == field_descriptor.TYPE_MESSAGE:
            # Nested message (e.g., pos, orders)
            if field_descriptor.label == field_descriptor.LABEL_REPEATED:
                # Repeated message field (orders, passengers, buff_ids, etc.)
                result[field_name] = list(value)
            else:
                # Singular message field (pos)
                result[field_name] = value
        elif field_descriptor.label == field_descriptor.LABEL_REPEATED:
            # Repeated scalar field (buff_ids is repeated uint32)
            result[field_name] = list(value)
        else:
            # Scalar field
            result[field_name] = value

    return result
```

### 8.3 Checking if Optional Fields Have Values vs Default

In protobuf2 (which s2client-proto uses), optional fields have a concept of "being set" vs "having the default value". This distinction matters for fields like `shield` (which is 0 for non-Protoss but also 0 for a Protoss unit with depleted shields).

```python
# HasField() checks if a singular field was explicitly set in the message
if unit.HasField('shield'):
    # Field was set in the message (unit has shields, even if current value is 0)
    shield_value = unit.shield
else:
    # Field was NOT set (unit does not have shields at all)
    shield_value = None

# For repeated fields, check length
if len(unit.orders) > 0:
    # Unit has orders
    pass

if len(unit.buff_ids) > 0:
    # Unit has active buffs
    pass

# IMPORTANT: HasField() only works on singular (non-repeated) fields
# For repeated fields (orders, buff_ids, passengers, rally_targets),
# check len() instead
```

**Caveat**: In the Python protobuf API, `HasField()` works for singular fields but NOT for repeated fields. Repeated fields always exist (as empty lists) even if not populated. For enum fields, the default value is typically the first enum value (value 0), which can be confusing -- always check `HasField()` rather than comparing to 0.

### 8.4 Protobuf Enum Access in Python

```python
from s2clientprotocol import raw_pb2 as raw_pb

# Enum values are accessed as module-level constants
if unit.display_type == raw_pb.Visible:
    print("Unit is fully visible")
elif unit.display_type == raw_pb.Snapshot:
    print("Unit is a fog-of-war snapshot")
elif unit.display_type == raw_pb.Hidden:
    print("Unit is hidden")
elif unit.display_type == raw_pb.Placeholder:
    print("Unit is a placeholder building")

# Alliance enum
if unit.alliance == raw_pb.Self:
    print("Own unit")
elif unit.alliance == raw_pb.Enemy:
    print("Enemy unit")
elif unit.alliance == raw_pb.Neutral:
    print("Neutral unit")

# CloakState enum
if unit.cloak == raw_pb.NotCloaked:
    print("Not cloaked")
elif unit.cloak == raw_pb.Cloaked:
    print("Cloaked")
elif unit.cloak == raw_pb.CloakedDetected:
    print("Cloaked but detected")
```

### 8.5 Websocket Connection to SC2

The raw s2client-proto API communicates over websockets. The SC2 client listens on a configurable port:

```
SC2.exe -listen 127.0.0.1 -port 5000
```

Connect to: `ws://127.0.0.1:5000/sc2api`

Communication is via serialized protobuf `Request` and `Response` messages:

```python
import websocket
from s2clientprotocol import sc2api_pb2 as sc_pb

# Connect to SC2 instance
ws = websocket.create_connection("ws://127.0.0.1:5000/sc2api")

# Send a request
request = sc_pb.Request(ping=sc_pb.RequestPing())
ws.send(request.SerializeToString())

# Receive response
response_data = ws.recv()
response = sc_pb.Response()
response.ParseFromString(response_data)
print(f"Game version: {response.ping.game_version}")
```

### 8.6 Complete Replay Processing Loop

```python
import websocket
from s2clientprotocol import sc2api_pb2 as sc_pb

def process_replay(ws, replay_path):
    """
    Process a replay using the raw s2client-proto API in observer mode.

    Args:
        ws: Active websocket connection to SC2 instance
        replay_path: Path to the .SC2Replay file

    Returns:
        List of per-step observation data dicts
    """
    # 1. Get replay info for metadata
    req = sc_pb.Request(
        replay_info=sc_pb.RequestReplayInfo(replay_path=replay_path)
    )
    ws.send(req.SerializeToString())
    resp = sc_pb.Response()
    resp.ParseFromString(ws.recv())
    replay_info = resp.replay_info

    # 2. Start replay in observer mode (no observed_player_id)
    interface = sc_pb.InterfaceOptions(
        raw=True,
        score=True,
        show_cloaked=True,
        show_burrowed_shadows=True,
        show_placeholders=True,
    )
    req = sc_pb.Request(
        start_replay=sc_pb.RequestStartReplay(
            replay_path=replay_path,
            options=interface,
            disable_fog=True,
            # observed_player_id intentionally omitted
        )
    )
    ws.send(req.SerializeToString())
    resp = sc_pb.Response()
    resp.ParseFromString(ws.recv())

    if resp.start_replay.HasField('error'):
        raise RuntimeError(f"Failed to start replay: {resp.start_replay.error_details}")

    # 3. Request static game data (unit types, abilities, upgrades, buffs, effects)
    req = sc_pb.Request(
        data=sc_pb.RequestData(
            ability_id=True,
            unit_type_id=True,
            upgrade_id=True,
            buff_id=True,
            effect_id=True,
        )
    )
    ws.send(req.SerializeToString())
    resp = sc_pb.Response()
    resp.ParseFromString(ws.recv())
    game_data = resp.data

    # 4. Main observation loop
    all_observations = []
    step_size = 16  # ~0.7 seconds at "Faster" speed

    while True:
        # Request observation
        req = sc_pb.Request(observation=sc_pb.RequestObservation())
        ws.send(req.SerializeToString())
        resp = sc_pb.Response()
        resp.ParseFromString(ws.recv())

        obs_response = resp.observation

        # Check for game end
        if len(obs_response.player_result) > 0:
            break

        obs = obs_response.observation
        game_loop = obs.game_loop

        # Extract units
        units_data = []
        for unit in obs.raw_data.units:
            units_data.append({
                'tag': unit.tag,
                'unit_type': unit.unit_type,
                'owner': unit.owner,
                'pos_x': unit.pos.x,
                'pos_y': unit.pos.y,
                'pos_z': unit.pos.z,
                'health': unit.health if unit.HasField('health') else None,
                'health_max': unit.health_max if unit.HasField('health_max') else None,
                'shield': unit.shield if unit.HasField('shield') else None,
                'energy': unit.energy if unit.HasField('energy') else None,
                'build_progress': unit.build_progress,
                # ... additional fields as needed
            })

        # Extract economy (player_common)
        pc = obs.player_common
        economy = {
            'player_id': pc.player_id,
            'minerals': pc.minerals,
            'vespene': pc.vespene,
            'food_cap': pc.food_cap,
            'food_used': pc.food_used,
        }

        # Extract score
        if obs.HasField('score'):
            score = obs.score.score_details
            score_data = {
                'collection_rate_minerals': score.collection_rate_minerals,
                'collection_rate_vespene': score.collection_rate_vespene,
                'spent_minerals': score.spent_minerals,
                'spent_vespene': score.spent_vespene,
            }
        else:
            score_data = {}

        all_observations.append({
            'game_loop': game_loop,
            'units': units_data,
            'economy': economy,
            'score': score_data,
            'dead_units': list(obs.raw_data.event.dead_units) if obs.raw_data.HasField('event') else [],
        })

        # Step the replay forward
        req = sc_pb.Request(step=sc_pb.RequestStep(count=step_size))
        ws.send(req.SerializeToString())
        resp = sc_pb.Response()
        resp.ParseFromString(ws.recv())

        # Check if replay ended
        if resp.status == sc_pb.ended:
            break

    return all_observations
```

### 8.7 Performance: Singlestep Mode for Maximum Speed

When `realtime` is `False` (the default for `RequestStartReplay`), the replay only advances when `RequestStep` is sent. The engine processes each step at CPU speed with no frame-rate cap. This means:

- Replays process as fast as the CPU can simulate + the network round-trip for each request/response
- For maximum throughput, keep the websocket request queue saturated (the protocol supports pipelining -- you can send the next `RequestStep` before receiving the previous `ResponseObservation`)
- A step count of 1 gives per-game-loop resolution; higher values skip frames for faster processing

At "Faster" game speed, there are **22.4 game loops per second** of real-time gameplay. A typical 15-minute game is approximately 20,160 game loops.

---

## 9. Key Findings for Migration

### 9.1 What Changes from pysc2 to Raw API

| Component | pysc2 Approach | Raw API Approach |
|-----------|---------------|------------------|
| SC2 process management | `run_configs.get()`, `run_config.start()` | Must manage SC2 process launch and websocket connection directly |
| Replay loading | `controller.start_replay(request)` | Send `RequestStartReplay` over websocket |
| Observation | `controller.observe()` | Send `RequestObservation`, parse `ResponseObservation` |
| Stepping | `controller.step(count)` | Send `RequestStep(count=N)` |
| Version detection | `run_config.version()`, auto version matching | Use `RequestReplayInfo` to get `base_build` and `data_version`, launch correct SC2 binary with `-dataVersion` flag |
| `observed_player_id` | **Forced to 1 or 2** (pysc2 sets it always) | **Can be omitted** for observer mode |
| Economy data | Single player per pass | Per-player via observer perspective switching or single observer view |

### 9.2 What pysc2 Provides That Must Be Replicated

1. **SC2 process launch and lifecycle management**: pysc2 handles finding the SC2 binary, launching it with correct command-line arguments, and cleaning up. The raw API approach must:
   - Locate the SC2 installation directory
   - Find the correct binary version (using `base_build` from replay info)
   - Launch SC2 with `-listen`, `-port`, and optionally `-dataVersion` flags
   - Connect via websocket
   - Handle process cleanup on completion or error

2. **Version compatibility**: pysc2 uses `run_configs` to match replay versions to SC2 binaries. The raw approach must:
   - Parse replay info to get `base_build` and `data_version`
   - Map these to the correct SC2 executable in the Versions directory
   - Pass `-dataVersion` on the command line if needed

3. **Protobuf message construction**: pysc2 wraps protobuf creation in convenience methods. Direct usage requires constructing `Request` messages manually (as shown in examples above).

### 9.3 What Can Be Dropped

1. **pysc2's forced `observed_player_id`**: This is the primary reason for migration. pysc2 always sets this field, preventing observer mode.

2. **Feature layer / render interfaces**: pysc2 is designed for ML agent training and always configures feature layers. For data extraction, only `raw=True` and `score=True` are needed.

3. **Agent/bot framework**: pysc2's `Agent` base class, action spaces, and reward computation are not needed for replay extraction.

4. **Two-pass extraction**: If observer mode works as documented, the entire second replay pass for P2 economy/upgrades can be eliminated.

### 9.4 Migration Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| `ActionObserverPlayerPerspective` marked "Not implemented" in some proto comments | High | Test empirically. If not working, fall back to: (a) check if `player_common` in observer mode automatically provides both players' data, or (b) keep two-pass as fallback |
| Observer mode behavior undocumented for replays specifically | Medium | The proto comments and community usage confirm observer mode works for live games. Replay behavior should be identical but needs verification |
| SC2 process management complexity | Medium | Consider using pysc2's `run_configs` module in isolation (just for SC2 launch) while using raw websocket for the protocol |
| Orders/passengers/cargo may not populate for enemy units even in observer mode | Low | With `disable_fog=True`, all units are "visible" but the engine may still restrict certain fields based on ownership. Test and document which fields are available for all units vs only the observed player's units |
| Protobuf field presence semantics (0 vs unset) | Low | Use `HasField()` consistently for singular fields, `len()` for repeated fields |

### 9.5 Recommended Migration Strategy

1. **Phase 1 - Validation**: Write a minimal test script that:
   - Launches SC2 and connects via websocket
   - Starts a replay WITHOUT `observed_player_id`
   - Observes one frame and prints `player_common` contents
   - Tests `ActionObserverPlayerPerspective` with `player_id=1` and `player_id=2`
   - Confirms that per-player economy data is accessible
   - Documents which Unit fields are populated for both players' units

2. **Phase 2 - Core Implementation**: Build the extraction pipeline using raw API:
   - Reuse pysc2's `run_configs` for SC2 process management (or replicate it)
   - Use raw websocket + protobuf for all game communication
   - Single-pass extraction with observer mode
   - Build `RequestData` lookup tables at replay start

3. **Phase 3 - Integration**: Replace the current two-pass pipeline with the single-pass observer mode pipeline, maintaining the same output format.

---

## Appendix A: ResponseObservation Full Structure

For reference, the complete nesting of the observation response:

```
ResponseObservation
  actions[]                          -- Actions taken since last observation
    action_raw                       -- Raw action (if raw interface enabled)
    action_chat                      -- Chat message
    game_loop                        -- Game loop when action was executed
  action_errors[]                    -- Failed action reports
  observation                        -- The actual game state snapshot
    game_loop                        -- Current game loop number
    player_common                    -- Economy data (PlayerCommon)
      player_id, minerals, vespene, food_cap, food_used,
      food_army, food_workers, idle_worker_count, army_count,
      warp_gate_count, larva_count
    alerts[]                         -- Alert events (building complete, under attack, etc.)
    abilities[]                      -- Available abilities for selection
    score                            -- Score data (Score)
      score_type, score, score_details (ScoreDetails)
    raw_data                         -- Raw observation (ObservationRaw)
      player                         -- PlayerRaw
        power_sources[], camera, upgrade_ids[]
      units[]                        -- All units on map (Unit messages)
      map_state                      -- MapState (visibility, creep)
      event                          -- Event (dead_units[])
      effects[]                      -- Active effects (Effect messages)
      radar[]                        -- Radar rings (RadarRing messages)
  player_result[]                    -- Game result (only when game ends)
    player_id, result (Victory/Defeat/Tie/Undecided)
  chat[]                             -- Chat messages received
    player_id, message
```

## Appendix B: RequestReplayInfo for Metadata

Before processing a replay, use `RequestReplayInfo` to get metadata:

```protobuf
message ResponseReplayInfo {
  optional string map_name = 1;
  optional string local_map_path = 2;
  repeated PlayerInfoExtra player_info = 3;    // Player details + results
  optional uint32 game_duration_loops = 4;     // Total game length in game loops
  optional float game_duration_seconds = 5;    // Total game length in seconds
  optional string game_version = 6;            // Patch version (e.g., "4.12.1")
  optional string data_version = 11;           // Data version hash
  optional uint32 data_build = 7;              // Data build number
  optional uint32 base_build = 8;              // Binary version (base build number)
}
```

Where `PlayerInfoExtra` contains:
```protobuf
message PlayerInfoExtra {
  optional PlayerInfo player_info = 1;     // Player ID, type, race, name
  optional PlayerResult player_result = 2; // Victory/Defeat/Tie
  optional int32 player_mmr = 3;           // Player MMR at time of game
  optional int32 player_apm = 4;           // Player APM for the game
}
```

And `PlayerInfo`:
```protobuf
message PlayerInfo {
  optional uint32 player_id = 1;       // Player ID (1, 2, etc.)
  optional PlayerType type = 2;        // Participant, Computer, Observer
  optional Race race_requested = 3;    // Race selected (may be Random)
  optional Race race_actual = 4;       // Actual race played
  optional Difficulty difficulty = 5;  // AI difficulty (if Computer)
  optional AIBuild ai_build = 7;       // AI build order (if Computer)
  optional string player_name = 6;     // Player name
}
```

## Appendix C: Game Loop Timing Reference

At "Faster" game speed (the standard competitive speed):
- **22.4 game loops per second** of real-time
- 1 game loop = ~44.6 milliseconds of real-time
- 1 minute of real-time = 1,344 game loops
- A typical 15-minute game = ~20,160 game loops
- `SPlayerStatsEvent` from s2protocol fires every ~160 game loops (~7.1 seconds)

Common step sizes for extraction:
- `step_size=1`: Every game loop (highest resolution, slowest)
- `step_size=16`: ~0.7 seconds (good balance of resolution and speed)
- `step_size=22`: ~1 second intervals
- `step_size=160`: ~7.1 seconds (matches s2protocol tracker event frequency)
