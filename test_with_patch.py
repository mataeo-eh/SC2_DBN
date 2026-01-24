"""
Test sc2reader with the monkey patch applied
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
        # Load with full data (load_level=4)
        print("Loading with load_level=4 (full data)...")
        replay = sc2reader.load_replay(replay_path, load_level=4)

        print(f"[OK] SUCCESS!")
        print(f"\nReplay Info:")
        print(f"  - Map: {replay.map_name}")
        print(f"  - Duration: {replay.game_length}")
        print(f"  - Region: {replay.region}")
        print(f"  - Game version: {replay.release_string}")
        print(f"  - Frames: {replay.frames}")

        print(f"\nPlayers: {len(replay.players)}")
        for player in replay.players:
            print(f"  - {player.name} ({player.pick_race}) - {player.result}")

        print(f"\nEvents:")
        print(f"  - Tracker events: {len(replay.tracker_events)}")
        print(f"  - Game events: {len(replay.game_events)}")
        print(f"  - Messages: {len(replay.messages)}")

        # Test extracting unit data
        print(f"\nExtracting unit lifecycle data...")
        unit_born_count = 0
        unit_died_count = 0
        building_count = 0
        upgrade_count = 0

        for event in replay.tracker_events:
            event_name = event.name
            if 'UnitBorn' in event_name or 'UnitInit' in event_name:
                unit_born_count += 1
            elif 'UnitDied' in event_name:
                unit_died_count += 1
            elif 'Upgrade' in event_name:
                upgrade_count += 1

        print(f"  - Units born/created: {unit_born_count}")
        print(f"  - Units died: {unit_died_count}")
        print(f"  - Upgrade events: {upgrade_count}")

        # Sample some events
        print(f"\nSample events (first 5):")
        for i, event in enumerate(replay.tracker_events[:5]):
            frame_time = event.frame / 22.4  # Convert frames to game seconds (22.4 fps)
            print(f"  [{i+1}] Frame {event.frame} ({frame_time:.1f}s): {event.name}")
            if hasattr(event, 'unit_type_name'):
                print(f"      Unit: {event.unit_type_name}")

        print(f"\n[OK] Successfully extracted all data from bot replay!")

    except Exception as e:
        print(f"[FAIL] Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("Patch testing complete!")
print(f"{'='*80}")
