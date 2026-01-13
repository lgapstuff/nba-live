"""
The Odds API port interface (contract).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


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
        
        Args:
            event_id: Event identifier from The Odds API
            regions: Regions to get odds from (default: "us")
            markets: Market type (default: "player_points")
            odds_format: Odds format - "american", "decimal", or "fractional" (default: "american")
            
        Returns:
            Dictionary with odds information including bookmakers and player points markets
        """
        pass




