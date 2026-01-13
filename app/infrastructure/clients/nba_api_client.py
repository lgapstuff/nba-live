"""
NBA API client using nba_api library.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.domain.ports.nba_api_port import NBAPort
from app.domain.value_objects.team_names import get_team_name

logger = logging.getLogger(__name__)


class NBAClient(NBAPort):
    """
    Client for NBA API using nba_api library.
    """
    
    def __init__(self):
        """
        Initialize the client.
        """
        self._player_id_cache = {}  # Cache for player name -> NBA player_id mapping
        try:
            from nba_api.stats.endpoints import playergamelog, commonteamroster
            from nba_api.stats.library.parameters import SeasonType
            from nba_api.stats.static import players, teams
            self.playergamelog = playergamelog
            self.commonteamroster = commonteamroster
            self.SeasonType = SeasonType
            self.players = players
            self.teams = teams
        except ImportError as e:
            logger.error(f"Failed to import nba_api: {e}")
            logger.error("Please install nba_api: pip install nba_api")
            raise
    
    def get_player_game_log(self, player_id: int, season: Optional[str] = None, 
                           season_type: str = "Regular Season") -> List[Dict[str, Any]]:
        """
        Get game log for a specific player.
        
        Args:
            player_id: NBA player ID
            season: Season in format "YYYY-YY" (e.g., "2023-24"). If None, uses current season.
            season_type: Type of season - "Regular Season" or "Playoffs" (default: "Regular Season")
            
        Returns:
            List of game dictionaries with player statistics
        """
        try:
            # If season is not provided, use current season
            if not season:
                current_year = datetime.now().year
                # NBA season spans two years (e.g., 2023-24)
                # If we're before October, use previous season
                if datetime.now().month < 10:
                    season = f"{current_year - 1}-{str(current_year)[2:]}"
                else:
                    season = f"{current_year}-{str(current_year + 1)[2:]}"
            
            logger.info(f"Fetching game log for player {player_id}, season {season}, type {season_type}")
            
            # Get player game log
            # PlayerGameLog uses season_type_all_star parameter
            # SeasonType.regular exists (not regular_season)
            # For regular season, use SeasonType.regular or SeasonType.default
            # For playoffs, check if it exists, otherwise use regular
            if season_type == "Playoffs":
                # Try playoffs attribute, if it doesn't exist, use regular
                season_type_enum = getattr(self.SeasonType, 'playoffs', self.SeasonType.regular)
            else:
                # For regular season, use SeasonType.regular
                season_type_enum = self.SeasonType.regular
            
            game_log = self.playergamelog.PlayerGameLog(
                player_id=str(player_id),
                season=season,
                season_type_all_star=season_type_enum
            )
            
            # Get data frames - may return empty list if no games found
            data_frames = game_log.get_data_frames()
            
            if not data_frames or len(data_frames) == 0:
                logger.warning(f"No games found for player {player_id} in season {season}")
                return []
            
            # Get first data frame (game log)
            df = data_frames[0]
            
            # Check if dataframe is empty
            if df.empty:
                logger.warning(f"No games found for player {player_id} in season {season}")
                return []
            
            # Convert to list of dictionaries
            games = df.to_dict('records')
            
            logger.info(f"Retrieved {len(games)} games for player {player_id}")
            
            return games
            
        except ValueError as e:
            # Handle JSON parsing errors (empty response, invalid JSON)
            error_msg = str(e)
            if "Expecting value" in error_msg or "line 1 column 1" in error_msg:
                logger.warning(f"No games found for player {player_id} (empty response from NBA API)")
            else:
                logger.warning(f"Error fetching game log for player {player_id}: {e}")
            return []
        except Exception as e:
            error_msg = str(e)
            # Check for pandas import error
            if "pandas" in error_msg.lower() or "DataFrame" in error_msg:
                logger.error(f"Pandas not available for player {player_id}: {e}")
                logger.error("Please install pandas: pip install pandas")
            else:
                logger.warning(f"Error fetching game log for player {player_id}: {e}")
            return []
    
    def find_nba_player_id_by_name(self, player_name: str) -> Optional[int]:
        """
        Find NBA official player ID by player name.
        Uses fuzzy matching to find the closest match.
        
        Args:
            player_name: Player name (e.g., "Keyonte George")
            
        Returns:
            NBA player ID or None if not found
        """
        try:
            # Check cache first
            if player_name in self._player_id_cache:
                return self._player_id_cache[player_name]
            
            # Get all players from NBA API
            all_players = self.players.get_players()
            
            player_name_lower = player_name.lower().strip()
            
            # Try exact match first
            for player in all_players:
                full_name = player.get('full_name', '').lower().strip()
                if full_name == player_name_lower:
                    nba_id = player.get('id')
                    if nba_id:
                        self._player_id_cache[player_name] = nba_id
                        logger.info(f"Found NBA player ID {nba_id} for {player_name}")
                        return nba_id
            
            # Try partial match (first name or last name)
            name_parts = player_name_lower.split()
            for player in all_players:
                full_name = player.get('full_name', '').lower().strip()
                full_name_parts = full_name.split()
                
                # Check if all parts of the search name are in the full name
                if len(name_parts) > 0 and all(part in full_name for part in name_parts):
                    nba_id = player.get('id')
                    if nba_id:
                        self._player_id_cache[player_name] = nba_id
                        logger.info(f"Found NBA player ID {nba_id} for {player_name} (fuzzy match: {player.get('full_name')})")
                        return nba_id
            
            logger.warning(f"Could not find NBA player ID for {player_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding NBA player ID for {player_name}: {e}")
            return None
    
    def get_player_last_n_games(self, player_id: int, n: int = 10, 
                                season: Optional[str] = None,
                                season_type: str = "Regular Season") -> List[Dict[str, Any]]:
        """
        Get last N games for a specific player.
        
        Args:
            player_id: NBA player ID
            n: Number of recent games to retrieve (default: 10)
            season: Season in format "YYYY-YY" (e.g., "2023-24"). If None, uses current season.
            season_type: Type of season - "Regular Season" or "Playoffs" (default: "Regular Season")
            
        Returns:
            List of the last N games, ordered by most recent first
        """
        try:
            games = self.get_player_game_log(player_id, season, season_type)
            
            # Games are already ordered by most recent first (GAME_DATE descending)
            # Take the first N games
            last_n_games = games[:n]
            
            logger.info(f"Retrieved last {len(last_n_games)} games for player {player_id}")
            
            return last_n_games
            
        except Exception as e:
            logger.error(f"Error fetching last {n} games for player {player_id}: {e}")
            return []
    
    def get_team_players(self, team_abbr: str, season: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all players for a specific team from NBA API.
        
        Args:
            team_abbr: Team abbreviation (e.g., "LAL", "BOS")
            season: Season in format "YYYY-YY" (e.g., "2023-24"). If None, uses current season.
            
        Returns:
            List of player dictionaries with:
            - id: NBA player ID
            - full_name: Player full name
            - team_id: NBA team ID
            - team_abbreviation: Team abbreviation
        """
        try:
            # Get team name from abbreviation
            team_name = get_team_name(team_abbr)
            
            # Find team ID from NBA API
            nba_teams = self.teams.get_teams()
            team_id = None
            
            for team in nba_teams:
                # Match by full name or abbreviation
                if (team.get('full_name', '').lower() == team_name.lower() or 
                    team.get('abbreviation', '').upper() == team_abbr.upper()):
                    team_id = team.get('id')
                    break
            
            if not team_id:
                logger.warning(f"Could not find NBA team ID for {team_abbr} ({team_name})")
                return []
            
            # If season is not provided, use current season
            if not season:
                current_year = datetime.now().year
                if datetime.now().month < 10:
                    season = f"{current_year - 1}-{str(current_year)[2:]}"
                else:
                    season = f"{current_year}-{str(current_year + 1)[2:]}"
            
            logger.info(f"Fetching roster for team {team_abbr} (ID: {team_id}), season {season}")
            
            # Get team roster with retry logic and timeout handling
            import time
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    roster = self.commonteamroster.CommonTeamRoster(
                        team_id=team_id,
                        season=season
                    )
                    
                    # Get data frames with timeout
                    data_frames = roster.get_data_frames()
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    # Check if it's a timeout error
                    error_msg = str(e).lower()
                    is_timeout = 'timeout' in error_msg or 'timed out' in error_msg
                    
                    if attempt < max_retries - 1:  # Not the last attempt
                        if is_timeout:
                            logger.warning(f"Timeout fetching roster for {team_abbr} (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
                        else:
                            logger.warning(f"Error fetching roster for {team_abbr} (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        # Last attempt failed
                        if is_timeout:
                            logger.error(f"Timeout fetching roster for {team_abbr} (ID: {team_id}), season {season} after {max_retries} attempts. The NBA API may be slow or rate-limited.")
                        else:
                            logger.error(f"Error fetching roster for {team_abbr} (ID: {team_id}), season {season} after {max_retries} attempts: {e}")
                        return []
            
            if not data_frames or len(data_frames) == 0:
                logger.warning(f"No roster found for team {team_abbr} in season {season}")
                return []
            
            # First data frame contains the roster
            df = data_frames[0]
            
            if df.empty:
                logger.warning(f"Empty roster for team {team_abbr} in season {season}")
                return []
            
            # Convert to list of dictionaries
            players_list = df.to_dict('records')
            
            # Format the response
            formatted_players = []
            for player in players_list:
                formatted_players.append({
                    'id': player.get('PLAYER_ID'),
                    'full_name': player.get('PLAYER', ''),
                    'team_id': team_id,
                    'team_abbreviation': team_abbr,
                    'position': player.get('POSITION', ''),
                    'jersey_number': player.get('NUM', '')
                })
            
            logger.info(f"Retrieved {len(formatted_players)} players for team {team_abbr}")
            
            return formatted_players
            
        except Exception as e:
            logger.error(f"Error fetching team players for {team_abbr}: {e}")
            return []

