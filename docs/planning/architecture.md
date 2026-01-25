# SC2 Replay Ground Truth Extraction Pipeline - Architecture

## Overview

This document provides a comprehensive architectural view of the SC2 Replay Ground Truth Extraction Pipeline, showing component interactions, data flow, and processing stages.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BATCH PROCESSING LAYER                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     Main Process Controller                       │  │
│  │  - Manages replay queue                                           │  │
│  │  - Spawns worker processes                                        │  │
│  │  - Monitors progress                                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│              ┌─────────────────────┼─────────────────────┐              │
│              ▼                     ▼                     ▼              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ Worker Process 1 │  │ Worker Process 2 │  │ Worker Process N │      │
│  │ (SC2 Instance 1) │  │ (SC2 Instance 2) │  │ (SC2 Instance N) │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     SINGLE REPLAY PROCESSING PIPELINE                   │
│                                                                          │
│  ┌────────────┐      ┌─────────────┐      ┌──────────────┐            │
│  │   Replay   │─────▶│   Replay    │─────▶│  Game Loop   │            │
│  │   Loader   │      │  Validator  │      │   Iterator   │            │
│  └────────────┘      └─────────────┘      └──────────────┘            │
│                                                    │                    │
│                                                    ▼                    │
│                                          ┌──────────────────┐          │
│                                          │ State Extractor  │          │
│                                          │   Components     │          │
│                                          └──────────────────┘          │
│                                                    │                    │
│        ┌───────────────────┬───────────────────────┼─────────────────┐ │
│        ▼                   ▼                       ▼                 ▼ │
│  ┌──────────┐      ┌─────────────┐      ┌──────────────┐  ┌─────────┐│
│  │  Unit    │      │  Building   │      │   Economy    │  │Upgrade  ││
│  │Extractor │      │  Extractor  │      │   Extractor  │  │Extractor││
│  └──────────┘      └─────────────┘      └──────────────┘  └─────────┘│
│        │                   │                       │                 │ │
│        └───────────────────┴───────────────────────┴─────────────────┘ │
│                                    │                                    │
│                                    ▼                                    │
│                          ┌──────────────────┐                          │
│                          │  Wide Table      │                          │
│                          │  Builder         │                          │
│                          └──────────────────┘                          │
│                                    │                                    │
│                                    ▼                                    │
│                          ┌──────────────────┐                          │
│                          │  Parquet Writer  │                          │
│                          └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            OUTPUT FILES                                 │
│                                                                          │
│  data/processed/                                                        │
│    ├── replay_name_parsed.parquet    (Game state wide table)          │
│    └── replay_name_messages.parquet  (Chat/messages - if available)   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Architecture

### 1. Batch Processing Layer

```
Main Process
├── Replay Queue Filler (Thread)
│   └── Scans replay directory
│   └── Populates multiprocessing.JoinableQueue
│
├── Stats Printer (Thread)
│   └── Monitors stats_queue
│   └── Prints progress every 10 seconds
│
└── Worker Process Pool (N processes)
    ├── Worker 1: ReplayProcessor(proc_id=0)
    ├── Worker 2: ReplayProcessor(proc_id=1)
    └── Worker N: ReplayProcessor(proc_id=N-1)

Communication:
- replay_queue: JoinableQueue (Main → Workers)
- stats_queue: Queue (Workers → Main)
```

### 2. Single Replay Processing Pipeline

Each worker process executes this pipeline for each replay:

