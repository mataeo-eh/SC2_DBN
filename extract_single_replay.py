"""
Example script: Extract data from a single SC2 replay
"""
from src.main import ReplayExtractor

def main():
    # Initialize extractor
    extractor = ReplayExtractor(
        output_format='json',  # or 'parquet'
        frame_interval=112,    # 5 seconds @ Faster speed
        output_dir='data/processed',
        verbose=True
    )

    # Extract single replay
    replay_path = r"replays\4533040_what_why_PylonAIE_v4.SC2Replay"

    print(f"Extracting replay: {replay_path}")
    result = extractor.extract(replay_path)

    if result['success']:
        print("\n✓ Extraction successful!")
        print(f"  Replay hash: {result['replay_hash']}")
        print(f"  Map: {result['map_name']}")
        print(f"  Duration: {result['game_length_seconds']:.1f}s")
        print(f"  Frames extracted: {result['frame_count']}")
        print(f"  Events processed: {result['event_count']}")
        print(f"  Output directory: data/processed/")
    else:
        print(f"\n✗ Extraction failed: {result['error']}")


if __name__ == "__main__":
    main()
