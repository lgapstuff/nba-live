"""
Game log controller for NBA game log endpoints.
"""
import logging
from datetime import datetime
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
    
    def load_player_game_logs(self, player_id: int, player_name: str = None, num_games: int = 25) -> Tuple[Dict[str, Any], int]:
        """
        Load game logs for a specific player from NBA API and save to database.
        
        Args:
            player_id: NBA player ID
            player_name: Player name (optional, used for logging)
            num_games: Number of recent games to load (default: 25)
            
        Returns:
            JSON response with loading results and status code
        """
        try:
            logger.info(f"Loading game logs for player {player_id} ({player_name or 'Unknown'})")

            # Check latest saved game log date to avoid unnecessary API calls
            latest_date = self.game_log_service.game_log_repository.get_latest_game_date(player_id)
            today = datetime.now().date()
            if latest_date and latest_date == today:
                return jsonify({
                    "success": True,
                    "player_id": player_id,
                    "player_name": player_name,
                    "games_loaded": 0,
                    "total_games": 0,
                    "already_up_to_date": True,
                    "latest_game_date": str(latest_date)
                }), 200
            
            # Load from NBA API with timeout protection
            import threading
            import queue
            
            result_queue = queue.Queue()
            exception_queue = queue.Queue()
            
            def fetch_games():
                try:
                    games = self.game_log_service.nba_api.get_player_last_n_games(player_id, n=num_games)
                    result_queue.put(games)
                except Exception as e:
                    exception_queue.put(e)
            
            # Start the fetch in a separate thread
            fetch_thread = threading.Thread(target=fetch_games, daemon=True)
            fetch_thread.start()
            
            # Wait for result with timeout (20 seconds)
            fetch_thread.join(timeout=20.0)
            
            if fetch_thread.is_alive():
                # Thread is still running, timeout occurred
                logger.warning(f"Timeout loading game logs from NBA API for player {player_id} (20s timeout)")
                return jsonify({
                    "success": False,
                    "message": f"Timeout loading game logs for player {player_id}",
                    "player_id": player_id,
                    "games_loaded": 0
                }), 408
            
            # Thread finished, check results
            if not exception_queue.empty():
                error = exception_queue.get_nowait()
                error_msg = str(error).lower()
                if 'timeout' in error_msg or 'timed out' in error_msg:
                    logger.warning(f"Timeout loading game logs from NBA API for player {player_id}: {error}")
                    return jsonify({
                        "success": False,
                        "message": f"Timeout loading game logs for player {player_id}",
                        "player_id": player_id,
                        "games_loaded": 0
                    }), 408
                else:
                    logger.error(f"Error loading game logs from NBA API for player {player_id}: {error}")
                    return jsonify({
                        "success": False,
                        "message": f"Error loading game logs: {error}",
                        "player_id": player_id,
                        "games_loaded": 0
                    }), 500
            
            if not result_queue.empty():
                games = result_queue.get_nowait()
                
                if games:
                    # Save to database
                    saved_count = self.game_log_service.game_log_repository.save_player_game_logs(
                        player_id=player_id,
                        player_name=player_name or f"Player_{player_id}",
                        games=games
                    )
                    logger.info(f"Loaded and saved {saved_count} game logs for player {player_id} from NBA API")
                    
                    return jsonify({
                        "success": True,
                        "player_id": player_id,
                        "player_name": player_name,
                        "games_loaded": saved_count,
                        "total_games": len(games),
                        "already_up_to_date": False
                    }), 200
                else:
                    logger.warning(f"No games found in NBA API for player {player_id}")
                    return jsonify({
                        "success": False,
                        "message": f"No games found for player {player_id}",
                        "player_id": player_id,
                        "games_loaded": 0
                    }), 404
            else:
                return jsonify({
                    "success": False,
                    "message": f"No result received for player {player_id}",
                    "player_id": player_id,
                    "games_loaded": 0
                }), 500
            
        except Exception as e:
            logger.error(f"Error in load_player_game_logs: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}",
                "player_id": player_id
            }), 500
    
    def get_player_game_logs(self, player_id: int, player_name: str = None) -> Tuple[Dict[str, Any], int]:
        """
        Get game logs for a specific player from database only.
        Does NOT load from NBA API (use POST /players/<player_id>/game-logs/load to pre-load).
        
        Args:
            player_id: NBA player ID
            player_name: Player name (optional, used for logging)
            
        Returns:
            JSON response with game logs and status code
        """
        try:
            # Only get game logs from database - no lazy loading
            # Game logs should be pre-loaded using POST /players/<player_id>/game-logs/load
            game_logs = self.game_log_service.get_player_game_logs(player_id, limit=25)
            
            logger.debug(f"Retrieved {len(game_logs)} game logs from DB for player {player_id}")
            
            return jsonify({
                "success": True,
                "player_id": player_id,
                "game_logs": game_logs,
                "total_games": len(game_logs),
                "loaded_from_db": True
            }), 200
            
        except Exception as e:
            logger.error(f"Error in get_player_game_logs: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500
    
    def get_live_player_stats(self, game_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Get live statistics for selected players in a game.
        
        Args:
            game_id: Game identifier from our database
            
        Returns:
            JSON response with live stats for selected players
        """
        try:
            # Get player IDs from request body
            data = request.get_json() or {}
            player_ids = data.get('player_ids', [])
            
            if not player_ids:
                return jsonify({
                    "success": False,
                    "message": "No player IDs provided"
                }), 400
            
            # Get game info to find NBA GameID
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
            game_date = game.get('game_date', '')
            
            logger.info(f"[LIVE STATS] Looking for NBA GameID: {away_team} @ {home_team} on {game_date}")
            
            # Find NBA GameID
            nba_game_id = self.game_log_service.nba_api.find_nba_game_id(
                home_team_abbr=home_team,
                away_team_abbr=away_team,
                game_date=game_date
            )
            
            if not nba_game_id:
                # Provide more helpful error message
                error_msg = (
                    f"Could not find NBA GameID for game {game_id} "
                    f"({away_team} @ {home_team} on {game_date}). "
                    f"The game may have already ended, not started yet, or the teams/date may not match."
                )
                logger.warning(f"[LIVE STATS] {error_msg}")
                return jsonify({
                    "success": False,
                    "message": error_msg,
                    "game_id": game_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "game_date": game_date
                }), 404
            
            # Get live boxscore
            live_stats = self.game_log_service.nba_api.get_live_boxscore(
                game_id=nba_game_id,
                player_ids=player_ids
            )
            
            if not live_stats:
                return jsonify({
                    "success": False,
                    "message": f"No live stats available for game {game_id}",
                    "nba_game_id": nba_game_id
                }), 404
            
            return jsonify({
                "success": True,
                "game_id": game_id,
                "nba_game_id": nba_game_id,
                "player_stats": live_stats,
                "players_found": len(live_stats)
            }), 200
            
        except Exception as e:
            logger.error(f"Error in get_live_player_stats: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }), 500

