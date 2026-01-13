"""
Lineup repository for MySQL operations.
"""
from typing import List, Dict, Any, Optional
import logging
import json

from app.infrastructure.database.connection import DatabaseConnection
from app.domain.value_objects.player_photos import get_player_photo_url

logger = logging.getLogger(__name__)


class LineupRepository:
    """
    Repository for managing lineup data in MySQL.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the repository.
        
        Args:
            db_connection: Database connection manager
        """
        self.db = db_connection
    
    def save_lineup_for_game(self, game_id: str, lineup_date: str, team_abbr: str, 
                             position: str, player_id: int, player_name: str, 
                             confirmed: bool = False, player_photo_url: Optional[str] = None,
                             player_status: str = 'STARTER', points_line: Optional[float] = None) -> None:
        """
        Save a single lineup entry for a game.
        
        Args:
            game_id: Game identifier
            lineup_date: Date of the lineup (YYYY-MM-DD)
            team_abbr: Team abbreviation
            position: Player position (C, PF, PG, SF, SG)
            player_id: Player ID
            player_name: Player name
            confirmed: Whether the lineup is confirmed
            player_photo_url: URL to player photo (auto-generated if not provided)
            player_status: Player status - 'STARTER' or 'BENCH' (default: 'STARTER')
        """
        if not player_photo_url and player_id:
            player_photo_url = get_player_photo_url(player_id)
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO game_lineups (
                        game_id, lineup_date, team_abbr, position,
                        player_id, player_name, player_photo_url, confirmed, player_status, points_line
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        player_id = VALUES(player_id),
                        player_name = VALUES(player_name),
                        player_photo_url = VALUES(player_photo_url),
                        confirmed = VALUES(confirmed),
                        -- Only update player_status if current status is not STARTER
                        -- This preserves STARTER status when odds are loaded after lineups
                        player_status = CASE 
                            WHEN player_status = 'STARTER' THEN 'STARTER'
                            ELSE VALUES(player_status)
                        END,
                        points_line = COALESCE(VALUES(points_line), points_line),
                        updated_at = CURRENT_TIMESTAMP
                """, (game_id, lineup_date, team_abbr, position, 
                      player_id, player_name, player_photo_url, 1 if confirmed else 0, player_status, points_line))
                conn.commit()
    
    def update_points_line_for_player(self, game_id: str, lineup_date: str, 
                                      team_abbr: str, player_id: int, 
                                      points_line: Optional[float],
                                      assists_line: Optional[float] = None,
                                      rebounds_line: Optional[float] = None,
                                      over_under_history: Optional[Dict[str, Any]] = None) -> None:
        """
        Update points_line, assists_line, rebounds_line and optionally over_under_history for a player in the lineup.
        
        Args:
            game_id: Game identifier
            lineup_date: Date of the lineup
            team_abbr: Team abbreviation
            player_id: Player ID
            points_line: Points line from odds
            assists_line: Assists line from odds (optional)
            rebounds_line: Rebounds line from odds (optional)
            over_under_history: OVER/UNDER history dictionary (optional)
        """
        import json
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                if over_under_history:
                    over_under_json = json.dumps(over_under_history)
                    cursor.execute("""
                        UPDATE game_lineups
                        SET points_line = %s,
                            assists_line = %s,
                            rebounds_line = %s,
                            over_under_history = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE game_id = %s
                          AND lineup_date = %s
                          AND team_abbr = %s
                          AND player_id = %s
                    """, (points_line, assists_line, rebounds_line, over_under_json, 
                          game_id, lineup_date, team_abbr, player_id))
                else:
                    cursor.execute("""
                        UPDATE game_lineups
                        SET points_line = %s,
                            assists_line = %s,
                            rebounds_line = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE game_id = %s
                          AND lineup_date = %s
                          AND team_abbr = %s
                          AND player_id = %s
                    """, (points_line, assists_line, rebounds_line, 
                          game_id, lineup_date, team_abbr, player_id))
                conn.commit()
    
    def save_lineups_for_game(self, game_id: str, lineup_date: str, 
                              team_lineups: Dict[str, Dict[str, Dict[str, Any]]]) -> int:
        """
        Save lineups for a game (both home and away teams).
        
        Args:
            game_id: Game identifier
            lineup_date: Date of the lineup (YYYY-MM-DD)
            team_lineups: Dictionary with team abbreviations as keys and positions as values
                         Example: {"LAL": {"PG": {"playerId": 123, "name": "Player", "confirmed": "1"}}}
            
        Returns:
            Number of lineup entries saved
        """
        saved_count = 0
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                for team_abbr, positions in team_lineups.items():
                    for position, player_data in positions.items():
                        try:
                            player_id = int(player_data.get('playerId', 0))
                            player_name = player_data.get('name', '')
                            confirmed = player_data.get('confirmed', '0')
                            
                            # Handle both string and int confirmed values
                            if isinstance(confirmed, str):
                                confirmed_bool = confirmed == '1' or confirmed.lower() == 'true'
                            else:
                                confirmed_bool = bool(confirmed)
                            
                            # Generate player photo URL (may be None if unavailable)
                            # Note: FantasyNerds player_id may not work with their photo CDN
                            player_photo_url = get_player_photo_url(player_id)
                            
                            # If confirmed lineup, first update any existing BENCH entries for this player
                            # This handles the case where player was saved from odds with position='BENCH'
                            if confirmed_bool and player_id > 0:
                                # Update any existing BENCH entries for this player to the correct position and STARTER status
                                cursor.execute("""
                                    UPDATE game_lineups
                                    SET position = %s,
                                        player_status = 'STARTER',
                                        confirmed = 1,
                                        player_photo_url = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE game_id = %s
                                      AND lineup_date = %s
                                      AND team_abbr = %s
                                      AND player_id = %s
                                      AND (position = 'BENCH' OR player_status = 'BENCH')
                                """, (position, player_photo_url, game_id, lineup_date, team_abbr, player_id))
                            
                            # Determine player status:
                            # ALL players from FantasyNerds lineups are STARTERS
                            # The 'confirmed' field indicates if the lineup is officially confirmed,
                            # but if FantasyNerds returns a lineup, those players are the starters
                            # regardless of the confirmed value
                            # Only players from odds (not in lineup) should be BENCH
                            player_status = 'STARTER'  # All lineup players are starters
                            
                            cursor.execute("""
                                INSERT INTO game_lineups (
                                    game_id, lineup_date, team_abbr, position,
                                    player_id, player_name, player_photo_url, confirmed, player_status
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                                ON DUPLICATE KEY UPDATE
                                    player_id = VALUES(player_id),
                                    player_name = VALUES(player_name),
                                    player_photo_url = VALUES(player_photo_url),
                                    confirmed = VALUES(confirmed),
                                    -- All players from FantasyNerds lineups are STARTERS
                                    -- The confirmed field indicates official confirmation, but
                                    -- if they're in the lineup, they're starters
                                    player_status = 'STARTER',
                                    updated_at = CURRENT_TIMESTAMP
                            """, (game_id, lineup_date, team_abbr, position,
                                  player_id, player_name, player_photo_url, 1 if confirmed_bool else 0, player_status))
                            
                            # After INSERT/UPDATE, ensure that all lineup players are STARTER
                            # This fixes any cases where the status wasn't updated correctly
                            # Also update by player_id to catch cases where position changed
                            if player_id > 0:
                                # Update by position (for the current position)
                                # All players in lineup should be STARTER regardless of confirmed value
                                cursor.execute("""
                                    UPDATE game_lineups
                                    SET player_status = 'STARTER'
                                    WHERE game_id = %s
                                      AND lineup_date = %s
                                      AND team_abbr = %s
                                      AND position = %s
                                      AND player_status != 'STARTER'
                                """, (game_id, lineup_date, team_abbr, position))
                                
                                # Also update by player_id to catch any other entries for this player
                                # (in case they were saved with different positions)
                                cursor.execute("""
                                    UPDATE game_lineups
                                    SET player_status = 'STARTER',
                                        position = %s
                                    WHERE game_id = %s
                                      AND lineup_date = %s
                                      AND team_abbr = %s
                                      AND player_id = %s
                                      AND player_status != 'STARTER'
                                """, (position, game_id, lineup_date, team_abbr, player_id))
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"Error saving lineup entry: {e}")
                            continue
                
                conn.commit()
                return saved_count
    
    def get_lineups_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Get all lineups for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of lineup dictionaries grouped by game
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        gl.game_id, gl.team_abbr, gl.position,
                        gl.player_id, gl.player_name, gl.player_photo_url, gl.confirmed, gl.player_status,
                        gl.lineup_date, gl.points_line, gl.assists_line, gl.rebounds_line, gl.over_under_history,
                        g.home_team, g.away_team, g.game_date, g.game_time,
                        g.home_team_name, g.away_team_name,
                        g.home_team_logo_url, g.away_team_logo_url
                    FROM game_lineups gl
                    JOIN games g ON gl.game_id = g.game_id
                    WHERE gl.lineup_date = %s
                    ORDER BY gl.game_id, gl.team_abbr, gl.position
                """, (date,))
                
                rows = cursor.fetchall()
                
                # Group by game_id and team
                result = {}
                for row in rows:
                    game_id = row['game_id']
                    if game_id not in result:
                        result[game_id] = {
                            'game_id': game_id,
                            'home_team': row['home_team'],
                            'away_team': row['away_team'],
                            'home_team_name': row['home_team_name'],
                            'away_team_name': row['away_team_name'],
                            'home_team_logo_url': row['home_team_logo_url'],
                            'away_team_logo_url': row['away_team_logo_url'],
                            'game_date': str(row['game_date']) if row['game_date'] else None,
                            'game_time': str(row['game_time']) if row['game_time'] else None,
                            'lineup_date': str(row['lineup_date']) if row['lineup_date'] else None,
                            'lineups': {}
                        }
                    
                    team_abbr = row['team_abbr']
                    if team_abbr not in result[game_id]['lineups']:
                        result[game_id]['lineups'][team_abbr] = {}
                    
                    position = row['position']
                    player_status = row.get('player_status', 'BENCH')
                    
                    # Get photo URL - may be None if FantasyNerds CDN doesn't have the photo
                    photo_url = row['player_photo_url']
                    if not photo_url:
                        photo_url = get_player_photo_url(row['player_id'])
                    
                    # Parse over_under_history JSON if present
                    over_under_history = None
                    if row.get('over_under_history'):
                        try:
                            if isinstance(row['over_under_history'], str):
                                over_under_history = json.loads(row['over_under_history'])
                            else:
                                # Already a dict (MySQL JSON type returns dict)
                                over_under_history = row['over_under_history']
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Failed to parse over_under_history for player {row['player_name']}")
                            over_under_history = None
                    
                    player_data = {
                        'player_id': row['player_id'],
                        'player_name': row['player_name'],
                        'player_photo_url': photo_url,  # May be None if photo unavailable
                        'confirmed': bool(row['confirmed']),
                        'player_status': player_status,
                        'points_line': float(row['points_line']) if row.get('points_line') is not None else None,
                        'assists_line': float(row['assists_line']) if row.get('assists_line') is not None else None,
                        'rebounds_line': float(row['rebounds_line']) if row.get('rebounds_line') is not None else None,
                        'over_under_history': over_under_history
                    }
                    
                    # Handle BENCH players (position format: 'BENCH-{player_id}')
                    if position.startswith('BENCH-'):
                        # Store BENCH players in a list under 'BENCH' key
                        if 'BENCH' not in result[game_id]['lineups'][team_abbr]:
                            result[game_id]['lineups'][team_abbr]['BENCH'] = []
                        result[game_id]['lineups'][team_abbr]['BENCH'].append(player_data)
                    else:
                        # Regular position (PG, SG, SF, PF, C)
                        result[game_id]['lineups'][team_abbr][position] = player_data
                
                return list(result.values())
    
    def get_lineup_by_game_id(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get lineup for a specific game.
        
        Args:
            game_id: Game identifier
            
        Returns:
            Lineup dictionary or None if not found
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        gl.game_id, gl.team_abbr, gl.position,
                        gl.player_id, gl.player_name, gl.player_photo_url, gl.confirmed, gl.player_status,
                        gl.lineup_date, gl.points_line, gl.assists_line, gl.rebounds_line, gl.over_under_history,
                        g.home_team, g.away_team,
                        g.home_team_name, g.away_team_name,
                        g.home_team_logo_url, g.away_team_logo_url,
                        g.game_date, g.game_time
                    FROM game_lineups gl
                    JOIN games g ON gl.game_id = g.game_id
                    WHERE gl.game_id = %s
                    ORDER BY gl.team_abbr, gl.position
                """, (game_id,))
                
                rows = cursor.fetchall()
                
                if not rows:
                    return None
                
                # Get game info from first row
                first_row = rows[0]
                result = {
                    'game_id': game_id,
                    'home_team': first_row['home_team'],
                    'away_team': first_row['away_team'],
                    'home_team_name': first_row['home_team_name'],
                    'away_team_name': first_row['away_team_name'],
                    'home_team_logo_url': first_row['home_team_logo_url'],
                    'away_team_logo_url': first_row['away_team_logo_url'],
                    'game_date': str(first_row['game_date']) if first_row['game_date'] else None,
                    'game_time': str(first_row['game_time']) if first_row['game_time'] else None,
                    'lineup_date': str(first_row['lineup_date']) if first_row['lineup_date'] else None,
                    'lineups': {}
                }
                
                for row in rows:
                    team_abbr = row['team_abbr']
                    if team_abbr not in result['lineups']:
                        result['lineups'][team_abbr] = {}
                    
                    # Get photo URL - may be None if FantasyNerds CDN doesn't have the photo
                    photo_url = row['player_photo_url']
                    if not photo_url:
                        photo_url = get_player_photo_url(row['player_id'])
                    
                    position = row['position']
                    player_status = row.get('player_status', 'BENCH')
                    
                    # Parse over_under_history JSON if present
                    over_under_history = None
                    if row.get('over_under_history'):
                        try:
                            if isinstance(row['over_under_history'], str):
                                over_under_history = json.loads(row['over_under_history'])
                            else:
                                # Already a dict (MySQL JSON type returns dict)
                                over_under_history = row['over_under_history']
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Failed to parse over_under_history for player {row['player_name']}")
                            over_under_history = None
                    
                    player_data = {
                        'player_id': row['player_id'],
                        'player_name': row['player_name'],
                        'player_photo_url': photo_url,  # May be None if photo unavailable
                        'confirmed': bool(row['confirmed']),
                        'player_status': player_status,
                        'points_line': float(row['points_line']) if row.get('points_line') is not None else None,
                        'assists_line': float(row['assists_line']) if row.get('assists_line') is not None else None,
                        'rebounds_line': float(row['rebounds_line']) if row.get('rebounds_line') is not None else None,
                        'over_under_history': over_under_history
                    }
                    
                    # Handle BENCH players (position format: 'BENCH-{player_id}')
                    if position.startswith('BENCH-'):
                        if 'BENCH' not in result['lineups'][team_abbr]:
                            result['lineups'][team_abbr]['BENCH'] = []
                        result['lineups'][team_abbr]['BENCH'].append(player_data)
                    else:
                        result['lineups'][team_abbr][position] = player_data
                
                return result
    
    def delete_lineups_for_game(self, game_id: str, lineup_date: str) -> None:
        """
        Delete all lineups for a specific game and date.
        
        Args:
            game_id: Game identifier
            lineup_date: Date of the lineup
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM game_lineups
                    WHERE game_id = %s AND lineup_date = %s
                """, (game_id, lineup_date))
                conn.commit()
    
    def delete_lineups_for_team_game(self, game_id: str, lineup_date: str, team_abbr: str) -> None:
        """
        Delete all lineups for a specific team, game and date.
        
        Args:
            game_id: Game identifier
            lineup_date: Date of the lineup
            team_abbr: Team abbreviation
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM game_lineups
                    WHERE game_id = %s AND lineup_date = %s AND team_abbr = %s
                """, (game_id, lineup_date, team_abbr))
                conn.commit()
    
    def save_bench_player_for_game(self, game_id: str, lineup_date: str, team_abbr: str,
                                      player_id: int, player_name: str, 
                                      player_photo_url: Optional[str] = None,
                                      points_line: Optional[float] = None,
                                      assists_line: Optional[float] = None,
                                      rebounds_line: Optional[float] = None,
                                      over_under_history: Optional[Dict[str, Any]] = None) -> None:
        """
        Save a BENCH player for a game.
        Uses a composite position 'BENCH-{player_id}' to ensure uniqueness.
        
        Args:
            game_id: Game identifier
            lineup_date: Date of the lineup
            team_abbr: Team abbreviation
            player_id: Player ID
            player_name: Player name
            player_photo_url: URL to player photo
            points_line: Points line from odds (optional)
            assists_line: Assists line from odds (optional)
            rebounds_line: Rebounds line from odds (optional)
            over_under_history: OVER/UNDER history dictionary (optional)
        """
        import json
        if not player_photo_url and player_id:
            player_photo_url = get_player_photo_url(player_id)
        
        # Use composite position to ensure uniqueness for BENCH players
        position = f'BENCH-{player_id}'
        
        over_under_json = json.dumps(over_under_history) if over_under_history else None
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO game_lineups (
                        game_id, lineup_date, team_abbr, position,
                        player_id, player_name, player_photo_url, confirmed, player_status, 
                        points_line, assists_line, rebounds_line, over_under_history
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        player_id = VALUES(player_id),
                        player_name = VALUES(player_name),
                        player_photo_url = VALUES(player_photo_url),
                        confirmed = 0,
                        player_status = 'BENCH',
                        points_line = VALUES(points_line),
                        assists_line = VALUES(assists_line),
                        rebounds_line = VALUES(rebounds_line),
                        over_under_history = VALUES(over_under_history),
                        updated_at = CURRENT_TIMESTAMP
                """, (game_id, lineup_date, team_abbr, position, 
                      player_id, player_name, player_photo_url, 0, 'BENCH', 
                      points_line, assists_line, rebounds_line, over_under_json))
                conn.commit()
    
    def save_depth_chart(self, team_abbr: str, season: int, depth_chart: Dict[str, List[Dict[str, Any]]]) -> int:
        """
        Save depth chart for a team.
        Players are saved with position and depth, but not as part of a game lineup.
        These are used to identify which team a player belongs to when matching with odds.
        
        Args:
            team_abbr: Team abbreviation (e.g., "SA", "DEN")
            season: Season year (e.g., 2021)
            depth_chart: Dictionary with positions as keys and list of players as values
                        Example: {"PG": [{"playerId": 450, "name": "Keldon Johnson", ...}], ...}
        
        Returns:
            Number of players saved
        """
        saved_count = 0
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                # First, delete existing depth chart for this team and season
                cursor.execute("""
                    DELETE FROM team_depth_charts
                    WHERE team_abbr = %s AND season = %s
                """, (team_abbr, season))
                
                # Insert all players from depth chart
                for position, players in depth_chart.items():
                    for player_data in players:
                        try:
                            player_id = int(player_data.get('playerId', 0))
                            player_name = player_data.get('name', '')
                            depth = int(player_data.get('depth', 0))
                            
                            if not player_name:
                                continue
                            
                            player_photo_url = get_player_photo_url(player_id) if player_id > 0 else None
                            
                            cursor.execute("""
                                INSERT INTO team_depth_charts (
                                    team_abbr, season, position, depth,
                                    player_id, player_name, player_photo_url
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s
                                )
                                ON DUPLICATE KEY UPDATE
                                    player_name = VALUES(player_name),
                                    player_photo_url = VALUES(player_photo_url),
                                    depth = VALUES(depth),
                                    updated_at = CURRENT_TIMESTAMP
                            """, (team_abbr, season, position, depth, 
                                  player_id, player_name, player_photo_url))
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"Error saving depth chart player: {e}")
                            continue
                
                conn.commit()
                return saved_count
    
    def get_players_by_team(self, team_abbr: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all players for a team from depth charts.
        Used to match players from odds with their correct team.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year (optional, uses latest if not provided)
        
        Returns:
            List of player dictionaries with team, position, depth, etc.
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                if season:
                    cursor.execute("""
                        SELECT team_abbr, position, depth, player_id, player_name, player_photo_url
                        FROM team_depth_charts
                        WHERE team_abbr = %s AND season = %s
                        ORDER BY position, depth
                    """, (team_abbr, season))
                else:
                    # Get latest season
                    cursor.execute("""
                        SELECT team_abbr, position, depth, player_id, player_name, player_photo_url
                        FROM team_depth_charts
                        WHERE team_abbr = %s
                        AND season = (SELECT MAX(season) FROM team_depth_charts WHERE team_abbr = %s)
                        ORDER BY position, depth
                    """, (team_abbr, team_abbr))
                
                rows = cursor.fetchall()
                return [
                    {
                        'team_abbr': row['team_abbr'],
                        'position': row['position'],
                        'depth': row['depth'],
                        'player_id': row['player_id'],
                        'player_name': row['player_name'],
                        'player_photo_url': row['player_photo_url']
                    }
                    for row in rows
                ]
    
    def get_all_teams_players(self, season: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all players for all teams from depth charts.
        Used to match players from odds with their correct team.
        
        Args:
            season: Season year (optional, uses latest if not provided)
        
        Returns:
            Dictionary with team_abbr as key and list of players as value
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                if season:
                    cursor.execute("""
                        SELECT team_abbr, position, depth, player_id, player_name, player_photo_url
                        FROM team_depth_charts
                        WHERE season = %s
                        ORDER BY team_abbr, position, depth
                    """, (season,))
                else:
                    # Get latest season
                    cursor.execute("""
                        SELECT team_abbr, position, depth, player_id, player_name, player_photo_url
                        FROM team_depth_charts
                        WHERE season = (SELECT MAX(season) FROM team_depth_charts)
                        ORDER BY team_abbr, position, depth
                    """)
                
                rows = cursor.fetchall()
                result = {}
                for row in rows:
                    team_abbr = row['team_abbr']
                    if team_abbr not in result:
                        result[team_abbr] = []
                    result[team_abbr].append({
                        'team_abbr': team_abbr,
                        'position': row['position'],
                        'depth': row['depth'],
                        'player_id': row['player_id'],
                        'player_name': row['player_name'],
                        'player_photo_url': row['player_photo_url']
                    })
                return result
