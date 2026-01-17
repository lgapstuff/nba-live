"""
Lineup controller for NBA lineup endpoints.
"""
import logging
from flask import jsonify, request
from typing import Dict, Any, Tuple, Optional

from app.application.services.lineup_service import LineupService
from app.application.services.odds_service import OddsService

logger = logging.getLogger(__name__)


class LineupController:
    """Controller for lineup endpoints."""
    
    def __init__(self, lineup_service: LineupService, odds_service: Optional[OddsService] = None):
        """
        Initialize the controller.
        
        Args:
            lineup_service: Lineup service instance
            odds_service: Optional odds service to check odds availability
        """
        self.lineup_service = lineup_service
        self.odds_service = odds_service
    
    def import_lineups(self) -> Tuple[Dict[str, Any], int]:
        """
        Import lineups from FantasyNerds API or request body.
        
        Query parameters:
            date: Date in YYYY-MM-DD format (required if not in body)
        
        Request body (optional):
            JSON with lineup data
        
        Returns:
            JSON response and status code
        """
        try:
            # Check if JSON data is in request body
            # Use silent=True to avoid exceptions on empty body
            json_data = request.get_json(silent=True)
            if json_data is not None:
                # Only process if we actually got JSON data (not empty body)
                result = self.lineup_service.import_lineups_from_dict(json_data)
                status_code = 200 if result['success'] else 400
                return jsonify(result), status_code
            
            # Check if date parameter is provided
            date = request.args.get('date')
            if not date:
                return jsonify({
                    "success": False,
                    "message": "date parameter is required (format: YYYY-MM-DD) or provide JSON body"
                }), 400
            
            # Validate that only today's lineups can be loaded (Los Angeles timezone)
            from datetime import datetime
            from zoneinfo import ZoneInfo
            
            # Get today's date in Los Angeles timezone
            la_tz = ZoneInfo('America/Los_Angeles')
            today_la = datetime.now(la_tz).date()
            
            # Parse the requested date
            try:
                requested_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": f"Invalid date format. Expected YYYY-MM-DD, got: {date}"
                }), 400
            
            # Only allow loading lineups for today
            if requested_date != today_la:
                return jsonify({
                    "success": False,
                    "message": f"Solo se pueden cargar lineups del día actual ({today_la.strftime('%Y-%m-%d')}). Fecha solicitada: {date}"
                }), 400
            
            result = self.lineup_service.import_lineups_for_date(date)
            status_code = 200 if result['success'] else 400
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in import_lineups: {e}", exc_info=True)
            error_msg = str(e)
            # Clean up error messages that might confuse users
            if "Failed to decode JSON" in error_msg or "Expecting value" in error_msg:
                error_msg = "Error al comunicarse con la API de FantasyNerds. Por favor intenta nuevamente."
            return jsonify({
                "success": False,
                "message": f"Internal server error: {error_msg}"
            }), 500
    
    def get_lineups_by_date(self, date: str) -> Tuple[Dict[str, Any], int]:
        """
        Get lineups for a specific date.
        Only returns lineups that are already confirmed in the database.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            JSON response and status code
        """
        try:
            lineups = self.lineup_service.get_lineups_by_date(date, auto_fetch=False)
            
            # Check if each game has odds available
            if self.odds_service:
                for game in lineups:
                    # Check if odds are available for this game
                    has_odds = self.odds_service.check_if_game_has_odds(game)
                    game['has_odds_available'] = has_odds
                    # Mark if lineup is confirmed (has lineups data)
                    game['has_lineup'] = bool(game.get('lineups'))
            else:
                # If no odds service, default to False
                for game in lineups:
                    game['has_odds_available'] = False
                    game['has_lineup'] = bool(game.get('lineups'))
            
            return jsonify({
                "success": True,
                "date": date,
                "count": len(lineups),
                "games": lineups
            }), 200
            
        except Exception as e:
            logger.error(f"Error in get_lineups_by_date: {e}")
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500
    
    def get_lineup_by_game_id(self, game_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Get lineup for a specific game.
        
        Args:
            game_id: Game identifier
            
        Returns:
            JSON response and status code
        """
        try:
            lineup = self.lineup_service.get_lineup_by_game_id(game_id)
            
            if not lineup:
                return jsonify({
                    "success": False,
                    "message": f"Lineup not found for game {game_id}"
                }), 404
            
            return jsonify({
                "success": True,
                "game_id": game_id,
                "lineup": lineup
            }), 200
            
        except Exception as e:
            logger.error(f"Error in get_lineup_by_game_id: {e}")
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500

    def get_lineup_by_teams(self, home_team: str, away_team: str, date: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Get lineup for a game identified by team abbreviations.

        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            date: Optional date in YYYY-MM-DD format

        Returns:
            JSON response and status code
        """
        try:
            resolved = self.lineup_service.get_lineup_by_teams(home_team, away_team, date)

            if not resolved:
                return jsonify({
                    "success": True,
                    "lineup": [],
                    "message": "No game found for the specified matchup"
                }), 200

            game = resolved.get("game")
            lineup = resolved.get("lineup")

            if not lineup:
                return jsonify({
                    "success": True,
                    "game_id": game.get("game_id") if game else None,
                    "lineup": [],
                    "message": "No lineup found for the specified matchup"
                }), 200

            return jsonify({
                "success": True,
                "home_team": home_team,
                "away_team": away_team,
                "game_id": game.get("game_id") if game else None,
                "lineup": lineup
            }), 200

        except Exception as e:
            logger.error(f"Error in get_lineup_by_teams: {e}")
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500

