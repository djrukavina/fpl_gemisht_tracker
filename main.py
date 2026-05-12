from flask import Flask, render_template
import requests
import os

app = Flask(__name__)

@app.route('/')
def index():
    response = requests.get('https://fantasy.premierleague.com/api/leagues-classic/91460/standings/')
    data = response.json()
    standings = data['standings']['results']
    league_name = data['league']['name']
    return render_template('index.html', standings=standings, league_name=league_name)

@app.route('/team/<int:entry_id>')
def team(entry_id):
    # Fetch static data for players and current GW
    static_resp = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    static_data = static_resp.json()
    players = {p['id']: p for p in static_data['elements']}
    teams = {t['id']: t for t in static_data['teams']}
    events = static_data['events']
    current_gw = next((e['id'] for e in events if e['is_current']), max(e['id'] for e in events))
    
    # Fetch manager data for team name
    manager_resp = requests.get(f'https://fantasy.premierleague.com/api/entry/{entry_id}/')
    manager_data = manager_resp.json()
    team_name = manager_data['name']
    
    # Fetch current picks
    picks_resp = requests.get(f'https://fantasy.premierleague.com/api/entry/{entry_id}/event/{current_gw}/picks/')
    picks_data = picks_resp.json()
    picks = picks_data['picks']
    
    # Fetch live data for current gameweek
    live_resp = requests.get(f'https://fantasy.premierleague.com/api/event/{current_gw}/live/')
    live_data = live_resp.json()
    live_elements = {elem['id']: elem for elem in live_data.get('elements', [])}
    
    # Prepare player list
    team_players = []
    for pick in picks:
        player_id = pick['element']
        player = players[player_id]
        position_names = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        
        # Get live points if available, otherwise use event_points
        live_player_data = live_elements.get(player_id, {})
        points = live_player_data.get('stats', {}).get('total_points', pick.get('event_points', 0))
        
        # Check if player is captain or vice-captain
        is_captain = pick.get('is_captain', False)
        is_vice_captain = pick.get('is_vice_captain', False)
        
        # Calculate actual points with captain/vice-captain multiplier
        minutes_played = live_player_data.get('stats', {}).get('minutes', 0)
        actual_points = points
        
        if is_captain and minutes_played > 0:
            actual_points = points * 2
        elif is_vice_captain:
            # Vice captain only gets double if captain didn't play
            # This is handled after checking all players' minutes
            pass
        
        team_players.append({
            'name': player['web_name'],
            'position': position_names.get(player['element_type'], 'UNK'),
            'points': points,
            'actual_points': actual_points,
            'is_sub': pick['position'] > 11,
            'is_captain': is_captain,
            'is_vice_captain': is_vice_captain,
            'minutes_played': minutes_played,
            'player_id': player_id,
            'code': player['code'],
            'team_id': player['team'],
            'badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{teams.get(player['team'], {}).get('code', player['team'])}.svg"
        })
    
    # Handle vice-captain double points if captain didn't play
    captain = next((p for p in team_players if p['is_captain']), None)
    vice_captain = next((p for p in team_players if p['is_vice_captain']), None)
    
    if captain and captain['minutes_played'] == 0 and vice_captain:
        vice_captain['actual_points'] = vice_captain['points'] * 2
    
    return render_template('team.html', team_name=team_name, players=team_players)

@app.route('/player/<int:player_id>')
def player(player_id):
    # Fetch static data for player info
    static_resp = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    static_data = static_resp.json()
    players_list = {p['id']: p for p in static_data['elements']}
    teams = {t['id']: t for t in static_data['teams']}
    position_names = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    
    # Get player info
    player_info = players_list.get(player_id)
    if not player_info:
        return "Player not found", 404
    
    # Fetch player fixture history
    summary_resp = requests.get(f'https://fantasy.premierleague.com/api/element-summary/{player_id}/')
    summary_data = summary_resp.json()
    fixture_history = summary_data.get('history', [])
    
    # Get last 8 matches
    last_8_matches = fixture_history[-8:] if fixture_history else []
    
    # Calculate average points safely
    games_played = len(fixture_history)
    avg_points = round(player_info['total_points'] / games_played, 2) if games_played > 0 else 0
    
    player_details = {
        'name': player_info['first_name'] + ' ' + player_info['second_name'],
        'player_id': player_id,
        'code': player_info['code'],
        'team': teams.get(player_info['team'], {}).get('name', 'N/A'),
        'team_id': player_info['team'],
        'team_code': teams.get(player_info['team'], {}).get('code'),
        'position': position_names.get(player_info['element_type'], 'UNK'),
        'total_points': player_info['total_points'],
        'avg_points': avg_points,
        'games_played': games_played,
        'value': player_info['now_cost'] / 10,
        'badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{teams.get(player_info['team'], {}).get('code', player_info['team'])}.svg"
    }
    
    # Prepare last 8 matches data
    matches = []
    for match in last_8_matches:
        matches.append({
            'gw': match['round'],
            'points': match['total_points'],
            'minutes': match['minutes'],
            'goals': match['goals_scored'],
            'assists': match['assists'],
            'clean_sheets': match['clean_sheets'],
            'bonus': match['bonus']
        })
    
    # Reverse to show most recent first
    matches.reverse()
    
    return render_template('player.html', player=player_details, matches=matches)

