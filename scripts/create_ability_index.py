import re
import json

# Read the markdown file
with open(r'../python-sc2.wiki\Unit-abilities-and-IDs.md', 'r') as f:
    lines = f.readlines()

# Create unit ID -> abilities mapping
unit_abilities = {}

for line in lines:
    # Skip header and separator lines
    if line.startswith('Id') or line.startswith('---') or not line.strip():
        continue
    
    # Split by | to get columns
    parts = line.split('|')
    if len(parts) >= 3:
        unit_id_str = parts[0].strip()
        unit_name = parts[1].strip()
        abilities_text = parts[2].strip()
        
        # Skip if no unit ID
        if not unit_id_str or not unit_id_str.isdigit():
            continue
        
        unit_id = int(unit_id_str)
        
        # Find all ability patterns like "ABILITY_NAME (123)"
        ability_matches = re.findall(r'([A-Z_0-9]+)\s*\((\d+)\)', abilities_text)
        
        # Store as ordered list (cmdIndex = position in list)
        unit_abilities[unit_id] = {
            'name': unit_name,
            'abilities': [
                {'name': name, 'id': int(ability_id)} 
                for name, ability_id in ability_matches
            ]
        }

# Save to JSON
with open('../unit_abilities_lookup.json', 'w') as f:
    json.dump(unit_abilities, f, indent=2)

print(f"Parsed {len(unit_abilities)} units")

# Test with your command
abil_link = 45
cmd_index = 0

if abil_link in unit_abilities:
    unit = unit_abilities[abil_link]
    print(f"\nAbilLink {abil_link} = {unit['name']}")
    if cmd_index < len(unit['abilities']):
        ability = unit['abilities'][cmd_index]
        print(f"CmdIndex {cmd_index} = {ability['name']} (ID: {ability['id']})")