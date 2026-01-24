"""
Main extraction script for SC2 replay data extraction
"""
import logging
from typing import Optional
from pathlib import Path

# Import patch FIRST
import sc2reader_patch  # noqa: F401

from src.parser.replay_parser import ReplayParser
from src.processors.event_processor import EventProcessor
from src.state.game_state_tracker import GameStateTracker
from src.state.frame_sampler import FrameSampler
from src.output.json_writer import JSONWriter
from src.output.parquet_writer import ParquetWriter
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


class ReplayExtractor:
    """Main replay extraction class"""

    def __init__(
        self,
        output_format: str = "json",
        frame_interval: int = 112,  # 5 seconds @ Faster
        output_dir: str = "data/processed",
        verbose: bool = True
    ):
        """
        Initialize replay extractor

        Args:
            output_format: Output format ('json' or 'parquet')
            frame_interval: Frames between samples (112 = 5 seconds @ Faster)
            output_dir: Directory for output files
            verbose: Enable verbose logging
        """
        self.output_format = output_format
        self.frame_interval = frame_interval
        self.output_dir = output_dir

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        setup_logging(log_level)

        # Initialize components
        self.parser = ReplayParser()
        logger.info(f"ReplayExtractor initialized (format={output_format}, interval={frame_interval} frames)")

    def extract(self, replay_path: str, output_dir: Optional[str] = None) -> dict:
        """
        Extract data from a single replay

        Args:
            replay_path: Path to .SC2Replay file
            output_dir: Optional output directory (overrides default)

        Returns:
            Dict with extraction results
        """
        output_dir = output_dir or self.output_dir
        logger.info(f"Starting extraction: {replay_path}")

        try:
            # PHASE 1: Load and validate replay
            replay = self.parser.load_replay(replay_path, load_level=3)
            is_valid, errors = self.parser.validate_replay(replay)

            if not is_valid:
                logger.warning(f"Validation failed: {errors}")
                return {
                    'success': False,
                    'error': f"Validation failed: {errors}"
                }

            # Extract metadata
            metadata = self.parser.extract_metadata(replay, replay_path)

            # Extract replay name for output file naming
            replay_name = Path(replay_path).stem  # Gets filename without .SC2Replay extension

            # PHASE 2: Initialize state tracking
            state_tracker = GameStateTracker()

            # PHASE 3: Process events
            event_processor = EventProcessor(state_tracker)
            event_processor.process_events(replay)

            # PHASE 4: Sample frames
            sampler = FrameSampler(interval_frames=self.frame_interval)
            frame_states = sampler.sample_frames(replay, state_tracker)

            # PHASE 5: Write output
            if self.output_format == "json":
                writer = JSONWriter(output_dir)
                writer.write_all(metadata, frame_states, replay_name=replay_name)
            elif self.output_format == "parquet":
                writer = ParquetWriter(output_dir)
                writer.write_all(metadata, frame_states, replay_name=replay_name)
            else:
                raise ValueError(f"Unsupported output format: {self.output_format}")

            logger.info(f"Extraction complete: {len(frame_states)} frames extracted")

            return {
                'success': True,
                'replay_hash': metadata.replay_hash,
                'frame_count': len(frame_states),
                'event_count': len(replay.tracker_events),
                'map_name': metadata.map_name,
                'game_length_seconds': metadata.game_length_seconds
            }

        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def extract_batch(
        self,
        replay_paths: list,
        output_dir: Optional[str] = None,
        skip_errors: bool = True
    ) -> list:
        """
        Extract data from multiple replays

        Args:
            replay_paths: List of replay file paths
            output_dir: Optional output directory
            skip_errors: Continue on errors vs fail

        Returns:
            List of extraction results
        """
        output_dir = output_dir or self.output_dir
        results = []

        logger.info(f"Batch extraction: {len(replay_paths)} replays")

        for i, replay_path in enumerate(replay_paths):
            logger.info(f"Processing {i+1}/{len(replay_paths)}: {replay_path}")

            result = self.extract(replay_path, output_dir)
            results.append(result)

            if not result['success'] and not skip_errors:
                logger.error(f"Stopping batch due to error: {result.get('error')}")
                break

        # Summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful

        logger.info(f"Batch complete: {successful} successful, {failed} failed")

        return results


def main():
    """Command-line entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract data from SC2 replay files")
    parser.add_argument("replay", help="Path to .SC2Replay file or directory")
    parser.add_argument("-o", "--output", default="data/processed", help="Output directory")
    parser.add_argument("-f", "--format", choices=["json", "parquet"], default="json", help="Output format")
    parser.add_argument("-i", "--interval", type=int, default=112, help="Frame sampling interval (default: 112 = 5s)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Create extractor
    extractor = ReplayExtractor(
        output_format=args.format,
        frame_interval=args.interval,
        output_dir=args.output,
        verbose=args.verbose
    )

    # Check if directory or file
    replay_path = Path(args.replay)

    if replay_path.is_dir():
        # Batch process directory
        replay_files = list(replay_path.glob("*.SC2Replay"))
        logger.info(f"Found {len(replay_files)} replays in directory")
        results = extractor.extract_batch([str(f) for f in replay_files])

        # Print summary
        successful = sum(1 for r in results if r['success'])
        print(f"\nBatch processing complete:")
        print(f"  Successful: {successful}/{len(results)}")
        print(f"  Output: {args.output}")

    else:
        # Single file
        result = extractor.extract(str(replay_path))

        if result['success']:
            print(f"\nExtraction successful!")
            print(f"  Frames extracted: {result['frame_count']}")
            print(f"  Events processed: {result['event_count']}")
            print(f"  Output: {args.output}")
        else:
            print(f"\nExtraction failed: {result['error']}")


if __name__ == "__main__":
    main()