@app.route('/plteam/<int:team_id>')
def plteam(team_id):
    # Fetch static data
    static_resp = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    static_data = static_resp.json()
    teams = {t['id']: t for t in static_data['teams']}
    position_names = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    
    # Get team info
    team_info = teams.get(team_id)
    if not team_info:
        return "Team not found", 404
    
    # Get all players for this team
    all_players = [p for p in static_data['elements'] if p['team'] == team_id]
    
    # Group players by position and sort by total points (descending)
    players_by_position = {
        'GK': [],
        'DEF': [],
        'MID': [],
        'FWD': []
    }

    # Regions
    regions_resp = requests.get('https://fantasy.premierleague.com/api/regions/')
    regions_data = regions_resp.json()
    unicode_mismatch = {
        'en': 'gb-eng',
        'nn': 'gb-nir',
        's1': 'gb-sct',
        'wa': 'gb-wls',
    }
    region_map = {
        r["id"]: {
            "name": r["name"],
            "flag": f"https://flagcdn.com/w40/{r['iso_code_short'].lower() if r['iso_code_short'].lower() not in unicode_mismatch else unicode_mismatch[r['iso_code_short'].lower()]}.png"
        }
        for r in regions_data
    }

    # Status
    status_map = {
        "a": "Available",
        "d": "Doubtful",
        "i": "Injured",
        "s": "Suspended",
        "u": "Unavailable",
        "n": "Not Available"
    }

    for player in all_players:
        pos_key = position_names.get(player['element_type'], 'UNK')
        players_by_position[pos_key].append({
            'name': player['web_name'],
            'player_id': player['id'],
            'code': player['code'],
            'total_points': player['total_points'],
            'value': player['now_cost'] / 10,
            'status': status_map[player['status']] or 'Available',
            'region': region_map.get(player['region'])['name'] if player['region'] in region_map else 'Unknown',
            'region_flag': region_map.get(player['region'])['flag'] if player['region'] in region_map else None,
        })
    
    # Sort each position by total points descending
    for pos in players_by_position:
        players_by_position[pos].sort(key=lambda x: x['total_points'], reverse=True)
    
    team_details = {
        'name': team_info['name'],
        'badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{team_info['code']}.svg"
    }
    
    return render_template('plteam.html', team=team_details, players=players_by_position)

@app.route('/fixtures')
@app.route('/fixtures/<int:gw>')
def fixtures(gw=None):
    # Fetch static data
    static_resp = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    static_data = static_resp.json()
    events = static_data['events']
    teams = {t['id']: t for t in static_data['teams']}
    
    # Determine GW
    if gw is None:
        current_gw = next((e['id'] for e in events if e['is_current']), max(e['id'] for e in events))
    else:
        current_gw = gw
    
    # Fetch all fixtures
    fixtures_resp = requests.get('https://fantasy.premierleague.com/api/fixtures/')
    fixtures_data = fixtures_resp.json()
    
    # Fetch live data if it's the current GW
    live_data = {}
    try:
        live_resp = requests.get(f'https://fantasy.premierleague.com/api/event/{current_gw}/live/')
        live_response = live_resp.json()
        live_data = {elem['id']: elem for elem in live_response.get('elements', [])}
    except:
        pass
    
    # Filter fixtures for current GW
    gw_fixtures = [f for f in fixtures_data if f['event'] == current_gw]
    
    # Prepare fixtures list
    fixtures_list = []
    for f in gw_fixtures:
        home_team = teams[f['team_h']]
        away_team = teams[f['team_a']]
        fixture = {
            'id': f['id'],
            'home_team': home_team['name'],
            'away_team': away_team['name'],
            'home_badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{home_team['code']}.svg",
            'away_badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{away_team['code']}.svg",
            'finished': f['finished'],
            'home_score': f['team_h_score'],
            'away_score': f['team_a_score'],
            'kickoff_time': f['kickoff_time']
        }
        fixtures_list.append(fixture)
    
    # Get prev and next GW
    prev_gw = current_gw - 1 if current_gw > 1 else None
    next_gw = current_gw + 1 if current_gw < len(events) else None
    
    return render_template('fixtures.html', fixtures=fixtures_list, current_gw=current_gw, prev_gw=prev_gw, next_gw=next_gw)

