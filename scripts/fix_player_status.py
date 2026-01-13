"""
Script to fix player_status for confirmed lineups.
Sets all players with confirmed=1 to player_status='STARTER'.
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


def fix_player_status():
    """Fix player_status for all confirmed lineups."""
    config = Config()
    db = DatabaseConnection(config)
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Update all confirmed players to STARTER
                cursor.execute("""
                    UPDATE game_lineups
                    SET player_status = 'STARTER'
                    WHERE confirmed = 1
                      AND player_status != 'STARTER'
                """)
                
                rows_updated = cursor.rowcount
                conn.commit()
                
                logger.info(f"Updated {rows_updated} players from BENCH to STARTER")
                
                # Show some examples
                cursor.execute("""
                    SELECT game_id, team_abbr, position, player_name, confirmed, player_status
                    FROM game_lineups
                    WHERE confirmed = 1
                    LIMIT 10
                """)
                
                examples = cursor.fetchall()
                logger.info("Examples of confirmed players:")
                for row in examples:
                    logger.info(f"  {row['player_name']} ({row['team_abbr']} {row['position']}): confirmed={row['confirmed']}, status={row['player_status']}")
                
    except Exception as e:
        logger.error(f"Error fixing player status: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_player_status()




