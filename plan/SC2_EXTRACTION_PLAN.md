# SC2 Replay Data Extraction System - Implementation Plan

**Project:** StarCraft 2 Replay Frame-by-Frame Data Extraction for DBN Training
**Date:** 2026-01-23
**Version:** 1.0
**Status:** Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Schema Specifications](#3-data-schema-specifications)
4. [Module Specifications](#4-module-specifications)
5. [Processing Algorithms](#5-processing-algorithms)
6. [Implementation Roadmap](#6-implementation-roadmap)
7. [Configuration & Usage](#7-configuration--usage)
8. [Testing Strategy](#8-testing-strategy)
9. [Example Outputs](#9-example-outputs)
10. [Performance Considerations](#10-performance-considerations)
11. [Error Handling & Edge Cases](#11-error-handling--edge-cases)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. Executive Summary

### 1.1 Project Objective

Build a robust, efficient system to extract frame-by-frame game state data from SC2 replay files (.SC2Replay) to train Dynamic Bayesian Networks (DBNs) for strategy prediction.

### 1.2 Key Requirements

Extract the following data at every frame/timestep:

**Units:**
- Unit name/type, position (x, y), ownership (player ID)
- Unit creation, cancellation, death events

**Buildings:**
- Building name/type, position, ownership
- Building states: started, cancelled, destroyed, existing (differentiable)

**Upgrades:**
- Upgrade started, cancelled, completed events
- Current upgrades for each player at each timestep

**Messages:**
- All game messages/chat with timestamp, sender, content

### 1.3 Technical Approach

**Library:** sc2reader v1.8.0 with custom patch for AI Arena bot replay compatibility
**Load Level:** 3 (tracker events only) - provides all required data
**Temporal Resolution:** 5-second intervals (112 frames @ Faster speed)
**Output Format:** Parquet (production), JSON (development/debugging)
**Architecture:** Event-driven state tracking with incremental updates

### 1.4 Success Criteria

- All required data points extracted and validated
- Handles both ladder and AI Arena bot replays
- Processes replays at 25+ replays/second
- Scalable to 10,000+ replay datasets
- Comprehensive error handling and logging
- Full test coverage with example replays

---

## 2. Architecture Overview

### 2.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                                  │
├─────────────────────────────────────────────────────────────────────┤
│  .SC2Replay Files (MPQ Archives)                                     │
│  - Ladder replays (human games)                                      │
│  - AI Arena bot replays (requires patch)                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PARSING LAYER                                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  sc2reader_patch.py (Monkey Patch)                           │   │
│  │  - Handles empty cache_handles for bot replays               │   │
│  │  - Must be imported BEFORE sc2reader                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                           │                                          │
│                           ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  ReplayParser (src/parser/replay_parser.py)                  │   │
│  │  - Uses sc2reader.load_replay(path, load_level=3)            │   │
│  │  - Validates replay (version, length, completion)            │   │
│  │  - Extracts metadata (map, players, duration)                │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   EVENT PROCESSING LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  EventProcessor (src/processors/event_processor.py)          │   │
│  │  - Processes tracker events by type                          │   │
│  │  - Dispatches to specialized handlers                        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                           │                                          │
│              ┌────────────┼────────────┬────────────┐                │
│              ▼            ▼            ▼            ▼                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │   UnitEvent │ │  BuildEvent │ │  UpgradeEvt │ │  MessageEvt │   │
│  │   Handler   │ │   Handler   │ │   Handler   │ │   Handler   │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STATE TRACKING LAYER                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  GameStateTracker (src/state/game_state_tracker.py)          │   │
│  │  - Maintains current game state across frames                │   │
│  │  - Tracks unit lifecycles (born → done → died)               │   │
│  │  - Tracks building states (started/existing/destroyed)       │   │
│  │  - Accumulates upgrades per player                           │   │
│  │  - Stores latest player stats                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                           │                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FrameSampler (src/state/frame_sampler.py)                   │   │
│  │  - Samples game state at specified intervals                 │   │
│  │  - Default: 5-second intervals (112 frames)                  │   │
│  │  - Configurable sampling strategy                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA FORMATTING LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  OutputFormatter (src/output/output_formatter.py)            │   │
│  │  - Converts game state to output schema                      │   │
│  │  - Applies feature engineering transformations               │   │
│  │  - Handles data validation and cleaning                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                           │                                          │
│              ┌────────────┼────────────┐                             │
│              ▼            ▼            ▼                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                    │
│  │   Parquet   │ │    JSON     │ │     CSV     │                    │
│  │   Writer    │ │   Writer    │ │   Writer    │                    │
│  └─────────────┘ └─────────────┘ └─────────────┘                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         OUTPUT LAYER                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Structured Data Files                                               │
│  - replay_metadata.parquet   (replay-level info)                     │
│  - frame_states.parquet      (frame-by-frame state)                  │
│  - unit_events.parquet       (unit lifecycle events)                 │
│  - building_events.parquet   (building lifecycle events)             │
│  - upgrade_events.parquet    (upgrade completions)                   │
│  - messages.parquet          (chat/game messages)                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
1. LOAD REPLAY
   ├─ Import sc2reader_patch (for bot replays)
   ├─ Load replay file with sc2reader (load_level=3)
   ├─ Validate replay (min length, completion, version)
   └─ Extract metadata (map, players, duration, winner)

2. PROCESS EVENTS
   ├─ Iterate through replay.tracker_events (sorted by frame)
   ├─ Dispatch events to specialized handlers:
   │  ├─ UnitBornEvent → UnitEventHandler
   │  ├─ UnitInitEvent → UnitEventHandler (building construction)
   │  ├─ UnitDoneEvent → UnitEventHandler (construction complete)
   │  ├─ UnitDiedEvent → UnitEventHandler (death/cancellation)
   │  ├─ UpgradeCompleteEvent → UpgradeEventHandler
   │  ├─ PlayerStatsEvent → StatsEventHandler
   │  └─ ChatEvent → MessageEventHandler
   └─ Update GameStateTracker with each event

3. SAMPLE FRAMES
   ├─ At configured intervals (default: 112 frames / 5 seconds):
   │  ├─ Capture current game state
   │  ├─ Count units by type and player
   │  ├─ Determine building states
   │  ├─ List current upgrades
   │  ├─ Include latest player stats
   │  └─ Store frame snapshot
   └─ Continue until replay end

4. FORMAT OUTPUT
   ├─ Convert frame snapshots to output schema
   ├─ Apply feature engineering (unit counts, tech indicators, etc.)
   ├─ Validate data (no negatives, valid ranges)
   └─ Write to chosen format (Parquet/JSON/CSV)

5. SAVE RESULTS
   ├─ Write metadata file (replay info)
   ├─ Write frame states file (main DBN training data)
   ├─ Write event logs (optional, for detailed analysis)
   └─ Update processing log (success/errors)
```

### 2.3 Component Interaction

```
ReplayParser
    ├─> EventProcessor
    │       ├─> UnitEventHandler ────┐
    │       ├─> UpgradeEventHandler ─┤
    │       ├─> StatsEventHandler ───┼─> GameStateTracker
    │       └─> MessageEventHandler ─┘
    │
    ├─> FrameSampler ────────────────> GameStateTracker.get_state(frame)
    │
    └─> OutputFormatter
            ├─> ParquetWriter
            ├─> JSONWriter
            └─> CSVWriter
```

---

## 3. Data Schema Specifications

### 3.1 Core Data Models

#### 3.1.1 ReplayMetadata

Replay-level information.

```python
@dataclass
class ReplayMetadata:
    """Metadata for a single replay"""
    replay_hash: str              # Unique replay identifier (hash of file)
    file_path: str                # Path to replay file
    map_name: str                 # Map name
    map_hash: Optional[str]       # Map hash (if available)
    region: str                   # Region (us/eu/kr/local for bot replays)
    game_version: str             # SC2 version (e.g., "5.0.11")
    expansion: str                # Expansion (LotV/HotS/WoL)
    game_mode: str                # Game mode (1v1/2v2/3v3/4v4/FFA)
    speed: str                    # Game speed (Faster/Fast/Normal/etc.)

    # Temporal info
    game_length_frames: int       # Total frames
    game_length_seconds: float    # Real-time seconds
    end_time: datetime            # When replay ended (UTC)

    # Players
    player_count: int             # Number of players
    players: List[PlayerInfo]     # Player information

    # Outcome
    winner_id: Optional[int]      # Winning player ID (None if draw/disconnect)

    # Processing info
    extraction_version: str       # Version of extraction code
    extraction_timestamp: datetime  # When extracted

    # Validation flags
    is_complete: bool             # Game finished normally
    is_valid: bool                # Passed validation checks
    has_errors: bool              # Encountered errors during extraction
    error_messages: List[str]     # Error details
```

#### 3.1.2 PlayerInfo

Information about each player in the replay.

```python
@dataclass
class PlayerInfo:
    """Player information"""
    player_id: int                # Player ID (1, 2, etc.)
    name: str                     # Player name (empty for bot replays)
    race: str                     # Race (Protoss/Terran/Zerg/Random)
    result: str                   # Result (Win/Loss/Tie/Unknown)
    handicap: int                 # Handicap value
    color: str                    # Player color

    # MMR/Rating (if available)
    mmr: Optional[int]            # Match-making rating
    highest_league: Optional[str] # Highest league achieved

    # Derived stats (from replay)
    final_units: int              # Final unit count
    final_buildings: int          # Final building count
    final_upgrades: int           # Total upgrades completed
    final_minerals: int           # Minerals at end
    final_vespene: int            # Vespene at end
    final_supply_used: float      # Supply used at end
    final_supply_made: float      # Supply capacity at end
```

#### 3.1.3 FrameState

Complete game state at a specific frame.

```python
@dataclass
class FrameState:
    """Game state at a specific frame"""
    frame: int                    # Frame number
    game_time_seconds: float      # Game time in seconds

    # Player states (keyed by player_id)
    player_states: Dict[int, PlayerFrameState]

    # Optional: Recent events in this interval
    units_born: List[UnitEvent]
    units_died: List[UnitEvent]
    buildings_started: List[BuildingEvent]
    buildings_completed: List[BuildingEvent]
    buildings_destroyed: List[BuildingEvent]
    upgrades_completed: List[UpgradeEvent]
    messages: List[MessageEvent]
```

#### 3.1.4 PlayerFrameState

Per-player state at a specific frame.

```python
@dataclass
class PlayerFrameState:
    """State for one player at a specific frame"""
    player_id: int

    # Resources
    minerals: int
    vespene: int
    minerals_collection_rate: float
    vespene_collection_rate: float

    # Supply
    supply_used: float
    supply_made: float
    supply_cap: float              # Supply cap (200 or 100 based on race/settings)

    # Economy
    workers_active: int
    workers_total: int
    minerals_spent_economy: int
    vespene_spent_economy: int

    # Military
    army_value_minerals: int
    army_value_vespene: int
    army_supply: float
    minerals_spent_army: int
    vespene_spent_army: int

    # Technology
    minerals_spent_technology: int
    vespene_spent_technology: int

    # Losses
    minerals_lost: int
    vespene_lost: int
    minerals_killed: int          # Enemy value destroyed
    vespene_killed: int

    # Units (counts by type)
    unit_counts: Dict[str, int]   # {"Probe": 16, "Zealot": 5, ...}

    # Buildings (counts by type and state)
    buildings_existing: Dict[str, int]      # Completed buildings
    buildings_constructing: Dict[str, int]  # Under construction

    # Upgrades (set of completed upgrade names)
    upgrades_completed: Set[str]   # {"WarpGateResearch", "ProtossGroundWeaponsLevel1", ...}

    # Derived features
    tech_tier: int                 # Tech tier (1/2/3) based on buildings
    base_count: int                # Number of bases (Nexus/CC/Hatchery)
    production_capacity: int       # Number of production buildings
```

#### 3.1.5 UnitEvent

Unit lifecycle event (birth, death, etc.).

```python
@dataclass
class UnitEvent:
    """Unit lifecycle event"""
    frame: int
    event_type: str               # "born" | "died"
    unit_id: int
    unit_type: str                # "Probe", "Marine", etc.
    player_id: int

    # Position
    x: int
    y: int

    # Death-specific
    killer_player_id: Optional[int]
    killer_unit_id: Optional[int]
```

#### 3.1.6 BuildingEvent

Building lifecycle event (construction, completion, destruction).

```python
@dataclass
class BuildingEvent:
    """Building lifecycle event"""
    frame: int
    event_type: str               # "started" | "completed" | "destroyed" | "cancelled"
    unit_id: int
    building_type: str            # "Pylon", "Gateway", etc.
    player_id: int

    # Position
    x: int
    y: int

    # Destruction-specific
    killer_player_id: Optional[int]

    # Timing (for completed buildings)
    started_frame: Optional[int]  # When construction started
    build_time_frames: Optional[int]  # Time to complete
```

#### 3.1.7 UpgradeEvent

Upgrade completion event.

```python
@dataclass
class UpgradeEvent:
    """Upgrade completion event"""
    frame: int
    upgrade_name: str             # "WarpGateResearch", etc.
    player_id: int
    upgrade_level: int            # For multi-level upgrades (1, 2, 3)
```

#### 3.1.8 MessageEvent

Chat/game message event.

```python
@dataclass
class MessageEvent:
    """Chat or game message"""
    frame: int
    game_time_seconds: float
    player_id: int
    text: str
    target: str                   # "all" | "allies" | "observers"
```

### 3.2 Output Schema (Parquet Tables)

#### Table 1: replay_metadata.parquet

One row per replay.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Unique identifier |
| file_path | string | Path to replay file |
| map_name | string | Map name |
| map_hash | string | Map hash (nullable) |
| region | string | Region/server |
| game_version | string | SC2 version |
| expansion | string | Expansion |
| game_mode | string | Game mode |
| speed | string | Game speed |
| game_length_frames | int64 | Total frames |
| game_length_seconds | float64 | Duration in seconds |
| end_time | timestamp | Replay end time |
| player_count | int32 | Number of players |
| winner_id | int32 | Winner player ID (nullable) |
| is_complete | bool | Finished normally |
| is_valid | bool | Passed validation |
| extraction_timestamp | timestamp | When extracted |

#### Table 2: players.parquet

One row per player per replay.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Links to metadata |
| player_id | int32 | Player ID |
| name | string | Player name |
| race | string | Race |
| result | string | Win/Loss/Tie |
| final_units | int32 | Final unit count |
| final_buildings | int32 | Final building count |
| final_upgrades | int32 | Upgrades completed |
| final_minerals | int32 | Minerals at end |
| final_vespene | int32 | Vespene at end |

#### Table 3: frame_states.parquet

One row per frame sample per player per replay.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Links to metadata |
| frame | int64 | Frame number |
| game_time_seconds | float64 | Game time |
| player_id | int32 | Player ID |
| minerals | int32 | Current minerals |
| vespene | int32 | Current vespene |
| minerals_collection_rate | float64 | Income rate |
| vespene_collection_rate | float64 | Income rate |
| supply_used | float64 | Supply used |
| supply_made | float64 | Supply capacity |
| workers_active | int32 | Active workers |
| army_value_minerals | int32 | Army value |
| army_value_vespene | int32 | Army value |
| minerals_lost | int32 | Total lost |
| vespene_lost | int32 | Total lost |
| minerals_killed | int32 | Enemy value killed |
| vespene_killed | int32 | Enemy value killed |
| tech_tier | int32 | Tech tier (1/2/3) |
| base_count | int32 | Number of bases |

#### Table 4: unit_counts.parquet

Unit counts per frame per player.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Links to metadata |
| frame | int64 | Frame number |
| player_id | int32 | Player ID |
| unit_type | string | Unit type name |
| count | int32 | Number alive |

#### Table 5: building_counts.parquet

Building counts per frame per player.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Links to metadata |
| frame | int64 | Frame number |
| player_id | int32 | Player ID |
| building_type | string | Building type |
| state | string | "existing" or "constructing" |
| count | int32 | Number in this state |

#### Table 6: upgrades.parquet

Upgrades completed per player.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Links to metadata |
| frame | int64 | Completion frame |
| player_id | int32 | Player ID |
| upgrade_name | string | Upgrade name |
| upgrade_level | int32 | Level (1/2/3) |

#### Table 7: unit_events.parquet

Detailed unit lifecycle events.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Links to metadata |
| frame | int64 | Event frame |
| event_type | string | "born" or "died" |
| unit_id | int64 | Unique unit ID |
| unit_type | string | Unit type |
| player_id | int32 | Owner player ID |
| x | int32 | X position |
| y | int32 | Y position |
| killer_player_id | int32 | Killer player (nullable) |

#### Table 8: building_events.parquet

Detailed building lifecycle events.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Links to metadata |
| frame | int64 | Event frame |
| event_type | string | started/completed/destroyed/cancelled |
| unit_id | int64 | Unique building ID |
| building_type | string | Building type |
| player_id | int32 | Owner player ID |
| x | int32 | X position |
| y | int32 | Y position |
| started_frame | int64 | Construction start (nullable) |
| build_time_frames | int64 | Time to complete (nullable) |

#### Table 9: messages.parquet

Chat messages.

| Column | Type | Description |
|--------|------|-------------|
| replay_hash | string | Links to metadata |
| frame | int64 | Message frame |
| game_time_seconds | float64 | Game time |
| player_id | int32 | Sender player ID |
| text | string | Message text |
| target | string | all/allies/observers |

---

## 4. Module Specifications

### 4.1 Project Structure

```
sc2_replay_extraction/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point for extraction
│   ├── config.py                  # Configuration management
│   │
│   ├── parser/
│   │   ├── __init__.py
│   │   └── replay_parser.py       # Replay loading and validation
│   │
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── event_processor.py     # Main event dispatcher
│   │   ├── unit_handler.py        # Unit event handler
│   │   ├── building_handler.py    # Building event handler
│   │   ├── upgrade_handler.py     # Upgrade event handler
│   │   ├── stats_handler.py       # Player stats handler
│   │   └── message_handler.py     # Message event handler
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── replay_data.py         # ReplayMetadata, PlayerInfo
│   │   ├── frame_data.py          # FrameState, PlayerFrameState
│   │   └── event_data.py          # Event dataclasses
│   │
│   ├── state/
│   │   ├── __init__.py
│   │   ├── game_state_tracker.py  # State tracking across frames
│   │   ├── unit_tracker.py        # Unit lifecycle tracking
│   │   ├── building_tracker.py    # Building lifecycle tracking
│   │   ├── upgrade_tracker.py     # Upgrade accumulation
│   │   └── frame_sampler.py       # Frame sampling logic
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   ├── output_formatter.py    # Format game state for output
│   │   ├── parquet_writer.py      # Parquet file writer
│   │   ├── json_writer.py         # JSON file writer
│   │   └── csv_writer.py          # CSV file writer
│   │
│   └── utils/
│       ├── __init__.py
│       ├── validation.py          # Data validation functions
│       ├── unit_types.py          # Unit/building type definitions
│       └── logging_config.py      # Logging setup
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_parser.py
│   ├── test_event_processors.py
│   ├── test_state_tracker.py
│   ├── test_output_formatter.py
│   └── test_integration.py        # End-to-end tests
│
├── config/
│   ├── default_config.yaml        # Default configuration
│   └── extraction_profiles.yaml   # Preset extraction profiles
│
├── data/
│   ├── raw/                       # Input replays
│   └── processed/                 # Output data
│       ├── metadata/
│       ├── frame_states/
│       └── events/
│
├── docs/
│   ├── architecture.md
│   ├── data_schema.md
│   └── usage_guide.md
│
├── scripts/
│   ├── batch_extract.py           # Batch processing script
│   ├── validate_output.py         # Output validation
│   └── benchmark.py               # Performance benchmarking
│
├── requirements.txt
├── setup.py
├── README.md
└── sc2reader_patch.py             # Bot replay compatibility patch
```

### 4.2 Module Details

#### 4.2.1 src/parser/replay_parser.py

**Purpose:** Load and validate SC2 replay files.

**Key Functions:**
- `load_replay(file_path: str) -> Replay` - Load replay with sc2reader
- `validate_replay(replay: Replay) -> Tuple[bool, List[str]]` - Validate replay
- `extract_metadata(replay: Replay) -> ReplayMetadata` - Extract metadata

**Dependencies:**
- sc2reader (with patch applied)
- src/models/replay_data

**Inputs:** File path to .SC2Replay
**Outputs:** Parsed Replay object + ReplayMetadata

**Algorithm:**
```python
def load_replay(file_path: str) -> Replay:
    """
    Load SC2 replay file with bot replay compatibility

    Returns:
        sc2reader.Replay object

    Raises:
        FileNotFoundError: Replay file not found
        ParseError: Failed to parse replay
    """
    # Check file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Replay not found: {file_path}")

    try:
        # Load with tracker events only (load_level=3)
        replay = sc2reader.load_replay(file_path, load_level=3)
        return replay
    except Exception as e:
        raise ParseError(f"Failed to parse replay: {e}")

def validate_replay(replay: Replay) -> Tuple[bool, List[str]]:
    """
    Validate replay meets quality requirements

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # Check minimum game length (2 minutes = ~1792 frames @ Faster)
    if replay.frames < 1792:
        errors.append(f"Game too short: {replay.frames} frames")

    # Check has tracker events
    if not hasattr(replay, 'tracker_events') or not replay.tracker_events:
        errors.append("No tracker events found")

    # Check SC2 version (should be >= 2.0.8 for tracker events)
    if replay.release_string < "2.0.8":
        errors.append(f"Version too old: {replay.release_string}")

    # Check has players (at least 2 for 1v1)
    # Note: bot replays may have empty players list
    # So this is a warning, not a blocker

    return (len(errors) == 0, errors)
```

#### 4.2.2 src/processors/event_processor.py

**Purpose:** Main event dispatcher that routes events to specialized handlers.

**Key Functions:**
- `process_events(replay: Replay, state_tracker: GameStateTracker) -> None`
- `dispatch_event(event: Event, state_tracker: GameStateTracker) -> None`

**Dependencies:**
- All event handlers (unit, building, upgrade, stats, message)
- GameStateTracker

**Algorithm:**
```python
class EventProcessor:
    def __init__(self, state_tracker: GameStateTracker):
        self.state_tracker = state_tracker
        self.handlers = {
            'UnitBornEvent': UnitHandler(),
            'UnitInitEvent': BuildingHandler(),
            'UnitDoneEvent': BuildingHandler(),
            'UnitDiedEvent': UnitHandler(),
            'UpgradeCompleteEvent': UpgradeHandler(),
            'PlayerStatsEvent': StatsHandler(),
            'ChatEvent': MessageHandler(),
        }

    def process_events(self, replay: Replay) -> None:
        """Process all tracker events in chronological order"""
        for event in replay.tracker_events:
            self.dispatch_event(event)

    def dispatch_event(self, event: Event) -> None:
        """Route event to appropriate handler"""
        event_type = type(event).__name__

        if event_type in self.handlers:
            handler = self.handlers[event_type]
            handler.handle(event, self.state_tracker)
        else:
            # Unknown event type - log but don't fail
            logger.debug(f"Unknown event type: {event_type}")
```

#### 4.2.3 src/state/game_state_tracker.py

**Purpose:** Maintain current game state across all frames.

**Key Functions:**
- `update(event: Event) -> None` - Update state with new event
- `get_state_at_frame(frame: int) -> FrameState` - Get state snapshot
- `get_player_state(player_id: int, frame: int) -> PlayerFrameState`

**Data Structures:**
```python
class GameStateTracker:
    def __init__(self):
        # Unit tracking
        self.units: Dict[int, UnitLifecycle] = {}  # unit_id -> lifecycle

        # Building tracking
        self.buildings: Dict[int, BuildingLifecycle] = {}  # unit_id -> lifecycle

        # Upgrade tracking (per player)
        self.upgrades: Dict[int, Set[str]] = defaultdict(set)  # player_id -> upgrade names

        # Player stats (latest known)
        self.player_stats: Dict[int, PlayerStatsEvent] = {}  # player_id -> latest stats

        # Messages
        self.messages: List[MessageEvent] = []

        # Current frame
        self.current_frame: int = 0
```

**Key Methods:**
```python
def get_state_at_frame(self, frame: int) -> FrameState:
    """
    Get complete game state at specified frame

    This is the key method for frame sampling.
    """
    player_states = {}

    # Get all player IDs from units/buildings
    player_ids = self._get_player_ids()

    for player_id in player_ids:
        player_states[player_id] = self._build_player_state(player_id, frame)

    return FrameState(
        frame=frame,
        game_time_seconds=frame / 22.4,  # Convert to seconds (Faster speed)
        player_states=player_states,
        # Optionally include recent events
        units_born=self._get_recent_births(frame),
        units_died=self._get_recent_deaths(frame),
        # ... other events
    )

def _build_player_state(self, player_id: int, frame: int) -> PlayerFrameState:
    """Build player state at specific frame"""

    # Count units alive at this frame
    unit_counts = self._count_units(player_id, frame)

    # Count buildings by state
    buildings_existing = self._count_buildings(player_id, frame, "existing")
    buildings_constructing = self._count_buildings(player_id, frame, "constructing")

    # Get upgrades completed by this frame
    upgrades = self._get_upgrades(player_id, frame)

    # Get latest player stats before this frame
    stats = self._get_latest_stats(player_id, frame)

    # Calculate derived features
    tech_tier = self._calculate_tech_tier(player_id, buildings_existing)
    base_count = self._count_bases(player_id, buildings_existing)

    return PlayerFrameState(
        player_id=player_id,
        minerals=stats.minerals_current if stats else 0,
        vespene=stats.vespene_current if stats else 0,
        # ... all other fields
        unit_counts=unit_counts,
        buildings_existing=buildings_existing,
        buildings_constructing=buildings_constructing,
        upgrades_completed=upgrades,
        tech_tier=tech_tier,
        base_count=base_count,
    )
```

#### 4.2.4 src/state/frame_sampler.py

**Purpose:** Sample game state at specified intervals.

**Key Functions:**
- `sample_frames(replay: Replay, tracker: GameStateTracker, interval: int) -> List[FrameState]`

**Algorithm:**
```python
class FrameSampler:
    def __init__(self, interval_frames: int = 112):
        """
        Args:
            interval_frames: Frames between samples (default: 112 = 5 seconds @ Faster)
        """
        self.interval_frames = interval_frames

    def sample_frames(self, replay: Replay, tracker: GameStateTracker) -> List[FrameState]:
        """
        Sample game state at regular intervals

        Returns:
            List of FrameState objects
        """
        samples = []

        # Sample from frame 0 to replay end
        for frame in range(0, replay.frames, self.interval_frames):
            state = tracker.get_state_at_frame(frame)
            samples.append(state)

        # Always include final frame
        if replay.frames % self.interval_frames != 0:
            final_state = tracker.get_state_at_frame(replay.frames)
            samples.append(final_state)

        return samples
```

#### 4.2.5 src/output/parquet_writer.py

**Purpose:** Write extracted data to Parquet format.

**Key Functions:**
- `write_metadata(metadata: ReplayMetadata, output_dir: str) -> None`
- `write_frame_states(states: List[FrameState], output_dir: str) -> None`
- `write_events(events: List[Event], output_dir: str) -> None`

**Dependencies:**
- pandas
- pyarrow

**Algorithm:**
```python
class ParquetWriter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_frame_states(self, replay_hash: str, states: List[FrameState]) -> None:
        """
        Write frame states to Parquet

        Creates multiple tables:
        - frame_states.parquet (main player stats)
        - unit_counts.parquet (unit counts by type)
        - building_counts.parquet (building counts by type/state)
        """
        # Convert to pandas DataFrames
        main_rows = []
        unit_rows = []
        building_rows = []

        for state in states:
            for player_id, player_state in state.player_states.items():
                # Main frame state row
                main_rows.append({
                    'replay_hash': replay_hash,
                    'frame': state.frame,
                    'game_time_seconds': state.game_time_seconds,
                    'player_id': player_id,
                    'minerals': player_state.minerals,
                    'vespene': player_state.vespene,
                    # ... all other fields
                })

                # Unit counts rows
                for unit_type, count in player_state.unit_counts.items():
                    unit_rows.append({
                        'replay_hash': replay_hash,
                        'frame': state.frame,
                        'player_id': player_id,
                        'unit_type': unit_type,
                        'count': count,
                    })

                # Building counts rows
                for building_type, count in player_state.buildings_existing.items():
                    building_rows.append({
                        'replay_hash': replay_hash,
                        'frame': state.frame,
                        'player_id': player_id,
                        'building_type': building_type,
                        'state': 'existing',
                        'count': count,
                    })
                # ... same for constructing

        # Write to Parquet with compression
        df_main = pd.DataFrame(main_rows)
        df_main.to_parquet(
            self.output_dir / 'frame_states.parquet',
            engine='pyarrow',
            compression='snappy',
            index=False
        )

        df_units = pd.DataFrame(unit_rows)
        df_units.to_parquet(
            self.output_dir / 'unit_counts.parquet',
            engine='pyarrow',
            compression='snappy',
            index=False
        )

        # ... same for buildings
```

---

## 5. Processing Algorithms

### 5.1 Main Extraction Algorithm

**High-level pseudocode:**

```python
def extract_replay(replay_path: str, config: ExtractionConfig) -> ExtractionResult:
    """
    Main extraction algorithm

    Args:
        replay_path: Path to .SC2Replay file
        config: Extraction configuration

    Returns:
        ExtractionResult with metadata, frame states, events
    """

    # PHASE 1: LOAD AND VALIDATE
    logger.info(f"Loading replay: {replay_path}")

    try:
        # Load replay (with bot compatibility patch applied)
        replay = ReplayParser.load_replay(replay_path)

        # Validate replay
        is_valid, errors = ReplayParser.validate_replay(replay)
        if not is_valid:
            logger.warning(f"Validation errors: {errors}")
            if config.skip_invalid:
                return ExtractionResult(success=False, errors=errors)

        # Extract metadata
        metadata = ReplayParser.extract_metadata(replay)

    except Exception as e:
        logger.error(f"Failed to load replay: {e}")
        return ExtractionResult(success=False, errors=[str(e)])

    # PHASE 2: INITIALIZE STATE TRACKING
    logger.info("Initializing state tracker")
    state_tracker = GameStateTracker()

    # PHASE 3: PROCESS EVENTS
    logger.info(f"Processing {len(replay.tracker_events)} events")
    event_processor = EventProcessor(state_tracker)

    try:
        event_processor.process_events(replay)
    except Exception as e:
        logger.error(f"Error processing events: {e}")
        return ExtractionResult(success=False, errors=[str(e)])

    # PHASE 4: SAMPLE FRAMES
    logger.info(f"Sampling frames (interval: {config.frame_interval})")
    sampler = FrameSampler(interval_frames=config.frame_interval)

    try:
        frame_states = sampler.sample_frames(replay, state_tracker)
        logger.info(f"Sampled {len(frame_states)} frames")
    except Exception as e:
        logger.error(f"Error sampling frames: {e}")
        return ExtractionResult(success=False, errors=[str(e)])

    # PHASE 5: FORMAT OUTPUT
    logger.info("Formatting output")
    formatter = OutputFormatter(config)

    try:
        formatted_data = formatter.format(
            metadata=metadata,
            frame_states=frame_states,
            events=state_tracker.get_all_events() if config.include_events else None
        )
    except Exception as e:
        logger.error(f"Error formatting output: {e}")
        return ExtractionResult(success=False, errors=[str(e)])

    # PHASE 6: WRITE OUTPUT
    logger.info(f"Writing output to {config.output_dir}")

    try:
        if config.output_format == "parquet":
            writer = ParquetWriter(config.output_dir)
        elif config.output_format == "json":
            writer = JSONWriter(config.output_dir)
        else:
            writer = CSVWriter(config.output_dir)

        writer.write_all(formatted_data)

    except Exception as e:
        logger.error(f"Error writing output: {e}")
        return ExtractionResult(success=False, errors=[str(e)])

    # SUCCESS
    logger.info("Extraction complete")
    return ExtractionResult(
        success=True,
        metadata=metadata,
        frame_count=len(frame_states),
        event_count=len(replay.tracker_events)
    )
```

### 5.2 Building State Differentiation Algorithm

**Challenge:** Distinguish between building states (started/existing/destroyed/cancelled)

**Algorithm:**

```python
def determine_building_state(unit_id: int, target_frame: int,
                            lifecycles: Dict[int, BuildingLifecycle]) -> str:
    """
    Determine building state at a specific frame

    States:
        - "constructing": UnitInitEvent fired, no UnitDoneEvent yet
        - "existing": UnitDoneEvent fired, not yet died
        - "destroyed": UnitDiedEvent fired (after completion)
        - "cancelled": UnitDiedEvent fired before UnitDoneEvent
        - "not_started": Unit hasn't been initialized yet

    Args:
        unit_id: Unique building identifier
        target_frame: Frame to check state at
        lifecycles: Map of unit_id -> BuildingLifecycle

    Returns:
        State string
    """
    if unit_id not in lifecycles:
        return "not_started"

    lifecycle = lifecycles[unit_id]

    # Extract event frames
    init_frame = lifecycle.init_frame  # When construction started
    done_frame = lifecycle.done_frame  # When construction completed
    died_frame = lifecycle.died_frame  # When building was destroyed

    # State determination logic
    if died_frame is not None and died_frame <= target_frame:
        # Building has died
        if done_frame is not None:
            # Died after completion
            return "destroyed"
        else:
            # Died before completion
            return "cancelled"

    if done_frame is not None and done_frame <= target_frame:
        # Construction completed, still alive
        return "existing"

    if init_frame is not None and init_frame <= target_frame:
        # Construction started but not yet done
        return "constructing"

    # Construction not yet started at this frame
    return "not_started"


def count_buildings_by_state(player_id: int, target_frame: int,
                             building_lifecycles: Dict[int, BuildingLifecycle]) -> Dict[str, Dict[str, int]]:
    """
    Count buildings by type and state for a player at a specific frame

    Returns:
        {
            "existing": {"Pylon": 5, "Gateway": 2},
            "constructing": {"Gateway": 1, "CyberneticsCore": 1}
        }
    """
    counts = {
        "existing": defaultdict(int),
        "constructing": defaultdict(int),
        "destroyed": defaultdict(int),
        "cancelled": defaultdict(int),
    }

    for unit_id, lifecycle in building_lifecycles.items():
        # Skip if not owned by this player
        if lifecycle.player_id != player_id:
            continue

        # Determine state
        state = determine_building_state(unit_id, target_frame, building_lifecycles)

        # Skip if not relevant (not_started or destroyed/cancelled for state counts)
        if state in ["existing", "constructing"]:
            building_type = lifecycle.building_type
            counts[state][building_type] += 1

    return counts
```

### 5.3 Unit Counting Algorithm

```python
def count_units_alive(player_id: int, target_frame: int,
                      unit_lifecycles: Dict[int, UnitLifecycle]) -> Dict[str, int]:
    """
    Count units alive at a specific frame for a player

    Returns:
        {"Probe": 16, "Zealot": 5, "Stalker": 3, ...}
    """
    counts = defaultdict(int)

    for unit_id, lifecycle in unit_lifecycles.items():
        # Skip if not owned by this player
        if lifecycle.player_id != player_id:
            continue

        # Determine if unit is alive at target_frame
        born_frame = lifecycle.born_frame or lifecycle.init_frame
        done_frame = lifecycle.done_frame or born_frame  # When unit becomes functional
        died_frame = lifecycle.died_frame or float('inf')

        # Unit is alive if:
        # - Construction/birth completed by target_frame
        # - Death hasn't occurred yet
        if done_frame <= target_frame < died_frame:
            unit_type = lifecycle.unit_type
            counts[unit_type] += 1

    return dict(counts)
```

### 5.4 Tech Tier Calculation

```python
def calculate_tech_tier(player_id: int, race: str,
                       buildings_existing: Dict[str, int]) -> int:
    """
    Calculate tech tier based on completed buildings

    Args:
        player_id: Player ID
        race: Player's race (Protoss/Terran/Zerg)
        buildings_existing: Completed buildings count

    Returns:
        Tech tier (1, 2, or 3)
    """
    if race == "Protoss":
        # Tier 1: Nexus, Gateway
        # Tier 2: CyberneticsCore
        # Tier 3: Twilight Council OR Dark Shrine OR Templar Archives
        if any(b in buildings_existing for b in ["TwilightCouncil", "DarkShrine", "TemplarArchive", "FleetBeacon"]):
            return 3
        if "CyberneticsCore" in buildings_existing:
            return 2
        return 1

    elif race == "Terran":
        # Tier 1: CommandCenter, Barracks
        # Tier 2: Factory
        # Tier 3: Starport OR Fusion Core
        if "FusionCore" in buildings_existing or "Starport" in buildings_existing:
            return 3
        if "Factory" in buildings_existing:
            return 2
        return 1

    elif race == "Zerg":
        # Tier 1: Hatchery
        # Tier 2: Lair
        # Tier 3: Hive OR Infestation Pit OR Spire
        if "Hive" in buildings_existing or "InfestationPit" in buildings_existing or "Spire" in buildings_existing:
            return 3
        if "Lair" in buildings_existing:
            return 2
        return 1

    return 1  # Default
```

---

## 6. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)

**Goal:** Set up project structure and core parsing functionality

**Tasks:**
1. Project setup
   - Create directory structure
   - Set up virtual environment
   - Install dependencies (sc2reader, pandas, pyarrow)
   - Copy sc2reader_patch.py to project

2. Implement data models (src/models/)
   - ReplayMetadata, PlayerInfo dataclasses
   - FrameState, PlayerFrameState dataclasses
   - Event dataclasses (UnitEvent, BuildingEvent, etc.)

3. Implement replay parser (src/parser/)
   - load_replay() function
   - validate_replay() function
   - extract_metadata() function
   - Unit tests with sample replays

**Deliverables:**
- Working project structure
- Data models defined
- Replay loading and validation working
- Tests passing with sample replays

**Success Criteria:**
- Can load both ladder and bot replays
- Metadata extraction works correctly
- Validation catches invalid replays

---

### Phase 2: Event Processing (Week 2)

**Goal:** Process tracker events and update game state

**Tasks:**
1. Implement GameStateTracker (src/state/)
   - Initialize tracking data structures
   - Implement update methods for each event type
   - Implement get_state_at_frame() method

2. Implement event handlers (src/processors/)
   - UnitHandler (birth, death)
   - BuildingHandler (init, done, died)
   - UpgradeHandler (completion)
   - StatsHandler (player stats)
   - MessageHandler (chat messages)

3. Implement EventProcessor
   - Event dispatcher
   - Integration with handlers and state tracker

4. Unit tests
   - Test each handler individually
   - Test state tracker updates
   - Test event processing end-to-end

**Deliverables:**
- Complete event processing pipeline
- All handler classes implemented
- State tracking working correctly
- Unit tests passing

**Success Criteria:**
- Events correctly update game state
- Unit/building lifecycles tracked properly
- Player stats captured at each frame
- Upgrades accumulated correctly

---

### Phase 3: Frame Sampling & State Reconstruction (Week 3)

**Goal:** Sample game state at intervals and reconstruct full state

**Tasks:**
1. Implement FrameSampler (src/state/)
   - Configurable interval sampling
   - Always include final frame
   - Handle edge cases (very short games)

2. Implement state reconstruction methods
   - count_units_alive()
   - count_buildings_by_state()
   - calculate_tech_tier()
   - count_bases()
   - Other derived features

3. Implement unit/building type utilities (src/utils/)
   - is_building() function
   - get_unit_category() (worker/army/building)
   - Tech building identification

4. Integration testing
   - Extract full replay end-to-end
   - Verify frame states are correct
   - Check derived features are accurate

**Deliverables:**
- Frame sampling working
- State reconstruction complete
- Derived features implemented
- Integration tests passing

**Success Criteria:**
- Can sample frames at any interval
- State reconstruction is accurate
- Tech tier calculation works for all races
- Base counting is correct

---

### Phase 4: Output Formatting & Writers (Week 4)

**Goal:** Format extracted data and write to output files

**Tasks:**
1. Implement OutputFormatter (src/output/)
   - Convert FrameState to output schema
   - Flatten nested structures
   - Apply data validation

2. Implement writers
   - ParquetWriter (priority)
   - JSONWriter (for debugging)
   - CSVWriter (simple alternative)

3. Implement data validation (src/utils/)
   - Check for negative values
   - Verify supply constraints
   - Validate frame ordering
   - Check data completeness

4. Output testing
   - Test each writer format
   - Verify Parquet schema
   - Check JSON structure
   - Validate data integrity

**Deliverables:**
- Output formatting complete
- All writers implemented
- Data validation working
- Output tests passing

**Success Criteria:**
- Parquet files are valid and queryable
- JSON output is human-readable
- Data validation catches errors
- All required fields present in output

---

### Phase 5: Testing & Validation (Week 5)

**Goal:** Comprehensive testing with diverse replays

**Tasks:**
1. Create test replay suite
   - Ladder replays (PvP, TvT, ZvZ, PvT, PvZ, TvZ)
   - Bot replays (AI Arena)
   - Different game lengths (short, medium, long)
   - Different map types

2. Integration tests
   - Full extraction pipeline for each replay type
   - Batch processing tests
   - Error recovery tests

3. Data quality validation
   - Check unit counts match expected ranges
   - Verify building progression is logical
   - Check resource values are reasonable
   - Validate upgrade sequences

4. Performance benchmarking
   - Measure extraction time per replay
   - Measure memory usage
   - Test parallel processing
   - Identify bottlenecks

**Deliverables:**
- Comprehensive test suite
- Integration tests passing
- Benchmark results documented
- Bug fixes applied

**Success Criteria:**
- All test replays extract successfully
- No data corruption detected
- Performance meets targets (25+ replays/sec)
- Memory usage within limits

---

### Phase 6: Documentation & Deployment (Week 6)

**Goal:** Complete documentation and prepare for production use

**Tasks:**
1. Write documentation
   - README.md (quick start, examples)
   - docs/architecture.md (system design)
   - docs/data_schema.md (output schema reference)
   - docs/usage_guide.md (detailed usage)
   - API documentation (docstrings)

2. Create usage scripts
   - scripts/batch_extract.py (batch processing)
   - scripts/validate_output.py (output validation)
   - scripts/benchmark.py (performance testing)

3. Configuration management
   - config/default_config.yaml
   - config/extraction_profiles.yaml (presets)
   - Command-line argument parsing

4. Package for distribution
   - setup.py configuration
   - requirements.txt finalization
   - Entry point scripts
   - Installation testing

**Deliverables:**
- Complete documentation
- Usage scripts ready
- Configuration system working
- Package installable via pip

**Success Criteria:**
- Documentation is clear and complete
- Users can extract replays with minimal setup
- Configuration is flexible and well-documented
- Package installs cleanly

---

## 7. Configuration & Usage

### 7.1 Configuration File (config/default_config.yaml)

```yaml
# SC2 Replay Extraction Configuration

# Input/Output
input:
  replay_dir: "data/raw"
  file_patterns: ["*.SC2Replay"]
  recursive: true

output:
  output_dir: "data/processed"
  format: "parquet"  # parquet | json | csv
  compression: "snappy"  # snappy | gzip | none
  separate_files: true  # Separate files per replay or combined

# Extraction Settings
extraction:
  # Frame sampling interval (frames)
  # 112 frames = 5 seconds @ Faster speed
  # 224 frames = 10 seconds @ Faster speed
  frame_interval: 112

  # Load level for sc2reader (3 = tracker events only)
  load_level: 3

  # Include detailed event logs
  include_events: false

  # Include unit positions (from UnitPositionsEvent)
  include_positions: false

# Validation
validation:
  # Minimum game length (frames)
  min_game_length: 1792  # 2 minutes @ Faster

  # Maximum game length (frames, to skip very long games)
  max_game_length: 89600  # 1 hour @ Faster

  # Minimum SC2 version (for tracker events)
  min_version: "2.0.8"

  # Skip invalid replays or fail
  skip_invalid: true

  # Skip replays with errors during processing
  skip_errors: true

# Performance
performance:
  # Number of parallel workers (0 = auto, -1 = serial)
  num_workers: 0

  # Batch size for parallel processing
  batch_size: 100

  # Memory limit per worker (MB, 0 = no limit)
  memory_limit: 0

# Logging
logging:
  level: "INFO"  # DEBUG | INFO | WARNING | ERROR
  log_file: "logs/extraction.log"
  console_output: true

# Feature Engineering
features:
  # Calculate tech tier
  calculate_tech_tier: true

  # Count bases
  count_bases: true

  # Calculate production capacity
  calculate_production_capacity: true

  # Include spatial features (experimental)
  include_spatial: false
```

### 7.2 Command-Line Usage

```bash
# Extract a single replay
python -m src.main extract replay.SC2Replay --output data/processed

# Extract all replays in a directory
python -m src.main extract data/raw/*.SC2Replay --output data/processed

# Use custom configuration
python -m src.main extract data/raw/ --config config/my_config.yaml

# Batch processing with parallel workers
python -m src.main batch data/raw/ --output data/processed --workers 4

# Validate output
python scripts/validate_output.py data/processed/

# Benchmark performance
python scripts/benchmark.py data/raw/ --replays 100
```

### 7.3 Python API Usage

```python
from src.main import ReplayExtractor
from src.config import ExtractionConfig

# Create extractor with default config
extractor = ReplayExtractor()

# Extract single replay
result = extractor.extract("replay.SC2Replay")
print(f"Extracted {result.frame_count} frames")

# Extract with custom config
config = ExtractionConfig(
    frame_interval=224,  # 10-second intervals
    output_format="json",
    include_events=True
)
extractor = ReplayExtractor(config)
result = extractor.extract("replay.SC2Replay", output_dir="data/processed")

# Batch processing
results = extractor.extract_batch(
    replay_paths=["replay1.SC2Replay", "replay2.SC2Replay"],
    output_dir="data/processed",
    parallel=True,
    num_workers=4
)

# Access extracted data
import pandas as pd

# Load frame states
df_frames = pd.read_parquet("data/processed/frame_states.parquet")
print(df_frames.head())

# Load unit counts
df_units = pd.read_parquet("data/processed/unit_counts.parquet")
print(df_units[df_units.player_id == 1])

# Load metadata
df_metadata = pd.read_parquet("data/processed/replay_metadata.parquet")
print(df_metadata.columns)
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Coverage target:** 80%+

**Test modules:**

1. **test_parser.py**
   - Test replay loading (ladder + bot replays)
   - Test metadata extraction
   - Test validation logic
   - Test error handling (missing files, corrupt replays)

2. **test_event_processors.py**
   - Test each event handler individually
   - Test event dispatcher
   - Test event ordering
   - Test edge cases (simultaneous events)

3. **test_state_tracker.py**
   - Test unit lifecycle tracking
   - Test building state transitions
   - Test upgrade accumulation
   - Test stats updates
   - Test get_state_at_frame()

4. **test_output_formatter.py**
   - Test data formatting
   - Test schema validation
   - Test feature engineering
   - Test each writer (Parquet/JSON/CSV)

### 8.2 Integration Tests

**test_integration.py:**

```python
def test_full_extraction_ladder_replay():
    """Test complete extraction pipeline with ladder replay"""
    extractor = ReplayExtractor()
    result = extractor.extract("tests/fixtures/ladder_pvp.SC2Replay")

    assert result.success
    assert result.frame_count > 0
    assert result.metadata.player_count == 2

    # Verify output files exist
    assert os.path.exists("data/processed/frame_states.parquet")

    # Load and validate data
    df = pd.read_parquet("data/processed/frame_states.parquet")
    assert len(df) > 0
    assert "minerals" in df.columns

def test_full_extraction_bot_replay():
    """Test extraction with AI Arena bot replay"""
    # This tests sc2reader_patch compatibility
    extractor = ReplayExtractor()
    result = extractor.extract("tests/fixtures/bot_match.SC2Replay")

    assert result.success
    assert result.frame_count > 0

def test_batch_processing():
    """Test parallel batch processing"""
    replays = glob.glob("tests/fixtures/*.SC2Replay")
    extractor = ReplayExtractor()

    results = extractor.extract_batch(replays, parallel=True, num_workers=2)

    assert len(results) == len(replays)
    assert all(r.success for r in results)
```

### 8.3 Test Fixtures

**Required test replays:**

- `ladder_pvp.SC2Replay` - Ladder Protoss vs Protoss
- `ladder_tvt.SC2Replay` - Ladder Terran vs Terran
- `ladder_zvz.SC2Replay` - Ladder Zerg vs Zerg
- `bot_match.SC2Replay` - AI Arena bot replay
- `short_game.SC2Replay` - Very short game (< 2 min)
- `long_game.SC2Replay` - Long game (> 20 min)

### 8.4 Data Validation Tests

```python
def test_data_validity():
    """Test extracted data passes validation checks"""
    df = pd.read_parquet("output/frame_states.parquet")

    # No negative resources
    assert (df.minerals >= 0).all()
    assert (df.vespene >= 0).all()

    # Supply constraints
    assert (df.supply_used <= df.supply_made).all()

    # Frames are ordered
    assert df.frame.is_monotonic_increasing

    # Valid player IDs
    assert df.player_id.isin([1, 2]).all()
```

---

## 9. Example Outputs

### 9.1 Example JSON Output (Single Frame)

```json
{
  "replay_hash": "a3f2b9c8d1e4f5a6b7c8d9e0f1a2b3c4",
  "frame": 1120,
  "game_time_seconds": 50.0,
  "player_states": {
    "1": {
      "player_id": 1,
      "minerals": 450,
      "vespene": 200,
      "minerals_collection_rate": 850.5,
      "vespene_collection_rate": 320.0,
      "supply_used": 38.0,
      "supply_made": 46.0,
      "supply_cap": 200.0,
      "workers_active": 22,
      "workers_total": 22,
      "army_value_minerals": 600,
      "army_value_vespene": 200,
      "minerals_lost": 0,
      "vespene_lost": 0,
      "minerals_killed": 100,
      "vespene_killed": 0,
      "tech_tier": 2,
      "base_count": 2,
      "unit_counts": {
        "Probe": 22,
        "Zealot": 8,
        "Stalker": 3,
        "Sentry": 1,
        "Observer": 1
      },
      "buildings_existing": {
        "Nexus": 2,
        "Pylon": 6,
        "Gateway": 3,
        "CyberneticsCore": 1,
        "Assimilator": 2,
        "RoboticsFacility": 1
      },
      "buildings_constructing": {
        "Gateway": 1,
        "Pylon": 1
      },
      "upgrades_completed": [
        "WarpGateResearch",
        "ProtossGroundWeaponsLevel1"
      ]
    },
    "2": {
      "player_id": 2,
      "minerals": 380,
      "vespene": 150,
      "supply_used": 35.0,
      "supply_made": 38.0,
      "workers_active": 20,
      "army_value_minerals": 550,
      "tech_tier": 2,
      "base_count": 2,
      "unit_counts": {
        "Probe": 20,
        "Zealot": 10,
        "Stalker": 2,
        "Adept": 2
      },
      "buildings_existing": {
        "Nexus": 2,
        "Pylon": 5,
        "Gateway": 4,
        "CyberneticsCore": 1,
        "Assimilator": 2
      },
      "buildings_constructing": {},
      "upgrades_completed": [
        "WarpGateResearch"
      ]
    }
  }
}
```

### 9.2 Example Parquet Table (frame_states.parquet)

| replay_hash | frame | game_time_seconds | player_id | minerals | vespene | supply_used | supply_made | workers_active | tech_tier | base_count |
|-------------|-------|-------------------|-----------|----------|---------|-------------|-------------|----------------|-----------|------------|
| a3f2b9c8... | 0     | 0.0               | 1         | 50       | 0       | 12.0        | 15.0        | 12             | 1         | 1          |
| a3f2b9c8... | 0     | 0.0               | 2         | 50       | 0       | 12.0        | 15.0        | 12             | 1         | 1          |
| a3f2b9c8... | 112   | 5.0               | 1         | 180      | 0       | 14.0        | 15.0        | 14             | 1         | 1          |
| a3f2b9c8... | 112   | 5.0               | 2         | 175      | 0       | 14.0        | 15.0        | 14             | 1         | 1          |
| a3f2b9c8... | 224   | 10.0              | 1         | 320      | 50      | 18.0        | 23.0        | 16             | 1         | 1          |
| ...         | ...   | ...               | ...       | ...      | ...     | ...         | ...         | ...            | ...       | ...        |

### 9.3 Example unit_counts.parquet

| replay_hash | frame | player_id | unit_type | count |
|-------------|-------|-----------|-----------|-------|
| a3f2b9c8... | 0     | 1         | Probe     | 12    |
| a3f2b9c8... | 0     | 1         | Nexus     | 1     |
| a3f2b9c8... | 112   | 1         | Probe     | 14    |
| a3f2b9c8... | 224   | 1         | Probe     | 16    |
| a3f2b9c8... | 224   | 1         | Zealot    | 2     |
| ...         | ...   | ...       | ...       | ...   |

---

## 10. Performance Considerations

### 10.1 Target Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Parsing speed | 25+ replays/sec | Single-threaded, 5-min average game |
| Memory usage | < 500 MB per replay | Peak memory during processing |
| Parallel speedup | Near-linear | 4 workers = 4x faster |
| Output file size | 50-100 KB per replay | Parquet with compression |
| Processing stability | No memory leaks | 1000+ replays continuous |

### 10.2 Optimization Strategies

**1. Memory Management:**
- Stream processing (don't load all replays at once)
- Release replay objects after extraction
- Use generators for frame sampling
- Periodic garbage collection for large batches

**2. Parallel Processing:**
- Process replays independently (no shared state)
- Use multiprocessing.Pool for CPU-bound work
- Batch output writes to reduce I/O
- Queue-based architecture for continuous processing

**3. I/O Optimization:**
- Parquet columnar format (much smaller than JSON)
- Compression (snappy for speed, gzip for size)
- Batch writes instead of per-replay
- Separate files by replay_hash for easy partitioning

**4. Algorithmic Optimization:**
- Cache unit type lookups
- Pre-compute building type sets
- Avoid redundant calculations
- Use dict comprehensions over loops

### 10.3 Scalability

**For 10,000 replays:**

Estimated processing time:
- Single-threaded: 400 seconds (6.7 minutes)
- 4 workers: 100 seconds (1.7 minutes)
- 8 workers: 50 seconds

Estimated output size:
- Parquet: 500 MB - 1 GB (compressed)
- JSON: 5-10 GB (uncompressed)

Memory requirements:
- Peak: 2-4 GB (with 8 workers)
- Steady state: < 1 GB

---

## 11. Error Handling & Edge Cases

### 11.1 Error Handling Strategy

**Levels of error handling:**

1. **File-level errors:**
   - Missing replay file → Log error, skip file
   - Corrupt replay file → Log error, skip file
   - Parse error → Log error, skip file (or use fallback)

2. **Event-level errors:**
   - Unknown event type → Log warning, continue
   - Missing event attributes → Use default values
   - Invalid data → Log warning, sanitize or skip

3. **Data-level errors:**
   - Negative values → Clamp to 0, log warning
   - Supply violations → Log warning, continue
   - Missing player data → Infer from events or skip

4. **Output errors:**
   - Write failure → Retry, then fail with error message
   - Schema mismatch → Log error, skip replay
   - Disk full → Fail with clear error message

### 11.2 Edge Cases

**1. Very Short Games (<2 minutes)**
- Handle: Skip if < min_game_length, or mark as invalid
- Reason: Not enough data for meaningful training

**2. Very Long Games (>1 hour)**
- Handle: Process normally, or skip if > max_game_length
- Reason: Potential memory issues, anomalous games

**3. Bot Replays with Empty Players**
- Handle: sc2reader_patch handles this
- Fallback: Infer player IDs from events

**4. Disconnects/Crashes**
- Handle: Check replay.winner, mark as incomplete
- Continue extraction, but flag in metadata

**5. Old Replay Versions (<2.0.8)**
- Handle: Skip if no tracker events available
- Log version incompatibility

**6. Map-Specific Units**
- Handle: Filter out mineral fields, geysers, etc.
- Use unit type whitelist/blacklist

**7. Simultaneous Events (Same Frame)**
- Handle: Process in event order from replay
- Order doesn't matter for state tracking

**8. Unit Transformations (Morphing)**
- Handle: Treat as death of old unit + birth of new unit
- Track both unit IDs

**9. Missing Position Data**
- Handle: Use birth position or last known position
- Position data is optional (sparse anyway)

**10. Replays with No Winner**
- Handle: Mark winner_id as None
- Continue extraction normally

### 11.3 Logging & Debugging

**Log levels:**

- **DEBUG:** Detailed event processing, state transitions
- **INFO:** Replay loading, extraction progress, frame counts
- **WARNING:** Validation failures, missing data, sanitized values
- **ERROR:** Parse failures, write errors, critical issues

**Log example:**

```
2026-01-23 10:15:32 INFO     Loading replay: data/raw/replay1.SC2Replay
2026-01-23 10:15:32 INFO     Replay metadata: Map=AcropolisAIE, Duration=3:52, Players=2
2026-01-23 10:15:32 INFO     Processing 389 tracker events
2026-01-23 10:15:32 DEBUG    UnitBornEvent: Probe (player 1) at frame 0
2026-01-23 10:15:32 DEBUG    UnitInitEvent: Pylon (player 1) at frame 435
2026-01-23 10:15:33 WARNING  Validation: Supply used > supply made at frame 1250 (player 2)
2026-01-23 10:15:33 INFO     Sampled 47 frames (5-second intervals)
2026-01-23 10:15:33 INFO     Writing output to data/processed/
2026-01-23 10:15:33 INFO     Extraction complete: 47 frames, 389 events
```

---

## 12. Future Enhancements

### 12.1 Phase 2 Features

**Advanced Spatial Features:**
- Cluster units into groups (main army, harass groups)
- Detect base locations dynamically
- Calculate map control (territory occupied)
- Detect expansion timing

**Build Order Analysis:**
- Extract build order sequences
- Compare against known templates
- Classify opening strategies

**Advanced Event Analysis:**
- Extract upgrade start times (from command events)
- Detect building cancellations explicitly
- Track unit production queues

**Performance Optimizations:**
- Cython compilation for hot paths
- Distributed processing (Dask/Spark)
- Incremental extraction (only process new replays)
- Feature caching

### 12.2 Data Quality Improvements

**Anomaly Detection:**
- Detect unusual resource accumulation
- Identify bot-like behavior patterns
- Flag suspicious games (hacks, exploits)

**Replay Deduplication:**
- Hash-based duplicate detection
- Skip already-processed replays
- Maintain processing database

**Player Skill Normalization:**
- Extract MMR/league information
- Normalize features by skill level
- Stratified sampling by skill

### 12.3 Alternative Data Sources

**Integration with External Data:**
- Link to build order databases (spawningtool.com)
- Integrate pro-game annotations
- Combine with game balance data

**Real-time Extraction:**
- Watch replay folder for new files
- Auto-extract on file creation
- Live dashboard of extracted data

---

## Appendix A: Dependencies

### A.1 Python Requirements

```
# Core dependencies
sc2reader==1.8.0
pandas>=2.0.0
pyarrow>=10.0.0

# Optional
numpy>=1.24.0
tqdm>=4.65.0  # Progress bars

# Development
pytest>=7.3.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.3.0
```

### A.2 System Requirements

- Python 3.9+
- 4 GB RAM minimum (8 GB recommended for parallel processing)
- 1 GB disk space for code + dependencies
- Variable storage for output (depends on dataset size)

---

## Appendix B: Quick Start

```bash
# 1. Clone repository
git clone https://github.com/username/sc2-replay-extraction.git
cd sc2-replay-extraction

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run on sample replay
python -m src.main extract tests/fixtures/sample_replay.SC2Replay

# 5. Check output
ls data/processed/
```

---

**END OF PLAN**

---

## Document Metadata

**Version:** 1.0
**Date:** 2026-01-23
**Author:** SC2 Replay Extraction Planning Phase
**Status:** Ready for Implementation
**Next Steps:** Begin Phase 1 (Core Infrastructure)