```
┌──────────────────────────────────────────────────────────────────┐
│ PASS 1: Schema Discovery                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Replay File                                                     │
│      │                                                           │
│      ▼                                                           │
│  Load Replay (pysc2.run_config.replay_data)                     │
│      │                                                           │
│      ▼                                                           │
│  Start SC2 Controller (observed_player_id=1)                    │
│      │                                                           │
│      ▼                                                           │
│  Iterate All Game Loops (step_mul=8)                            │
│      │                                                           │
│      ▼                                                           │
│  Track Max Unit/Building Counts                                 │
│      │   {unit_type: max_count}                                 │
│      ▼                                                           │
│  Generate Column Schema                                         │
│      │   [p1_marine_001_x, p1_marine_001_y, ...]                │
│      ▼                                                           │
│  Save Schema Definition                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ PASS 2: Data Extraction (Player 1)                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Replay File                                                     │
│      │                                                           │
│      ▼                                                           │
│  Load Replay                                                     │
│      │                                                           │
│      ▼                                                           │
│  Start SC2 Controller (observed_player_id=1)                    │
│      │                                                           │
│      ▼                                                           │
│  For Each Game Loop:                                            │
│      │                                                           │
│      ├─▶ controller.observe() → obs                             │
│      │                                                           │
│      ├─▶ Extract State:                                         │
│      │   ├─ game_loop = obs.observation.game_loop               │
│      │   ├─ units = extract_units(obs)                          │
│      │   ├─ buildings = extract_buildings(obs)                  │
│      │   ├─ economy = extract_economy(obs)                      │
│      │   └─ upgrades = extract_upgrades(obs)                    │
│      │                                                           │
│      ├─▶ Build Wide Row (using schema from Pass 1)              │
│      │   └─ {game_loop: 100, p1_marine_001_x: 50.2, ...}        │
│      │                                                           │
│      ├─▶ Append to Buffer                                       │
│      │                                                           │
│      └─▶ controller.step(step_mul)                              │
│                                                                  │
│      ▼                                                           │
│  Write to Parquet (p1 data)                                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ PASS 3: Data Extraction (Player 2)                              │
├──────────────────────────────────────────────────────────────────┤
│  (Same as Pass 2, but with observed_player_id=2)                │
│      ▼                                                           │
│  Write to Parquet (p2 data)                                     │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ MERGE: Combine Player 1 and Player 2 Data                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Merge on game_loop:                                            │
│      p1_data JOIN p2_data ON game_loop                          │
│      ▼                                                           │
│  Final Wide Table:                                              │
│      [game_loop, p1_marine_001_x, ..., p2_zergling_001_x, ...]  │
│      ▼                                                           │
│  Write Final Parquet                                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Data Flow

### State Extractor Data Flow

```
obs (ResponseObservation from pysc2)
│
├─▶ Unit Extractor
│   │
│   ├─ Input: obs.observation.raw_data.units
│   │          obs.observation.raw_data.event.dead_units
│   │
│   ├─ Processing:
│   │  ├─ Filter by alliance (Self=1, Enemy=4)
│   │  ├─ Track tags (new, existing, dead)
│   │  ├─ Assign readable IDs
│   │  └─ Extract position, health, shields
│   │
│   └─ Output: {
│        'p1_units': {
│            'p1_marine_001': {
│                'tag': 12345,
│                'x': 50.2, 'y': 30.1, 'z': 8.0,
│                'health': 45, 'shields': 0,
│                'state': 'existing'
│            }, ...
│        }
│      }
│
├─▶ Building Extractor
│   │
│   ├─ Input: obs.observation.raw_data.units (filtered by building types)
│   │
│   ├─ Processing:
│   │  ├─ Filter units where unit_type is building
│   │  ├─ Track construction state (build_progress)
│   │  ├─ Detect started/completed/destroyed events
│   │  └─ Record timestamps
│   │
│   └─ Output: {
│        'p1_buildings': {
│            'p1_barracks_001': {
│                'tag': 67890,
│                'x': 100.5, 'y': 80.3, 'z': 8.0,
│                'status': 'building',
│                'progress': 75.5,
│                'started_loop': 500,
│                'completed_loop': None
│            }, ...
│        }
│      }
│
├─▶ Economy Extractor
│   │
│   ├─ Input: obs.observation.player_common
│   │
│   ├─ Processing:
│   │  └─ Direct field extraction
│   │
│   └─ Output: {
│        'p1_economy': {
│            'minerals': 450,
│            'gas': 200,
│            'supply_used': 45,
│            'supply_cap': 60,
│            'workers': 25
│        }
│      }
│
└─▶ Upgrade Extractor
    │
    ├─ Input: obs.observation.raw_data.player.upgrade_ids
    │
    ├─ Processing:
    │  ├─ Track new upgrades
    │  ├─ Lookup names via pysc2.lib.upgrades
    │  └─ Parse category and level
    │
    └─ Output: {
         'p1_upgrades': {
             'ground_weapons_1': True,
             'ground_armor_1': True,
             'stim_pack': True
         }
       }
