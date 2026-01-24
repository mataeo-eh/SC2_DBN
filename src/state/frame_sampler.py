"""
Frame sampler - samples game state at specified intervals
"""
import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2reader.resources import Replay

from src.models.frame_data import FrameState
from src.state.game_state_tracker import GameStateTracker

logger = logging.getLogger(__name__)


class FrameSampler:
    """Samples game state at regular intervals"""

    def __init__(self, interval_frames: int = 112):
        """
        Args:
            interval_frames: Frames between samples (default: 112 = 5 seconds @ Faster)
        """
        self.interval_frames = interval_frames

    def sample_frames(self, replay: 'Replay', tracker: GameStateTracker) -> List[FrameState]:
        """
        Sample game state at regular intervals

        Args:
            replay: Loaded replay object
            tracker: GameStateTracker with all events processed

        Returns:
            List of FrameState objects
        """
        samples = []

        logger.info(f"Sampling frames every {self.interval_frames} frames ({self.interval_frames / 22.4:.1f} seconds)")

        # Sample from frame 0 to replay end
        for frame in range(0, replay.frames, self.interval_frames):
            state = tracker.get_state_at_frame(frame)
            samples.append(state)

        # Always include final frame if not already sampled
        if replay.frames % self.interval_frames != 0:
            final_state = tracker.get_state_at_frame(replay.frames)
            samples.append(final_state)

        logger.info(f"Sampled {len(samples)} frames")

        return samples
