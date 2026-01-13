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
        Import depth charts from FantasyNerds API.
        
        Returns:
            JSON response and status code
        """
        try:
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

