"""
SC2 Replay Frame-by-Frame Extraction Example
Demonstrates recommended approach for extracting game state data for DBN training.

This example shows how to:
1. Load replays with sc2reader
2. Extract unit/building lifecycle events
3. Reconstruct game state at regular intervals
4. Export features in structured format

Author: Research Phase
Date: 2026-01-23
"""

import sc2reader
from collections import defaultdict
import json
from pathlib import Path
from typing import Dict, List, Any


# ============================================================================
# CONFIGURATION
# ============================================================================

INTERVAL_SECONDS = 5  # Extract state every 5 seconds
MIN_GAME_LENGTH_FRAMES = 1000  # Skip games < ~1 minute

# Unit types to ignore (map elements)
IGNORE_UNITS = {
    'MineralField', 'MineralField750', 'LabMineralField', 'LabMineralField750',
    'VespeneGeyser', 'SpacePlatformGeyser', 'RichVespeneGeyser',
    'DestructibleDebris', 'UnbuildablePlates', 'CleaningBot',
    'XelNagaTower', 'XelNagaTowerRadar'
}


# ============================================================================
# CORE EXTRACTION FUNCTIONS
# ============================================================================

def extract_unit_lifecycles(replay) -> Dict[int, Dict[str, Any]]:
    """
    Extract complete lifecycle for all units/buildings.

    Returns dict mapping unit_id -> lifecycle data with fields:
    - type: unit type name
    - player: controlling player ID
    - born_frame / init_frame: when unit appeared/started
    - done_frame: when construction completed (if applicable)
    - died_frame: when unit died (if applicable)
    - location: (x, y) coordinates
    - killer: player ID of killer (if died)
    """
    units = {}

    for event in replay.tracker_events:
        if not hasattr(event, 'unit_id'):
            continue

        unit_id = event.unit_id
        event_type = type(event).__name__

        if event_type == 'UnitBornEvent':
            # Unit spawned fully constructed
            units[unit_id] = {
                'type': event.unit_type_name,
                'player': event.control_pid,
                'born_frame': event.frame,
                'location': event.location,
                'status': 'alive'
            }

        elif event_type == 'UnitInitEvent':
            # Unit/building construction started
            units[unit_id] = {
                'type': event.unit_type_name,
                'player': event.control_pid,
                'init_frame': event.frame,
                'location': event.location,
                'status': 'constructing'
            }

        elif event_type == 'UnitDoneEvent':
            # Construction completed
            if unit_id in units:
                units[unit_id]['done_frame'] = event.frame
                units[unit_id]['status'] = 'completed'

        elif event_type == 'UnitDiedEvent':
            # Unit died or cancelled
            if unit_id in units:
                units[unit_id]['died_frame'] = event.frame
                units[unit_id]['killer'] = event.killer_pid
                units[unit_id]['status'] = 'dead'

    return units


