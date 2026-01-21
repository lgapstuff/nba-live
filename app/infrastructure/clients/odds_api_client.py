"""
The Odds API HTTP client.
"""
import json
import requests
import logging
from typing import List, Dict, Any, Optional

from app.domain.ports.odds_api_port import OddsAPIPort

logger = logging.getLogger(__name__)


class OddsAPIClient(OddsAPIPort):
    """
    HTTP client for The Odds API microservice.
    This client now calls the internal Odds API microservice instead of the external API directly.
    """
    
    def __init__(
        self,
        service_url: str = "http://odds-api-service:8003",
        api_prefix: str = "/api/v1/odds"
    ):
        """
        Initialize the client.
        
        Args:
            service_url: Base URL for the Odds API microservice
        """
        self.service_url = service_url.rstrip('/')
        api_prefix = api_prefix.strip()
        if not api_prefix.startswith("/"):
            api_prefix = f"/{api_prefix}"
        self.api_prefix = api_prefix.rstrip("/")
        self.base_url = f"{self.service_url}{self.api_prefix}"

    @staticmethod
    def _log_request(method: str, url: str, params: Optional[Dict[str, Any]] = None) -> None:
        try:
            req = requests.Request(method=method, url=url, params=params)
            prepared = req.prepare()
            logger.info(f"[ODDS API SERVICE] RAW REQUEST: {prepared.method} {prepared.url}")
        except Exception as e:
            logger.warning(f"[ODDS API SERVICE] Could not format request URL: {e}")
    
    def get_events_for_sport(self, sport: str = "basketball_nba") -> List[Dict[str, Any]]:
        """
        Get events for a specific sport from Odds API microservice.
        
        Args:
            sport: Sport key (default: "basketball_nba")
            
        Returns:
            List of event dictionaries
        """
        try:
            url = f"{self.base_url}/events"
            params = {'sport': sport}
            
            logger.info(f"[ODDS API SERVICE] REQUEST: Fetching events for sport: {sport}")
            self._log_request("GET", url, params)
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[ODDS API SERVICE] RESPONSE: Successfully fetched events")
                return result.get('events', [])
            else:
                logger.error(f"[ODDS API SERVICE] RESPONSE ERROR: {result.get('error')}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[ODDS API SERVICE] REQUEST ERROR: Error fetching events: {e}")
            return []
        except Exception as e:
            logger.error(f"[ODDS API SERVICE] ERROR: Unexpected error: {e}")
            return []
    
    def get_player_points_odds(self, event_id: str, regions: str = "us", 
                              markets: str = "player_points,player_assists,player_rebounds", 
                              odds_format: str = "american") -> Dict[str, Any]:
        """
        Get player props odds for a specific event (points, assists, rebounds).
        Uses the event-specific endpoint which supports player prop markets.
        Filters to only FanDuel bookmaker.
        
        Note: Method name kept as 'get_player_points_odds' for interface compatibility,
        but it can fetch multiple markets (points, assists, rebounds).
        
        Args:
            event_id: Event identifier from The Odds API
            regions: Regions to get odds from (default: "us")
            markets: Market types (default: "player_points,player_assists,player_rebounds")
            odds_format: Odds format (default: "american")
            
        Returns:
            Dictionary with odds information (only FanDuel bookmaker)
        """
        try:
            url = f"{self.base_url}/events/{event_id}/odds"
            params = {
                'regions': regions,
                'markets': markets,
                'odds_format': odds_format
            }
            
            logger.info(f"[ODDS API SERVICE] REQUEST: Fetching player props odds for event {event_id}")
            self._log_request("GET", url, params)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[ODDS API SERVICE] RESPONSE: Successfully fetched odds")
                return result.get('data', {})
            else:
                logger.error(f"[ODDS API SERVICE] RESPONSE ERROR: {result.get('error')}")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"[ODDS API SERVICE] REQUEST ERROR: Error fetching odds: {e}")
            return {}
        except Exception as e:
            logger.error(f"[ODDS API SERVICE] ERROR: Unexpected error: {e}")
            return {}
    
    def get_scores(self, sport: str = "basketball_nba", days_from: int = 1, 
                  event_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get scores for games from Odds API microservice.
        
        Args:
            sport: Sport key (default: "basketball_nba")
            days_from: Number of days in the past from which to return completed games (1-3)
            event_ids: Comma-separated game ids to filter results (optional)
            
        Returns:
            List of score dictionaries
        """
        try:
            url = f"{self.base_url}/scores"
            params = {
                'sport': sport,
                'days_from': days_from
            }
            
            if event_ids:
                params['event_ids'] = event_ids
            
            logger.info(f"[ODDS API SERVICE] REQUEST: Fetching scores for sport: {sport}")
            self._log_request("GET", url, params)
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[ODDS API SERVICE] RESPONSE: Successfully fetched scores")
                return result.get('scores', [])
            else:
                logger.error(f"[ODDS API SERVICE] RESPONSE ERROR: {result.get('error')}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[ODDS API SERVICE] REQUEST ERROR: Error fetching scores: {e}")
            return []
        except Exception as e:
            logger.error(f"[ODDS API SERVICE] ERROR: Unexpected error: {e}")
            return []

