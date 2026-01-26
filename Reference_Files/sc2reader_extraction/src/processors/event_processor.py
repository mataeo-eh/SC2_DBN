"""
Event processor - dispatches events to specialized handlers
"""
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2reader.resources import Replay

from src.state.game_state_tracker import GameStateTracker

logger = logging.getLogger(__name__)


class EventProcessor:
    """Main event dispatcher that routes events to state tracker"""

    def __init__(self, state_tracker: GameStateTracker):
        self.state_tracker = state_tracker

    def process_events(self, replay: 'Replay') -> None:
        """
        Process all tracker events in chronological order

        Args:
            replay: Loaded replay object with tracker_events
        """
        if not hasattr(replay, 'tracker_events'):
            logger.warning("No tracker events in replay")
            return

        logger.info(f"Processing {len(replay.tracker_events)} tracker events")

        for event in replay.tracker_events:
            try:
                self.dispatch_event(event)
            except Exception as e:
                logger.warning(f"Error processing event {type(event).__name__}: {e}")
                # Continue processing (fail-safe)

        logger.info("Event processing complete")

    def dispatch_event(self, event) -> None:
        """Route event to appropriate handler"""
        event_type = type(event).__name__

        # Unit birth
        if event_type == 'UnitBornEvent':
            self._handle_unit_born(event)

        # Building/unit construction
        elif event_type == 'UnitInitEvent':
            self._handle_unit_init(event)

        # Construction completion
        elif event_type == 'UnitDoneEvent':
            self._handle_unit_done(event)

        # Death/destruction
        elif event_type == 'UnitDiedEvent':
            self._handle_unit_died(event)

        # Upgrade completion
        elif event_type == 'UpgradeCompleteEvent':
            self._handle_upgrade_complete(event)

        # Player stats
        elif event_type == 'PlayerStatsEvent':
            self._handle_player_stats(event)

        # Messages (from replay.messages, not tracker events)
        # Handled separately in main extraction

    def _handle_unit_born(self, event):
        """Handle UnitBornEvent"""
        self.state_tracker.add_unit_born(
            frame=event.frame,
            unit_id=event.unit_id,
            unit_type=event.unit_type_name,
            player_id=event.control_pid,
            x=event.x if hasattr(event, 'x') else 0,
            y=event.y if hasattr(event, 'y') else 0
        )

    def _handle_unit_init(self, event):
        """Handle UnitInitEvent (building construction start)"""
        self.state_tracker.add_unit_init(
            frame=event.frame,
            unit_id=event.unit_id,
            unit_type=event.unit_type_name,
            player_id=event.control_pid,
            x=event.x if hasattr(event, 'x') else 0,
            y=event.y if hasattr(event, 'y') else 0
        )

    def _handle_unit_done(self, event):
        """Handle UnitDoneEvent (construction completion)"""
        self.state_tracker.add_unit_done(
            frame=event.frame,
            unit_id=event.unit_id
        )

    def _handle_unit_died(self, event):
        """Handle UnitDiedEvent"""
        killer_pid = None
        if hasattr(event, 'killer_pid'):
            killer_pid = event.killer_pid

        self.state_tracker.add_unit_died(
            frame=event.frame,
            unit_id=event.unit_id,
            killer_player_id=killer_pid
        )

    def _handle_upgrade_complete(self, event):
        """Handle UpgradeCompleteEvent"""
        self.state_tracker.add_upgrade(
            frame=event.frame,
            player_id=event.pid,
            upgrade_name=event.upgrade_type_name
        )

    def _handle_player_stats(self, event):
        """Handle PlayerStatsEvent"""
        self.state_tracker.add_player_stats(
            frame=event.frame,
            player_id=event.pid,
            stats_event=event
        )
