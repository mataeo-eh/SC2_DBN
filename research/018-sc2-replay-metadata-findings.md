# Research 018: SC2 Replay Metadata Available for JSON Output

**Date**: 2026-03-01
**Objective**: Document all metadata fields available from SC2 replay files to build a comprehensive metadata JSON output, replacing the current schema-only JSON.

---

## Summary

SC2 replay files contain rich metadata from **three independent sources**, each accessible without running the full replay loop. Combined, they provide everything needed for a comprehensive dataset metadata file: map dimensions, game version, player details, game speed, duration, timestamps, and end-of-game statistics.

| Source | How to access | Requires SC2 engine? |
|--------|--------------|---------------------|
| `replay.gamemetadata.json` (MPQ) | `mpyq.MPQArchive` + `json.loads` | No |
| `replay.header` / `replay.details` / `replay.initData` (s2protocol) | `mpyq.MPQArchive` + `s2protocol.versions.build(N).decode_*()` | No |
| `ResponseReplayInfo` / `ResponseGameInfo` (SC2 API proto) | `controller.replay_info()` / `controller.game_info()` | Yes |

---

## Research Question 1: Map Dimensions

### Answer: AVAILABLE from two sources

**Source A: s2protocol `replay.initData` (no engine required)**

```python
import mpyq
from s2protocol import versions

archive = mpyq.MPQArchive(replay_path)
header_content = archive.header['user_data_header']['content']
header = versions.latest().decode_replay_header(header_content)
base_build = header['m_version']['m_baseBuild']
protocol = versions.build(base_build)

initdata_raw = archive.read_file('replay.initData')
initdata = protocol.decode_replay_initdata(initdata_raw)
game_desc = initdata['m_syncLobbyState']['m_gameDescription']

map_width = game_desc['m_mapSizeX']   # e.g., 160
map_height = game_desc['m_mapSizeY']  # e.g., 184
```

Verified with actual replays:
- `match_4184936.SC2Replay` (Persephone AIE): 160 x 184
- `Astrea vs SKillous` (Curious Minds LE): 152 x 152

**Source B: `controller.game_info()` proto (requires engine, only after `start_replay()`)**

```python
# Only valid in Status.in_game or Status.in_replay (after start_replay())
game_info = controller.game_info()  # Returns ResponseGameInfo

# ResponseGameInfo.start_raw is a StartRaw message with:
map_size = game_info.start_raw.map_size  # Size2DI with .x and .y fields
playable_area = game_info.start_raw.playable_area  # RectangleI with .p0 and .p1 (PointI)
start_locations = game_info.start_raw.start_locations  # repeated Point2D
```

`StartRaw` fields:
| Field | Type | Description |
|-------|------|-------------|
| `map_size` | `Size2DI` (x, y) | Full map dimensions in game tiles |
| `pathing_grid` | `ImageData` | Binary grid of pathable tiles |
| `terrain_height` | `ImageData` | Height map |
| `placement_grid` | `ImageData` | Binary grid of buildable tiles |
| `playable_area` | `RectangleI` (p0, p1) | Playable region bounds |
| `start_locations` | `repeated Point2D` | Player spawn points |

**Recommendation**: Use Source A (s2protocol initdata) because it requires no engine and is already parsed during economy extraction. Source B provides additional data (playable_area, start_locations) that could be valuable but requires an extra `controller.game_info()` call after `start_replay()`.

**Currently in pipeline**: NOT captured. Neither source is used for map dimensions.

---

## Research Question 2: Map Name

### Answer: AVAILABLE and already captured

The map name is accessible from multiple sources:

| Source | Field | Example value |
|--------|-------|---------------|
| `ResponseReplayInfo` | `info.map_name` | `"Persephone AIE"` |
| `replay.gamemetadata.json` | `metadata["Title"]` | `"Persephone AIE"` |
| `replay.details` (s2protocol) | `details['m_title']` | `b'Persephone AIE'` |
| `replay.gamemetadata.json` | `metadata["MapName"]` | `"PersephoneAIE_v4.SC2Map"` |
| `replay.details` (s2protocol) | `details['m_mapFileName']` | `b'PersephoneAIE_v4.SC2Map'` |

