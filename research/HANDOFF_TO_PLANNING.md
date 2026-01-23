# Research Phase Handoff to Planning
## SC2 Replay Data Extraction - Ready for Implementation Planning

**Date:** 2026-01-23
**Research Status:** ✅ COMPLETE - All Objectives Met

---

## Executive Summary

Research successfully confirmed that **all required data points** for DBN training can be extracted from SC2 replay files using the `sc2reader` Python library. No blockers identified. Ready to proceed to planning phase.

---

## Key Deliverables

### 1. Comprehensive Research Document
- **File:** `SC2_EXTRACTION_RESEARCH.md` (1,510 lines)
- **Contents:** Complete technical analysis of SC2 replay parsing
- **Sections:** Library comparison, data availability, technical architecture, performance, code examples

### 2. Quick Reference Guide
- **File:** `QUICK_REFERENCE.md`
- **Purpose:** Fast lookup for common tasks and decisions
- **Use:** Day-to-day development reference

### 3. Working Code Example
- **File:** `extraction_example.py` (350 lines)
- **Purpose:** Demonstrates recommended extraction approach
- **Features:**
  - Single replay extraction
  - Batch processing
  - Frame-by-frame state reconstruction
  - JSON output format

---

## Critical Findings

### ✅ Technical Feasibility: CONFIRMED

**All required data is extractable:**

| Data Category | Availability | Quality |
|--------------|--------------|---------|
| Unit creation/death | ✅ Complete | Excellent |
| Building lifecycle | ✅ Complete | Excellent |
| Unit positions | ✅ Periodic | Good (snapshots) |
| Upgrades | ✅ Completion only | Adequate |
| Messages | ✅ Complete | Excellent |
| Player stats | ✅ Periodic | Excellent |
| Temporal precision | ✅ Frame-level | Excellent |

### 📊 Performance: EXCELLENT

**Benchmarks from real replay:**
- Parse speed: 164,671 events/second
- Load time: 0.04 seconds per replay
- Memory: ~1 MB per replay (estimated)
- Scalability: Linear (parallelizable)

**Projected throughput:**
- 10,000 replays: ~7 minutes sequential
- With 8 cores: ~1 minute parallel

### ⚠️ Known Limitations

1. **AI Arena replay compatibility**
   - Issue: Some bot replays fail to load (cache_handles bug)
   - Impact: May need to use human/ladder replays
   - Workaround: Patch sc2reader OR filter failures

2. **Upgrade start times**
   - Issue: Only completion tracked, not start
   - Impact: Can't measure research time
   - Workaround: Acceptable for DBN (completion is key data point)

3. **Sparse position data**
   - Issue: Position snapshots are periodic (~10 per game)
   - Impact: Can't track precise unit movements
   - Workaround: Sufficient for base-level spatial features

**None of these limitations block DBN training.**

---

## Recommended Technical Decisions

### Library Choice
**Selected:** `sc2reader` v1.8.0

**Alternatives considered:**
- ❌ s2protocol (too low-level)
- ❌ pysc2 (version-dependent, RL-focused)
- ❌ zephyrus-sc2-parser (broken on Python 3.14+)

**Justification:** sc2reader provides perfect balance of ease-of-use, performance, and data completeness.

### Temporal Resolution
**Selected:** 5-second intervals (80 frames @ Faster speed)

**Rationale:**
- Captures strategic decisions (buildings, upgrades)
- Balances granularity vs. data volume
- Aligns with PlayerStatsEvent frequency
- Recommended by domain analysis

### Output Format
**Selected:** Parquet (production), JSON (development)

**Rationale:**
- Parquet: Columnar, compressed, fast for ML pipelines
- JSON: Human-readable, flexible, good for debugging
- Both: Easy to convert between formats

### Validation Criteria
**Required checks:**
- Minimum game length: 1,000 frames (~60 seconds)
- SC2 version: >= 2.0.8 (tracker events available)
- Parse success: No exceptions during load
- Winner present: Completed game (not disconnect)

---

## Data Extraction Specifications

### Event Types to Track

**Primary (tracker events):**
```python
REQUIRED_EVENTS = [
    'UnitBornEvent',      # Instant units
    'UnitInitEvent',      # Construction started
    'UnitDoneEvent',      # Construction completed
    'UnitDiedEvent',      # Unit/building destroyed
    'PlayerStatsEvent',   # Resource/economy snapshots
    'UpgradeCompleteEvent',  # Upgrade finished
    'UnitPositionsEvent', # Position snapshots (optional)
    'ChatEvent'           # Messages (optional)
]
```

