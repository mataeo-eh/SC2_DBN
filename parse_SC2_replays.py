from zephyrus_sc2_parser import parse_replay
import os
from pathlib import Path
import json


output_dir = Path("game_info")
os.makedirs(output_dir, exist_ok=True)
replay = parse_replay("replays/4533040_what_why_PylonAIE_v4.SC2Replay", local=True, tick=1)


with open(output_dir / "4533040_what_why_PylonAIE_v4.json", "w") as f:
    json.dump(replay.to_dict(), f, indent=4)