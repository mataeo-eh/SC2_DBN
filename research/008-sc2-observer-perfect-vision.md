# 008 - SC2 Observer Mode: Perfect Information Replay Extraction

## 1. Executive Summary

The current extraction pipeline uses a **two-pass replay approach** to extract complete game state: Pass A observes from player 1's perspective (getting correct P1 economy + all units via `disable_fog=True`), then Pass B replays from player 2's perspective solely to patch P2's economy and upgrade data. This is necessary because `player_common` (minerals, vespene, supply, workers) and `score_details` (collection rates) are **perspective-dependent** -- they always reflect the `observed_player_id`, not a global view. The core question is whether a true "observer mode" (e.g., `observed_player_id=0`) exists that would provide both players' economy data in a single pass.

**Key finding: There is no true observer `observed_player_id=0` mode in the SC2 client protocol for replays.** The `observed_player_id` field in `RequestStartReplay` is an `int32` that must be set to a valid player ID (1 or 2 in a standard 1v1). Setting it to 0 will result in an error or undefined behavior. The `player_common` and `score` fields in `ResponseObservation` are always scoped to a single player perspective. The `raw_data.units` list, however, **does** contain all players' units when `disable_fog=True` is set (each unit has an `owner` field), which is why the current pipeline can extract unit data for both players in a single pass.

**Recommended approach:** Rather than trying to achieve single-pass extraction (which the protocol does not support for economy data), the best optimization is to (a) keep the current two-pass approach for game engine observations, or (b) use `s2protocol` tracker events (`SPlayerStatsEvent`) as a supplementary source for per-player economy data, which provides both players' economy snapshots without requiring the game engine at all. A hybrid approach combining game engine unit extraction with `s2protocol` tracker event economy data could eliminate Pass B entirely.

---

## 2. SC2 Client Protocol Analysis

### 2.1 RequestStartReplay Message

The `RequestStartReplay` protobuf message (defined in `sc2api.proto`) has these relevant fields:

```protobuf
message RequestStartReplay {
  oneof replay {
    string replay_path = 1;
    bytes replay_data = 5;
  }
  optional bytes map_data = 6;
  optional int32 observed_player_id = 2;  // Player perspective (1 or 2)
  optional InterfaceOptions options = 3;
  optional bool disable_fog = 4;          // Disable fog of war
  optional bool realtime = 7;
  optional bool record_replay = 8;
}
```

**Critical fields:**

- **`observed_player_id`**: Specifies which player's perspective to use. Must be 1 or 2 for a standard 1v1 game. There is **no observer value** (0 or otherwise) that provides a neutral/global perspective. The SC2 game engine always renders the observation from a specific player's viewpoint.

- **`disable_fog`**: When `true`, removes fog of war so that all units on the map are visible regardless of the observed player's actual vision. This affects `raw_data.units` -- all units from all players become visible with full attribute data. However, `player_common` and `score` remain scoped to the `observed_player_id`.

### 2.2 InterfaceOptions

```protobuf
message InterfaceOptions {
  optional bool raw = 1;                    // Enable raw data access
  optional bool score = 2;                  // Enable score information
  optional SpatialCameraSetup feature_layer = 3;
  optional SpatialCameraSetup render = 4;
  optional bool show_cloaked = 5;           // Show cloaked units
  optional bool show_burrowed_shadows = 6;  // Show burrowed units
  optional bool show_placeholders = 7;      // Show queued buildings
  optional bool raw_affects_selection = 8;
  optional bool raw_crop_to_playable_area = 9;
}
```

The `show_cloaked`, `show_burrowed_shadows`, and `show_placeholders` options provide additional unit visibility in the raw data, complementing `disable_fog`.

### 2.3 ResponseObservation Structure

```protobuf
message ResponseObservation {
  repeated Action actions = 1;
  repeated ActionError action_errors = 2;
  optional Observation observation = 3;
  repeated PlayerResult player_result = 4;  // Populated when game ends
  repeated ChatReceived chat = 5;
}
```