Note: `Title`/`m_title`/`map_name` = human-readable name. `MapName`/`m_mapFileName` = the actual .SC2Map filename.

**Currently in pipeline**: `info_proto.map_name` is captured in the metadata dict at `src_new/extraction/replay_loader.py:171`. This is the human-readable name. The .SC2Map filename is NOT captured.

---

## Research Question 3: Game Version

### Answer: AVAILABLE from three sources

**Source A: `ResponseReplayInfo` proto (already in pipeline flow)**

```python
info = controller.replay_info(replay_data)
info.game_version  # string, e.g., "4.10.0.75689"
info.data_version  # string, hex hash, e.g., "B89B5D6FA7CBF6452E721311BFBC6CB2"
info.data_build    # uint32, e.g., 75689
info.base_build    # uint32, e.g., 75689
```

**Source B: pysc2's `replay.get_replay_version()` (already called in pipeline)**

```python
# In src_new/pipeline/replay_loader.py:94
self.replay_version = replay.get_replay_version(self.replay_data)
# Returns a Version namedtuple with:
#   game_version: str, e.g., "4.10.0" (3 parts, NOT 4 like the proto)
#   build_version: int, e.g., 75689
#   data_version: str (hex hash, only in replays >= 4.1)
#   binary: None
```

This function internally reads `replay.gamemetadata.json` from the MPQ archive:
```python
metadata = json.loads(archive[b"replay.gamemetadata.json"].decode("utf-8"))
# metadata["GameVersion"] = "4.10.0.75689" (4 parts)
# metadata["BaseBuild"] = "Base75689"
# metadata["DataBuild"] = "75689"
# metadata["DataVersion"] = "B89B5D6FA7CBF6452E721311BFBC6CB2"
```

**Source C: s2protocol replay header**

```python
header = versions.latest().decode_replay_header(header_content)
# header['m_version'] dict:
#   m_major: 4
#   m_minor: 10
#   m_revision: 0
#   m_build: 75689
#   m_baseBuild: 75689
#   m_flags: 1
# header['m_dataBuildNum']: 75689
```

**Currently in pipeline**: `self.replay_version.game_version` is logged at `pipeline/replay_loader.py:96` but NOT included in the metadata dict. The metadata dict at `extraction/replay_loader.py:170-188` does not include version fields.

---

## Research Question 4: Additional ResponseReplayInfo Fields

### Answer: Several fields NOT currently captured

Complete `ResponseReplayInfo` fields from the proto definition at `sc2api_pb2.py:2488-2586`:

| Field | Type | Proto # | Currently captured? | Description |
|-------|------|---------|-------------------|-------------|
| `map_name` | string | 1 | YES | Human-readable map name |
| `local_map_path` | string | 2 | NO | Local filesystem path to map |
| `player_info` | repeated `PlayerInfoExtra` | 3 | YES (partially) | Player details |
| `game_duration_loops` | uint32 | 4 | YES | Duration in game loops |
| `game_duration_seconds` | float | 5 | NO (computed manually) | Duration in seconds (from engine) |
| `game_version` | string | 6 | NO | Full version string e.g., "4.10.0.75689" |
| `data_version` | string | 11 | NO | Data hash |
| `data_build` | uint32 | 7 | NO | Data build number |
| `base_build` | uint32 | 8 | NO | Base build number |
| `error` | enum Error | 9 | NO | Error code if any |
| `error_details` | string | 10 | NO | Error details if any |

`PlayerInfoExtra` fields (proto at `sc2api_pb2.py:2436-2484`):

| Field | Type | Currently captured? |
|-------|------|-------------------|
| `player_info` | `PlayerInfo` | YES (partially) |
| `player_result` | `PlayerResult` | YES |
| `player_mmr` | int32 | YES |
| `player_apm` | int32 | YES |

`PlayerInfo` fields (proto at `sc2api_pb2.py:3058-3127`):

| Field | Type | Currently captured? |
|-------|------|-------------------|
| `player_id` | uint32 | NO (using loop index + 1 instead) |
| `type` | enum `PlayerType` | NO |
| `race_requested` | enum `Race` | NO |
| `race_actual` | enum `Race` | YES |
| `difficulty` | enum `Difficulty` | NO |
| `ai_build` | enum `AIBuild` | NO |
| `player_name` | string | YES |

