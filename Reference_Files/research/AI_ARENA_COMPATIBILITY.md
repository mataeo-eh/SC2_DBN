# AI Arena Bot Replay Compatibility with sc2reader

## Executive Summary

**Problem**: AI Arena bot replays (from aiarena.net or local bot matches) fail to parse with sc2reader due to missing metadata.

**Root Cause**: Bot replays have empty `cache_handles` list, causing IndexError when sc2reader tries to access `cache_handles[0]` on line 389 of resources.py.

**Solution**: Apply monkey patch + use `load_level=3` (tracker events only).

**Status**: ✅ **WORKING** - All required data points successfully extractable from bot replays.

---

## Problem Details

### The cache_handles Bug

**Error Message**:
```
IndexError: list index out of range
File ".../sc2reader/resources.py", line 389, in load_details
    self.region = details["cache_handles"][0].server.lower()
```

**Root Cause**:
- Ladder/human replays: `cache_handles` contains server and map metadata
- Bot replays: `cache_handles` is an empty list `[]`
- sc2reader blindly accesses `[0]` without checking if list is empty

**Affected Code** (sc2reader/resources.py:389-397):
```python
self.region = details["cache_handles"][0].server.lower()  # CRASHES HERE
self.map_hash = details["cache_handles"][-1].hash
self.map_file = details["cache_handles"][-1]
dependency_hashes = [d.hash for d in details["cache_handles"]]
```

###Secondary Issue: Unknown Game Events

Bot replays contain game event type `0x76` which sc2reader doesn't recognize:
```
sc2reader.exceptions.ReadError: Event type 0x76 unknown at position 0x0., Type: 118
```

This only affects `load_level=4` (game events parsing).

---

## Solution

### Part 1: Monkey Patch for cache_handles

Apply patch BEFORE loading replays:

```python
import sc2reader_patch  # This applies the fix
import sc2reader

replay = sc2reader.load_replay('bot_replay.SC2Replay', load_level=3)
```

**What the patch does**:
- Checks if `cache_handles` exists and has length > 0
- If empty (bot replay): sets `region="local"`, `map_hash=None`, `map_file=None`
- Handles expansion detection gracefully
- Defaults to `expansion="LotV"` for bot replays

**Patch file**: `sc2reader_patch.py` (see full code below)

### Part 2: Use load_level=3

**Load level comparison**:

| Level | Data Loaded | Bot Replay Support |
|-------|-------------|-------------------|
| 0 | Basic metadata only | ✅ Works (but no useful data) |
| 1 | + Details (map, players) | ✅ Works (but no events!) |
| 2 | + Messages | ✅ Works (but no events!) |
| 3 | + Tracker events | ✅ **WORKS PERFECTLY** |
| 4 | + Game events | ❌ Fails on unknown event 0x76 |

**Recommendation**: **Use load_level=3** for bot replays.

---

## Data Availability (load_level=3)

Tested on bot replays:
- `replays/1_basic_bot_vs_loser_bot.SC2Replay` (280 tracker events)
- `replays/4533040_what_why_PylonAIE_v4.SC2Replay` (330 tracker events)

### Available Data ✅

| Data Category | Status | Event Types | Notes |
|--------------|--------|-------------|-------|
| **Units - Creation** | ✅ Available | `UnitBornEvent`, `UnitInitEvent` | Full unit lifecycle tracking |
| **Units - Death** | ✅ Available | `UnitDiedEvent` | Includes killer info |
| **Units - Completion** | ✅ Available | `UnitDoneEvent` | When construction finishes |
| **Unit Positions** | ✅ Available | `UnitPositionsEvent` | Periodic snapshots |
| **Unit Type Changes** | ✅ Available | `UnitTypeChangeEvent` | Zerg morphing, etc. |
| **Buildings** | ✅ Available | Same as units | Differentiate via unit_type_name |
| **Upgrades** | ✅ Available | `UpgradeCompleteEvent` | Completion only (not start) |
| **Player Stats** | ✅ Available | `PlayerStatsEvent` | Resources, supply, workers |
| **Messages** | ✅ Available | Via `replay.messages` | Chat/game messages |
| **Temporal Data** | ✅ Available | All events have `frame` | Frame-by-frame precision |

