"""
FantasyNerds HTTP client.
"""
import requests
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

from app.domain.ports.fantasynerds_port import FantasyNerdsPort

logger = logging.getLogger(__name__)


class FantasyNerdsClient(FantasyNerdsPort):
    """
    HTTP client for FantasyNerds API.
    
    This is a stub for future implementation.
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.fantasynerds.com"):
        """
        Initialize the client.
        
        Args:
            api_key: FantasyNerds API key
            base_url: Base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url
    
    def get_games_for_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Get games for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of game dictionaries
        """
        # Stub implementation
        return []
    
    def get_lineups_for_game(self, game_id: str) -> Dict[str, Any]:
        """
        Get lineups for a specific game.
        
        Args:
            game_id: Game identifier
            
        Returns:
            Dictionary with lineup information
        """
        # Stub implementation
        return {}
    
    def get_lineups_by_date(self, date: str) -> Dict[str, Any]:
        """
        Get lineups for a specific date from FantasyNerds API.
        
        Args:
            date: Date in YYYY-MM-DD format (will be converted to YYYYMMDD)
            
        Returns:
            Dictionary with lineup information
        """
        try:
            # Convert date format from YYYY-MM-DD to YYYYMMDD
            if '-' in date:
                date_formatted = date.replace('-', '')
            else:
                date_formatted = date
            
            url = f"{self.base_url}/v1/nba/lineups"
            params = {
                'apikey': self.api_key,
                'date': date_formatted
            }
            
            logger.info(f"Fetching lineups from FantasyNerds for date: {date_formatted}")
            response = requests.get(url, params=params, timeout=10)
            
            # Check if response is successful
            if not response.ok:
                error_text = response.text[:500] if response.text else "No error message"
                logger.error(f"FantasyNerds API returned {response.status_code}: {error_text}")
                # Try to parse as JSON if possible
                try:
                    error_json = response.json()
                    error_msg = error_json.get('message', error_json.get('error', error_text))
                except:
                    error_msg = error_text
                raise requests.exceptions.HTTPError(
                    f"API returned {response.status_code}: {error_msg}",
                    response=response
                )
            
            # Check if response has content
            if not response.text or not response.text.strip():
                logger.error("FantasyNerds API returned empty response")
                raise ValueError("Empty response from FantasyNerds API")
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' not in content_type and 'text/json' not in content_type:
                logger.warning(f"Unexpected content type: {content_type}")
            
            # Try to parse JSON
            try:
                # Use response.json() which handles encoding automatically
                data = response.json()
                if not isinstance(data, dict):
                    logger.error(f"Response is not a dictionary: {type(data)}")
                    raise ValueError(f"Expected dictionary, got {type(data)}")
                logger.info(f"Successfully fetched lineups from FantasyNerds. Found {len(data.get('lineups', {}))} teams")
                return data
            except (json.JSONDecodeError, ValueError) as e:
                # json.JSONDecodeError is raised by response.json() when JSON is invalid
                # ValueError can be raised by our own validation
                response_preview = response.text[:500] if response.text else "(empty)"
                logger.error(f"Failed to decode JSON from FantasyNerds API: {e}")
                logger.error(f"Response status: {response.status_code}, Content-Type: {content_type}")
                logger.error(f"Response preview: {response_preview}")
                raise ValueError(f"Invalid JSON response from FantasyNerds API. Status: {response.status_code}, Error: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching lineups from FantasyNerds: {e}")
            raise
        except ValueError as e:
            logger.error(f"Error parsing response from FantasyNerds: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching lineups: {e}")
            raise

