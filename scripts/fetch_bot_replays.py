import requests
from dotenv import load_dotenv
import os
import pprint
from tqdm import tqdm
import json
load_dotenv()


def authorize():
    token = os.getenv("AIARENA_TOKEN")
    base_url = os.getenv("AIARENA_NET_URL")

    # Set up auth header with your token
    auth = {'Authorization': f'Token {token}'}
    return auth, base_url




def fetch_bots_list(auth, base_url, max: int = 5, print_output: bool = True, bot: str = None):
    """ 
    Fetches a list of bots from the AI Arena API 
    Args: 
        auth: Authorization header
        base_url: Base URL for the API
    Kwargs:
        max (int): Maximum number of bots to fetch (default = 5)
        print_output (bool): Whether to print the output (default = True)
        bot (str): Specific bot name to filter (default = None)
    Returns:
        List of bots (dict)
    """
    bots = []
    url = f"{base_url}/bots/"
    pbar = None

    while url:
        response = requests.get(url, headers=auth)
        response.raise_for_status()
        data = response.json()

        # Initialize progress bar once
        if pbar is None:
            total = data.get("count")
            pbar = tqdm(total=total, desc="Fetching bots", unit="bots")

        bots.extend(data["results"])
        pbar.update(len(data["results"]))

        url = data.get("next")

    if pbar:
        pbar.close()

    if bot:
        bots = [b for b in bots if bot.lower() in b.get("name", "").lower()]

    if print_output:
        print(f"Total bots fetched: {len(bots)}")
        print(json.dumps(bots[:max], indent=2))

    return bots

def fetch_bot_id(auth, url, bot_name: str):
    """ 
    Finds the bot ID for a given bot name 
    Args: 
        auth: Authorization header
        url: Base URL for the API
        bot_name (str): Name of the bot to find
    """
    bots = fetch_bots_list(auth, url, bot=bot_name, print_output=False)
    if bots:
        return bots[0]["id"]
    return None


def fetch_bot_match_ids(auth, base_url, bot_ids: list, max_replays: int = None, print_output: bool = True):
    """ 
    Fetches a list of matches for a specific bot from the AI Arena API 
    Args: 
        auth: Authorization header
        base_url: Base URL for the API
        bot_ids (list): List of bot IDs to fetch matches for
    Kwargs:
        max_replays (int): Maximum number of matches to fetch (default = None)
        print_output (bool): Whether to print the output (default = True)
    Returns:
        Number of match ID's collected (int)
        List of match IDs collected (list)
    """
    match_ids = []
    # Make replays directory if it doesn't exist
    os.makedirs('replays', exist_ok=True)
    # Iterate over bot IDs
    for bot_id in tqdm(bot_ids, desc="Processing bots"):
        # Get matches for a given bot id
        matches = requests.get(f'{base_url}/match-participations/?bot={bot_id}', headers=auth).json()
        # Iterate over matches to get each ID
        for match in tqdm(matches['results'][:max_replays], desc=f"Processing matches for bot {bot_id}"):
            match_ids.append(match['match'])
    if print_output:
        print(f"Total match IDs fetched: {len(match_ids)}")
        pprint.pprint(match_ids)
    return len(match_ids), match_ids




def download_replays(auth, base_url, match_ids: list, print_output: bool = True):
    """
    Downloads replays for given match IDs
    Args:
        auth: Authorization header
        base_url: Base URL for the API
        match_ids (list): List of match IDs to download replays for
    Kwargs:
        print_output (bool): Whether to print the output (default = True)
    Returns:
        Number of replays downloaded (int)
    """
    num_replays = 0
    # Iterate over match IDs to download replays
    for match_id in tqdm(match_ids, desc="Downloading replays", leave=False):
        # Check if replay has already been downloaded
        if os.path.exists(f'replays/match_{match_id}.SC2Replay'):
            print(f"Replay for match {match_id} already exists. Skipping download.")
            continue
        # Get info for each match
        result = requests.get(f'{base_url}/results/?match={match_id}', headers=auth).json()
        # Get replay URL
        if print_output:
            pprint.pprint(result)
        replay_url = result['results'][0]['replay_file']
        if replay_url:  # Check it's not null
            replay_response = requests.get(replay_url)

            # Use the actual match_id variable instead of hardcoded "12345" for filename
            filename = f'replays/match_{match_id}.SC2Replay'
            # Save replay file
            with open(filename, 'wb') as f:
                f.write(replay_response.content)

            print(f"Downloaded: {filename}")
            num_replays += 1
    return num_replays

def main(bots: list, print_output = True, max_replays=None):
    """ 
    Main function to fetch and download bot replays 
    Args: 
        bots (list): List of bot names to fetch replays for
    Kwargs:
        print_output (bool): Whether to print the output (default = True)
        max_replays (int): Maximum number of replays to download per bot (default = None)
    """
    try:
        # Authorize API usage for this session
        auth, url = authorize()
        # Initialize list to hold bot IDs
        bot_ids = []
        # Populate bot IDs from names using helper function
        for bot_name in (pbar := tqdm(bots)):
            pbar.set_description(f"Fetching bot ID for {bot_name}")
            bot_id = fetch_bot_id(auth, url, bot_name)
            if bot_id:
                bot_ids.append(bot_id)
            else:
                print(f"Bot '{bot_name}' not found.")
        # Fetch and download matches for the bot IDs
        match_ids = fetch_bot_match_ids(auth, url, bot_ids, max_replays=max_replays, print_output=print_output)[1]
        if print_output:
            print("Finished fetching match IDs.")
        if match_ids:
            # Download replays for the fetched match IDs
            num_replays = download_replays(auth, url, match_ids, print_output=print_output)
    except Exception as e:
        raise RuntimeError(f"Error in replay download pipeline: {e}")
    if print_output:
        print(f"Total replays downloaded: {num_replays}")



if __name__ == "__main__":
    bots = ["really","why","what"]
    main(bots, max_replays = 1, print_output=True)
    #auth, base_url = authorize()
    #bots = fetch_bot_id(auth, base_url, bot_name="really")
    #bots = fetch_bots_list(auth, base_url, max=10, bot="really")
    #print(bots)
    #fetch_bot_match_ids(auth, base_url, bot_ids=[934], print_output=True)