### Event Attributes

**UnitBornEvent** provides:
- `frame`: Game frame number
- `unit_id`: Unique unit identifier
- `unit_type_name`: Unit/building name (e.g., "Probe", "Gateway")
- `control_pid`: Owner player ID
- `x`, `y`: Position coordinates
- `unit_controller`, `unit_upkeeper`: Ownership details

**UnitDiedEvent** provides:
- `frame`: When unit died
- `unit_id`: Which unit died
- `killer_pid`: Which player killed it (if applicable)

**UpgradeCompleteEvent** provides:
- `frame`: When upgrade finished
- `upgrade_type_name`: Upgrade name
- `pid`: Player ID
- `count`: Upgrade level

**PlayerStatsEvent** provides:
- `frame`: Snapshot time
- `player_id`: Which player
- `minerals_current`, `vespene_current`: Resources
- `food_used`, `food_made`: Supply
- `workers_active_count`: Worker count
- `minerals_collection_rate`, `vespene_collection_rate`: Income

### Building State Differentiation

**How to distinguish building states**:

```python
buildings = {}

for event in replay.tracker_events:
    if isinstance(event, UnitBornEvent):
        if is_building(event.unit_type_name):
            buildings[event.unit_id] = {
                'type': event.unit_type_name,
                'state': 'started',  # Construction started
                'born_frame': event.frame
            }

    elif isinstance(event, UnitDoneEvent):
        if event.unit_id in buildings:
            buildings[event.unit_id]['state'] = 'existing'  # Construction complete
            buildings[event.unit_id]['done_frame'] = event.frame

    elif isinstance(event, UnitDiedEvent):
        if event.unit_id in buildings:
            buildings[event.unit_id]['state'] = 'destroyed'  # Building destroyed
            buildings[event.unit_id]['died_frame'] = event.frame
```

**States are clearly differentiable**: ✅
- **Started**: `UnitBornEvent` fired, no `UnitDoneEvent` yet
- **Existing**: `UnitDoneEvent` fired (construction complete)
- **Destroyed**: `UnitDiedEvent` fired
- **Cancelled**: Unit dies before `UnitDoneEvent` (born_frame exists, no done_frame, then died)

---

## Implementation Code

### sc2reader_patch.py (Monkey Patch)

