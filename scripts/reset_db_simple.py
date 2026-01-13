"""
Script simple para reiniciar la base de datos (sin confirmación).
Útil para ejecutar desde Docker.
"""
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import Config
from app.infrastructure.database.connection import DatabaseConnection
from app.infrastructure.database.migrations import create_tables

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reset_database():
    """Drop all tables and recreate them from scratch."""
    config = Config()
    db = DatabaseConnection(config)
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                logger.info("Dropping existing tables...")
                
                # Drop tables in reverse order of dependencies
                cursor.execute("DROP TABLE IF EXISTS player_game_logs")
                logger.info("  ✓ Dropped player_game_logs table")
                
                cursor.execute("DROP TABLE IF EXISTS game_lineups")
                logger.info("  ✓ Dropped game_lineups table")
                
                cursor.execute("DROP TABLE IF EXISTS team_depth_charts")
                logger.info("  ✓ Dropped team_depth_charts table")
                
                cursor.execute("DROP TABLE IF EXISTS games")
                logger.info("  ✓ Dropped games table")
                
                conn.commit()
                logger.info("All tables dropped successfully")
                
                # Recreate tables using the migration function
                logger.info("Creating tables from scratch...")
                create_tables(config)
                
                logger.info("")
                logger.info("=" * 60)
                logger.info("Database reset completed successfully!")
                logger.info("You can now import schedules and lineups from scratch.")
                logger.info("=" * 60)
                
    except Exception as e:
        logger.error(f"Error resetting database: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_database()


