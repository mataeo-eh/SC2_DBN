# SC2 Replay Extraction System - Architecture

**Version:** 1.0
**Date:** 2026-01-23

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architectural Principles](#2-architectural-principles)
3. [Component Architecture](#3-component-architecture)
4. [Data Flow](#4-data-flow)
5. [State Management](#5-state-management)
6. [Event Processing Pipeline](#6-event-processing-pipeline)
7. [Output Strategy](#7-output-strategy)
8. [Performance Architecture](#8-performance-architecture)
9. [Error Handling Architecture](#9-error-handling-architecture)
10. [Scalability Considerations](#10-scalability-considerations)

---

## 1. System Overview

### 1.1 Purpose

Extract frame-by-frame game state data from StarCraft 2 replay files (.SC2Replay) to train Dynamic Bayesian Networks (DBNs) for strategy prediction.

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTRACTION SYSTEM                         │
│                                                              │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐          │
│  │   INPUT    │──>│  PROCESS   │──>│   OUTPUT   │          │
│  │   LAYER    │   │   LAYER    │   │   LAYER    │          │
│  └────────────┘   └────────────┘   └────────────┘          │
│                                                              │
│  Replay Files  →  Event Processing  →  Structured Data      │
│  (MPQ Archive)    State Tracking       (Parquet/JSON)       │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Key Design Goals

1. **Completeness**: Extract all required data points for DBN training
2. **Correctness**: Accurate state reconstruction and event tracking
3. **Compatibility**: Support both ladder and AI Arena bot replays
4. **Performance**: Process 25+ replays/second (single-threaded)
5. **Scalability**: Handle datasets of 10,000+ replays
6. **Maintainability**: Clean, modular, well-documented code

---

## 2. Architectural Principles

### 2.1 Separation of Concerns

**Principle**: Each component has a single, well-defined responsibility.

**Application**:
- **Parsing**: Load and validate replays
- **Processing**: Handle events and update state
- **State Tracking**: Maintain game state across frames
- **Formatting**: Convert state to output schema
- **Writing**: Persist data to files

### 2.2 Event-Driven Architecture

**Principle**: Process replay as a stream of events, updating state incrementally.

**Benefits**:
- Memory-efficient (don't need full game state in memory)
- Natural fit for SC2 replay structure
- Easy to extend with new event types
- Supports streaming/incremental processing

### 2.3 State Reconstruction

**Principle**: Maintain minimal state, reconstruct full state on demand.

**Strategy**:
- Track unit/building lifecycles (born → done → died)
- Store only state changes (events), not full snapshots
- Reconstruct full state at sample points by replaying events

### 2.4 Immutable Data Models

**Principle**: Data models are immutable (dataclasses, no setters).

**Benefits**:
- Thread-safe
- Easier to reason about
- Cacheable
- No accidental mutations

### 2.5 Fail-Safe Processing

**Principle**: Handle errors gracefully, continue processing when possible.

**Strategy**:
- Per-replay error handling (one bad replay doesn't kill batch)
- Per-event error handling (skip unknown events, log warnings)
- Validation at multiple levels (input, processing, output)

---

## 3. Component Architecture

### 3.1 Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  main.py - CLI, orchestration, batch processing     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       PARSING LAYER                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ReplayParser                                       │    │
│  │  - load_replay()                                    │    │
│  │  - validate_replay()                                │    │
│  │  - extract_metadata()                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     PROCESSING LAYER                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  EventProcessor (dispatcher)                        │    │
│  │    ├─> UnitEventHandler                             │    │
│  │    ├─> BuildingEventHandler                         │    │
│  │    ├─> UpgradeEventHandler                          │    │
│  │    ├─> StatsEventHandler                            │    │
│  │    └─> MessageEventHandler                          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    STATE TRACKING LAYER                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  GameStateTracker                                   │    │
│  │  - Units: Dict[unit_id, UnitLifecycle]              │    │
│  │  - Buildings: Dict[unit_id, BuildingLifecycle]      │    │
│  │  - Upgrades: Dict[player_id, Set[upgrade_name]]     │    │
│  │  - Stats: Dict[player_id, PlayerStatsEvent]         │    │
│  │  - get_state_at_frame(frame) -> FrameState          │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  FrameSampler                                       │    │
│  │  - sample_frames(interval) -> List[FrameState]      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     FORMATTING LAYER                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  OutputFormatter                                    │    │
│  │  - format_metadata()                                │    │
│  │  - format_frame_states()                            │    │
│  │  - format_events()                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Parquet     │  │     JSON     │  │     CSV      │      │
│  │  Writer      │  │    Writer    │  │   Writer     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

#### ReplayParser
**Responsibility**: Load replay files and extract basic metadata

**Inputs**: File path to .SC2Replay
**Outputs**: sc2reader.Replay object, ReplayMetadata

**Key Methods**:
- `load_replay(path) -> Replay` - Load with sc2reader (load_level=3)
- `validate_replay(replay) -> (bool, errors)` - Check quality
- `extract_metadata(replay) -> ReplayMetadata` - Extract replay info

**Dependencies**: sc2reader (with patch), models.replay_data

#### EventProcessor
**Responsibility**: Dispatch events to specialized handlers

**Inputs**: Replay object
**Outputs**: None (updates GameStateTracker)

**Key Methods**:
- `process_events(replay)` - Process all tracker events
- `dispatch_event(event)` - Route to appropriate handler

**Dependencies**: All event handlers, GameStateTracker

#### Event Handlers
**Responsibility**: Process specific event types and update state

**Handlers**:
- `UnitEventHandler` - UnitBornEvent, UnitDiedEvent
- `BuildingEventHandler` - UnitInitEvent, UnitDoneEvent, UnitDiedEvent
- `UpgradeEventHandler` - UpgradeCompleteEvent
- `StatsEventHandler` - PlayerStatsEvent
- `MessageEventHandler` - ChatEvent

**Interface**:
```python
class EventHandler(ABC):
    @abstractmethod
    def handle(self, event: Event, state_tracker: GameStateTracker) -> None:
        pass
```

#### GameStateTracker
**Responsibility**: Maintain current game state across all frames

**State Storage**:
- `units: Dict[int, UnitLifecycle]` - Unit lifecycles by unit_id
- `buildings: Dict[int, BuildingLifecycle]` - Building lifecycles by unit_id
- `upgrades: Dict[int, Set[str]]` - Upgrades by player_id
- `player_stats: Dict[int, PlayerStatsEvent]` - Latest stats by player_id
- `messages: List[MessageEvent]` - All chat messages

**Key Methods**:
- `get_state_at_frame(frame) -> FrameState` - Reconstruct full state
- `count_units_alive(player_id, frame) -> Dict[str, int]` - Count units
- `count_buildings_by_state(player_id, frame) -> Dict[str, Dict[str, int]]`

**Dependencies**: models.frame_data, models.event_data

#### FrameSampler
**Responsibility**: Sample game state at regular intervals

**Inputs**: Replay, GameStateTracker, interval (frames)
**Outputs**: List[FrameState]

**Key Methods**:
- `sample_frames(replay, tracker, interval) -> List[FrameState]`

**Strategy**: Calls `tracker.get_state_at_frame(frame)` at each sample point

#### OutputFormatter
**Responsibility**: Convert game state to output schema

**Inputs**: ReplayMetadata, List[FrameState], List[Event]
**Outputs**: Formatted data structures (dicts/DataFrames)

**Key Methods**:
- `format_metadata(metadata) -> dict`
- `format_frame_states(states) -> pd.DataFrame`
- `format_events(events) -> pd.DataFrame`

**Transformations**:
- Flatten nested structures
- Convert sets to lists
- Apply feature engineering
- Validate data

#### Writers
**Responsibility**: Persist formatted data to files

**Writers**:
- `ParquetWriter` - Write Parquet files (recommended)
- `JSONWriter` - Write JSON files (debugging)
- `CSVWriter` - Write CSV files (simple alternative)

**Interface**:
```python
class DataWriter(ABC):
    @abstractmethod
    def write_metadata(self, metadata: ReplayMetadata, path: str) -> None:
        pass

    @abstractmethod
    def write_frame_states(self, states: List[FrameState], path: str) -> None:
        pass

    @abstractmethod
    def write_events(self, events: List[Event], path: str) -> None:
        pass
```

---

## 4. Data Flow

### 4.1 Extraction Pipeline

```
1. LOAD REPLAY
   ├─ Import sc2reader_patch (CRITICAL for bot replays)
   ├─ Call sc2reader.load_replay(path, load_level=3)
   ├─ Validate replay (min length, version, completion)
   └─ Extract metadata (map, players, duration)
        │
        ▼
2. INITIALIZE STATE TRACKER
   ├─ Create GameStateTracker instance
   ├─ Initialize tracking data structures (empty dicts)
   └─ Set current_frame = 0
        │
        ▼
3. PROCESS EVENTS (for each event in replay.tracker_events)
   ├─ Dispatch event to appropriate handler
   ├─ Handler updates GameStateTracker
   │   ├─ UnitBornEvent → Add to units dict
   │   ├─ UnitDiedEvent → Mark as dead in units dict
   │   ├─ UnitInitEvent → Add to buildings dict (constructing)
   │   ├─ UnitDoneEvent → Mark as completed in buildings dict
   │   ├─ UpgradeCompleteEvent → Add to upgrades set
   │   └─ PlayerStatsEvent → Update player_stats dict
   └─ Continue to next event
        │
        ▼
4. SAMPLE FRAMES (every N frames, default 112)
   ├─ Call tracker.get_state_at_frame(frame)
   │   ├─ Count units alive at this frame
   │   ├─ Count buildings by state
   │   ├─ Get upgrades completed by this frame
   │   ├─ Get latest player stats before this frame
   │   └─ Calculate derived features (tech_tier, base_count)
   ├─ Create FrameState object
   └─ Append to frames list
        │
        ▼
5. FORMAT OUTPUT
   ├─ Convert ReplayMetadata to output schema
   ├─ Convert List[FrameState] to DataFrames
   │   ├─ frame_states.parquet (main stats)
   │   ├─ unit_counts.parquet (unit counts by type)
   │   ├─ building_counts.parquet (building counts by type/state)
   │   └─ upgrades.parquet (upgrade completions)
   └─ Validate data (no negatives, valid ranges)
        │
        ▼
6. WRITE OUTPUT
   ├─ Write replay_metadata.parquet
   ├─ Write frame_states.parquet
   ├─ Write unit_counts.parquet
   ├─ Write building_counts.parquet
   ├─ Write upgrades.parquet
   └─ Write messages.parquet (if messages exist)
        │
        ▼
7. CLEANUP
   ├─ Release replay object (free memory)
   ├─ Log extraction statistics
   └─ Return ExtractionResult
```

### 4.2 Event Flow

```
Replay File
    │
    ▼
sc2reader.load_replay()
    │
    ▼
replay.tracker_events (sorted by frame)
    │
    ├─> UnitBornEvent ───────────> UnitEventHandler ──┐
    ├─> UnitInitEvent ───────────> BuildingEventHandler ─┤
    ├─> UnitDoneEvent ───────────> BuildingEventHandler ─┤
    ├─> UnitDiedEvent ───────────> UnitEventHandler ──┤
    ├─> UpgradeCompleteEvent ────> UpgradeEventHandler ┼──> GameStateTracker
    ├─> PlayerStatsEvent ────────> StatsEventHandler ──┤
    └─> ChatEvent ───────────────> MessageEventHandler ┘
                                                        │
                                                        ▼
                                            State Updated (units, buildings,
                                                         upgrades, stats)
```

### 4.3 State Reconstruction Flow

```
FrameSampler.sample_frames(interval=112)
    │
    ├─> For frame in range(0, replay.frames, 112):
    │       │
    │       ▼
    │   GameStateTracker.get_state_at_frame(frame)
    │       │
    │       ├─> For player_id in [1, 2, ...]:
    │       │       │
    │       │       ├─> count_units_alive(player_id, frame)
    │       │       │     └─> Check each unit lifecycle:
    │       │       │           if born_frame <= frame < died_frame: count++
    │       │       │
    │       │       ├─> count_buildings_by_state(player_id, frame)
    │       │       │     └─> For each building:
    │       │       │           Determine state (started/existing/destroyed)
    │       │       │           Count by type and state
    │       │       │
    │       │       ├─> get_upgrades_completed(player_id, frame)
    │       │       │     └─> Filter upgrades where completion_frame <= frame
    │       │       │
    │       │       ├─> get_latest_stats(player_id, frame)
    │       │       │     └─> Find most recent PlayerStatsEvent before frame
    │       │       │
    │       │       └─> Build PlayerFrameState object
    │       │
    │       └─> Build FrameState object with all player states
    │
    └─> Return List[FrameState]
```

---

## 5. State Management

### 5.1 State Tracking Strategy

**Core Principle**: Event-driven state updates with on-demand reconstruction.

**Why Not Store Full State Every Frame?**
- Memory: 5000 frames × 2 players × ~100 features = 1M data points per replay
- Redundancy: Most features don't change every frame
- Inefficiency: Lots of copying and storage

**Our Approach**: Store minimal state (lifecycle events), reconstruct on demand.

### 5.2 Unit Lifecycle Tracking

```python
@dataclass
class UnitLifecycle:
    unit_id: int
    unit_type: str
    player_id: int

    # Event frames
    born_frame: Optional[int] = None      # UnitBornEvent
    init_frame: Optional[int] = None      # UnitInitEvent (for buildings)
    done_frame: Optional[int] = None      # UnitDoneEvent
    died_frame: Optional[int] = None      # UnitDiedEvent

    # Position
    x: int = 0
    y: int = 0

    # Death info
    killer_player_id: Optional[int] = None
    killer_unit_id: Optional[int] = None

def is_alive_at_frame(self, frame: int) -> bool:
    """Check if unit is alive at given frame"""
    # When unit becomes functional
    active_frame = self.done_frame or self.born_frame or self.init_frame

    # When unit stops existing
    death_frame = self.died_frame or float('inf')

    return active_frame <= frame < death_frame
```

### 5.3 Building State Machine

```
                  UnitInitEvent
                       │
                       ▼
    ┌─────────────────────────────────┐
    │      CONSTRUCTING               │
    │  (init_frame <= frame < done)   │
    └─────────────────────────────────┘
          │                    │
          │ UnitDoneEvent      │ UnitDiedEvent
          ▼                    ▼
    ┌──────────────┐     ┌──────────────┐
    │   EXISTING   │     │  CANCELLED   │
    │   (alive)    │     │   (died)     │
    └──────────────┘     └──────────────┘
          │
          │ UnitDiedEvent
          ▼
    ┌──────────────┐
    │  DESTROYED   │
    └──────────────┘
```

**State Determination Algorithm**:
```python
def get_building_state(lifecycle: BuildingLifecycle, frame: int) -> str:
    if lifecycle.died_frame and lifecycle.died_frame <= frame:
        # Building has died
        if lifecycle.done_frame:
            return "destroyed"  # Completed then destroyed
        else:
            return "cancelled"  # Destroyed before completion

    if lifecycle.done_frame and lifecycle.done_frame <= frame:
        return "existing"  # Completed and still alive

    if lifecycle.init_frame and lifecycle.init_frame <= frame:
        return "constructing"  # Construction started but not done

    return "not_started"  # Construction hasn't begun
```

### 5.4 Upgrade Accumulation

```python
class UpgradeTracker:
    def __init__(self):
        # player_id -> Set[upgrade_name]
        self.upgrades: Dict[int, Set[str]] = defaultdict(set)

        # For frame-specific queries:
        # (player_id, upgrade_name) -> completion_frame
        self.completion_frames: Dict[Tuple[int, str], int] = {}

    def add_upgrade(self, player_id: int, upgrade_name: str, frame: int):
        self.upgrades[player_id].add(upgrade_name)
        self.completion_frames[(player_id, upgrade_name)] = frame

    def get_upgrades_at_frame(self, player_id: int, frame: int) -> Set[str]:
        """Get all upgrades completed by this frame"""
        result = set()
        for upgrade_name in self.upgrades[player_id]:
            completion_frame = self.completion_frames[(player_id, upgrade_name)]
            if completion_frame <= frame:
                result.add(upgrade_name)
        return result
```

### 5.5 Player Stats Tracking

**Challenge**: PlayerStatsEvent occurs periodically (every ~3-5 seconds), not every frame.

**Solution**: Store all stats events, retrieve latest one before target frame.

```python
class StatsTracker:
    def __init__(self):
        # List of (frame, player_id, stats) tuples, kept sorted by frame
        self.stats_events: List[Tuple[int, int, PlayerStatsEvent]] = []

    def add_stats(self, frame: int, player_id: int, stats: PlayerStatsEvent):
        self.stats_events.append((frame, player_id, stats))

    def get_latest_stats(self, player_id: int, target_frame: int) -> Optional[PlayerStatsEvent]:
        """Get most recent stats event before target_frame"""
        latest = None
        latest_frame = -1

        for frame, pid, stats in self.stats_events:
            if pid == player_id and frame <= target_frame and frame > latest_frame:
                latest = stats
                latest_frame = frame

        return latest
```

---

## 6. Event Processing Pipeline

### 6.1 Event Processing Flow

```python
class EventProcessor:
    def __init__(self, state_tracker: GameStateTracker):
        self.state_tracker = state_tracker
        self.handlers = self._initialize_handlers()

    def process_events(self, replay: Replay) -> None:
        """Process all tracker events"""
        for event in replay.tracker_events:
            try:
                self.dispatch_event(event)
            except Exception as e:
                logger.warning(f"Error processing event {event}: {e}")
                # Continue processing (fail-safe)

    def dispatch_event(self, event: Event) -> None:
        """Route event to appropriate handler"""
        event_type = type(event).__name__

        if event_type in self.handlers:
            handler = self.handlers[event_type]
            handler.handle(event, self.state_tracker)
        else:
            logger.debug(f"Unknown event type: {event_type}")
```

### 6.2 Handler Pattern

```python
class UnitEventHandler(EventHandler):
    def handle(self, event: Event, tracker: GameStateTracker) -> None:
        if isinstance(event, UnitBornEvent):
            self._handle_birth(event, tracker)
        elif isinstance(event, UnitDiedEvent):
            self._handle_death(event, tracker)

    def _handle_birth(self, event: UnitBornEvent, tracker: GameStateTracker):
        # Skip non-game units (minerals, geysers)
        if self._is_map_unit(event.unit_type_name):
            return

        lifecycle = UnitLifecycle(
            unit_id=event.unit_id,
            unit_type=event.unit_type_name,
            player_id=event.control_pid,
            born_frame=event.frame,
            x=event.x,
            y=event.y
        )
        tracker.units[event.unit_id] = lifecycle

    def _handle_death(self, event: UnitDiedEvent, tracker: GameStateTracker):
        if event.unit_id in tracker.units:
            lifecycle = tracker.units[event.unit_id]
            lifecycle.died_frame = event.frame
            lifecycle.killer_player_id = event.killer_pid
```

### 6.3 Event Type Mapping

| sc2reader Event | Handler | State Update |
|----------------|---------|--------------|
| UnitBornEvent | UnitEventHandler | Add unit lifecycle |
| UnitInitEvent | BuildingEventHandler | Add building lifecycle (constructing) |
| UnitDoneEvent | BuildingEventHandler | Mark building as completed |
| UnitDiedEvent | UnitEventHandler / BuildingEventHandler | Mark as dead/destroyed/cancelled |
| UpgradeCompleteEvent | UpgradeEventHandler | Add upgrade to player's set |
| PlayerStatsEvent | StatsEventHandler | Update player stats |
| ChatEvent | MessageEventHandler | Append to messages list |
| UnitPositionsEvent | (Optional) PositionHandler | Update unit positions |

---

## 7. Output Strategy

### 7.1 Output Format Selection

**Why Parquet?**
- **Columnar storage**: Efficient for analytics queries
- **Compression**: 5-10x smaller than JSON
- **Type safety**: Schema enforcement
- **Performance**: Fast reads with pyarrow/pandas
- **Industry standard**: Widely supported

**When to use JSON?**
- Debugging (human-readable)
- Small datasets (< 100 replays)
- Need to inspect structure

**When to use CSV?**
- Simple analysis in Excel
- Compatibility with legacy tools
- Single table output

### 7.2 Table Design

**Design Philosophy**: Denormalized for query performance, partitioned by replay_hash.

**Main Tables**:

1. **replay_metadata.parquet** - One row per replay
   - Contains all metadata fields
   - Small (few KB per replay)
   - Used for filtering/joining

2. **frame_states.parquet** - One row per frame per player
   - Contains all numeric stats (minerals, vespene, supply, etc.)
   - Largest table (~50% of total data)
   - Core data for DBN training

3. **unit_counts.parquet** - One row per (frame, player, unit_type)
   - Stores unit counts by type
   - Sparse representation (only non-zero counts)
   - ~25% of total data

4. **building_counts.parquet** - One row per (frame, player, building_type, state)
   - Stores building counts by type and state
   - Includes state column ("existing" or "constructing")
   - ~15% of total data

5. **upgrades.parquet** - One row per upgrade completion
   - Event-based (not frame-based)
   - Small table
   - ~5% of total data

6. **messages.parquet** - One row per chat message
   - Event-based
   - Often empty (no chat in bot games)
   - ~5% of total data

### 7.3 Schema Design

**Common Fields** (all tables):
- `replay_hash`: Links rows to specific replay (partition key)

**Temporal Fields**:
- `frame`: Frame number (int64)
- `game_time_seconds`: Real-time seconds (float64)

**Player Fields**:
- `player_id`: Player identifier (int32)

**Parquet Schema Example** (frame_states.parquet):
```
replay_hash: string (required)
frame: int64 (required)
game_time_seconds: float64 (required)
player_id: int32 (required)
minerals: int32 (required, min=0)
vespene: int32 (required, min=0)
minerals_collection_rate: float64 (required, min=0)
vespene_collection_rate: float64 (required, min=0)
supply_used: float64 (required, min=0)
supply_made: float64 (required, min=0)
workers_active: int32 (required, min=0)
army_value_minerals: int32 (required, min=0)
army_value_vespene: int32 (required, min=0)
tech_tier: int32 (required, min=1, max=3)
base_count: int32 (required, min=0)
... (additional fields)
```

### 7.4 Partitioning Strategy

**Option 1**: Single file per table (simpler)
```
frame_states.parquet  (contains all replays)
```

**Option 2**: Partitioned by replay_hash (better for large datasets)
```
frame_states/
  replay_hash=a3f2b9c8.../
    part-0.parquet
  replay_hash=d4e5f6a7.../
    part-0.parquet
```

**Recommendation**: Start with Option 1, migrate to Option 2 for >1000 replays.

---

## 8. Performance Architecture

### 8.1 Performance Bottlenecks

**Identified bottlenecks**:
1. Replay parsing (I/O bound)
2. Event processing (CPU bound)
3. State reconstruction (CPU bound)
4. Output writing (I/O bound)

### 8.2 Optimization Strategies

**1. Minimize Memory Allocations**
- Reuse objects where possible
- Use generators for large sequences
- Release replay objects after extraction

**2. Efficient State Queries**
- Cache unit type lookups
- Pre-compute building type sets
- Use dict comprehensions over loops

**3. Parallel Processing**
- Process replays independently (no shared state)
- Use multiprocessing.Pool for CPU parallelism
- Queue-based architecture for continuous processing

**4. I/O Optimization**
- Batch writes (don't write per replay)
- Use Parquet compression (snappy for speed)
- Stream processing for very large batches

### 8.3 Parallelization Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    MAIN PROCESS                          │
│                                                          │
│  ┌────────────────────────────────────────────────┐     │
│  │  ReplayQueue                                   │     │
│  │  [replay1.SC2Replay, replay2.SC2Replay, ...]   │     │
│  └────────────────────────────────────────────────┘     │
│                       │                                  │
│                       ├─────────┬─────────┬─────────┐   │
│                       ▼         ▼         ▼         ▼   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Worker 1   │  │  Worker 2   │  │  Worker N   │     │
│  │  Extract    │  │  Extract    │  │  Extract    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│         │                │                │             │
│         └────────────────┼────────────────┘             │
│                          ▼                               │
│  ┌────────────────────────────────────────────────┐     │
│  │  ResultQueue                                   │     │
│  │  [result1, result2, ...]                       │     │
│  └────────────────────────────────────────────────┘     │
│                          │                               │
│                          ▼                               │
│  ┌────────────────────────────────────────────────┐     │
│  │  Batch Writer (aggregates and writes)          │     │
│  └────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

### 8.4 Batch Processing Strategy

```python
def extract_batch_parallel(replay_paths: List[str], num_workers: int = 4) -> List[ExtractionResult]:
    """
    Extract replays in parallel using multiprocessing

    Strategy:
    1. Create worker pool
    2. Map extract_replay over replay_paths
    3. Collect results
    4. Aggregate and write in batches
    """
    with multiprocessing.Pool(num_workers) as pool:
        results = pool.map(extract_replay_worker, replay_paths)

    # Aggregate results
    all_metadata = [r.metadata for r in results if r.success]
    all_frame_states = [frame for r in results if r.success for frame in r.frame_states]

    # Write in batches (reduces I/O overhead)
    writer = ParquetWriter(output_dir)
    writer.write_batch(all_metadata, all_frame_states)

    return results
```

---

## 9. Error Handling Architecture

### 9.1 Error Levels

**Level 1: File-level errors** (fatal for that replay)
- Missing replay file
- Corrupt replay file
- Parse error

**Action**: Log error, skip replay, continue batch

**Level 2: Event-level errors** (warnings)
- Unknown event type
- Missing event attributes
- Invalid data

**Action**: Log warning, use defaults, continue processing

**Level 3: Data-level errors** (sanitizable)
- Negative values
- Supply violations
- Missing fields

**Action**: Log warning, sanitize data, continue

**Level 4: Output errors** (retryable)
- Write failure
- Disk full
- Permission error

**Action**: Retry with backoff, then fail

### 9.2 Error Handling Flow

```
extract_replay(path)
    │
    ├─> Try: Load replay
    │   └─> Except FileNotFoundError:
    │         Log error, return failed result
    │
    ├─> Try: Validate replay
    │   └─> If invalid and skip_invalid=true:
    │         Log warning, return failed result
    │
    ├─> Try: Process events
    │   └─> For each event:
    │         Try: Handle event
    │           └─> Except: Log warning, continue to next event
    │
    ├─> Try: Sample frames
    │   └─> Except: Log error, return failed result
    │
    ├─> Try: Format output
    │   └─> Except: Log error, return failed result
    │
    └─> Try: Write output
        └─> Except: Retry 3 times, then fail
```

### 9.3 Logging Strategy

**Log Levels**:
- **DEBUG**: Event processing details (verbose)
- **INFO**: Replay loaded, extraction progress
- **WARNING**: Validation failures, missing data
- **ERROR**: Parse errors, write failures

**Log Format**:
```
2026-01-23 10:15:32 INFO     [ReplayParser] Loading: data/raw/replay1.SC2Replay
2026-01-23 10:15:32 INFO     [ReplayParser] Loaded successfully (389 events, 3:52 duration)
2026-01-23 10:15:33 WARNING  [Validation] Supply constraint violated at frame 1250 (player 2)
2026-01-23 10:15:33 INFO     [FrameSampler] Sampled 47 frames
2026-01-23 10:15:33 INFO     [ParquetWriter] Wrote frame_states.parquet (1.2 MB)
```

---

## 10. Scalability Considerations

### 10.1 Horizontal Scalability

**Current Design**: Single-machine processing

**Extension to Distributed**:
- Replays are independent (no shared state)
- Easy to partition across machines
- Use distributed framework (Dask, Spark) if needed

**Dask Example**:
```python
import dask.bag as db

# Create bag of replay paths
replays = db.from_sequence(replay_paths, partition_size=100)

# Map extraction function
results = replays.map(extract_replay)

# Compute in parallel across cluster
extracted = results.compute()
```

### 10.2 Memory Scalability

**Current Memory Usage** (per replay):
- Replay object: ~1-5 MB
- Event storage: ~100-500 KB
- State tracker: ~500 KB - 2 MB
- **Total**: ~2-8 MB per replay

**For 10,000 replays**:
- Serial processing: ~5 MB peak (one replay at a time)
- 8 workers: ~40 MB peak (8 replays in memory)
- Batch aggregation: +100-500 MB for DataFrame

**Optimization for Very Large Datasets**:
- Stream processing (don't accumulate all results)
- Write incrementally (per-replay or small batches)
- Use generators instead of lists

### 10.3 Storage Scalability

**Output Size Estimates**:
- 1 replay (5-min game, 5-sec intervals): 50-100 KB (Parquet)
- 1,000 replays: 50-100 MB
- 10,000 replays: 500 MB - 1 GB
- 100,000 replays: 5-10 GB

**Parquet Compression Ratios**:
- Snappy: 3-5x smaller than uncompressed
- Gzip: 5-10x smaller (slower)
- None: Fast but large

**Recommendation**: Use Snappy for production (good balance)

---

## Appendix: Design Decisions

### A.1 Why sc2reader over s2protocol?

**sc2reader**:
- High-level API (easier to use)
- Automatic version handling
- Good documentation
- Community support

**s2protocol**:
- Official Blizzard library
- More control over raw data
- Lower-level (more complex)

**Decision**: Use sc2reader for productivity, fall back to s2protocol if needed.

### A.2 Why load_level=3 (tracker events only)?

- Bot replays fail at load_level=4 (unknown game events)
- Tracker events contain all required data
- Game events not needed for DBN training
- Faster parsing (skip game events)

**Decision**: Always use load_level=3 for consistency.

### A.3 Why 5-second sampling interval?

- Balances granularity vs. data volume
- Aligns with PlayerStatsEvent frequency
- Captures strategic decisions (buildings, upgrades)
- Sufficient for DBN temporal resolution

**Decision**: 5 seconds (112 frames) as default, configurable.

### A.4 Why Parquet over CSV/JSON?

**Parquet**:
- 5-10x smaller than JSON
- Type safety and schema enforcement
- Fast querying with pandas
- Industry standard

**Decision**: Parquet for production, JSON for debugging.

---

**END OF ARCHITECTURE DOCUMENT**