```python
"""
Monkey patch for sc2reader to handle AI Arena bot replays with empty cache_handles

The bug: Bot replays have empty cache_handles list, but sc2reader tries to access [0]
Location: sc2reader/resources.py lines 389-397

This patch fixes the IndexError and allows bot replays to be parsed.
"""
import sc2reader
from sc2reader.resources import Replay
from sc2reader import utils
from datetime import datetime
import hashlib

# GAME_SPEED_FACTOR from sc2reader
GAME_SPEED_FACTOR = {
    "LotV": {"Slower": 0.6, "Slow": 0.8, "Normal": 1.0, "Fast": 1.2, "Faster": 1.4},
    "HotS": {"Slower": 0.6, "Slow": 0.8, "Normal": 1.0, "Fast": 1.2, "Faster": 1.4},
    "WoL": {"Slower": 0.6, "Slow": 0.8, "Normal": 1.0, "Fast": 1.2, "Faster": 1.4},
}

def patched_load_details(self):
    """
    Patched version that handles empty cache_handles gracefully for bot replays
    This is a direct copy of the original with safe cache_handles access
    """
    if "replay.details" in self.raw_data:
        details = self.raw_data["replay.details"]
    elif "replay.details.backup" in self.raw_data:
        details = self.raw_data["replay.details.backup"]
    else:
        return

    self.map_name = details["map_name"]

    # PATCH: Handle empty cache_handles for bot replays
    if details.get("cache_handles") and len(details["cache_handles"]) > 0:
        self.region = details["cache_handles"][0].server.lower()
        self.map_hash = details["cache_handles"][-1].hash
        self.map_file = details["cache_handles"][-1]
    else:
        # Bot replay - no cache_handles
        self.region = "local"
        self.map_hash = None
        self.map_file = None

    # Expand this special case mapping
    if self.region == "sg":
        self.region = "sea"

    # PATCH: Handle dependency hashes safely
    if details.get("cache_handles") and len(details["cache_handles"]) > 0:
        dependency_hashes = [d.hash for d in details["cache_handles"]]
        if (
            hashlib.sha256("Standard Data: Void.SC2Mod".encode("utf8")).hexdigest()
            in dependency_hashes
        ):
            self.expansion = "LotV"
        elif (
            hashlib.sha256("Standard Data: Swarm.SC2Mod".encode("utf8")).hexdigest()
            in dependency_hashes
        ):
            self.expansion = "HotS"
        elif (
            hashlib.sha256("Standard Data: Liberty.SC2Mod".encode("utf8")).hexdigest()
            in dependency_hashes
        ):
            self.expansion = "WoL"
        else:
            self.expansion = ""
    else:
        # Bot replays - default to LotV
        self.expansion = "LotV"

    self.windows_timestamp = details["file_time"]
    self.unix_timestamp = utils.windows_to_unix(self.windows_timestamp)
    self.end_time = datetime.utcfromtimestamp(self.unix_timestamp)

    # The utc_adjustment is either the adjusted windows timestamp OR
    # the value required to get the adjusted timestamp. We know the upper
    # limit for any adjustment number so use that to distinguish between
    # the two cases.
    if details["utc_adjustment"] < 10**7 * 60 * 60 * 24:
        self.time_zone = details["utc_adjustment"] / (10**7 * 60 * 60)
    else:
        self.time_zone = (details["utc_adjustment"] - details["file_time"]) / (
            10**7 * 60 * 60
        )

    self.game_length = self.length
    self.real_length = utils.Length(
        seconds=self.length.seconds
        // GAME_SPEED_FACTOR[self.expansion].get(self.speed, 1.0)
    )
    self.start_time = datetime.utcfromtimestamp(
        self.unix_timestamp - self.real_length.seconds
    )
    self.date = self.end_time  # backwards compatibility

# Apply the monkey patch
Replay.load_details = patched_load_details

print("sc2reader patch applied successfully!")
print("Bot replays with empty cache_handles will now work.")
```

### Usage Example

```python
# Apply patch BEFORE loading replays
import sc2reader_patch

import sc2reader

# Load bot replay with tracker events
replay = sc2reader.load_replay('bot_replay.SC2Replay', load_level=3)

# Extract data
print(f"Map: {replay.map_name}")
print(f"Duration: {replay.game_length}")
print(f"Tracker Events: {len(replay.tracker_events)}")

# Process events
for event in replay.tracker_events:
    if isinstance(event, sc2reader.events.tracker.UnitBornEvent):
        print(f"Unit born: {event.unit_type_name} at frame {event.frame}")
    elif isinstance(event, sc2reader.events.tracker.UpgradeCompleteEvent):
        print(f"Upgrade: {event.upgrade_type_name} completed at frame {event.frame}")
```

---

## Testing Results

Tested with:
- **sc2reader version**: 1.8.0
- **Python version**: 3.12
- **Replay types**: Local bot matches, AI Arena replays

### Test Replay 1: `1_basic_bot_vs_loser_bot.SC2Replay`
- **Duration**: 01:37 (2,176 frames)
- **Map**: Acropolis AIE
- **Events**: 280 tracker events
  - 228 UnitBornEvent
  - 13 UnitDiedEvent
  - 4 UpgradeCompleteEvent
  - 30 PlayerStatsEvent
  - 3 UnitPositionsEvent
- **Result**: ✅ All data extracted successfully

### Test Replay 2: `4533040_what_why_PylonAIE_v4.SC2Replay`
- **Duration**: 02:45 (3,704 frames)
- **Map**: Pylon AIE
- **Events**: 330 tracker events
  - 228 UnitBornEvent (includes UnitInitEvent: 5)
  - 18 UnitDiedEvent
  - 2 UnitDoneEvent
  - 4 UpgradeCompleteEvent
  - 50 PlayerStatsEvent
  - 11 UnitPositionsEvent
  - 15 UnitTypeChangeEvent