Within `Observation`:

```protobuf
message Observation {
  optional uint32 game_loop = 9;
  optional PlayerCommon player_common = 1;     // PERSPECTIVE-DEPENDENT
  repeated Alert alerts = 10;
  repeated AvailableAbility abilities = 3;
  optional Score score = 6;                     // PERSPECTIVE-DEPENDENT
  optional ObservationRaw raw_data = 7;         // Units for ALL players (with disable_fog)
  optional ObservationFeatureLayer feature_layer = 8;
  optional ObservationRender render_data = 5;
  optional ObservationUI ui_data = 11;
}
```

### 2.4 What Is Perspective-Dependent vs. Global

| Data Source | Perspective-Dependent? | Notes |
|---|---|---|
| `player_common.minerals` | YES | Always the observed player's minerals |
| `player_common.vespene` | YES | Always the observed player's vespene |
| `player_common.food_used` | YES | Always the observed player's supply |
| `player_common.food_cap` | YES | Always the observed player's supply cap |
| `player_common.food_workers` | YES | Always the observed player's worker count |
| `player_common.idle_worker_count` | YES | Always the observed player's idle workers |
| `player_common.army_count` | YES | Always the observed player's army count |
| `score.score_details.*` | YES | All score details are for the observed player |
| `raw_data.units` | NO (with disable_fog) | Contains ALL players' units, each with `owner` field |
| `raw_data.effects` | NO | Global effects visible to observer |
| `raw_data.player.upgrade_ids` | YES | Upgrades for the observed player only |
| `raw_data.event.dead_units` | NO (with disable_fog) | Global death events |

### 2.5 disable_fog vs. Observer Perspective

- **`disable_fog=True`**: Removes visibility restrictions on `raw_data.units`. All units on the map are included with full data (health, position, orders, etc.), regardless of whether the observed player could actually see them. However, `player_common` and `score` still reflect only the observed player.

- **There is no "neutral observer" perspective**: The SC2 engine always runs the observation from a player's viewpoint. In the in-game replay viewer, the "Everyone" perspective is a UI-level feature that switches between views -- it is not a single unified observation. The API does not replicate this.

---

## 3. pysc2 Implementation

### 3.1 How pysc2 Handles Replay Observation

pysc2 wraps the s2clientprotocol and provides a Python interface. The key classes and methods:

- **`run_configs.get()`**: Gets the SC2 run configuration for the current platform.
- **`run_config.start()`**: Starts an SC2 instance, returns a controller context manager.
- **`controller.replay_info(replay_data)`**: Gets `ResponseReplayInfo` metadata.
- **`controller.start_replay(RequestStartReplay)`**: Starts replay playback.
- **`controller.step(count)`**: Advances the replay by `count` game loops.
- **`controller.observe()`**: Returns `ResponseObservation` with current game state.

### 3.2 Current Pipeline Usage (from replay_loader.py)

```python
from s2clientprotocol import sc2api_pb2 as sc_pb

# Interface configuration
interface = sc_pb.InterfaceOptions(
    raw=True,
    score=True,
    show_cloaked=True,
    show_burrowed_shadows=True,
    show_placeholders=True,
)

# Start replay from player 1's perspective with fog disabled
replay_request = sc_pb.RequestStartReplay(
    replay_data=replay_data,
    options=interface,
    observed_player_id=1,       # Must be 1 or 2
    disable_fog=True,           # See all units
)
controller.start_replay(replay_request)

# Observe
obs = controller.observe()

# Units for ALL players (because disable_fog=True)
for unit in obs.observation.raw_data.units:
    print(f"Unit owner={unit.owner}, type={unit.unit_type}")
    # unit.owner == 1 for player 1, == 2 for player 2

# Economy for OBSERVED player ONLY
pc = obs.observation.player_common
print(f"Minerals: {pc.minerals}")  # This is player 1's minerals only
```

### 3.3 pysc2 Does NOT Support observed_player_id=0

