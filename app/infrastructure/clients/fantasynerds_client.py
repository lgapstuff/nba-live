"""
FantasyNerds HTTP client - Now consumes the FantasyNerds microservice.
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
    HTTP client for FantasyNerds microservice.
    This client now calls the internal FantasyNerds microservice instead of the external API directly.
    """
    
    def __init__(
        self,
        service_url: str = "http://fantasynerds-service:8001",
        api_prefix: str = "/api/v1/fantasynerds"
    ):
        """
        Initialize the client.
        
        Args:
            service_url: Base URL for the FantasyNerds microservice
        """
        self.service_url = service_url.rstrip('/')
        api_prefix = api_prefix.strip()
        if not api_prefix.startswith("/"):
            api_prefix = f"/{api_prefix}"
        self.api_prefix = api_prefix.rstrip("/")
        self.base_url = f"{self.service_url}{self.api_prefix}"
    
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
        Get lineups for a specific date from FantasyNerds microservice.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with lineup information
        """
        try:
            url = f"{self.base_url}/lineups/date/{date}"
            logger.info(f"[FANTASYNERDS SERVICE] REQUEST: Fetching lineups for date: {date}")
            logger.info(f"[FANTASYNERDS SERVICE] REQUEST URL: {url}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[FANTASYNERDS SERVICE] RESPONSE: Successfully fetched lineups")
                return result.get('data', {})
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"[FANTASYNERDS SERVICE] RESPONSE ERROR: {error_msg}")
                raise ValueError(f"FantasyNerds service error: {error_msg}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[FANTASYNERDS SERVICE] REQUEST ERROR: Error fetching lineups: {e}")
            raise
        except Exception as e:
            logger.error(f"[FANTASYNERDS SERVICE] ERROR: Unexpected error: {e}")
            raise
    
    def get_depth_charts(self) -> Dict[str, Any]:
        """
        Get depth charts for all NBA teams from FantasyNerds microservice.
        
        Returns:
            Dictionary with depth charts for all teams
            Format: {"season": 2021, "charts": {"SA": {...}, "DEN": {...}, ...}}
        """
        try:
            url = f"{self.base_url}/depth-charts"
            logger.info(f"[FANTASYNERDS SERVICE] REQUEST: Fetching depth charts")
            logger.info(f"[FANTASYNERDS SERVICE] REQUEST URL: {url}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"[FANTASYNERDS SERVICE] RESPONSE: Successfully fetched depth charts")
                return result.get('data', {})
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"[FANTASYNERDS SERVICE] RESPONSE ERROR: {error_msg}")
                raise ValueError(f"FantasyNerds service error: {error_msg}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[FANTASYNERDS SERVICE] REQUEST ERROR: Error fetching depth charts: {e}")
            raise
        except Exception as e:
            logger.error(f"[FANTASYNERDS SERVICE] ERROR: Unexpected error: {e}")
            raise

