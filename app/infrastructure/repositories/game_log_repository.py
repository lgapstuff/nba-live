"""
Repository for player game logs operations.
"""
import logging
import unicodedata
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
                        
                        start_position = game.get('START_POSITION', game.get('start_position'))
                        if isinstance(start_position, str):
                            start_position = start_position.strip()
                            if start_position == '':
                                start_position = None

                        starter_status = None
                        if start_position:
                            starter_status = 'STARTER'

                        # Try to hydrate starter info from saved lineups (same date)
                        lineup_info = self.get_lineup_info_for_player_date(player_id, game_date)
                        if not lineup_info and player_name:
                            lineup_info = self.get_lineup_info_for_player_name_date(player_name, game_date)
                        if lineup_info:
                            if lineup_info.get('start_position'):
                                start_position = lineup_info.get('start_position')
                                starter_status = lineup_info.get('starter_status')
                            elif lineup_info.get('starter_status') and not starter_status:
                                starter_status = lineup_info.get('starter_status')

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
                                points, minutes_played, start_position, starter_status,
                                field_goals_made, field_goals_attempted,
                                three_pointers_made, three_pointers_attempted,
                                free_throws_made, free_throws_attempted,
                                rebounds, assists, steals, blocks,
                                turnovers, personal_fouls, plus_minus,
                                game_data
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s
                            )
                            ON DUPLICATE KEY UPDATE
                                player_name = VALUES(player_name),
                                matchup = VALUES(matchup),
                                points = VALUES(points),
                                minutes_played = VALUES(minutes_played),
                                start_position = COALESCE(VALUES(start_position), start_position),
                                starter_status = COALESCE(VALUES(starter_status), starter_status),
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
                            points_float, minutes_float, start_position, starter_status,
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

    def get_lineup_info_for_player_date(self, player_id: int, game_date) -> Optional[Dict[str, Any]]:
        """
        Get starter status/position from saved lineups for a player on a specific date.
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT position, player_status
                    FROM game_lineups
                    WHERE player_id = %s
                      AND lineup_date = %s
                    LIMIT 1
                """, (player_id, game_date))
                row = cursor.fetchone()
                if not row:
                    return None

                position = row.get('position')
                player_status = row.get('player_status')

                start_position = None
                starter_status = None
                if player_status:
                    starter_status = player_status
                if position and not str(position).startswith('BENCH'):
                    start_position = position
                    if not starter_status:
                        starter_status = 'STARTER'
                elif position and str(position).startswith('BENCH') and not starter_status:
                    starter_status = 'BENCH'

                return {
                    'start_position': start_position,
                    'starter_status': starter_status
                }

    def get_lineup_info_for_player_name_date(self, player_name: str, game_date) -> Optional[Dict[str, Any]]:
        """
        Fallback: get starter status/position by player name and date.
        """
        def normalize_name(name: str) -> str:
            if not name:
                return ""
            normalized = unicodedata.normalize('NFD', name)
            normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
            return normalized.lower().strip()

        target_name = normalize_name(player_name)
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT player_name, position, player_status
                    FROM game_lineups
                    WHERE lineup_date = %s
                """, (game_date,))
                rows = cursor.fetchall()
                if not rows:
                    return None

                matched_row = None
                for row in rows:
                    if normalize_name(row.get('player_name')) == target_name:
                        matched_row = row
                        break

                if not matched_row:
                    return None

                position = matched_row.get('position')
                player_status = matched_row.get('player_status')

                start_position = None
                starter_status = None
                if player_status:
                    starter_status = player_status
                if position and not str(position).startswith('BENCH'):
                    start_position = position
                    if not starter_status:
                        starter_status = 'STARTER'
                elif position and str(position).startswith('BENCH') and not starter_status:
                    starter_status = 'BENCH'

                return {
                    'start_position': start_position,
                    'starter_status': starter_status
                }
    
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
                            points, minutes_played, start_position, starter_status,
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
                            points, minutes_played, start_position, starter_status,
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
                
                results = []
                for row in rows:
                    game_data = json.loads(row['game_data']) if row.get('game_data') else None
                    start_position = row.get('start_position')
                    starter_status = row.get('starter_status')

                    if not start_position and not starter_status and isinstance(game_data, dict):
                        if 'START_POSITION' in game_data:
                            raw_position = game_data.get('START_POSITION')
                        elif 'start_position' in game_data:
                            raw_position = game_data.get('start_position')
                        else:
                            raw_position = None

                        if raw_position is not None:
                            start_position = str(raw_position).strip()
                            if start_position == '':
                                start_position = None
                                starter_status = 'BENCH'
                            else:
                                starter_status = 'STARTER'

                        if starter_status is None:
                            starter_flag = None
                            if 'STARTER' in game_data:
                                starter_flag = game_data.get('STARTER')
                            elif 'starter' in game_data:
                                starter_flag = game_data.get('starter')

                            if starter_flag is not None:
                                if isinstance(starter_flag, str):
                                    starter_flag = starter_flag.strip()
                                if starter_flag in (1, '1', True, 'true', 'TRUE', 'Y', 'Yes'):
                                    starter_status = 'STARTER'
                                elif starter_flag in (0, '0', False, 'false', 'FALSE', 'N', 'No'):
                                    starter_status = 'BENCH'

                    results.append({
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
                        'starter_status': starter_status,
                        'start_position': start_position,
                        'game_data': game_data
                    })

                return results

    def get_player_game_logs_by_name(self, player_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get game logs for a player by name (case-insensitive), ordered by most recent first.
        """
        if not player_name:
            return []
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                if limit:
                    cursor.execute("""
                        SELECT 
                            player_id, player_name, game_date, matchup,
                            points, minutes_played, start_position, starter_status,
                            field_goals_made, field_goals_attempted,
                            three_pointers_made, three_pointers_attempted,
                            free_throws_made, free_throws_attempted,
                            rebounds, assists, steals, blocks,
                            turnovers, personal_fouls, plus_minus,
                            game_data
                        FROM player_game_logs
                        WHERE LOWER(player_name) = LOWER(%s)
                        ORDER BY game_date DESC, id DESC
                        LIMIT %s
                    """, (player_name, limit))
                else:
                    cursor.execute("""
                        SELECT 
                            player_id, player_name, game_date, matchup,
                            points, minutes_played, start_position, starter_status,
                            field_goals_made, field_goals_attempted,
                            three_pointers_made, three_pointers_attempted,
                            free_throws_made, free_throws_attempted,
                            rebounds, assists, steals, blocks,
                            turnovers, personal_fouls, plus_minus,
                            game_data
                        FROM player_game_logs
                        WHERE LOWER(player_name) = LOWER(%s)
                        ORDER BY game_date DESC, id DESC
                    """, (player_name,))

                rows = cursor.fetchall()

                results = []
                for row in rows:
                    game_data = json.loads(row['game_data']) if row.get('game_data') else None
                    start_position = row.get('start_position')
                    starter_status = row.get('starter_status')

                    if not start_position and not starter_status and isinstance(game_data, dict):
                        if 'START_POSITION' in game_data:
                            start_position = game_data.get('START_POSITION') or None
                        if 'START_POSITION' in game_data and not starter_status:
                            starter_status = 'STARTER' if start_position else starter_status

                    results.append({
                        'player_id': row['player_id'],
                        'player_name': row['player_name'],
                        'game_date': str(row['game_date']) if row.get('game_date') else None,
                        'matchup': row.get('matchup'),
                        'points': row.get('points'),
                        'minutes_played': row.get('minutes_played'),
                        'start_position': start_position,
                        'starter_status': starter_status,
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
                        'game_data': game_data
                    })

                return results

    def get_latest_game_date(self, player_id: int) -> Optional[datetime]:
        """
        Get the most recent game_date for a player.
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(game_date) AS latest_date
                    FROM player_game_logs
                    WHERE player_id = %s
                """, (player_id,))
                row = cursor.fetchone()
                return row.get('latest_date') if row else None

    def update_game_log_lineup_info(self, player_id: int, game_date: str,
                                    start_position: Optional[str],
                                    starter_status: Optional[str]) -> None:
        """
        Update lineup position/status for a player's game log on a specific date.
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE player_game_logs
                    SET start_position = %s,
                        starter_status = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE player_id = %s
                      AND game_date = %s
                """, (start_position, starter_status, player_id, game_date))
                conn.commit()

    def backfill_lineup_info_for_player_dates(self, player_id: int, player_name: Optional[str],
                                              dates: List[str]) -> int:
        """
        Backfill lineup info for existing game logs for given dates.
        """
        updated = 0
        for date in dates:
            lineup_info = self.get_lineup_info_for_player_date(player_id, date)
            if not lineup_info and player_name:
                lineup_info = self.get_lineup_info_for_player_name_date(player_name, date)
            if not lineup_info:
                continue
            self.update_game_log_lineup_info(
                player_id=player_id,
                game_date=date,
                start_position=lineup_info.get('start_position'),
                starter_status=lineup_info.get('starter_status')
            )
            updated += 1
        return updated