Looking at pysc2's source code and tests (e.g., `replay_obs_test.py`, `replay_actions.py`, `sc2_env.py`):

- `observed_player_id` is always set to a specific player (1 or 2).
- The `--observed_player` flag defaults to 1.
- There is no special handling for value 0.
- The SC2 engine will reject or produce undefined behavior with `observed_player_id=0`.

### 3.4 pysc2 Configuration for Full Map Vision

The closest to "perfect information" in pysc2:

```python
interface = sc_pb.InterfaceOptions(
    raw=True,                     # Raw unit data
    score=True,                   # Score/economy data
    show_cloaked=True,            # Reveal cloaked units
    show_burrowed_shadows=True,   # Reveal burrowed units
    show_placeholders=True,       # Show queued buildings
)

request = sc_pb.RequestStartReplay(
    replay_data=replay_data,
    options=interface,
    observed_player_id=1,  # Still must pick a player
    disable_fog=True,      # Remove fog of war
)
```

This gives:
- All units from both players with full attributes (via `raw_data.units`)
- Economy/score data for player 1 only (via `player_common` and `score`)
- Upgrades for player 1 only (via `raw_data.player.upgrade_ids`)

---

## 4. Raw API Approach

### 4.1 Direct s2clientprotocol Usage

If pysc2 is insufficient, you can use the raw protobuf API over a websocket connection. This is what pysc2 does internally, but direct usage gives more control.

However, the fundamental limitation remains: **`player_common` and `score` are always per-player**. No amount of raw API manipulation changes this because the SC2 game engine itself only computes these values for the observed player.

### 4.2 ResponseObservation with All Players' Unit Data

With `disable_fog=True` and `raw=True`:

```python
obs = controller.observe()

# raw_data.units contains ALL units from ALL players
for unit in obs.observation.raw_data.units:
    # Key fields available for every unit:
    unit.display_type      # Visible, Snapshot, Hidden, Placeholder
    unit.alliance          # Self(1), Ally(2), Neutral(3), Enemy(4)
    unit.tag               # Persistent unique ID (uint64)
    unit.unit_type         # Unit type ID
    unit.owner             # Player ID (1 or 2) - THIS is the key field
    unit.pos               # Position {x, y, z}
    unit.facing            # Direction facing
    unit.radius            # Unit radius
    unit.build_progress    # 0.0 to 1.0
    unit.cloak             # Cloak state
    unit.is_flying         # Whether unit is flying
    unit.is_burrowed       # Whether unit is burrowed
    unit.health            # Current health
    unit.health_max        # Max health
    unit.shield            # Current shields (Protoss)
    unit.shield_max        # Max shields
    unit.energy            # Current energy (casters)
    unit.energy_max        # Max energy
    unit.mineral_contents  # For mineral fields
    unit.vespene_contents  # For geysers
    unit.weapon_cooldown   # Weapon cooldown
    unit.orders            # Current orders
    unit.buff_ids          # Active buffs
    unit.assigned_harvesters   # Workers assigned
    unit.ideal_harvesters      # Ideal workers
    unit.attack_upgrade_level  # Attack upgrades
    unit.armor_upgrade_level   # Armor upgrades
    unit.shield_upgrade_level  # Shield upgrades
    unit.is_hallucination      # Hallucination flag
    unit.cargo_space_taken     # Cargo used
    unit.cargo_space_max       # Cargo capacity
```

### 4.3 Per-Player Economy: Why It Requires Two Passes

The `PlayerCommon` message in `sc2api.proto`:

```protobuf
message PlayerCommon {
  optional uint32 player_id = 1;
  optional uint32 minerals = 2;
  optional uint32 vespene = 3;
  optional uint32 food_used = 4;
  optional uint32 food_cap = 5;
  optional uint32 food_army = 6;
  optional uint32 food_workers = 7;
  optional uint32 idle_worker_count = 8;
  optional uint32 army_count = 9;
  optional uint32 warp_gate_count = 10;
  optional uint32 larva_count = 11;
}
```

