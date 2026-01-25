# pysc2 Observation Schema Documentation

## Overview
This document provides the complete structure of a pysc2 observation object, including all available fields, data types, nesting structure, and which fields provide which required information for Ground Truth Game State extraction.

---

## Top-Level Observation Structure

```python
obs = controller.observe()  # Returns ResponseObservation proto

# Top-level fields
obs.actions                    # list[Action] - Actions taken since last observation
obs.action_errors              # list[ActionResult] - Errors from attempted actions
obs.observation                # Observation - The main observation data
obs.player_result              # list[PlayerResult] - Game outcome (if game ended)
obs.chat                       # list[ChatReceived] - Chat messages (not in replays)
```

---

## Main Observation Object (`obs.observation`)

### Core Fields
```python
obs.observation.game_loop                      # uint32 - Current game loop count
obs.observation.player_common                  # PlayerCommon - Player-specific data
obs.observation.alerts                         # list[Alert] - In-game alerts
obs.observation.abilities                      # list[AvailableAbility] - Available abilities
obs.observation.score                          # Score - Detailed score information
obs.observation.raw_data                       # ObservationRaw - RAW GAME STATE (PRIMARY)
obs.observation.feature_layer_data             # ObservationFeatureLayer - Feature layers
obs.observation.render_data                    # ObservationRender - RGB rendering
obs.observation.ui_data                        # ObservationUI - UI state
```

---

## Critical: `obs.observation.raw_data` (Ground Truth Source)

This is the **primary source** for ground truth game state. It contains the actual game engine state.

### Structure
```python
obs.observation.raw_data.player                # PlayerRaw - Player-specific raw data
obs.observation.raw_data.units                 # list[Unit] - ALL UNITS (PRIMARY DATA)
obs.observation.raw_data.map_state             # MapState - Visibility and creep
obs.observation.raw_data.event                 # Event - Game events (deaths, etc.)
obs.observation.raw_data.effects               # list[Effect] - Active effects
obs.observation.raw_data.radar                 # list[RadarRing] - Sensor tower radii
```

### `raw_data.player` (PlayerRaw)
```python
raw.player.power_sources                       # list[PowerSource] - Protoss pylons
raw.player.camera                              # Point - Camera position (x, y, z)
raw.player.upgrade_ids                         # list[uint32] - COMPLETED UPGRADES
```

#### PowerSource Structure
```python
power_source.pos                               # Point - Pylon position
power_source.radius                            # float - Power radius
power_source.tag                               # uint64 - Unit tag of pylon
```

### `raw_data.units` (CRITICAL - Main Unit Data)

Each unit in `raw_data.units` list has this structure:

