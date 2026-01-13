"""
FantasyNerds port interface (contract).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class FantasyNerdsPort(ABC):
    """
    Port interface for FantasyNerds API integration.
    
    This defines the contract that infrastructure implementations must follow.
    """
    
    @abstractmethod
    def get_games_for_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Get games for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of game dictionaries
        """
        pass
    
    @abstractmethod
    def get_lineups_for_game(self, game_id: str) -> Dict[str, Any]:
        """
        Get lineups for a specific game.
        
        Args:
            game_id: Game identifier
            
        Returns:
            Dictionary with lineup information
        """
        pass
    
    @abstractmethod
    def get_lineups_by_date(self, date: str) -> Dict[str, Any]:
        """
        Get lineups for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format (or YYYYMMDD)
            
        Returns:
            Dictionary with lineup information for all teams on that date
        """
        pass
    
    @abstractmethod
    def get_depth_charts(self) -> Dict[str, Any]:
        """
        Get depth charts for all NBA teams.
        
        Returns:
            Dictionary with depth charts for all teams
            Format: {"season": 2021, "charts": {"SA": {...}, "DEN": {...}, ...}}
        """
        pass

