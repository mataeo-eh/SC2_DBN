"""
Proof of Concept: Basic Replay Loading with pysc2

This example demonstrates:
1. How to load a replay
2. How to step through game loops
3. How to access basic observation data

Usage:
    python 01_basic_replay_loading.py --replay_path /path/to/replay.SC2Replay
"""

from absl import app
from absl import flags

from pysc2 import run_configs
from pysc2.lib import point
from pysc2.lib import replay

from s2clientprotocol import sc2api_pb2 as sc_pb

FLAGS = flags.FLAGS
flags.DEFINE_string("replay_path", None, "Path to the replay file")
flags.mark_flag_as_required("replay_path")


def main(unused_argv):
    """Load and step through a replay."""

    # 1. GET RUN CONFIG
    # This manages the SC2 binary and configuration
    run_config = run_configs.get()

    # 2. LOAD REPLAY DATA
    print(f"Loading replay: {FLAGS.replay_path}")
    replay_data = run_config.replay_data(FLAGS.replay_path)

    # Get replay version to ensure compatibility
    replay_version = replay.get_replay_version(replay_data)
    print(f"Replay version: {replay_version.game_version}")

    # Update run_config to use the correct version
    run_config = run_configs.get(version=replay_version)

    # 3. CONFIGURE INTERFACE
    # Set up what observations we want to receive
    interface = sc_pb.InterfaceOptions(
        raw=True,                    # Enable raw data (CRITICAL for ground truth)
        score=True,                  # Enable score information
        show_cloaked=True,           # Show cloaked units (for ground truth)
        show_burrowed_shadows=True,  # Show burrowed units
        show_placeholders=True       # Show queued buildings
    )

    # 4. START SC2 INSTANCE
    print("Starting SC2 instance...")
    with run_config.start(want_rgb=False) as controller:
        print("SC2 started successfully")

        # 5. GET REPLAY INFO
        print("\nGetting replay info...")
        info = controller.replay_info(replay_data)

        print(f"Map: {info.map_name}")
        print(f"Duration: {info.game_duration_loops} loops ({info.game_duration_loops / 22.4:.1f} seconds)")
        print(f"Players: {len(info.player_info)}")

        for i, player_info in enumerate(info.player_info):
            race_name = sc_pb.Race.Name(player_info.player_info.race_actual)
            print(f"  Player {i+1}: {race_name}, APM: {player_info.player_apm}, MMR: {player_info.player_mmr}")

        # 6. START REPLAY from Player 1's perspective
        print("\nStarting replay playback...")
        player_id = 1  # Observe from player 1's perspective

        controller.start_replay(sc_pb.RequestStartReplay(
            replay_data=replay_data,
            map_data=None,  # Map should be installed in SC2
            options=interface,
            observed_player_id=player_id  # Critical: sets perspective
        ))

        print(f"Observing from player {player_id}'s perspective")

        # 7. STEP THROUGH REPLAY
        step_mul = 22  # Observe every 22 game loops (≈1 second)
        observation_count = 0
        max_observations = 10  # Limit for this demo

        print(f"\nStepping through replay (step_mul={step_mul})...")
        print("=" * 60)

        # Initial step to get first observation
        controller.step()

        while observation_count < max_observations:
            # 8. GET OBSERVATION
            obs = controller.observe()

            # Check if game ended
            if obs.player_result:
                print("\nGame ended!")
                for result in obs.player_result:
                    print(f"  Player {result.player_id}: {sc_pb.Result.Name(result.result)}")
                break

            # Extract basic information
            game_loop = obs.observation.game_loop
            game_time_seconds = game_loop / 22.4

            # Player common data (economy)
            player_common = obs.observation.player_common
            minerals = player_common.minerals
            vespene = player_common.vespene
            supply_used = player_common.food_used
            supply_cap = player_common.food_cap

            # Raw data (units)
            raw = obs.observation.raw_data
            unit_count = len(raw.units)
            player_units = [u for u in raw.units if u.alliance == 1]  # Self
            enemy_units = [u for u in raw.units if u.alliance == 4]   # Enemy

            # Print observation summary
            print(f"[{observation_count+1}] Loop: {game_loop} ({game_time_seconds:.1f}s)")
            print(f"    Economy: {minerals}m, {vespene}g, Supply: {supply_used}/{supply_cap}")
            print(f"    Units: {len(player_units)} own, {len(enemy_units)} enemy (total: {unit_count})")

            observation_count += 1

            # Step forward
            controller.step(step_mul)

        print("=" * 60)
        print(f"\nProcessed {observation_count} observations")
        print("Demo complete!")


if __name__ == "__main__":
    app.run(main)