```python
# Identity
unit.tag                                       # uint64 - PERSISTENT UNIT ID (unique)
unit.unit_type                                 # uint32 - Unit type ID
unit.owner                                     # int32 - Player ID (1-15, 16=neutral)
unit.alliance                                  # Alliance enum - Self/Ally/Neutral/Enemy

# Position and Orientation
unit.pos                                       # Point - Position (x, y, z)
unit.facing                                    # float - Direction in radians
unit.radius                                    # float - Unit radius

# State
unit.display_type                              # DisplayType enum - Visible/Snapshot/Hidden
unit.cloak                                     # CloakState enum - Cloak status
unit.is_selected                               # bool - Currently selected
unit.is_on_screen                              # bool - Visible in screen view
unit.is_blip                                   # bool - Detected but not visible
unit.is_powered                                # bool - In pylon power field (Protoss)
unit.is_active                                 # bool - Currently active
unit.is_flying                                 # bool - Flying unit
unit.is_burrowed                               # bool - Burrowed (Zerg)
unit.is_hallucination                          # bool - Is a hallucination

# Vital Stats
unit.health                                    # float - Current health
unit.health_max                                # float - Maximum health
unit.shield                                    # float - Current shields
unit.shield_max                                # float - Maximum shields
unit.energy                                    # float - Current energy
unit.energy_max                                # float - Maximum energy

# Construction
unit.build_progress                            # float - Build progress (0.0-1.0)

# Combat
unit.weapon_cooldown                           # float - Weapon cooldown
unit.engaged_target_tag                        # uint64 - Tag of attack target
unit.attack_upgrade_level                      # int32 - Attack upgrade level
unit.armor_upgrade_level                       # int32 - Armor upgrade level
unit.shield_upgrade_level                      # int32 - Shield upgrade level
unit.detect_range                              # float - Detection range
unit.radar_range                               # float - Radar range

# Resources (for resource units)
unit.mineral_contents                          # int32 - Minerals in this node
unit.vespene_contents                          # int32 - Gas in this geyser

# Cargo and Passengers
unit.cargo_space_taken                         # int32 - Cargo slots used
unit.cargo_space_max                           # int32 - Max cargo slots
unit.passengers                                # list[PassengerUnit] - Units inside

# Harvesting (for bases/geysers)
unit.assigned_harvesters                       # int32 - Workers assigned
unit.ideal_harvesters                          # int32 - Optimal worker count

# Orders (Current Actions)
unit.orders                                    # list[UnitOrder] - Current orders
# See UnitOrder structure below

# Buffs
unit.buff_ids                                  # list[uint32] - Active buff IDs
unit.buff_duration_remain                      # int32 - Remaining buff duration
unit.buff_duration_max                         # int32 - Maximum buff duration

# Addons (Terran)
unit.add_on_tag                                # uint64 - Tag of attached addon

# Rally Points
unit.rally_targets                             # list[RallyTarget] - Rally points
```

#### UnitOrder Structure
```python
order.ability_id                               # uint32 - Ability being executed
order.progress                                 # float - Order progress (0.0-1.0)
order.target_world_space_pos                   # Point (optional) - Target position
order.target_unit_tag                          # uint64 (optional) - Target unit tag
```

#### PassengerUnit Structure
```python
passenger.tag                                  # uint64 - Passenger unit tag
passenger.health                               # float - Passenger health
passenger.health_max                           # float - Passenger max health
passenger.shield                               # float - Passenger shields
passenger.shield_max                           # float - Passenger max shields
passenger.energy                               # float - Passenger energy
passenger.energy_max                           # float - Passenger max energy
passenger.unit_type                            # uint32 - Passenger unit type
```

#### RallyTarget Structure
```python
rally.point                                    # Point - Rally point location
rally.tag                                      # uint64 - Rally target unit tag (optional)
```

### `raw_data.map_state` (MapState)
```python
map_state.visibility                           # ImageData - Visibility map
map_state.creep                                # ImageData - Creep map
```

#### ImageData Structure
```python
image.bits_per_pixel                           # int32 - Bits per pixel (1, 8, 16, 32)
image.size                                     # Size2DI - Width and height
image.data                                     # bytes - Raw image data
```

### `raw_data.event` (Event)
```python
event.dead_units                               # list[uint64] - Tags of units that died
```

### `raw_data.effects` (List of Active Effects)
```python
effect.effect_id                               # uint32 - Effect type ID
effect.pos                                     # list[Point2D] - Effect positions
effect.alliance                                # Alliance enum - Effect alliance
effect.owner                                   # int32 - Player who owns effect
effect.radius                                  # float - Effect radius
```

### `raw_data.radar` (List of Radar Rings)
```python
radar.pos                                      # Point - Sensor tower position
radar.radius                                   # float - Radar radius
```

---

## Player Common Data (`obs.observation.player_common`)

This is **critical for economy data**:

```python
player_common.player_id                        # uint32 - Current player ID
player_common.minerals                         # uint32 - MINERALS
player_common.vespene                          # uint32 - VESPENE GAS
player_common.food_used                        # uint32 - SUPPLY USED
player_common.food_cap                         # uint32 - SUPPLY CAP
player_common.food_army                        # uint32 - Supply used by army
player_common.food_workers                     # uint32 - WORKER COUNT
player_common.idle_worker_count                # uint32 - Idle workers
player_common.army_count                       # uint32 - Army unit count
player_common.warp_gate_count                  # uint32 - Warp gates (Protoss)
player_common.larva_count                      # uint32 - Larva count (Zerg)
```

