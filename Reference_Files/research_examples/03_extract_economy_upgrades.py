"""
Proof of Concept: Extract Economy and Upgrade Data

This example demonstrates:
1. How to extract economy metrics (minerals, gas, supply, workers)
2. How to extract upgrade information
3. How to track upgrade research completion

Usage:
    python 03_extract_economy_upgrades.py --replay_path /path/to/replay.SC2Replay
"""

from absl import app
from absl import flags

from pysc2 import run_configs
from pysc2.lib import replay
from pysc2.lib import upgrades

from s2clientprotocol import sc2api_pb2 as sc_pb

FLAGS = flags.FLAGS
flags.DEFINE_string("replay_path", None, "Path to the replay file")
flags.DEFINE_integer("max_frames", 100, "Maximum frames to process")
flags.mark_flag_as_required("replay_path")


def get_upgrade_name(upgrade_id):
    """Convert upgrade ID to human-readable name."""
    try:
        return upgrades.Upgrades(upgrade_id).name
    except:
        return f"Unknown({upgrade_id})"


def parse_upgrade_details(upgrade_name):
    """Parse upgrade name to extract category and level."""
    category = "unknown"
    level = 0

    # Determine category
    if "Weapon" in upgrade_name or "Melee" in upgrade_name or "Missile" in upgrade_name or "Ship" in upgrade_name:
        category = "weapons"
    elif "Armor" in upgrade_name:
        category = "armor"
    elif "Shield" in upgrade_name:
        category = "shields"
    else:
        category = "other"

    # Extract level
    import re
    match = re.search(r'Level(\d)', upgrade_name)
    if match:
        level = int(match.group(1))

    return category, level


def main(unused_argv):
    """Extract economy and upgrade data from a replay."""

    # Setup
    run_config = run_configs.get()
    replay_data = run_config.replay_data(FLAGS.replay_path)
    replay_version = replay.get_replay_version(replay_data)
    run_config = run_configs.get(version=replay_version)

    interface = sc_pb.InterfaceOptions(
        raw=True,
        score=True,
        show_cloaked=True
    )

    print("Starting SC2 instance...")
    with run_config.start(want_rgb=False) as controller:
        # Get replay info
        info = controller.replay_info(replay_data)
        print(f"\nReplay: {info.map_name}")
        print(f"Duration: {info.game_duration_loops / 22.4:.1f} seconds")

        # Start replay from player 1's perspective
        controller.start_replay(sc_pb.RequestStartReplay(
            replay_data=replay_data,
            map_data=None,
            options=interface,
            observed_player_id=1
        ))

        # Track upgrades
        previous_upgrades = set()
        upgrade_completion_times = {}  # upgrade_id -> game_loop

        print("\nProcessing frames...")
        print("=" * 80)

        frame_count = 0
        controller.step()

        while frame_count < FLAGS.max_frames:
            obs = controller.observe()

            if obs.player_result:
                print("\nGame ended")
                break

            game_loop = obs.observation.game_loop
            game_time = game_loop / 22.4

            # ===== ECONOMY DATA =====
            player_common = obs.observation.player_common
            minerals = player_common.minerals
            vespene = player_common.vespene
            food_used = player_common.food_used
            food_cap = player_common.food_cap
            food_army = player_common.food_army
            food_workers = player_common.food_workers
            idle_workers = player_common.idle_worker_count
            army_count = player_common.army_count

            # ===== UPGRADE DATA =====
            raw = obs.observation.raw_data
            current_upgrades = set(raw.player.upgrade_ids)

            # Detect newly completed upgrades
            new_upgrades = current_upgrades - previous_upgrades
            if new_upgrades:
                for upgrade_id in new_upgrades:
                    upgrade_completion_times[upgrade_id] = game_loop

            # ===== SCORE DATA (Economy Details) =====
            score = obs.observation.score.score_details
            minerals_collected = score.collected_minerals
            vespene_collected = score.collected_vespene
            mineral_rate = score.collection_rate_minerals
            vespene_rate = score.collection_rate_vespene

            # Print periodic status
            if frame_count % 10 == 0:
                print(f"\n[Frame {frame_count+1}] Time: {game_time:.1f}s (Loop: {game_loop})")
                print(f"  Economy:")
                print(f"    Resources: {minerals}m, {vespene}g")
                print(f"    Supply: {food_used}/{food_cap} (Army: {food_army}, Workers: {food_workers})")
                print(f"    Workers: {food_workers} total, {idle_workers} idle")
                print(f"    Army: {army_count} units")
                print(f"  Collection:")
                print(f"    Total: {minerals_collected:.0f}m, {vespene_collected:.0f}g")
                print(f"    Rate: {mineral_rate:.1f}m/min, {vespene_rate:.1f}g/min")
                print(f"  Upgrades: {len(current_upgrades)} completed")

            # Show upgrade completions
            if new_upgrades:
                print(f"\n  *** NEW UPGRADES COMPLETED ***")
                for upgrade_id in new_upgrades:
                    upgrade_name = get_upgrade_name(upgrade_id)
                    category, level = parse_upgrade_details(upgrade_name)
                    print(f"    - {upgrade_name}")
                    print(f"        ID: {upgrade_id}")
                    print(f"        Category: {category}")
                    print(f"        Level: {level}")
                    print(f"        Completed at: {game_time:.1f}s (loop {game_loop})")

            previous_upgrades = current_upgrades
            frame_count += 1
            controller.step(22)  # Step ~1 second

        print("\n" + "=" * 80)
        print("\nSummary:")
        print(f"  Frames processed: {frame_count}")
        print(f"  Total upgrades completed: {len(upgrade_completion_times)}")

        if upgrade_completion_times:
            print("\n  All completed upgrades:")
            # Sort by completion time
            sorted_upgrades = sorted(upgrade_completion_times.items(), key=lambda x: x[1])
            for upgrade_id, completion_loop in sorted_upgrades:
                upgrade_name = get_upgrade_name(upgrade_id)
                category, level = parse_upgrade_details(upgrade_name)
                completion_time = completion_loop / 22.4
                print(f"    [{completion_time:6.1f}s] {upgrade_name}")
                print(f"               Category: {category}, Level: {level}")

        # Final economy snapshot
        print("\n  Final economy state:")
        print(f"    Resources: {minerals}m, {vespene}g")
        print(f"    Supply: {food_used}/{food_cap}")
        print(f"    Workers: {food_workers}")
        print(f"    Army: {army_count} units")


if __name__ == "__main__":
    app.run(main)
