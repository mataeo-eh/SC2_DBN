"""
Test script for BuildingExtractor, EconomyExtractor, and UpgradeExtractor.

This script loads a replay and tests all three new extractors to ensure
they work correctly.

Usage:
    python test_extractors.py
"""

import sys
import logging
from pathlib import Path

# Setup imports before importing modules
from absl import app
from pysc2 import run_configs
from pysc2.lib import replay
from s2clientprotocol import sc2api_pb2 as sc_pb

# Add src_new to path
sys.path.insert(0, str(Path(__file__).parent / 'src_new'))

from extractors.building_extractor import BuildingExtractor
from extractors.economy_extractor import EconomyExtractor
from extractors.upgrade_extractor import UpgradeExtractor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_extractors(unused_argv):
    """Test all three extractors on a sample replay."""

    # Use first replay in replays directory
    replay_path = Path(__file__).parent / 'replays' / '4533018_ArgoBot_what_UltraloveAIE_v2.SC2Replay'

    if not replay_path.exists():
        logger.error(f"Replay not found: {replay_path}")
        return

    logger.info(f"Testing extractors with replay: {replay_path.name}")

    # Setup replay using pysc2 directly
    run_config = run_configs.get()
    replay_data = run_config.replay_data(str(replay_path))
    replay_version = replay.get_replay_version(replay_data)
    run_config = run_configs.get(version=replay_version)

    interface = sc_pb.InterfaceOptions(
        raw=True,
        score=True,
        show_cloaked=True,
        show_burrowed_shadows=True,
        show_placeholders=True
    )

    # Start SC2 instance
    logger.info("Starting SC2 instance...")
    with run_config.start(want_rgb=False) as controller:
        # Get replay info
        info = controller.replay_info(replay_data)
        logger.info(f"Map: {info.map_name}")
        logger.info(f"Duration: {info.game_duration_loops / 22.4:.1f}s")

        # Start replay from player 1's perspective
        controller.start_replay(sc_pb.RequestStartReplay(
            replay_data=replay_data,
            map_data=None,
            options=interface,
            observed_player_id=1
        ))

        # Create extractors
        building_extractor = BuildingExtractor(player_id=1)
        economy_extractor = EconomyExtractor(player_id=1)
        upgrade_extractor = UpgradeExtractor(player_id=1)

        logger.info("\nProcessing frames...")
        print("=" * 80)

        frame_count = 0
        max_frames = 50  # Test first 50 seconds

        # Initial step
        controller.step()

        while frame_count < max_frames:
            obs = controller.observe()

            # Check for game end
            if obs.player_result:
                logger.info("Game ended")
                break

            # Extract data
            buildings_data = building_extractor.extract(obs)
            economy_data = economy_extractor.extract(obs)
            upgrades_data = upgrade_extractor.extract(obs)

            # Get game time
            game_loop = obs.observation.game_loop
            game_time = game_loop / 22.4

            # Print summary every 10 frames
            if frame_count % 10 == 0:
                print(f"\n[Frame {frame_count+1}] Time: {game_time:.1f}s (Loop: {game_loop})")

                # Building summary
                building_counts = building_extractor.get_building_counts(buildings_data)
                building_states = building_extractor.get_building_by_state(buildings_data)
                print(f"  Buildings: {len(buildings_data)} total")
                if building_counts:
                    print(f"    Types: {building_counts}")
                print(f"    States: Building={len(building_states['building'])}, "
                      f"Completed={len(building_states['completed'])}, "
                      f"Destroyed={len(building_states['destroyed'])}")

                # Economy summary
                print(f"  Economy:")
                print(f"    {economy_extractor.get_summary(economy_data)}")

                # Upgrade summary
                upgrade_summary = upgrade_extractor.get_upgrade_summary(upgrades_data)
                print(f"  Upgrades: {upgrade_summary}")

            # Show new upgrades as they complete
            new_upgrades = upgrade_extractor.get_new_upgrades()
            if new_upgrades:
                print(f"\n  *** NEW UPGRADES COMPLETED at {game_time:.1f}s ***")
                for upgrade_id in new_upgrades:
                    from extractors.upgrade_extractor import get_upgrade_name, parse_upgrade_details
                    name = get_upgrade_name(upgrade_id)
                    category, level = parse_upgrade_details(name)
                    print(f"    - {name} (Category: {category}, Level: {level})")

            frame_count += 1
            controller.step(22)  # Step ~1 second

        print("\n" + "=" * 80)
        print("\nTest Summary:")
        print(f"  Frames processed: {frame_count}")
        print(f"  Final building count: {len(buildings_data)}")
        print(f"  Final upgrade count: {upgrade_extractor.get_upgrade_count(upgrades_data)}")
        print(f"  Final minerals: {economy_data['minerals']}")
        print(f"  Final vespene: {economy_data['vespene']}")

        # Show detailed building data (first 3 buildings)
        print("\nSample Building Data:")
        for i, (readable_id, building_data) in enumerate(list(buildings_data.items())[:3]):
            if building_data.get('state') != 'destroyed':
                print(f"\n  Building {i+1}: {readable_id}")
                print(f"    Type: {building_data['unit_type_name']}")
                print(f"    Position: ({building_data['x']:.1f}, {building_data['y']:.1f})")
                print(f"    Health: {building_data['health']:.0f}/{building_data['health_max']:.0f}")
                print(f"    Build Progress: {building_data['build_progress']*100:.0f}%")
                print(f"    State: {building_data['state']}")

        # Show upgrade categories
        if upgrades_data:
            print("\nUpgrades by Category:")
            by_category = upgrade_extractor.get_upgrades_by_category(upgrades_data)
            for category, upgrade_names in sorted(by_category.items()):
                print(f"  {category.capitalize()}: {', '.join(upgrade_names)}")

        print("\n[SUCCESS] All extractors tested successfully!")

        # Cleanup
        controller.quit()


if __name__ == "__main__":
    app.run(test_extractors)
