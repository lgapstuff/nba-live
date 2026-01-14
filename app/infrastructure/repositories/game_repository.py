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
                        home_team_logo_url, away_team_logo_url,
                        home_score, away_score, score_last_update, game_completed
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
                        home_team_logo_url, away_team_logo_url,
                        home_score, away_score, score_last_update, game_completed
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
    
    def update_game_scores(self, game_id: str, home_score: Optional[int] = None, 
                          away_score: Optional[int] = None, completed: bool = False,
                          last_update: Optional[str] = None) -> None:
        """
        Update game scores and completion status.
        
        Args:
            game_id: Game identifier
            home_score: Home team score
            away_score: Away team score
            completed: Whether the game is completed
            last_update: Last update timestamp
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                updates = []
                params = []
                
                if home_score is not None:
                    updates.append("home_score = %s")
                    params.append(home_score)
                
                if away_score is not None:
                    updates.append("away_score = %s")
                    params.append(away_score)
                
                # Always update completed status
                updates.append("game_completed = %s")
                params.append(1 if completed else 0)
                
                if last_update:
                    # Convert ISO 8601 format (with Z) to MySQL DATETIME format
                    # MySQL doesn't accept 'Z' timezone indicator, so we need to convert it
                    try:
                        from datetime import datetime
                        # Parse ISO 8601 format (e.g., '2026-01-14T04:25:21Z')
                        if isinstance(last_update, str):
                            # Handle ISO 8601 format with 'Z' (UTC)
                            if last_update.endswith('Z'):
                                # Remove 'Z' and replace 'T' with space for MySQL DATETIME format
                                last_update_mysql = last_update[:-1].replace('T', ' ')
                            elif 'T' in last_update:
                                # Has 'T' but no 'Z', just replace 'T' with space
                                last_update_mysql = last_update.replace('T', ' ')
                            else:
                                # Already in MySQL format or different format
                                last_update_mysql = last_update
                        else:
                            last_update_mysql = last_update
                    except Exception as e:
                        logger.warning(f"Error parsing last_update datetime '{last_update}': {e}, using as-is")
                        # Try simple string replacement as fallback
                        if isinstance(last_update, str):
                            last_update_mysql = last_update.replace('Z', '').replace('T', ' ')
                        else:
                            last_update_mysql = last_update
                    
                    updates.append("score_last_update = %s")
                    params.append(last_update_mysql)
                
                if updates:
                    params.append(game_id)
                    cursor.execute(f"""
                        UPDATE games
                        SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                        WHERE game_id = %s
                    """, params)
                    conn.commit()

