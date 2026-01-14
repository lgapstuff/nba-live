"""
Lineup service for managing NBA lineups and associating them with games.
"""
import logging
import unicodedata
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.domain.ports.fantasynerds_port import FantasyNerdsPort
from app.infrastructure.repositories.lineup_repository import LineupRepository
from app.infrastructure.repositories.game_repository import GameRepository
from app.application.services.depth_chart_service import DepthChartService
from app.application.services.player_stats_service import PlayerStatsService

logger = logging.getLogger(__name__)


class LineupService:
    """
    Service for managing NBA lineups operations.
    """
    
    def __init__(self, 
                 fantasynerds_port: FantasyNerdsPort,
                 lineup_repository: LineupRepository,
                 game_repository: GameRepository,
                 depth_chart_service: DepthChartService = None,
                 player_stats_service: PlayerStatsService = None):
        """
        Initialize the service.
        
        Args:
            fantasynerds_port: Port for FantasyNerds API integration
            lineup_repository: Repository for lineup operations
            game_repository: Repository for game operations
            depth_chart_service: Depth chart service (optional, for updating player status)
            player_stats_service: Player stats service (optional, for OVER/UNDER history)
        """
        self.fantasynerds_port = fantasynerds_port
        self.lineup_repository = lineup_repository
        self.depth_chart_service = depth_chart_service
        self.player_stats_service = player_stats_service
        self.game_repository = game_repository
    
    def import_lineups_for_date(self, date: str) -> Dict[str, Any]:
        """
        Import lineups from FantasyNerds API for a specific date and associate with games.
        If lineups are not available, fallback to loading rosters from NBA API and saving them as BENCH.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with import results
        """
        try:
            # Get lineups from FantasyNerds API
            logger.info(f"Fetching lineups from FantasyNerds for date: {date}")
            lineups_data = self.fantasynerds_port.get_lineups_by_date(date)
            logger.info(f"Received lineups data: {type(lineups_data)}, keys: {list(lineups_data.keys()) if isinstance(lineups_data, dict) else 'N/A'}")
            
            # Get all games for this date from our database
            games = self.game_repository.get_games_by_date(date)
            
            # If no lineups found, try fallback to NBA API rosters
            if not lineups_data or 'lineups' not in lineups_data or not lineups_data.get('lineups'):
                logger.warning(f"No lineups found from FantasyNerds for date {date}, attempting fallback to NBA API rosters...")
                
                if not games:
                    return {
                        "success": False,
                        "message": f"No lineups found for date {date} and no games found in schedule",
                        "games_processed": 0,
                        "lineups_saved": 0
                    }
                
                # Fallback: Load rosters from NBA API and save as BENCH
                return self._import_rosters_as_bench_for_date(date, games)
            
            lineup_date = lineups_data.get('lineup_date', date)
            lineups = lineups_data.get('lineups', {})
            
            # If no games found for the exact date, try to find games by matching teams
            # This handles cases where lineups are published for a date but games might be on a different date
            if not games and lineups:
                logger.info(f"No games found for date {date}, searching for games by team match...")
                # Get all teams that have lineups
                teams_with_lineups = set(lineups.keys())
                
                # Try to find games that include these teams (check date +/- 1 day)
                from datetime import datetime, timedelta
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    # Check previous day, current day, and next day
                    for day_offset in [-1, 0, 1]:
                        check_date = (date_obj + timedelta(days=day_offset)).strftime('%Y-%m-%d')
                        potential_games = self.game_repository.get_games_by_date(check_date)
                        # Filter games that have teams matching our lineups
                        for game in potential_games:
                            if game['home_team'] in teams_with_lineups or game['away_team'] in teams_with_lineups:
                                games.append(game)
                                logger.info(f"Found matching game {game['game_id']} on {check_date} for lineup date {date}")
                except Exception as e:
                    logger.warning(f"Error searching for games by date range: {e}")
            
            if not games:
                return {
                    "success": False,
                    "message": f"No games found in schedule for date {date} or nearby dates",
                    "games_processed": 0,
                    "lineups_saved": 0
                }
            
            games_processed = 0
            total_lineups_saved = 0
            
            # Associate lineups with games
            for game in games:
                game_id = game['game_id']
                home_team = game['home_team']
                away_team = game['away_team']
                
                # Find lineups for both teams
                team_lineups = {}
                
                if home_team in lineups:
                    team_lineups[home_team] = lineups[home_team]
                
                if away_team in lineups:
                    team_lineups[away_team] = lineups[away_team]
                
                if team_lineups:
                    # Save lineups for this game using depth chart
                    # This will mark players from FantasyNerds as STARTER and others as BENCH
                    saved_count = self._save_lineups_with_depth_chart(
                        game_id=game_id,
                        lineup_date=lineup_date,
                        home_team=home_team,
                        away_team=away_team,
                        team_lineups=team_lineups
                    )
                    total_lineups_saved += saved_count
                    games_processed += 1
                    logger.info(f"Saved {saved_count} lineup entries for game {game_id} (game_date: {game.get('game_date')}, lineup_date: {lineup_date})")
            
            return {
                "success": True,
                "message": f"Successfully imported lineups for {games_processed} games",
                "games_processed": games_processed,
                "lineups_saved": total_lineups_saved,
                "lineup_date": lineup_date
            }
            
        except Exception as e:
            logger.error(f"Error importing lineups: {e}", exc_info=True)
            error_message = str(e)
            # Provide more user-friendly error messages
            if "Empty response" in error_message or "Invalid JSON" in error_message:
                error_message = f"No se pudieron obtener los lineups de FantasyNerds para la fecha {date}. Verifica que la fecha sea correcta y que haya juegos programados."
            elif "404" in error_message or "Not Found" in error_message:
                error_message = f"No se encontraron lineups para la fecha {date}."
            elif "401" in error_message or "403" in error_message or "Unauthorized" in error_message:
                error_message = "Error de autenticación con la API de FantasyNerds. Verifica la configuración de la API key."
            elif "timeout" in error_message.lower():
                error_message = "La solicitud a FantasyNerds tardó demasiado. Intenta nuevamente."
            
            # Try fallback to rosters if we have games
            try:
                games = self.game_repository.get_games_by_date(date)
                if games:
                    logger.info(f"Attempting fallback to NBA API rosters after error...")
                    return self._import_rosters_as_bench_for_date(date, games)
            except Exception as fallback_error:
                logger.error(f"Fallback to rosters also failed: {fallback_error}")
            
            return {
                "success": False,
                "error": str(e),
                "message": error_message
            }
    
    def import_lineups_from_dict(self, lineups_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import lineups from a dictionary (useful for API uploads or testing).
        
        Args:
            lineups_data: Dictionary containing lineup data with structure:
                         {
                             "lineup_date": "2026-01-09",
                             "lineups": {
                                 "LAL": {"PG": {...}, "SG": {...}, ...},
                                 ...
                             }
                         }
            
        Returns:
            Dictionary with import results
        """
        try:
            lineup_date = lineups_data.get('lineup_date')
            if not lineup_date:
                return {
                    "success": False,
                    "message": "lineup_date is required in the data"
                }
            
            # Convert date format if needed
            if len(lineup_date) == 8:  # YYYYMMDD
                lineup_date = f"{lineup_date[:4]}-{lineup_date[4:6]}-{lineup_date[6:8]}"
            
            lineups = lineups_data.get('lineups', {})
            
            if not lineups:
                return {
                    "success": False,
                    "message": "No lineups found in data"
                }
            
            # Get all games for this date from our database
            games = self.game_repository.get_games_by_date(lineup_date)
            
            if not games:
                return {
                    "success": False,
                    "message": f"No games found in schedule for date {lineup_date}",
                    "games_processed": 0,
                    "lineups_saved": 0
                }
            
            games_processed = 0
            total_lineups_saved = 0
            
            # Associate lineups with games
            for game in games:
                game_id = game['game_id']
                home_team = game['home_team']
                away_team = game['away_team']
                
                # Find lineups for both teams
                team_lineups = {}
                
                if home_team in lineups:
                    team_lineups[home_team] = lineups[home_team]
                
                if away_team in lineups:
                    team_lineups[away_team] = lineups[away_team]
                
                if team_lineups:
                    # Save lineups for this game
                    saved_count = self.lineup_repository.save_lineups_for_game(
                        game_id=game_id,
                        lineup_date=lineup_date,
                        team_lineups=team_lineups
                    )
                    total_lineups_saved += saved_count
                    games_processed += 1
            
            return {
                "success": True,
                "message": f"Successfully imported lineups for {games_processed} games",
                "games_processed": games_processed,
                "lineups_saved": total_lineups_saved,
                "lineup_date": lineup_date
            }
            
        except Exception as e:
            logger.error(f"Error importing lineups from dict: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import lineups: {e}"
            }
    
    def get_lineups_by_date(self, date: str, auto_fetch: bool = False) -> List[Dict[str, Any]]:
        """
        Get lineups for a specific date.
        Only returns lineups that are already in the database.
        Does NOT automatically fetch from FantasyNerds or return games from schedule.
        
        Args:
            date: Date in YYYY-MM-DD format
            auto_fetch: If True, automatically fetch from FantasyNerds if not found (default: False)
            
        Returns:
            List of game dictionaries with their lineups (empty if no lineups found)
        """
        # Get lineups from database
        lineups = self.lineup_repository.get_lineups_by_date(date)
        
        # If no lineups found and auto_fetch is enabled, try to fetch from FantasyNerds
        if not lineups and auto_fetch:
            logger.info(f"No lineups found in database for {date}, fetching from FantasyNerds...")
            
            # Fetch and import lineups automatically
            import_result = self.import_lineups_for_date(date)
            
            if import_result.get('success'):
                # Now get the lineups from database
                lineups = self.lineup_repository.get_lineups_by_date(date)
                logger.info(f"Successfully fetched and saved lineups for {date}")
            else:
                logger.warning(f"Failed to fetch lineups from FantasyNerds: {import_result.get('message')}")
        
        # Enrich with OVER/UNDER history if player_stats_service is available
        if lineups:
            lineups = self._enrich_lineups_with_over_under_history(lineups)
        
        return lineups
    
    def get_lineup_by_game_id(self, game_id: str, auto_fetch: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get lineup for a specific game.
        Automatically fetches from FantasyNerds if not in database.
        
        Args:
            game_id: Game identifier
            auto_fetch: If True, automatically fetch from FantasyNerds if not found
            
        Returns:
            Lineup dictionary or None if not found
        """
        # First, try to get from database
        lineup = self.lineup_repository.get_lineup_by_game_id(game_id)
        
        # If not found and auto_fetch is enabled, try to fetch
        if not lineup and auto_fetch:
            # Get game info to know the date
            game = self.game_repository.get_game_by_id(game_id)
            
            if game and game.get('game_date'):
                game_date = str(game['game_date'])
                logger.info(f"Lineup not found for game {game_id}, fetching lineups for date {game_date}...")
                
                # Fetch lineups for that date
                import_result = self.import_lineups_for_date(game_date)
                
                if import_result.get('success'):
                    # Now get the lineup from database
                    lineup = self.lineup_repository.get_lineup_by_game_id(game_id)
                    logger.info(f"Successfully fetched and saved lineup for game {game_id}")
        
        # Enrich with OVER/UNDER history if player_stats_service is available
        if lineup:
            enriched_lineups = self._enrich_lineups_with_over_under_history([lineup])
            if enriched_lineups:
                lineup = enriched_lineups[0]
        
        return lineup
    
    def _import_rosters_as_bench_for_date(self, date: str, games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Import rosters from NBA API for games and save all players as BENCH.
        This is used as a fallback when FantasyNerds lineups are not available.
        
        Args:
            date: Date in YYYY-MM-DD format
            games: List of game dictionaries
            
        Returns:
            Dictionary with import results
        """
        if not self.depth_chart_service:
            return {
                "success": False,
                "message": "Depth chart service not available. Cannot load rosters.",
                "games_processed": 0,
                "lineups_saved": 0
            }
        
        games_processed = 0
        total_players_saved = 0
        errors = []
        
        # Collect all unique teams from all games
        all_teams = set()
        for game in games:
            if game.get('home_team'):
                all_teams.add(game['home_team'])
            if game.get('away_team'):
                all_teams.add(game['away_team'])
        
        # First, ensure rosters are loaded in database for all teams
        # This will skip teams that already have rosters
        logger.info(f"Ensuring rosters are loaded for {len(all_teams)} teams...")
        roster_import_result = self.depth_chart_service.import_rosters_for_teams(list(all_teams))
        
        if not roster_import_result.get('success'):
            logger.warning(f"Failed to import some rosters: {roster_import_result.get('message')}")
            # Continue anyway, we'll try to use what we have
        
        # Now process each game and save rosters as BENCH
        for game in games:
            game_id = game['game_id']
            home_team = game.get('home_team')
            away_team = game.get('away_team')
            
            if not home_team or not away_team:
                logger.warning(f"Game {game_id} missing team information, skipping...")
                continue
            
            game_players_saved = 0
            
            # Process both teams
            for team_abbr in [home_team, away_team]:
                try:
                    # Get roster from database
                    roster_players = self.depth_chart_service.get_players_by_team(team_abbr)
                    
                    if not roster_players:
                        # Try to load from NBA API directly if available
                        logger.info(f"No roster in database for {team_abbr}, attempting to load from NBA API...")
                        if hasattr(self.depth_chart_service, 'nba_api') and self.depth_chart_service.nba_api:
                            from datetime import datetime
                            current_year = datetime.now().year
                            current_month = datetime.now().month
                            if current_month < 10:
                                season = current_year - 1
                            else:
                                season = current_year
                            season_str = f"{season}-{str(season + 1)[2:]}"
                            
                            nba_players = self.depth_chart_service.nba_api.get_team_players(team_abbr, season=season_str)
                            
                            if nba_players:
                                # Convert to roster format
                                roster_players = []
                                for nba_player in nba_players:
                                    roster_players.append({
                                        'player_id': nba_player.get('id'),
                                        'player_name': nba_player.get('full_name', ''),
                                        'player_photo_url': None  # Will be generated by save_bench_player_for_game
                                    })
                                logger.info(f"Loaded {len(roster_players)} players from NBA API for {team_abbr}")
                    
                    if not roster_players:
                        logger.warning(f"Could not load roster for team {team_abbr}, skipping...")
                        errors.append(f"Could not load roster for team {team_abbr}")
                        continue
                    
                    # Delete any existing lineups for this team and game to start fresh
                    self.lineup_repository.delete_lineups_for_team_game(game_id, date, team_abbr)
                    
                    # Save all players as BENCH
                    logger.info(f"Saving {len(roster_players)} players as BENCH for team {team_abbr} in game {game_id}")
                    for player in roster_players:
                        player_id = player.get('player_id', 0)
                        player_name = player.get('player_name', '')
                        
                        if not player_id or not player_name:
                            continue
                        
                        try:
                            self.lineup_repository.save_bench_player_for_game(
                                game_id=game_id,
                                lineup_date=date,
                                team_abbr=team_abbr,
                                player_id=player_id,
                                player_name=player_name,
                                player_photo_url=player.get('player_photo_url')
                            )
                            game_players_saved += 1
                        except Exception as e:
                            logger.error(f"Error saving BENCH player {player_name} for team {team_abbr}: {e}")
                            continue
                    
                except Exception as e:
                    error_msg = f"Error processing roster for team {team_abbr} in game {game_id}: {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    continue
            
            if game_players_saved > 0:
                games_processed += 1
                total_players_saved += game_players_saved
                logger.info(f"Saved {game_players_saved} players as BENCH for game {game_id}")
        
        result = {
            "success": True,
            "message": f"Successfully loaded rosters as BENCH for {games_processed} games ({total_players_saved} players saved). Los lineups se asignarán como STARTER cuando estén disponibles.",
            "games_processed": games_processed,
            "lineups_saved": total_players_saved,
            "lineup_date": date,
            "fallback_used": True
        }
        
        if errors:
            result["errors"] = errors
            result["error_count"] = len(errors)
        
        return result
    
    def _save_lineups_with_depth_chart(self, game_id: str, lineup_date: str,
                                       home_team: str, away_team: str,
                                       team_lineups: Dict[str, Dict[str, Dict[str, Any]]]) -> int:
        """
        Save lineups for a game using NBA API rosters.
        Players from FantasyNerds lineups are matched by name with NBA API rosters and marked as STARTER.
        Other players from NBA API rosters are marked as BENCH.
        
        This ensures we always use official NBA player IDs.
        """
        """
        Save lineups for a game using depth chart.
        Players from FantasyNerds lineups are marked as STARTER.
        Players in depth chart but not in FantasyNerds lineups are marked as BENCH.
        
        Args:
            game_id: Game identifier
            lineup_date: Date of the lineup
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            team_lineups: Dictionary with team lineups from FantasyNerds
        
        Returns:
            Number of players saved
        """
        if not self.depth_chart_service:
            # Fallback to old behavior if depth chart service is not available
            return self.lineup_repository.save_lineups_for_game(
                game_id=game_id,
                lineup_date=lineup_date,
                team_lineups=team_lineups
            )
        
        saved_count = 0
        
        # Process both teams
        for team_abbr in [home_team, away_team]:
            # Helper function to normalize player names (remove accents)
            def normalize_player_name(name: str) -> str:
                """Normalize player name by removing accents and converting to lowercase."""
                if not name:
                    return ""
                normalized = unicodedata.normalize('NFD', name)
                normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
                return normalized.lower().strip()
            
            # Get all players from depth chart (NBA API rosters) for this team
            logger.debug(f"[LINEUP] Looking up roster for team {team_abbr} from database...")
            depth_chart_players = self.depth_chart_service.get_players_by_team(team_abbr)
            
            # Create a map of player names (normalized) to NBA player data for quick lookup
            nba_players_map = {}  # player_name_normalized -> {player_id, player_name, ...}
            if depth_chart_players:
                logger.info(f"[LINEUP] Found {len(depth_chart_players)} players in database for team {team_abbr}")
                for nba_player in depth_chart_players:
                    player_name = nba_player.get('player_name', '')
                    if player_name:
                        nba_players_map[normalize_player_name(player_name)] = nba_player
            else:
                logger.warning(f"[LINEUP] No roster found in database for team {team_abbr}, will use FantasyNerds IDs as fallback")
                logger.debug(f"[LINEUP] This means rosters need to be imported. Check if depth_chart_service has rosters: {self.depth_chart_service.has_depth_charts() if hasattr(self.depth_chart_service, 'has_depth_charts') else 'N/A'}")
            
            # Get lineup from FantasyNerds for this team
            fantasy_lineup = team_lineups.get(team_abbr, {})
            
            if not fantasy_lineup:
                logger.warning(f"[LINEUP] No FantasyNerds lineup found for team {team_abbr}, skipping")
                continue
            
            logger.info(f"[LINEUP] Processing FantasyNerds lineup for {team_abbr}: {list(fantasy_lineup.keys())}")
            
            # First, delete existing lineups for this team and game to start fresh
            self.lineup_repository.delete_lineups_for_team_game(game_id, lineup_date, team_abbr)
            
            # Match FantasyNerds lineup players with NBA API roster by name
            starter_nba_ids = set()  # Track NBA IDs of starters
            starter_players_by_position = {}  # position -> player_data with NBA ID
            
            for position, player_data in fantasy_lineup.items():
                if position in ['PG', 'SG', 'SF', 'PF', 'C']:  # Only actual positions
                    fantasy_player_name = player_data.get('name', '')
                    if not fantasy_player_name:
                        continue
                    
                    # Find matching player in NBA roster by name (normalized)
                    matched_nba_player = nba_players_map.get(normalize_player_name(fantasy_player_name))
                    
                    if matched_nba_player:
                        # Found match - use NBA official ID
                        nba_player_id = matched_nba_player.get('player_id')
                        starter_nba_ids.add(nba_player_id)
                        starter_players_by_position[position] = {
                            'player_id': nba_player_id,  # Official NBA ID
                            'player_name': matched_nba_player.get('player_name', fantasy_player_name),
                            'confirmed': player_data.get('confirmed', '0') == '1' or player_data.get('confirmed', False),
                            'player_photo_url': matched_nba_player.get('player_photo_url')
                        }
                        logger.info(f"[LINEUP] Matched STARTER {fantasy_player_name} with NBA ID {nba_player_id} for {team_abbr}")
                    else:
                        # No match found - log warning but still save with FantasyNerds data
                        logger.warning(f"[LINEUP] Could not find NBA roster match for STARTER {fantasy_player_name} from {team_abbr}")
                        fantasy_player_id = int(player_data.get('playerId', 0))
                        if fantasy_player_id > 0:
                            starter_players_by_position[position] = {
                                'player_id': fantasy_player_id,  # Fallback to FantasyNerds ID
                                'player_name': fantasy_player_name,
                                'confirmed': player_data.get('confirmed', '0') == '1' or player_data.get('confirmed', False)
                            }
            
            # Save players from FantasyNerds lineup as STARTERS in their positions (using NBA IDs when available)
            logger.info(f"[LINEUP] Saving {len(starter_players_by_position)} STARTER players for {team_abbr}")
            for position in ['PG', 'SG', 'SF', 'PF', 'C']:
                if position in starter_players_by_position:
                    starter_data = starter_players_by_position[position]
                    player_id = starter_data['player_id']  # NBA ID if matched, otherwise FantasyNerds ID
                    player_name = starter_data['player_name']
                    confirmed = starter_data['confirmed']
                    player_photo_url = starter_data.get('player_photo_url')
                    
                    logger.debug(f"[LINEUP] Saving STARTER {player_name} (ID: {player_id}) at {position} for {team_abbr}")
                    # Save player as STARTER
                    try:
                        self.lineup_repository.save_lineup_for_game(
                            game_id=game_id,
                            lineup_date=lineup_date,
                            team_abbr=team_abbr,
                            position=position,
                            player_id=player_id,
                            player_name=player_name,
                            confirmed=confirmed,
                            player_status='STARTER',
                            player_photo_url=player_photo_url
                        )
                        saved_count += 1
                        logger.debug(f"[LINEUP] Successfully saved STARTER {player_name} for {team_abbr}")
                    except Exception as e:
                        logger.error(f"[LINEUP] Error saving STARTER {player_name} for {team_abbr} at {position}: {e}", exc_info=True)
                        continue
                else:
                    logger.warning(f"[LINEUP] No player found for position {position} in FantasyNerds lineup for {team_abbr}")
            
            # Then, save players from NBA roster that are NOT in FantasyNerds lineup as BENCH
            # Only do this if we have rosters in the database
            if depth_chart_players:
                for nba_player in depth_chart_players:
                    nba_player_id = nba_player.get('player_id', 0)
                    
                    # Skip if player is already saved as STARTER
                    if nba_player_id in starter_nba_ids:
                        continue
                    
                    player_name = nba_player.get('player_name', '')
                    
                    # Save player from NBA roster as BENCH
                    try:
                        self.lineup_repository.save_bench_player_for_game(
                            game_id=game_id,
                            lineup_date=lineup_date,
                            team_abbr=team_abbr,
                            player_id=nba_player_id,  # Official NBA ID
                            player_name=player_name,
                            player_photo_url=nba_player.get('player_photo_url')
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Error saving BENCH player {player_name} for team {team_abbr}: {e}")
                        continue
            else:
                logger.info(f"[LINEUP] Skipping BENCH players for {team_abbr} - no roster in database")
        
        return saved_count
    
    def _enrich_lineups_with_over_under_history(self, lineups_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich lineup data with OVER/UNDER history for players who have points_line.
        
        Args:
            lineups_data: List of game dictionaries with lineups
            
        Returns:
            List of game dictionaries with enriched lineup data including OVER/UNDER history
        """
        if not self.player_stats_service:
            logger.debug("Player stats service not available, skipping OVER/UNDER history enrichment")
            return lineups_data
        
        logger.info(f"[ENRICH] Enriching {len(lineups_data)} games with OVER/UNDER history")
        
        nba_api = getattr(self.player_stats_service, 'nba_api', None)
        
        for game in lineups_data:
            if 'lineups' not in game:
                continue
            
            # Get team abbreviations from the game
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            
            # Helper function to normalize player names (remove accents)
            def normalize_player_name(name: str) -> str:
                """Normalize player name by removing accents and converting to lowercase."""
                if not name:
                    return ""
                normalized = unicodedata.normalize('NFD', name)
                normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
                return normalized.lower().strip()
            
            # Try to get NBA roster for both teams from database to map names to official IDs
            team_players_map = {}  # player_name_normalized -> nba_id
            if self.depth_chart_service:
                try:
                    for team_abbr in [home_team, away_team]:
                        if team_abbr:
                            # Get players from database (depth charts) instead of API
                            nba_players = self.depth_chart_service.get_players_by_team(team_abbr)
                            for nba_player in nba_players:
                                player_name = nba_player.get('player_name', '')
                                nba_id = nba_player.get('player_id')
                                if player_name and nba_id:
                                    team_players_map[normalize_player_name(player_name)] = nba_id
                    logger.info(f"[ENRICH] Loaded {len(team_players_map)} NBA player IDs from database rosters")
                except Exception as e:
                    logger.warning(f"[ENRICH] Could not load NBA team rosters from database: {e}")
                    # Fallback to API if database fails
                    if nba_api and hasattr(nba_api, 'get_team_players'):
                        try:
                            for team_abbr in [home_team, away_team]:
                                if team_abbr:
                                    nba_players = nba_api.get_team_players(team_abbr)
                                    for nba_player in nba_players:
                                        player_name = nba_player.get('full_name', '')
                                        nba_id = nba_player.get('id')
                                        if player_name and nba_id:
                                            team_players_map[normalize_player_name(player_name)] = nba_id
                            logger.info(f"[ENRICH] Loaded {len(team_players_map)} NBA player IDs from API (fallback)")
                        except Exception as api_error:
                            logger.warning(f"[ENRICH] Could not load NBA team rosters from API either: {api_error}")
            
            for team_abbr, team_lineup in game['lineups'].items():
                # Process starters (positions PG, SG, SF, PF, C)
                for position in ['PG', 'SG', 'SF', 'PF', 'C']:
                    if position in team_lineup:
                        player = team_lineup[position]
                        if player.get('points_line') and player.get('player_id'):
                            player_name = player.get('player_name', 'Unknown')
                            player_id = player.get('player_id')  # FantasyNerds ID
                            
                            # Try to find official NBA ID (using normalized name)
                            official_nba_id = None
                            if player_name:
                                official_nba_id = team_players_map.get(normalize_player_name(player_name))
                                if official_nba_id:
                                    logger.info(f"[ENRICH] Found official NBA ID {official_nba_id} for {player_name} (FantasyNerds ID: {player_id})")
                            
                            # Use official NBA ID if found, otherwise use FantasyNerds ID
                            player_id_to_use = official_nba_id if official_nba_id else player_id
                            
                            logger.info(f"[ENRICH] Processing STARTER {player_name} (Using ID: {player_id_to_use}, Position: {position}, Points Line: {player.get('points_line')})")
                            try:
                                # Use local-only mode to avoid NBA API calls when just loading lineups
                                # Game logs should be loaded separately using the "Cargar Game Logs" button
                                over_under_history = self.player_stats_service.calculate_over_under_history(
                                    player_id=player_id_to_use,
                                    points_line=player['points_line'],
                                    num_games=25,
                                    player_name=player_name,
                                    use_local_only=True,  # Only use local game logs, don't call NBA API
                                    assists_line=player.get('assists_line'),
                                    rebounds_line=player.get('rebounds_line')
                                )
                                # Only assign over_under_history if we have valid game logs (total_games > 0)
                                if over_under_history.get('total_games', 0) > 0:
                                    player['over_under_history'] = over_under_history
                                    logger.info(f"[ENRICH] Successfully calculated OVER/UNDER for {player_name}: {over_under_history.get('over_count')} OVER, {over_under_history.get('under_count')} UNDER")
                                else:
                                    logger.debug(f"[ENRICH] No game logs available for {player_name}, skipping OVER/UNDER history assignment")
                            except Exception as e:
                                logger.warning(f"Could not calculate OVER/UNDER history for player {player_name}: {e}")
                
                # Process BENCH players
                if 'BENCH' in team_lineup:
                    bench_players = team_lineup['BENCH']
                    if isinstance(bench_players, list):
                        for player in bench_players:
                            if player.get('points_line') and player.get('player_id'):
                                player_name = player.get('player_name', 'Unknown')
                                player_id = player.get('player_id')
                                
                                # Try to find official NBA ID (using normalized name)
                                official_nba_id = None
                                if player_name:
                                    official_nba_id = team_players_map.get(normalize_player_name(player_name))
                                    if official_nba_id:
                                        logger.info(f"[ENRICH] Found official NBA ID {official_nba_id} for BENCH player {player_name} (FantasyNerds ID: {player_id})")
                                
                                # Use official NBA ID if found
                                player_id_to_use = official_nba_id if official_nba_id else player_id
                                
                                try:
                                    # Use local-only mode to avoid NBA API calls when just loading lineups
                                    # Game logs should be loaded separately using the "Cargar Game Logs" button
                                    over_under_history = self.player_stats_service.calculate_over_under_history(
                                        player_id=player_id_to_use,
                                        points_line=player['points_line'],
                                        num_games=25,
                                        player_name=player_name,
                                        use_local_only=True,  # Only use local game logs, don't call NBA API
                                        assists_line=player.get('assists_line'),
                                        rebounds_line=player.get('rebounds_line')
                                    )
                                    # Only assign over_under_history if we have valid game logs (total_games > 0)
                                    if over_under_history.get('total_games', 0) > 0:
                                        player['over_under_history'] = over_under_history
                                        logger.debug(f"[ENRICH] Successfully calculated OVER/UNDER for BENCH {player_name}: {over_under_history.get('over_count')} OVER, {over_under_history.get('under_count')} UNDER")
                                    else:
                                        logger.debug(f"[ENRICH] No game logs available for BENCH {player_name}, skipping OVER/UNDER history assignment")
                                except Exception as e:
                                    logger.warning(f"Could not calculate OVER/UNDER history for player {player_name}: {e}")
        
        return lineups_data

