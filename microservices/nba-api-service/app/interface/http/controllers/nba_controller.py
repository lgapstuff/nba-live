"""
NBA API controller.
"""
import logging
from flask import Blueprint, jsonify, request
from typing import List

from app.infrastructure.clients.nba_api_client import NBAClient
from app.infrastructure.clients.nba_cdn_client import NBACdnClient

logger = logging.getLogger(__name__)


def create_nba_controller(client: NBAClient) -> Blueprint:
    """Create and configure the NBA API controller blueprint."""
    bp = Blueprint("nba", __name__, url_prefix="/api/v1")
    cdn_client = NBACdnClient()
    
    @bp.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "nba-api-service"
        })
    
    @bp.route("/players/<int:player_id>/game-log", methods=["GET"])
    def get_player_game_log(player_id: int):
        """Get game log for a specific player."""
        try:
            season = request.args.get('season')
            season_type = request.args.get('season_type', 'Regular Season')
            games = client.get_player_game_log(player_id, season, season_type)
            return jsonify({
                "success": True,
                "player_id": player_id,
                "games": games
            })
        except Exception as e:
            logger.error(f"Error fetching game log: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/players/<int:player_id>/last-games", methods=["GET"])
    def get_player_last_n_games(player_id: int):
        """Get last N games for a specific player."""
        try:
            n = int(request.args.get('n', 10))
            season = request.args.get('season')
            season_type = request.args.get('season_type', 'Regular Season')
            games = client.get_player_last_n_games(player_id, n, season, season_type)
            return jsonify({
                "success": True,
                "player_id": player_id,
                "games": games
            })
        except Exception as e:
            logger.error(f"Error fetching last games: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/players/find-by-name", methods=["GET"])
    def find_player_by_name():
        """Find NBA player ID by name."""
        try:
            player_name = request.args.get('name')
            if not player_name:
                return jsonify({
                    "success": False,
                    "error": "name parameter is required"
                }), 400
            
            player_id = client.find_nba_player_id_by_name(player_name)
            return jsonify({
                "success": True,
                "player_name": player_name,
                "player_id": player_id
            })
        except Exception as e:
            logger.error(f"Error finding player: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/teams/<team_abbr>/players", methods=["GET"])
    def get_team_players(team_abbr: str):
        """Get all players for a specific team."""
        try:
            season = request.args.get('season')
            players = client.get_team_players(team_abbr, season)
            return jsonify({
                "success": True,
                "team_abbr": team_abbr,
                "players": players
            })
        except Exception as e:
            logger.error(f"Error fetching team players: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/games/<game_id>/boxscore", methods=["GET"])
    def get_live_boxscore(game_id: str):
        """Get live boxscore for a game."""
        try:
            player_ids_str = request.args.get('player_ids')
            player_ids = None
            if player_ids_str:
                player_ids = [int(pid) for pid in player_ids_str.split(',') if pid.strip()]
            boxscore = client.get_live_boxscore(game_id, player_ids)
            return jsonify({
                "success": True,
                "game_id": game_id,
                "boxscore": boxscore,
                "filtered": bool(player_ids)
            })
        except Exception as e:
            logger.error(f"Error fetching boxscore: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route("/games/<game_id>/status", methods=["GET"])
    def get_game_status(game_id: str):
        """Get live status for a game (period/clock)."""
        try:
            game_date = request.args.get('game_date')  # YYYY-MM-DD optional
            status = client.get_game_status(game_id, game_date)
            if not status:
                return jsonify({
                    "success": False,
                    "game_id": game_id,
                    "message": "No live status found for game"
                }), 404
            return jsonify({
                "success": True,
                "game_id": game_id,
                "status": status
            })
        except Exception as e:
            logger.error(f"Error fetching game status: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route("/games/find-game-id", methods=["GET"])
    def find_game_id():
        """Find NBA GameID by teams and date."""
        try:
            home_team = request.args.get('home_team')
            away_team = request.args.get('away_team')
            game_date = request.args.get('game_date')
            
            if not home_team or not away_team:
                return jsonify({
                    "success": False,
                    "error": "home_team and away_team parameters are required"
                }), 400
            
            game_id = client.find_nba_game_id(home_team, away_team, game_date)
            return jsonify({
                "success": True,
                "home_team": home_team,
                "away_team": away_team,
                "game_date": game_date,
                "game_id": game_id
            })
        except Exception as e:
            logger.error(f"Error finding game ID: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route("/cdn/scoreboard/today", methods=["GET"])
    def get_cdn_scoreboard():
        """Get today's live scoreboard from NBA CDN."""
        try:
            data = cdn_client.get_todays_scoreboard()
            return jsonify({
                "success": True,
                "scoreboard": data
            })
        except Exception as e:
            logger.error(f"Error fetching CDN scoreboard: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route("/cdn/boxscore/<game_id>", methods=["GET"])
    def get_cdn_boxscore(game_id: str):
        """Get live boxscore from NBA CDN for a specific game."""
        try:
            cache_bust = request.args.get('t')
            data = cdn_client.get_boxscore(game_id, cache_bust=cache_bust)
            return jsonify({
                "success": True,
                "game_id": game_id,
                "boxscore": data
            })
        except Exception as e:
            logger.error(f"Error fetching CDN boxscore: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    return bp
