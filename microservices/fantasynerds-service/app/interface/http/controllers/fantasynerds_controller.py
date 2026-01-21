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
    
    @bp.route("/lineups", methods=["GET"])
    def get_lineups_by_date():
        """
        Get lineups for a specific date or current day if no date is provided.
        
        Query Parameters:
            date (optional): Date in YYYY-MM-DD format. If not provided, returns current day's lineups.
        """
        try:
            date = request.args.get("date")
            lineups = client.get_lineups_by_date(date)
            response_data = {
                "success": True,
                "data": lineups
            }
            if date:
                response_data["date"] = date
            return jsonify(response_data)
        except Exception as e:
            logger.error(f"Error fetching lineups for date {date or 'current day'}: {e}", exc_info=True)
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
