"""
Test script to diagnose bot replay compatibility issues.
Tests both human ladder replays and AI Arena bot replays.
"""

import sys
import io
# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sc2reader
from pathlib import Path
import traceback

# Test files
HUMAN_REPLAY = r"c:\Users\matae\OneDrive\Desktop\Coding-Projects\local-play-bootstrap-main\.venv-3_12\src\python-sc2\test\replays\20220223 - GAME 1 - Astrea vs SKillous - P vs P - Curious Minds LE.SC2Replay"

BOT_REPLAYS = [
    r"c:\Users\matae\OneDrive\Desktop\Coding-Projects\local-play-bootstrap-main\replays\1_basic_bot_vs_loser_bot.SC2Replay",
    r"c:\Users\matae\OneDrive\Desktop\Coding-Projects\local-play-bootstrap-main\replays\3_basic_bot_vs_loser_bot.SC2Replay",
    r"c:\Users\matae\OneDrive\Desktop\Coding-Projects\local-play-bootstrap-main\replays\4533040_what_why_PylonAIE_v4.SC2Replay",
    r"c:\Users\matae\OneDrive\Desktop\Coding-Projects\local-play-bootstrap-main\replays\4533038_really_what_IncorporealAIE_v4.SC2Replay",
]


def test_replay(replay_path, replay_type="UNKNOWN"):
    """Test loading a replay file."""
    print(f"\n{'='*80}")
    print(f"Testing {replay_type}: {Path(replay_path).name}")
    print(f"{'='*80}")

    try:
        # Try basic load (level 0)
        print("Loading level 0 (metadata only)...")
        replay = sc2reader.load_replay(replay_path, load_level=0)
        print(f"  [OK] Level 0 successful")

        # Try level 1 (details)
        print("Loading level 1 (+ details)...")
        replay = sc2reader.load_replay(replay_path, load_level=1)
        print(f"  [OK] Level 1 successful")

        # Try level 2 (init data)
        print("Loading level 2 (+ init data)...")
        replay = sc2reader.load_replay(replay_path, load_level=2)
        print(f"  [OK] Level 2 successful")

        # Try level 3 (tracker events)
        print("Loading level 3 (+ tracker events)...")
        replay = sc2reader.load_replay(replay_path, load_level=3)
        print(f"  [OK] Level 3 successful")
        print(f"    Tracker events: {len(replay.tracker_events)}")

        # Try level 4 (game events)
        print("Loading level 4 (+ game events)...")
        replay = sc2reader.load_replay(replay_path, load_level=4)
        print(f"  [OK] Level 4 successful")
        print(f"    Game events: {len(replay.game_events)}")

        # Print metadata
        print(f"\n  Map: {replay.map_name}")
        print(f"  Duration: {replay.game_length}")
        print(f"  Frames: {replay.frames}")
        print(f"  Speed: {replay.speed}")
        print(f"  Build: {replay.build}")
        print(f"  Release: {replay.release_string}")

        # Print players
        print(f"  Players:")
        for player in replay.players:
            print(f"    - {player.name} ({player.play_race}): {player.result}")

        # Check for cache_handles
        print(f"\n  Checking replay.details attributes:")
        if hasattr(replay, 'details') and replay.details:
            print(f"    details exists: {type(replay.details)}")
            if hasattr(replay.details, '__dict__'):
                for key in dir(replay.details):
                    if not key.startswith('_'):
                        try:
                            val = getattr(replay.details, key)
                            print(f"      {key}: {type(val).__name__}")
                        except:
                            print(f"      {key}: <error accessing>")

        print(f"\n  [OK][OK][OK] ALL TESTS PASSED for {replay_type} [OK][OK][OK]")
        return True

    except Exception as e:
        print(f"\n  [FAIL][FAIL][FAIL] FAILED at some level [FAIL][FAIL][FAIL]")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error message: {str(e)}")
        print(f"\n  Full traceback:")
        traceback.print_exc()
        return False


def main():
    print("="*80)
    print("SC2READER BOT REPLAY COMPATIBILITY TEST")
    print("="*80)
    print(f"sc2reader version: {sc2reader.__version__}")

    # Test human replay first
    human_success = test_replay(HUMAN_REPLAY, "HUMAN LADDER REPLAY")

    # Test bot replays
    bot_results = []
    for bot_replay in BOT_REPLAYS:
        if Path(bot_replay).exists():
            success = test_replay(bot_replay, "BOT REPLAY")
            bot_results.append((Path(bot_replay).name, success))
        else:
            print(f"\nSkipping {bot_replay} (not found)")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Human replay: {'[OK] PASS' if human_success else '[FAIL] FAIL'}")
    print(f"\nBot replays:")
    for name, success in bot_results:
        print(f"  {name}: {'[OK] PASS' if success else '[FAIL] FAIL'}")

    # Count failures
    failures = sum(1 for _, s in bot_results if not s)
    if failures > 0:
        print(f"\n[WARNING]  {failures}/{len(bot_results)} bot replays FAILED")
        print("This confirms the AI Arena bot replay compatibility issue!")
    else:
        print(f"\n[OK] All bot replays loaded successfully!")


if __name__ == "__main__":
    main()