**Key missing fields**: `game_version`, `data_build`, `base_build`, `game_duration_seconds` (native), `player_info.type` (Participant/Computer/Observer), `race_requested` (relevant when player picks Random).

---

## Research Question 5: s2protocol Header Data

### Answer: Rich metadata available from 4 MPQ sections

### 5a. `replay.header` (decoded via `decode_replay_header`)

```python
{
    "m_signature": b'StarCraft II replay\x1b11',
    "m_version": {
        "m_flags": 1,           # Release flag
        "m_major": 4,           # Major version
        "m_minor": 10,          # Minor version
        "m_revision": 0,        # Revision
        "m_build": 75689,       # Build number
        "m_baseBuild": 75689    # Base build (used to select protocol decoder)
    },
    "m_type": 2,                 # Replay type
    "m_elapsedGameLoops": 8886,  # Total game loops (same as game_duration_loops)
    "m_useScaledTime": true,     # Whether game uses scaled time
    "m_dataBuildNum": 75689,     # Data build number
    "m_ngdpRootKey": {...},      # CDN key for game data
    "m_ngdpRootKeyIsDevData": false
}
```

### 5b. `replay.details` (decoded via `decode_replay_details`)

```python
{
    "m_playerList": [
        {
            "m_name": b'VeTerran_another',   # Player name (bytes)
            "m_toon": {                       # Battle.net identity
                "m_region": 0, "m_programId": b'\x00\x00\x00\x00',
                "m_realm": 0, "m_id": 0
            },
            "m_race": b'Terran',             # Full race name (bytes)
            "m_color": {"m_a": 255, "m_r": 180, "m_g": 20, "m_b": 30},  # Player color
            "m_control": 2,                   # Control type
            "m_teamId": 0,                    # Team ID (0-indexed)
            "m_handicap": 100,                # Handicap percentage
            "m_observe": 0,                   # 0=player, 1=observer
            "m_result": 1,                    # 1=Victory, 2=Defeat
            "m_workingSetSlotId": null,
            "m_hero": b''
        },
        # ... player 2
    ],
    "m_title": b'Persephone AIE',            # Human-readable map name
    "m_difficulty": b'',                      # Game difficulty string
    "m_thumbnail": {"m_file": b'Minimap.tga'},
    "m_isBlizzardMap": false,                 # Whether it's an official Blizzard map
    "m_timeUTC": 134021650307205200,          # Windows FILETIME (100ns since 1601-01-01)
    "m_timeLocalOffset": 0,                   # Local time offset from UTC
    "m_mapFileName": b'PersephoneAIE_v4.SC2Map',  # Actual map filename
    "m_gameSpeed": 4,                         # 0=Slower, 1=Slow, 2=Normal, 3=Fast, 4=Faster
    "m_defaultDifficulty": 3,
    "m_modPaths": [b'Mods/Liberty.SC2Mod', b'Mods/Swarm.SC2Mod', b'Mods/Void.SC2Mod'],
    "m_campaignIndex": 0,
    "m_miniSave": false,
    "m_disableRecoverGame": false
}
```

**m_timeUTC conversion** (Windows FILETIME to Python datetime):
```python
import datetime
EPOCH_OFFSET = 116444736000000000  # 1601->1970 in 100ns intervals
unix_timestamp = (m_timeUTC - EPOCH_OFFSET) / 10_000_000
dt = datetime.datetime.fromtimestamp(unix_timestamp, tz=datetime.timezone.utc)
# e.g., "2025-09-12T15:37:10.720520+00:00"
```

### 5c. `replay.initData` (decoded via `decode_replay_initdata`)

Contains `m_syncLobbyState` with three key sub-objects:

**`m_gameDescription`** (the most useful):
```python
{
    "m_mapSizeX": 160,           # MAP WIDTH in game tiles
    "m_mapSizeY": 184,           # MAP HEIGHT in game tiles
    "m_gameSpeed": 4,            # 0-4 (Slower to Faster)
    "m_gameType": 0,             # Game type (see attributes for "1v1" etc.)
    "m_maxUsers": 2,
    "m_maxObservers": 14,
    "m_maxPlayers": 2,
    "m_maxTeams": 2,
    "m_mapFileName": "PersephoneAIE_v4.SC2Map",
    "m_mapAuthorName": "",
    "m_isBlizzardMap": false,
    "m_isPremadeFFA": false,
    "m_isCoopMode": false,
    "m_isRealtimeMode": false,
    "m_gameOptions": {
        "m_lockTeams": false,
        "m_teamsTogether": false,
        "m_advancedSharedControl": false,
        "m_randomRaces": false,
        "m_battleNet": false,       # Whether played on Battle.net
        "m_amm": false,             # Automatic matchmaking (ranked)
        "m_competitive": false,     # Competitive mode
        "m_practice": false,
        "m_cooperative": false,
        "m_noVictoryOrDefeat": false,
        "m_fog": 0,                 # Fog of war setting
        "m_observers": 0,
        "m_userDifficulty": 0,
        "m_clientDebugFlags": 0,
        "m_buildCoachEnabled": false
    },
    "m_mapFileSyncChecksum": 2392464063,
    "m_randomValue": 3299906529
}
```

**`m_lobbyState`** (less useful, mostly redundant):
```python
{
    "m_phase": 0,
    "m_maxUsers": 2,
    "m_maxObservers": 14,
    "m_isSinglePlayer": false,
    "m_gameDuration": 0,
    "m_randomSeed": ...,
    "m_slots": [...]   # 16 slots with detailed player info, rewards, toon handles, etc.
}
```

### 5d. `replay.gamemetadata.json` (embedded JSON, always present)

```json
{
    "Title": "Persephone AIE",
    "MapName": "PersephoneAIE_v4.SC2Map",
    "GameVersion": "4.10.0.75689",
    "DataBuild": "75689",
    "DataVersion": "B89B5D6FA7CBF6452E721311BFBC6CB2",
    "BaseBuild": "Base75689",
    "Duration": 555,
    "Players": [
        {
            "PlayerID": 1,
            "APM": 4063.0,
            "Result": "Win",
            "SelectedRace": "Terr",
            "AssignedRace": "Terr"
        },
        {
            "PlayerID": 2,
            "APM": 2797.0,
            "Result": "Loss",
            "SelectedRace": "Prot",
            "AssignedRace": "Prot"
        }
    ]
}
```

Note: `Duration` here is in real-time seconds. `IsNotAvailable` may appear in some replays (seen in pro replays).

### 5e. `replay.attributes.events` (decoded via `decode_replay_attributes_events`)

Contains attribute key-value pairs scoped by player ID. Notable attributes in scope `16` (global):

| attrid | Value example | Meaning |
|--------|---------------|---------|
| 3000 | `b'Fasr'` | Game speed ("Fasr" = Faster) |
| 2001 | `b'1v1'` | Game type / format |
| 3009 | `b'Priv'` | Game privacy (Private/Public) |
| 2000 | `b't2'` | Number of teams |
| 4000 | `b'NoMH'` | Map hiding disabled |

Per-player attributes (scope `1` and `2`):

| attrid | Value example | Meaning |
|--------|---------------|---------|
| 500 | `b'Humn'` | Player type (Human/Comp) |
| 3001 | `b'Prot'` | Race |
| 3007 | `b'Part'` | Participant type |
| 3004 | `b'Medi'` | Difficulty (for AI) |

**Note**: Attributes events may be empty (0 bytes) for bot/AI replays. Present for human ladder/custom replays.

---

## Research Question 6: Player Statistics from Tracker Events

### Answer: YES, comprehensive end-of-game stats available

The last `SPlayerStatsEvent` for each player contains final economy and military statistics. These events are emitted every ~160 game loops, so the last one is very close to end-of-game.

**All fields in `SPlayerStatsEvent.m_stats`** (from actual replay data):

