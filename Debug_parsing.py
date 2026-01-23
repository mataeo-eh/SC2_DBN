import mpyq
from s2protocol import versions
from collections import Counter

# Try a different replay - use your real bot game
replay_path = "replays/4533040_what_why_PylonAIE_v4.SC2Replay"

archive = mpyq.MPQArchive(replay_path)

# Get protocol version
contents = archive.header['user_data_header']['content']
header = versions.latest().decode_replay_header(contents)
base_build = header['m_version']['m_baseBuild']
protocol = versions.build(base_build)

# Parse game events
contents = archive.read_file('replay.game.events')
game_events = list(protocol.decode_replay_game_events(contents))

# Count command events
cmd_events = [e for e in game_events if e['_event'] == 'NNet.Game.SCmdEvent']

# Separate events with and without ability data
with_abil = [e for e in cmd_events if e.get('m_abil') is not None]
without_abil = [e for e in cmd_events if e.get('m_abil') is None]

print(f"Total command events: {len(cmd_events)}")
print(f"  With ability: {len(with_abil)}")
print(f"  Without ability: {len(without_abil)}")

if with_abil:
    ability_counts = Counter(e['m_abil']['m_abilLink'] for e in with_abil)
    print(f"\nAbility types used:")
    for abil_link, count in ability_counts.most_common(10):
        print(f"  Ability {abil_link}: {count} times")

import mpyq
from s2protocol import versions

replay_path = "replays/4533040_what_why_PylonAIE_v4.SC2Replay"
archive = mpyq.MPQArchive(replay_path)

contents = archive.header['user_data_header']['content']
header = versions.latest().decode_replay_header(contents)
base_build = header['m_version']['m_baseBuild']
protocol = versions.build(base_build)

contents = archive.read_file('replay.game.events')
game_events = list(protocol.decode_replay_game_events(contents))

cmd_events = [e for e in game_events if e['_event'] == 'NNet.Game.SCmdEvent' and e.get('m_abil')]

# Group by ability and show examples
from collections import defaultdict
ability_examples = defaultdict(list)

for cmd in cmd_events:
    abil_link = cmd['m_abil']['m_abilLink']
    if len(ability_examples[abil_link]) < 2:  # Keep 2 examples per ability
        ability_examples[abil_link].append(cmd)

# Show examples for top abilities
for abil_link in [42, 45, 184, 119]:
    print(f"\nAbility {abil_link} examples:")
    for i, cmd in enumerate(ability_examples[abil_link][:2]):
        print(f"  Example {i+1}:")
        print(f"    cmdIndex: {cmd['m_abil']['m_abilCmdIndex']}")
        print(f"    Data type: {list(cmd['m_data'].keys())[0] if cmd['m_data'] else 'None'}")
        if cmd['m_data']:
            print(f"    Data: {cmd['m_data']}")
