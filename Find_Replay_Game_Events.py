import mpyq
from s2protocol import versions
from collections import Counter
import json

# Open the replay
archive = mpyq.MPQArchive("replays/1_basic_bot_vs_loser_bot.SC2Replay")

# Get protocol version
contents = archive.header['user_data_header']['content']
header = versions.latest().decode_replay_header(contents)
base_build = header['m_version']['m_baseBuild']
protocol = versions.build(base_build)

# Parse game events
contents = archive.read_file('replay.game.events')
game_events = protocol.decode_replay_game_events(contents)

# Count event types
event_types = Counter(event['_event'] for event in game_events)

print("Game event types:")
for event_type, count in event_types.most_common(20):  # Top 20
    print(f"  {event_type}: {count}")

