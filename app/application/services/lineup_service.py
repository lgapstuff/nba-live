"""
Lineup service for managing NBA lineups and associating them with games.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.domain.ports.fantasynerds_port import FantasyNerdsPort
from app.infrastructure.repositories.lineup_repository import LineupRepository
from app.infrastructure.repositories.game_repository import GameRepository

logger = logging.getLogger(__name__)


class LineupService:
    """
    Service for managing NBA lineups operations.
    """
    
    def __init__(self, 
                 fantasynerds_port: FantasyNerdsPort,
                 lineup_repository: LineupRepository,
                 game_repository: GameRepository):
        """
        Initialize the service.
        
        Args:
            fantasynerds_port: Port for FantasyNerds API integration
            lineup_repository: Repository for lineup operations
            game_repository: Repository for game operations
        """
        self.fantasynerds_port = fantasynerds_port
        self.lineup_repository = lineup_repository
        self.game_repository = game_repository
    
    def import_lineups_for_date(self, date: str) -> Dict[str, Any]:
        """
        Import lineups from FantasyNerds API for a specific date and associate with games.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with import results
        """
        try:
            # Get lineups from FantasyNerds API
            logger.info(f"Fetching lineups from FantasyNerds for date: {date}")
            lineups_data = self.fantasynerds_port.get_lineups_by_date(date)
            logger.info(f"Received lineups data: {type(lineups_data)}, keys: {list(lineups_data.keys()) if isinstance(lineups_data, dict) else 'N/A'}")
            
            if not lineups_data or 'lineups' not in lineups_data:
                return {
                    "success": False,
                    "message": f"No lineups found for date {date}",
                    "games_processed": 0,
                    "lineups_saved": 0
                }
            
            lineup_date = lineups_data.get('lineup_date', date)
            lineups = lineups_data.get('lineups', {})
            
            # Get all games for this date from our database
            games = self.game_repository.get_games_by_date(date)
            
            # If no games found for the exact date, try to find games by matching teams
            # This handles cases where lineups are published for a date but games might be on a different date
            if not games and lineups:
                logger.info(f"No games found for date {date}, searching for games by team match...")
                # Get all teams that have lineups
                teams_with_lineups = set(lineups.keys())
                
                # Try to find games that include these teams (check date +/- 1 day)
                from datetime import datetime, timedelta
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    # Check previous day, current day, and next day
                    for day_offset in [-1, 0, 1]:
                        check_date = (date_obj + timedelta(days=day_offset)).strftime('%Y-%m-%d')
                        potential_games = self.game_repository.get_games_by_date(check_date)
                        # Filter games that have teams matching our lineups
                        for game in potential_games:
                            if game['home_team'] in teams_with_lineups or game['away_team'] in teams_with_lineups:
                                games.append(game)
                                logger.info(f"Found matching game {game['game_id']} on {check_date} for lineup date {date}")
                except Exception as e:
                    logger.warning(f"Error searching for games by date range: {e}")
            
            if not games:
                return {
                    "success": False,
                    "message": f"No games found in schedule for date {date} or nearby dates",
                    "games_processed": 0,
                    "lineups_saved": 0
                }
            
            games_processed = 0
            total_lineups_saved = 0
            
            # Associate lineups with games
            for game in games:
                game_id = game['game_id']
                home_team = game['home_team']
                away_team = game['away_team']
                
                # Find lineups for both teams
                team_lineups = {}
                
                if home_team in lineups:
                    team_lineups[home_team] = lineups[home_team]
                
                if away_team in lineups:
                    team_lineups[away_team] = lineups[away_team]
                
                if team_lineups:
                    # Save lineups for this game
                    saved_count = self.lineup_repository.save_lineups_for_game(
                        game_id=game_id,
                        lineup_date=lineup_date,
                        team_lineups=team_lineups
                    )
                    total_lineups_saved += saved_count
                    games_processed += 1
                    logger.info(f"Saved {saved_count} lineup entries for game {game_id} (game_date: {game.get('game_date')}, lineup_date: {lineup_date})")
            
            return {
                "success": True,
                "message": f"Successfully imported lineups for {games_processed} games",
                "games_processed": games_processed,
                "lineups_saved": total_lineups_saved,
                "lineup_date": lineup_date
            }
            
        except Exception as e:
            logger.error(f"Error importing lineups: {e}", exc_info=True)
            error_message = str(e)
            # Provide more user-friendly error messages
            if "Empty response" in error_message or "Invalid JSON" in error_message:
                error_message = f"No se pudieron obtener los lineups de FantasyNerds para la fecha {date}. Verifica que la fecha sea correcta y que haya juegos programados."
            elif "404" in error_message or "Not Found" in error_message:
                error_message = f"No se encontraron lineups para la fecha {date}."
            elif "401" in error_message or "403" in error_message or "Unauthorized" in error_message:
                error_message = "Error de autenticación con la API de FantasyNerds. Verifica la configuración de la API key."
            elif "timeout" in error_message.lower():
                error_message = "La solicitud a FantasyNerds tardó demasiado. Intenta nuevamente."
            
            return {
                "success": False,
                "error": str(e),
                "message": error_message
            }
    
    def import_lineups_from_dict(self, lineups_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import lineups from a dictionary (useful for API uploads or testing).
        
        Args:
            lineups_data: Dictionary containing lineup data with structure:
                         {
                             "lineup_date": "2026-01-09",
                             "lineups": {
                                 "LAL": {"PG": {...}, "SG": {...}, ...},
                                 ...
                             }
                         }
            
        Returns:
            Dictionary with import results
        """
        try:
            lineup_date = lineups_data.get('lineup_date')
            if not lineup_date:
                return {
                    "success": False,
                    "message": "lineup_date is required in the data"
                }
            
            # Convert date format if needed
            if len(lineup_date) == 8:  # YYYYMMDD
                lineup_date = f"{lineup_date[:4]}-{lineup_date[4:6]}-{lineup_date[6:8]}"
            
            lineups = lineups_data.get('lineups', {})
            
            if not lineups:
                return {
                    "success": False,
                    "message": "No lineups found in data"
                }
            
            # Get all games for this date from our database
            games = self.game_repository.get_games_by_date(lineup_date)
            
            if not games:
                return {
                    "success": False,
                    "message": f"No games found in schedule for date {lineup_date}",
                    "games_processed": 0,
                    "lineups_saved": 0
                }
            
            games_processed = 0
            total_lineups_saved = 0
            
            # Associate lineups with games
            for game in games:
                game_id = game['game_id']
                home_team = game['home_team']
                away_team = game['away_team']
                
                # Find lineups for both teams
                team_lineups = {}
                
                if home_team in lineups:
                    team_lineups[home_team] = lineups[home_team]
                
                if away_team in lineups:
                    team_lineups[away_team] = lineups[away_team]
                
                if team_lineups:
                    # Save lineups for this game
                    saved_count = self.lineup_repository.save_lineups_for_game(
                        game_id=game_id,
                        lineup_date=lineup_date,
                        team_lineups=team_lineups
                    )
                    total_lineups_saved += saved_count
                    games_processed += 1
            
            return {
                "success": True,
                "message": f"Successfully imported lineups for {games_processed} games",
                "games_processed": games_processed,
                "lineups_saved": total_lineups_saved,
                "lineup_date": lineup_date
            }
            
        except Exception as e:
            logger.error(f"Error importing lineups from dict: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import lineups: {e}"
            }
    
    def get_lineups_by_date(self, date: str, auto_fetch: bool = False) -> List[Dict[str, Any]]:
        """
        Get lineups for a specific date.
        Only returns lineups that are already in the database.
        Does NOT automatically fetch from FantasyNerds or return games from schedule.
        
        Args:
            date: Date in YYYY-MM-DD format
            auto_fetch: If True, automatically fetch from FantasyNerds if not found (default: False)
            
        Returns:
            List of game dictionaries with their lineups (empty if no lineups found)
        """
        # Get lineups from database
        lineups = self.lineup_repository.get_lineups_by_date(date)
        
        # If no lineups found and auto_fetch is enabled, try to fetch from FantasyNerds
        if not lineups and auto_fetch:
            logger.info(f"No lineups found in database for {date}, fetching from FantasyNerds...")
            
            # Fetch and import lineups automatically
            import_result = self.import_lineups_for_date(date)
            
            if import_result.get('success'):
                # Now get the lineups from database
                lineups = self.lineup_repository.get_lineups_by_date(date)
                logger.info(f"Successfully fetched and saved lineups for {date}")
            else:
                logger.warning(f"Failed to fetch lineups from FantasyNerds: {import_result.get('message')}")
        
        return lineups
    
    def get_lineup_by_game_id(self, game_id: str, auto_fetch: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get lineup for a specific game.
        Automatically fetches from FantasyNerds if not in database.
        
        Args:
            game_id: Game identifier
            auto_fetch: If True, automatically fetch from FantasyNerds if not found
            
        Returns:
            Lineup dictionary or None if not found
        """
        # First, try to get from database
        lineup = self.lineup_repository.get_lineup_by_game_id(game_id)
        
        # If not found and auto_fetch is enabled, try to fetch
        if not lineup and auto_fetch:
            # Get game info to know the date
            game = self.game_repository.get_game_by_id(game_id)
            
            if game and game.get('game_date'):
                game_date = str(game['game_date'])
                logger.info(f"Lineup not found for game {game_id}, fetching lineups for date {game_date}...")
                
                # Fetch lineups for that date
                import_result = self.import_lineups_for_date(game_date)
                
                if import_result.get('success'):
                    # Now get the lineup from database
                    lineup = self.lineup_repository.get_lineup_by_game_id(game_id)
                    logger.info(f"Successfully fetched and saved lineup for game {game_id}")
        
        return lineup

