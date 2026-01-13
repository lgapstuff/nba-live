"""
The Odds API HTTP client.
"""
import json
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
            # Use the event-specific endpoint which supports player_points market
            # The general /odds endpoint doesn't support player_points
            url = f"{self.base_url}/v4/sports/basketball_nba/events/{event_id}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': regions,
                'markets': markets,
                'oddsFormat': odds_format
            }
            
            logger.info(f"Fetching player props odds from The Odds API for event {event_id}: {url}")
            logger.debug(f"Request params: {params}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Get event data with odds
            event_data = response.json()
            
            if not event_data:
                logger.warning(f"Empty response for event {event_id}")
                return {}
            
            logger.info(f"Received odds data for event {event_id}: {event_data.get('away_team')} @ {event_data.get('home_team')}")
            
            # Log the complete raw response from The Odds API
            logger.info(f"[ODDS API] Raw response for event {event_id}:")
            logger.info(f"[ODDS API] {json.dumps(event_data, indent=2, default=str)}")
            
            # Check what bookmakers are available
            all_bookmakers = event_data.get('bookmakers', [])
            if not all_bookmakers:
                logger.warning(f"No bookmakers found for event {event_id}")
                return {}
            
            bookmaker_keys = [b.get('key', '') for b in all_bookmakers]
            logger.info(f"Available bookmakers for event {event_id}: {bookmaker_keys}")
            
            # Filter to only FanDuel bookmaker
            filtered_bookmakers = []
            for bookmaker in all_bookmakers:
                bookmaker_key = bookmaker.get('key', '').lower()
                logger.debug(f"Checking bookmaker: {bookmaker_key}")
                if bookmaker_key == 'fanduel':
                    # Get all player prop markets (points, assists, rebounds)
                    markets_list = bookmaker.get('markets', [])
                    market_keys = [m.get('key', '') for m in markets_list]
                    logger.info(f"FanDuel markets available: {market_keys}")
                    
                    # Filter to player prop markets
                    player_prop_markets = [m for m in markets_list if m.get('key') in ['player_points', 'player_assists', 'player_rebounds']]
                    if player_prop_markets:
                        # Create a bookmaker dict with player prop markets
                        fanduel_with_props = {
                            **bookmaker,
                            'markets': player_prop_markets
                        }
                        filtered_bookmakers.append(fanduel_with_props)
                        logger.info(f"Found FanDuel player props for event {event_id}: {[m.get('key') for m in player_prop_markets]}")
                    else:
                        logger.warning(f"FanDuel found but no player prop markets available. Available markets: {market_keys}")
                    break  # Only need one FanDuel entry
            
            if not filtered_bookmakers:
                logger.warning(f"No FanDuel player props found for event {event_id}. Available bookmakers: {bookmaker_keys}")
                return {}
            
            # Return event data with only FanDuel bookmaker
            result = {
                'id': event_data.get('id'),
                'sport_key': event_data.get('sport_key'),
                'sport_title': event_data.get('sport_title'),
                'commence_time': event_data.get('commence_time'),
                'home_team': event_data.get('home_team'),
                'away_team': event_data.get('away_team'),
                'bookmakers': filtered_bookmakers
            }
            
            logger.info(f"Successfully retrieved FanDuel player props for event {event_id}")
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching odds from The Odds API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                try:
                    error_body = e.response.json()
                    logger.error(f"Response body: {error_body}")
                except:
                    logger.error(f"Response body (text): {e.response.text[:500]}")
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching odds from The Odds API: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error fetching odds: {e}", exc_info=True)
            return {}

