"""
Script to import schedule from JSON file.
Usage: python scripts/import_schedule.py <path_to_json_file>
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import Config
from app.infrastructure.database.connection import DatabaseConnection
from app.infrastructure.repositories.game_repository import GameRepository
from app.application.services.schedule_service import ScheduleService

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_schedule.py <path_to_json_file>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    if not os.path.exists(json_path):
        print(f"Error: File not found: {json_path}")
        sys.exit(1)
    
    print(f"Importing schedule from {json_path}...")
    
    config = Config()
    db_connection = DatabaseConnection(config)
    game_repository = GameRepository(db_connection)
    schedule_service = ScheduleService(game_repository)
    
    try:
        result = schedule_service.import_schedule_from_json(json_path)
        if result['success']:
            print(f"✓ Successfully imported {result['saved_games']} games")
            print(f"  Total games in file: {result['total_games']}")
        else:
            print(f"✗ Error: {result.get('message', 'Unknown error')}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error importing schedule: {e}")
        sys.exit(1)
    finally:
        db_connection.close()


