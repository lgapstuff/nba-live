"""
Odds service for matching player odds with lineups.
"""
import json
import logging
import unicodedata
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher
from datetime import datetime, timedelta

from app.domain.ports.odds_api_port import OddsAPIPort
from app.infrastructure.repositories.lineup_repository import LineupRepository
from app.infrastructure.repositories.game_repository import GameRepository
from app.infrastructure.repositories.odds_history_repository import OddsHistoryRepository
from app.application.services.depth_chart_service import DepthChartService
from app.application.services.player_stats_service import PlayerStatsService

logger = logging.getLogger(__name__)


class OddsService:
    """
    Service for managing NBA odds operations and matching with lineups.
    """
    
    def __init__(self, 
                 odds_api_port: OddsAPIPort,
                 lineup_repository: LineupRepository,
                 game_repository: GameRepository,
                 depth_chart_service: DepthChartService = None,
                 player_stats_service: PlayerStatsService = None,
                 odds_history_repository: OddsHistoryRepository = None):
        """
        Initialize the service.
        
        Args:
            odds_api_port: Port for The Odds API integration
            lineup_repository: Repository for lineup operations
            game_repository: Repository for game operations
            depth_chart_service: Service for depth charts (optional, for team matching)
            player_stats_service: Service for player statistics (optional, for OVER/UNDER history)
            odds_history_repository: Repository for odds history (optional)
        """
        self.odds_api = odds_api_port
        self.lineup_repository = lineup_repository
        self.game_repository = game_repository
        self.depth_chart_service = depth_chart_service
        self.player_stats_service = player_stats_service
        self.odds_history_repository = odds_history_repository
        self._cached_events = None
        self._events_cache_time = None
    
    def check_if_game_has_odds(self, game: Dict[str, Any]) -> bool:
        """
        Check if a game has odds available in The Odds API.
        Only returns True if the game is in the future or today.
        
        Args:
            game: Game dictionary from our database
            
        Returns:
            True if odds are available and game hasn't passed, False otherwise
        """
        try:
            # First check if the game date has passed
            game_date = game.get('game_date')
            if game_date:
                try:
                    from datetime import date, timezone
                    
                    # Parse game date - handle different formats
                    game_date_only = None
                    if isinstance(game_date, str):
                        # Try different date formats
                        try:
                            # Format: YYYY-MM-DD
                            if len(game_date) == 10 and game_date.count('-') == 2:
                                parts = game_date.split('-')
                                game_date_only = date(int(parts[0]), int(parts[1]), int(parts[2]))
                            else:
                                # Try ISO format
                                game_date_obj = datetime.fromisoformat(str(game_date).replace('Z', '+00:00'))
                                game_date_only = game_date_obj.date()
                        except (ValueError, AttributeError):
                            # Try parsing as datetime first
                            try:
                                game_date_obj = datetime.fromisoformat(str(game_date).replace('Z', '+00:00'))
                                game_date_only = game_date_obj.date()
                            except:
                                logger.warning(f"Could not parse game date: {game_date}")
                    elif isinstance(game_date, datetime):
                        game_date_only = game_date.date()
                    elif isinstance(game_date, date):
                        game_date_only = game_date
                    
                    if game_date_only:
                        # Get current date
                        now = datetime.now()
                        current_date = now.date()
                        
                        # If game date is in the past, no odds available
                        if game_date_only < current_date:
                            logger.debug(f"Game {game.get('game_id')} date has passed ({game_date_only}), no odds available")
                            return False
                        
                        # If game is today, check the time
                        if game_date_only == current_date:
                            game_time = game.get('game_time')
                            if game_time:
                                try:
                                    if isinstance(game_time, str):
                                        # Parse time string (HH:MM:SS or HH:MM)
                                        time_parts = game_time.split(':')
                                        hour = int(time_parts[0])
                                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                                        second = int(time_parts[2]) if len(time_parts) > 2 else 0
                                        
                                        # Create datetime with today's date and game time
                                        from datetime import time as dt_time
                                        game_time_obj = dt_time(hour, minute, second)
                                        game_datetime = datetime.combine(current_date, game_time_obj)
                                        
                                        # If game time has passed today, no odds available
                                        if game_datetime < now:
                                            logger.debug(f"Game {game.get('game_id')} time has passed today ({game_datetime}), no odds available")
                                            return False
                                except Exception as e:
                                    logger.warning(f"Could not parse game time: {e}")
                except Exception as e:
                    logger.warning(f"Could not parse game date for odds check: {e}")
            
            # Check if event exists in The Odds API
            event_id = self._find_odds_api_event_id(game)
            return event_id is not None
        except Exception as e:
            logger.warning(f"Error checking odds availability: {e}")
            return False
    
    def get_player_points_odds_for_game(self, game_id: str) -> Dict[str, Any]:
        """
        Get player points odds for a game and match them with lineup players.
        
        Args:
            game_id: Game identifier from our database
            
        Returns:
            Dictionary with matched odds for players in the lineup
        """
        try:
            # Get game info to find The Odds API event
            game = self.game_repository.get_game_by_id(game_id)
            if not game:
                logger.error(f"Game {game_id} not found in database")
                return {
                    "success": False,
                    "message": f"Game {game_id} not found"
                }
            
            logger.info(f"Looking for odds for game: {game.get('home_team_name')} vs {game.get('away_team_name')}")
            
            # Get lineup for this game
            lineup = self.lineup_repository.get_lineup_by_game_id(game_id)
            if not lineup:
                logger.warning(f"Lineup not found for game {game_id}, but continuing to fetch odds anyway")
            
            # Find The Odds API event ID by matching teams and date
            event_id = self._find_odds_api_event_id(game)
            
            # Log the event_id that was found for this game
            if event_id:
                logger.info(f"[ODDS] Game {game_id} ({game.get('away_team_name')} @ {game.get('home_team_name')}) - Using event_id: {event_id}")
            else:
                logger.warning(f"[ODDS] Game {game_id} ({game.get('away_team_name')} @ {game.get('home_team_name')}) - No event_id found")
            
            if not event_id:
                # Log more details for debugging
                logger.error(f"Could not find matching event for game {game_id}")
                logger.error(f"Game teams: {game.get('away_team_name')} @ {game.get('home_team_name')}")
                logger.error(f"Game date: {game.get('game_date')}")
                
                # Try to get available events to help with debugging
                try:
                    available_events = self.odds_api.get_events_for_sport()
                    events_summary = [
                        {
                            "id": e.get('id'),
                            "away": e.get('away_team'),
                            "home": e.get('home_team'),
                            "date": e.get('commence_time')
                        }
                        for e in available_events[:5]
                    ]
                    logger.info(f"Sample of available events: {events_summary}")
                except Exception as e:
                    logger.warning(f"Could not fetch available events for debugging: {e}")
                
                return {
                    "success": False,
                    "message": f"Could not find matching event in The Odds API for {game.get('away_team_name', 'Away')} @ {game.get('home_team_name', 'Home')} on {game.get('game_date', 'unknown date')}. The game may not be available in The Odds API yet."
                }
            
            # Get odds from The Odds API (only FanDuel) - try to get points, assists, and rebounds
            # First try with all markets, fallback to just points if that fails
            try:
                odds_data = self.odds_api.get_player_points_odds(
                    event_id, 
                    markets="player_points,player_assists,player_rebounds"
                )
            except Exception as e:
                logger.warning(f"Failed to get all player props, trying just points: {e}")
                odds_data = self.odds_api.get_player_points_odds(event_id, markets="player_points")
            
            # Log the complete odds data received from The Odds API
            if odds_data:
                logger.info(f"[ODDS] Game {game_id} - Event {event_id} - Complete odds response from The Odds API:")
                logger.info(f"[ODDS] Response structure: {json.dumps(odds_data, indent=2, default=str)}")
                
                # Also log a summary
                bookmakers_count = len(odds_data.get('bookmakers', []))
                if bookmakers_count > 0:
                    fanduel = next((b for b in odds_data.get('bookmakers', []) if b.get('key', '').lower() == 'fanduel'), None)
                    if fanduel:
                        player_points_market = next((m for m in fanduel.get('markets', []) if m.get('key') == 'player_points'), None)
                        if player_points_market:
                            outcomes_count = len(player_points_market.get('outcomes', []))
                            logger.info(f"[ODDS] Summary - FanDuel player_points: {outcomes_count} outcomes found")
                        else:
                            logger.warning(f"[ODDS] Summary - FanDuel found but no player_points market")
                    else:
                        logger.warning(f"[ODDS] Summary - FanDuel not found in {bookmakers_count} bookmakers")
                else:
                    logger.warning(f"[ODDS] Summary - No bookmakers in response")
            else:
                logger.warning(f"[ODDS] Game {game_id} - Event {event_id} - Empty odds response from The Odds API")
            
            if not odds_data or 'bookmakers' not in odds_data or not odds_data.get('bookmakers'):
                return {
                    "success": False,
                    "message": "No FanDuel player points odds available from The Odds API for this event"
                }
            
            # Match players from lineup with odds
            # If no lineup exists, create entries with BENCH status
            matched_odds = self._match_players_with_odds(lineup, odds_data, game, game_id)
            
            return {
                "success": True,
                "game_id": game_id,
                "event_id": event_id,
                "matched_players": matched_odds
            }
            
        except Exception as e:
            logger.error(f"Error getting odds for game {game_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get odds: {e}"
            }
    
    def get_game_scores(self, game_id: str) -> Dict[str, Any]:
        """
        Get scores for a specific game from The Odds API.
        
        Args:
            game_id: Game identifier from our database
            
        Returns:
            Dictionary with score information
        """
        try:
            # Get game info to find The Odds API event
            game = self.game_repository.get_game_by_id(game_id)
            if not game:
                logger.error(f"Game {game_id} not found in database")
                return {
                    "success": False,
                    "message": f"Game {game_id} not found"
                }
            
            # Find The Odds API event ID by matching teams and date
            event_id = self._find_odds_api_event_id(game)
            
            # If event_id not found in events, try to find it in scores (for completed games)
            if not event_id:
                logger.info(f"Event ID not found in events list, trying to find in scores for completed games...")
                # Try to get scores without event_id filter to find the game
                try:
                    scores_all = self.odds_api.get_scores(sport="basketball_nba", days_from=3)
                    if scores_all:
                        # Try to find matching event in scores by team names
                        home_team_name = game.get('home_team_name', '').strip()
                        away_team_name = game.get('away_team_name', '').strip()
                        
                        for score_data in scores_all:
                            score_home = score_data.get('home_team', '').strip()
                            score_away = score_data.get('away_team', '').strip()
                            
                            # Check if teams match (normal or swapped)
                            home_match = self._calculate_team_match_score(home_team_name, score_home)
                            away_match = self._calculate_team_match_score(away_team_name, score_away)
                            normal_score = (home_match + away_match) / 2
                            
                            home_match_swapped = self._calculate_team_match_score(home_team_name, score_away)
                            away_match_swapped = self._calculate_team_match_score(away_team_name, score_home)
                            swapped_score = (home_match_swapped + away_match_swapped) / 2
                            
                            match_score = max(normal_score, swapped_score)
                            
                            if match_score >= 0.6:
                                event_id = score_data.get('id')
                                logger.info(f"Found matching event in scores: {event_id} with score {match_score:.2f}")
                                break
                except Exception as e:
                    logger.warning(f"Error searching for event in scores: {e}")
            
            if not event_id:
                logger.warning(f"Could not find matching event for game {game_id}")
                return {
                    "success": False,
                    "message": f"Could not find matching event in The Odds API for {game.get('away_team_name', 'Away')} @ {game.get('home_team_name', 'Home')}"
                }
            
            # Get scores from The Odds API
            # Use days_from=3 to include completed games from the past 3 days
            try:
                scores = self.odds_api.get_scores(sport="basketball_nba", days_from=3, event_ids=event_id)
                if scores:
                    # Find the score for this specific event
                    score_data = next((s for s in scores if s.get('id') == event_id), None)
                    if score_data:
                        # Extract score information
                        home_score = None
                        away_score = None
                        completed = score_data.get('completed', False)
                        last_update = score_data.get('last_update')
                        
                        # Extract scores from the scores array
                        # Scores come as strings in the API response
                        scores_list = score_data.get('scores', [])
                        if scores_list:
                            # Match by team names (home_team and away_team from score_data)
                            home_team_name = score_data.get('home_team', '')
                            away_team_name = score_data.get('away_team', '')
                            
                            for score_entry in scores_list:
                                team_name = score_entry.get('name', '')
                                score_str = score_entry.get('score', '')
                                
                                # Try to convert score to int, handle empty strings
                                try:
                                    score_value = int(score_str) if score_str else None
                                except (ValueError, TypeError):
                                    score_value = None
                                
                                if score_value is not None:
                                    # Match by team name from score_data
                                    if team_name == home_team_name:
                                        home_score = score_value
                                    elif team_name == away_team_name:
                                        away_score = score_value
                        
                        # Update game scores in database
                        self.game_repository.update_game_scores(
                            game_id=game_id,
                            home_score=home_score,
                            away_score=away_score,
                            completed=completed,
                            last_update=last_update
                        )
                        
                        logger.info(f"[SCORES] Updated scores for game {game_id}: {away_score} - {home_score} (Completed: {completed})")
                        
                        return {
                            "success": True,
                            "game_id": game_id,
                            "event_id": event_id,
                            "home_score": home_score,
                            "away_score": away_score,
                            "completed": completed,
                            "last_update": last_update
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"No score data found for event {event_id}"
                        }
                else:
                    return {
                        "success": False,
                        "message": f"No scores available for game {game_id}"
                    }
            except Exception as e:
                logger.error(f"Error fetching scores from The Odds API: {e}")
                return {
                    "success": False,
                    "message": f"Error fetching scores: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error getting scores for game {game_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get scores: {e}"
            }
    
    def _find_odds_api_event_id(self, game: Dict[str, Any]) -> Optional[str]:
        """
        Find The Odds API event ID by matching teams and date.
        
        Args:
            game: Game dictionary from our database
            
        Returns:
            Event ID from The Odds API or None if not found
        """
        try:
            # Get events from The Odds API
            events = self.odds_api.get_events_for_sport()
            
            if not events:
                logger.warning("No events returned from The Odds API")
                return None
            
            home_team_name = game.get('home_team_name', '').strip()
            away_team_name = game.get('away_team_name', '').strip()
            game_date = game.get('game_date')
            
            logger.info(f"Looking for event: {away_team_name} @ {home_team_name} on {game_date}")
            
            # Parse game date if available
            game_date_obj = None
            if game_date:
                try:
                    if isinstance(game_date, str):
                        game_date_obj = datetime.fromisoformat(str(game_date).replace('Z', '+00:00'))
                    elif isinstance(game_date, datetime):
                        game_date_obj = game_date
                except Exception as e:
                    logger.warning(f"Could not parse game date: {e}")
            
            # Try to find matching event
            best_match = None
            best_score = 0
            
            for event in events:
                event_home = event.get('home_team', '').strip()
                event_away = event.get('away_team', '').strip()
                event_id = event.get('id')
                commence_time = event.get('commence_time')
                
                # Check date match if available (but don't skip if date parsing fails)
                date_match = True
                if game_date_obj and commence_time:
                    try:
                        from datetime import timezone
                        event_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                        
                        # Ensure both datetimes are timezone-aware before subtracting
                        if event_date.tzinfo is None:
                            event_date = event_date.replace(tzinfo=timezone.utc)
                        
                        if game_date_obj.tzinfo is None:
                            # If game_date_obj is naive, assume it's in UTC
                            game_date_obj = game_date_obj.replace(tzinfo=timezone.utc)
                        
                        # Allow events within 48 hours (more lenient)
                        time_diff = abs((event_date - game_date_obj).total_seconds())
                        date_match = time_diff < 172800  # 48 hours in seconds
                        if not date_match:
                            logger.debug(f"Skipping event {event_id} - date difference: {time_diff/3600:.1f} hours")
                    except Exception as e:
                        logger.warning(f"Could not parse event date: {e}, continuing anyway")
                        date_match = True  # Don't skip if we can't parse date
                
                if not date_match:
                    continue
                
                # Calculate match score
                home_match = self._calculate_team_match_score(home_team_name, event_home)
                away_match = self._calculate_team_match_score(away_team_name, event_away)
                
                # Also try swapping teams (home/away might be reversed)
                home_match_swapped = self._calculate_team_match_score(home_team_name, event_away)
                away_match_swapped = self._calculate_team_match_score(away_team_name, event_home)
                
                # Get best match score (normal or swapped)
                normal_score = (home_match + away_match) / 2
                swapped_score = (home_match_swapped + away_match_swapped) / 2
                match_score = max(normal_score, swapped_score)
                
                logger.debug(f"Event {event_id}: {event_away} @ {event_home} - Score: {match_score:.2f}")
                
                if match_score > best_score and match_score >= 0.6:  # Lower threshold for better matching
                    best_score = match_score
                    best_match = event_id
            
            if best_match:
                logger.info(f"Found matching event: {best_match} with score {best_score:.2f}")
                return best_match
            else:
                logger.warning(f"No matching event found. Best score: {best_score:.2f}")
                # Log available events for debugging
                available_events_info = [(e.get('id'), e.get('away_team'), e.get('home_team'), e.get('commence_time')) for e in events[:10]]
                logger.warning(f"Available events (first 10): {available_events_info}")
                logger.warning(f"Looking for: {away_team_name} @ {home_team_name} on {game_date}")
                
                # Check if there are any events at all
                if not events:
                    logger.error("No events available from The Odds API")
                elif best_score == 0.0:
                    # No match at all - might be date issue
                    event_dates = [e.get('commence_time', '')[:10] for e in events if e.get('commence_time')]
                    unique_dates = sorted(set(event_dates))
                    logger.warning(f"Game date {game_date} not in available dates: {unique_dates}")
                
                return None
            
        except Exception as e:
            logger.error(f"Error finding event ID: {e}", exc_info=True)
            return None
    
    def _calculate_team_match_score(self, team1: str, team2: str) -> float:
        """
        Calculate match score between two team names (0.0 to 1.0).
        
        Args:
            team1: First team name
            team2: Second team name
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not team1 or not team2:
            return 0.0
        
        team1_lower = team1.lower().strip()
        team2_lower = team2.lower().strip()
        
        # Exact match
        if team1_lower == team2_lower:
            return 1.0
        
        # Remove common suffixes/prefixes for comparison
        def normalize_team_name(name: str) -> str:
            # Remove common words
            words_to_remove = ['the', 'team', 'club']
            words = name.split()
            words = [w for w in words if w not in words_to_remove]
            return ' '.join(words)
        
        team1_normalized = normalize_team_name(team1_lower)
        team2_normalized = normalize_team_name(team2_lower)
        
        # Exact match after normalization
        if team1_normalized == team2_normalized:
            return 0.95
        
        # Check if one contains the other (for cases like "Los Angeles Lakers" vs "Lakers")
        if team1_normalized in team2_normalized or team2_normalized in team1_normalized:
            # Calculate containment score based on length ratio
            shorter = min(len(team1_normalized), len(team2_normalized))
            longer = max(len(team1_normalized), len(team2_normalized))
            if longer > 0:
                containment_score = shorter / longer
                return 0.7 + (containment_score * 0.2)  # Between 0.7 and 0.9
        
        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, team1_lower, team2_lower).ratio()
        
        # Also try normalized similarity
        normalized_similarity = SequenceMatcher(None, team1_normalized, team2_normalized).ratio()
        
        return max(similarity, normalized_similarity)
    
    def _fuzzy_match_team(self, team1: str, team2: str, threshold: float = 0.8) -> bool:
        """
        Fuzzy match team names.
        
        Args:
            team1: First team name
            team2: Second team name
            threshold: Similarity threshold (default: 0.8)
            
        Returns:
            True if teams match
        """
        return self._calculate_team_match_score(team1, team2) >= threshold
    
    def _match_players_with_odds(self, lineup: Optional[Dict[str, Any]], 
                                 odds_data: Dict[str, Any],
                                 game: Dict[str, Any],
                                 game_id: str) -> List[Dict[str, Any]]:
        """
        Match players from lineup with odds from The Odds API.
        If no lineup exists, create entries with BENCH status.
        
        Args:
            lineup: Lineup dictionary with players (can be None)
            odds_data: Odds data from The Odds API
            game: Game dictionary
            game_id: Game identifier
            
        Returns:
            List of matched players with their odds
        """
        matched_players = []
        has_lineup = lineup and 'lineups' in lineup
        
        # Helper function to normalize player names (remove accents)
        def normalize_player_name_for_matching(name: str) -> str:
            """Normalize player name by removing accents and converting to lowercase."""
            if not name:
                return ""
            normalized = unicodedata.normalize('NFD', name)
            normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
            normalized = normalized.replace("'", "").replace("'", "").replace("'", "")
            normalized = " ".join(normalized.split())
            return normalized.lower()
        
        # Extract STARTER players from lineup (only PG, SG, SF, PF, C positions)
        starter_players = {}  # normalized_name -> player_data
        starter_players_by_id = {}  # player_id -> player_data (for ID-based lookup)
        starter_player_ids = set()  # Track player IDs to avoid duplicates
        if has_lineup:
            for team_abbr, positions in lineup['lineups'].items():
                for position, player_data in positions.items():
                    # Only consider actual positions (starters), not BENCH
                    if position in ['PG', 'SG', 'SF', 'PF', 'C']:
                        player_name = player_data.get('player_name', '')
                        player_id = player_data.get('player_id')
                        if player_name:
                            # Store by normalized name for matching
                            normalized_name = normalize_player_name_for_matching(player_name)
                            player_entry = {
                                'player_name': player_name,
                                'player_id': player_id,
                                'position': position,
                                'team': team_abbr,
                                'player_status': 'STARTER'
                            }
                            starter_players[normalized_name] = player_entry
                            # Also track by player ID to catch duplicates with different name spellings
                            if player_id:
                                starter_player_ids.add(player_id)
                                starter_players_by_id[player_id] = player_entry
        
        # Get game date for saving players (use lineup_date if available, otherwise game_date)
        game_date = None
        if lineup and lineup.get('lineup_date'):
            game_date = str(lineup.get('lineup_date'))
        elif game.get('game_date'):
            game_date = str(game.get('game_date'))
        
        if not game_date:
            logger.warning(f"Cannot determine date for saving odds players in game {game_id}")
        
        # Extract unique players from odds (to avoid duplicates)
        # Only process FanDuel bookmaker
        odds_players_map = {}
        bookmakers = odds_data.get('bookmakers', [])
        
        for bookmaker in bookmakers:
            # Only process FanDuel
            if bookmaker.get('key', '').lower() != 'fanduel':
                logger.debug(f"Skipping bookmaker {bookmaker.get('key')} - only processing FanDuel")
                continue
            
            markets = bookmaker.get('markets', [])
            market_keys = [m.get('key') for m in markets]
            logger.info(f"[ODDS] Available markets in FanDuel: {market_keys}")
            
            # First pass: collect all outcomes by player and market
            player_markets_data = {}  # player_name_lower -> {player_points: {...}, player_assists: {...}, player_rebounds: {...}}
            
            for market in markets:
                market_key = market.get('key')
                # Process player_points, player_assists, and player_rebounds markets
                if market_key in ['player_points', 'player_assists', 'player_rebounds']:
                    outcomes = market.get('outcomes', [])
                    
                    for outcome in outcomes:
                        player_name_odds = outcome.get('description', '')
                        player_name_lower = player_name_odds.lower()
                        
                        # Initialize player entry if not exists
                        if player_name_lower not in player_markets_data:
                            player_markets_data[player_name_lower] = {
                                'name': player_name_odds,
                                'player_points': {},
                                'player_assists': {},
                                'player_rebounds': {}
                            }
                        
                        outcome_name = outcome.get('name', '')
                        point_value = outcome.get('point')
                        price_value = outcome.get('price')
                        
                        # Store Over and Under outcomes for each market
                        if outcome_name == 'Over':
                            player_markets_data[player_name_lower][market_key]['over'] = {
                                'point': point_value,
                                'price': price_value
                            }
                        elif outcome_name == 'Under':
                            player_markets_data[player_name_lower][market_key]['under'] = {
                                'point': point_value,
                                'price': price_value
                            }
            
            # Second pass: combine all markets into single odds entries per player
            for player_name_lower, player_data in player_markets_data.items():
                # Create a single odds entry combining all available markets
                odds_entry = {
                    'bookmaker': bookmaker.get('title', ''),
                    'bookmaker_key': bookmaker.get('key', ''),
                    'over_under': 'Over',  # Default to Over for points market
                    'last_update': markets[0].get('last_update') if markets else None
                }
                
                # Add points market data (required)
                # Use the point value from Over outcome (both Over and Under should have the same point value)
                if player_data['player_points'].get('over'):
                    points_line_value = player_data['player_points']['over']['point']
                    odds_entry['points_line'] = points_line_value
                    odds_entry['odds'] = player_data['player_points']['over']['price']
                    if player_data['player_points'].get('under'):
                        odds_entry['under_odds'] = player_data['player_points']['under']['price']
                        # Verify that Over and Under have the same point value (they should)
                        under_point = player_data['player_points']['under']['point']
                        if under_point != points_line_value:
                            logger.warning(f"[ODDS] Point mismatch for {player_data['name']}: Over={points_line_value}, Under={under_point}, using Over value")
                
                # Add assists market data (optional)
                if player_data['player_assists'].get('over'):
                    odds_entry['assists_line'] = player_data['player_assists']['over']['point']
                    odds_entry['assists_odds'] = player_data['player_assists']['over']['price']
                    if player_data['player_assists'].get('under'):
                        odds_entry['assists_under_odds'] = player_data['player_assists']['under']['price']
                
                # Add rebounds market data (optional)
                if player_data['player_rebounds'].get('over'):
                    odds_entry['rebounds_line'] = player_data['player_rebounds']['over']['point']
                    odds_entry['rebounds_odds'] = player_data['player_rebounds']['over']['price']
                    if player_data['player_rebounds'].get('under'):
                        odds_entry['rebounds_under_odds'] = player_data['player_rebounds']['under']['price']
                
                # Only add to odds_players_map if we have at least points_line (required)
                if odds_entry.get('points_line') is not None:
                    if player_name_lower not in odds_players_map:
                        odds_players_map[player_name_lower] = {
                            'name': player_data['name'],
                            'odds': []
                        }
                    odds_players_map[player_name_lower]['odds'].append(odds_entry)
                    logger.info(f"[ODDS] Combined odds for {player_data['name']}: PTS={odds_entry.get('points_line')}, AST={odds_entry.get('assists_line')}, REB={odds_entry.get('rebounds_line')}, Bookmaker={bookmaker.get('key')}")
        
        # Get players for both teams - try database first (depth charts), fallback to NBA API
        home_team_abbr = game.get('home_team', '')
        away_team_abbr = game.get('away_team', '')
        team_players_list = []  # List for matching players from odds
        
        # Try to get players from database first (faster, no API calls)
        nba_players_available = False
        if self.depth_chart_service:
            try:
                logger.info(f"[ODDS] Fetching players from database for teams {home_team_abbr} and {away_team_abbr}")
                home_nba_players = self.depth_chart_service.get_players_by_team(home_team_abbr)
                away_nba_players = self.depth_chart_service.get_players_by_team(away_team_abbr)
                
                # Add players from database with official IDs
                for player in home_nba_players:
                    team_players_list.append({
                        'player_name': player.get('player_name', ''),
                        'player_id': player.get('player_id'),  # Official NBA ID
                        'team': home_team_abbr,
                        'position': player.get('position', ''),
                        'source': 'database'
                    })
                
                for player in away_nba_players:
                    team_players_list.append({
                        'player_name': player.get('player_name', ''),
                        'player_id': player.get('player_id'),  # Official NBA ID
                        'team': away_team_abbr,
                        'position': player.get('position', ''),
                        'source': 'database'
                    })
                
                if team_players_list:
                    nba_players_available = True
                    logger.info(f"[ODDS] Found {len(team_players_list)} players from database")
            except Exception as e:
                logger.warning(f"[ODDS] Could not fetch players from database: {e}, falling back to NBA API")
        
        # Fallback to NBA API if database didn't work
        if not nba_players_available and hasattr(self, 'player_stats_service') and self.player_stats_service:
            nba_api = getattr(self.player_stats_service, 'nba_api', None)
            if nba_api and hasattr(nba_api, 'get_team_players'):
                try:
                    logger.info(f"[ODDS] Fetching players from NBA API for teams {home_team_abbr} and {away_team_abbr}")
                    home_nba_players = nba_api.get_team_players(home_team_abbr)
                    away_nba_players = nba_api.get_team_players(away_team_abbr)
                    
                    # Add NBA API players with official IDs
                    for player in home_nba_players:
                        team_players_list.append({
                            'player_name': player.get('full_name', ''),
                            'player_id': player.get('id'),  # Official NBA ID
                            'team': home_team_abbr,
                            'position': player.get('position', ''),
                            'source': 'nba_api'
                        })
                    
                    for player in away_nba_players:
                        team_players_list.append({
                            'player_name': player.get('full_name', ''),
                            'player_id': player.get('id'),  # Official NBA ID
                            'team': away_team_abbr,
                            'position': player.get('position', ''),
                            'source': 'nba_api'
                        })
                    
                    if team_players_list:
                        nba_players_available = True
                        logger.info(f"[ODDS] Found {len(team_players_list)} players from NBA API")
                except Exception as e:
                    logger.warning(f"[ODDS] Could not fetch players from NBA API: {e}")
        
        # Final fallback to depth charts if both database and API didn't work
        if not nba_players_available and self.depth_chart_service:
            logger.info(f"[ODDS] Using depth charts for teams {home_team_abbr} and {away_team_abbr}")
            # Get all players from both teams' depth charts
            home_players = self.depth_chart_service.get_players_by_team(home_team_abbr)
            away_players = self.depth_chart_service.get_players_by_team(away_team_abbr)
            
            # Add team info to each player
            for player in home_players:
                team_players_list.append({
                    **player,
                    'team': home_team_abbr,
                    'source': 'depth_chart'
                })
            
            for player in away_players:
                team_players_list.append({
                    **player,
                    'team': away_team_abbr,
                    'source': 'depth_chart'
                })
        
        # Match or create players
        for player_name_lower, player_odds_data in odds_players_map.items():
            player_name = player_odds_data['name']
            
            # Normalize the odds player name for matching
            normalized_odds_name = normalize_player_name_for_matching(player_name)
            
            # First, check if player is in starters by normalized name
            matched_starter = starter_players.get(normalized_odds_name)
            
            # If not found by name, try to find by player_id if we have it from team_players_list
            if not matched_starter:
                # Try to find the player in team_players_list to get their ID
                team_player = self._find_matching_player_in_list(player_name, team_players_list)
                if team_player and team_player.get('player_id'):
                    player_id = team_player.get('player_id')
                    # Check if this player_id is already a STARTER
                    if player_id in starter_players_by_id:
                        matched_starter = starter_players_by_id[player_id]
                        logger.info(f"[ODDS] Matched {player_name} to STARTER {matched_starter['player_name']} by player_id {player_id}")
            
            if matched_starter:
                # Player is a STARTER - but we need to find their official NBA ID
                # Try to find the player in team_players_list to get official NBA ID
                team_player = self._find_matching_player_in_list(player_name, team_players_list)
                
                # Use official NBA ID if found, otherwise use FantasyNerds ID
                official_nba_id = None
                if team_player and team_player.get('player_id'):
                    official_nba_id = team_player.get('player_id')
                    logger.info(f"[ODDS] Found official NBA ID {official_nba_id} for STARTER {player_name} (FantasyNerds ID was {matched_starter['player_id']})")
                else:
                    # Try to find NBA ID by name if not in team roster
                    if hasattr(self, 'player_stats_service') and self.player_stats_service:
                        nba_api = getattr(self.player_stats_service, 'nba_api', None)
                        if nba_api and hasattr(nba_api, 'find_nba_player_id_by_name'):
                            try:
                                official_nba_id = nba_api.find_nba_player_id_by_name(player_name)
                                if official_nba_id:
                                    logger.info(f"[ODDS] Found official NBA ID {official_nba_id} for STARTER {player_name} by name search")
                            except Exception as e:
                                logger.warning(f"[ODDS] Could not find NBA ID for STARTER {player_name}: {e}")
                
                # Use official NBA ID if found, otherwise fallback to FantasyNerds ID
                player_id_to_use = official_nba_id if official_nba_id else matched_starter['player_id']
                
                # Update points_line, assists_line, rebounds_line in database for this STARTER player
                if game_date and player_odds_data['odds']:
                    try:
                        # Use the first odds entry (should only be one from FanDuel)
                        # If there are multiple entries, log a warning
                        if len(player_odds_data['odds']) > 1:
                            logger.warning(f"[ODDS] Multiple odds entries found for {matched_starter['player_name']}: {len(player_odds_data['odds'])} entries. Using first one.")
                            for idx, entry in enumerate(player_odds_data['odds']):
                                logger.warning(f"[ODDS] Entry {idx}: PTS={entry.get('points_line')}, Bookmaker={entry.get('bookmaker_key')}")
                        
                        first_odds_entry = player_odds_data['odds'][0]
                        points_line = first_odds_entry.get('points_line')
                        assists_line = first_odds_entry.get('assists_line')
                        rebounds_line = first_odds_entry.get('rebounds_line')
                        over_odds = first_odds_entry.get('odds')
                        under_odds = first_odds_entry.get('under_odds')
                        bookmaker = first_odds_entry.get('bookmaker')
                        
                        # Calculate OVER/UNDER history using official NBA ID (only if local game logs available)
                        # This must be done BEFORE updating the database
                        over_under_history = None
                        if self.player_stats_service and points_line and player_id_to_use:
                            try:
                                logger.debug(f"[ODDS] Calculating OVER/UNDER for STARTER {matched_starter['player_name']} using NBA ID {player_id_to_use} (local-only)")
                                # Use local-only mode to avoid NBA API calls during odds loading
                                over_under_history = self.player_stats_service.calculate_over_under_history(
                                    player_id=player_id_to_use,
                                    points_line=points_line,
                                    num_games=25,
                                    player_name=matched_starter['player_name'],
                                    use_local_only=True,  # Only use local game logs, no NBA API calls
                                    assists_line=assists_line,
                                    rebounds_line=rebounds_line
                                )
                                if over_under_history.get('total_games', 0) > 0:
                                    logger.debug(f"OVER/UNDER history for {matched_starter['player_name']}: {over_under_history.get('over_count')} OVER, {over_under_history.get('under_count')} UNDER")
                                else:
                                    logger.debug(f"No local game logs available for {matched_starter['player_name']}, skipping OVER/UNDER calculation")
                                    over_under_history = None  # Don't include if no games
                            except Exception as e:
                                logger.warning(f"Could not calculate OVER/UNDER history for player {matched_starter['player_name']}: {e}")
                        
                        # Log the values being saved for debugging
                        logger.info(f"[ODDS] Updating lines for STARTER {matched_starter['player_name']} (ID: {matched_starter['player_id']}): PTS={points_line}, AST={assists_line}, REB={rebounds_line}, Bookmaker={bookmaker}")
                        
                        self.lineup_repository.update_points_line_for_player(
                            game_id=game_id,
                            lineup_date=game_date,
                            team_abbr=matched_starter['team'],
                            player_id=matched_starter['player_id'],  # Keep FantasyNerds ID in DB for reference
                            points_line=points_line,
                            assists_line=assists_line,
                            rebounds_line=rebounds_line,
                            over_under_history=over_under_history
                        )
                        
                        # Save odds history (only if changed)
                        if self.odds_history_repository and points_line:
                            try:
                                saved = self.odds_history_repository.save_odds_history(
                                    player_id=matched_starter['player_id'],
                                    player_name=matched_starter['player_name'],
                                    game_id=game_id,
                                    game_date=game_date,
                                    team_abbr=matched_starter['team'],
                                    points_line=points_line,
                                    assists_line=assists_line,
                                    rebounds_line=rebounds_line,
                                    over_odds=over_odds,
                                    under_odds=under_odds,
                                    bookmaker=bookmaker
                                )
                                if saved:
                                    logger.debug(f"Saved odds history for STARTER player {matched_starter['player_name']}")
                            except Exception as e:
                                logger.warning(f"Could not save odds history for STARTER player {matched_starter['player_name']}: {e}")
                    except Exception as e:
                        logger.warning(f"Could not update points_line for STARTER player {matched_starter['player_name']}: {e}")
                
                for odds_entry in player_odds_data['odds']:
                    player_data = {
                        'player_name': matched_starter['player_name'],
                        'player_id': matched_starter['player_id'],
                        'position': matched_starter['position'],
                        'team': matched_starter['team'],
                        'player_status': 'STARTER',
                        'bookmaker': odds_entry['bookmaker'],
                        'bookmaker_key': odds_entry['bookmaker_key'],
                        'over_under': odds_entry['over_under'],
                        'points_line': odds_entry['points_line'],
                        'assists_line': odds_entry.get('assists_line'),
                        'rebounds_line': odds_entry.get('rebounds_line'),
                        'odds': odds_entry['odds'],
                        'under_odds': odds_entry.get('under_odds'),
                        'last_update': odds_entry['last_update']
                    }
                    
                    # Add OVER/UNDER history if available
                    if over_under_history:
                        player_data['over_under_history'] = over_under_history
                    
                    matched_players.append(player_data)
            else:
                # Player is NOT in starters - check team players (NBA API or depth chart) with fuzzy matching
                team_player = self._find_matching_player_in_list(player_name, team_players_list)
                
                if team_player:
                    # Player found in team roster (NBA API or depth chart)
                    team_abbr = team_player['team']
                    player_id = team_player.get('player_id', 0)
                    player_position = team_player.get('position', 'BENCH')
                    player_source = team_player.get('source', 'unknown')
                    
                    # Check if this player is already a STARTER by player ID (to catch duplicates with different name spellings)
                    if player_id and player_id in starter_player_ids:
                        logger.info(f"[ODDS] Skipping {player_name} (NBA ID: {player_id}) - already exists as STARTER")
                        continue
                    
                    # It's a BENCH player (not in starters and not already a starter by ID)
                    logger.info(f"[ODDS] Matched {player_name} from odds with {team_player.get('player_name', player_name)} from {player_source} (NBA ID: {player_id}, Team: {team_abbr})")
                    
                    # Calculate OVER/UNDER history if player_stats_service is available (only if local game logs available)
                    over_under_history = None
                    if self.player_stats_service and player_odds_data['odds']:
                        try:
                            first_odds_entry = player_odds_data['odds'][0]
                            points_line = first_odds_entry.get('points_line')
                            
                            if points_line and player_id:
                                logger.debug(f"[ODDS] Calculating OVER/UNDER for BENCH {player_name} using NBA ID {player_id} (local-only)")
                                # Use local-only mode to avoid NBA API calls during odds loading
                                over_under_history = self.player_stats_service.calculate_over_under_history(
                                    player_id=player_id,
                                    points_line=points_line,
                                    num_games=25,
                                    player_name=player_name,
                                    use_local_only=True  # Only use local game logs, no NBA API calls
                                )
                                if over_under_history.get('total_games', 0) > 0:
                                    logger.debug(f"OVER/UNDER history for {player_name}: {over_under_history.get('over_count')} OVER, {over_under_history.get('under_count')} UNDER")
                                else:
                                    logger.debug(f"No local game logs available for {player_name}, skipping OVER/UNDER calculation")
                                    over_under_history = None  # Don't include if no games
                        except Exception as e:
                            logger.warning(f"Could not calculate OVER/UNDER history for player {player_name}: {e}")
                    
                    for odds_entry in player_odds_data['odds']:
                        player_data = {
                            'player_name': player_name,
                            'player_id': player_id,
                            'position': player_position,
                            'team': team_abbr,
                            'player_status': 'BENCH',  # BENCH because not in starters
                            'bookmaker': odds_entry['bookmaker'],
                            'bookmaker_key': odds_entry['bookmaker_key'],
                            'over_under': odds_entry['over_under'],
                            'points_line': odds_entry['points_line'],
                            'assists_line': odds_entry.get('assists_line'),
                            'rebounds_line': odds_entry.get('rebounds_line'),
                            'odds': odds_entry['odds'],
                            'under_odds': odds_entry.get('under_odds'),
                            'last_update': odds_entry['last_update']
                        }
                        
                        # Add OVER/UNDER history if available
                        if over_under_history:
                            player_data['over_under_history'] = over_under_history
                        
                        matched_players.append(player_data)
                    
                    # Save player as BENCH in database with points_line, assists_line, rebounds_line from first odds entry
                    if game_date and player_odds_data['odds']:
                        try:
                            first_odds_entry = player_odds_data['odds'][0]
                            points_line = first_odds_entry.get('points_line')
                            assists_line = first_odds_entry.get('assists_line')
                            rebounds_line = first_odds_entry.get('rebounds_line')
                            over_odds = first_odds_entry.get('odds')
                            under_odds = first_odds_entry.get('under_odds')
                            bookmaker = first_odds_entry.get('bookmaker')
                            
                            # Only save if we have at least points_line
                            if points_line is not None:
                                self.lineup_repository.save_bench_player_for_game(
                                    game_id=game_id,
                                    lineup_date=game_date,
                                    team_abbr=team_abbr,
                                    player_id=player_id,
                                    player_name=player_name,
                                    player_photo_url=team_player.get('player_photo_url'),
                                    points_line=points_line,
                                    assists_line=assists_line,
                                    rebounds_line=rebounds_line,
                                    over_under_history=over_under_history
                                )
                            
                            # Save odds history (only if changed)
                            if self.odds_history_repository and points_line:
                                try:
                                    saved = self.odds_history_repository.save_odds_history(
                                        player_id=player_id,
                                        player_name=player_name,
                                        game_id=game_id,
                                        game_date=game_date,
                                        team_abbr=team_abbr,
                                        points_line=points_line,
                                        assists_line=assists_line,
                                        rebounds_line=rebounds_line,
                                        over_odds=over_odds,
                                        under_odds=under_odds,
                                        bookmaker=bookmaker
                                    )
                                    if saved:
                                        logger.debug(f"Saved odds history for BENCH player {player_name}")
                                except Exception as e:
                                    logger.warning(f"Could not save odds history for BENCH player {player_name}: {e}")
                        except Exception as e:
                            logger.warning(f"Could not save BENCH player {player_name} for team {team_abbr}: {e}")
                else:
                    # Player not found in team roster (NBA API or depth chart) - skip (can't determine team)
                    logger.warning(f"Player {player_name} from odds not found in team rosters (NBA API or depth charts) for game {game_id}")
                    continue
        
        return matched_players
    
    def _find_matching_player(self, odds_player_name: str, 
                             lineup_players: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Find matching player in lineup by name.
        
        Args:
            odds_player_name: Player name from odds (lowercase)
            lineup_players: Dictionary of lineup players keyed by lowercase name
            
        Returns:
            Matched player dictionary or None
        """
        # Normalize names (remove special characters, handle apostrophes, remove accents)
        def normalize_name(name: str) -> str:
            if not name:
                return ""
            # Remove accents and special characters (e.g., č -> c, é -> e)
            normalized = unicodedata.normalize('NFD', name)
            normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
            # Remove apostrophes and normalize whitespace
            normalized = normalized.replace("'", "").replace("'", "").replace("'", "")
            # Remove extra spaces and convert to lowercase for comparison
            normalized = " ".join(normalized.split())
            return normalized.lower()
        
        normalized_odds_name = normalize_name(odds_player_name)
        
        # Direct match (exact)
        if odds_player_name in lineup_players:
            return lineup_players[odds_player_name]
        
        # Direct match (normalized)
        for lineup_name, player_data in lineup_players.items():
            normalized_lineup_name = normalize_name(lineup_name)
            if normalized_odds_name == normalized_lineup_name:
                return player_data
        
        # Fuzzy match
        best_match = None
        best_similarity = 0.0
        
        for lineup_name, player_data in lineup_players.items():
            normalized_lineup_name = normalize_name(lineup_name)
            
            # Compare normalized names
            similarity = SequenceMatcher(None, normalized_odds_name, normalized_lineup_name).ratio()
            
            # Also check if names contain each other (for nicknames, etc.)
            if normalized_odds_name in normalized_lineup_name or normalized_lineup_name in normalized_odds_name:
                similarity = max(similarity, 0.85)
            
            # Also compare original names
            original_similarity = SequenceMatcher(None, odds_player_name, lineup_name).ratio()
            similarity = max(similarity, original_similarity)
            
            if similarity > best_similarity and similarity >= 0.75:
                best_similarity = similarity
                best_match = player_data
        
        return best_match
    
    def _find_matching_player_in_list(self, player_name: str, players_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find matching player in a list of players by name.
        Used to match players from odds with depth chart players.
        
        Args:
            player_name: Player name from odds
            players_list: List of player dictionaries from depth chart
        
        Returns:
            Matched player dictionary or None
        """
        if not players_list:
            return None
        
        # Normalize name (remove accents and special characters)
        def normalize_name(name: str) -> str:
            if not name:
                return ""
            # Remove accents and special characters (e.g., č -> c, é -> e)
            normalized = unicodedata.normalize('NFD', name)
            normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
            # Remove apostrophes and normalize whitespace
            normalized = normalized.replace("'", "").replace("'", "").replace("'", "")
            # Remove extra spaces and convert to lowercase for comparison
            normalized = " ".join(normalized.split())
            return normalized.lower()
        
        player_name_normalized = normalize_name(player_name)
        
        # Create dictionaries keyed by both original and normalized names for quick lookup
        players_by_name = {p['player_name'].lower().strip(): p for p in players_list}
        players_by_normalized = {normalize_name(p['player_name']): p for p in players_list}
        
        # Direct match (original)
        player_name_lower = player_name.lower().strip()
        if player_name_lower in players_by_name:
            return players_by_name[player_name_lower]
        
        # Direct match (normalized)
        if player_name_normalized in players_by_normalized:
            return players_by_normalized[player_name_normalized]
        
        # Fuzzy match using normalized names
        best_match = None
        best_similarity = 0.0
        
        for player in players_list:
            lineup_name = player['player_name']
            lineup_name_normalized = normalize_name(lineup_name)
            lineup_name_lower = lineup_name.lower().strip()
            
            # Compare normalized names
            normalized_similarity = SequenceMatcher(None, player_name_normalized, lineup_name_normalized).ratio()
            
            # Also compare original names
            original_similarity = SequenceMatcher(None, player_name_lower, lineup_name_lower).ratio()
            
            # Use the best similarity
            similarity = max(normalized_similarity, original_similarity)
            
            # Also check if names contain each other (for nicknames, etc.)
            if player_name_normalized in lineup_name_normalized or lineup_name_normalized in player_name_normalized:
                similarity = max(similarity, 0.85)
            
            if similarity > best_similarity and similarity >= 0.75:
                best_similarity = similarity
                best_match = player
        
        return best_match
    
    def import_odds_for_date(self, date: str) -> Dict[str, Any]:
        """
        Import odds for all games of a specific date.
        Players found in odds are saved as BENCH if not in lineup,
        or remain as STARTER if they're already in the lineup.
        
        Requires depth charts to be loaded first to match players with teams.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with import results
        """
        try:
            # Check if depth charts exist
            if not self.depth_chart_service or not self.depth_chart_service.has_depth_charts():
                return {
                    "success": False,
                    "message": "Depth charts must be loaded before importing odds. Please load depth charts first.",
                    "games_processed": 0,
                    "players_saved": 0
                }
            
            # Get all games for this date
            games = self.game_repository.get_games_by_date(date)
            
            if not games:
                return {
                    "success": False,
                    "message": f"No games found for date {date}",
                    "games_processed": 0,
                    "players_saved": 0
                }
            
            games_processed = 0
            total_players_saved = 0
            errors = []
            
            for game in games:
                game_id = game['game_id']
                try:
                    # Get odds for this game
                    result = self.get_player_points_odds_for_game(game_id)
                    
                    if result.get('success') and result.get('matched_players'):
                        matched_players = result['matched_players']
                        
                        # Count players saved (only BENCH players are saved here)
                        # STARTER players are already in the lineup and don't need to be saved again
                        bench_players_count = sum(1 for p in matched_players if p.get('player_status') == 'BENCH')
                        total_players_saved += bench_players_count
                        games_processed += 1
                        logger.info(f"Processed odds for game {game_id}: {len(matched_players)} players found, {bench_players_count} saved as BENCH")
                    else:
                        logger.debug(f"No odds found for game {game_id}: {result.get('message', 'Unknown error')}")
                        
                except Exception as e:
                    error_msg = f"Error processing game {game_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            result = {
                "success": True,
                "message": f"Successfully imported odds for {games_processed} games",
                "games_processed": games_processed,
                "total_games": len(games),
                "players_saved": total_players_saved
            }
            
            if errors:
                result["errors"] = errors
                result["error_count"] = len(errors)
            
            return result
            
        except Exception as e:
            logger.error(f"Error importing odds for date {date}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import odds: {e}"
            }

