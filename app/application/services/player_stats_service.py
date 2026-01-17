"""
Service for calculating player statistics and OVER/UNDER history.
Uses local game logs when available, falls back to NBA API.
"""
import logging
from typing import Dict, Any, Optional, List

from app.domain.ports.nba_api_port import NBAPort

logger = logging.getLogger(__name__)


class PlayerStatsService:
    """
    Service for calculating player statistics based on game logs.
    Prefers local database over real-time API calls.
    """
    
    def __init__(self, nba_port: NBAPort, game_log_service=None):
        """
        Initialize the service.
        
        Args:
            nba_port: Port for NBA API integration
            game_log_service: GameLogService for local game logs (optional)
        """
        self.nba_api = nba_port
        self.game_log_service = game_log_service
    
    def calculate_over_under_history(self, player_id: int, points_line: float, 
                                    num_games: int = 15, player_name: Optional[str] = None,
                                    use_local_only: bool = False,
                                    assists_line: Optional[float] = None,
                                    rebounds_line: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate OVER/UNDER history for a player based on their last N games.
        
        Args:
            player_id: Player ID (may be FantasyNerds ID, will try to find NBA ID if needed)
            points_line: Points line from odds (e.g., 22.5)
            num_games: Number of recent games to analyze (default: 15)
            player_name: Player name (optional, used to find NBA player ID if player_id doesn't work)
            use_local_only: If True, only use local game logs (no NBA API calls)
            
        Returns:
            Dictionary with:
            - over_count: Number of games where player scored OVER the line
            - under_count: Number of games where player scored UNDER the line
            - total_games: Total number of games analyzed
            - over_percentage: Percentage of games that were OVER
            - under_percentage: Percentage of games that were UNDER
            - games: List of last N games with their points and OVER/UNDER result
        """
        try:
            # Log what we're trying
            logger.info(f"[OVER/UNDER] Calculating history for player_id={player_id}, player_name={player_name}, points_line={points_line}, use_local_only={use_local_only}")
            
            # Try to use local game logs first (optimization)
            if self.game_log_service:
                try:
                    # If we have player_name, try to find NBA player ID first for local lookup
                    # But skip this in local-only mode to avoid unnecessary API calls
                    nba_player_id = None
                    if player_name and not use_local_only:
                        # Only try to find NBA ID if we're not in local-only mode
                        logger.debug(f"[OVER/UNDER] Searching for NBA official ID by name: {player_name}")
                        nba_player_id = self.nba_api.find_nba_player_id_by_name(player_name)
                        if nba_player_id:
                            logger.debug(f"[OVER/UNDER] Found NBA player ID {nba_player_id} for {player_name}")
                    elif player_name and use_local_only:
                        # In local-only mode, don't search for NBA ID to avoid API calls
                        logger.debug(f"[OVER/UNDER] Local-only mode: skipping NBA ID search for {player_name}")
                    
                    # Try with NBA player ID first if found, otherwise use provided player_id
                    target_player_id = nba_player_id if nba_player_id else player_id
                    
                    logger.debug(f"[OVER/UNDER] Attempting to use local game logs for player {target_player_id}")
                    result = self.game_log_service.calculate_over_under_from_local(
                        target_player_id, points_line, num_games, assists_line, rebounds_line
                    )
                    if result.get('total_games', 0) > 0:
                        logger.info(f"[OVER/UNDER] Using local game logs: {result.get('over_count')} OVER, {result.get('under_count')} UNDER")
                        return result
                    else:
                        # If local-only mode, return empty result
                        if use_local_only:
                            logger.debug(f"[OVER/UNDER] No local game logs found for player {target_player_id} (local-only mode)")
                            return {
                                'over_count': 0,
                                'under_count': 0,
                                'total_games': 0,
                                'over_percentage': 0.0,
                                'under_percentage': 0.0,
                                'games': [],
                                'source': 'local_db'
                            }
                        logger.debug(f"[OVER/UNDER] No local game logs found, falling back to NBA API")
                except Exception as e:
                    logger.warning(f"[OVER/UNDER] Error using local game logs: {e}")
                    if use_local_only:
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
            
            # If use_local_only is True, don't fallback to NBA API
            if use_local_only:
                logger.debug(f"[OVER/UNDER] Local-only mode: skipping NBA API fallback")
                return {
                    'over_count': 0,
                    'under_count': 0,
                    'total_games': 0,
                    'over_percentage': 0.0,
                    'under_percentage': 0.0,
                    'games': [],
                    'source': 'local_db'
                }
            
            # Fallback to NBA API (only if not in local-only mode)
            # If we have player_name, try to find NBA player ID first
            nba_player_id = None
            if player_name:
                logger.debug(f"[OVER/UNDER] Player ID {player_id} is from FantasyNerds, searching for NBA official ID by name: {player_name}")
                nba_player_id = self.nba_api.find_nba_player_id_by_name(player_name)
                
                if nba_player_id:
                    logger.info(f"[OVER/UNDER] Found NBA player ID {nba_player_id} for {player_name} (FantasyNerds ID was {player_id})")
                else:
                    logger.warning(f"[OVER/UNDER] Could not find NBA player ID for {player_name}, will try with FantasyNerds ID {player_id}")
            
            # Try with NBA player ID first if found, otherwise use provided player_id
            target_player_id = nba_player_id if nba_player_id else player_id
            logger.info(f"[OVER/UNDER] Using player_id {target_player_id} to fetch games from NBA API")
            
            games = self.nba_api.get_player_last_n_games(target_player_id, n=num_games)
            
            # If still no games found and we haven't tried the other ID, try it
            if not games:
                if nba_player_id and target_player_id == player_id:
                    # We tried FantasyNerds ID, now try NBA ID
                    logger.info(f"[OVER/UNDER] No games found with FantasyNerds ID {player_id}, trying NBA ID {nba_player_id}")
                    games = self.nba_api.get_player_last_n_games(nba_player_id, n=num_games)
                elif not nba_player_id and player_name:
                    # We tried FantasyNerds ID, now try to find NBA ID by name
                    logger.info(f"[OVER/UNDER] No games found with player_id {player_id}, trying to find NBA player ID by name: {player_name}")
                    nba_player_id = self.nba_api.find_nba_player_id_by_name(player_name)
                    
                    if nba_player_id and nba_player_id != player_id:
                        logger.info(f"[OVER/UNDER] Found NBA player ID {nba_player_id} for {player_name}, trying again...")
                        games = self.nba_api.get_player_last_n_games(nba_player_id, n=num_games)
            
            if not games:
                logger.warning(f"No games found for player {player_id}")
                return {
                    'over_count': 0,
                    'under_count': 0,
                    'total_games': 0,
                    'over_percentage': 0.0,
                    'under_percentage': 0.0,
                    'games': [],
                    'source': 'nba_api'
                }
            
            over_count = 0
            under_count = 0
            assists_over_count = 0
            assists_under_count = 0
            rebounds_over_count = 0
            rebounds_under_count = 0
            games_with_result = []
            
            for game in games:
                # Get points scored in this game
                # The column name in nba_api is usually 'PTS' or 'pts'
                points = None
                if 'PTS' in game:
                    points = float(game['PTS']) if game['PTS'] is not None else None
                elif 'pts' in game:
                    points = float(game['pts']) if game['pts'] is not None else None
                elif 'POINTS' in game:
                    points = float(game['POINTS']) if game['POINTS'] is not None else None
                
                # Get assists
                assists = None
                if 'AST' in game:
                    assists = float(game['AST']) if game['AST'] is not None else None
                elif 'ast' in game:
                    assists = float(game['ast']) if game['ast'] is not None else None
                elif 'ASSISTS' in game:
                    assists = float(game['ASSISTS']) if game['ASSISTS'] is not None else None
                
                # Get rebounds
                rebounds = None
                if 'REB' in game:
                    rebounds = float(game['REB']) if game['REB'] is not None else None
                elif 'reb' in game:
                    rebounds = float(game['reb']) if game['reb'] is not None else None
                elif 'REBOUNDS' in game:
                    rebounds = float(game['REBOUNDS']) if game['REBOUNDS'] is not None else None
                
                if points is not None:
                    # Determine if OVER or UNDER
                    if points > points_line:
                        over_count += 1
                        result = 'OVER'
                    elif points < points_line:
                        under_count += 1
                        result = 'UNDER'
                    else:
                        # Exactly equal to line (push) - count as neither
                        result = 'PUSH'
                    
                    games_with_result.append({
                        'game_date': game.get('GAME_DATE', game.get('game_date', '')),
                        'points': points,
                        'result': result,
                        'opponent': game.get('MATCHUP', game.get('matchup', ''))
                    })
                
                # Calculate assists OVER/UNDER if assists_line is provided
                if assists_line is not None and assists is not None:
                    if assists > assists_line:
                        assists_over_count += 1
                    elif assists < assists_line:
                        assists_under_count += 1
                
                # Calculate rebounds OVER/UNDER if rebounds_line is provided
                if rebounds_line is not None and rebounds is not None:
                    if rebounds > rebounds_line:
                        rebounds_over_count += 1
                    elif rebounds < rebounds_line:
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
                'source': 'nba_api'
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
            logger.error(f"Error calculating OVER/UNDER history for player {player_id}: {e}", exc_info=True)
            return {
                'over_count': 0,
                'under_count': 0,
                'total_games': 0,
                'over_percentage': 0.0,
                'under_percentage': 0.0,
                'games': [],
                'error': str(e),
                'source': 'error'
            }

