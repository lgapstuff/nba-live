"""
Service for managing player game logs from NBA API.
Pre-loads game logs to avoid real-time API calls.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.domain.ports.nba_api_port import NBAPort
from app.infrastructure.repositories.game_log_repository import GameLogRepository

logger = logging.getLogger(__name__)


class GameLogService:
    """
    Service for loading and managing player game logs.
    Pre-loads game logs from NBA API and stores them locally.
    """
    
    def __init__(self, nba_api: NBAPort, game_log_repository: GameLogRepository):
        """
        Initialize the service.
        
        Args:
            nba_api: NBA API port for fetching game logs
            game_log_repository: Repository for game log operations
        """
        self.nba_api = nba_api
        self.game_log_repository = game_log_repository
    
    def load_game_logs_for_event(self, game_id: str, home_team_abbr: str, 
                                 away_team_abbr: str, num_games: int = 25) -> Dict[str, Any]:
        """
        Load game logs for all players from both teams in an event.
        Stores the last N games for each player in the database.
        
        Args:
            game_id: Game identifier
            home_team_abbr: Home team abbreviation
            away_team_abbr: Away team abbreviation
            num_games: Number of recent games to load per player (default: 25)
            
        Returns:
            Dictionary with loading results
        """
        try:
            logger.info(f"Loading game logs for event {game_id} (teams: {home_team_abbr} vs {away_team_abbr})")
            
            # Get rosters for both teams from NBA API
            home_players = self.nba_api.get_team_players(home_team_abbr)
            away_players = self.nba_api.get_team_players(away_team_abbr)
            
            all_players = home_players + away_players
            
            if not all_players:
                return {
                    "success": False,
                    "message": "No players found for teams",
                    "players_processed": 0,
                    "games_loaded": 0
                }
            
            logger.info(f"Found {len(all_players)} players total ({len(home_players)} home, {len(away_players)} away)")
            
            players_processed = 0
            total_games_loaded = 0
            errors = []
            
            for player in all_players:
                player_id = player.get('id')
                player_name = player.get('full_name', '')
                
                if not player_id:
                    logger.warning(f"Skipping player {player_name} - no NBA ID")
                    continue
                
                try:
                    # Get last N games from NBA API with timeout protection
                    logger.info(f"Loading last {num_games} games for {player_name} (ID: {player_id})")
                    
                    import threading
                    import queue
                    
                    result_queue = queue.Queue()
                    exception_queue = queue.Queue()
                    
                    def fetch_games():
                        try:
                            games = self.nba_api.get_player_last_n_games(player_id, n=num_games)
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
                        error_msg = f"Timeout loading game logs for {player_name} (ID: {player_id}) - 20s timeout exceeded"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    # Thread finished, check results
                    if not exception_queue.empty():
                        error = exception_queue.get_nowait()
                        error_msg = f"Error loading game logs for {player_name} (ID: {player_id}): {error}"
                        error_str = str(error).lower()
                        if 'timeout' in error_str or 'timed out' in error_str:
                            logger.warning(error_msg)
                        else:
                            logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    if not result_queue.empty():
                        games = result_queue.get_nowait()
                        
                        if not games:
                            logger.warning(f"No games found for {player_name} (ID: {player_id})")
                            continue
                        
                        # Save games to database
                        saved_count = self.game_log_repository.save_player_game_logs(
                            player_id=player_id,
                            player_name=player_name,
                            games=games
                        )
                        
                        total_games_loaded += saved_count
                        players_processed += 1
                        logger.info(f"Saved {saved_count} games for {player_name}")
                    else:
                        logger.warning(f"No result received for {player_name} (ID: {player_id})")
                        errors.append(f"No result received for {player_name} (ID: {player_id})")
                    
                except Exception as e:
                    error_msg = f"Error loading game logs for {player_name} (ID: {player_id}): {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            result = {
                "success": True,
                "message": f"Successfully loaded game logs for {players_processed} players",
                "game_id": game_id,
                "players_processed": players_processed,
                "total_players": len(all_players),
                "games_loaded": total_games_loaded
            }
            
            if errors:
                result["errors"] = errors
                result["error_count"] = len(errors)
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading game logs for event {game_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to load game logs: {e}"
            }
    
    def get_player_game_logs(self, player_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get game logs for a player from local database.
        
        Args:
            player_id: NBA player ID
            limit: Maximum number of games to return (default: all)
            
        Returns:
            List of game log dictionaries, ordered by most recent first
        """
        return self.game_log_repository.get_player_game_logs(player_id, limit)
    
    def calculate_over_under_from_local(self, player_id: int, points_line: float, 
                                       num_games: int = 10,
                                       assists_line: Optional[float] = None,
                                       rebounds_line: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate OVER/UNDER history using local game logs (no API call).
        
        Args:
            player_id: NBA player ID
            points_line: Points line from odds
            num_games: Number of recent games to analyze (default: 10)
            assists_line: Assists line from odds (optional)
            rebounds_line: Rebounds line from odds (optional)
            
        Returns:
            Dictionary with OVER/UNDER statistics for points, assists, and rebounds
        """
        try:
            # Get last N games from local database
            games = self.game_log_repository.get_player_game_logs(player_id, limit=num_games)
            
            if not games:
                logger.warning(f"No game logs found locally for player {player_id}")
                return {
                    'over_count': 0,
                    'under_count': 0,
                    'total_games': 0,
                    'over_percentage': 0.0,
                    'under_percentage': 0.0,
                    'games': [],
                    'source': 'local_db'
                }
            
            over_count = 0
            under_count = 0
            assists_over_count = 0
            assists_under_count = 0
            rebounds_over_count = 0
            rebounds_under_count = 0
            games_with_result = []
            
            for game in games:
                points = game.get('points')
                assists = game.get('assists')
                rebounds = game.get('rebounds')
                
                if points is not None:
                    points_float = float(points) if isinstance(points, (int, float, str)) else None
                    
                    if points_float is not None:
                        if points_float > points_line:
                            over_count += 1
                            result = 'OVER'
                        elif points_float < points_line:
                            under_count += 1
                            result = 'UNDER'
                        else:
                            result = 'PUSH'
                        
                        games_with_result.append({
                            'game_date': str(game.get('game_date', '')),
                            'points': points_float,
                            'result': result,
                            'opponent': game.get('matchup', '')
                        })
                
                # Calculate assists OVER/UNDER if assists_line is provided
                if assists_line is not None and assists is not None:
                    assists_float = float(assists) if isinstance(assists, (int, float, str)) else None
                    if assists_float is not None:
                        if assists_float > assists_line:
                            assists_over_count += 1
                        elif assists_float < assists_line:
                            assists_under_count += 1
                
                # Calculate rebounds OVER/UNDER if rebounds_line is provided
                if rebounds_line is not None and rebounds is not None:
                    rebounds_float = float(rebounds) if isinstance(rebounds, (int, float, str)) else None
                    if rebounds_float is not None:
                        if rebounds_float > rebounds_line:
                            rebounds_over_count += 1
                        elif rebounds_float < rebounds_line:
                            rebounds_under_count += 1
            
            total_games = len(games_with_result)
            over_percentage = (over_count / total_games * 100) if total_games > 0 else 0.0
            under_percentage = (under_count / total_games * 100) if total_games > 0 else 0.0
            
            result = {
                'over_count': over_count,
                'under_count': under_count,
                'total_games': total_games,
                'over_percentage': round(over_percentage, 1),
                'under_percentage': round(under_percentage, 1),
                'games': games_with_result,
                'source': 'local_db'
            }
            
            # Add assists OVER/UNDER counts if assists_line was provided
            if assists_line is not None:
                result['assists_over_count'] = assists_over_count
                result['assists_under_count'] = assists_under_count
            
            # Add rebounds OVER/UNDER counts if rebounds_line was provided
            if rebounds_line is not None:
                result['rebounds_over_count'] = rebounds_over_count
                result['rebounds_under_count'] = rebounds_under_count
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating OVER/UNDER from local DB for player {player_id}: {e}", exc_info=True)
            return {
                'over_count': 0,
                'under_count': 0,
                'total_games': 0,
                'over_percentage': 0.0,
                'under_percentage': 0.0,
                'games': [],
                'error': str(e),
                'source': 'local_db'
            }


