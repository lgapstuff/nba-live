"""
Repository for player game logs operations.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.infrastructure.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class GameLogRepository:
    """
    Repository for managing player game logs in the database.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the repository.
        
        Args:
            db_connection: Database connection manager
        """
        self.db = db_connection
    
    def save_player_game_logs(self, player_id: int, player_name: str, 
                             games: List[Dict[str, Any]]) -> int:
        """
        Save game logs for a player.
        Only saves the most recent games (keeps last 25).
        
        Args:
            player_id: NBA player ID
            player_name: Player name
            games: List of game dictionaries from NBA API
            
        Returns:
            Number of games saved
        """
        saved_count = 0
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                for game in games:
                    try:
                        # Extract game data
                        game_date_str = game.get('GAME_DATE', game.get('game_date', ''))
                        if not game_date_str:
                            continue
                        
                        # Parse date - NBA API can return dates in multiple formats
                        game_date = None
                        try:
                            # Clean the date string
                            game_date_str = str(game_date_str).strip()
                            
                            # Try format "YYYY-MM-DD" first (most common)
                            if len(game_date_str) >= 10 and '-' in game_date_str and game_date_str[4] == '-':
                                game_date = datetime.strptime(game_date_str[:10], '%Y-%m-%d').date()
                            # Try format "MMM DD, YYYY" (e.g., "Dec 06, 2025" or "Dec 6, 2025")
                            elif ',' in game_date_str:
                                # Handle both "Dec 06, 2025" and "Dec 6, 2025"
                                try:
                                    game_date = datetime.strptime(game_date_str, '%b %d, %Y').date()
                                except ValueError:
                                    # Try with zero-padded day
                                    try:
                                        game_date = datetime.strptime(game_date_str, '%b %d, %Y').date()
                                    except ValueError:
                                        # Try without comma (some variations)
                                        game_date = datetime.strptime(game_date_str.replace(',', ''), '%b %d %Y').date()
                            # Try format "MM/DD/YYYY"
                            elif '/' in game_date_str and len(game_date_str.split('/')) == 3:
                                parts = game_date_str.split('/')
                                if len(parts[2]) == 4:  # Full year
                                    game_date = datetime.strptime(game_date_str, '%m/%d/%Y').date()
                                else:  # 2-digit year
                                    game_date = datetime.strptime(game_date_str, '%m/%d/%y').date()
                            else:
                                logger.warning(f"Unknown date format: {game_date_str}")
                                continue
                        except Exception as e:
                            logger.warning(f"Could not parse game date '{game_date_str}': {e}")
                            continue
                        
                        matchup = game.get('MATCHUP', game.get('matchup', ''))
                        points = game.get('PTS', game.get('pts'))
                        minutes = game.get('MIN', game.get('min'))
                        
                        # Extract other stats
                        fgm = game.get('FGM', game.get('fgm'))
                        fga = game.get('FGA', game.get('fga'))
                        fg3m = game.get('FG3M', game.get('fg3m'))
                        fg3a = game.get('FG3A', game.get('fg3a'))
                        ftm = game.get('FTM', game.get('ftm'))
                        fta = game.get('FTA', game.get('fta'))
                        reb = game.get('REB', game.get('reb'))
                        ast = game.get('AST', game.get('ast'))
                        stl = game.get('STL', game.get('stl'))
                        blk = game.get('BLK', game.get('blk'))
                        tov = game.get('TOV', game.get('tov'))
                        pf = game.get('PF', game.get('pf'))
                        plus_minus = game.get('PLUS_MINUS', game.get('plus_minus'))
                        
                        # Store full game data as JSON for future use
                        game_data_json = json.dumps(game, default=str)
                        
                        # Convert points to float if possible
                        points_float = None
                        if points is not None:
                            try:
                                points_float = float(points)
                            except (ValueError, TypeError):
                                pass
                        
                        # Convert minutes to float if possible
                        minutes_float = None
                        if minutes is not None:
                            try:
                                # NBA API returns minutes as "MM:SS" or decimal
                                if isinstance(minutes, str) and ':' in minutes:
                                    parts = minutes.split(':')
                                    minutes_float = float(parts[0]) + (float(parts[1]) / 60.0)
                                else:
                                    minutes_float = float(minutes)
                            except (ValueError, TypeError):
                                pass
                        
                        # Insert or update game log
                        cursor.execute("""
                            INSERT INTO player_game_logs (
                                player_id, player_name, game_date, matchup,
                                points, minutes_played,
                                field_goals_made, field_goals_attempted,
                                three_pointers_made, three_pointers_attempted,
                                free_throws_made, free_throws_attempted,
                                rebounds, assists, steals, blocks,
                                turnovers, personal_fouls, plus_minus,
                                game_data
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON DUPLICATE KEY UPDATE
                                player_name = VALUES(player_name),
                                matchup = VALUES(matchup),
                                points = VALUES(points),
                                minutes_played = VALUES(minutes_played),
                                field_goals_made = VALUES(field_goals_made),
                                field_goals_attempted = VALUES(field_goals_attempted),
                                three_pointers_made = VALUES(three_pointers_made),
                                three_pointers_attempted = VALUES(three_pointers_attempted),
                                free_throws_made = VALUES(free_throws_made),
                                free_throws_attempted = VALUES(free_throws_attempted),
                                rebounds = VALUES(rebounds),
                                assists = VALUES(assists),
                                steals = VALUES(steals),
                                blocks = VALUES(blocks),
                                turnovers = VALUES(turnovers),
                                personal_fouls = VALUES(personal_fouls),
                                plus_minus = VALUES(plus_minus),
                                game_data = VALUES(game_data),
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            player_id, player_name, game_date, matchup,
                            points_float, minutes_float,
                            fgm, fga, fg3m, fg3a, ftm, fta,
                            reb, ast, stl, blk, tov, pf, plus_minus,
                            game_data_json
                        ))
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error saving game log for player {player_id}: {e}")
                        continue
                
                conn.commit()
                
                # Clean up old games (keep only last 25 per player)
                self._cleanup_old_games(cursor, player_id, keep_count=25)
                conn.commit()
                
                return saved_count
    
    def _cleanup_old_games(self, cursor, player_id: int, keep_count: int = 25) -> None:
        """
        Remove old game logs, keeping only the most recent N games.
        
        Args:
            cursor: Database cursor
            player_id: Player ID
            keep_count: Number of recent games to keep
        """
        try:
            cursor.execute("""
                DELETE FROM player_game_logs
                WHERE player_id = %s
                AND id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM player_game_logs
                        WHERE player_id = %s
                        ORDER BY game_date DESC, id DESC
                        LIMIT %s
                    ) AS recent_games
                )
            """, (player_id, player_id, keep_count))
        except Exception as e:
            logger.warning(f"Could not cleanup old games for player {player_id}: {e}")
    
    def get_player_game_logs(self, player_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get game logs for a player, ordered by most recent first.
        
        Args:
            player_id: NBA player ID
            limit: Maximum number of games to return (default: all)
            
        Returns:
            List of game log dictionaries
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                if limit:
                    cursor.execute("""
                        SELECT 
                            player_id, player_name, game_date, matchup,
                            points, minutes_played,
                            field_goals_made, field_goals_attempted,
                            three_pointers_made, three_pointers_attempted,
                            free_throws_made, free_throws_attempted,
                            rebounds, assists, steals, blocks,
                            turnovers, personal_fouls, plus_minus,
                            game_data
                        FROM player_game_logs
                        WHERE player_id = %s
                        ORDER BY game_date DESC, id DESC
                        LIMIT %s
                    """, (player_id, limit))
                else:
                    cursor.execute("""
                        SELECT 
                            player_id, player_name, game_date, matchup,
                            points, minutes_played,
                            field_goals_made, field_goals_attempted,
                            three_pointers_made, three_pointers_attempted,
                            free_throws_made, free_throws_attempted,
                            rebounds, assists, steals, blocks,
                            turnovers, personal_fouls, plus_minus,
                            game_data
                        FROM player_game_logs
                        WHERE player_id = %s
                        ORDER BY game_date DESC, id DESC
                    """, (player_id,))
                
                rows = cursor.fetchall()
                
                return [
                    {
                        'player_id': row['player_id'],
                        'player_name': row['player_name'],
                        'game_date': row['game_date'],
                        'matchup': row['matchup'],
                        'points': float(row['points']) if row.get('points') is not None else None,
                        'minutes_played': float(row['minutes_played']) if row.get('minutes_played') is not None else None,
                        'field_goals_made': row.get('field_goals_made'),
                        'field_goals_attempted': row.get('field_goals_attempted'),
                        'three_pointers_made': row.get('three_pointers_made'),
                        'three_pointers_attempted': row.get('three_pointers_attempted'),
                        'free_throws_made': row.get('free_throws_made'),
                        'free_throws_attempted': row.get('free_throws_attempted'),
                        'rebounds': row.get('rebounds'),
                        'assists': row.get('assists'),
                        'steals': row.get('steals'),
                        'blocks': row.get('blocks'),
                        'turnovers': row.get('turnovers'),
                        'personal_fouls': row.get('personal_fouls'),
                        'plus_minus': row.get('plus_minus'),
                        'game_data': json.loads(row['game_data']) if row.get('game_data') else None
                    }
                    for row in rows
                ]

