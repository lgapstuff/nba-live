"""
NBA API port interface (contract).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class NBAPort(ABC):
    """
    Port interface for NBA API integration (nba_api library).
    """
    
    @abstractmethod
    def get_player_game_log(self, player_id: int, season: Optional[str] = None, 
                           season_type: str = "Regular Season") -> List[Dict[str, Any]]:
        """
        Get game log for a specific player.
        
        Args:
            player_id: NBA player ID
            season: Season in format "YYYY-YY" (e.g., "2023-24"). If None, uses current season.
            season_type: Type of season - "Regular Season" or "Playoffs" (default: "Regular Season")
            
        Returns:
            List of game dictionaries with player statistics for each game
            Each game should include at least: points (PTS), game_date, etc.
        """
        pass
    
    @abstractmethod
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
            List of the last N games with player statistics, ordered by most recent first
        """
        pass
    
    @abstractmethod
    def find_nba_player_id_by_name(self, player_name: str) -> Optional[int]:
        """
        Find NBA official player ID by player name.
        
        Args:
            player_name: Player name (e.g., "Keyonte George")
            
        Returns:
            NBA player ID or None if not found
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_live_boxscore(self, game_id: str, player_ids: Optional[List[int]] = None) -> Any:
        """
        Get live boxscore statistics for specific players in a game.
        
        Args:
            game_id: NBA GameID (format: "0022400123" where 00224 is season, 00123 is game number)
            player_ids: Optional list of NBA player IDs to filter stats
            
        Returns:
            If player_ids provided, dictionary with stats per player_id.
            If omitted, list of player stat dictionaries for the full boxscore.
        """
        pass

