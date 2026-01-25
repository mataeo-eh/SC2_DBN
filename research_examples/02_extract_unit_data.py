"""
Proof of Concept: Extract Unit Information

This example demonstrates:
1. How to extract unit information from observations
2. How to access unit properties (type, position, health, etc.)
3. How to filter units by player/alliance
4. How to track unit tags across frames

Usage:
    python 02_extract_unit_data.py --replay_path /path/to/replay.SC2Replay
"""

from absl import app
from absl import flags

from pysc2 import run_configs
from pysc2.lib import point
from pysc2.lib import replay
from pysc2.lib import units

from s2clientprotocol import sc2api_pb2 as sc_pb

FLAGS = flags.FLAGS
flags.DEFINE_string("replay_path", None, "Path to the replay file")
flags.DEFINE_integer("max_frames", 50, "Maximum frames to process")
flags.mark_flag_as_required("replay_path")


def get_unit_type_name(unit_type_id):
    """Convert unit type ID to human-readable name."""
    try:
        return units.get_unit_type(unit_type_id).name
    except:
        return f"Unknown({unit_type_id})"


def extract_unit_data(unit):
    """Extract comprehensive data from a unit."""
    return {
        # Identity
        'tag': unit.tag,
        'unit_type_id': unit.unit_type,
        'unit_type_name': get_unit_type_name(unit.unit_type),
        'owner': unit.owner,
        'alliance': unit.alliance,  # 1=Self, 2=Ally, 3=Neutral, 4=Enemy

        # Position
        'pos_x': unit.pos.x,
        'pos_y': unit.pos.y,
        'pos_z': unit.pos.z,
        'facing': unit.facing,

        # Vital stats
        'health': unit.health,
        'health_max': unit.health_max,
        'health_percent': (unit.health / unit.health_max * 100) if unit.health_max > 0 else 0,
        'shield': unit.shield,
        'shield_max': unit.shield_max,
        'energy': unit.energy,
        'energy_max': unit.energy_max,

        # State
        'build_progress': unit.build_progress,
        'is_flying': unit.is_flying,
        'is_burrowed': unit.is_burrowed,
        'is_hallucination': unit.is_hallucination,
        'cloak': unit.cloak,  # 0=CloakedUnknown, 1=Cloaked, 2=CloakedDetected, 3=NotCloaked

        # Combat
        'weapon_cooldown': unit.weapon_cooldown,
        'attack_upgrade_level': unit.attack_upgrade_level,
        'armor_upgrade_level': unit.armor_upgrade_level,
        'shield_upgrade_level': unit.shield_upgrade_level,

        # Additional
        'radius': unit.radius,
        'cargo_space_taken': unit.cargo_space_taken,
        'cargo_space_max': unit.cargo_space_max,
        'order_count': len(unit.orders),
    }


def main(unused_argv):
    """Extract and display unit information from a replay."""

    # Setup
    run_config = run_configs.get()
    replay_data = run_config.replay_data(FLAGS.replay_path)
    replay_version = replay.get_replay_version(replay_data)
    run_config = run_configs.get(version=replay_version)

    interface = sc_pb.InterfaceOptions(
        raw=True,
        score=True,
        show_cloaked=True,
        show_burrowed_shadows=True,
        show_placeholders=True
    )

    print("Starting SC2 instance...")
    with run_config.start(want_rgb=False) as controller:
        # Get replay info
        info = controller.replay_info(replay_data)
        print(f"\nReplay: {info.map_name}")

        # Start replay from player 1's perspective
        controller.start_replay(sc_pb.RequestStartReplay(
            replay_data=replay_data,
            map_data=None,
            options=interface,
            observed_player_id=1
        ))

        # Track units across frames
        seen_tags = set()
        unit_first_seen = {}  # tag -> game_loop when first seen
        unit_deaths = {}      # tag -> game_loop when died

        print("\nProcessing frames...")
        print("=" * 80)

        frame_count = 0
        controller.step()

        while frame_count < FLAGS.max_frames:
            obs = controller.observe()

            if obs.player_result:
                print("Game ended")
                break

            game_loop = obs.observation.game_loop
            raw = obs.observation.raw_data

            # Get current units
            current_tags = {u.tag for u in raw.units}

            # Detect new units
            new_tags = current_tags - seen_tags
            if new_tags:
                for tag in new_tags:
                    unit_first_seen[tag] = game_loop
                    seen_tags.add(tag)

            # Detect dead units
            for dead_tag in raw.event.dead_units:
                if dead_tag not in unit_deaths:
                    unit_deaths[dead_tag] = game_loop

            # Categorize units
            self_units = [u for u in raw.units if u.alliance == 1]
            enemy_units = [u for u in raw.units if u.alliance == 4]
            neutral_units = [u for u in raw.units if u.alliance == 3]

            # Print frame summary
            print(f"\n[Frame {frame_count+1}] Game Loop: {game_loop} ({game_loop/22.4:.1f}s)")
            print(f"Units: {len(self_units)} own, {len(enemy_units)} enemy, {len(neutral_units)} neutral")

            if new_tags:
                print(f"New units created: {len(new_tags)}")

            if raw.event.dead_units:
                print(f"Units died: {len(raw.event.dead_units)}")

            # Show sample unit details (first 3 own units)
            if self_units and frame_count == 0:
                print("\nSample unit details (own units):")
                for i, unit in enumerate(self_units[:3]):
                    data = extract_unit_data(unit)
                    print(f"\n  Unit {i+1}:")
                    print(f"    Type: {data['unit_type_name']} (ID: {data['unit_type_id']})")
                    print(f"    Tag: {data['tag']}")
                    print(f"    Position: ({data['pos_x']:.1f}, {data['pos_y']:.1f}, {data['pos_z']:.1f})")
                    print(f"    Health: {data['health']:.0f}/{data['health_max']:.0f} ({data['health_percent']:.0f}%)")
                    if data['shield_max'] > 0:
                        print(f"    Shield: {data['shield']:.0f}/{data['shield_max']:.0f}")
                    if data['energy_max'] > 0:
                        print(f"    Energy: {data['energy']:.0f}/{data['energy_max']:.0f}")
                    if data['build_progress'] < 1.0:
                        print(f"    Build Progress: {data['build_progress']*100:.0f}%")
                    if data['order_count'] > 0:
                        print(f"    Current Orders: {data['order_count']}")

            frame_count += 1
            controller.step(22)  # Step forward 22 loops (≈1 second)

        print("\n" + "=" * 80)
        print("\nSummary:")
        print(f"  Frames processed: {frame_count}")
        print(f"  Unique units seen: {len(seen_tags)}")
        print(f"  Units created (tracked): {len(unit_first_seen)}")
        print(f"  Units died: {len(unit_deaths)}")

        # Show first few unit lifecycles
        print("\nSample unit lifecycles:")
        for i, (tag, birth_loop) in enumerate(list(unit_first_seen.items())[:5]):
            death_loop = unit_deaths.get(tag, None)
            if death_loop:
                lifespan = death_loop - birth_loop
                print(f"  Tag {tag}: Created at loop {birth_loop}, died at {death_loop} (lifespan: {lifespan} loops)")
            else:
                print(f"  Tag {tag}: Created at loop {birth_loop}, still alive")


if __name__ == "__main__":
    app.run(main)