---

## Score Data (`obs.observation.score`)

Detailed score breakdown:

```python
# High-level score
score.score_type                               # ScoreType enum - Score type
score.score                                    # int32 - Total score
score.score_details                            # ScoreDetails - Detailed breakdown

# ScoreDetails structure
details = score.score_details

# Production
details.idle_production_time                   # float - Idle production time
details.idle_worker_time                       # float - Idle worker time
details.total_value_units                      # float - Value of units
details.total_value_structures                 # float - Value of structures

# Combat
details.killed_value_units                     # float - Enemy unit value killed
details.killed_value_structures                # float - Enemy structure value killed

# Economy
details.collected_minerals                     # float - Total minerals collected
details.collected_vespene                      # float - Total gas collected
details.collection_rate_minerals               # float - Current mineral rate
details.collection_rate_vespene                # float - Current gas rate
details.spent_minerals                         # float - Minerals spent
details.spent_vespene                          # float - Gas spent

# Detailed breakdowns by category
details.food_used                              # ScoreByCategory - Food by category
details.killed_minerals                        # ScoreByCategory - Kill value minerals
details.killed_vespene                         # ScoreByCategory - Kill value gas
details.lost_minerals                          # ScoreByCategory - Loss value minerals
details.lost_vespene                           # ScoreByCategory - Loss value gas
details.friendly_fire_minerals                 # ScoreByCategory - FF value minerals
details.friendly_fire_vespene                  # ScoreByCategory - FF value gas
details.used_minerals                          # ScoreByCategory - Spent minerals
details.used_vespene                           # ScoreByCategory - Spent gas
details.total_used_minerals                    # ScoreByCategory - Total spent minerals
details.total_used_vespene                     # ScoreByCategory - Total spent gas

# ScoreByCategory has fields for each category
category.none                                  # float
category.army                                  # float
category.economy                               # float
category.technology                            # float
category.upgrade                               # float

# Vital stats
details.total_damage_dealt                     # ScoreByVital - Damage by vital
details.total_damage_taken                     # ScoreByVital - Damage taken
details.total_healed                           # ScoreByVital - Healing

# ScoreByVital has fields for each vital
vital.life                                     # float
vital.shields                                  # float
vital.energy                                   # float
```

---

## UI Data (`obs.observation.ui_data`)

```python
# Control Groups
ui_data.groups                                 # list[ControlGroup] - 10 control groups

# ControlGroup structure
group.control_group_index                      # uint32 - Group index (0-9)
group.leader_unit_type                         # uint32 - Type of leader unit
group.count                                    # uint32 - Unit count in group

# Selection
ui_data.single                                 # SinglePanel - Single unit selected
ui_data.multi                                  # MultiPanel - Multiple units selected
ui_data.cargo                                  # CargoPanel - Cargo view
ui_data.production                             # ProductionPanel - Production view

# SinglePanel
single.unit                                    # UnitInfo - Selected unit info

# MultiPanel
multi.units                                    # list[UnitInfo] - Selected units

# CargoPanel
cargo.unit                                     # UnitInfo - Transport unit
cargo.passengers                               # list[UnitInfo] - Passengers
cargo.slots_available                          # int32 - Available cargo slots

# ProductionPanel
production.unit                                # UnitInfo - Production building
production.build_queue                         # list[UnitInfo] - Build queue
production.production_queue                    # list[BuildItem] - Production queue

# UnitInfo structure (simplified unit data for UI)
unit_info.unit_type                            # uint32 - Unit type
unit_info.player_relative                      # PlayerRelative enum
unit_info.health                               # int32 - Health
unit_info.shields                              # int32 - Shields
unit_info.energy                               # int32 - Energy
unit_info.transport_slots_taken                # int32 - Cargo slots used
unit_info.build_progress                       # int32 - Build progress (0-100)
unit_info.addon                                # UnitInfo (optional) - Attached addon

# BuildItem structure
build_item.ability_id                          # uint32 - Production ability
build_item.build_progress                      # float - Progress (0.0-1.0)
```

