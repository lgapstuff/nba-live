"""
NBA endpoints blueprint.
"""
from flask import Blueprint, request, jsonify
import requests

from app.config.settings import Config
from app.infrastructure.database.connection import DatabaseConnection
from app.infrastructure.repositories.game_repository import GameRepository
from app.infrastructure.repositories.lineup_repository import LineupRepository
from app.infrastructure.repositories.odds_history_repository import OddsHistoryRepository
from app.infrastructure.clients.fantasynerds_client import FantasyNerdsClient
from app.infrastructure.clients.odds_api_client import OddsAPIClient
from app.infrastructure.clients.nba_api_client import NBAClient
from app.application.services.schedule_service import ScheduleService
from app.application.services.lineup_service import LineupService
from app.application.services.odds_service import OddsService
from app.application.services.depth_chart_service import DepthChartService
from app.application.services.player_stats_service import PlayerStatsService
from app.application.services.game_log_service import GameLogService
from app.infrastructure.repositories.game_log_repository import GameLogRepository
from app.interface.http.controllers.schedule_controller import ScheduleController
from app.interface.http.controllers.lineup_controller import LineupController
from app.interface.http.controllers.odds_controller import OddsController
from app.interface.http.controllers.depth_chart_controller import DepthChartController
from app.interface.http.controllers.game_log_controller import GameLogController

nba_bp = Blueprint("nba", __name__, url_prefix="/nba")

# Initialize dependencies
config = Config()
db_connection = DatabaseConnection(config)
game_repository = GameRepository(db_connection)
lineup_repository = LineupRepository(db_connection)
odds_history_repository = OddsHistoryRepository(db_connection)
# Initialize clients to consume microservices
fantasynerds_client = FantasyNerdsClient(config.FANTASYNERDS_SERVICE_URL)
odds_api_client = OddsAPIClient(config.ODDS_API_SERVICE_URL)

# Initialize NBA API client (now consumes microservice)
nba_client = None
player_stats_service = None
game_log_service = None
try:
    nba_client = NBAClient(
        config.NBA_API_SERVICE_URL,
        request_timeout_seconds=config.NBA_API_REQUEST_TIMEOUT_SECONDS
    )
    # Initialize game log repository and service
    game_log_repository = GameLogRepository(db_connection)
    game_log_service = GameLogService(
        nba_client,
        game_log_repository,
        thread_timeout_seconds=config.NBA_API_GAME_LOG_THREAD_TIMEOUT_SECONDS
    )
    # Initialize player stats service with game log service for optimization
    player_stats_service = PlayerStatsService(nba_client, game_log_service)
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"NBA API client not available: {e}. OVER/UNDER history will not be calculated.")

schedule_service = ScheduleService(game_repository)
# Initialize depth chart service with NBA API (preferred) and FantasyNerds (fallback)
depth_chart_service = DepthChartService(
    lineup_repository=lineup_repository,
    nba_api_port=nba_client,  # Use NBA API for rosters
    fantasynerds_port=fantasynerds_client  # Keep for backward compatibility
)
lineup_service = LineupService(
    fantasynerds_client,
    lineup_repository,
    game_repository,
    depth_chart_service,
    player_stats_service,
    game_log_repository
)
odds_service = OddsService(odds_api_client, lineup_repository, game_repository, depth_chart_service, player_stats_service, odds_history_repository)
schedule_controller = ScheduleController(schedule_service, depth_chart_service)
lineup_controller = LineupController(lineup_service, odds_service)
odds_controller = OddsController(odds_service)
depth_chart_controller = DepthChartController(depth_chart_service)
game_log_controller = (
    GameLogController(
        game_log_service,
        thread_timeout_seconds=config.NBA_API_GAME_LOG_THREAD_TIMEOUT_SECONDS
    )
    if game_log_service else None
)


@nba_bp.route("/games", methods=["GET"])
def get_games():
    """
    Get games for a specific date.
    
    Query parameters:
        date: Date in YYYY-MM-DD format (required)
    
    Returns:
        JSON with games for the specified date
    """
    date = request.args.get('date')
    if not date:
        return {
            "success": False,
            "message": "date parameter is required (format: YYYY-MM-DD)"
        }, 400
    
    return schedule_controller.get_games_by_date(date)


@nba_bp.route("/schedule/import", methods=["POST"])
def import_schedule():
    """
    Import schedule from JSON file or request body.
    
    Accepts:
        - File upload (multipart/form-data with 'file' field)
        - JSON body with schedule data
        - Query parameter 'json_path' pointing to a file path
    
    Returns:
        JSON with import results
    """
    return schedule_controller.import_schedule()


@nba_bp.route("/lineups", methods=["GET"])
def get_lineups():
    """
    Get lineups for a specific date.
    
    Query parameters:
        date: Date in YYYY-MM-DD format (required)
    
    Returns:
        JSON with lineups for the specified date
    """
    date = request.args.get('date')
    if not date:
        return {
            "success": False,
            "message": "date parameter is required (format: YYYY-MM-DD)"
        }, 400
    
    return lineup_controller.get_lineups_by_date(date)