```

### Wide Table Builder Data Flow

```
Extracted State (nested dict)
│
├─ game_loop: 1000
├─ p1_units: {p1_marine_001: {...}, p1_marine_002: {...}}
├─ p1_buildings: {p1_barracks_001: {...}}
├─ p1_economy: {...}
└─ p1_upgrades: {...}
│
▼
Wide Table Builder
│
├─ Initialize row with game_loop
│
├─ For each unit in p1_units:
│  ├─ row['p1_marine_001_x'] = unit.x
│  ├─ row['p1_marine_001_y'] = unit.y
│  ├─ row['p1_marine_001_state'] = unit.state
│  └─ ...
│
├─ For each building in p1_buildings:
│  └─ Similar field mapping
│
├─ For economy:
│  ├─ row['p1_minerals'] = economy.minerals
│  └─ ...
│
├─ For upgrades:
│  ├─ row['p1_upgrade_ground_weapons_1'] = True
│  └─ ...
│
├─ Fill NaN for missing units/buildings
│
▼
Wide Row (dict)
{
    'game_loop': 1000,
    'p1_marine_001_x': 50.2,
    'p1_marine_001_y': 30.1,
    'p1_marine_001_z': 8.0,
    'p1_marine_001_state': 'existing',
    'p1_marine_002_x': None,  # NaN
    'p1_minerals': 450,
    ...
}
```

---

## Data Structures

### Tag Tracking Structure

```python
# Persistent across all frames for a replay
{
    'tag_to_readable_id': {
        12345: 'p1_marine_001',
        12346: 'p1_marine_002',
        67890: 'p1_barracks_001'
    },
    'unit_type_counters': {
        48: 3,  # Marine: next ID is 003
        71: 1   # Barracks: next ID is 001
    },
    'previous_frame': {
        'tags': {12345, 12346, 67890},
        'upgrades': {1, 2, 5},
        'building_progress': {
            67890: 0.75
        }
    }
}
```

### Schema Structure

```python
{
    'columns': [
        {'name': 'game_loop', 'type': 'int32'},
        {'name': 'p1_marine_001_x', 'type': 'float32'},
        {'name': 'p1_marine_001_y', 'type': 'float32'},
        {'name': 'p1_marine_001_z', 'type': 'float32'},
        {'name': 'p1_marine_001_state', 'type': 'string'},
        # ... more columns
    ],
    'metadata': {
        'replay_name': 'game_2024_01_15.SC2Replay',
        'map_name': 'Goldenaura LE',
        'player_1': 'PlayerA',
        'player_2': 'PlayerB',
        'game_duration_loops': 15234,
        'sc2_version': '5.0.12',
        'extraction_timestamp': '2024-01-24T12:00:00',
        'step_mul': 8
    }
}
```

---

## Processing Patterns

### Two-Pass Pattern

```
Pass 1: Schema Discovery
─────────────────────────
Purpose: Determine maximum column set
Process:
  1. Iterate entire replay
  2. Track: max_units[unit_type] = max(count)
  3. Generate schema based on maximums
Time: ~1-5 minutes per replay

Pass 2: Data Extraction
────────────────────────
Purpose: Extract data into fixed schema
Process:
  1. Load schema from Pass 1
  2. Iterate replay, extract data
  3. Build wide rows using schema
  4. Fill NaN for missing entries
Time: ~1-5 minutes per replay

Total: ~2-10 minutes per replay (acceptable)
```

### Multi-Player Pattern

```
Sequential Processing
─────────────────────
For player_id in [1, 2]:
    Load replay with observed_player_id=player_id
    Extract data for this player
    Save intermediate result

