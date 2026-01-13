"""
Depth chart service for managing NBA team rosters (depth charts).
Now uses NBA API to get official rosters instead of FantasyNerds.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.domain.ports.fantasynerds_port import FantasyNerdsPort
from app.domain.ports.nba_api_port import NBAPort
from app.infrastructure.repositories.lineup_repository import LineupRepository

logger = logging.getLogger(__name__)


class DepthChartService:
    """
    Service for managing NBA team rosters (depth charts).
    Uses NBA API to get official rosters with correct player IDs.
    """
    
    def __init__(self, 
                 lineup_repository: LineupRepository,
                 nba_api_port: Optional[NBAPort] = None,
                 fantasynerds_port: Optional[FantasyNerdsPort] = None):
        """
        Initialize the service.
        
        Args:
            lineup_repository: Repository for lineup operations
            nba_api_port: Port for NBA API integration (optional, but recommended)
            fantasynerds_port: Port for FantasyNerds API (optional, for backward compatibility)
        """
        self.lineup_repository = lineup_repository
        self.nba_api = nba_api_port
        self.fantasynerds_port = fantasynerds_port
    
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
    
    def import_rosters_from_nba_api(self, season: Optional[int] = None) -> Dict[str, Any]:
        """
        Import team rosters from NBA API for all teams.
        This replaces the FantasyNerds depth charts with official NBA rosters.
        
        Args:
            season: Season year (e.g., 2024). If None, uses current season.
            
        Returns:
            Dictionary with import results
        """
        if not self.nba_api:
            return {
                "success": False,
                "message": "NBA API not available. Please ensure NBA API client is initialized.",
                "teams_processed": 0,
                "players_saved": 0
            }
        
        try:
            from app.domain.value_objects.team_names import NBA_TEAM_NAMES
            
            # Determine season
            if not season:
                current_year = datetime.now().year
                current_month = datetime.now().month
                # NBA season spans two years (e.g., 2023-24)
                # Season starts in October, so:
                # - Jan-Sep: use previous season (e.g., if we're in Jan 2026, use 2025-26)
                # - Oct-Dec: use current season (e.g., if we're in Oct 2025, use 2025-26)
                if current_month < 10:
                    # Before October, we're in the middle of the previous season
                    season = current_year - 1
                else:
                    # October or later, we're in the current season
                    season = current_year
            
            # Convert season to NBA API format (YYYY-YY)
            # e.g., 2025 -> "2025-26"
            season_str = f"{season}-{str(season + 1)[2:]}"
            
            logger.info(f"Using season {season_str} (current date: {datetime.now().strftime('%Y-%m-%d')})")
            
            logger.info(f"Importing rosters from NBA API for season {season_str}")
            
            teams_processed = 0
            total_players_saved = 0
            errors = []
            
            # Get all team abbreviations
            import time
            for idx, team_abbr in enumerate(NBA_TEAM_NAMES.keys()):
                try:
                    # Add delay between ALL requests to avoid rate limiting (0.5 seconds between each)
                    # NBA API recommends ~0.4s delay to avoid rate limiting
                    if idx > 0:
                        time.sleep(0.5)
                    
                    # Also add longer delay every 10 teams
                    if idx > 0 and idx % 10 == 0:
                        logger.info(f"Waiting 2 seconds to avoid rate limiting... ({idx}/{len(NBA_TEAM_NAMES)} teams processed)")
                        time.sleep(2)
                    
                    # Get roster from NBA API
                    logger.info(f"Fetching roster for team {team_abbr} ({idx + 1}/{len(NBA_TEAM_NAMES)})...")
                    nba_players = self.nba_api.get_team_players(team_abbr, season=season_str)
                    
                    if not nba_players:
                        logger.warning(f"No players found for team {team_abbr} from NBA API")
                        continue
                    
                    # Convert NBA API format to depth chart format
                    # NBA API returns: [{'id': 123, 'full_name': 'Player Name', 'position': 'PG', ...}, ...]
                    # We need to convert to depth chart format for storage
                    depth_chart_format = {}
                    
                    for player in nba_players:
                        position = player.get('position', 'BENCH')
                        if position not in depth_chart_format:
                            depth_chart_format[position] = []
                        
                        depth_chart_format[position].append({
                            'playerId': player.get('id'),  # NBA official ID
                            'name': player.get('full_name', ''),
                            'depth': len(depth_chart_format[position]) + 1,  # Assign depth based on order
                            'team': team_abbr
                        })
                    
                    # Save depth chart
                    saved_count = self.lineup_repository.save_depth_chart(
                        team_abbr=team_abbr,
                        season=season,
                        depth_chart=depth_chart_format
                    )
                    
                    total_players_saved += saved_count
                    teams_processed += 1
                    logger.info(f"Saved {saved_count} players for team {team_abbr} (season {season}) from NBA API")
                    
                except Exception as e:
                    error_msg = f"Error importing roster for team {team_abbr}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            result = {
                "success": True,
                "message": f"Successfully imported rosters from NBA API for {teams_processed} teams",
                "season": season,
                "teams_processed": teams_processed,
                "players_saved": total_players_saved
            }
            
            if errors:
                result["errors"] = errors
                result["error_count"] = len(errors)
            
            return result
            
        except Exception as e:
            logger.error(f"Error importing rosters from NBA API: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import rosters from NBA API: {e}"
            }
    
    def import_depth_charts(self) -> Dict[str, Any]:
        """
        Import depth charts from FantasyNerds API for all teams.
        DEPRECATED: Use import_rosters_from_nba_api() instead.
        
        Returns:
            Dictionary with import results
        """
        if not self.fantasynerds_port:
            return {
                "success": False,
                "message": "FantasyNerds API not available. Use import_rosters_from_nba_api() instead.",
                "teams_processed": 0,
                "players_saved": 0
            }
        
        try:
            # Get depth charts from FantasyNerds API
            logger.info("Fetching depth charts from FantasyNerds (DEPRECATED - use NBA API instead)")
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

