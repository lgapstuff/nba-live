"""
Game repository for MySQL operations.
"""
from typing import List, Optional, Dict, Any
import logging

from app.domain.models.game import Game
from app.domain.value_objects.game_id import GameId
from app.infrastructure.database.connection import DatabaseConnection
from app.config.settings import Config

logger = logging.getLogger(__name__)


class GameRepository:
    """
    Repository for managing game data in MySQL.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the repository.
        
        Args:
            db_connection: Database connection manager
        """
        self.db = db_connection
    
    def save_game(self, game_data: Dict[str, Any]) -> None:
        """
        Save a game to the database.
        
        Args:
            game_data: Dictionary with game information
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO games (
                        game_id, home_team, away_team, game_date, game_time,
                        status, season, season_type, home_team_name, away_team_name,
                        home_team_logo_url, away_team_logo_url
                    ) VALUES (
                        %(game_id)s, %(home_team)s, %(away_team)s, %(game_date)s, %(game_time)s,
                        %(status)s, %(season)s, %(season_type)s, %(home_team_name)s, %(away_team_name)s,
                        %(home_team_logo_url)s, %(away_team_logo_url)s
                    )
                    ON DUPLICATE KEY UPDATE
                        home_team = VALUES(home_team),
                        away_team = VALUES(away_team),
                        game_date = VALUES(game_date),
                        game_time = VALUES(game_time),
                        status = VALUES(status),
                        season = VALUES(season),
                        season_type = VALUES(season_type),
                        home_team_name = VALUES(home_team_name),
                        away_team_name = VALUES(away_team_name),
                        home_team_logo_url = VALUES(home_team_logo_url),
                        away_team_logo_url = VALUES(away_team_logo_url),
                        updated_at = CURRENT_TIMESTAMP
                """, game_data)
                conn.commit()
    
    def get_games_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Get all games for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of game dictionaries
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        game_id, home_team, away_team, game_date, game_time,
                        status, season, season_type, home_team_name, away_team_name,
                        home_team_logo_url, away_team_logo_url
                    FROM games
                    WHERE game_date = %s
                    ORDER BY game_time ASC
                """, (date,))
                return cursor.fetchall()
    
    def get_game_by_id(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a game by its ID.
        
        Args:
            game_id: Game identifier
            
        Returns:
            Game dictionary or None if not found
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        game_id, home_team, away_team, game_date, game_time,
                        status, season, season_type, home_team_name, away_team_name,
                        home_team_logo_url, away_team_logo_url
                    FROM games
                    WHERE game_id = %s
                """, (game_id,))
                return cursor.fetchone()
    
    def save_batch(self, games_data: List[Dict[str, Any]]) -> int:
        """
        Save multiple games in a batch.
        
        Args:
            games_data: List of game dictionaries
            
        Returns:
            Number of games saved
        """
        if not games_data:
            return 0
        
        saved_count = 0
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                for game_data in games_data:
                    try:
                        cursor.execute("""
                            INSERT INTO games (
                                game_id, home_team, away_team, game_date, game_time,
                                status, season, season_type, home_team_name, away_team_name,
                                home_team_logo_url, away_team_logo_url
                            ) VALUES (
                                %(game_id)s, %(home_team)s, %(away_team)s, %(game_date)s, %(game_time)s,
                                %(status)s, %(season)s, %(season_type)s, %(home_team_name)s, %(away_team_name)s,
                                %(home_team_logo_url)s, %(away_team_logo_url)s
                            )
                            ON DUPLICATE KEY UPDATE
                                home_team = VALUES(home_team),
                                away_team = VALUES(away_team),
                                game_date = VALUES(game_date),
                                game_time = VALUES(game_time),
                                status = VALUES(status),
                                season = VALUES(season),
                                season_type = VALUES(season_type),
                                home_team_name = VALUES(home_team_name),
                                away_team_name = VALUES(away_team_name),
                                home_team_logo_url = VALUES(home_team_logo_url),
                                away_team_logo_url = VALUES(away_team_logo_url),
                                updated_at = CURRENT_TIMESTAMP
                        """, game_data)
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Error saving game {game_data.get('game_id')}: {e}")
                        continue
                
                conn.commit()
                return saved_count

