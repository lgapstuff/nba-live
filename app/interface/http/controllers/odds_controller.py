"""
Odds controller for NBA odds endpoints.
"""
import logging
from flask import jsonify
from typing import Dict, Any, Tuple

from app.application.services.odds_service import OddsService

logger = logging.getLogger(__name__)


class OddsController:
    """Controller for odds endpoints."""
    
    def __init__(self, odds_service: OddsService):
        """
        Initialize the controller.
        
        Args:
            odds_service: Odds service instance
        """
        self.odds_service = odds_service
    
    def get_player_points_odds(self, game_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Get player points odds for a specific game.
        
        Args:
            game_id: Game identifier
            
        Returns:
            JSON response and status code
        """
        try:
            result = self.odds_service.get_player_points_odds_for_game(game_id)
            
            # Always return 200, even if no match found
            # This allows frontend to display the error message properly
            # The success field in the response indicates if odds were found
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"Error in get_player_points_odds: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500
    
    def import_odds_for_date(self, date: str) -> Tuple[Dict[str, Any], int]:
        """
        Import odds for all games of a specific date.
        Players found in odds are saved as BENCH if not in lineup,
        or updated to STARTER if they're already in the lineup.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            JSON response and status code
        """
        try:
            result = self.odds_service.import_odds_for_date(date)
            status_code = 200 if result.get('success', False) else 400
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in import_odds_for_date: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500

