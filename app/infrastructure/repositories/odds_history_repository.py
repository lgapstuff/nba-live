"""
Repository for player odds history operations.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.infrastructure.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class OddsHistoryRepository:
    """
    Repository for managing player odds history.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the repository.
        
        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
    
    def get_latest_odds(self, player_id: int, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest odds entry for a player and game.
        
        Args:
            player_id: Player ID
            game_id: Game identifier
            
        Returns:
            Latest odds entry or None
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT points_line, assists_line, rebounds_line, over_odds, under_odds
                    FROM player_odds_history
                    WHERE player_id = %s AND game_id = %s
                    ORDER BY recorded_at DESC
                    LIMIT 1
                """, (player_id, game_id))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'points_line': float(row['points_line']) if row['points_line'] else None,
                        'assists_line': float(row['assists_line']) if row['assists_line'] else None,
                        'rebounds_line': float(row['rebounds_line']) if row['rebounds_line'] else None,
                        'over_odds': row['over_odds'],
                        'under_odds': row['under_odds']
                    }
                return None
    
    def save_odds_history(self, player_id: int, player_name: str, game_id: str, 
                        game_date: str, team_abbr: str, points_line: float,
                        assists_line: Optional[float] = None,
                        rebounds_line: Optional[float] = None,
                        over_odds: Optional[int] = None, under_odds: Optional[int] = None,
                        bookmaker: Optional[str] = None) -> bool:
        """
        Save odds history entry for a player only if odds have changed.
        
        Args:
            player_id: Player ID
            player_name: Player name
            game_id: Game identifier
            game_date: Date of the game (YYYY-MM-DD)
            team_abbr: Team abbreviation
            points_line: Points line from odds
            assists_line: Assists line from odds (optional)
            rebounds_line: Rebounds line from odds (optional)
            over_odds: Over odds (optional)
            under_odds: Under odds (optional)
            bookmaker: Bookmaker name (optional)
            
        Returns:
            True if saved, False if skipped (no changes)
        """
        # Check if odds have changed
        latest_odds = self.get_latest_odds(player_id, game_id)
        
        if latest_odds:
            # Compare with latest entry
            points_changed = abs(float(latest_odds.get('points_line', 0) or 0) - float(points_line or 0)) > 0.01
            assists_changed = abs(float(latest_odds.get('assists_line', 0) or 0) - float(assists_line or 0)) > 0.01
            rebounds_changed = abs(float(latest_odds.get('rebounds_line', 0) or 0) - float(rebounds_line or 0)) > 0.01
            over_odds_changed = latest_odds.get('over_odds') != over_odds
            under_odds_changed = latest_odds.get('under_odds') != under_odds
            
            # Only save if something changed
            if not (points_changed or assists_changed or rebounds_changed or over_odds_changed or under_odds_changed):
                logger.debug(f"Odds unchanged for player {player_id} in game {game_id}, skipping save")
                return False
        
        # Save new entry
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO player_odds_history (
                        player_id, player_name, game_id, game_date, team_abbr,
                        points_line, assists_line, rebounds_line, over_odds, under_odds, bookmaker, recorded_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                """, (player_id, player_name, game_id, game_date, team_abbr,
                      points_line, assists_line, rebounds_line, over_odds, under_odds, bookmaker))
                conn.commit()
                return True
    
    def get_player_odds_history(self, player_id: int, game_id: Optional[str] = None,
                               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get odds history for a player.
        
        Args:
            player_id: Player ID
            game_id: Optional game ID to filter by
            limit: Optional limit on number of records
            
        Returns:
            List of odds history entries
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT 
                        id, player_id, player_name, game_id, game_date, team_abbr,
                        points_line, assists_line, rebounds_line, over_odds, under_odds, bookmaker, recorded_at
                    FROM player_odds_history
                    WHERE player_id = %s
                """
                params = [player_id]
                
                if game_id:
                    query += " AND game_id = %s"
                    params.append(game_id)
                
                query += " ORDER BY recorded_at DESC"
                
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row['id'],
                        'player_id': row['player_id'],
                        'player_name': row['player_name'],
                        'game_id': row['game_id'],
                        'game_date': str(row['game_date']),
                        'team_abbr': row['team_abbr'],
                        'points_line': float(row['points_line']) if row['points_line'] else None,
                        'assists_line': float(row['assists_line']) if row.get('assists_line') else None,
                        'rebounds_line': float(row['rebounds_line']) if row.get('rebounds_line') else None,
                        'over_odds': row['over_odds'],
                        'under_odds': row['under_odds'],
                        'bookmaker': row['bookmaker'],
                        'recorded_at': row['recorded_at'].isoformat() if row['recorded_at'] else None
                    }
                    for row in rows
                ]