This is a **single** message, not a repeated field. It does not contain data for multiple players. It always reflects the state of whichever player is set as `observed_player_id`.

Similarly, `raw_data.player` contains:

```protobuf
message PlayerRaw {
  repeated PowerSource power_sources = 1;
  optional Point camera = 2;
  repeated uint32 upgrade_ids = 3;  // Only the observed player's upgrades
}
```

There is **no** `repeated PlayerRaw players` -- it is a singular field for the observed player only.

---

## 5. Alternative Tools

### 5.1 s2protocol (Blizzard's Replay Parser)

**Repository**: https://github.com/Blizzard/s2protocol

s2protocol decodes SC2 replay files directly (without the game engine) into Python data structures. It provides access to:

- **Tracker events**: Including `SPlayerStatsEvent` which contains per-player economy snapshots
- **Game events**: Player actions, selections, commands
- **Details**: Player names, races, match results
- **Message events**: Chat messages

**Key advantage for economy data**: `SPlayerStatsEvent` tracker events contain economy data for **BOTH players** simultaneously, emitted at regular intervals (approximately every 160 game loops / ~7.1 seconds).

#### SPlayerStatsEvent Fields (per player)

Each event includes `m_playerId` and an `m_stats` dictionary with fields like:
- `m_scoreValueMineralsCurrent` -- Current unspent minerals
- `m_scoreValueVespeneCurrent` -- Current unspent vespene
- `m_scoreValueFoodUsed` -- Supply used (fixed-point, divide by 4096)
- `m_scoreValueFoodMade` -- Supply cap (fixed-point, divide by 4096)
- `m_scoreValueMineralsCollectionRate` -- Mineral collection rate
- `m_scoreValueVespeneCollectionRate` -- Vespene collection rate
- `m_scoreValueWorkersActiveCount` -- Active worker count
- And many more (army value, tech value, resources lost, etc.)

#### Example s2protocol Usage

```python
import mpyq
from s2protocol import versions

# Open replay
archive = mpyq.MPQArchive('replay.SC2Replay')
header = versions.latest().decode_replay_header(
    archive.header['user_data_header']['content']
)

# Get protocol version
baseBuild = header['m_version']['m_baseBuild']
protocol = versions.build(baseBuild)

# Decode tracker events
tracker_events_raw = archive.read_file('replay.tracker.events')
tracker_events = protocol.decode_replay_tracker_events(tracker_events_raw)

# Extract economy data for BOTH players
for event in tracker_events:
    if event['_event'] == 'NNet.Replay.Tracker.SPlayerStatsEvent':
        player_id = event['m_playerId']
        stats = event['m_stats']
        game_loop = event['_gameloop']

        minerals = stats['m_scoreValueMineralsCurrent']
        vespene = stats['m_scoreValueVespeneCurrent']
        food_used = stats['m_scoreValueFoodUsed'] / 4096
        food_made = stats['m_scoreValueFoodMade'] / 4096

        print(f"Loop {game_loop}, Player {player_id}: "
              f"{minerals}m, {vespene}g, {food_used}/{food_made} supply")
```

**Limitations:**
- SPlayerStatsEvent is emitted at ~160 game loop intervals, not every frame
- Does not provide precise unit positions, health, or other per-unit data
- Cannot provide ground truth unit state (only aggregated stats)
- Tracker events were introduced in version 2.0.8 and do not exist in older replays

### 5.2 sc2reader

**Repository**: https://github.com/GraylinKim/sc2reader

sc2reader is a community Python library that parses replay files. It provides:
- Player details (name, race, team, result)
- Message events (chat)
- Unit selection and hotkey events
- Resource transfers and requests

**Limitation**: sc2reader explicitly states it provides "Resource Transfers and Requests (but not collection rate or unspent totals!)". It **cannot** provide current mineral/vespene counts for either player.

### 5.3 zephyrus-sc2-parser

**Repository**: https://github.com/ZephyrBlu/zephyrus-sc2-parser

