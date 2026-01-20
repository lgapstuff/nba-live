"""
NBA API client using nba_api library.
"""
import logging
import unicodedata
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Team names mapping (simplified version)
NBA_TEAM_NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DET": "Detroit Pistons", "IND": "Indiana Pacers", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "NY": "New York Knicks", "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers", "TOR": "Toronto Raptors", "WAS": "Washington Wizards",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "GS": "Golden State Warriors",
    "HOU": "Houston Rockets", "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies", "MIN": "Minnesota Timberwolves", "NO": "New Orleans Pelicans",
    "OKC": "Oklahoma City Thunder", "PHO": "Phoenix Suns", "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings", "SA": "San Antonio Spurs", "UTA": "Utah Jazz",
    "GSW": "Golden State Warriors", "NOP": "New Orleans Pelicans", "PHX": "Phoenix Suns", "NYK": "New York Knicks",
}

def get_team_name(abbreviation: str) -> str:
    """Get full team name from abbreviation."""
    if not abbreviation:
        return ""
    return NBA_TEAM_NAMES.get(abbreviation.upper().strip(), abbreviation)


class NBAClient:
    """
    Client for NBA API using nba_api library.
    """
    
    def __init__(self):
        """Initialize the client."""
        self._player_id_cache = {}
        try:
            from nba_api.stats.endpoints import playergamelog, commonteamroster, commonplayerinfo, boxscoretraditionalv2, scoreboardv2
            from nba_api.stats.library.parameters import SeasonType
            from nba_api.stats.static import players, teams
            self.playergamelog = playergamelog
            self.commonteamroster = commonteamroster
            self.commonplayerinfo = commonplayerinfo
            self.boxscoretraditionalv2 = boxscoretraditionalv2
            self.scoreboardv2 = scoreboardv2
            self.SeasonType = SeasonType
            self.players = players
            self.teams = teams
        except ImportError as e:
            logger.error(f"Failed to import nba_api: {e}")
            raise
    
    def _normalize_name(self, name: str) -> str:
        """Normalize player name by removing accents."""
        if not name:
            return ""
        normalized = unicodedata.normalize('NFD', name)
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn').lower().strip()
    
    def get_player_game_log(self, player_id: int, season: Optional[str] = None, 
                           season_type: str = "Regular Season") -> List[Dict[str, Any]]:
        """Get game log for a specific player."""
        try:
            if not season:
                current_year = datetime.now().year
                if datetime.now().month < 10:
                    season = f"{current_year - 1}-{str(current_year)[2:]}"
                else:
                    season = f"{current_year}-{str(current_year + 1)[2:]}"
            
            logger.info(f"[NBA API] Fetching game log for player {player_id}, season {season}")
            
            season_type_enum = getattr(self.SeasonType, 'playoffs', self.SeasonType.regular) if season_type == "Playoffs" else self.SeasonType.regular
            
            game_log = self.playergamelog.PlayerGameLog(
                player_id=str(player_id),
                season=season,
                season_type_all_star=season_type_enum
            )
            
            data_frames = game_log.get_data_frames()
            if not data_frames or len(data_frames) == 0:
                return []
            
            df = data_frames[0]
            if df.empty:
                return []
            
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error fetching game log: {e}")
            return []
    
    def get_player_last_n_games(self, player_id: int, n: int = 10, 
                                season: Optional[str] = None,
                                season_type: str = "Regular Season") -> List[Dict[str, Any]]:
        """Get last N games for a specific player."""
        try:
            games = self.get_player_game_log(player_id, season, season_type)
            return games[:n]
        except Exception as e:
            logger.error(f"Error fetching last {n} games: {e}")
            return []
    
    def find_nba_player_id_by_name(self, player_name: str) -> Optional[int]:
        """Find NBA official player ID by player name."""
        try:
            if player_name in self._player_id_cache:
                return self._player_id_cache[player_name]
            
            all_players = self.players.get_players()
            player_name_normalized = self._normalize_name(player_name)
            
            for player in all_players:
                full_name = player.get('full_name', '')
                full_name_normalized = self._normalize_name(full_name)
                if full_name_normalized == player_name_normalized:
                    nba_id = player.get('id')
                    if nba_id:
                        self._player_id_cache[player_name] = nba_id
                        return nba_id
            
            name_parts = player_name_normalized.split()
            for player in all_players:
                full_name = player.get('full_name', '')
                full_name_normalized = self._normalize_name(full_name)
                if len(name_parts) > 0 and all(part in full_name_normalized for part in name_parts):
                    nba_id = player.get('id')
                    if nba_id:
                        self._player_id_cache[player_name] = nba_id
                        return nba_id
            
            return None
        except Exception as e:
            logger.error(f"Error finding NBA player ID: {e}")
            return None
    
    def get_team_players(self, team_abbr: str, season: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all players for a specific team from NBA API."""
        try:
            team_name = get_team_name(team_abbr)
            nba_teams = self.teams.get_teams()
            team_id = None
            
            for team in nba_teams:
                if (team.get('full_name', '').lower() == team_name.lower() or 
                    team.get('abbreviation', '').upper() == team_abbr.upper()):
                    team_id = team.get('id')
                    break
            
            if not team_id:
                return []
            
            if not season:
                current_year = datetime.now().year
                if datetime.now().month < 10:
                    season = f"{current_year - 1}-{str(current_year)[2:]}"
                else:
                    season = f"{current_year}-{str(current_year + 1)[2:]}"
            
            roster = self.commonteamroster.CommonTeamRoster(team_id=team_id, season=season)
            data_frames = roster.get_data_frames()
            
            if not data_frames or len(data_frames) == 0:
                return []
            
            df = data_frames[0]
            if df.empty:
                return []
            
            players_list = df.to_dict('records')
            formatted_players = []
            for player in players_list:
                player_id = player.get('PLAYER_ID')
                player_name = player.get('PLAYER', '')
                if not player_id or not player_name:
                    continue
                formatted_players.append({
                    'id': player_id,
                    'full_name': player_name,
                    'team_id': team_id,
                    'team_abbreviation': team_abbr,
                    'position': player.get('POSITION', ''),
                    'jersey_number': player.get('NUM', '')
                })
            
            return formatted_players
        except Exception as e:
            logger.error(f"Error fetching team players: {e}")
            return []

    def get_player_profile(self, player_id: int) -> Dict[str, Any]:
        """Get player profile details (height, weight, age, etc.)."""
        try:
            profile = self.commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            data_frames = profile.get_data_frames()
            if not data_frames or len(data_frames) == 0:
                return {}
            df = data_frames[0]
            if df.empty:
                return {}
            row = df.iloc[0].to_dict()
            return {
                "player_id": player_id,
                "full_name": row.get("DISPLAY_FIRST_LAST") or row.get("PLAYER_NAME"),
                "height": row.get("HEIGHT"),
                "weight": row.get("WEIGHT"),
                "birth_date": row.get("BIRTHDATE"),
                "age": row.get("PLAYER_AGE"),
                "position": row.get("POSITION"),
                "school": row.get("SCHOOL"),
                "country": row.get("COUNTRY"),
                "experience": row.get("SEASON_EXP")
            }
        except Exception as e:
            logger.error(f"Error fetching player profile: {e}")
            return {}
    
    def get_live_boxscore(self, game_id: str, player_ids: Optional[List[int]] = None) -> Any:
        """Get live boxscore statistics for a game."""
        try:
            boxscore = self.boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
            data_frames = boxscore.get_data_frames()
            
            if not data_frames or len(data_frames) == 0:
                return [] if not player_ids else {}
            
            df = data_frames[0]
            if df.empty:
                return [] if not player_ids else {}
            
            player_stats = df.to_dict('records')
            if player_ids:
                result = {}
                for stat in player_stats:
                    player_id = stat.get('PLAYER_ID')
                    if player_id and player_id in player_ids:
                        result[player_id] = {
                            'PTS': stat.get('PTS', 0),
                            'AST': stat.get('AST', 0),
                            'REB': stat.get('REB', 0),
                            'MIN': stat.get('MIN', '0:00'),
                            'FGM': stat.get('FGM', 0),
                            'FGA': stat.get('FGA', 0),
                            'FG3M': stat.get('FG3M', 0),
                            'FG3A': stat.get('FG3A', 0),
                            'FTM': stat.get('FTM', 0),
                            'FTA': stat.get('FTA', 0),
                            'TOV': stat.get('TOV', 0),
                            'STL': stat.get('STL', 0),
                            'BLK': stat.get('BLK', 0),
                            'PF': stat.get('PF', 0),
                            'PLAYER_NAME': stat.get('PLAYER_NAME', ''),
                            'START_POSITION': stat.get('START_POSITION'),
                            'TEAM_ABBREVIATION': stat.get('TEAM_ABBREVIATION', ''),
                        }
                return result

            return [
                {
                    'PLAYER_ID': stat.get('PLAYER_ID'),
                    'PLAYER_NAME': stat.get('PLAYER_NAME', ''),
                    'TEAM_ABBREVIATION': stat.get('TEAM_ABBREVIATION', ''),
                    'START_POSITION': stat.get('START_POSITION'),
                    'MIN': stat.get('MIN', '0:00'),
                    'PTS': stat.get('PTS', 0),
                    'AST': stat.get('AST', 0),
                    'REB': stat.get('REB', 0),
                    'FGM': stat.get('FGM', 0),
                    'FGA': stat.get('FGA', 0),
                    'FG3M': stat.get('FG3M', 0),
                    'FG3A': stat.get('FG3A', 0),
                    'FTM': stat.get('FTM', 0),
                    'FTA': stat.get('FTA', 0),
                    'TOV': stat.get('TOV', 0),
                    'STL': stat.get('STL', 0),
                    'BLK': stat.get('BLK', 0),
                    'PF': stat.get('PF', 0),
                }
                for stat in player_stats
            ]
        except Exception as e:
            logger.error(f"Error fetching live boxscore: {e}")
            return [] if not player_ids else {}

    def get_game_status(self, game_id: str, game_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get live game status (period/clock) for a specific NBA GameID.
        """
        def to_scoreboard_date(date_str: str) -> Optional[str]:
            try:
                date_str = str(date_str).strip()
                if '-' in date_str and len(date_str) >= 10:
                    return datetime.strptime(date_str[:10], '%Y-%m-%d').strftime('%m/%d/%Y')
                if '/' in date_str and len(date_str.split('/')) == 3:
                    # Already in MM/DD/YYYY
                    return date_str
            except Exception:
                return None
            return None

        try:
            from datetime import timedelta, date
            dates_to_try = []
            if game_date:
                scoreboard_date = to_scoreboard_date(game_date)
                if scoreboard_date:
                    dates_to_try.append(scoreboard_date)
            else:
                today = datetime.now().date()
                for offset in [0, -1, 1]:
                    dates_to_try.append((today + timedelta(days=offset)).strftime('%m/%d/%Y'))

            for try_date in dates_to_try:
                try:
                    scoreboard = self.scoreboardv2.ScoreboardV2(game_date=try_date)
                    # Try dict format first
                    try:
                        scoreboard_dict = scoreboard.get_dict()
                        if scoreboard_dict and 'resultSets' in scoreboard_dict:
                            result_sets = scoreboard_dict.get('resultSets', [])
                            if result_sets and len(result_sets) > 0:
                                game_header = result_sets[0]
                                headers = game_header.get('headers', [])
                                rows = game_header.get('rowSet', [])
                                for row in rows:
                                    row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                                    if row_dict.get('GAME_ID') == game_id:
                                        return row_dict
                    except Exception:
                        pass

                    # Fallback to dataframe
                    data_frames = scoreboard.get_data_frames()
                    if data_frames and len(data_frames) > 0:
                        df = data_frames[0]
                        if df is not None and not (hasattr(df, 'empty') and df.empty):
                            games = df.to_dict('records')
                            for game in games:
                                if game.get('GAME_ID') == game_id:
                                    return game
                except Exception:
                    continue

            return None
        except Exception as e:
            logger.error(f"Error fetching game status: {e}")
            return None
    
    def find_nba_game_id(self, home_team_abbr: str, away_team_abbr: str, game_date: str = None) -> Optional[str]:
        """Find NBA GameID by matching teams and date."""
        try:
            from datetime import timedelta, date
            
            if not game_date:
                game_date = datetime.now().strftime("%Y-%m-%d")
            
            if isinstance(game_date, (date, datetime)):
                game_date = game_date.strftime("%Y-%m-%d")
            
            dates_to_try = []
            try:
                game_date_obj = datetime.strptime(game_date, "%Y-%m-%d")
                dates_to_try.append(game_date_obj.strftime("%Y-%m-%d"))
                dates_to_try.extend([
                    (game_date_obj - timedelta(days=1)).strftime("%Y-%m-%d"),
                    (game_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                ])
            except:
                dates_to_try.append(str(game_date))
            
            for try_date in dates_to_try:
                try:
                    scoreboard_data = self.scoreboardv2.ScoreboardV2(game_date=try_date)
                    
                    try:
                        scoreboard_dict = scoreboard_data.get_dict()
                        if scoreboard_dict and 'resultSets' in scoreboard_dict:
                            result_sets = scoreboard_dict.get('resultSets', [])
                            if result_sets and len(result_sets) > 0:
                                game_header = result_sets[0]
                                if 'rowSet' in game_header:
                                    headers = game_header.get('headers', [])
                                    rows = game_header.get('rowSet', [])
                                    games = []
                                    for row in rows:
                                        game_dict = {}
                                        for i, header in enumerate(headers):
                                            if i < len(row):
                                                game_dict[header] = row[i]
                                        games.append(game_dict)
                                    
                                    for game in games:
                                        home_team = game.get('HOME_TEAM_ABBREVIATION', '')
                                        away_team = game.get('VISITOR_TEAM_ABBREVIATION', '')
                                        game_id = game.get('GAME_ID', '')
                                        
                                        if (home_team.upper() == home_team_abbr.upper() and 
                                            away_team.upper() == away_team_abbr.upper()):
                                            return game_id
                    except:
                        pass
                    
                    data_frames = scoreboard_data.get_data_frames()
                    if data_frames and len(data_frames) > 0:
                        df = data_frames[0]
                        if df is not None and not (hasattr(df, 'empty') and df.empty):
                            games = df.to_dict('records')
                            for game in games:
                                home_team = game.get('HOME_TEAM_ABBREVIATION', '')
                                away_team = game.get('VISITOR_TEAM_ABBREVIATION', '')
                                game_id = game.get('GAME_ID', '')
                                
                                if (home_team.upper() == home_team_abbr.upper() and 
                                    away_team.upper() == away_team_abbr.upper()):
                                    return game_id
                except:
                    continue
            
            return None
        except Exception as e:
            logger.error(f"Error finding GameID: {e}")
            return None
