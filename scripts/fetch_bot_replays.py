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
            pbar = tqdm(total=total, desc="Fetching bots", unit="bot")

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

def fetch_bot_matches(auth, base_url, bot_id: int, max: int = 5, print_output: bool = True):
    """ 
    Fetches a list of matches for a specific bot from the AI Arena API 
    Args: 
        auth: Authorization header
        base_url: Base URL for the API
        bot_id (int): ID of the bot to fetch matches for
    Kwargs:
        max (int): Maximum number of matches to fetch (default = 5)
        print_output (bool): Whether to print the output (default = True)
    """
    matches = requests.get(f'{base_url}/match-participations/?bot={bot_id}', headers=auth).json()

    # Get match results with replay URLs
    match_id = matches['results'][0]['match']
    result = requests.get(f'{base_url}/results/?match={match_id}', headers=auth).json()
    print("replay file?", result['results'][0]['replay_file'])
    replay_url = result['results'][0]['replay_file']

    if replay_url:  # Check it's not null
        replay_response = requests.get(replay_url)
        
        os.makedirs('../replays', exist_ok=True)

        # Use the actual match_id variable instead of hardcoded "12345"
        filename = f'replays/match_{match_id}.SC2Replay'
        with open(filename, 'wb') as f:
            f.write(replay_response.content)

        print(f"Downloaded: {filename}")

if __name__ == "__main__":
    auth, base_url = authorize()
    #fetch_bots_list(auth, base_url, max=10, print_output=True, bot="really")
    fetch_bot_matches(auth, base_url, bot_id=934, max=5, print_output=True)

