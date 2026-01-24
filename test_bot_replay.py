"""
Test script to diagnose sc2reader issues with AI Arena bot replays
"""
import sc2reader
import traceback

# Test replays
test_replays = [
    "replays/1_basic_bot_vs_loser_bot.SC2Replay",  # Local bot match
    "replays/4533040_what_why_PylonAIE_v4.SC2Replay",  # AI Arena replay
    ".venv-3_12/src/python-sc2/test/replays/20220223 - GAME 1 - Astrea vs SKillous - P vs P - Curious Minds LE.SC2Replay",  # Human replay
]

for replay_path in test_replays:
    print(f"\n{'='*80}")
    print(f"Testing: {replay_path}")
    print(f"{'='*80}")

    try:
        # Try loading with minimal level first
        print("\n[1] Loading with load_level=0 (minimal)...")
        replay = sc2reader.load_replay(replay_path, load_level=0)
        print(f"[OK] SUCCESS - load_level=0")
        print(f"  - Map: {replay.map_name}")
        print(f"  - Duration: {replay.game_length}")
        print(f"  - Players: {len(replay.players)}")
        for player in replay.players:
            print(f"    - {player.name} ({player.play_race})")

    except Exception as e:
        print(f"[FAIL] FAILED - load_level=0")
        print(f"  Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        continue

    try:
        # Try loading with level 1 (includes tracker events)
        print("\n[2] Loading with load_level=1 (tracker events)...")
        replay = sc2reader.load_replay(replay_path, load_level=1)
        print(f"[OK] SUCCESS - load_level=1")
        print(f"  - Tracker events: {len(replay.tracker_events)}")

    except Exception as e:
        print(f"[FAIL] FAILED - load_level=1")
        print(f"  Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        continue

    try:
        # Try loading with level 4 (full data including game events)
        print("\n[3] Loading with load_level=4 (full data)...")
        replay = sc2reader.load_replay(replay_path, load_level=4)
        print(f"[OK] SUCCESS - load_level=4")
        print(f"  - Game events: {len(replay.game_events)}")
        print(f"  - Messages: {len(replay.messages)}")

        # Check for cache_handles attribute
        if hasattr(replay, 'cache_handles'):
            print(f"  - Has cache_handles: {replay.cache_handles}")
        else:
            print(f"  - No cache_handles attribute")

    except AttributeError as e:
        print(f"[FAIL] FAILED - load_level=4 (AttributeError)")
        print(f"  Error: {str(e)}")
        if 'cache_handles' in str(e):
            print("  → This is the cache_handles bug!")
        traceback.print_exc()

    except Exception as e:
        print(f"[FAIL] FAILED - load_level=4")
        print(f"  Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()

print(f"\n{'='*80}")
print("Testing complete!")
print(f"{'='*80}")
