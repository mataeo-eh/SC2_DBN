# SC2 Replay Extraction System - Planning Documents

**Project:** StarCraft 2 Frame-by-Frame Replay Data Extraction for DBN Training
**Status:** Planning Complete - Ready for Implementation
**Date:** 2026-01-23

---

## Overview

This directory contains comprehensive planning documentation for building an SC2 replay data extraction system. The system will extract frame-by-frame game state information from StarCraft 2 replay files to train Dynamic Bayesian Networks (DBNs) for strategy prediction.

---

## Planning Documents

### 1. SC2_EXTRACTION_PLAN.md (73 KB)
**Main implementation plan with complete specifications**

**Contents:**
- Executive Summary
- Architecture Overview
- Data Schema Specifications (all data models)
- Module Specifications (all source files)
- Processing Algorithms (pseudocode)
- Implementation Roadmap (6-week plan)
- Configuration & Usage
- Testing Strategy
- Example Outputs
- Performance Considerations
- Error Handling & Edge Cases
- Future Enhancements

**Start here** for a complete understanding of the project.

---

### 2. data_schema.json (19 KB)
**Complete JSON schema for all data structures**

**Defines:**
- ReplayMetadata (replay-level information)
- PlayerInfo (player details)
- FrameState (complete game state at a frame)
- PlayerFrameState (per-player state)
- UnitEvent, BuildingEvent, UpgradeEvent, MessageEvent
- Output schema with validation rules

**Use for:**
- Schema validation during development
- API contract documentation
- Output format verification
- Data model reference

---

### 3. file_structure.txt (15 KB)
**Complete project structure with file descriptions**

**Contains:**
- Directory tree with all files
- Description of each source file
- Module responsibilities
- Configuration file layouts
- Test file organization
- Output file structure examples
- Dependencies list
- Installation instructions

**Use for:**
- Setting up the project structure
- Understanding module organization
- Locating specific functionality
- Quick reference during implementation

---

### 4. architecture.md (40 KB)
**Detailed system architecture and design**

**Covers:**
- System overview and high-level architecture
- Architectural principles (separation of concerns, event-driven, etc.)
- Component architecture (all layers)
- Data flow diagrams
- State management strategy
- Event processing pipeline
- Output strategy and table design
- Performance architecture
- Error handling architecture
- Scalability considerations
- Design decisions and rationale

**Use for:**
- Understanding system design
- Making implementation decisions
- Extending the system
- Performance optimization
- Troubleshooting

---

## Quick Start

### For Implementers

1. **Read SC2_EXTRACTION_PLAN.md** (focus on sections 1-6)
   - Understand requirements
   - Review architecture
   - Study data models
   - Review implementation roadmap

2. **Reference file_structure.txt**
   - Create directory structure
   - Set up project files
   - Install dependencies

3. **Follow Implementation Roadmap** (SC2_EXTRACTION_PLAN.md Section 6)
   - Phase 1: Core Infrastructure
   - Phase 2: Event Processing
   - Phase 3: Frame Sampling
   - Phase 4: Output Formatting
   - Phase 5: Testing
   - Phase 6: Documentation

4. **Use architecture.md as reference**
   - Component design details
   - Algorithm implementations
   - Performance considerations

### For Reviewers

1. **SC2_EXTRACTION_PLAN.md** - Review completeness and feasibility
2. **architecture.md** - Review design decisions
3. **data_schema.json** - Validate data model
4. **file_structure.txt** - Check project organization

---

## Key Requirements Recap

### Data to Extract (Frame-by-Frame)

**Units:**
- Unit name/type, position (x, y), ownership
- Creation, death, cancellation events

**Buildings:**
- Building name/type, position, ownership
- States: started, cancelled, destroyed, existing (differentiable)

**Upgrades:**
- Upgrade started, cancelled, completed events
- Current upgrades per player at each timestep

**Messages:**
- All chat messages with timestamp, sender, content

### Technical Specifications

- **Library:** sc2reader v1.8.0 with bot replay patch
- **Load Level:** 3 (tracker events only)
- **Temporal Resolution:** 5-second intervals (112 frames @ Faster speed)
- **Output Format:** Parquet (production), JSON (debugging)
- **Performance Target:** 25+ replays/second
- **Scalability:** 10,000+ replay datasets

---

## Critical Implementation Notes

### 1. Bot Replay Compatibility (CRITICAL)

**Must apply sc2reader_patch.py BEFORE importing sc2reader**

```python
# CORRECT ORDER:
import sc2reader_patch  # Apply patch first
import sc2reader        # Then import sc2reader

# Load with tracker events only
replay = sc2reader.load_replay(path, load_level=3)
```

