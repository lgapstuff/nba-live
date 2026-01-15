"""
The Odds API HTTP client.
"""
import json
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class OddsAPIClient:
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

    @staticmethod
    def _log_request(method: str, url: str, params: Optional[Dict[str, Any]] = None) -> None:
        try:
            req = requests.Request(method=method, url=url, params=params or {})
            prepared = req.prepare()
            logger.info(f"[ODDS API] RAW REQUEST: {prepared.method} {prepared.url}")
        except Exception as e:
            logger.warning(f"[ODDS API] Could not format request URL: {e}")
    
    def get_events_for_sport(self, sport: str = "basketball_nba") -> List[Dict[str, Any]]:
        """Get events for a specific sport."""
        try:
            url = f"{self.base_url}/v4/sports/{sport}/events"
            params = {'apiKey': self.api_key}
            
            logger.info(f"[ODDS API] Fetching events for sport: {sport}")
            self._log_request("GET", url, params)
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            events = response.json()
            logger.info(f"[ODDS API] Received {len(events)} events")
            return events
        except requests.exceptions.RequestException as e:
            logger.error(f"[ODDS API] Error fetching events: {e}")
            return []
        except Exception as e:
            logger.error(f"[ODDS API] Unexpected error: {e}")
            return []
    
    def get_player_points_odds(self, event_id: str, regions: str = "us", 
                              markets: str = "player_points,player_assists,player_rebounds", 
                              odds_format: str = "american") -> Dict[str, Any]:
        """Get player props odds for a specific event."""
        try:
            url = f"{self.base_url}/v4/sports/basketball_nba/events/{event_id}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': regions,
                'markets': markets,
                'oddsFormat': odds_format
            }
            
            logger.info(f"[ODDS API] Fetching player props odds for event {event_id}")
            self._log_request("GET", url, params)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            event_data = response.json()
            if not event_data:
                return {}
            
            all_bookmakers = event_data.get('bookmakers', [])
            if not all_bookmakers:
                return {}
            
            # Filter to only FanDuel bookmaker
            filtered_bookmakers = []
            for bookmaker in all_bookmakers:
                bookmaker_key = bookmaker.get('key', '').lower()
                if bookmaker_key == 'fanduel':
                    markets_list = bookmaker.get('markets', [])
                    player_prop_markets = [m for m in markets_list if m.get('key') in ['player_points', 'player_assists', 'player_rebounds']]
                    if player_prop_markets:
                        filtered_bookmakers.append({
                            **bookmaker,
                            'markets': player_prop_markets
                        })
                    break
            
            if not filtered_bookmakers:
                return {}
            
            return {
                'id': event_data.get('id'),
                'sport_key': event_data.get('sport_key'),
                'sport_title': event_data.get('sport_title'),
                'commence_time': event_data.get('commence_time'),
                'home_team': event_data.get('home_team'),
                'away_team': event_data.get('away_team'),
                'bookmakers': filtered_bookmakers
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"[ODDS API] Error fetching odds: {e}")
            return {}
        except Exception as e:
            logger.error(f"[ODDS API] Unexpected error: {e}")
            return {}
    
    def get_scores(self, sport: str = "basketball_nba", days_from: int = 1, 
                  event_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get scores for games."""
        try:
            url = f"{self.base_url}/v4/sports/{sport}/scores"
            params = {
                'apiKey': self.api_key,
                'daysFrom': days_from
            }
            
            if event_ids:
                params['eventIds'] = event_ids
            
            logger.info(f"[ODDS API] Fetching scores for sport: {sport}")
            self._log_request("GET", url, params)
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            scores = response.json()
            logger.info(f"[ODDS API] Received {len(scores)} scores")
            return scores
        except requests.exceptions.RequestException as e:
            logger.error(f"[ODDS API] Error fetching scores: {e}")
            return []
        except Exception as e:
            logger.error(f"[ODDS API] Unexpected error: {e}")
            return []
