"""
Schedule controller for NBA schedule endpoints.
"""
import logging
from flask import jsonify, request
from typing import Dict, Any, Tuple

from app.application.services.schedule_service import ScheduleService
from app.application.services.depth_chart_service import DepthChartService

logger = logging.getLogger(__name__)


class ScheduleController:
    """Controller for schedule endpoints."""
    
    def __init__(self, schedule_service: ScheduleService, depth_chart_service: DepthChartService = None):
        """
        Initialize the controller.
        
        Args:
            schedule_service: Schedule service instance
            depth_chart_service: Depth chart service instance (optional)
        """
        self.schedule_service = schedule_service
        self.depth_chart_service = depth_chart_service
    
    def import_schedule(self) -> Tuple[Dict[str, Any], int]:
        """
        Import schedule from JSON file and automatically load rosters from NBA API.
        Only requires 'schedule_file'. Depth charts are now loaded from NBA API automatically.
        
        Returns:
            JSON response and status code
        """
        try:
            import tempfile
            import os
            
            # Check if schedule file was uploaded
            schedule_file = request.files.get('schedule_file')
            
            if not schedule_file or schedule_file.filename == '':
                return jsonify({
                    "success": False,
                    "message": "schedule_file is required"
                }), 400
            
            # Save uploaded file temporarily
            schedule_tmp_path = None
            
            try:
                # Save schedule file
                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.json') as tmp:
                    schedule_file.save(tmp.name)
                    schedule_tmp_path = tmp.name
                
                # Import schedule
                schedule_result = self.schedule_service.import_schedule_from_json(schedule_tmp_path)
                
                # Automatically load rosters from NBA API (optimization)
                roster_result = None
                if self.depth_chart_service and schedule_result.get('success', False):
                    logger.info("Automatically loading rosters from NBA API after schedule import...")
                    roster_result = self.depth_chart_service.import_rosters_from_nba_api()
                else:
                    roster_result = {
                        "success": False,
                        "message": "Depth chart service not available or schedule import failed"
                    }
                
                # Combine results
                combined_result = {
                    "success": schedule_result.get('success', False) and roster_result.get('success', False),
                    "schedule": schedule_result,
                    "rosters": roster_result,
                    "message": f"Schedule: {schedule_result.get('message', 'Unknown')}. Rosters: {roster_result.get('message', 'Unknown')}"
                }
                
                status_code = 200 if combined_result['success'] else 400
                return jsonify(combined_result), status_code
                
            finally:
                # Clean up temporary file
                if schedule_tmp_path and os.path.exists(schedule_tmp_path):
                    os.unlink(schedule_tmp_path)
                
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

