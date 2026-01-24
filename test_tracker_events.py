"""
Test sc2reader with tracker events only (load_level=1)
This avoids the game events parser which fails on bot replays
"""
# Apply patch BEFORE importing/using sc2reader functionality
import sc2reader_patch

import sc2reader
from collections import defaultdict

# Test bot replays
test_replays = [
    "replays/1_basic_bot_vs_loser_bot.SC2Replay",
    "replays/4533040_what_why_PylonAIE_v4.SC2Replay",
]

for replay_path in test_replays:
    print(f"\n{'='*80}")
    print(f"Testing: {replay_path}")
    print(f"{'='*80}")

    try:
        # Load with tracker events only (load_level=1) - this is what we need!
        print("Loading with load_level=1 (tracker events only)...")
        replay = sc2reader.load_replay(replay_path, load_level=1)

        print(f"[OK] SUCCESS!")
        print(f"\nReplay Info:")
        print(f"  - Map: {replay.map_name}")
        print(f"  - Duration: {replay.game_length}")
        print(f"  - Region: {replay.region}")
        print(f"  - Frames: {replay.frames}")
        print(f"  - Expansion: {replay.expansion}")

        print(f"\nPlayers: {len(replay.players)}")
        for player in replay.players:
            print(f"  - {player.name} ({player.pick_race}) - {player.result}")

        print(f"\nTracker Events: {len(replay.tracker_events)}")

        # Analyze events to see what we can extract
        event_types = defaultdict(int)
        unit_born_events = []
        unit_died_events = []
        upgrade_events = []
        player_stats_events = []

        for event in replay.tracker_events:
            event_name = event.name
            event_types[event_name] += 1

            if 'UnitBorn' in event_name or 'UnitInit' in event_name:
                unit_born_events.append(event)
            elif 'UnitDied' in event_name:
                unit_died_events.append(event)
            elif 'Upgrade' in event_name:
                upgrade_events.append(event)
            elif 'PlayerStats' in event_name:
                player_stats_events.append(event)

        print(f"\nEvent Type Summary:")
        for event_type, count in sorted(event_types.items()):
            print(f"  - {event_type}: {count}")

        print(f"\nData Extraction Results:")
        print(f"  - Units born/created: {len(unit_born_events)}")
        print(f"  - Units died: {len(unit_died_events)}")
        print(f"  - Upgrade events: {len(upgrade_events)}")
        print(f"  - Player stats snapshots: {len(player_stats_events)}")

        # Sample unit born event
        if unit_born_events:
            print(f"\nSample Unit Born Event:")
            event = unit_born_events[0]
            print(f"  - Frame: {event.frame}")
            print(f"  - Unit ID: {event.unit_id}")
            if hasattr(event, 'unit_type_name'):
                print(f"  - Unit Type: {event.unit_type_name}")
            if hasattr(event, 'control_pid'):
                print(f"  - Owner: Player {event.control_pid}")
            if hasattr(event, 'x') and hasattr(event, 'y'):
                print(f"  - Position: ({event.x}, {event.y})")

        # Sample unit died event
        if unit_died_events:
            print(f"\nSample Unit Died Event:")
            event = unit_died_events[0]
            print(f"  - Frame: {event.frame}")
            print(f"  - Unit ID: {event.unit_id}")
            if hasattr(event, 'killer_pid'):
                print(f"  - Killer: Player {event.killer_pid}")

        # Sample upgrade event
        if upgrade_events:
            print(f"\nSample Upgrade Event:")
            event = upgrade_events[0]
            print(f"  - Frame: {event.frame}")
            if hasattr(event, 'upgrade_type_name'):
                print(f"  - Upgrade: {event.upgrade_type_name}")
            if hasattr(event, 'player_id'):
                print(f"  - Player: {event.player_id}")

        # Sample player stats
        if player_stats_events:
            print(f"\nSample Player Stats Event:")
            event = player_stats_events[0]
            print(f"  - Frame: {event.frame}")
            if hasattr(event, 'player_id'):
                print(f"  - Player: {event.player_id}")
            if hasattr(event, 'minerals_current'):
                print(f"  - Minerals: {event.minerals_current}")
            if hasattr(event, 'vespene_current'):
                print(f"  - Vespene: {event.vespene_current}")
            if hasattr(event, 'food_used'):
                print(f"  - Supply: {event.food_used}/{event.food_made}")

        print(f"\n[OK] Successfully extracted tracker events from bot replay!")

    except Exception as e:
        print(f"[FAIL] Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("Tracker events testing complete!")
print(f"{'='*80}")