A more modern parser that combines tracker and game events to reconstruct game state. It provides:
- Resource collection rates for both players
- Unspent resources
- Unit compositions
- Game state snapshots at 5-second intervals

This could be a useful supplementary data source, though its 5-second interval is coarser than the game engine's per-frame data.

### 5.4 SC2EGSet Dataset Tools

**Repository**: https://github.com/Kaszanas/SC2_Datasets

The SC2EGSet research project processed thousands of tournament replays. Their tools use s2protocol-based parsing (not engine simulation). They note that engine-based simulation provides higher resolution data but at much higher computational cost.

---

## 6. Recommended Implementation Plan

### Option A: Hybrid Approach (Recommended)

Combine game engine extraction (for unit data) with s2protocol tracker events (for economy data) to eliminate the second replay pass.

```
Pass 1 (engine): observed_player_id=1, disable_fog=True
  - Extract ALL units for both players (via raw_data.units + owner filter)
  - Extract ALL buildings for both players
  - Extract P1 upgrades (via raw_data.player.upgrade_ids)
  - Skip economy extraction from player_common

Supplementary (no engine needed): s2protocol tracker events
  - Extract SPlayerStatsEvent for BOTH players
  - Get minerals, vespene, supply, workers, collection rates
  - Interpolate between ~160-loop intervals if needed

Pass 2 (engine): observed_player_id=2, disable_fog=True
  - Extract P2 upgrades ONLY (via raw_data.player.upgrade_ids)
  - This pass is much faster since we only need upgrade data
```

**Tradeoff**: Economy data resolution drops from per-frame to ~7-second intervals. This may or may not matter for your ML pipeline.

### Option B: Keep Two-Pass Approach (Current)

If per-frame economy data is essential, keep the current two-pass approach. Optimizations:

**Step 1**: In Pass B, extract ONLY what is needed (economy + upgrades). Skip unit extraction entirely.

**Step 2**: Consider increasing `step_size` for Pass B if frame-perfect economy alignment is not critical.

**Step 3**: Profile to determine if Pass B is actually a bottleneck. If the game engine step is the bottleneck (not the Python extraction code), then reducing Python-side work in Pass B has minimal impact.

### Option C: s2protocol-Only Economy + Single Engine Pass for Upgrades

If you can tolerate lower-resolution economy data AND can find a way to extract both players' upgrades without the engine:

**Note**: Upgrade completion events exist in s2protocol tracker events as `NNet.Replay.Tracker.SUpgradeEvent`. This contains `m_playerId` and `m_upgradeTypeName` for each upgrade completion. This means you could potentially extract upgrades from tracker events too, eliminating the need for Pass B entirely.

```
Single Pass (engine): observed_player_id=1, disable_fog=True
  - Extract ALL units + buildings for both players
  - P1 upgrades from raw_data.player.upgrade_ids (for real-time state)

No-engine supplementary:
  - Economy for BOTH players from SPlayerStatsEvent
  - Upgrades for BOTH players from SUpgradeEvent
```

This would reduce the pipeline from 2+ engine passes to a single engine pass.

---

## 7. Code Examples

### 7.1 Current Pipeline Approach (Two-Pass)

This is what the current `extraction_pipeline.py` does:

```python
# Pass A: Player 1 perspective
self.replay_loader.start_replay(controller, observed_player_id=1, disable_fog=True)
# ... iterate and extract units (both players), P1 economy, P1 upgrades

# Pass B: Player 2 perspective
self.replay_loader.start_replay(controller, observed_player_id=2, disable_fog=True)
# ... iterate and extract ONLY P2 economy and P2 upgrades
# Patch P2 data into Pass A rows
```

### 7.2 s2protocol Economy Extraction (Supplementary)

