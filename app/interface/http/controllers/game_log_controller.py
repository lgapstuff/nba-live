"""
Game log controller for NBA game log endpoints.
"""
import logging
from flask import jsonify, request
from typing import Dict, Any, Tuple

from app.application.services.game_log_service import GameLogService

logger = logging.getLogger(__name__)


class GameLogController:
    """Controller for game log endpoints."""
    
    def __init__(self, game_log_service: GameLogService):
        """
        Initialize the controller.
        
        Args:
            game_log_service: Game log service instance
        """
        self.game_log_service = game_log_service
    
    def load_game_logs_for_event(self, game_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Load game logs for all players in an event.
        
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
            
            result = self.game_log_service.load_game_logs_for_event(
                game_id=game_id,
                home_team_abbr=home_team,
                away_team_abbr=away_team,
                num_games=25
            )
            
            status_code = 200 if result.get('success', False) else 400
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Error in load_game_logs_for_event: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500
    
    def get_player_game_logs(self, player_id: int, player_name: str = None) -> Tuple[Dict[str, Any], int]:
        """
        Get game logs for a specific player.
        If not in database, loads from NBA API and saves them (lazy loading).
        
        Args:
            player_id: NBA player ID
            player_name: Player name (optional, used for logging)
            
        Returns:
            JSON response with game logs and status code
        """
        try:
            # First, check if we have game logs in database
            game_logs = self.game_log_service.get_player_game_logs(player_id, limit=25)
            
            # If we have less than 10 games, try to load from NBA API
            if len(game_logs) < 10:
                logger.info(f"Only {len(game_logs)} game logs found in DB for player {player_id}. Loading from NBA API...")
                
                # Load from NBA API and save to database
                try:
                    games = self.game_log_service.nba_api.get_player_last_n_games(player_id, n=25)
                    
                    if games:
                        # Save to database
                        saved_count = self.game_log_service.game_log_repository.save_player_game_logs(
                            player_id=player_id,
                            player_name=player_name or f"Player_{player_id}",
                            games=games
                        )
                        logger.info(f"Loaded and saved {saved_count} game logs for player {player_id} from NBA API")
                        
                        # Get updated game logs from database
                        game_logs = self.game_log_service.get_player_game_logs(player_id, limit=25)
                    else:
                        logger.warning(f"No games found in NBA API for player {player_id}")
                except Exception as e:
                    logger.error(f"Error loading game logs from NBA API for player {player_id}: {e}")
                    # Continue with whatever we have in DB
            
            return jsonify({
                "success": True,
                "player_id": player_id,
                "game_logs": game_logs,
                "total_games": len(game_logs),
                "loaded_from_db": len(game_logs) > 0
            }), 200
            
        except Exception as e:
            logger.error(f"Error in get_player_game_logs: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500

