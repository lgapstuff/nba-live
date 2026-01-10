"""
NBA endpoints blueprint.
"""
from flask import Blueprint, request

from app.config.settings import Config
from app.infrastructure.database.connection import DatabaseConnection
from app.infrastructure.repositories.game_repository import GameRepository
from app.infrastructure.repositories.lineup_repository import LineupRepository
from app.infrastructure.clients.fantasynerds_client import FantasyNerdsClient
from app.infrastructure.clients.odds_api_client import OddsAPIClient
from app.application.services.schedule_service import ScheduleService
from app.application.services.lineup_service import LineupService
from app.application.services.odds_service import OddsService
from app.interface.http.controllers.schedule_controller import ScheduleController
from app.interface.http.controllers.lineup_controller import LineupController
from app.interface.http.controllers.odds_controller import OddsController

nba_bp = Blueprint("nba", __name__, url_prefix="/nba")

# Initialize dependencies
config = Config()
db_connection = DatabaseConnection(config)
game_repository = GameRepository(db_connection)
lineup_repository = LineupRepository(db_connection)
fantasynerds_client = FantasyNerdsClient(config.FANTASYNERDS_API_KEY or "")
odds_api_client = OddsAPIClient(config.THE_ODDS_API_KEY or "")
schedule_service = ScheduleService(game_repository)
lineup_service = LineupService(fantasynerds_client, lineup_repository, game_repository)
odds_service = OddsService(odds_api_client, lineup_repository, game_repository)
schedule_controller = ScheduleController(schedule_service)
lineup_controller = LineupController(lineup_service, odds_service)
odds_controller = OddsController(odds_service)


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

