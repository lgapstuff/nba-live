"""
Database migration and initialization scripts.
"""
import logging
from app.config.settings import Config
from app.infrastructure.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


def create_tables(config: Config) -> None:
    """
    Create database tables if they don't exist.
    
    Args:
        config: Application configuration
    """
    db = DatabaseConnection(config)
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create games table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS games (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        game_id VARCHAR(50) UNIQUE NOT NULL,
                        home_team VARCHAR(10) NOT NULL,
                        away_team VARCHAR(10) NOT NULL,
                        game_date DATE NOT NULL,
                        game_time TIME,
                        status VARCHAR(20),
                        season VARCHAR(10),
                        season_type VARCHAR(20),
                        home_team_name VARCHAR(100),
                        away_team_name VARCHAR(100),
                        home_team_logo_url VARCHAR(255),
                        away_team_logo_url VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_game_date (game_date),
                        INDEX idx_game_id (game_id),
                        INDEX idx_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Add logo URL columns if they don't exist (for existing tables)
                try:
                    cursor.execute("""
                        ALTER TABLE games 
                        ADD COLUMN home_team_logo_url VARCHAR(255)
                    """)
                except Exception:
                    # Column already exists, ignore
                    pass
                
                try:
                    cursor.execute("""
                        ALTER TABLE games 
                        ADD COLUMN away_team_logo_url VARCHAR(255)
                    """)
                except Exception:
                    # Column already exists, ignore
                    pass
                
                # Create game_lineups table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS game_lineups (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        game_id VARCHAR(50) NOT NULL,
                        lineup_date DATE NOT NULL,
                        team_abbr VARCHAR(10) NOT NULL,
                        position VARCHAR(50) NOT NULL,
                        player_id INT NOT NULL,
                        player_name VARCHAR(100) NOT NULL,
                        player_photo_url VARCHAR(255),
                        confirmed TINYINT(1) DEFAULT 0,
                        player_status VARCHAR(10) DEFAULT 'BENCH',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_lineup (game_id, team_abbr, position, lineup_date),
                        INDEX idx_game_id (game_id),
                        INDEX idx_lineup_date (lineup_date),
                        INDEX idx_team_abbr (team_abbr),
                        FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Update position column size if it exists and is too small
                # This handles existing databases that have VARCHAR(5)
                try:
                    cursor.execute("""
                        ALTER TABLE game_lineups 
                        MODIFY COLUMN position VARCHAR(50) NOT NULL
                    """)
                    logger.info("Updated position column size to VARCHAR(50)")
                except Exception as e:
                    # Column might not exist yet or already has correct size
                    logger.debug(f"Position column update: {e}")
                    pass
                
                # Add player_photo_url column if it doesn't exist (for existing tables)
                try:
                    cursor.execute("""
                        ALTER TABLE game_lineups 
                        ADD COLUMN player_photo_url VARCHAR(255)
                    """)
                except Exception:
                    # Column already exists, ignore
                    pass
                
                # Add player_status column if it doesn't exist (for existing tables)
                try:
                    cursor.execute("""
                        ALTER TABLE game_lineups 
                        ADD COLUMN player_status VARCHAR(10) DEFAULT 'BENCH'
                    """)
                except Exception:
                    # Column already exists, ignore
                    pass
                
                # Add points_line column if it doesn't exist (for storing odds points)
                try:
                    cursor.execute("""
                        ALTER TABLE game_lineups 
                        ADD COLUMN points_line DECIMAL(5,1) NULL
                    """)
                    logger.info("Added points_line column to game_lineups")
                except Exception:
                    # Column already exists, ignore
                    pass
                
                # Add assists_line column if it doesn't exist (for storing assists odds)
                try:
                    cursor.execute("""
                        ALTER TABLE game_lineups 
                        ADD COLUMN assists_line DECIMAL(5,1) NULL
                    """)
                    logger.info("Added assists_line column to game_lineups")
                except Exception:
                    # Column already exists, ignore
                    pass
                
                # Add rebounds_line column if it doesn't exist (for storing rebounds odds)
                try:
                    cursor.execute("""
                        ALTER TABLE game_lineups 
                        ADD COLUMN rebounds_line DECIMAL(5,1) NULL
                    """)
                    logger.info("Added rebounds_line column to game_lineups")
                except Exception:
                    # Column already exists, ignore
                    pass
                
                # Add over_under_history column if it doesn't exist (for storing OVER/UNDER history JSON)
                try:
                    cursor.execute("""
                        ALTER TABLE game_lineups 
                        ADD COLUMN over_under_history JSON NULL
                    """)
                    logger.info("Added over_under_history column to game_lineups")
                except Exception:
                    # Column already exists, ignore
                    pass
                
                # Create team_depth_charts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS team_depth_charts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        team_abbr VARCHAR(10) NOT NULL,
                        season INT NOT NULL,
                        position VARCHAR(5) NOT NULL,
                        depth INT NOT NULL,
                        player_id INT NOT NULL,
                        player_name VARCHAR(100) NOT NULL,
                        player_photo_url VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_depth_chart (team_abbr, season, position, depth, player_id),
                        INDEX idx_team_abbr (team_abbr),
                        INDEX idx_season (season),
                        INDEX idx_player_name (player_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Create player_game_logs table for storing game logs locally
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS player_game_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        player_id INT NOT NULL,
                        player_name VARCHAR(100) NOT NULL,
                        game_date DATE NOT NULL,
                        matchup VARCHAR(50),
                        points DECIMAL(5,1),
                        minutes_played DECIMAL(5,1),
                        field_goals_made INT,
                        field_goals_attempted INT,
                        three_pointers_made INT,
                        three_pointers_attempted INT,
                        free_throws_made INT,
                        free_throws_attempted INT,
                        rebounds INT,
                        assists INT,
                        steals INT,
                        blocks INT,
                        turnovers INT,
                        personal_fouls INT,
                        plus_minus INT,
                        game_data JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_game_log (player_id, game_date, matchup),
                        INDEX idx_player_id (player_id),
                        INDEX idx_game_date (game_date),
                        INDEX idx_player_date (player_id, game_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Create player_odds_history table for storing odds history
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS player_odds_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        player_id INT NOT NULL,
                        player_name VARCHAR(100) NOT NULL,
                        game_id VARCHAR(50) NOT NULL,
                        game_date DATE NOT NULL,
                        team_abbr VARCHAR(10) NOT NULL,
                        points_line DECIMAL(5,1) NOT NULL,
                        assists_line DECIMAL(5,1) NULL,
                        rebounds_line DECIMAL(5,1) NULL,
                        over_odds INT,
                        under_odds INT,
                        bookmaker VARCHAR(50),
                        recorded_at DATETIME NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_player_id (player_id),
                        INDEX idx_game_id (game_id),
                        INDEX idx_game_date (game_date),
                        INDEX idx_recorded_at (recorded_at),
                        INDEX idx_player_game (player_id, game_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Add assists_line and rebounds_line columns if they don't exist (migration)
                try:
                    cursor.execute("""
                        ALTER TABLE player_odds_history 
                        ADD COLUMN assists_line DECIMAL(5,1) NULL
                    """)
                    logger.info("Added assists_line column to player_odds_history")
                except Exception:
                    pass
                
                try:
                    cursor.execute("""
                        ALTER TABLE player_odds_history 
                        ADD COLUMN rebounds_line DECIMAL(5,1) NULL
                    """)
                    logger.info("Added rebounds_line column to player_odds_history")
                except Exception:
                    pass
                
                conn.commit()
                logger.info("Database tables created successfully")
                
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise
    finally:
        db.close()

