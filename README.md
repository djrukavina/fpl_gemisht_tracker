# FPL League Web Service

A comprehensive Fantasy Premier League (FPL) web application that displays league standings, team compositions, player details, fixtures, and match statistics for league ID 91460.

## Features

- **FPL League Standings**: View current league rankings with manager names, team names, and total points
- **Team Details**: Click on teams to see current squad composition with captain/vice-captain info
- **Player Profiles**: Detailed player information with performance history and statistics
- **Premier League Standings**: Full Premier League table with wins, draws, losses, goals, form, and next opponents
- **Fixtures**: Browse current and past gameweek fixtures with match details
- **Match Statistics**: Comprehensive match data including goals, assists, cards, saves, and bonus points

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, Bootstrap 5
- **Data Source**: Fantasy Premier League API
- **Deployment**: Render

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
4. Open http://localhost:5000 in your browser

## Deployment to Render

1. **Connect Repository**: Link your GitHub repository to Render
2. **Service Configuration**:
   - **Service Type**: Web Service
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app`
3. **Environment Variables**: None required (uses FPL public API)
4. **Deploy**: Render will automatically build and deploy your application

## Project Structure

```
FPL 2027/
├── main.py                 # Flask application
├── requirements.txt        # Python dependencies
├── templates/              # HTML templates
│   ├── index.html         # FPL league standings
│   ├── team.html          # Team squad details
│   ├── player.html        # Player profile
│   ├── plteam.html        # Premier League team squad
│   ├── fixtures.html      # Gameweek fixtures
│   ├── match.html         # Match details
│   └── standings.html     # Premier League standings
└── README.md              # This file
```

## API Endpoints

- `/` - FPL League standings
- `/team/<entry_id>` - Team squad details
- `/player/<player_id>` - Player profile
- `/plteam/<team_id>` - Premier League team squad
- `/fixtures` - Current gameweek fixtures
- `/fixtures/<gw>` - Specific gameweek fixtures
- `/standings` - Premier League standings table
- `/match/<fixture_id>` - Match details and statistics

## License

This project is for educational purposes only. Please respect Fantasy Premier League's terms of service.
