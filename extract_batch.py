"""
Example script: Extract data from multiple SC2 replays
"""
from pathlib import Path
from src.main import ReplayExtractor

def main():
    # Initialize extractor
    extractor = ReplayExtractor(
        output_format='parquet',  # Use Parquet for batch processing
        frame_interval=112,       # 5 seconds @ Faster speed
        output_dir='data/processed',
        verbose=True
    )

    # Find all replays in directory
    replay_dir = Path("replays")
    replay_files = list(replay_dir.glob("*.SC2Replay"))

    print(f"Found {len(replay_files)} replays in {replay_dir}")

    if not replay_files:
        print("No replays found! Place .SC2Replay files in the 'replays/' directory")
        return

    # Extract all replays
    results = extractor.extract_batch(
        replay_paths=[str(f) for f in replay_files],
        skip_errors=True  # Continue even if some replays fail
    )

    # Print summary
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print("\n" + "="*60)
    print("BATCH EXTRACTION SUMMARY")
    print("="*60)
    print(f"Total replays: {len(results)}")
    print(f"✓ Successful: {len(successful)}")
    print(f"✗ Failed: {len(failed)}")

    if successful:
        total_frames = sum(r['frame_count'] for r in successful)
        total_events = sum(r['event_count'] for r in successful)
        print(f"\nData extracted:")
        print(f"  Total frames: {total_frames}")
        print(f"  Total events: {total_events}")
        print(f"  Output: data/processed/")

    if failed:
        print(f"\nFailed replays:")
        for result in failed:
            print(f"  - {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