| Field | Example value | Description |
|-------|--------------|-------------|
| `m_scoreValueMineralsCurrent` | 11 | Current mineral bank |
| `m_scoreValueVespeneCurrent` | 563 | Current vespene bank |
| `m_scoreValueFoodUsed` | 221184 | Supply used (fixed-point, /4096) |
| `m_scoreValueFoodMade` | 258048 | Supply cap (fixed-point, /4096) |
| `m_scoreValueMineralsCollectionRate` | 1259 | Mineral income rate |
| `m_scoreValueVespeneCollectionRate` | 335 | Vespene income rate |
| `m_scoreValueWorkersActiveCount` | 30 | Active worker count |
| `m_scoreValueMineralsUsedCurrentArmy` | 925 | Minerals invested in army (alive) |
| `m_scoreValueMineralsUsedCurrentEconomy` | 2800 | Minerals invested in economy (alive) |
| `m_scoreValueMineralsUsedCurrentTechnology` | 850 | Minerals invested in tech (alive) |
| `m_scoreValueMineralsUsedInProgressArmy` | 225 | Minerals in queued army units |
| `m_scoreValueMineralsUsedInProgressEconomy` | 550 | Minerals in queued economy |
| `m_scoreValueMineralsUsedInProgressTechnology` | 0 | Minerals in queued tech |
| `m_scoreValueMineralsUsedActiveForces` | 925 | Active army mineral value |
| `m_scoreValueMineralsLostArmy` | 1050 | Minerals lost in army |
| `m_scoreValueMineralsLostEconomy` | 350 | Minerals lost in economy |
| `m_scoreValueMineralsLostTechnology` | -150 | Minerals lost in tech |
| `m_scoreValueMineralsKilledArmy` | 300 | Enemy army minerals killed |
| `m_scoreValueMineralsKilledEconomy` | 1500 | Enemy economy minerals killed |
| `m_scoreValueMineralsKilledTechnology` | 0 | Enemy tech minerals killed |
| `m_scoreValueMineralsFriendlyFireArmy` | 0 | Friendly fire army minerals |
| `m_scoreValueMineralsFriendlyFireEconomy` | 400 | Friendly fire economy (e.g., sacrificed) |
| `m_scoreValueMineralsFriendlyFireTechnology` | 200 | Friendly fire tech minerals |
| `m_scoreValueVespeneUsedCurrentArmy` | 450 | (Same pattern for vespene...) |
| `m_scoreValueVespeneUsedCurrentEconomy` | 0 | |
| `m_scoreValueVespeneUsedCurrentTechnology` | 275 | |
| `m_scoreValueVespeneUsedInProgressArmy` | 175 | |
| `m_scoreValueVespeneUsedInProgressEconomy` | 0 | |
| `m_scoreValueVespeneUsedInProgressTechnology` | 0 | |
| `m_scoreValueVespeneUsedActiveForces` | 450 | |
| `m_scoreValueVespeneLostArmy` | 175 | |
| `m_scoreValueVespeneLostEconomy` | 0 | |
| `m_scoreValueVespeneLostTechnology` | 0 | |
| `m_scoreValueVespeneKilledArmy` | 0 | |
| `m_scoreValueVespeneKilledEconomy` | 0 | |
| `m_scoreValueVespeneKilledTechnology` | 0 | |
| `m_scoreValueVespeneFriendlyFireArmy` | 0 | |
| `m_scoreValueVespeneFriendlyFireEconomy` | 0 | |
| `m_scoreValueVespeneFriendlyFireTechnology` | 0 | |

**Tracker event types available** (all from `replay.tracker.events`):
- `SPlayerSetupEvent` -- Player ID/slot mapping at game start
- `SPlayerStatsEvent` -- Economy snapshots every ~160 loops
- `SUnitBornEvent` -- Unit spawned
- `SUnitDiedEvent` -- Unit died
- `SUnitDoneEvent` -- Building/unit completed
- `SUnitInitEvent` -- Building/unit started (queued)
- `SUnitPositionsEvent` -- Unit position updates
- `SUnitTypeChangeEvent` -- Unit morph/transform
- `SUpgradeEvent` -- Upgrade completed

**Currently in pipeline**: Only 6 fields from `SPlayerStatsEvent` are used (via `economy_extractor.py`). End-of-game aggregate stats are NOT extracted.

---

## Research Question 7: Current Pipeline Metadata Dict

### Answer: 7 fields, most from ResponseReplayInfo

The metadata dict is built at `src_new/extraction/replay_loader.py:170-188`:

