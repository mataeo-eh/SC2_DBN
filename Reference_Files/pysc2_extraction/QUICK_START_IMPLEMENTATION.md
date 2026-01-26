# Quick Start: Continue SC2 Pipeline Implementation

**Status**: Phase 1 - Core Components (21% complete)
**Next Task**: Implement BuildingExtractor
**Estimated Time**: 2-3 hours

---

## What's Been Done ✅

1. **Project Structure** - Complete module layout in `src_new/`
2. **ReplayLoader** - Loads replays, starts SC2, handles player perspectives
3. **GameLoopIterator** - Iterates through game loops, yields observations
4. **UnitExtractor** - Extracts unit data, tracks tags, assigns IDs

**Total Code**: ~730 lines across 4 files

---

## Next Step: BuildingExtractor

### Implementation Guide

**File**: `src_new/extractors/building_extractor.py`

**Pattern**: Copy from `unit_extractor.py` and modify for buildings

**Key Differences**:

1. **Filter for buildings ONLY**
```python
# In extract() method:
for unit in raw_data.units:
    if not is_building(unit.unit_type):  # Opposite of UnitExtractor
        continue
```

2. **Track construction state**
```python
# Add to unit_data:
'status': self._determine_building_status(tag, unit),  # started/building/completed/destroyed
'progress': unit.build_progress * 100,  # Convert to percentage
```

3. **Building status detection**
```python
def _determine_building_status(self, tag, unit):
    """
    Returns: 'started', 'building', 'completed', or 'destroyed'

    Logic:
    - started: tag not in previous_tags AND build_progress < 1.0
    - building: tag in previous_tags AND build_progress < 1.0
    - completed: build_progress == 1.0
    - destroyed: tag in dead_units event
    """
```

4. **Track timestamps**
```python
# Add to __init__:
self.building_started_loops = {}  # tag -> game_loop when started
self.building_completed_loops = {}  # tag -> game_loop when completed

# In extract():
if status == 'started':
    self.building_started_loops[tag] = obs.observation.game_loop

if status == 'completed' and tag not in self.building_completed_loops:
    self.building_completed_loops[tag] = obs.observation.game_loop

# Add to unit_data:
'started_loop': self.building_started_loops.get(tag),
'completed_loop': self.building_completed_loops.get(tag),
```

### Testing Your Implementation

**Test Script** (save as `test_building_extractor.py`):

```python
from src_new.pipeline import ReplayLoader, GameLoopIterator
from src_new.extractors import BuildingExtractor

# Load a replay
loader = ReplayLoader()
loader.load_replay("replays/test_game.SC2Replay")

with loader.start_sc2_instance() as controller:
    loader.get_replay_info(controller)
    loader.start_replay(controller, observed_player_id=1)

    # Create extractor
    building_extractor = BuildingExtractor(player_id=1)

    # Process first 50 loops
    iterator = GameLoopIterator(controller, step_mul=22, max_loops=1000)

    for obs in iterator:
        buildings_data = building_extractor.extract(obs)

        # Print buildings
        if buildings_data:
            print(f"\nLoop {iterator.current_loop}:")
            for building_id, data in buildings_data.items():
                print(f"  {building_id}: {data.get('unit_type_name')} - "
                      f"{data.get('status')} ({data.get('progress', 0):.0f}%)")

    controller.quit()
```

**Expected Output**:
```
Loop 100:
  p1_commandcenter_001: CommandCenter - completed (100%)
  p1_supplydepot_001: SupplyDepot - building (45%)

Loop 200:
  p1_commandcenter_001: CommandCenter - completed (100%)
  p1_supplydepot_001: SupplyDepot - completed (100%)
  p1_barracks_001: Barracks - started (5%)
...
```

---

## After BuildingExtractor: Next Components

### 2. EconomyExtractor (Simple, 1 hour)

**File**: `src_new/extractors/economy_extractor.py`

**No state tracking needed!** Just extract fields:

```python
def extract(self, obs):
    player_common = obs.observation.player_common
    score = obs.observation.score.score_details

    return {
        'minerals': player_common.minerals,
        'vespene': player_common.vespene,
        'supply_used': player_common.food_used,
        'supply_cap': player_common.food_cap,
        'supply_army': player_common.food_army,
        'supply_workers': player_common.food_workers,
        'workers_idle': player_common.idle_worker_count,
        'army_count': player_common.army_count,

        # Collection stats
        'minerals_collected': score.collected_minerals,
        'vespene_collected': score.collected_vespene,
        'mineral_rate': score.collection_rate_minerals,
        'vespene_rate': score.collection_rate_vespene,
    }
```

### 3. UpgradeExtractor (Moderate, 1-2 hours)

**File**: `src_new/extractors/upgrade_extractor.py`

**Track upgrade completions**:

```python
def extract(self, obs):
    current_upgrades = set(obs.observation.raw_data.player.upgrade_ids)
    new_upgrades = current_upgrades - self.previous_upgrades

    # Record new upgrades
    for upgrade_id in new_upgrades:
        name = self._get_upgrade_name(upgrade_id)
        self.completed_upgrades[name] = obs.observation.game_loop

    self.previous_upgrades = current_upgrades

    # Return all completed upgrades (boolean flags)
    return {f'upgrade_{name}': True for name in self.completed_upgrades.keys()}
```

---

## Complete Phase 1 Checklist

- [x] ReplayLoader
- [x] GameLoopIterator
- [x] UnitExtractor
- [ ] BuildingExtractor ← **YOU ARE HERE**
- [ ] EconomyExtractor
- [ ] UpgradeExtractor

**When Phase 1 is done**:
- You can extract ALL game state data from a replay
- Ready to move to Phase 2 (schema management and wide-format transformation)

---

## Reference Materials

### Code Examples
- **UnitExtractor**: `src_new/extractors/unit_extractor.py` (your template)
- **Research Examples**: `research_examples/02_extract_unit_data.py`
- **Research Examples**: `research_examples/03_extract_economy_upgrades.py`

### Documentation
- **Architecture**: `docs/planning/architecture.md`
- **API Specs**: `docs/planning/api_specifications.md`
- **Processing Algorithms**: `docs/planning/processing_algorithm.md`
- **Research Summary**: `docs/research/00_RESEARCH_SUMMARY.md`

### Data Access Paths
```python
# Units/Buildings
obs.observation.raw_data.units  # List of all units
unit.unit_type                  # Type ID
unit.build_progress             # 0.0 to 1.0
unit.pos                        # Position (x, y, z)
unit.health, unit.shield        # Vitals

# Economy
obs.observation.player_common.minerals
obs.observation.player_common.vespene
obs.observation.score.score_details.collected_minerals

# Upgrades
obs.observation.raw_data.player.upgrade_ids  # List of int IDs
```

---

## Common Issues & Solutions

### Issue: Import errors
**Solution**: Make sure you're running from project root:
```bash
cd C:\Users\matae\OneDrive\Desktop\Coding-Projects\local-play-bootstrap-main
python test_building_extractor.py
```

### Issue: SC2 not starting
**Solution**: Ensure SC2 is installed and run_config can find it

### Issue: Replay not loading
**Solution**: Check replay path is correct and replay file is not corrupted

### Issue: No buildings found
**Solution**: Verify `is_building()` function includes correct type IDs

---

## Timeline Estimate

**Remaining Phase 1 Work**:
- BuildingExtractor: 2-3 hours
- EconomyExtractor: 1 hour
- UpgradeExtractor: 1-2 hours

**Total**: 4-6 hours to complete Phase 1

**After Phase 1**: You'll have complete game state extraction! 🎉

---

## Questions? Check These First

1. **How do I test a component?**
   - Create a simple test script (see examples above)
   - Use a small replay from `replays/` directory
   - Print extracted data to verify correctness

2. **What if I get a pysc2 error?**
   - Check SC2 is installed
   - Verify replay version compatibility
   - Check logs for specific error messages

3. **How do I know if my extraction is correct?**
   - Compare with research examples output
   - Verify unit counts match what you see in replay viewer
   - Check all expected fields are present

---

**Good luck! You're 21% done with implementation! 🚀**

**Next**: Implement BuildingExtractor following the guide above.