### Unit Categorization

**Buildings vs. Units:**
- Differentiate via `unit_type_name` keyword matching
- See Appendix B in research doc for complete list
- Example: "Nexus", "Gateway", "Pylon" = buildings

**Filtering:**
- Ignore map elements (minerals, geysers, critters)
- See `IGNORE_UNITS` set in `extraction_example.py`

### State Reconstruction Logic

**Building states:**
```
UnitInitEvent → "constructing"
UnitDoneEvent → "completed"
UnitDiedEvent (after Done) → "destroyed"
UnitDiedEvent (before Done) → "cancelled"
```

**Unit tracking:**
- Track by `unit_id` across events
- Maintain lifecycle map: `unit_id -> {born, done, died, type, player}`
- At each frame, count units where `done_frame <= current_frame < died_frame`

---

## Proposed Feature Set for DBN

### Core Features (Per Player, Per Frame)

**Unit Composition (20-30 features):**
- Count by type: Probe, Zealot, Stalker, etc.
- Total units: sum of all unit counts
- Total army value: minerals + gas invested in army
- Worker count: special case (from PlayerStatsEvent)

**Building/Tech (15-20 features):**
- Count by type: Nexus, Gateway, CyberneticsCore, etc.
- Tech level: has_Lair, has_Hive, etc. (boolean)
- Production capacity: total production buildings

**Resources (5-10 features):**
- Current minerals
- Current vespene (gas)
- Supply used / supply made
- Resource collection rate (from PlayerStatsEvent)
- Total resources spent (cumulative)

**Upgrades (5-10 features):**
- Completed upgrades (count or boolean flags)
- Example: has_Stim, has_Charge, attack_level_1, etc.

**Temporal (2-3 features):**
- Game time (seconds elapsed)
- Frame number

**Total: ~50-75 features per player per frame**
**For 2-player game: ~100-150 features per frame**

### Optional Advanced Features

**Spatial (if needed later):**
- Base count (cluster buildings by location)
- Expansion timing (when new bases started)

**Strategic (derived):**
- Army composition archetype (bio, mech, air, etc.)
- Tech path indicator (rushing, teching, expanding)
- Resource advantage ratio (player1 / player2)

---

## Implementation Guidance

### Recommended Pipeline Architecture

```
┌─────────────────────────────────────────┐
│ 1. BATCH LOADER                         │
│    - List all .SC2Replay files          │
│    - Filter by validation criteria      │
│    - Parallel worker pool               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 2. REPLAY PARSER (per replay)           │
│    - sc2reader.load_replay(level=4)     │
│    - Extract unit lifecycles            │
│    - Build event index by frame         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 3. STATE RECONSTRUCTOR                  │
│    - For each interval frame            │
│    - Apply events up to frame           │
│    - Count units/buildings alive        │
│    - Retrieve latest PlayerStatsEvent   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 4. FEATURE EXTRACTOR                    │
│    - Convert state to feature vector    │
│    - One row per frame interval         │
│    - Columns: all features              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 5. OUTPUT WRITER                        │
│    - Save to Parquet/JSON               │
│    - One file per replay OR             │
│    - Batched into large files           │
└─────────────────────────────────────────┘
```

### Error Handling Strategy

**Three-tier handling:**

1. **Replay-level errors:**
   - Catch parse failures
   - Log error with replay path
   - Skip replay, continue batch
   - Report at end

2. **Event-level errors:**
   - Handle missing attributes gracefully
   - Use defaults (0, None, empty list)
   - Log warnings for investigation

3. **Validation errors:**
   - Check before processing (fast fail)
   - Examples: too short, wrong version
   - Skip silently or log to filter list

### Parallelization

**Approach:**
- Replays are independent → embarrassingly parallel
- Use `multiprocessing.Pool` or `concurrent.futures`
- Workers = CPU cores (8-16 typical)
- Combine results after processing

**Example:**
```python
from concurrent.futures import ProcessPoolExecutor

def extract_one_replay(replay_path):
    return extract_replay_features(replay_path)

with ProcessPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(extract_one_replay, replay_paths))
```

---

## Data Volume Estimates

### Per Replay

**Assumptions:**
- Average game length: 250 seconds (~4 minutes)
- Sampling interval: 5 seconds
- Snapshots per game: 250/5 = 50
- Features per snapshot: 150 (2 players × 75 features)

