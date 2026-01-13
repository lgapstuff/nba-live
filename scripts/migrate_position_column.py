"""
Migration script to update position column size in game_lineups table.
This fixes the "Data too long for column 'position'" error when saving BENCH players.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import Config
from app.infrastructure.database.connection import DatabaseConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_position_column():
    """
    Update the position column in game_lineups table from VARCHAR(5) to VARCHAR(50).
    This is needed because BENCH players use format 'BENCH-{player_id}' which can exceed 5 characters.
    """
    config = Config()
    db = DatabaseConnection(config)
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check current column definition
                cursor.execute("""
                    SELECT COLUMN_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'game_lineups' 
                    AND COLUMN_NAME = 'position'
                """)
                result = cursor.fetchone()
                
                if result:
                    current_type = result.get('COLUMN_TYPE', '')
                    logger.info(f"Current position column type: {current_type}")
                    
                    if 'varchar(5)' in current_type.lower():
                        logger.info("Updating position column from VARCHAR(5) to VARCHAR(50)...")
                        cursor.execute("""
                            ALTER TABLE game_lineups 
                            MODIFY COLUMN position VARCHAR(50) NOT NULL
                        """)
                        conn.commit()
                        logger.info("✓ Position column updated successfully to VARCHAR(50)")
                    else:
                        logger.info(f"Position column already has correct size or different type: {current_type}")
                else:
                    logger.warning("game_lineups table or position column not found. Run init_db.py first.")
                    
    except Exception as e:
        logger.error(f"Error migrating position column: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Migrating position column in game_lineups table...")
    try:
        migrate_position_column()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

