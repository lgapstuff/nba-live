"""
The Odds API HTTP client.
"""
import requests
import logging
from typing import List, Dict, Any

from app.domain.ports.odds_api_port import OddsAPIPort

logger = logging.getLogger(__name__)


class OddsAPIClient(OddsAPIPort):
    """
    HTTP client for The Odds API.
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.the-odds-api.com"):
        """
        Initialize the client.
        
        Args:
            api_key: The Odds API key
            base_url: Base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url
    
    def get_events_for_sport(self, sport: str = "basketball_nba") -> List[Dict[str, Any]]:
        """
        Get events for a specific sport.
        
        Args:
            sport: Sport key (default: "basketball_nba")
            
        Returns:
            List of event dictionaries
        """
        try:
            url = f"{self.base_url}/v4/sports/{sport}/events"
            params = {
                'apiKey': self.api_key
            }
            
            logger.info(f"Fetching events from The Odds API: {url}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            events = response.json()
            logger.info(f"Received {len(events)} events from The Odds API")
            
            return events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching events from The Odds API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching events: {e}")
            return []
    
    def get_player_points_odds(self, event_id: str, regions: str = "us", 
                              markets: str = "player_points", 
                              odds_format: str = "american") -> Dict[str, Any]:
        """
        Get player points odds for a specific event.
        
        Args:
            event_id: Event identifier from The Odds API
            regions: Regions to get odds from (default: "us")
            markets: Market type (default: "player_points")
            odds_format: Odds format (default: "american")
            
        Returns:
            Dictionary with odds information
        """
        try:
            url = f"{self.base_url}/v4/sports/basketball_nba/events/{event_id}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': regions,
                'markets': markets,
                'oddsFormat': odds_format
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching odds from The Odds API: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error fetching odds: {e}")
            return {}

