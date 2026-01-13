"""
Depth chart service for managing NBA team depth charts.
"""
import logging
from typing import Dict, Any, List, Optional

from app.domain.ports.fantasynerds_port import FantasyNerdsPort
from app.infrastructure.repositories.lineup_repository import LineupRepository

logger = logging.getLogger(__name__)


class DepthChartService:
    """
    Service for managing NBA depth charts operations.
    """
    
    def __init__(self, 
                 fantasynerds_port: FantasyNerdsPort,
                 lineup_repository: LineupRepository):
        """
        Initialize the service.
        
        Args:
            fantasynerds_port: Port for FantasyNerds API integration
            lineup_repository: Repository for lineup operations
        """
        self.fantasynerds_port = fantasynerds_port
        self.lineup_repository = lineup_repository
    
    def import_depth_charts_from_json(self, json_path: str) -> Dict[str, Any]:
        """
        Import depth charts from a JSON file.
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            Dictionary with import results
        """
        try:
            from pathlib import Path
            import json
            
            file_path = Path(json_path)
            if not file_path.exists():
                raise FileNotFoundError(f"JSON file not found: {json_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data or 'charts' not in data:
                return {
                    "success": False,
                    "message": "No depth charts found in file",
                    "teams_processed": 0,
                    "players_saved": 0
                }
            
            season = data.get('season')
            charts = data.get('charts', {})
            
            if not season:
                return {
                    "success": False,
                    "message": "Season not found in depth charts data",
                    "teams_processed": 0,
                    "players_saved": 0
                }
            
            teams_processed = 0
            total_players_saved = 0
            
            # Save depth charts for each team
            for team_abbr, team_chart in charts.items():
                try:
                    saved_count = self.lineup_repository.save_depth_chart(
                        team_abbr=team_abbr,
                        season=season,
                        depth_chart=team_chart
                    )
                    total_players_saved += saved_count
                    teams_processed += 1
                    logger.info(f"Saved {saved_count} players for team {team_abbr} (season {season})")
                except Exception as e:
                    logger.error(f"Error saving depth chart for team {team_abbr}: {e}")
                    continue
            
            return {
                "success": True,
                "message": f"Successfully imported depth charts for {teams_processed} teams",
                "season": season,
                "teams_processed": teams_processed,
                "players_saved": total_players_saved
            }
            
        except Exception as e:
            logger.error(f"Error importing depth charts from file: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import depth charts: {e}"
            }
    
    def import_depth_charts(self) -> Dict[str, Any]:
        """
        Import depth charts from FantasyNerds API for all teams.
        
        Returns:
            Dictionary with import results
        """
        try:
            # Get depth charts from FantasyNerds API
            logger.info("Fetching depth charts from FantasyNerds")
            depth_charts_data = self.fantasynerds_port.get_depth_charts()
            
            if not depth_charts_data or 'charts' not in depth_charts_data:
                return {
                    "success": False,
                    "message": "No depth charts found in response",
                    "teams_processed": 0,
                    "players_saved": 0
                }
            
            season = depth_charts_data.get('season')
            charts = depth_charts_data.get('charts', {})
            
            if not season:
                return {
                    "success": False,
                    "message": "Season not found in depth charts data",
                    "teams_processed": 0,
                    "players_saved": 0
                }
            
            teams_processed = 0
            total_players_saved = 0
            
            # Save depth charts for each team
            for team_abbr, team_chart in charts.items():
                try:
                    saved_count = self.lineup_repository.save_depth_chart(
                        team_abbr=team_abbr,
                        season=season,
                        depth_chart=team_chart
                    )
                    total_players_saved += saved_count
                    teams_processed += 1
                    logger.info(f"Saved {saved_count} players for team {team_abbr} (season {season})")
                except Exception as e:
                    logger.error(f"Error saving depth chart for team {team_abbr}: {e}")
                    continue
            
            return {
                "success": True,
                "message": f"Successfully imported depth charts for {teams_processed} teams",
                "season": season,
                "teams_processed": teams_processed,
                "players_saved": total_players_saved
            }
            
        except Exception as e:
            logger.error(f"Error importing depth charts: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import depth charts: {e}"
            }
    
    def get_players_by_team(self, team_abbr: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all players for a team from depth charts.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year (optional, uses latest if not provided)
        
        Returns:
            List of player dictionaries
        """
        return self.lineup_repository.get_players_by_team(team_abbr, season)
    
    def get_all_teams_players(self, season: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all players for all teams from depth charts.
        
        Args:
            season: Season year (optional, uses latest if not provided)
        
        Returns:
            Dictionary with team_abbr as key and list of players as value
        """
        return self.lineup_repository.get_all_teams_players(season)
    
    def has_depth_charts(self, season: Optional[int] = None) -> bool:
        """
        Check if depth charts exist in the database.
        
        Args:
            season: Season year (optional, checks latest if not provided)
        
        Returns:
            True if depth charts exist, False otherwise
        """
        try:
            all_players = self.get_all_teams_players(season)
            return len(all_players) > 0
        except Exception as e:
            logger.error(f"Error checking depth charts: {e}")
            return False