Merge results by game_loop
```

---

## Technology Stack

```
┌─────────────────────────────────────────────────┐
│ Application Layer                               │
├─────────────────────────────────────────────────┤
│ Python 3.8+                                     │
│ - Main application logic                       │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ Core Libraries                                  │
├─────────────────────────────────────────────────┤
│ pysc2         - SC2 interface & observation     │
│ s2clientprotocol - Protobuf definitions        │
│ pandas        - Data manipulation               │
│ pyarrow       - Parquet I/O                     │
│ numpy         - Numeric operations              │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ SC2 Engine Layer                                │
├─────────────────────────────────────────────────┤
│ StarCraft II Binary                             │
│ - Game engine simulation                        │
│ - Ground truth state computation                │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ Data Storage                                    │
├─────────────────────────────────────────────────┤
│ Input:  .SC2Replay files                        │
│ Output: .parquet files (columnar format)        │
└─────────────────────────────────────────────────┘
```

---

## Concurrency Model

```
┌────────────────────────────────────────────────────────────┐
│                     Main Process                           │
│                                                            │
│  Main Thread                                               │
│  ├─ Initialize queues                                     │
│  ├─ Spawn worker processes                                │
│  └─ Wait for completion                                   │
│                                                            │
│  Queue Filler Thread                                       │
│  └─ Add replays to replay_queue                           │
│                                                            │
│  Stats Printer Thread                                      │
│  └─ Monitor stats_queue and print progress                │
│                                                            │
└────────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Worker Process 1│ │ Worker Process 2│ │ Worker Process N│
│                 │ │                 │ │                 │
│ SC2 Instance 1  │ │ SC2 Instance 2  │ │ SC2 Instance N  │
│ Memory: ~2 GB   │ │ Memory: ~2 GB   │ │ Memory: ~2 GB   │
│ CPU: 1 core     │ │ CPU: 1 core     │ │ CPU: 1 core     │
│                 │ │                 │ │                 │
│ Process:        │ │ Process:        │ │ Process:        │
│ 1. Get replay   │ │ 1. Get replay   │ │ 1. Get replay   │
│ 2. Extract data │ │ 2. Extract data │ │ 2. Extract data │
│ 3. Write output │ │ 3. Write output │ │ 3. Write output │
│ 4. Report stats │ │ 4. Report stats │ │ 4. Report stats │
│ 5. Repeat       │ │ 5. Repeat       │ │ 5. Repeat       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## File Organization

```
local-play-bootstrap-main/
├── replays/                           # Input directory
│   ├── game_001.SC2Replay
│   ├── game_002.SC2Replay
│   └── ...
│
├── data/
│   ├── processed/                     # Output directory
│   │   ├── game_001_parsed.parquet
│   │   ├── game_002_parsed.parquet
│   │   └── ...
│   │
│   └── schemas/                       # Schema definitions
│       ├── game_001_schema.json
│       └── ...
│
├── src/
│   ├── pipeline/
│   │   ├── replay_loader.py          # Component 1
│   │   ├── game_loop_iterator.py     # Component 2
│   │   ├── state_extractor.py        # Component 3
│   │   ├── wide_table_builder.py     # Component 4
│   │   ├── schema_manager.py         # Component 5
│   │   └── parquet_writer.py         # Component 6
│   │
│   ├── extractors/
│   │   ├── unit_extractor.py
│   │   ├── building_extractor.py
│   │   ├── economy_extractor.py
│   │   └── upgrade_extractor.py
│   │
│   └── batch/
│       ├── replay_processor.py       # Worker process
│       └── batch_controller.py       # Main controller
│
└── docs/
    └── planning/
        └── architecture.md            # This file
```

---

## Error Handling Flow

```
Replay Processing
│
├─▶ Try: Load replay
│   └─▶ Catch: Version mismatch → Log error, skip replay
│
├─▶ Try: Validate replay
│   └─▶ Catch: Missing map → Log error, skip replay
│
├─▶ Try: Process game loops
│   │
│   ├─▶ Try: Extract state
│   │   └─▶ Catch: Unexpected proto structure → Log warning, use defaults
│   │
│   └─▶ Catch: Protocol error → Save partial data, mark as incomplete
│
└─▶ Try: Write parquet
    └─▶ Catch: I/O error → Retry 3x, then fail replay
```

---

## Performance Characteristics

```
Single Replay Processing
────────────────────────
Time Complexity: O(game_loops * units_per_loop)
Space Complexity: O(game_loops * columns)

Typical Game:
- Game loops: 15,000
- Units per loop: ~200
- Columns: ~500-1000
- Memory: ~200-500 MB
- Time: 2-10 minutes

Batch Processing
────────────────
Throughput: Linear scaling with workers
- 1 worker: ~6-30 replays/hour
- 4 workers: ~24-120 replays/hour
- 8 workers: ~48-240 replays/hour

Bottleneck: SC2 engine simulation speed
```

---

## Summary

This architecture provides:
- **Scalability**: Parallel processing with configurable workers
- **Reliability**: Process isolation and comprehensive error handling
- **Flexibility**: Two-pass design allows schema evolution
- **Performance**: Optimized for batch processing with reasonable throughput
- **Maintainability**: Modular component design with clear responsibilities

The pipeline transforms SC2 replays into ML-ready wide-format Parquet files containing complete ground truth game state at every game loop.
