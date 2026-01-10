"""
Schedule service for managing NBA game schedules.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.infrastructure.repositories.game_repository import GameRepository
from app.domain.value_objects.team_names import get_team_name, get_team_logo_url

logger = logging.getLogger(__name__)


class ScheduleService:
    """
    Service for managing NBA schedule operations.
    """
    
    def __init__(self, game_repository: GameRepository):
        """
        Initialize the service.
        
        Args:
            game_repository: Repository for game operations
        """
        self.game_repository = game_repository
    
    def import_schedule_from_json(self, json_path: str) -> Dict[str, Any]:
        """
        Import schedule from a JSON file.
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            Dictionary with import results
        """
        try:
            file_path = Path(json_path)
            if not file_path.exists():
                raise FileNotFoundError(f"JSON file not found: {json_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Normalize the data structure
            games_data = self._normalize_schedule_data(data)
            
            # Save to database
            saved_count = self.game_repository.save_batch(games_data)
            
            return {
                "success": True,
                "total_games": len(games_data),
                "saved_games": saved_count,
                "message": f"Successfully imported {saved_count} games"
            }
            
        except Exception as e:
            logger.error(f"Error importing schedule: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import schedule: {e}"
            }
    
    def import_schedule_from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import schedule from a dictionary (useful for API uploads).
        
        Args:
            data: Dictionary containing schedule data
            
        Returns:
            Dictionary with import results
        """
        try:
            games_data = self._normalize_schedule_data(data)
            saved_count = self.game_repository.save_batch(games_data)
            
            return {
                "success": True,
                "total_games": len(games_data),
                "saved_games": saved_count,
                "message": f"Successfully imported {saved_count} games"
            }
            
        except Exception as e:
            logger.error(f"Error importing schedule: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import schedule: {e}"
            }
    
    def get_games_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Get games for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of game dictionaries
        """
        return self.game_repository.get_games_by_date(date)
    
    def _normalize_schedule_data(self, data: Any) -> List[Dict[str, Any]]:
        """
        Normalize schedule data from various JSON formats.
        
        Args:
            data: Raw data from JSON (could be list, dict, etc.)
            
        Returns:
            List of normalized game dictionaries
        """
        games = []
        season = None  # Extract season from top level if present
        
        # Handle different JSON structures
        if isinstance(data, list):
            # If it's a list of games
            games_list = data
        elif isinstance(data, dict):
            # Extract season from top level if present
            season = data.get('season')
            
            # If it's a dict with a 'games' key or similar
            if 'games' in data:
                games_list = data['games']
            elif 'schedule' in data:
                games_list = data['schedule']
            else:
                # Try to extract games from dict values
                games_list = list(data.values()) if data else []
        else:
            raise ValueError(f"Unexpected data format: {type(data)}")
        
        for game in games_list:
            try:
                normalized = self._normalize_game(game, season=season)
                if normalized:
                    games.append(normalized)
            except Exception as e:
                logger.warning(f"Error normalizing game: {e}")
                continue
        
        return games
    
    def _normalize_game(self, game: Dict[str, Any], season: Any = None) -> Optional[Dict[str, Any]]:
        """
        Normalize a single game dictionary.
        
        Args:
            game: Raw game dictionary
            season: Season from top level (optional)
            
        Returns:
            Normalized game dictionary or None if invalid
        """
        # Extract common field names (handle different API formats)
        game_id = (
            game.get('gameId') or 
            game.get('game_id') or 
            game.get('id') or
            game.get('GameID')
        )
        
        if not game_id:
            return None
        
        # Extract teams (handle different formats)
        home_team = (
            game.get('homeTeam') or 
            game.get('home_team') or 
            game.get('HOME_TEAM') or
            game.get('hTeam', {}).get('abbreviation') or
            game.get('home', {}).get('abbreviation')
        )
        
        away_team = (
            game.get('awayTeam') or 
            game.get('away_team') or 
            game.get('AWAY_TEAM') or
            game.get('vTeam', {}).get('abbreviation') or
            game.get('away', {}).get('abbreviation')
        )
        
        # Extract date and time - handle format "YYYY-MM-DD HH:MM:SS"
        game_date_time = (
            game.get('gameDate') or 
            game.get('game_date') or 
            game.get('date') or
            game.get('GAME_DATE')
        )
        
        # Separate date and time if they're together
        game_date = None
        game_time = None
        
        if game_date_time:
            # Try to parse "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD HH:MM:SS.microseconds"
            if ' ' in str(game_date_time):
                parts = str(game_date_time).split(' ')
                game_date = parts[0]  # YYYY-MM-DD
                if len(parts) > 1:
                    time_part = parts[1]
                    # Remove microseconds if present
                    if '.' in time_part:
                        time_part = time_part.split('.')[0]
                    game_time = time_part  # HH:MM:SS
            else:
                # Assume it's just a date
                game_date = str(game_date_time)
        
        # If date/time weren't extracted from game_date_time, try separate fields
        if not game_date:
            game_date = (
                game.get('gameDate') or 
                game.get('game_date') or 
                game.get('date') or
                game.get('GAME_DATE')
            )
        
        if not game_time:
            game_time = (
                game.get('gameTime') or 
                game.get('game_time') or 
                game.get('time') or
                game.get('GAME_TIME')
            )
        
        # Extract status - default to 'Scheduled' if winner is empty, 'Finished' if winner exists
        winner = game.get('winner', '')
        if winner:
            status = 'Finished'
        else:
            status = (
                game.get('status') or 
                game.get('gameStatus') or 
                game.get('STATUS') or
                'Scheduled'
            )
        
        # Extract season info - use passed season or from game
        game_season = season or game.get('season') or game.get('seasonId') or None
        season_type = game.get('seasonType') or game.get('season_type') or None
        
        # Extract team names - try from JSON first, then use mapping from abbreviations
        home_team_name = (
            game.get('homeTeamName') or 
            game.get('home_team_name') or
            game.get('hTeam', {}).get('fullName') or
            game.get('home', {}).get('name')
        )
        
        away_team_name = (
            game.get('awayTeamName') or 
            game.get('away_team_name') or
            game.get('vTeam', {}).get('fullName') or
            game.get('away', {}).get('name')
        )
        
        # If team names are not in JSON, get them from abbreviation mapping
        if not home_team_name and home_team:
            home_team_name = get_team_name(home_team)
        
        if not away_team_name and away_team:
            away_team_name = get_team_name(away_team)
        
        # Get team logo URLs from abbreviation mapping
        home_team_logo_url = (
            game.get('home_team_logo_url') or 
            game.get('homeTeamLogoUrl') or
            game.get('hTeam', {}).get('logoUrl')
        )
        if not home_team_logo_url and home_team:
            home_team_logo_url = get_team_logo_url(home_team)
        
        away_team_logo_url = (
            game.get('away_team_logo_url') or 
            game.get('awayTeamLogoUrl') or
            game.get('vTeam', {}).get('logoUrl')
        )
        if not away_team_logo_url and away_team:
            away_team_logo_url = get_team_logo_url(away_team)
        
        return {
            'game_id': str(game_id),
            'home_team': str(home_team) if home_team else '',
            'away_team': str(away_team) if away_team else '',
            'game_date': game_date,
            'game_time': game_time,
            'status': str(status),
            'season': str(game_season) if game_season else None,
            'season_type': str(season_type) if season_type else None,
            'home_team_name': str(home_team_name) if home_team_name else None,
            'away_team_name': str(away_team_name) if away_team_name else None,
            'home_team_logo_url': str(home_team_logo_url) if home_team_logo_url else None,
            'away_team_logo_url': str(away_team_logo_url) if away_team_logo_url else None,
        }

