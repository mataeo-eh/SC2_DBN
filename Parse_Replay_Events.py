import mpyq
from s2protocol import versions

# Open the replay
archive = mpyq.MPQArchive("replays/1_basic_bot_vs_loser_bot.SC2Replay")

# Get protocol version
contents = archive.header['user_data_header']['content']
header = versions.latest().decode_replay_header(contents)
base_build = header['m_version']['m_baseBuild']
protocol = versions.build(base_build)

# Parse tracker events
contents = archive.read_file('replay.tracker.events')
tracker_events = protocol.decode_replay_tracker_events(contents)

# Show examples of each event type
event_types = ['NNet.Replay.Tracker.SUnitBornEvent', 
               'NNet.Replay.Tracker.SUnitDiedEvent',
               'NNet.Replay.Tracker.SUpgradeEvent',
               'NNet.Replay.Tracker.SUnitPositionsEvent']

for event_type in event_types:
    example = next((e for e in tracker_events if e['_event'] == event_type), None)
    if example:
        print(f"\n{event_type}:")
        for key, value in example.items():
            print(f"  {key}: {value}")
    else:
        print(f"\n{event_type}: (not found in this replay)")


import mpyq
from s2protocol import versions

# Open the replay
archive = mpyq.MPQArchive("replays/1_basic_bot_vs_loser_bot.SC2Replay")

# Get protocol version
contents = archive.header['user_data_header']['content']
header = versions.latest().decode_replay_header(contents)
base_build = header['m_version']['m_baseBuild']
protocol = versions.build(base_build)

# Parse tracker events
contents = archive.read_file('replay.tracker.events')
tracker_events = protocol.decode_replay_tracker_events(contents)

# Find position events
position_events = [e for e in tracker_events if 'Position' in e['_event']]

print(f"Found {len(position_events)} position events")
if position_events:
    print("\nFirst position event:")
    for key, value in position_events[0].items():
        print(f"  {key}: {value}")