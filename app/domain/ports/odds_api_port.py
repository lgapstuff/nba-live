"""
The Odds API port interface (contract).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class OddsAPIPort(ABC):
    """
    Port interface for The Odds API integration.
    """
    
    @abstractmethod
    def get_events_for_sport(self, sport: str = "basketball_nba") -> List[Dict[str, Any]]:
        """
        Get events for a specific sport.
        
        Args:
            sport: Sport key (default: "basketball_nba")
            
        Returns:
            List of event dictionaries
        """
        pass
    
    @abstractmethod
    def get_player_points_odds(self, event_id: str, regions: str = "us", 
                             markets: str = "player_points", 
                             odds_format: str = "american") -> Dict[str, Any]:
        """
        Get player points odds for a specific event.
        Note: This method name is kept for backward compatibility.
        The implementation may fetch multiple markets (points, assists, rebounds).
        
        Args:
            event_id: Event identifier from The Odds API
            regions: Regions to get odds from (default: "us")
            markets: Market types (default: "player_points", can include "player_assists", "player_rebounds")
            odds_format: Odds format - "american", "decimal", or "fractional" (default: "american")
            
        Returns:
            Dictionary with odds information including bookmakers and player prop markets
        """
        pass
    
    @abstractmethod
    def get_scores(self, sport: str = "basketball_nba", days_from: int = 1, 
                  event_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get scores for games.
        
        Args:
            sport: Sport key (default: "basketball_nba")
            days_from: Number of days in the past from which to return completed games (1-3)
            event_ids: Comma-separated game ids to filter results (optional)
            
        Returns:
            List of score dictionaries
        """
        pass