---

## Feature Layer Data (`obs.observation.feature_layer_data`)

Agent-friendly rendered layers (not needed for ground truth, but available):

```python
feature_layer_data.renders                     # FeatureLayersMinimap - Screen layers
feature_layer_data.minimap_renders             # FeatureLayersMinimap - Minimap layers

# Available feature layers (see pysc2.lib.features for details)
# Screen: height_map, visibility, creep, power, player_id, player_relative,
#         unit_type, selected, unit_hit_points, unit_energy, unit_shields, etc.
# Minimap: height_map, visibility, creep, camera, player_id, player_relative, etc.
```

---

## Abilities (`obs.observation.abilities`)

Available abilities for currently selected units:

```python
# List of AvailableAbility
ability.ability_id                             # int32 - Ability ID
ability.requires_point                         # bool - Requires target point
```

---

## Alerts (`obs.observation.alerts`)

```python
# List of Alert enums
# Examples: NuclearLaunchDetected, NydusWormDetected, etc.
```

---

## Actions (`obs.actions`)

Actions taken since last observation (for replays):

```python
action.action_feature_layer                    # ActionSpatial (optional)
action.action_render                           # ActionSpatial (optional)
action.action_ui                               # ActionUI (optional)
action.action_raw                              # ActionRaw (optional)
action.action_chat                             # ActionChat (optional)
action.game_loop                               # uint32 - When action was executed
```

---

## Data Flow Summary

```
controller.observe()
    ↓
ResponseObservation
    ├── observation (Observation proto)
    │   ├── game_loop [TIMESTAMP]
    │   ├── player_common [ECONOMY DATA]
    │   │   ├── minerals
    │   │   ├── vespene
    │   │   ├── food_used
    │   │   ├── food_cap
    │   │   └── food_workers
    │   │
    │   ├── raw_data [PRIMARY GROUND TRUTH]
    │   │   ├── player
    │   │   │   └── upgrade_ids [UPGRADES]
    │   │   │
    │   │   ├── units [ALL UNITS & BUILDINGS]
    │   │   │   ├── tag [PERSISTENT ID]
    │   │   │   ├── unit_type [TYPE]
    │   │   │   ├── pos [POSITION]
    │   │   │   ├── health, shield, energy [VITALS]
    │   │   │   ├── build_progress [CONSTRUCTION]
    │   │   │   ├── orders [CURRENT ACTIONS]
    │   │   │   └── ... [50+ more fields]
    │   │   │
    │   │   ├── event
    │   │   │   └── dead_units [DEATHS]
    │   │   │
    │   │   └── effects [ACTIVE EFFECTS]
    │   │
    │   └── score [DETAILED STATS]
    │
    ├── actions [PLAYER ACTIONS]
    └── player_result [GAME OUTCOME]
```

---

## Enum Reference

### Alliance
```python
Self = 1
Ally = 2
Neutral = 3
Enemy = 4
```

### DisplayType
```python
Visible = 1
Snapshot = 2
Hidden = 3
Placeholder = 4
```

### CloakState
```python
CloakedUnknown = 0
Cloaked = 1
CloakedDetected = 2
NotCloaked = 3
CloakedAllied = 4
```

---

## Nesting Depth

The observation object has up to 4 levels of nesting:
```python
obs                                    # Level 0
  .observation                         # Level 1
    .raw_data                          # Level 2
      .units[i]                        # Level 3
        .orders[j]                     # Level 4
          .target_world_space_pos      # Level 5 (deepest)
```

---

## Size Estimates

For a typical game with ~200 units:
- Full observation proto: ~50-100 KB
- `raw_data.units` list: ~80% of observation size
- Each unit: ~200-500 bytes (varies with orders, passengers, etc.)

---

## Conclusion

The pysc2 observation schema is comprehensive and deeply nested. The **`obs.observation.raw_data.units`** list is the primary source for ground truth unit/building data, while **`obs.observation.player_common`** provides economy data. All fields use protobuf serialization for efficient transfer.
