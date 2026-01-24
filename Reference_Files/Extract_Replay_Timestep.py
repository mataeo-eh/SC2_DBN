"""
SC2 Replay State Parser
Extracts comprehensive game state at specific timesteps from SC2 replay files
"""

import mpyq
from s2protocol import versions
import json
from collections import defaultdict
import os


class ReplayStateParser:
    """Parse SC2 replays and extract game state at specific timestamps"""
    
    def __init__(self, ability_lookup_path='unit_abilities_lookup.json'):
        """
        Initialize the parser
        
        Args:
            ability_lookup_path: Path to the unit abilities lookup JSON file
        """
        self.unit_abilities = {}
        if os.path.exists(ability_lookup_path):
            with open(ability_lookup_path, 'r') as f:
                self.unit_abilities = json.load(f)
        else:
            print(f"Warning: Ability lookup file not found at {ability_lookup_path}")
            print("Ability names will show as 'Unknown'")
    
    def parse_at_timestep(self, replay_path, target_gameloop, command_window=100):
        """
        Extract all game state at a specific gameloop
        
        Args:
            replay_path: Path to the .SC2Replay file
            target_gameloop: The gameloop to extract state at
            command_window: How many gameloops before target to include commands
            
        Returns:
            dict: Complete game state at the target gameloop
        """
        archive = mpyq.MPQArchive(replay_path)
        
        # Get protocol version
        contents = archive.header['user_data_header']['content']
        header = versions.latest().decode_replay_header(contents)
        base_build = header['m_version']['m_baseBuild']
        protocol = versions.build(base_build)
        
        # Parse all events
        tracker_events = list(protocol.decode_replay_tracker_events(
            archive.read_file('replay.tracker.events')))
        game_events = list(protocol.decode_replay_game_events(
            archive.read_file('replay.game.events')))
        
        # Get replay details
        details = protocol.decode_replay_details(archive.read_file('replay.details'))
        
        # Track game state
        alive_units = {}  # unit_tag -> unit_info
        player_stats = {1: {}, 2: {}}
        upgrades = {1: [], 2: []}
        recent_commands = []
        
        # Process tracker events up to target_gameloop
        for event in tracker_events:
            if event['_gameloop'] > target_gameloop:
                break
                
            self._process_tracker_event(event, alive_units, player_stats, upgrades)
        
        # Process game events for recent commands
        for event in game_events:
            if event['_gameloop'] > target_gameloop:
                break
            if event['_gameloop'] < target_gameloop - command_window:
                continue
                
            if event['_event'] == 'NNet.Game.SCmdEvent' and event.get('m_abil'):
                cmd_info = self._parse_command_event(event)
                recent_commands.append(cmd_info)
        
        # Organize units by player
        units_by_player = {1: defaultdict(list), 2: defaultdict(list)}
        for tag, unit in alive_units.items():
            player = unit['owner']
            if player in [1, 2]:
                units_by_player[player][unit['type']].append(unit)
        
        # Create summary
        state = {
            'gameloop': target_gameloop,
            'time_seconds': target_gameloop / 22.4,
            'map_name': details['m_title'].decode(),
            'player_1': {
                'name': details['m_playerList'][0]['m_name'].decode(),
                'stats': player_stats[1],
                'units': {k: v for k, v in units_by_player[1].items()},
                'unit_counts': {k: len(v) for k, v in units_by_player[1].items()},
                'total_units': sum(len(v) for v in units_by_player[1].values()),
                'upgrades': upgrades[1]
            },
            'player_2': {
                'name': details['m_playerList'][1]['m_name'].decode(),
                'stats': player_stats[2],
                'units': {k: v for k, v in units_by_player[2].items()},
                'unit_counts': {k: len(v) for k, v in units_by_player[2].items()},
                'total_units': sum(len(v) for v in units_by_player[2].values()),
                'upgrades': upgrades[2]
            },
            'recent_commands': recent_commands
        }
        
        return state
    
    def _process_tracker_event(self, event, alive_units, player_stats, upgrades):
        """Process a single tracker event and update game state"""
        
        if event['_event'] == 'NNet.Replay.Tracker.SUnitBornEvent':
            unit_tag = (event['m_unitTagIndex'], event['m_unitTagRecycle'])
            alive_units[unit_tag] = {
                'type': event['m_unitTypeName'].decode(),
                'owner': event['m_controlPlayerId'],
                'x': event['m_x'],
                'y': event['m_y'],
                'born_loop': event['_gameloop']
            }
            
        elif event['_event'] == 'NNet.Replay.Tracker.SUnitDiedEvent':
            unit_tag = (event['m_unitTagIndex'], event['m_unitTagRecycle'])
            if unit_tag in alive_units:
                del alive_units[unit_tag]
                
        elif event['_event'] == 'NNet.Replay.Tracker.SUnitPositionsEvent':
            # Update positions from snapshot
            self._update_unit_positions(event, alive_units)
                    
        elif event['_event'] == 'NNet.Replay.Tracker.SPlayerStatsEvent':
            player_id = event['m_playerId']
            if 1 <= player_id <= 2:
                player_stats[player_id] = {
                    'minerals': event.get('m_scoreValueMineralsCurrent', 0),
                    'vespene': event.get('m_scoreValueVespeneCurrent', 0),
                    'minerals_collection_rate': event.get('m_scoreValueMineralsCollectionRate', 0),
                    'vespene_collection_rate': event.get('m_scoreValueVespeneCollectionRate', 0),
                    'workers_active': event.get('m_scoreValueWorkersActiveCount', 0),
                    'food_used': event.get('m_scoreValueFoodUsed', 0),
                    'food_made': event.get('m_scoreValueFoodMade', 0)
                }
                
        elif event['_event'] == 'NNet.Replay.Tracker.SUpgradeEvent':
            player_id = event['m_playerId']
            if 1 <= player_id <= 2:
                upgrades[player_id].append({
                    'name': event['m_upgradeTypeName'].decode(),
                    'completed_loop': event['_gameloop']
                })
    
    def _update_unit_positions(self, event, alive_units):
        """Update unit positions from SUnitPositionsEvent"""
        first_index = event['m_firstUnitIndex']
        items = event['m_items']
        
        # Items format: [unit_index, x, y, ...] in groups of 3
        for i in range(0, len(items), 3):
            if i + 2 < len(items):
                unit_index = first_index + items[i]
                x = items[i + 1]
                y = items[i + 2]
                
                # Find unit by index and update position
                for tag, unit in alive_units.items():
                    if tag[0] == unit_index:
                        unit['x'] = x
                        unit['y'] = y
    
    def _parse_command_event(self, event):
        """Parse a command event and decode ability information"""
        abil_link = event['m_abil']['m_abilLink']
        cmd_index = event['m_abil']['m_abilCmdIndex']
        
        # Decode ability
        ability_name = "Unknown"
        unit_name = "Unknown"
        
        if str(abil_link) in self.unit_abilities:
            unit = self.unit_abilities[str(abil_link)]
            unit_name = unit['name']
            if cmd_index < len(unit['abilities']):
                ability_name = unit['abilities'][cmd_index]['name']
        
        return {
            'gameloop': event['_gameloop'],
            'player': event['_userid']['m_userId'] + 1,
            'unit_type': unit_name,
            'ability': ability_name,
            'abil_link': abil_link,
            'cmd_index': cmd_index,
            'data': event['m_data']
        }
    
    def parse_multiple_timesteps(self, replay_path, gameloops):
        """
        Parse state at multiple timesteps
        
        Args:
            replay_path: Path to replay file
            gameloops: List of gameloops to sample
            
        Returns:
            list: Game states at each timestep
        """
        states = []
        for gameloop in gameloops:
            state = self.parse_at_timestep(replay_path, gameloop)
            states.append(state)
        return states
    
    def save_state(self, state, output_path):
        """Save game state to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        print(f"State saved to {output_path}")


def print_state_summary(state):
    """Print a human-readable summary of game state"""
    print(f"\n{'='*60}")
    print(f"Game State at {state['time_seconds']:.1f} seconds (gameloop {state['gameloop']})")
    print(f"Map: {state['map_name']}")
    print(f"{'='*60}")
    
    for player_num in [1, 2]:
        player_key = f'player_{player_num}'
        player = state[player_key]
        
        print(f"\n{player['name']} (Player {player_num}):")
        print(f"  Resources:")
        stats = player['stats']
        if stats:
            print(f"    Minerals: {stats.get('minerals', 'N/A')} (rate: {stats.get('minerals_collection_rate', 0)})")
            print(f"    Vespene:  {stats.get('vespene', 'N/A')} (rate: {stats.get('vespene_collection_rate', 0)})")
            print(f"    Workers:  {stats.get('workers_active', 0)}")
            print(f"    Supply:   {stats.get('food_used', 0)}/{stats.get('food_made', 0)}")
        
        print(f"  Total units: {player['total_units']}")
        
        if player['unit_counts']:
            print(f"  Unit composition:")
            for unit_type, count in sorted(player['unit_counts'].items(), 
                                          key=lambda x: x[1], reverse=True)[:10]:
                print(f"    {unit_type}: {count}")
        
        if player['upgrades']:
            print(f"  Upgrades completed: {len(player['upgrades'])}")
            for upgrade in player['upgrades'][:5]:
                print(f"    - {upgrade['name']}")
    
    print(f"\n  Recent commands: {len(state['recent_commands'])}")
    if state['recent_commands']:
        print(f"  Last 5 commands (with raw IDs):")
        for cmd in state['recent_commands'][-5:]:
            print(f"    Player {cmd['player']}: {cmd['unit_type']} (link:{cmd['abil_link']}, idx:{cmd['cmd_index']}) -> {cmd['ability']}")


# Example usage
if __name__ == "__main__":
    # Initialize parser
    parser = ReplayStateParser('unit_abilities_lookup.json')
    
    # Parse a replay at a specific timestep
    replay_path = r"replays\4533040_what_why_PylonAIE_v4.SC2Replay"
    target_gameloop = 500
    
    print("Parsing replay...")
    state = parser.parse_at_timestep(replay_path, target_gameloop)
    
    # Print summary
    print_state_summary(state)
    
    # Save to file
    #parser.save_state(state, 'game_state_500.json')
    
    # Example: Parse at multiple timesteps
    print("\n\nParsing at multiple timesteps...")
    timesteps = [100, 500, 1000, 1500, 2000]
    states = parser.parse_multiple_timesteps(replay_path, timesteps)
    
    print(f"\nExtracted {len(states)} timesteps")
    for i, s in enumerate(states):
        print(f"  Timestep {i+1}: {s['time_seconds']:.1f}s - "
              f"P1: {s['player_1']['total_units']} units, "
              f"P2: {s['player_2']['total_units']} units")