```python
import mpyq
from s2protocol import versions

def extract_economy_from_tracker(replay_path: str) -> dict:
    """
    Extract per-player economy data from s2protocol tracker events.
    Returns dict mapping (player_id, game_loop) -> economy_data.
    """
    archive = mpyq.MPQArchive(replay_path)
    header_content = archive.header['user_data_header']['content']
    header = versions.latest().decode_replay_header(header_content)

    base_build = header['m_version']['m_baseBuild']
    protocol = versions.build(base_build)

    tracker_raw = archive.read_file('replay.tracker.events')
    tracker_events = protocol.decode_replay_tracker_events(tracker_raw)

    economy_data = {}  # (player_id, game_loop) -> dict

    for event in tracker_events:
        if event['_event'] == 'NNet.Replay.Tracker.SPlayerStatsEvent':
            pid = event['m_playerId']
            gl = event['_gameloop']
            stats = event['m_stats']

            economy_data[(pid, gl)] = {
                'minerals': stats['m_scoreValueMineralsCurrent'],
                'vespene': stats['m_scoreValueVespeneCurrent'],
                'supply_used': stats['m_scoreValueFoodUsed'] / 4096,
                'supply_cap': stats['m_scoreValueFoodMade'] / 4096,
                'workers': stats['m_scoreValueWorkersActiveCount'],
                'collection_rate_minerals': stats['m_scoreValueMineralsCollectionRate'],
                'collection_rate_vespene': stats['m_scoreValueVespeneCollectionRate'],
            }

    return economy_data
```

### 7.3 s2protocol Upgrade Extraction

```python
def extract_upgrades_from_tracker(replay_path: str) -> dict:
    """
    Extract per-player upgrade completions from tracker events.
    Returns dict mapping player_id -> list of (game_loop, upgrade_name).
    """
    archive = mpyq.MPQArchive(replay_path)
    header_content = archive.header['user_data_header']['content']
    header = versions.latest().decode_replay_header(header_content)

    base_build = header['m_version']['m_baseBuild']
    protocol = versions.build(base_build)

    tracker_raw = archive.read_file('replay.tracker.events')
    tracker_events = protocol.decode_replay_tracker_events(tracker_raw)

    upgrades = {1: [], 2: []}

    for event in tracker_events:
        if event['_event'] == 'NNet.Replay.Tracker.SUpgradeEvent':
            pid = event['m_playerId']
            gl = event['_gameloop']
            upgrade_name = event['m_upgradeTypeName'].decode('utf-8')

            if pid in upgrades:
                upgrades[pid].append((gl, upgrade_name))

    return upgrades
```

### 7.4 Hybrid Pipeline Sketch

```python
class HybridExtractionPipeline:
    """
    Single engine pass + s2protocol for economy/upgrades.
    """

    def process_replay(self, replay_path, output_dir):
        # Step 1: Extract economy + upgrades from tracker events (no engine)
        economy_data = extract_economy_from_tracker(str(replay_path))
        upgrade_data = extract_upgrades_from_tracker(str(replay_path))

        # Step 2: Single engine pass for unit/building ground truth
        self.replay_loader.load_replay(replay_path)

        with self.replay_loader.start_sc2_instance() as controller:
            metadata = self.replay_loader.get_replay_info(controller)

            # Single pass: player 1 perspective with disable_fog
            self.replay_loader.start_replay(
                controller, observed_player_id=1, disable_fog=True
            )

            rows = []
            game_loop = 0
            max_loops = metadata['game_duration_loops']

            while game_loop < max_loops:
                controller.step(self.step_size)
                obs = controller.observe()

                if obs.player_result:
                    break

                game_loop = obs.observation.game_loop

                # Extract units for BOTH players (owner field distinguishes them)
                state = self.state_extractor.extract_units_and_buildings(obs, game_loop)

                # Merge economy from tracker events (nearest game_loop)
                for pid in [1, 2]:
                    econ = self._get_nearest_economy(economy_data, pid, game_loop)
                    state[f'p{pid}_economy'] = econ

                # Merge upgrades from tracker events
                for pid in [1, 2]:
                    active = self._get_active_upgrades(upgrade_data, pid, game_loop)
                    state[f'p{pid}_upgrades'] = active

                row = self.wide_table_builder.build_row(state)
                rows.append(row)

        # Write output
        # ...

    def _get_nearest_economy(self, economy_data, player_id, target_loop):
        """Find the most recent economy snapshot for this player at or before target_loop."""
        best_loop = None
        for (pid, gl) in economy_data:
            if pid == player_id and gl <= target_loop:
                if best_loop is None or gl > best_loop:
                    best_loop = gl

        if best_loop is not None:
            return economy_data[(player_id, best_loop)]
        return {}

    def _get_active_upgrades(self, upgrade_data, player_id, target_loop):
        """Get all upgrades completed at or before target_loop for this player."""
        return [
            name for (gl, name) in upgrade_data.get(player_id, [])
            if gl <= target_loop
        ]
```

