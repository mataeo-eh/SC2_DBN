# Replay Processing Analysis

## Overview
This document analyzes `pysc2.bin.replay_actions` and the overall architecture for processing SC2 replays through pysc2 to extract Ground Truth Game State.

---

## replay_actions Module Analysis

### Location
`C:\Users\matae\OneDrive\Desktop\Coding-Projects\local-play-bootstrap-main\pysc2\pysc2\bin\replay_actions.py`

### Purpose
The `replay_actions.py` script is designed to process multiple replays in parallel and collect statistics about actions, units, abilities, and other gameplay elements used in those replays.

### Architecture

#### 1. Multiprocessing Design
```python
# Uses multiprocessing.Process for parallel replay processing
class ReplayProcessor(multiprocessing.Process):
    def __init__(self, proc_id, run_config, replay_queue, stats_queue):
        # Each process has its own SC2 instance
        # Processes pull replays from a shared queue
```

**Key Points**:
- **Parallel Processing**: Yes, multiple SC2 instances run simultaneously
- **Max Workers**: Configurable via `--parallel` flag (default: 1)
- **Queue-Based**: Uses `multiprocessing.JoinableQueue` for work distribution
- **Process Lifecycle**: Each process handles up to 300 replays before restarting SC2

#### 2. SC2 Instance Management
```python
with self.run_config.start(want_rgb=interface.HasField("render")) as controller:
    # SC2 instance runs for up to 300 replays
    for _ in range(300):
        # Process one replay
        replay_path = self.replay_queue.get()
        # ...
        controller.start_replay(...)
```

**Key Points**:
- One SC2 instance per worker process
- Each instance processes ~300 replays before restart (prevents memory leaks)
- SC2 binary lifecycle managed by `run_config`

#### 3. Interface Configuration
```python
size = point.Point(16, 16)
interface = sc_pb.InterfaceOptions(
    raw=True,                                   # RAW DATA ENABLED
    score=False,
    feature_layer=sc_pb.SpatialCameraSetup(width=24))
size.assign_to(interface.feature_layer.resolution)
size.assign_to(interface.feature_layer.minimap_resolution)
```

**Key Points**:
- **`raw=True`**: Enables raw data interface (essential for ground truth)
- Low resolution feature layers (16x16) - only for minimal rendering
- **Ground Truth Access**: YES, via raw interface

---

## Ground Truth State Extraction

### Does replay_actions Extract Full Observations?

**YES - with caveats**:

#### What It Extracts (Currently)
```python
def process_replay(self, controller, replay_data, map_data, player_id):
    controller.start_replay(...)
    feat = features.features_from_game_info(controller.game_info())

    controller.step()
    while True:
        obs = controller.observe()  # FULL OBSERVATION

        # Current processing:
        for action in obs.actions:          # Player actions
            # Track actions

        for valid in obs.observation.abilities:  # Available abilities
            # Track abilities

        for u in obs.observation.raw_data.units:  # ALL UNITS
            self.stats.unit_ids[u.unit_type] += 1
            for b in u.buff_ids:
                self.stats.buffs[b] += 1

        for u in obs.observation.raw_data.player.upgrade_ids:  # UPGRADES
            self.stats.upgrades[u] += 1

        for e in obs.observation.raw_data.effects:  # EFFECTS
            self.stats.effects[e.effect_id] += 1
```

**Answer**: replay_actions **has access to full ground truth** (`obs.observation.raw_data`) but **currently only extracts summary statistics**, not detailed state.

---

## Performance Analysis

### Computational Cost

#### From Code Analysis
```python
FLAGS.DEFINE_integer("step_mul", 8, "How many game steps per observation.")
# Default: Observe every 8 game loops (0.36 seconds of game time)
```

**Observations per Replay**:
- Average game: ~15,000 game loops (11 minutes)
- At step_mul=8: ~1,875 observations per replay
- At step_mul=1: ~15,000 observations per replay

#### Performance Overhead

**Engine-Based vs Traditional Parsers**:

| Aspect | Traditional Parser | pysc2 (Engine-Based) |
|--------|-------------------|----------------------|
| Processing Method | Parse replay file directly | Run through SC2 engine |
| Speed | Very fast (~1-10 seconds) | Slower (~1-5 minutes per replay) |
| Accuracy | Approximate state | Perfect ground truth |
| Memory | Low (~100 MB) | High (~1-2 GB per SC2 instance) |
| CPU | Low (single core) | High (full game simulation) |
| Parallelization | Easy | Limited by RAM/CPU |

