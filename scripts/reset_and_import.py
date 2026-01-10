"""
Script to reset the database and import schedule from JSON file.
This is a complete reset: drops all tables, recreates them, and imports schedule.
"""
import sys
import os
import argparse
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import Config
from app.infrastructure.database.connection import DatabaseConnection
from app.infrastructure.database.migrations import create_tables
from app.infrastructure.repositories.game_repository import GameRepository
from app.application.services.schedule_service import ScheduleService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reset_and_import(schedule_file: str = None):
    """
    Reset database and optionally import schedule.
    
    Args:
        schedule_file: Path to JSON file with schedule data (optional)
    """
    config = Config()
    db = DatabaseConnection(config)
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                logger.info("=" * 60)
                logger.info("RESETTING DATABASE")
                logger.info("=" * 60)
                
                # Drop tables in reverse order of dependencies
                logger.info("Dropping existing tables...")
                cursor.execute("DROP TABLE IF EXISTS game_lineups")
                logger.info("  ✓ Dropped game_lineups table")
                
                cursor.execute("DROP TABLE IF EXISTS games")
                logger.info("  ✓ Dropped games table")
                
                conn.commit()
                logger.info("All tables dropped successfully\n")
                
                # Recreate tables
                logger.info("Creating tables from scratch...")
                create_tables(config)
                logger.info("  ✓ Tables created successfully\n")
                
                # Import schedule if file provided
                if schedule_file:
                    if not os.path.exists(schedule_file):
                        logger.error(f"Schedule file not found: {schedule_file}")
                        return
                    
                    logger.info("=" * 60)
                    logger.info("IMPORTING SCHEDULE")
                    logger.info("=" * 60)
                    logger.info(f"Reading schedule from: {schedule_file}")
                    
                    import json
                    with open(schedule_file, 'r', encoding='utf-8') as f:
                        schedule_data = json.load(f)
                    
                    game_repository = GameRepository(db)
                    schedule_service = ScheduleService(game_repository)
                    
                    # Import schedule using the service method
                    result = schedule_service.import_schedule_from_dict(schedule_data)
                    
                    if result.get('success'):
                        logger.info(f"  ✓ Successfully imported {result.get('games_saved', 0)} games")
                        logger.info(f"  ✓ Season: {result.get('season', 'N/A')}")
                        logger.info(f"  ✓ Date range: {result.get('date_range', 'N/A')}")
                    else:
                        logger.error(f"  ✗ Import failed: {result.get('message', 'Unknown error')}")
                else:
                    logger.info("No schedule file provided. Database is ready for manual import.")
                
                logger.info("")
                logger.info("=" * 60)
                logger.info("DATABASE RESET COMPLETED!")
                logger.info("=" * 60)
                
    except Exception as e:
        logger.error(f"Error resetting database: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Reset database and optionally import schedule')
    parser.add_argument('--schedule', '-s', type=str, help='Path to JSON schedule file to import')
    parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    if not args.force:
        print("=" * 60)
        print("WARNING: This will DELETE ALL DATA from the database!")
        print("=" * 60)
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            sys.exit(0)
    
    reset_and_import(args.schedule)

