"""
NBA API client - Now consumes the NBA API microservice.
"""
import logging
import requests
import unicodedata
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.domain.ports.nba_api_port import NBAPort

logger = logging.getLogger(__name__)


class NBAClient(NBAPort):
    """
    Client for NBA API microservice.
    This client now calls the internal NBA API microservice instead of using nba_api library directly.
    """
    
    def __init__(self, service_url: str = "http://nba-api-service:8002"):
        """
        Initialize the client.
        
        Args:
            service_url: Base URL for the NBA API microservice
        """
        self.service_url = service_url.rstrip('/')
        self._player_id_cache = {}  # Cache for player name -> NBA player_id mapping
    
    def get_player_game_log(self, player_id: int, season: Optional[str] = None, 
                           season_type: str = "Regular Season") -> List[Dict[str, Any]]:
        """
        Get game log for a specific player from NBA API microservice.
        
        Args:
            player_id: NBA player ID
            season: Season in format "YYYY-YY" (e.g., "2023-24"). If None, uses current season.
            season_type: Type of season - "Regular Season" or "Playoffs" (default: "Regular Season")
            
        Returns:
            List of game dictionaries with player statistics
        """
        try:
            url = f"{self.service_url}/api/v1/players/{player_id}/game-log"
            params = {}
            if season:
                params['season'] = season
            if season_type:
                params['season_type'] = season_type
            
            logger.info(f"[NBA API SERVICE] REQUEST: Fetching game log for player {player_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[NBA API SERVICE] RESPONSE: Successfully fetched game log")
                return result.get('games', [])
            else:
                logger.warning(f"[NBA API SERVICE] RESPONSE ERROR: {result.get('error')}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[NBA API SERVICE] REQUEST ERROR: Error fetching game log: {e}")
            return []
        except Exception as e:
            logger.error(f"[NBA API SERVICE] ERROR: Unexpected error: {e}")
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
        Find NBA official player ID by player name from NBA API microservice.
        
        Args:
            player_name: Player name (e.g., "Keyonte George" or "Nikola Vučević")
            
        Returns:
            NBA player ID or None if not found
        """
        try:
            # Check cache first
            if player_name in self._player_id_cache:
                return self._player_id_cache[player_name]
            
            url = f"{self.service_url}/api/v1/players/find-by-name"
            params = {'name': player_name}
            
            logger.info(f"[NBA API SERVICE] REQUEST: Finding player ID for {player_name}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                player_id = result.get('player_id')
                if player_id:
                    self._player_id_cache[player_name] = player_id
                    logger.info(f"[NBA API SERVICE] Found player ID {player_id} for {player_name}")
                return player_id
            else:
                logger.warning(f"[NBA API SERVICE] Could not find player ID for {player_name}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[NBA API SERVICE] REQUEST ERROR: Error finding player ID: {e}")
            return None
        except Exception as e:
            logger.error(f"[NBA API SERVICE] ERROR: Unexpected error: {e}")
            return None
    
    def get_player_last_n_games(self, player_id: int, n: int = 10, 
                                season: Optional[str] = None,
                                season_type: str = "Regular Season") -> List[Dict[str, Any]]:
        """
        Get last N games for a specific player from NBA API microservice.
        
        Args:
            player_id: NBA player ID
            n: Number of recent games to retrieve (default: 10)
            season: Season in format "YYYY-YY" (e.g., "2023-24"). If None, uses current season.
            season_type: Type of season - "Regular Season" or "Playoffs" (default: "Regular Season")
            
        Returns:
            List of the last N games, ordered by most recent first
        """
        try:
            url = f"{self.service_url}/api/v1/players/{player_id}/last-games"
            params = {'n': n}
            if season:
                params['season'] = season
            if season_type:
                params['season_type'] = season_type
            
            logger.info(f"[NBA API SERVICE] REQUEST: Fetching last {n} games for player {player_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[NBA API SERVICE] RESPONSE: Successfully fetched last games")
                return result.get('games', [])
            else:
                logger.warning(f"[NBA API SERVICE] RESPONSE ERROR: {result.get('error')}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[NBA API SERVICE] REQUEST ERROR: Error fetching last games: {e}")
            return []
        except Exception as e:
            logger.error(f"[NBA API SERVICE] ERROR: Unexpected error: {e}")
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
            url = f"{self.service_url}/api/v1/teams/{team_abbr}/players"
            params = {}
            if season:
                params['season'] = season
            
            logger.info(f"[NBA API SERVICE] REQUEST: Fetching players for team {team_abbr}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[NBA API SERVICE] RESPONSE: Successfully fetched team players")
                return result.get('players', [])
            else:
                logger.warning(f"[NBA API SERVICE] RESPONSE ERROR: {result.get('error')}")
                return []
            
        except Exception as e:
            logger.error(f"[NBA API] REQUEST ERROR: Error fetching team players for {team_abbr}: {e}")
            return []
    
    def get_live_boxscore(self, game_id: str, player_ids: Optional[List[int]] = None) -> Any:
        """
        Get live boxscore statistics for specific players in a game.
        
        Args:
            game_id: NBA GameID (format: "0022400123" where 00224 is season, 00123 is game number)
            player_ids: Optional list of NBA player IDs to get statistics for
            
        Returns:
            Dictionary with live statistics for each player
        """
        try:
            url = f"{self.service_url}/api/v1/games/{game_id}/boxscore"
            params = None
            if player_ids:
                params = {'player_ids': ','.join(map(str, player_ids))}
            
            logger.info(f"[NBA API SERVICE] REQUEST: Fetching live boxscore for game {game_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[NBA API SERVICE] RESPONSE: Successfully fetched boxscore")
                return result.get('boxscore', {})
            else:
                logger.warning(f"[NBA API SERVICE] RESPONSE ERROR: {result.get('error')}")
                return {}
            
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
            from datetime import timedelta, date
            
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
            
            url = f"{self.service_url}/api/v1/games/find-game-id"
            params = {
                'home_team': home_team_abbr,
                'away_team': away_team_abbr
            }
            if game_date:
                params['game_date'] = game_date
            
            logger.info(f"[NBA API SERVICE] REQUEST: Finding GameID for {away_team_abbr} @ {home_team_abbr}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                game_id = result.get('game_id')
                logger.info(f"[NBA API SERVICE] Found GameID: {game_id}")
                return game_id
            else:
                logger.warning(f"[NBA API SERVICE] GameID not found: {result.get('error')}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[NBA API SERVICE] REQUEST ERROR: Error finding GameID: {e}")
            return None
        except Exception as e:
            logger.error(f"[NBA API SERVICE] ERROR: Unexpected error: {e}")
            return None

