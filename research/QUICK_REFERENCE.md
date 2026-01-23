# SC2 Replay Extraction - Quick Reference

## TL;DR

**Library:** `sc2reader` v1.8.0
**Installation:** `pip install sc2reader`
**Status:** ✅ All required data extractable
**Performance:** ~0.04s per replay, 164k events/sec

---

## Basic Usage

```python
import sc2reader

# Load replay with full event data
replay = sc2reader.load_replay('replay.SC2Replay', load_level=4)

# Access metadata
print(f"Map: {replay.map_name}")
print(f"Duration: {replay.game_length}")
print(f"Players: {[p.name for p in replay.players]}")

# Iterate events
for event in replay.tracker_events:
    print(f"Frame {event.frame}: {type(event).__name__}")
```

---

## Key Event Types

| Event | When | Key Data |
|-------|------|----------|
| `UnitBornEvent` | Unit spawns instantly | type, location, player, frame |
| `UnitInitEvent` | Building/unit construction starts | type, location, player, frame |
| `UnitDoneEvent` | Construction completes | unit_id, frame |
| `UnitDiedEvent` | Unit/building dies | unit_id, killer, location, frame |
| `PlayerStatsEvent` | Periodic resource snapshot | minerals, gas, supply, workers |
| `UpgradeCompleteEvent` | Upgrade finishes | upgrade_type, player, frame |
| `ChatEvent` | In-game message | text, player, target, frame |

---

## Data Availability Checklist

- ✅ Unit creation/completion/death
- ✅ Building lifecycle (started/completed/destroyed)
- ✅ Upgrade completion
- ✅ Chat messages
- ✅ Resources (minerals, gas)
- ✅ Supply (used/made)
- ✅ Worker count
- ✅ Unit positions (periodic)
- ✅ Frame-level timestamps
- ⚠️ Upgrade start (indirect via commands)
- ❌ Upgrade cancellation (not tracked)

---

## Recommended Settings

**Temporal Resolution:** 5-second intervals (80 frames @ Faster speed)
**Output Format:** Parquet (for large-scale) or JSON (for debugging)
**Load Level:** 4 (full game + tracker events)
**Validation:** Min 2 minutes game length, version >= 2.0.8

---

## Performance Estimates

| Replays | Parse Time | Storage (Parquet, 5s intervals) |
|---------|------------|----------------------------------|
| 100 | ~4 seconds | ~5 MB |
| 1,000 | ~40 seconds | ~50 MB |
| 10,000 | ~7 minutes | ~500 MB |

---

## Building State Logic

```python
# Track building states via event sequence
if UnitInitEvent and not UnitDoneEvent:
    state = "constructing"
elif UnitDoneEvent and not UnitDiedEvent:
    state = "completed"
elif UnitDiedEvent and UnitDoneEvent:
    state = "destroyed"
elif UnitDiedEvent and not UnitDoneEvent:
    state = "cancelled"
```

---

## Known Issues

1. **AI Arena replays:** May fail to load (cache_handles bug)
   - **Fix:** Use human/ladder replays OR patch sc2reader

2. **Old replays:** Versions < 2.0.4 lack tracker events
   - **Fix:** Filter to version >= 2.0.8

3. **Unit transformations:** Zerg morph creates new unit_id
   - **Fix:** Track both IDs, note transformation

---

## Next Steps

1. Define exact feature set for DBN (100-200 features typical)
2. Implement extraction pipeline with error handling
3. Test on sample replays (10-100)
4. Scale to full dataset (10,000+)
5. Train DBN model

---

## Full Documentation

See `SC2_EXTRACTION_RESEARCH.md` for complete technical analysis (1,510 lines).

---

## Key Contacts

- **sc2reader GitHub:** https://github.com/GraylinKim/sc2reader
- **Documentation:** https://sc2reader.readthedocs.io/
- **IRC:** #sc2reader on Freenode (for live support)