@app.route('/standings')
def standings():
    # Fetch static data
    static_resp = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    static_data = static_resp.json()
    teams = {t['id']: t for t in static_data['teams']}
    
    # Fetch all fixtures
    fixtures_resp = requests.get('https://fantasy.premierleague.com/api/fixtures/')
    fixtures_data = fixtures_resp.json()
    
    # Calculate standings
    standings_dict = {}
    for team_id, team_info in teams.items():
        standings_dict[team_id] = {
            'team_id': team_id,
            'name': team_info['name'],
            'code': team_info['code'],
            'badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{team_info['code']}.svg",
            'played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'points': 0,
            'form': [],
            'next_opponent': None
        }
    
    # Process fixtures
    for fixture in fixtures_data:
        if fixture['finished']:
            home_team_id = fixture['team_h']
            away_team_id = fixture['team_a']
            home_goals = fixture['team_h_score']
            away_goals = fixture['team_a_score']
            
            # Update matches played and goals
            standings_dict[home_team_id]['played'] += 1
            standings_dict[away_team_id]['played'] += 1
            standings_dict[home_team_id]['goals_for'] += home_goals
            standings_dict[home_team_id]['goals_against'] += away_goals
            standings_dict[away_team_id]['goals_for'] += away_goals
            standings_dict[away_team_id]['goals_against'] += home_goals
            
            # Determine result
            if home_goals > away_goals:
                standings_dict[home_team_id]['wins'] += 1
                standings_dict[home_team_id]['points'] += 3
                standings_dict[away_team_id]['losses'] += 1
                standings_dict[home_team_id]['form'].append('W')
                standings_dict[away_team_id]['form'].append('L')
            elif home_goals < away_goals:
                standings_dict[away_team_id]['wins'] += 1
                standings_dict[away_team_id]['points'] += 3
                standings_dict[home_team_id]['losses'] += 1
                standings_dict[away_team_id]['form'].append('W')
                standings_dict[home_team_id]['form'].append('L')
            else:
                standings_dict[home_team_id]['draws'] += 1
                standings_dict[away_team_id]['draws'] += 1
                standings_dict[home_team_id]['points'] += 1
                standings_dict[away_team_id]['points'] += 1
                standings_dict[home_team_id]['form'].append('D')
                standings_dict[away_team_id]['form'].append('D')
    
    # Set next opponent
    for fixture in fixtures_data:
        if not fixture['finished']:
            home_team_id = fixture['team_h']
            away_team_id = fixture['team_a']
            home_team = teams[home_team_id]
            away_team = teams[away_team_id]
            
            standings_dict[home_team_id]['next_opponent'] = {
                'name': away_team['name'],
                'badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{away_team['code']}.svg",
                'is_home': True,
                'kickoff': fixture['kickoff_time']
            }
            standings_dict[away_team_id]['next_opponent'] = {
                'name': home_team['name'],
                'badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{home_team['code']}.svg",
                'is_home': False,
                'kickoff': fixture['kickoff_time']
            }
    
    # Convert to list and sort by points
    standings_list = list(standings_dict.values())
    standings_list.sort(key=lambda x: (-x['points'], -(x['goals_for'] - x['goals_against']), -x['goals_for']))
    
    # Keep only last 5 form
    for team in standings_list:
        team['form'] = team['form'][-5:] if team['form'] else []
    
    return render_template('standings.html', standings=standings_list)

