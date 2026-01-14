"""
NBA API client using nba_api library.
"""
import logging
import unicodedata
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
            
            logger.info(f"[NBA API] REQUEST: Fetching game log for player {player_id}, season {season}, type {season_type}")
            
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
            logger.debug(f"[NBA API] Getting data frames from PlayerGameLog...")
            data_frames = game_log.get_data_frames()
            logger.info(f"[NBA API] RESPONSE: Received {len(data_frames) if data_frames else 0} data frames")
            
            if not data_frames or len(data_frames) == 0:
                logger.warning(f"[NBA API] RESPONSE: No games found for player {player_id} in season {season}")
                return []
            
            # Get first data frame (game log)
            df = data_frames[0]
            
            # Check if dataframe is empty
            if df.empty:
                logger.warning(f"[NBA API] RESPONSE: Empty data frame for player {player_id} in season {season}")
                return []
            
            # Convert to list of dictionaries
            games = df.to_dict('records')
            
            logger.info(f"[NBA API] RESPONSE: Successfully retrieved {len(games)} games for player {player_id}")
            
            return games
            
        except ValueError as e:
            # Handle JSON parsing errors (empty response, invalid JSON)
            error_msg = str(e)
            if "Expecting value" in error_msg or "line 1 column 1" in error_msg:
                logger.warning(f"[NBA API] RESPONSE ERROR: No games found for player {player_id} (empty response)")
            else:
                logger.warning(f"[NBA API] REQUEST ERROR: Error fetching game log for player {player_id}: {e}")
            return []
        except Exception as e:
            error_msg = str(e)
            # Check for pandas import error
            if "pandas" in error_msg.lower() or "DataFrame" in error_msg:
                logger.error(f"[NBA API] ERROR: Pandas not available for player {player_id}: {e}")
                logger.error("[NBA API] ERROR: Please install pandas: pip install pandas")
            else:
                logger.warning(f"[NBA API] REQUEST ERROR: Error fetching game log for player {player_id}: {e}")
            return []
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize player name by removing accents and converting to lowercase.
        
        Args:
            name: Player name (e.g., "Nikola Vučević")
            
        Returns:
            Normalized name (e.g., "nikola vucevic")
        """
        if not name:
            return ""
        # Remove accents and diacritics
        normalized = unicodedata.normalize('NFD', name)
        # Remove combining characters (accents)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        # Convert to lowercase and strip
        return normalized.lower().strip()
    
    def find_nba_player_id_by_name(self, player_name: str) -> Optional[int]:
        """
        Find NBA official player ID by player name.
        Uses fuzzy matching to find the closest match.
        Handles accents and special characters in names.
        
        Args:
            player_name: Player name (e.g., "Keyonte George" or "Nikola Vučević")
            
        Returns:
            NBA player ID or None if not found
        """
        try:
            # Check cache first
            if player_name in self._player_id_cache:
                return self._player_id_cache[player_name]
            
            # Get all players from NBA API
            all_players = self.players.get_players()
            
            # Normalize search name (remove accents, lowercase)
            player_name_normalized = self._normalize_name(player_name)
            
            # Try exact match first (normalized)
            for player in all_players:
                full_name = player.get('full_name', '')
                full_name_normalized = self._normalize_name(full_name)
                if full_name_normalized == player_name_normalized:
                    nba_id = player.get('id')
                    if nba_id:
                        self._player_id_cache[player_name] = nba_id
                        logger.info(f"Found NBA player ID {nba_id} for {player_name} (matched: {full_name})")
                        return nba_id
            
            # Try partial match (first name or last name) with normalized names
            name_parts = player_name_normalized.split()
            for player in all_players:
                full_name = player.get('full_name', '')
                full_name_normalized = self._normalize_name(full_name)
                full_name_parts = full_name_normalized.split()
                
                # Check if all parts of the search name are in the full name
                if len(name_parts) > 0 and all(part in full_name_normalized for part in name_parts):
                    nba_id = player.get('id')
                    if nba_id:
                        self._player_id_cache[player_name] = nba_id
                        logger.info(f"Found NBA player ID {nba_id} for {player_name} (fuzzy match: {full_name})")
                        return nba_id
            
            logger.warning(f"[NBA API] REQUEST: Could not find NBA player ID for {player_name}")
            return None
            
        except Exception as e:
            logger.error(f"[NBA API] REQUEST ERROR: Error finding NBA player ID for {player_name}: {e}")
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
            
            logger.info(f"[NBA API] RESPONSE: Retrieved last {len(last_n_games)} games for player {player_id}")
            
            return last_n_games
            
        except Exception as e:
            logger.error(f"[NBA API] REQUEST ERROR: Error fetching last {n} games for player {player_id}: {e}")
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
            logger.debug(f"[NBA API] Looking up team ID for {team_abbr} (team_name: {team_name})")
            nba_teams = self.teams.get_teams()
            team_id = None
            matched_team = None
            
            for team in nba_teams:
                # Match by full name or abbreviation
                if (team.get('full_name', '').lower() == team_name.lower() or 
                    team.get('abbreviation', '').upper() == team_abbr.upper()):
                    team_id = team.get('id')
                    matched_team = team
                    break
            
            if not team_id:
                logger.warning(f"[NBA API] Could not find NBA team ID for {team_abbr} ({team_name})")
                logger.debug(f"[NBA API] Available teams (first 5): {[{'abbr': t.get('abbreviation'), 'name': t.get('full_name'), 'id': t.get('id')} for t in nba_teams[:5]]}")
                return []
            
            logger.info(f"[NBA API] Found team: {matched_team.get('full_name')} (ID: {team_id}, Abbr: {matched_team.get('abbreviation')})")
            
            # If season is not provided, use current season
            if not season:
                current_year = datetime.now().year
                if datetime.now().month < 10:
                    season = f"{current_year - 1}-{str(current_year)[2:]}"
                else:
                    season = f"{current_year}-{str(current_year + 1)[2:]}"
            
            logger.info(f"[NBA API] REQUEST: Fetching roster for team {team_abbr} (ID: {team_id}), season {season}")
            logger.debug(f"[NBA API] REQUEST PARAMS: team_id={team_id}, season={season}")
            
            # Get team roster with retry logic and timeout handling
            import time
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    logger.debug(f"[NBA API] Attempt {attempt + 1}/{max_retries}: Calling CommonTeamRoster(team_id={team_id}, season={season})")
                    roster = self.commonteamroster.CommonTeamRoster(
                        team_id=team_id,
                        season=season
                    )
                    
                    # Try to get the URL that was called (if available in the SDK)
                    try:
                        # The nba_api library stores the URL in the response object
                        if hasattr(roster, 'url'):
                            logger.debug(f"[NBA API] REQUEST URL: {roster.url}")
                        elif hasattr(roster, 'response'):
                            logger.debug(f"[NBA API] Response object available, status: {getattr(roster.response, 'status_code', 'N/A')}")
                    except Exception as url_error:
                        logger.debug(f"[NBA API] Could not extract URL from response: {url_error}")
                    
                    # Get data frames with timeout
                    logger.debug(f"[NBA API] Getting data frames from response...")
                    data_frames = roster.get_data_frames()
                    logger.debug(f"[NBA API] RESPONSE: Received {len(data_frames) if data_frames else 0} data frames")
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
                logger.warning(f"[NBA API] RESPONSE: No data frames returned for team {team_abbr} in season {season}")
                logger.debug(f"[NBA API] RESPONSE: data_frames = {data_frames}")
                return []
            
            # First data frame contains the roster
            df = data_frames[0]
            logger.debug(f"[NBA API] RESPONSE: Data frame shape: {df.shape if hasattr(df, 'shape') else 'N/A'}")
            logger.debug(f"[NBA API] RESPONSE: Data frame columns: {list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
            
            if df.empty:
                logger.warning(f"[NBA API] RESPONSE: Empty data frame for team {team_abbr} in season {season}")
                logger.debug(f"[NBA API] RESPONSE: DataFrame info: {df.info() if hasattr(df, 'info') else 'N/A'}")
                return []
            
            # Convert to list of dictionaries
            players_list = df.to_dict('records')
            logger.debug(f"[NBA API] RESPONSE: Converted to {len(players_list)} player records")
            if players_list:
                logger.debug(f"[NBA API] RESPONSE: Sample player record (first): {players_list[0]}")
            
            # Format the response
            formatted_players = []
            for player in players_list:
                player_id = player.get('PLAYER_ID')
                player_name = player.get('PLAYER', '')
                if not player_id or not player_name:
                    logger.warning(f"[NBA API] Skipping invalid player record: {player}")
                    continue
                    
                formatted_players.append({
                    'id': player_id,
                    'full_name': player_name,
                    'team_id': team_id,
                    'team_abbreviation': team_abbr,
                    'position': player.get('POSITION', ''),
                    'jersey_number': player.get('NUM', '')
                })
            
            logger.info(f"[NBA API] RESPONSE: Successfully retrieved {len(formatted_players)} players for team {team_abbr}")
            if formatted_players:
                logger.debug(f"[NBA API] RESPONSE: Sample formatted player: {formatted_players[0]}")
            
            return formatted_players
            
        except Exception as e:
            logger.error(f"[NBA API] REQUEST ERROR: Error fetching team players for {team_abbr}: {e}")
            return []
    
    def get_live_boxscore(self, game_id: str, player_ids: List[int]) -> Dict[str, Any]:
        """
        Get live boxscore statistics for specific players in a game.
        
        Args:
            game_id: NBA GameID (format: "0022400123" where 00224 is season, 00123 is game number)
            player_ids: List of NBA player IDs to get statistics for
            
        Returns:
            Dictionary with live statistics for each player
        """
        try:
            from nba_api.stats.endpoints import boxscoretraditionalv2
            from nba_api.stats.library.parameters import GameID
            
            logger.info(f"[NBA API] REQUEST: Fetching live boxscore for game {game_id}, players: {player_ids}")
            
            # Get boxscore
            boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
            data_frames = boxscore.get_data_frames()
            
            if not data_frames or len(data_frames) == 0:
                logger.warning(f"[NBA API] RESPONSE: No boxscore data for game {game_id}")
                return {}
            
            # First data frame contains player stats
            df = data_frames[0]
            
            if df.empty:
                logger.warning(f"[NBA API] RESPONSE: Empty boxscore for game {game_id}")
                return {}
            
            # Convert to list of dictionaries
            player_stats = df.to_dict('records')
            
            # Filter to only requested players and format response
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
                        'PLAYER_NAME': stat.get('PLAYER_NAME', '')
                    }
            
            logger.info(f"[NBA API] RESPONSE: Retrieved live stats for {len(result)} players")
            return result
            
        except Exception as e:
            logger.error(f"[NBA API] REQUEST ERROR: Error fetching live boxscore for game {game_id}: {e}")
            return {}
    
    def find_nba_game_id(self, home_team_abbr: str, away_team_abbr: str, game_date: str = None) -> Optional[str]:
        """
        Find NBA GameID by matching teams and date using Scoreboard.
        
        Args:
            home_team_abbr: Home team abbreviation (e.g., "LAL")
            away_team_abbr: Away team abbreviation (e.g., "BOS")
            game_date: Game date in format "YYYY-MM-DD" (optional, defaults to today)
            
        Returns:
            NBA GameID (format: "0022400123") or None if not found
        """
        try:
            from nba_api.stats.endpoints import scoreboardv2
            from datetime import datetime, timedelta, date
            
            # If no date provided, use today
            if not game_date:
                game_date = datetime.now().strftime("%Y-%m-%d")
            
            # Convert game_date to string if it's a date/datetime object
            if isinstance(game_date, (date, datetime)):
                game_date = game_date.strftime("%Y-%m-%d")
            elif not isinstance(game_date, str):
                game_date = str(game_date)
            
            logger.info(f"[NBA API] REQUEST: Finding GameID for {away_team_abbr} @ {home_team_abbr} on {game_date}")
            
            # ScoreboardV2 expects format "YYYY-MM-DD"
            # Ensure game_date is in correct format
            try:
                # Parse the date to ensure it's in YYYY-MM-DD format
                if isinstance(game_date, str):
                    game_date_obj = datetime.strptime(game_date, "%Y-%m-%d")
                else:
                    game_date_obj = datetime.strptime(str(game_date), "%Y-%m-%d")
            except ValueError:
                # If parsing fails, try to extract date from string
                logger.warning(f"[NBA API] Could not parse game_date '{game_date}', using as-is")
                game_date_obj = None
            
            # Try current date and also check yesterday and tomorrow (games might span dates)
            dates_to_try = []
            
            if game_date_obj:
                # Format dates as YYYY-MM-DD for ScoreboardV2
                dates_to_try.append(game_date_obj.strftime("%Y-%m-%d"))
                yesterday = (game_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
                tomorrow = (game_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                dates_to_try.extend([yesterday, tomorrow])
            else:
                # Fallback: use game_date as-is if it's already a string
                dates_to_try.append(str(game_date))
            
            logger.debug(f"[NBA API] Will try dates: {dates_to_try}")
            
            for try_date in dates_to_try:
                try:
                    logger.debug(f"[NBA API] Trying scoreboard date: {try_date}")
                    # ScoreboardV2 expects game_date in format "YYYY-MM-DD"
                    scoreboard_data = scoreboardv2.ScoreboardV2(game_date=try_date)
                    
                    # Try get_dict() first (more reliable)
                    try:
                        scoreboard_dict = scoreboard_data.get_dict()
                        if scoreboard_dict and 'resultSets' in scoreboard_dict:
                            # resultSets[0] is GameHeader
                            result_sets = scoreboard_dict.get('resultSets', [])
                            if result_sets and len(result_sets) > 0:
                                game_header = result_sets[0]
                                if 'rowSet' in game_header:
                                    games = []
                                    headers = game_header.get('headers', [])
                                    rows = game_header.get('rowSet', [])
                                    
                                    # Convert rows to dictionaries
                                    for row in rows:
                                        game_dict = {}
                                        for i, header in enumerate(headers):
                                            if i < len(row):
                                                game_dict[header] = row[i]
                                        games.append(game_dict)
                                    
                                    if games:
                                        logger.debug(f"[NBA API] Found {len(games)} games in scoreboard (via get_dict) for {try_date}")
                                        
                                        # Search for matching game
                                        for game in games:
                                            home_team = game.get('HOME_TEAM_ABBREVIATION', '')
                                            away_team = game.get('VISITOR_TEAM_ABBREVIATION', '')
                                            game_id = game.get('GAME_ID', '')
                                            
                                            logger.debug(f"[NBA API] Checking game: {away_team} @ {home_team} (GameID: {game_id})")
                                            
                                            if (home_team.upper() == home_team_abbr.upper() and 
                                                away_team.upper() == away_team_abbr.upper()):
                                                logger.info(f"[NBA API] Found GameID: {game_id} for {away_team_abbr} @ {home_team_abbr} on {try_date}")
                                                return game_id
                    except Exception as dict_error:
                        logger.debug(f"[NBA API] get_dict() failed for {try_date}: {dict_error}, trying get_data_frames()")
                    
                    # Fallback to get_data_frames()
                    data_frames = scoreboard_data.get_data_frames()
                    
                    if not data_frames or len(data_frames) == 0:
                        logger.debug(f"[NBA API] No data frames returned for scoreboard date {try_date}")
                        continue
                    
                    # ScoreboardV2 returns multiple data frames:
                    # [0] = GameHeader (contains game info)
                    # [1] = LineScore
                    # [2] = SeriesStandings
                    # etc.
                    # We need the GameHeader which is the first data frame
                    if len(data_frames) < 1:
                        logger.debug(f"[NBA API] Not enough data frames in scoreboard for {try_date}")
                        continue
                    
                    # First data frame contains game header info
                    df = data_frames[0]
                    
                    if df is None or (hasattr(df, 'empty') and df.empty):
                        logger.debug(f"[NBA API] Empty game header data frame for {try_date}")
                        continue
                    
                    # Convert to list of dictionaries
                    games = df.to_dict('records')
                    
                    if not games:
                        logger.debug(f"[NBA API] No games in scoreboard for {try_date}")
                        continue
                    
                    logger.debug(f"[NBA API] Found {len(games)} games in scoreboard (via get_data_frames) for {try_date}")
                    
                    # Search for matching game
                    for game in games:
                        home_team = game.get('HOME_TEAM_ABBREVIATION', '')
                        away_team = game.get('VISITOR_TEAM_ABBREVIATION', '')
                        game_id = game.get('GAME_ID', '')
                        
                        logger.debug(f"[NBA API] Checking game: {away_team} @ {home_team} (GameID: {game_id})")
                        
                        if (home_team.upper() == home_team_abbr.upper() and 
                            away_team.upper() == away_team_abbr.upper()):
                            logger.info(f"[NBA API] Found GameID: {game_id} for {away_team_abbr} @ {home_team_abbr} on {try_date}")
                            return game_id
                    
                except IndexError as e:
                    logger.warning(f"[NBA API] IndexError fetching scoreboard for {try_date}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"[NBA API] Error fetching scoreboard for {try_date}: {e}", exc_info=True)
                    continue
            
            logger.warning(f"[NBA API] GameID not found for {away_team_abbr} @ {home_team_abbr} on {game_date} (tried dates: {dates_to_try})")
            return None
            
        except Exception as e:
            logger.error(f"[NBA API] REQUEST ERROR: Error finding GameID: {e}", exc_info=True)
            return None

