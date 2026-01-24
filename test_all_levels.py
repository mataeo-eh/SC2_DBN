"""
Test all load levels to see what data is available in bot replays
"""
import sc2reader_patch
import sc2reader

replay_path = "replays/1_basic_bot_vs_loser_bot.SC2Replay"

print(f"Testing: {replay_path}\n")

for load_level in range(5):
    print(f"\n{'='*80}")
    print(f"Load Level: {load_level}")
    print(f"{'='*80}")

    try:
        replay = sc2reader.load_replay(replay_path, load_level=load_level)

        print(f"[OK] SUCCESS")
        print(f"  - Map: {replay.map_name}")
        print(f"  - Duration: {replay.game_length}")
        print(f"  - Frames: {replay.frames}")
        print(f"  - Players: {len(replay.players)}")
        print(f"  - Region: {getattr(replay, 'region', 'N/A')}")

        if hasattr(replay, 'tracker_events'):
            print(f"  - Tracker events: {len(replay.tracker_events)}")

        if hasattr(replay, 'game_events'):
            print(f"  - Game events: {len(replay.game_events)}")

        if hasattr(replay, 'messages'):
            print(f"  - Messages: {len(replay.messages)}")

        if hasattr(replay, 'raw_data'):
            print(f"  - Raw data keys: {list(replay.raw_data.keys())}")

        # Check what's in the replay object
        print(f"  - Attributes: {[attr for attr in dir(replay) if not attr.startswith('_')][:20]}")

    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {str(e)}")

# Try to manually inspect the replay file structure
print(f"\n{'='*80}")
print("Manual Inspection")
print(f"{'='*80}")

try:
    import zipfile
    with zipfile.ZipFile(replay_path, 'r') as replay_zip:
        print(f"Files in replay archive:")
        for name in replay_zip.namelist():
            info = replay_zip.getinfo(name)
            print(f"  - {name} ({info.file_size} bytes)")

except Exception as e:
    print(f"Error: {e}")