@app.route('/match/<int:fixture_id>')
def match(fixture_id):
    # Fetch static data
    static_resp = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    static_data = static_resp.json()
    players_dict = {p['id']: p for p in static_data['elements']}
    teams = {t['id']: t for t in static_data['teams']}
    
    # Fetch all fixtures to find the specific one
    fixtures_resp = requests.get('https://fantasy.premierleague.com/api/fixtures/')
    fixtures_data = fixtures_resp.json()
    fixture = next((f for f in fixtures_data if f['id'] == fixture_id), None)
    
    if not fixture:
        return "Match not found", 404
    
    gw = fixture['event']
    home_team_id = fixture['team_h']
    away_team_id = fixture['team_a']
    
    # Fetch live data for the gameweek
    live_data = {}
    try:
        live_resp = requests.get(f'https://fantasy.premierleague.com/api/event/{gw}/live/')
        live_response = live_resp.json()
        live_data = {elem['id']: elem for elem in live_response.get('elements', [])}
    except:
        pass
    
    # Get players for home and away teams
    home_players = [p for p in static_data['elements'] if p['team'] == home_team_id]
    away_players = [p for p in static_data['elements'] if p['team'] == away_team_id]
    
    # Organize player stats by category
    def organize_player_stats(players_list, live_data):
        stats = {
            'goalscorers': [],
            'assists': [],
            'yellow_cards': [],
            'red_cards': [],
            'own_goals': [],
            'saves': [],
            'bonus_points': []
        }
        
        for player in players_list:
            player_id = player['id']
            if player_id not in live_data:
                continue
            
            live_player = live_data[player_id]
            player_stats = live_player.get('stats', {})
            
            player_info = {
                'name': player['web_name'],
                'position': {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}.get(player['element_type'], 'UNK'),
                'code': player['code'],
                'player_id': player_id
            }
            
            # Goals
            goals = player_stats.get('goals_scored', 0)
            if goals > 0:
                stats['goalscorers'].append({**player_info, 'count': goals})
            
            # Assists
            assists = player_stats.get('assists', 0)
            if assists > 0:
                stats['assists'].append({**player_info, 'count': assists})
            
            # Yellow cards
            yellow = player_stats.get('yellow_cards', 0)
            if yellow > 0:
                stats['yellow_cards'].append({**player_info, 'count': yellow})
            
            # Red cards
            red = player_stats.get('red_cards', 0)
            if red > 0:
                stats['red_cards'].append({**player_info, 'count': red})
            
            # Own goals
            own = player_stats.get('own_goals', 0)
            if own > 0:
                stats['own_goals'].append({**player_info, 'count': own})
            
            # Saves
            saves = player_stats.get('saves', 0)
            if saves > 0:
                stats['saves'].append({**player_info, 'count': saves})
            
            # Bonus points
            bonus = player_stats.get('bonus', 0)
            if bonus > 0:
                stats['bonus_points'].append({**player_info, 'bonus': bonus})

        stats['bonus_points'].sort(key=lambda x: x['bonus'], reverse=True)
        return stats
    
    home_stats = organize_player_stats(home_players, live_data)
    away_stats = organize_player_stats(away_players, live_data)
    
    # Collect all players with their points for the match
    def get_players_with_points(players_list, live_data):
        players_points = []
        for player in players_list:
            player_id = player['id']
            if player_id not in live_data:
                continue
            
            live_player = live_data[player_id]
            player_stats = live_player.get('stats', {})
            points = player_stats.get('total_points', 0)
            minutes = player_stats.get('minutes', 0)
            
            # Only include players who actually played (minutes > 0)
            if minutes > 0:
                players_points.append({
                    'name': player['web_name'],
                    'position': {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}.get(player['element_type'], 'UNK'),
                    'code': player['code'],
                    'player_id': player_id,
                    'points': points,
                    'minutes': minutes
                })
        
        # Sort by points descending
        players_points.sort(key=lambda x: x['points'], reverse=True)
        return players_points
    
    home_players_points = get_players_with_points(home_players, live_data)
    away_players_points = get_players_with_points(away_players, live_data)
    
    match_details = {
        'fixture_id': fixture_id,
        'home_team': teams[home_team_id]['name'],
        'away_team': teams[away_team_id]['name'],
        'home_badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{teams[home_team_id]['code']}.svg",
        'away_badge': f"https://resources.premierleague.com/premierleague25/badges-alt/{teams[away_team_id]['code']}.svg",
        'home_score': fixture['team_h_score'],
        'away_score': fixture['team_a_score'],
        'finished': fixture['finished'],
        'gw': gw,
        'home_stats': home_stats,
        'away_stats': away_stats,
        'home_players_points': home_players_points,
        'away_players_points': away_players_points
    }
    
    return render_template('match.html', match=match_details)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