@nba_bp.route("/lineups/resolve", methods=["GET"])
def resolve_lineup_by_teams():
    """
    Resolve lineup for a game by teams (optionally by date).

    Query parameters:
        home_team: Home team abbreviation (required)
        away_team: Away team abbreviation (required)
        date: Date in YYYY-MM-DD format (optional)
    """
    home_team = request.args.get('home_team')
    away_team = request.args.get('away_team')
    date = request.args.get('date')
    if not home_team or not away_team:
        return {
            "success": False,
            "message": "home_team and away_team parameters are required"
        }, 400
    return lineup_controller.get_lineup_by_teams(home_team, away_team, date)


@nba_bp.route("/lineups/import", methods=["POST"])
def import_lineups():
    """
    Import lineups from FantasyNerds API or request body.
    
    Query parameters:
        date: Date in YYYY-MM-DD format (required if not in body)
    
    Request body (optional):
        JSON with lineup data
    
    Returns:
        JSON with import results
    """
    return lineup_controller.import_lineups()


@nba_bp.route("/games/<game_id>/lineups", methods=["GET"])
def get_game_lineups(game_id: str):
    """
    Get lineups for a specific game.
    
    Path parameters:
        game_id: Game identifier
    
    Returns:
        JSON with lineup for the specified game
    """
    return lineup_controller.get_lineup_by_game_id(game_id)


@nba_bp.route("/games/<game_id>/odds", methods=["GET"])
def get_game_odds(game_id: str):
    """
    Get player points odds for a specific game.
    Matches players from lineup with odds from The Odds API.
    
    Path parameters:
        game_id: Game identifier
    
    Returns:
        JSON with matched player odds
    """
    return odds_controller.get_player_points_odds(game_id)


@nba_bp.route("/games/<game_id>/scores", methods=["GET"])
def get_game_scores(game_id: str):
    """
    Get scores for a specific game from The Odds API.
    
    Path parameters:
        game_id: Game identifier
    
    Returns:
        JSON with game scores
    """
    return odds_controller.get_game_scores(game_id)


@nba_bp.route("/odds/import", methods=["POST"])
def import_odds():
    """
    Import odds for all games of today.
    
    Query parameters:
        date: Date in YYYY-MM-DD format (required, defaults to today)
    
    Returns:
        JSON with import results
    """
    date = request.args.get('date')
    if not date:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        la_tz = ZoneInfo('America/Los_Angeles')
        date = datetime.now(la_tz).date().strftime('%Y-%m-%d')
    
    return odds_controller.import_odds_for_date(date)


@nba_bp.route("/depth-charts/import", methods=["POST"])
def import_depth_charts():
    """
    Import team rosters from NBA API for all teams.
    This replaces the old FantasyNerds depth charts with official NBA rosters.
    
    Returns:
        JSON with import results
    """
    return depth_chart_controller.import_depth_charts()


@nba_bp.route("/depth-charts/check", methods=["GET"])
def check_depth_charts():
    """
    Check if depth charts exist in the database.
    
    Returns:
        JSON with has_depth_charts boolean
    """
    return depth_chart_controller.check_depth_charts()


@nba_bp.route("/games/<game_id>/rosters", methods=["POST"])
def import_rosters_for_game(game_id: str):
    """
    Import rosters for teams in a specific game.
    Only loads rosters that don't already exist in the database.
    
    Path parameters:
        game_id: Game identifier
    
    Returns:
        JSON with import results
    """
    if not depth_chart_controller:
        return {
            "success": False,
            "message": "Depth chart service not available."
        }, 503
    
    return depth_chart_controller.import_rosters_for_game(game_id)


@nba_bp.route("/games/<game_id>/game-logs", methods=["POST"])
def load_game_logs(game_id: str):
    """
    Load game logs for all players in an event.
    Pre-loads the last 25 games for each player from both teams.
    
    Path parameters:
        game_id: Game identifier
    
    Returns:
        JSON with loading results
    """
    if not game_log_controller:
        return {
            "success": False,
            "message": "Game log service not available. NBA API client not initialized."
        }, 503
    
    return game_log_controller.load_game_logs_for_event(game_id)


@nba_bp.route("/players/<int:player_id>/game-logs/load", methods=["POST"])
def load_player_game_logs(player_id: int):
    """
    Load game logs for a specific player from NBA API and save to database.
    
    Path parameters:
        player_id: NBA player ID
    
    Query parameters:
        player_name: Player name (optional, for logging)
        num_games: Number of games to load (default: 25)
    
    Returns:
        JSON with loading results
    """
    if not game_log_controller:
        return {
            "success": False,
            "message": "Game log service not available. NBA API client not initialized."
        }, 503
    
    player_name = request.args.get('player_name')
    num_games = int(request.args.get('num_games', 15))
    return game_log_controller.load_player_game_logs(player_id, player_name, num_games)