```python
metadata = {
    'map_name': str,                    # info_proto.map_name (human-readable)
    'game_duration_loops': int,         # info_proto.game_duration_loops
    'game_duration_seconds': float,     # computed: game_duration_loops / 22.4
    'num_players': int,                 # len(info_proto.player_info)
    'players': [                        # list of player dicts
        {
            'player_id': int,           # loop index + 1 (NOT from proto)
            'player_name': str,         # player_info.player_info.player_name
            'race': str,                # Race.Name(player_info.player_info.race_actual)
            'apm': float,              # player_info.player_apm
            'mmr': int,                 # player_info.player_mmr
            'result': str,              # Result.Name(player_info.player_result.result)
        }
    ]
}
```

**Total fields**: 5 top-level + 6 per player = 17 fields for a 2-player game.

**What is NOT saved but could be**:
- Game version (available from `info_proto.game_version`)
- Data build / base build (available from `info_proto.data_build` / `info_proto.base_build`)
- Map dimensions (available from s2protocol initdata)
- Game speed (available from s2protocol details/initdata)
- Game timestamp (available from s2protocol details `m_timeUTC`)
- Player type (Human/AI) (available from `player_info.player_info.type`)
- Race requested vs actual (available from `player_info.player_info.race_requested`)
- Map filename (available from s2protocol details/gamemetadata)
- End-of-game stats (available from last SPlayerStatsEvent per player)
- Is Blizzard map (available from s2protocol details)

---

## Recommendations

### Priority 1: High Value, Low Complexity (add to existing metadata dict)

These fields are already available on the `info_proto` object that is already being read. Zero additional I/O:

| Field | Source | Access code |
|-------|--------|------------|
| `game_version` | `ResponseReplayInfo` | `info_proto.game_version` |
| `data_build` | `ResponseReplayInfo` | `info_proto.data_build` |
| `base_build` | `ResponseReplayInfo` | `info_proto.base_build` |
| `game_duration_seconds` (native) | `ResponseReplayInfo` | `info_proto.game_duration_seconds` |
| `player_type` | `PlayerInfo` | `PlayerType.Name(player_info.player_info.type)` |
| `race_requested` | `PlayerInfo` | `Race.Name(player_info.player_info.race_requested)` |

### Priority 2: High Value, Low-Medium Complexity (s2protocol, no engine)

These require parsing the MPQ archive with s2protocol, which the pipeline already does for economy extraction. The archive open can be shared:

| Field | Source | Section |
|-------|--------|---------|
| `map_width` | `initdata['m_syncLobbyState']['m_gameDescription']['m_mapSizeX']` | `replay.initData` |
| `map_height` | `initdata['m_syncLobbyState']['m_gameDescription']['m_mapSizeY']` | `replay.initData` |
| `game_speed` | `details['m_gameSpeed']` (int 0-4) | `replay.details` |
| `game_timestamp_utc` | `details['m_timeUTC']` (Windows FILETIME -> ISO 8601) | `replay.details` |
| `is_blizzard_map` | `details['m_isBlizzardMap']` | `replay.details` |
| `map_file_name` | `details['m_mapFileName']` (bytes -> str) | `replay.details` |

### Priority 3: Medium Value, Medium Complexity (end-of-game stats)

Requires iterating tracker events to collect the last `SPlayerStatsEvent` per player. Since `economy_extractor.py` already iterates all tracker events, this can be done in the same pass:

| Field | Source |
|-------|--------|
| `end_game_minerals` | Last `SPlayerStatsEvent.m_stats.m_scoreValueMineralsCurrent` |
| `end_game_vespene` | Last `SPlayerStatsEvent.m_stats.m_scoreValueVespeneCurrent` |
| `end_game_workers_active` | Last `SPlayerStatsEvent.m_stats.m_scoreValueWorkersActiveCount` |
| `total_minerals_killed` | Sum of `m_scoreValueMineralsKilledArmy/Economy/Technology` |
| `total_minerals_lost` | Sum of `m_scoreValueMineralsLostArmy/Economy/Technology` |
| `army_value_minerals` | `m_scoreValueMineralsUsedActiveForces` |
| `army_value_vespene` | `m_scoreValueVespeneUsedActiveForces` |

### Priority 4: Lower Value, Available If Needed

