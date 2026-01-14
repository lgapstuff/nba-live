"""
Odds API controller.
"""
import logging
from flask import Blueprint, jsonify, request

from app.infrastructure.clients.odds_api_client import OddsAPIClient

logger = logging.getLogger(__name__)


def create_odds_controller(client: OddsAPIClient) -> Blueprint:
    """Create and configure the Odds API controller blueprint."""
    bp = Blueprint("odds", __name__, url_prefix="/api/v1")
    
    @bp.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "odds-api-service"
        })
    
    @bp.route("/events", methods=["GET"])
    def get_events():
        """Get events for a specific sport."""
        try:
            sport = request.args.get('sport', 'basketball_nba')
            events = client.get_events_for_sport(sport)
            return jsonify({
                "success": True,
                "sport": sport,
                "events": events
            })
        except Exception as e:
            logger.error(f"Error fetching events: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/events/<event_id>/odds", methods=["GET"])
    def get_player_odds(event_id: str):
        """Get player props odds for a specific event."""
        try:
            regions = request.args.get('regions', 'us')
            markets = request.args.get('markets', 'player_points,player_assists,player_rebounds')
            odds_format = request.args.get('odds_format', 'american')
            
            odds = client.get_player_points_odds(event_id, regions, markets, odds_format)
            return jsonify({
                "success": True,
                "event_id": event_id,
                "data": odds
            })
        except Exception as e:
            logger.error(f"Error fetching odds: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/scores", methods=["GET"])
    def get_scores():
        """Get scores for games."""
        try:
            sport = request.args.get('sport', 'basketball_nba')
            days_from = int(request.args.get('days_from', 1))
            event_ids = request.args.get('event_ids')
            
            scores = client.get_scores(sport, days_from, event_ids)
            return jsonify({
                "success": True,
                "sport": sport,
                "scores": scores
            })
        except Exception as e:
            logger.error(f"Error fetching scores: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    return bp