---

## 8. Risks and Limitations

### 8.1 No Observer Mode in Protocol
- **Risk**: `observed_player_id=0` does not work. There is no neutral observer perspective in the API.
- **Impact**: Economy data always requires either two passes or an alternative data source.
- **Mitigation**: Use s2protocol tracker events for economy, or keep the two-pass approach.

### 8.2 s2protocol Economy Resolution
- **Risk**: `SPlayerStatsEvent` is emitted approximately every 160 game loops (~7.1 seconds at "Faster" speed). This is much coarser than per-frame data.
- **Impact**: Economy snapshots are interpolated/step-wise, not frame-accurate.
- **Mitigation**: For most ML applications, 7-second economy snapshots are sufficient. If frame-accurate economy is needed, the two-pass engine approach is required.

### 8.3 s2protocol Version Compatibility
- **Risk**: Tracker events were introduced in version 2.0.8. Very old replays may not have them.
- **Impact**: Older replays cannot use the hybrid approach.
- **Mitigation**: Fall back to two-pass engine extraction for old replays.

### 8.4 s2protocol Field Naming
- **Risk**: The `m_stats` field names in `SPlayerStatsEvent` may vary between protocol versions.
- **Impact**: Hard-coded field names may break on different replay versions.
- **Mitigation**: Use the version-specific protocol decoder (`versions.build(baseBuild)`), which handles version differences.

### 8.5 idle_worker_count Not in Tracker Events
- **Risk**: `SPlayerStatsEvent` may not include `idle_worker_count` -- this is a UI-level metric computed by the game engine.
- **Impact**: The hybrid approach may lose this field.
- **Mitigation**: Accept the loss (idle workers is less critical for ML) or keep a minimal Pass B for this specific field.

### 8.6 Performance Considerations
- **Two-pass engine approach**: ~2x the compute time for replay processing (each pass requires stepping through the entire replay in the SC2 engine).
- **Hybrid approach**: ~1x engine time + negligible s2protocol parsing time.
- **s2protocol parsing is very fast**: Parsing tracker events from a replay file takes milliseconds, compared to minutes for engine simulation.

### 8.7 raw_data.units with disable_fog Reliability
- **Confirmed working**: The current pipeline already relies on `raw_data.units` with `disable_fog=True` for both-player unit extraction in a single pass. The `owner` field on each unit reliably indicates which player owns it. This is a well-established pattern used by the community.
- **Edge case**: Some unit types (e.g., neutral minerals, destructible rocks) have `owner=0` (neutral). These should be filtered based on the extraction requirements.

### 8.8 Game Engine Availability
- **Risk**: Engine-based extraction requires a StarCraft II installation on the machine running the pipeline.
- **Impact**: Cannot run in headless cloud environments without the SC2 binary.
- **Mitigation**: The Linux headless client is available for server environments. For Windows, the retail client works.

---

## 9. Sources