| Field | Source | Notes |
|-------|--------|-------|
| `game_options.m_amm` | initdata | Automatic matchmaking flag |
| `game_options.m_competitive` | initdata | Competitive flag |
| `game_options.m_battleNet` | initdata | Battle.net game flag |
| `m_isCoopMode` | initdata | Coop mode flag |
| `m_isPremadeFFA` | initdata | FFA mode flag |
| `local_map_path` | ResponseReplayInfo | Local path (not portable) |
| `m_toonHandle` | lobby slots | Battle.net player identity |
| Player colors | details `m_color` | RGBA player colors |
| `m_handicap` | details | Player handicap setting |

### Priority 5: Available via `controller.game_info()` (after start_replay only)

These require an additional API call after the replay is already running. Most useful for spatial data:

| Field | Source | Notes |
|-------|--------|-------|
| `playable_area` | `start_raw.playable_area` | RectangleI bounds |
| `start_locations` | `start_raw.start_locations` | Spawn points (Point2D list) |
| `pathing_grid` | `start_raw.pathing_grid` | Binary pathability grid (large) |
| `placement_grid` | `start_raw.placement_grid` | Binary buildability grid (large) |
| `terrain_height` | `start_raw.terrain_height` | Height map (large) |

---

## Implementation Notes

### Shared MPQ Archive Access

The `economy_extractor.py` already opens the replay as an MPQ archive and decodes the header. The same archive instance can be reused to decode `replay.details` and `replay.initData` without re-opening the file. Suggested approach:

```python
archive = mpyq.MPQArchive(replay_path)
header_content = archive.header['user_data_header']['content']
header = versions.latest().decode_replay_header(header_content)
base_build = header['m_version']['m_baseBuild']
protocol = versions.build(base_build)

# All three can use the same archive + protocol
details = protocol.decode_replay_details(archive.read_file('replay.details'))
initdata = protocol.decode_replay_initdata(archive.read_file('replay.initData'))
tracker_events = protocol.decode_replay_tracker_events(archive.read_file('replay.tracker.events'))
```

### Game Speed Enum Mapping

```python
GAME_SPEED_NAMES = {0: 'Slower', 1: 'Slow', 2: 'Normal', 3: 'Fast', 4: 'Faster'}
```

Standard ladder games are always speed 4 (Faster). The 22.4 game-loops-per-second constant applies specifically to "Faster" speed.

### Timestamp Conversion

```python
import datetime

def filetime_to_iso(filetime_value):
    """Convert Windows FILETIME (100ns since 1601-01-01) to ISO 8601 string."""
    EPOCH_OFFSET = 116444736000000000
    unix_timestamp = (filetime_value - EPOCH_OFFSET) / 10_000_000
    dt = datetime.datetime.fromtimestamp(unix_timestamp, tz=datetime.timezone.utc)
    return dt.isoformat()
```

### Fixed-Point Supply Values

Supply values in `SPlayerStatsEvent` are stored as fixed-point integers multiplied by 4096. Divide by 4096 to get the real value:

```python
supply_used = event['m_stats']['m_scoreValueFoodUsed'] / 4096  # e.g., 221184 / 4096 = 54.0
```

---

## Files Referenced

| File | Role |
|------|------|
| `src_new/pipeline/replay_loader.py` | Low-level SC2 controller interface; calls `controller.replay_info()`, `controller.start_replay()` |
| `src_new/extraction/replay_loader.py` | High-level wrapper; builds metadata dict at lines 170-188 |
| `src_new/extractors/economy_extractor.py` | s2protocol MPQ parsing for tracker events |
| `src_new/pipeline/extraction_pipeline.py` | Orchestrates pipeline; writes schema JSON at line 397 |
| `src_new/extraction/schema_manager.py` | Schema save/load (current JSON output) |
| `.venv-3_11/Lib/site-packages/s2clientprotocol/sc2api_pb2.py` | Proto definitions for ResponseReplayInfo, PlayerInfoExtra, ResponseGameInfo, etc. |
| `.venv-3_11/Lib/site-packages/s2clientprotocol/raw_pb2.py` | Proto definitions for StartRaw, Size2DI |
| `.venv-3_11/Lib/site-packages/s2clientprotocol/common_pb2.py` | Proto definitions for Size2DI, PointI, RectangleI, Point2D |
