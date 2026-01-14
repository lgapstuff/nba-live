"""
FantasyNerds API controller.
"""
import logging
from flask import Blueprint, jsonify, request
from typing import Dict, Any

from app.infrastructure.clients.fantasynerds_client import FantasyNerdsClient

logger = logging.getLogger(__name__)


def create_fantasynerds_controller(client: FantasyNerdsClient) -> Blueprint:
    """
    Create and configure the FantasyNerds controller blueprint.
    
    Args:
        client: FantasyNerds API client instance
        
    Returns:
        Configured Flask Blueprint
    """
    bp = Blueprint("fantasynerds", __name__, url_prefix="/api/v1")
    
    @bp.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "fantasynerds-service"
        })
    
    @bp.route("/games/<date>", methods=["GET"])
    def get_games(date: str):
        """
        Get games for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
        """
        try:
            games = client.get_games_for_date(date)
            return jsonify({
                "success": True,
                "date": date,
                "games": games
            })
        except Exception as e:
            logger.error(f"Error fetching games for date {date}: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/lineups/date/<date>", methods=["GET"])
    def get_lineups_by_date(date: str):
        """
        Get lineups for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
        """
        try:
            lineups = client.get_lineups_by_date(date)
            return jsonify({
                "success": True,
                "date": date,
                "data": lineups
            })
        except Exception as e:
            logger.error(f"Error fetching lineups for date {date}: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/lineups/game/<game_id>", methods=["GET"])
    def get_lineups_for_game(game_id: str):
        """
        Get lineups for a specific game.
        
        Args:
            game_id: Game identifier
        """
        try:
            lineups = client.get_lineups_for_game(game_id)
            return jsonify({
                "success": True,
                "game_id": game_id,
                "data": lineups
            })
        except Exception as e:
            logger.error(f"Error fetching lineups for game {game_id}: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/depth-charts", methods=["GET"])
    def get_depth_charts():
        """Get depth charts for all NBA teams."""
        try:
            depth_charts = client.get_depth_charts()
            return jsonify({
                "success": True,
                "data": depth_charts
            })
        except Exception as e:
            logger.error(f"Error fetching depth charts: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    return bp