### Official Blizzard Repositories
- [s2client-proto (Protocol Definitions)](https://github.com/Blizzard/s2client-proto) -- The authoritative source for all protobuf message definitions
- [sc2api.proto](https://github.com/Blizzard/s2client-proto/blob/master/s2clientprotocol/sc2api.proto) -- RequestStartReplay, ResponseObservation, PlayerCommon, InterfaceOptions definitions
- [raw.proto](https://github.com/Blizzard/s2client-proto/blob/master/s2clientprotocol/raw.proto) -- ObservationRaw, Unit, PlayerRaw definitions
- [protocol.md](https://github.com/Blizzard/s2client-proto/blob/master/docs/protocol.md) -- Protocol documentation
- [s2client-api (C++ Library)](https://github.com/Blizzard/s2client-api) -- Reference C++ implementation
- [s2client-api replay.cc example](https://github.com/Blizzard/s2client-api/blob/master/examples/replay.cc) -- C++ replay processing example
- [s2client-api replay observer](https://github.com/Blizzard/s2client-api/blob/master/src/sc2api/sc2_replay_observer.cc) -- Replay observer implementation
- [s2protocol (Replay Parser)](https://github.com/Blizzard/s2protocol) -- Blizzard's official replay decoder
- [s2protocol tutorial](https://github.com/Blizzard/s2protocol/blob/master/docs/tutorial.rst) -- Tutorial for tracker events including SPlayerStatsEvent
- [s2protocol issue #7 - Resource inaccuracies](https://github.com/Blizzard/s2protocol/issues/7) -- Known issues with resource tracking in tracker events

### DeepMind / Google
- [pysc2 (SC2 Learning Environment)](https://github.com/google-deepmind/pysc2) -- Python SC2 wrapper
- [pysc2 replay_obs_test.py](https://github.com/google-deepmind/pysc2/blob/master/pysc2/tests/replay_obs_test.py) -- Replay observation tests
- [pysc2 replay_actions.py](https://github.com/google-deepmind/pysc2/blob/master/pysc2/bin/replay_actions.py) -- Replay action extraction script
- [pysc2 sc2_env.py](https://github.com/google-deepmind/pysc2/blob/master/pysc2/env/sc2_env.py) -- SC2 environment implementation

### Community Tools
- [sc2reader](https://github.com/GraylinKim/sc2reader) -- Community replay parser (limited economy data)
- [zephyrus-sc2-parser](https://github.com/ZephyrBlu/zephyrus-sc2-parser) -- Modern replay parser with game state reconstruction
- [pysc2_DataExtract](https://github.com/sino30535/pysc2_DataExtract) -- Tutorial for pysc2 data extraction
- [pysc2-replay (narhen)](https://github.com/narhen/pysc2-replay) -- Framework for replay inspection
- [pysc2-replay (njustesen)](https://github.com/njustesen/pysc2-replay) -- Framework for replay inspection

### Research Papers and Datasets
- [SC2EGSet: StarCraft II Esport Replay and Game-state Dataset](https://www.nature.com/articles/s41597-023-02510-7) -- Large-scale replay dataset
- [SC2EGSet (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10491788/) -- Full paper with dataset design details
- [StarCraft II: A New Challenge for Reinforcement Learning](https://ar5iv.labs.arxiv.org/html/1708.04782) -- Original SC2LE paper describing observation structure
- [SC2_Datasets (GitHub)](https://github.com/Kaszanas/SC2_Datasets) -- PyTorch dataset wrappers for SC2EGSet

### API Documentation
- [SC2API Documentation](https://blizzard.github.io/s2client-api/) -- Official C++ API docs
- [SC2API ReplayObserver Class](https://blizzard.github.io/s2client-api/classsc2_1_1_replay_observer.html) -- Replay observer reference
- [SC2API Coordinator Class](https://blizzard.github.io/s2client-api/classsc2_1_1_coordinator.html) -- Coordinator reference
- [Go s2client sc2proto Package](https://pkg.go.dev/github.com/grantmd/go-s2client/sc2proto) -- Go bindings (useful for browsing generated proto docs)
- [s2protocol ReadTheDocs](https://s2protocol.readthedocs.io/en/latest/) -- s2protocol documentation