@nba_bp.route("/players/<int:player_id>/game-logs", methods=["GET"])
def get_player_game_logs(player_id: int):
    """
    Get game logs for a specific player from database only.
    Does NOT load from NBA API. Use POST /players/<player_id>/game-logs/load to pre-load.
    
    Path parameters:
        player_id: NBA player ID
    
    Query parameters:
        player_name: Player name (optional, for logging)
    
    Returns:
        JSON with game logs (last 25 games from database)
    """
    if not game_log_controller:
        return {
            "success": False,
            "message": "Game log service not available. NBA API client not initialized."
        }, 503
    
    player_name = request.args.get('player_name')
    return game_log_controller.get_player_game_logs(player_id, player_name)


@nba_bp.route("/games/<game_id>/live-stats", methods=["POST"])
def get_live_player_stats(game_id: str):
    """
    Get live statistics for selected players in a game.
    
    Path parameters:
        game_id: Game identifier
    
    Request body:
        JSON with player_ids array:
        {
            "player_ids": [123456, 789012, ...]
        }
    
    Returns:
        JSON with live statistics for each player:
        {
            "success": true,
            "game_id": "...",
            "nba_game_id": "0022400123",
            "player_stats": {
                "123456": {
                    "PTS": 15,
                    "AST": 5,
                    "REB": 8,
                    "MIN": "25:30",
                    ...
                },
                ...
            }
        }
    """
    if not game_log_controller:
        return jsonify({
            "success": False,
            "message": "Game log service not available. NBA API client not initialized."
        }), 503
    
    return game_log_controller.get_live_player_stats(game_id)


@nba_bp.route("/nba-games/<nba_game_id>/boxscore", methods=["GET"])
def get_nba_game_boxscore(nba_game_id: str):
    """
    Get full boxscore for an NBA game (by NBA Game_ID).
    
    Path parameters:
        nba_game_id: NBA Game_ID (e.g., "0022500556")
    
    Query parameters (optional):
        player_ids: Comma-separated NBA player IDs to filter boxscore
    
    Returns:
        JSON with boxscore data (includes START_POSITION when available)
    """
    if not nba_client:
        return {
            "success": False,
            "message": "NBA API client not available."
        }, 503
    
    player_ids_str = request.args.get('player_ids')
    player_ids = None
    if player_ids_str:
        player_ids = [int(pid) for pid in player_ids_str.split(',') if pid.strip()]
    
    boxscore = nba_client.get_live_boxscore(nba_game_id, player_ids)
    if not boxscore:
        return {
            "success": False,
            "message": f"No boxscore available for NBA game {nba_game_id}",
            "nba_game_id": nba_game_id
        }, 404
    
    return {
        "success": True,
        "nba_game_id": nba_game_id,
        "boxscore": boxscore,
        "filtered": bool(player_ids)
    }


@nba_bp.route("/cdn/scoreboard/today", methods=["GET"])
def get_cdn_scoreboard():
    """
    Get today's live scoreboard from NBA CDN (via NBA API microservice).
    """
    try:
        url = f"{config.NBA_API_SERVICE_URL}/api/v1/cdn/scoreboard/today"
        response = requests.get(url, timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching CDN scoreboard: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@nba_bp.route("/cdn/boxscore/<game_id>", methods=["GET"])
def get_cdn_boxscore(game_id: str):
    """
    Get live boxscore from NBA CDN (via NBA API microservice).
    """
    try:
        url = f"{config.NBA_API_SERVICE_URL}/api/v1/cdn/boxscore/{game_id}"
        response = requests.get(url, timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching CDN boxscore: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@nba_bp.route("/cdn/playbyplay/<game_id>", methods=["GET"])
def get_cdn_playbyplay(game_id: str):
    """
    Get live play-by-play from NBA CDN (via NBA API microservice).
    """
    try:
        url = f"{config.NBA_API_SERVICE_URL}/api/v1/cdn/playbyplay/{game_id}"
        response = requests.get(url, timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching CDN play-by-play: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@nba_bp.route("/players/<int:player_id>/odds-history", methods=["GET"])
def get_player_odds_history(player_id: int):
    """
    Get odds history for a specific player.
    
    Path parameters:
        player_id: Player ID
    
    Query parameters:
        game_id: Optional game ID to filter by
        limit: Optional limit on number of records (default: 100)
    
    Returns:
        JSON with odds history
    """
    game_id = request.args.get('game_id')
    limit = request.args.get('limit', type=int)
    
    try:
        history = odds_history_repository.get_player_odds_history(
            player_id=player_id,
            game_id=game_id,
            limit=limit or 100
        )
        
        return {
            "success": True,
            "odds_history": history,
            "count": len(history)
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting odds history for player {player_id}: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error getting odds history: {str(e)}"
        }, 500

