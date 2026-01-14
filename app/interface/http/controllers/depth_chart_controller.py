"""
Depth chart controller for NBA depth chart endpoints.
"""
import logging
from flask import jsonify
from typing import Dict, Any, Tuple

from app.application.services.depth_chart_service import DepthChartService

logger = logging.getLogger(__name__)


class DepthChartController:
    """Controller for depth chart endpoints."""
    
    def __init__(self, depth_chart_service: DepthChartService):
        """
        Initialize the controller.
        
        Args:
            depth_chart_service: Depth chart service instance
        """
        self.depth_chart_service = depth_chart_service
    
    def import_depth_charts(self) -> Tuple[Dict[str, Any], int]:
        """
        Import rosters from NBA API (preferred) or FantasyNerds API (fallback).
        
        Returns:
            JSON response and status code
        """
        try:
            # Try NBA API first (preferred method)
            result = self.depth_chart_service.import_rosters_from_nba_api()
            
            # If NBA API failed, fallback to FantasyNerds (for backward compatibility)
            if not result.get('success'):
                logger.warning("NBA API import failed, trying FantasyNerds as fallback")
                result = self.depth_chart_service.import_depth_charts()
            
            status_code = 200 if result.get('success', False) else 400
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in import_depth_charts: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500
    
    def check_depth_charts(self) -> Tuple[Dict[str, Any], int]:
        """
        Check if depth charts exist in the database.
        
        Returns:
            JSON response with has_depth_charts boolean
        """
        try:
            has_charts = self.depth_chart_service.has_depth_charts()
            return jsonify({
                "success": True,
                "has_depth_charts": has_charts
            }), 200
            
        except Exception as e:
            logger.error(f"Error in check_depth_charts: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500
    
    def import_rosters_for_game(self, game_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Import rosters for teams in a specific game.
        Only loads rosters that don't already exist in the database.
        
        Args:
            game_id: Game identifier
            
        Returns:
            JSON response and status code
        """
        try:
            # Get game info to know teams
            from app.infrastructure.repositories.game_repository import GameRepository
            from app.config.settings import Config
            from app.infrastructure.database.connection import DatabaseConnection
            
            config = Config()
            db = DatabaseConnection(config)
            game_repo = GameRepository(db)
            
            game = game_repo.get_game_by_id(game_id)
            if not game:
                return jsonify({
                    "success": False,
                    "message": f"Game {game_id} not found"
                }), 404
            
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            
            if not home_team or not away_team:
                return jsonify({
                    "success": False,
                    "message": "Game teams not found"
                }), 400
            
            # Import rosters for both teams
            team_abbrs = [home_team, away_team]
            result = self.depth_chart_service.import_rosters_for_teams(team_abbrs)
            
            status_code = 200 if result.get('success', False) else 400
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in import_rosters_for_game: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500

