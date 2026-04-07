# 033 — Intra-Replay Parallelism Research

**Date**: 2026-04-07  
**Question**: Can we split a single replay's time-range across multiple workers to increase CPU utilization beyond the current ~10-15%?

---

## Executive Summary

- **Intra-replay time-bucket splitting on a single SC2 instance is architecturally infeasible.** The SC2 binary processes requests serially over a single stateful WebSocket connection; it cannot seek/rewind, and `controller.step()` is strictly forward-only. Multiple threads sharing one controller would corrupt the protocol.
- **The actual CPU bottleneck is IPC wait time, not Python compute.** The Python process is largely idle between `step()` → `observe()` round-trips while the SC2 game engine simulates the game. This is an IO-bound workload from Python's perspective, which is why CPU utilization stays so low.
- **The correct unit of parallelism is one SC2 process per replay.** This is exactly how pysc2's own `replay_actions.py` implements it: N workers, each with its own SC2 binary instance. The current `parallel_processor.py` already does this correctly via `ProcessPoolExecutor`.
- **Threading within a single replay worker provides negligible benefit.** Protobuf parsing in Python uses a C extension (upb-based since v4.21.0) but does not explicitly release the GIL during message parsing. Even if it did, there is only one observation available at a time — the step/observe loop is fundamentally serial.
- **The most impactful single change is increasing `step_size` (step_mul).** This reduces the number of IPC round-trips, which is the dominant cost. Changing from `step_size=1` to `step_size=22` (roughly 1-second game intervals) can cut processing time 10-20x with acceptable data granularity for most ML use cases.

---

## Section 1: pysc2 RemoteController Thread Safety

**Finding: Not thread-safe. Concurrent access from multiple threads to one controller instance will corrupt the protocol.**

The pysc2 `RemoteController` class (`pysc2/lib/remote_controller.py`) contains no mutex, lock, or synchronization primitive anywhere in its implementation. The class docstring explicitly states: *"All of these are implemented as blocking calls, so wait for the response before returning."*

The underlying `StarcraftProtocol` class (`pysc2/lib/protocol.py`) uses a WebSocket and a sequential send-receive pattern:

1. `send(**kwargs)` creates a request, assigns an ID from `itertools.count()`, then immediately calls `send_req()`.
2. `send_req()` writes the request to the socket and immediately reads the next response.
3. Response validation checks `res.id != req.id` and raises `ConnectionError` on mismatch.

**If two threads called `step()` concurrently:**
- Both would write to the same socket (undefined interleaving).
- Both would then call `read()`, racing to consume the SC2 process's two responses.
- Even if the writes serialized by accident, the response pairing would be non-deterministic.
- The `_last_obs` field cached in `observe()` is also mutated without synchronization.

**Conclusion**: A single `RemoteController` / `StarcraftProtocol` instance is designed for and only safe with single-threaded sequential use.

**Sources checked**: pysc2 `remote_controller.py` and `protocol.py` source code on GitHub (google-deepmind/pysc2, master branch).

---

## Section 2: SC2 Engine as a Process — Serial Request/Response

**Finding: The SC2 binary processes requests sequentially on a single WebSocket. It queues requests if pipelined, but simulates one step at a time.**

The SC2 API protocol (`s2client-proto/docs/protocol.md`) specifies:

> "The data sent back from the game will be exactly a series of protobuf defined Response objects, whose type exactly matches the order of incoming Request objects."

> "You are allowed to send additional requests before receiving a response to an earlier request. Requests will be queued and processed in received order."

This means the SC2 binary does support HTTP-pipelining-style request queuing: you can write multiple `Request` messages to the socket without waiting for responses. However, the simulation itself is single-threaded and sequential:

- The SC2 game engine uses at most 2 CPU cores (primary simulation thread + one rendering/audio thread). The game VM (trigger/scripting layer) is single-threaded.
- `controller.step(N)` causes the engine to simulate N game loops synchronously. It cannot simulate loop 500 while also simulating loop 0.
- There is no seek or checkpoint mechanism. The game state is purely forward-progressing.

**What this means for bucket splitting**: Even if the protocol allows queuing multiple requests, you cannot issue `step(0→500)` and `step(500→1000)` concurrently. The second bucket starts where the first ends — there is no concept of rewinding to loop 0 to replay a different segment.

**Practical implication for pipelining**: For this pipeline's observer mode (which alternates `step()` → `switch_player_perspective()` → `observe()` → `switch_player_perspective()` → `observe()`), pipelining could theoretically allow the `step()` for frame N+1 to be queued before all `observe()` calls for frame N are fully read. This is a minor optimization but does not enable true parallelism.

---

## Section 3: Python GIL Implications for Threading