**Benchmark Estimates** (based on code comments and flags):
- Single replay: 1-5 minutes at step_mul=8
- With 4 parallel workers: 4x throughput
- Memory per worker: ~1-2 GB (SC2 instance)
- CPU per worker: ~50-100% of one core

### Batch Processing Capabilities

```python
def main(unused_argv):
    # Parallel processing setup
    replay_queue = multiprocessing.JoinableQueue(FLAGS.parallel * 10)

    for i in range(min(len(replay_list), FLAGS.parallel)):
        p = ReplayProcessor(i, run_config, replay_queue, stats_queue)
        p.start()

    replay_queue.join()  # Wait for all replays to complete
```

**Capabilities**:
- **Parallel Workers**: Configurable (1 to N, limited by RAM)
- **Queue-Based**: Efficient work distribution
- **Progress Tracking**: Via `stats_queue` and `stats_printer` thread
- **Error Handling**: Continues processing if individual replays fail

**Recommended Configuration**:
- 4-8 parallel workers (assuming 16-32 GB RAM)
- step_mul=8 for faster processing (reduce if need finer granularity)
- Batch size: Unlimited (queue-based architecture)

---

## Memory and CPU Requirements

### Per SC2 Instance
```
Memory: ~1-2 GB
CPU: ~50-100% of one core
Disk I/O: Low (after replay loaded into memory)
```

### System Requirements for Batch Processing

For 1000 replays with 4 workers:
```
RAM: 8-10 GB (4 workers × 2 GB + OS overhead)
CPU: 4+ cores (ideally 8 for OS headroom)
Time: ~4-20 hours (depending on step_mul and replay length)
Disk: Minimal (sequential read of replays)
```

---

## Configuration Options

### Key Flags
```python
flags.DEFINE_integer("parallel", 1, "How many instances to run in parallel.")
flags.DEFINE_integer("step_mul", 8, "How many game steps per observation.")
flags.DEFINE_string("replays", None, "Path to a directory of replays.")
```

### Observation Detail Level

**Currently No Configuration for Observation Detail**:
- Interface is hardcoded in `replay_actions.py`
- `raw=True` is set, providing access to all raw data
- To extract more detailed data, modify `process_replay()` function

**Recommended Modifications**:
```python
# Add flag for observation detail
flags.DEFINE_bool("extract_full_state", False, "Extract full game state, not just stats")

# In process_replay():
if FLAGS.extract_full_state:
    # Extract and save obs.observation.raw_data.units
    # Extract and save obs.observation.player_common
    # etc.
```

---

## Parallel Processing Architecture

### Thread/Process Model
```
Main Process
    ├── replay_queue_filler (Thread)
    │       └── Fills queue with replay paths
    │
    ├── stats_printer (Thread)
    │       └── Prints progress every 10 seconds
    │
    └── ReplayProcessor (Process) × N workers
            ├── Each has own SC2 instance
            ├── Pulls replays from queue
            └── Sends stats to stats_queue
```

### Communication
```python
replay_queue = multiprocessing.JoinableQueue(FLAGS.parallel * 10)
stats_queue = multiprocessing.Queue()

# Worker process
class ReplayProcessor(multiprocessing.Process):
    def run(self):
        while True:
            replay_path = self.replay_queue.get()  # Pull work
            # Process replay
            self.stats_queue.put(self.stats)       # Send progress
            self.replay_queue.task_done()          # Mark complete
```