def get_state_at_frame(
    replay,
    frame: int,
    units: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Reconstruct complete game state at specific frame.

    Returns state dict with:
    - frame: frame number
    - game_time: seconds elapsed
    - players: dict of player states
        - units: count by type
        - buildings: count by type
        - upgrades: set of completed upgrades
        - resources: minerals, vespene
        - supply: used, made
        - workers: active count
    """
    state = {
        'frame': frame,
        'game_time': frame / replay.game_fps,
        'players': {}
    }

    # Initialize player states
    for player in replay.players:
        state['players'][player.pid] = {
            'name': player.name,
            'race': player.play_race,
            'units': defaultdict(int),
            'buildings': defaultdict(int),
            'upgrades': set(),
            'resources': {'minerals': 0, 'vespene': 0},
            'supply': {'used': 0, 'made': 0},
            'workers': 0
        }

    # Count units alive at this frame
    for unit_id, unit_data in units.items():
        # Skip map elements
        if unit_data['type'] in IGNORE_UNITS:
            continue

        # Determine if unit is alive at this frame
        born_frame = unit_data.get('born_frame', unit_data.get('init_frame', 0))
        done_frame = unit_data.get('done_frame', born_frame)
        died_frame = unit_data.get('died_frame', float('inf'))

        # Unit is alive if completed and not yet dead
        if done_frame <= frame < died_frame:
            player_id = unit_data['player']
            unit_type = unit_data['type']

            # Categorize as unit or building
            if is_building(unit_type):
                state['players'][player_id]['buildings'][unit_type] += 1
            else:
                state['players'][player_id]['units'][unit_type] += 1

    # Apply all events up to this frame
    for event in replay.tracker_events:
        if event.frame > frame:
            break

        # Update player stats
        if type(event).__name__ == 'PlayerStatsEvent':
            player_id = event.pid
            if player_id in state['players']:
                state['players'][player_id]['resources'] = {
                    'minerals': event.minerals_current,
                    'vespene': event.vespene_current
                }
                state['players'][player_id]['supply'] = {
                    'used': event.food_used,
                    'made': event.food_made
                }
                state['players'][player_id]['workers'] = event.workers_active_count

        # Track upgrades
        elif type(event).__name__ == 'UpgradeCompleteEvent':
            player_id = event.pid
            if player_id in state['players']:
                state['players'][player_id]['upgrades'].add(event.upgrade_type_name)

    # Convert defaultdicts and sets to regular dicts/lists for JSON serialization
    for player_id in state['players']:
        state['players'][player_id]['units'] = dict(state['players'][player_id]['units'])
        state['players'][player_id]['buildings'] = dict(state['players'][player_id]['buildings'])
        state['players'][player_id]['upgrades'] = list(state['players'][player_id]['upgrades'])

    return state


def is_building(unit_type: str) -> bool:
    """Check if unit type is a building/structure."""
    building_keywords = [
        # Protoss
        'Nexus', 'Pylon', 'Gateway', 'WarpGate', 'Forge', 'PhotonCannon',
        'CyberneticsCore', 'ShieldBattery', 'RoboticsFacility', 'RoboticsBay',
        'Stargate', 'FleetBeacon', 'TwilightCouncil', 'TemplarArchive',
        'DarkShrine', 'Assimilator',
        # Terran
        'CommandCenter', 'OrbitalCommand', 'PlanetaryFortress', 'SupplyDepot',
        'Barracks', 'Factory', 'Starport', 'EngineeringBay', 'Armory',
        'MissileTurret', 'Bunker', 'SensorTower', 'GhostAcademy',
        'FusionCore', 'TechLab', 'Reactor', 'Refinery',
        # Zerg
        'Hatchery', 'Lair', 'Hive', 'SpawningPool', 'RoachWarren',
        'BanelingNest', 'HydraliskDen', 'LurkerDen', 'InfestationPit',
        'Spire', 'GreaterSpire', 'UltraliskCavern', 'SpineCrawler',
        'SporeCrawler', 'EvolutionChamber', 'Extractor', 'NydusNetwork',
        'NydusCanal'
    ]

    return any(keyword in unit_type for keyword in building_keywords)


def extract_replay_features(
    replay_path: str,
    interval_seconds: float = INTERVAL_SECONDS
) -> Dict[str, Any]:
    """
    Extract frame-by-frame features from a single replay.

    Returns dict with:
    - metadata: replay info (map, players, duration, etc.)
    - frames: list of state snapshots at regular intervals
    """
    # Load replay
    replay = sc2reader.load_replay(replay_path, load_level=4)

    # Validate replay
    if replay.frames < MIN_GAME_LENGTH_FRAMES:
        raise ValueError(f"Game too short: {replay.frames} frames")

    # Extract unit lifecycles
    units = extract_unit_lifecycles(replay)

    # Calculate interval in frames
    interval_frames = int(interval_seconds * replay.game_fps)

    # Extract state at each interval
    frames = []
    for frame in range(0, replay.frames, interval_frames):
        state = get_state_at_frame(replay, frame, units)
        frames.append(state)

    # Build result
    return {
        'metadata': {
            'file': str(replay_path),
            'map': replay.map_name,
            'duration': str(replay.game_length),
            'frames': replay.frames,
            'fps': replay.game_fps,
            'speed': replay.speed,
            'date': str(replay.date) if replay.date else None,
            'players': [
                {
                    'name': p.name,
                    'race': p.play_race,
                    'result': p.result,
                    'pid': p.pid
                }
                for p in replay.players
            ],
            'winner': replay.winner.name if replay.winner else None
        },
        'frames': frames
    }


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def process_replay_batch(
    replay_dir: str,
    output_dir: str,
    interval_seconds: float = INTERVAL_SECONDS,
    max_replays: int = None
) -> Dict[str, List[str]]:
    """
    Process all replays in a directory.

    Args:
        replay_dir: Directory containing .SC2Replay files
        output_dir: Directory to save extracted features
        interval_seconds: Time between state snapshots
        max_replays: Maximum number of replays to process (None = all)

    Returns:
        Dict with 'success' and 'failed' lists of replay paths
    """
    replay_dir = Path(replay_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all replay files
    replay_files = list(replay_dir.glob('*.SC2Replay'))
    if max_replays:
        replay_files = replay_files[:max_replays]

    results = {'success': [], 'failed': []}

    for i, replay_path in enumerate(replay_files, 1):
        try:
            print(f"[{i}/{len(replay_files)}] Processing {replay_path.name}...")

            # Extract features
            features = extract_replay_features(str(replay_path), interval_seconds)

            # Save to JSON
            output_file = output_dir / f"{replay_path.stem}.json"
            with open(output_file, 'w') as f:
                json.dump(features, f, indent=2)

            results['success'].append(str(replay_path))
            print(f"  ✓ Saved to {output_file}")

        except Exception as e:
            results['failed'].append(str(replay_path))
            print(f"  ✗ Error: {e}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Success: {len(results['success'])}")
    print(f"Failed:  {len(results['failed'])}")

    return results


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Process a single replay
    REPLAY_PATH = r"c:\Users\matae\OneDrive\Desktop\Coding-Projects\local-play-bootstrap-main\.venv-3_12\src\python-sc2\test\replays\20220223 - GAME 1 - Astrea vs SKillous - P vs P - Curious Minds LE.SC2Replay"

    print("Extracting features from single replay...")
    features = extract_replay_features(REPLAY_PATH, interval_seconds=5)

    print(f"\nMetadata:")
    print(f"  Map: {features['metadata']['map']}")
    print(f"  Duration: {features['metadata']['duration']}")
    print(f"  Players: {', '.join(p['name'] for p in features['metadata']['players'])}")
    print(f"  Winner: {features['metadata']['winner']}")

    print(f"\nExtracted {len(features['frames'])} state snapshots")
    print(f"\nSample frame (frame 0):")
    print(json.dumps(features['frames'][0], indent=2))

    # Example: Batch process replays
    # REPLAY_DIR = "path/to/replays"
    # OUTPUT_DIR = "path/to/output"
    # results = process_replay_batch(REPLAY_DIR, OUTPUT_DIR, max_replays=10)