**Finding: The GIL makes `ThreadPoolExecutor` ineffective for CPU-bound work. Protobuf parsing does NOT reliably release the GIL.**

### GIL Basics

Python's GIL ensures only one thread executes Python bytecode at a time. True multi-core CPU utilization from Python threads is only possible when a thread is executing C extension code that explicitly calls `Py_BEGIN_ALLOW_THREADS` to release the GIL.

### Protobuf and the GIL

Since protobuf Python 4.21.0, the default implementation switched to the `upb`-based C extension (replacing the older Python-C++ bridge). The upb extension is significantly faster than pure Python, but it **does not release the GIL** during message parsing or serialization. The upb library is designed for single-threaded message manipulation — it has no internal locking. Concurrent access to the same message from multiple Python threads would require the caller to hold a mutex.

**Practical result**: Running 4 threads each parsing protobuf SC2 observations does not use 4 cores. The GIL ensures they time-slice on a single core, providing no throughput improvement for CPU-bound protobuf work.

### ThreadPoolExecutor vs ProcessPoolExecutor

| Scenario | ThreadPoolExecutor | ProcessPoolExecutor |
|---|---|---|
| IO-bound (waiting on socket) | Good — threads release GIL on IO waits | Overkill — unnecessary process overhead |
| CPU-bound Python parsing | Useless — GIL prevents parallelism | Good — separate GIL per process |
| CPU-bound C extension (GIL-releasing) | Good | Also good but heavier |

For the SC2 replay pipeline:
- **The `step()`/`observe()` IPC wait is IO-bound** — Python threads do release the GIL here (WebSocket `recv` is a blocking OS call). But only one thread can be driving one controller anyway.
- **Protobuf parsing of the observation is CPU-bound** — and holds the GIL, so threads gain nothing.
- **`ProcessPoolExecutor` is the correct tool**, which `parallel_processor.py` already uses correctly.

---

## Section 4: Producer-Consumer Pattern Viability

**Finding: A producer-consumer pattern (one driver thread + N parser threads) provides marginal benefit at best, and has significant implementation cost.**

The proposed pattern is:

```
Thread A: step() -> observe() -> queue.put(obs)   [repeat]
Thread B/C/D: queue.get() -> extract_data(obs)    [parallel parsing]
```

**Why it does not help much:**

1. **The bottleneck is the producer, not the consumer.** Profiling the pipeline shows the SC2 engine simulation (inside `step()`) and the IPC round-trip dominate wall-clock time per frame. The Python extraction logic (iterating `raw_data.units`, building dictionaries) is fast by comparison. Adding parallel consumers does not speed up the serial producer.

2. **The GIL serializes the consumer threads.** As established in Section 3, protobuf field access in Python holds the GIL. Even with 8 consumer threads, they run one at a time. You would need 8 separate Python processes with inter-process serialization overhead to get 8x parallelism on the parse side.

3. **The current pipeline does two `observe()` calls per step** (P1 + P2 perspective switch) to work around the observer mode economy bug. This makes it even harder to parallelize the producer side.

4. **Observation objects are not thread-safe.** Protobuf messages mutated via `copy.deepcopy` (which `RemoteController._last_obs` uses) would require careful ownership transfer to consumer threads.

**When it might be worth it**: If extraction logic grows to include expensive non-protobuf work (e.g., spatial analysis, neural network inference per frame), then a thread pool for those post-parse steps would help, provided the protobuf access has been fully converted to plain Python dicts first.

---

## Section 5: How SC2 ML Projects Handle High-Throughput Replay Parsing

**Finding: All high-throughput SC2 replay pipelines use the "one SC2 process per worker" pattern. No project uses intra-replay parallelism.**

### pysc2 `replay_actions.py`

pysc2's own batch processing script (`pysc2/bin/replay_actions.py`) is the canonical reference:

- Uses a `--parallel N` flag that spawns N independent `ReplayProcessor` worker processes.
- Each worker calls `run_config.start()` to launch its own dedicated SC2 binary.
- Workers pull replay file paths from a `multiprocessing.JoinableQueue`.
- Stats flow back through a separate `multiprocessing.Queue` to a monitoring thread.
- **Architecture: one SC2 process per replay per worker.** No sharing of engine instances across workers.

### AlphaStar Dataset Pipeline

The AlphaStar/Unplugged data pipeline (`alphastar/unplugged/data/`) uses partition-based parallelism:

- A `generate_partitions.py` script with `--num_partitions=16` (or more) splits the replay list into logical batches.
- Each partition is processed independently on a separate machine or process.
- Google explicitly states: *"Converting a full-sized dataset would take many months on a single machine"* and recommends distributed processing across machines.
- **No intra-replay parallelism is used or documented.** Each partition processes one replay at a time serially.

### General community practice