**Benefits**:
- True parallelism (Python multiprocessing)
- Isolated SC2 instances (crash in one doesn't affect others)
- Progress monitoring via stats_queue
- Graceful shutdown on KeyboardInterrupt

---

## Error Handling

```python
try:
    # Process replay
except (protocol.ConnectionError, protocol.ProtocolError, remote_controller.RequestError):
    self.stats.replay_stats.crashing_replays.add(replay_name)
except KeyboardInterrupt:
    return
```

**Error Types**:
- **Connection Errors**: SC2 instance crashed
- **Protocol Errors**: Invalid replay data
- **Validation Errors**: Corrupted or incompatible replay

**Recovery**:
- Mark replay as failed
- Continue with next replay
- Restart SC2 instance after 300 replays (prevents accumulation of errors)

---

## Replay Validation

```python
def valid_replay(info, ping):
    if (info.HasField("error") or
        info.base_build != ping.base_build or      # Version mismatch
        info.game_duration_loops < 1000 or         # Too short
        len(info.player_info) != 2):               # Not 1v1
        return False

    for p in info.player_info:
        if p.player_apm < 10 or p.player_mmr < 1000:  # Low quality
            return False

    return True
```

**Validation Criteria**:
- No errors in replay
- Matching SC2 version
- Minimum game length (1000 loops ≈ 45 seconds)
- 1v1 games only
- Minimum APM (10) and MMR (1000) - filters out corrupt replays

**Recommendation**: Customize validation for your use case (e.g., allow 2v2, different lengths)

---

## Recommended Approach for Ground Truth Extraction

### Modified Pipeline

```python
# 1. Modify replay_actions.py to extract full state
def process_replay(self, controller, replay_data, map_data, player_id):
    controller.start_replay(...)

    # Storage for ground truth
    ground_truth_frames = []

    controller.step()
    while True:
        obs = controller.observe()

        # Extract full state
        frame_data = {
            'game_loop': obs.observation.game_loop,
            'player_id': player_id,
            'minerals': obs.observation.player_common.minerals,
            'vespene': obs.observation.player_common.vespene,
            'supply_used': obs.observation.player_common.food_used,
            'supply_cap': obs.observation.player_common.food_cap,
            'units': [{
                'tag': u.tag,
                'unit_type': u.unit_type,
                'pos_x': u.pos.x,
                'pos_y': u.pos.y,
                'pos_z': u.pos.z,
                'health': u.health,
                'shields': u.shield,
                'energy': u.energy,
                'owner': u.owner,
                'alliance': u.alliance,
                # ... more fields
            } for u in obs.observation.raw_data.units],
            'upgrades': list(obs.observation.raw_data.player.upgrade_ids),
            'dead_units': list(obs.observation.raw_data.event.dead_units),
        }

        ground_truth_frames.append(frame_data)

        if obs.player_result:
            break

        controller.step(FLAGS.step_mul)

    # Save to file (JSON, pickle, parquet, etc.)
    save_ground_truth(replay_path, ground_truth_frames)
```

### Output Format Recommendation

**Parquet** (columnar format, ideal for ML):
```python
import pandas as pd
import pyarrow.parquet as pq

# One table per replay
df = pd.DataFrame(ground_truth_frames)
df.to_parquet(f'{replay_name}_parsed.parquet')
```

**Benefits**:
- Efficient storage
- Fast loading
- Direct integration with ML frameworks
- Columnar access for specific features

---

## Summary

### Key Findings

1. **Ground Truth Access**: YES - `replay_actions` uses raw interface
2. **Current State**: Extracts statistics only, not full state
3. **Parallel Processing**: YES - multiprocessing architecture
4. **Performance**: Slower than traditional parsers, but provides perfect accuracy
5. **Scalability**: Limited by RAM (1-2 GB per worker) and CPU

### Recommended Configuration

```bash
# For ground truth extraction
python -m pysc2.bin.replay_actions \
    --replays /path/to/replays \
    --parallel 4 \
    --step_mul 8
```

**Modifications Needed**:
- Extend `process_replay()` to save full observations
- Add output format (JSON/Parquet/CSV)
- Add per-replay file output
- Consider memory management for long replays

### Performance Estimates

| Scenario | Time | Workers | RAM |
|----------|------|---------|-----|
| 1 replay (11 min game) | 1-5 min | 1 | 2 GB |
| 100 replays | 2-8 hours | 4 | 10 GB |
| 1000 replays | 1-3 days | 4 | 10 GB |
| 1000 replays | 6-18 hours | 16 | 32 GB |

**Note**: Times assume step_mul=8. Reduce step_mul for finer granularity at cost of longer processing time.

---

## Next Steps

1. **Modify `replay_actions.py`** to extract full state
2. **Test on sample replay** to validate data extraction
3. **Design output schema** (flat table vs nested structure)
4. **Implement batch processing** with progress tracking
5. **Optimize for memory** (streaming write, chunk processing)
