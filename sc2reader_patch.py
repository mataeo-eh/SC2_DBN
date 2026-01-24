"""
Monkey patch for sc2reader to handle AI Arena bot replays with empty cache_handles

The bug: Bot replays have empty cache_handles list, but sc2reader tries to access [0]
Location: sc2reader/resources.py lines 389-397

This patch fixes the IndexError and allows bot replays to be parsed.
"""
import sc2reader
from sc2reader.resources import Replay
from sc2reader import utils
from datetime import datetime
import hashlib

# GAME_SPEED_FACTOR from sc2reader
GAME_SPEED_FACTOR = {
    "LotV": {"Slower": 0.6, "Slow": 0.8, "Normal": 1.0, "Fast": 1.2, "Faster": 1.4},
    "HotS": {"Slower": 0.6, "Slow": 0.8, "Normal": 1.0, "Fast": 1.2, "Faster": 1.4},
    "WoL": {"Slower": 0.6, "Slow": 0.8, "Normal": 1.0, "Fast": 1.2, "Faster": 1.4},
}

def patched_load_details(self):
    """
    Patched version that handles empty cache_handles gracefully for bot replays
    This is a direct copy of the original with safe cache_handles access
    """
    if "replay.details" in self.raw_data:
        details = self.raw_data["replay.details"]
    elif "replay.details.backup" in self.raw_data:
        details = self.raw_data["replay.details.backup"]
    else:
        return

    self.map_name = details["map_name"]

    # PATCH: Handle empty cache_handles for bot replays
    if details.get("cache_handles") and len(details["cache_handles"]) > 0:
        self.region = details["cache_handles"][0].server.lower()
        self.map_hash = details["cache_handles"][-1].hash
        self.map_file = details["cache_handles"][-1]
    else:
        # Bot replay - no cache_handles
        self.region = "local"
        self.map_hash = None
        self.map_file = None

    # Expand this special case mapping
    if self.region == "sg":
        self.region = "sea"

    # PATCH: Handle dependency hashes safely
    if details.get("cache_handles") and len(details["cache_handles"]) > 0:
        dependency_hashes = [d.hash for d in details["cache_handles"]]
        if (
            hashlib.sha256("Standard Data: Void.SC2Mod".encode("utf8")).hexdigest()
            in dependency_hashes
        ):
            self.expansion = "LotV"
        elif (
            hashlib.sha256("Standard Data: Swarm.SC2Mod".encode("utf8")).hexdigest()
            in dependency_hashes
        ):
            self.expansion = "HotS"
        elif (
            hashlib.sha256("Standard Data: Liberty.SC2Mod".encode("utf8")).hexdigest()
            in dependency_hashes
        ):
            self.expansion = "WoL"
        else:
            self.expansion = ""
    else:
        # Bot replays - default to LotV
        self.expansion = "LotV"

    self.windows_timestamp = details["file_time"]
    self.unix_timestamp = utils.windows_to_unix(self.windows_timestamp)
    self.end_time = datetime.utcfromtimestamp(self.unix_timestamp)

    # The utc_adjustment is either the adjusted windows timestamp OR
    # the value required to get the adjusted timestamp. We know the upper
    # limit for any adjustment number so use that to distinguish between
    # the two cases.
    if details["utc_adjustment"] < 10**7 * 60 * 60 * 24:
        self.time_zone = details["utc_adjustment"] / (10**7 * 60 * 60)
    else:
        self.time_zone = (details["utc_adjustment"] - details["file_time"]) / (
            10**7 * 60 * 60
        )

    self.game_length = self.length
    self.real_length = utils.Length(
        seconds=self.length.seconds
        // GAME_SPEED_FACTOR[self.expansion].get(self.speed, 1.0)
    )
    self.start_time = datetime.utcfromtimestamp(
        self.unix_timestamp - self.real_length.seconds
    )
    self.date = self.end_time  # backwards compatibility

# Apply the monkey patch
Replay.load_details = patched_load_details
