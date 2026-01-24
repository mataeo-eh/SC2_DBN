import mpyq
from s2protocol import versions

# Open the replay
archive = mpyq.MPQArchive("replays/4533040_what_why_PylonAIE_v4.SC2Replay")

# Get protocol version
contents = archive.header['user_data_header']['content']
header = versions.latest().decode_replay_header(contents)
base_build = header['m_version']['m_baseBuild']
protocol = versions.build(base_build)

# Parse game events
contents = archive.read_file('replay.game.events')
game_events = list(protocol.decode_replay_game_events(contents))

# Find selection and command events
selection_events = [e for e in game_events if 'Selection' in e['_event']]
# Find the SCmdEvent specifically
cmd_events = next((e for e in game_events if e['_event'] == 'NNet.Game.SCmdEvent'), None)

if cmd_events:
    print("SCmdEvent found:")
    for key, value in cmd_events.items():
        print(f"  {key}: {value}")
else:
    print("SCmdEvent not found")

print(f"Found {len(selection_events)} selection events")
print(f"Found {len(cmd_events)} command events")

if selection_events:
    print("\nExample selection event:")
    for key, value in selection_events[0].items():
        print(f"  {key}: {value}")