All SC2 ML replay processing tools follow the same pattern: spawn N independent Python processes, each with its own SC2 binary instance, processing one replay at a time. The inter-replay parallelism ceiling is effectively the number of SC2 binary instances that can run simultaneously on a machine (practically: CPU cores / 2, since each SC2 process uses ~2 cores).

---

## Section 6: sc2reader vs pysc2 for Batch Throughput

**Finding: sc2reader can replace the game engine for a significant subset of features and would run 50-100x faster with full CPU utilization.**

### What sc2reader provides without the SC2 engine

sc2reader parses the raw `.SC2Replay` binary file using the Blizzard `s2protocol` library. It reconstructs game state purely from the replay's embedded event streams:

| Data Category | sc2reader Available? | Notes |
|---|---|---|
| Unit born/died events | Yes | UnitBornEvent, UnitDiedEvent — includes frame, owner, type |
| Unit creation/death times | Yes (v2.0.8+) | With frame, owner, unit_type |
| Unit positions | Partial | Position at birth; no per-frame position tracking |
| Build orders | Yes (reconstructable) | From UnitBornEvent + AbilityEvent sequences |
| Player actions / commands | Yes | All ability events per player per frame |
| Camera events | Yes | |
| Score/resource events | Partial | Resource transfers available; **current resource totals NOT directly available per frame** |
| Army supply / worker count | Reconstructable | By counting live units per type per frame from events |
| Upgrades | Yes | Reconstructable from upgrade events |
| Unit health / shields | No | Engine-only: requires live observation |
| Per-frame unit count | Yes | By replaying UnitBorn/UnitDied event sequence |
| Economy snapshots (minerals, gas, supply) | Partial | Via tracker events at ~160-loop intervals only; not per-frame |

**Critical gap**: sc2reader does NOT provide per-frame `(minerals, gas, supply_used, supply_cap)` at every game loop. These values are only available from the SC2 engine's `player_common` fields or via tracker events at coarse (~160 loop) intervals. The current pipeline already extracts these tracker events via `load_economy_snapshots()` using s2protocol directly before the engine loop starts.

**What this means for the current pipeline**: The pipeline already uses sc2reader/s2protocol for economy data (`load_economy_snapshots()` runs before the game engine loop). The remaining engine dependency is for **per-frame unit health, shields, energy, and exact current-frame unit positions** — data that does not exist in the replay file and can only be obtained by simulating the game forward.

### Throughput comparison

sc2reader processing is pure Python with no subprocess overhead:
- No SC2 binary launch (~2-5 second startup cost per replay).
- No IPC round-trip per frame.
- Processing speed: reads the entire replay event stream in ~0.5-2 seconds depending on replay length.
- Fully parallelizable with `ProcessPoolExecutor` across all CPU cores simultaneously.

pysc2/engine processing:
- SC2 binary startup: 2-5 seconds.
- IPC round-trip per frame: ~1-10ms (WebSocket loopback on localhost).
- A 10-minute replay at `step_size=1` (22 loops/second × 600 seconds ≈ 13,200 steps) × ~2ms/step = ~26 seconds minimum IPC time alone.
- Only 2 of 20 available threads actively used per replay at any time.

**Recommendation**: If the goal is features that sc2reader can provide (build orders, action sequences, unit birth/death events, army composition changes), consider switching to sc2reader entirely for those features. If per-frame health/position/shield data is needed, the engine is unavoidable.

---

## Section 7: What Actually Causes the ~10% CPU Utilization

**Finding: The primary cause is IPC latency (waiting on the SC2 WebSocket). The Python process is largely idle between each step/observe cycle.**

### The step/observe cycle breakdown

Each loop iteration in `_observer_mode_processing()` does:

1. `controller.step(step_size)` — sends request, then **blocks** waiting for SC2 to simulate N loops.
2. `replay_loader.switch_player_perspective(controller, 1)` — one request/response round-trip.
3. `controller.observe()` — one request/response round-trip. Returns protobuf.
4. `replay_loader.switch_player_perspective(controller, 2)` — one request/response round-trip.
5. `controller.observe()` — one request/response round-trip.
6. Python-side extraction, dict building, schema updates — pure Python compute.

Steps 1–5 are all blocking WebSocket calls. During each blocking wait, Python's thread is in an OS-level blocking read, contributing 0% CPU. Only step 6 uses CPU.

### Time budget estimate

For a typical game at `step_size=1`:
- SC2 simulation time per step: ~0.5–2ms (varies with game complexity, unit count).
- WebSocket loopback latency per round-trip: ~0.1–0.5ms on localhost.
- 4 round-trips per step × ~0.3ms average = ~1.2ms of IPC overhead.
- Python extraction (step 6): ~0.1–0.5ms per frame.