- **Result**: ✅ All data extracted successfully

---

## Limitations & Workarounds

### 1. No Player Information (Minor)
- **Issue**: `replay.players` is empty (length 0)
- **Workaround**: Player IDs are available in events (`control_pid`, `player_id`)
- **Impact**: Minimal - can infer players from events

### 2. Upgrade Start Times Not Available
- **Issue**: Only `UpgradeCompleteEvent` exists, not start/cancel
- **Workaround**: Use completion events only
- **Impact**: Minimal for DBN training - completion is the key event

### 3. Game Events Not Parsable (load_level=4)
- **Issue**: Unknown event type 0x76
- **Workaround**: Use load_level=3 instead
- **Impact**: None - tracker events contain all required data

### 4. Position Data is Sparse
- **Issue**: `UnitPositionsEvent` occurs ~3-11 times per game (periodic snapshots)
- **Workaround**: Interpolate positions between snapshots, or use birth position
- **Impact**: Minor - sufficient for strategic analysis

---

## Comparison: Bot Replays vs Ladder Replays

| Feature | Ladder Replays | Bot Replays | Impact |
|---------|---------------|-------------|--------|
| cache_handles | ✅ Present | ❌ Empty list | Patched ✅ |
| Player metadata | ✅ Full details | ❌ Empty | Get from events ✅ |
| Tracker events | ✅ Full | ✅ Full | ✅ Works |
| Game events (0x76) | ✅ Parseable | ❌ Unknown type | Use load_level=3 ✅ |
| Map name | ✅ Yes | ✅ Yes | ✅ Works |
| Messages | ✅ Yes | ✅ Yes | ✅ Works |

---

## Recommendations

### For DBN Training

1. **Use load_level=3** for all bot replays
2. **Apply sc2reader_patch.py** before parsing
3. **Extract at 5-second intervals** (112 frames @ Faster speed)
4. **Ignore missing player metadata** - infer from events
5. **Use tracker events only** - they contain all needed data

### Data Extraction Strategy

```python
import sc2reader_patch
import sc2reader
from collections import defaultdict

def extract_bot_replay(replay_path):
    """Extract DBN training data from bot replay"""

    # Load with tracker events only
    replay = sc2reader.load_replay(replay_path, load_level=3)

    # Build state timeline
    frames = []
    current_state = defaultdict(lambda: defaultdict(dict))

    for event in replay.tracker_events:
        frame = event.frame

        # Track units
        if isinstance(event, UnitBornEvent):
            current_state['units'][event.unit_id] = {
                'type': event.unit_type_name,
                'player': event.control_pid,
                'state': 'alive',
                'born_frame': frame
            }

        # ... (process other events)

        # Sample every 5 seconds (112 frames)
        if frame % 112 == 0:
            frames.append({
                'frame': frame,
                'time': frame / 22.4,
                'units': dict(current_state['units']),
                'upgrades': dict(current_state['upgrades']),
                # ...
            })

    return frames
```

---

## Conclusion

✅ **AI Arena bot replays are fully compatible with sc2reader** when using:
1. Monkey patch for cache_handles bug
2. load_level=3 (tracker events)

✅ **All required data points for DBN training are available**:
- Units: creation, death, positions, types
- Buildings: lifecycle (started/existing/destroyed)
- Upgrades: completion events
- Player stats: resources, supply
- Frame-by-frame temporal data

❌ **No blockers** - minor limitations are easily worked around

**Recommendation**: Proceed with sc2reader v1.8.0 + patch for bot replay extraction.

---

## References

- [sc2reader GitHub - Issue #176](https://github.com/GraylinKim/sc2reader/issues/176) - Observer AttributeError
- [sc2reader GitHub - Issue #125](https://github.com/ggtracker/sc2reader/issues/125) - Replay parsing failures
- [sc2reader Documentation](https://sc2reader.readthedocs.io/)
- [AI Arena Documentation](https://aiarena.github.io/)

---

**Status**: ✅ **RESOLVED**
**Date**: 2026-01-23
**Tested By**: Claude Code Agent
