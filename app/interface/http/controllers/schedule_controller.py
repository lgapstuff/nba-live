"""
Schedule controller for NBA schedule endpoints.
"""
import logging
from flask import jsonify, request
from typing import Dict, Any, Tuple

from app.application.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)


class ScheduleController:
    """Controller for schedule endpoints."""
    
    def __init__(self, schedule_service: ScheduleService):
        """
        Initialize the controller.
        
        Args:
            schedule_service: Schedule service instance
        """
        self.schedule_service = schedule_service
    
    def import_schedule(self) -> Tuple[Dict[str, Any], int]:
        """
        Import schedule from JSON file or request body.
        
        Returns:
            JSON response and status code
        """
        try:
            # Check if file was uploaded
            if 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        "success": False,
                        "message": "No file selected"
                    }), 400
                
                # Save uploaded file temporarily
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
                    file.save(tmp.name)
                    tmp_path = tmp.name
                
                try:
                    result = self.schedule_service.import_schedule_from_json(tmp_path)
                    status_code = 200 if result['success'] else 400
                    return jsonify(result), status_code
                finally:
                    os.unlink(tmp_path)
            
            # Check if JSON data is in request body
            elif request.is_json:
                data = request.get_json()
                result = self.schedule_service.import_schedule_from_dict(data)
                status_code = 200 if result['success'] else 400
                return jsonify(result), status_code
            
            # Check if json_path parameter is provided
            elif 'json_path' in request.args:
                json_path = request.args.get('json_path')
                result = self.schedule_service.import_schedule_from_json(json_path)
                status_code = 200 if result['success'] else 400
                return jsonify(result), status_code
            
            else:
                return jsonify({
                    "success": False,
                    "message": "No file, JSON data, or json_path parameter provided"
                }), 400
                
        except Exception as e:
            logger.error(f"Error in import_schedule: {e}")
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500
    
    def get_games_by_date(self, date: str) -> Tuple[Dict[str, Any], int]:
        """
        Get games for a specific date from schedule.
        Returns games even if they don't have lineups yet.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            JSON response and status code
        """
        try:
            games = self.schedule_service.get_games_by_date(date)
            
            # Convert datetime objects to strings for JSON serialization
            # Also add lineup status and odds availability
            for game in games:
                if 'game_date' in game and game['game_date']:
                    game['game_date'] = str(game['game_date'])
                if 'game_time' in game and game['game_time']:
                    game['game_time'] = str(game['game_time'])
                
                # Add empty lineups structure
                game['lineups'] = {}
                game['has_lineup'] = False
                
                # Check if odds are available (would need odds_service injected)
                # For now, default to True if game is in future
                game['has_odds_available'] = True  # Will be checked in frontend
            
            return jsonify({
                "success": True,
                "date": date,
                "count": len(games),
                "games": games
            }), 200
            
        except Exception as e:
            logger.error(f"Error in get_games_by_date: {e}")
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500