**Storage:**
- JSON: ~50 KB per replay
- Parquet: ~10 KB per replay (compressed)

### Dataset Scale

| Replays | JSON Size | Parquet Size | Parse Time (8 cores) |
|---------|-----------|--------------|----------------------|
| 100 | 5 MB | 1 MB | ~1 second |
| 1,000 | 50 MB | 10 MB | ~5 seconds |
| 10,000 | 500 MB | 100 MB | ~1 minute |
| 100,000 | 5 GB | 1 GB | ~10 minutes |

**Recommendation:** Start with 1,000-10,000 replays for initial DBN training, scale up as needed.

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| AI Arena replays incompatible | Medium | High | Use human/ladder replays instead |
| Performance bottleneck | Low | Low | Parallelize, optimize hot paths |
| Missing data in old replays | Low | Low | Filter to version >= 2.0.8 |
| Memory issues (large batches) | Medium | Low | Stream processing, batch output |
| Feature engineering complexity | Medium | Medium | Start simple, iterate |

**Overall risk level: LOW** - No critical blockers identified.

---

## Success Criteria (for Planning Phase)

Planning phase should produce:

1. **Detailed implementation plan**
   - Task breakdown (weeks/sprints)
   - Milestones and deliverables
   - Resource requirements

2. **Feature specification**
   - Final list of 100-150 features
   - Feature engineering logic
   - Validation criteria

3. **Pipeline architecture**
   - Component design
   - Data flow diagram
   - Error handling strategy

4. **Testing strategy**
   - Unit tests (per component)
   - Integration tests (end-to-end)
   - Validation tests (data quality)

5. **Performance targets**
   - Throughput (replays/second)
   - Latency (time to process batch)
   - Memory (max usage per worker)

---

## Recommended Next Actions

### Immediate (Planning Phase)

1. **Define exact feature set** (100-150 features)
   - Consult with DBN requirements
   - Prioritize by importance
   - Document feature engineering logic

2. **Design data schema**
   - Parquet table structure
   - Column names and types
   - Partitioning strategy (by race, map, date, etc.)

3. **Create implementation plan**
   - Break into development tasks
   - Estimate time per task
   - Identify dependencies

4. **Set up development environment**
   - Install sc2reader
   - Download sample replays (100-1000)
   - Test extraction_example.py

### Short-term (Implementation Phase)

1. **Build core pipeline** (Week 1-2)
   - Implement batch loader
   - Implement feature extractor
   - Add error handling

2. **Test on sample data** (Week 2-3)
   - Process 1,000 replays
   - Validate output
   - Measure performance

3. **Scale and optimize** (Week 3-4)
   - Parallelize extraction
   - Optimize bottlenecks
   - Process full dataset (10,000+)

4. **Deliver to DBN training** (Week 4)
   - Clean, validated dataset
   - Feature documentation
   - Data quality report

---

## Questions for Planning Phase

**To be answered during planning:**

1. What is the target dataset size? (1K, 10K, 100K replays?)
2. What are the specific DBN architecture requirements?
3. Should we include spatial features? (base locations, expansion timing)
4. What is the priority: speed or comprehensiveness?
5. Do we need real-time extraction or batch processing?
6. Where will the data be stored? (local, cloud, database)
7. What replay sources are available? (AI Arena, ladder, tournaments)

---

## File Manifest

Research phase deliverables located in `research/` directory:

```
research/
├── SC2_EXTRACTION_RESEARCH.md   (1,510 lines) - Complete technical analysis
├── QUICK_REFERENCE.md           (120 lines)   - Quick lookup guide
├── extraction_example.py        (350 lines)   - Working code example
└── HANDOFF_TO_PLANNING.md       (THIS FILE)   - Planning phase handoff
```

**Total documentation:** ~2,000 lines
**Code examples:** ~350 lines
**Research time:** ~2 hours

---

## Conclusion

Research phase successfully completed all objectives:

✅ Identified best library (sc2reader)
✅ Confirmed data availability (all required points extractable)
✅ Measured performance (excellent: 164k events/sec)
✅ Documented technical architecture
✅ Provided working code examples
✅ No blockers identified

**Status: READY FOR PLANNING PHASE**

The planning phase can proceed with confidence that the technical foundation is solid and all required data is accessible. Implementation should be straightforward following the patterns demonstrated in `extraction_example.py`.

---

**Handoff Date:** 2026-01-23
**Next Phase Owner:** Planning Lead
**Contact for Questions:** Research Phase Team
