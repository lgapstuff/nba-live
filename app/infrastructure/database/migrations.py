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
                
                conn.commit()
                logger.info("Database tables created successfully")
                
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise
    finally:
        db.close()