**Why:**
- AI Arena bot replays have empty cache_handles
- Patch handles this gracefully
- load_level=3 avoids unknown game events (0x76)

**See:** `research/AI_ARENA_COMPATIBILITY.md` for full details

### 2. Building State Differentiation

**Challenge:** Distinguish between started/existing/destroyed/cancelled

**Solution:** Track event sequences per unit_id:

| Event Sequence | State | Example |
|---------------|-------|---------|
| UnitInitEvent only | Constructing | Pylon being built |
| UnitInitEvent → UnitDoneEvent | Completed | Finished Pylon |
| UnitDoneEvent only | Pre-existing | Starting Nexus |
| UnitInitEvent → UnitDiedEvent (no Done) | Cancelled | Cancelled Gateway |
| UnitDoneEvent → UnitDiedEvent | Destroyed | Nexus destroyed |

**See:** SC2_EXTRACTION_PLAN.md Section 5.2 for algorithm

### 3. Frame Sampling Strategy

**Default:** 5-second intervals (112 frames @ Faster speed)

**Rationale:**
- Balances granularity vs. data volume
- Aligns with PlayerStatsEvent frequency
- Captures strategic decisions
- Sufficient for DBN temporal resolution

**Configurable via:** `config.extraction.frame_interval`

### 4. Parquet Output Schema

**Multiple tables strategy:**

1. **replay_metadata.parquet** - One row per replay
2. **frame_states.parquet** - One row per (frame, player)
3. **unit_counts.parquet** - One row per (frame, player, unit_type)
4. **building_counts.parquet** - One row per (frame, player, building_type, state)
5. **upgrades.parquet** - One row per upgrade completion
6. **messages.parquet** - One row per chat message

**Linked by:** `replay_hash` (SHA256 of file)

---

## Implementation Roadmap Summary

### Phase 1: Core Infrastructure (Week 1)
- Project setup
- Data models
- Replay parser
- **Deliverable:** Can load and validate replays

### Phase 2: Event Processing (Week 2)
- GameStateTracker
- Event handlers
- EventProcessor
- **Deliverable:** Events correctly update game state

### Phase 3: Frame Sampling (Week 3)
- FrameSampler
- State reconstruction
- Derived features
- **Deliverable:** Can sample game state at intervals

### Phase 4: Output Formatting (Week 4)
- OutputFormatter
- Parquet/JSON/CSV writers
- Data validation
- **Deliverable:** Can write output files

### Phase 5: Testing (Week 5)
- Test suite
- Integration tests
- Benchmarking
- **Deliverable:** All tests passing, performance validated

### Phase 6: Documentation (Week 6)
- User documentation
- API reference
- Usage scripts
- **Deliverable:** Production-ready package

---

## Research Foundation

These plans are based on comprehensive research documented in:

- **research/SC2_EXTRACTION_RESEARCH.md** - Library comparison, data availability analysis
- **research/AI_ARENA_COMPATIBILITY.md** - Bot replay compatibility solution

**Key findings:**
- All required data is available from tracker events
- sc2reader is the best library choice
- AI Arena bot replays fully supported with patch
- No technical blockers identified

---

## Success Criteria

The implementation is ready when:

1. All required data points extractable
2. Handles both ladder and bot replays
3. Processes 25+ replays/second
4. Scalable to 10,000+ replays
5. Comprehensive error handling
6. Full test coverage
7. Complete documentation

---

## Next Steps

1. **Review planning documents** (this directory)
2. **Set up development environment**
   - Create virtual environment
   - Install dependencies (sc2reader, pandas, pyarrow)
   - Copy sc2reader_patch.py

3. **Begin Phase 1 implementation**
   - Create project structure (see file_structure.txt)
   - Implement data models (src/models/)
   - Implement replay parser (src/parser/)
   - Write initial tests

4. **Iterate through implementation roadmap**
   - Complete one phase at a time
   - Test thoroughly at each phase
   - Validate against example replays

5. **Deploy and validate**
   - Extract large batch of replays
   - Validate output quality
   - Benchmark performance
   - Use for DBN training

---

## Questions or Issues?

Refer to:
- **SC2_EXTRACTION_PLAN.md** - Comprehensive implementation guide
- **architecture.md** - Design details and rationale
- **research/** - Research findings and compatibility notes

---

## File Sizes

- SC2_EXTRACTION_PLAN.md: 73 KB
- architecture.md: 40 KB
- data_schema.json: 19 KB
- file_structure.txt: 15 KB
- **Total:** 147 KB

---

**Status:** Planning Phase Complete ✓
**Ready for:** Implementation Phase
**Estimated Duration:** 6 weeks (part-time) or 3 weeks (full-time)
**Confidence:** High (all blockers resolved, approach validated)