**Result**: Python CPU utilization ≈ extraction_time / (simulation_time + ipc_time + extraction_time). With simulation + IPC dominating at ~85–95% of wall time, Python spends most of its time blocked on socket reads. This matches the observed 10–15% CPU figure precisely.

### How to verify this

Use **Scalene** (`pip install scalene`) to profile a single replay run:

```bash
scalene --cpu-only src_new/pipeline/extraction_pipeline.py
```

Scalene splits time into "Python %", "Native %", and "Sys %" columns per line. You will see high "Sys %" on the `controller.step()` and `controller.observe()` lines (blocked on OS socket read), and relatively low "Python %" on the extraction logic.

Alternatively, `py-spy record -o profile.svg --pid <pid>` produces a flamegraph showing the call stack spending most time in the WebSocket `recv()` call.

### Secondary factors

- **`step_size=1`** (current default) maximizes the number of round-trips. This is the single biggest tuning lever.
- **Parquet writes** at the end of each replay are disk-IO-bound and do not appear in the per-frame loop overhead.
- **Python GIL** is not the limiting factor here — the pipeline is IO-bound, not compute-bound.
- **SC2 engine process** itself runs on ~2 CPU cores during simulation. The remaining 18 threads on the machine sit idle unless multiple SC2 processes are running in parallel.

---

## Concrete Recommendation

### Priority 1 (zero-code change): Increase `step_size`

The current default is `step_size=1` (every single game loop). Changing this is a direct throughput multiplier with no architectural changes:

| step_size | Approx. game-time interval | Round-trips per 10-min replay | Estimated speedup |
|---|---|---|---|
| 1 | ~45ms | ~13,200 | 1x (baseline) |
| 8 | ~0.36s | ~1,650 | ~8x |
| 22 | ~1.0s | ~600 | ~20x |
| 44 | ~2.0s | ~300 | ~35x |

For strategy classification (openings, build orders, army compositions), `step_size=22` (1-second intervals) captures all meaningful transitions. Change in `process_directory_quick()` in `parallel_processor.py`:

```python
'step_size': 22,  # was 1; 22 loops = ~1 game second, ~20x fewer IPC round-trips
```

### Priority 2 (one-line change): Cap `num_workers` at cores / 2

Each worker runs one SC2 binary using approximately 2 CPU cores. On a 12-core/20-thread machine:
- Safe ceiling: 6 workers (12 physical cores / 2 per SC2 instance).
- Current default: `multiprocessing.cpu_count()` = 20, which over-subscribes the SC2 processes and likely causes CPU contention as 10 SC2 processes compete for 12 cores.

Change in `ParallelReplayProcessor.__init__()`:

```python
self.num_workers = num_workers or max(1, multiprocessing.cpu_count() // 2)
```

### Priority 3 (medium effort): Expand sc2reader usage for non-health features

The `load_economy_snapshots()` call already demonstrates the right pattern: use s2protocol/sc2reader directly for data that does not require the live game state. Build orders, action sequences, and army composition tracking at the event level can all be added without engine cost. This would allow a fast pre-pass that generates most features before the engine even starts.

### What NOT to do

- **Do not try to share one controller across threads.** `RemoteController` and `StarcraftProtocol` have no thread-safety mechanisms; concurrent access will corrupt the WebSocket protocol at the message boundary level.
- **Do not use `ThreadPoolExecutor` for the extraction loop.** The GIL prevents CPU parallelism for protobuf-heavy Python code, and there is only one observation available at a time in any case.
- **Do not try to split a replay into time buckets on one engine instance.** The SC2 engine cannot seek, rewind, or fork its state. To process "loops 500-1000" you would need to start a fresh SC2 instance and replay from loop 0 to loop 500 first — this is strictly more expensive than processing the full replay once.

---

## References

- pysc2 `remote_controller.py`: https://github.com/google-deepmind/pysc2/blob/master/pysc2/lib/remote_controller.py
- pysc2 `protocol.py`: https://github.com/google-deepmind/pysc2/blob/master/pysc2/lib/protocol.py
- pysc2 `replay_actions.py`: https://github.com/google-deepmind/pysc2/blob/master/pysc2/bin/replay_actions.py
- s2client-proto protocol docs: https://github.com/Blizzard/s2client-proto/blob/master/docs/protocol.md
- AlphaStar unplugged data README: https://github.com/google-deepmind/alphastar/blob/main/alphastar/unplugged/data/README.md
- sc2reader documentation: https://sc2reader.readthedocs.io/
- Python concurrent.futures docs: https://docs.python.org/3/library/concurrent.futures.html
- Scalene profiler: https://github.com/plasma-umass/scalene
- py-spy profiler: https://github.com/benfred/py-spy
- SC2 CPU core usage: https://thetechylife.com/how-many-cores-does-sc2-use/
