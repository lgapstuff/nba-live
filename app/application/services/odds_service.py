"""
Odds service for matching player odds with lineups.
"""
import logging
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher
from datetime import datetime, timedelta

from app.domain.ports.odds_api_port import OddsAPIPort
from app.infrastructure.repositories.lineup_repository import LineupRepository
from app.infrastructure.repositories.game_repository import GameRepository

logger = logging.getLogger(__name__)


class OddsService:
    """
    Service for managing NBA odds operations and matching with lineups.
    """
    
    def __init__(self, 
                 odds_api_port: OddsAPIPort,
                 lineup_repository: LineupRepository,
                 game_repository: GameRepository):
        """
        Initialize the service.
        
        Args:
            odds_api_port: Port for The Odds API integration
            lineup_repository: Repository for lineup operations
            game_repository: Repository for game operations
        """
        self.odds_api = odds_api_port
        self.lineup_repository = lineup_repository
        self.game_repository = game_repository
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
            
            # Get odds from The Odds API
            odds_data = self.odds_api.get_player_points_odds(event_id)
            
            if not odds_data or 'bookmakers' not in odds_data:
                return {
                    "success": False,
                    "message": "No odds data available from The Odds API"
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
                        event_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
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
        
        # Extract all players from lineup if exists
        lineup_players = {}
        if has_lineup:
            for team_abbr, positions in lineup['lineups'].items():
                for position, player_data in positions.items():
                    player_name = player_data.get('player_name', '')
                    if player_name:
                        lineup_players[player_name.lower()] = {
                            'player_name': player_name,
                            'player_id': player_data.get('player_id'),
                            'position': position,
                            'team': team_abbr
                        }
        
        # Get game date for saving players
        game_date = str(game.get('game_date', ''))
        if not game_date:
            game_date = lineup.get('lineup_date', '') if lineup else ''
        
        # Extract unique players from odds (to avoid duplicates)
        odds_players_map = {}
        bookmakers = odds_data.get('bookmakers', [])
        
        for bookmaker in bookmakers:
            markets = bookmaker.get('markets', [])
            for market in markets:
                if market.get('key') == 'player_points':
                    outcomes = market.get('outcomes', [])
                    
                    for outcome in outcomes:
                        player_name_odds = outcome.get('description', '')
                        player_name_lower = player_name_odds.lower()
                        
                        # Store best odds for each player (only Over outcomes to avoid duplicates)
                        if outcome.get('name') == 'Over':
                            if player_name_lower not in odds_players_map:
                                odds_players_map[player_name_lower] = {
                                    'name': player_name_odds,
                                    'odds': []
                                }
                            
                            odds_players_map[player_name_lower]['odds'].append({
                                'bookmaker': bookmaker.get('title', ''),
                                'bookmaker_key': bookmaker.get('key', ''),
                                'over_under': outcome.get('name', ''),
                                'points_line': outcome.get('point'),
                                'odds': outcome.get('price'),
                                'under_odds': None,  # Will be filled from next outcome
                                'last_update': market.get('last_update')
                            })
                        elif outcome.get('name') == 'Under':
                            # Find corresponding Over outcome
                            if player_name_lower in odds_players_map:
                                # Add under odds to the last Over entry
                                if odds_players_map[player_name_lower]['odds']:
                                    odds_players_map[player_name_lower]['odds'][-1]['under_odds'] = outcome.get('price')
        
        # Match or create players
        for player_name_lower, player_odds_data in odds_players_map.items():
            matched_player = self._find_matching_player(player_name_lower, lineup_players) if has_lineup else None
            
            if matched_player:
                # Player exists in lineup - use lineup data
                for odds_entry in player_odds_data['odds']:
                    matched_players.append({
                        'player_name': matched_player['player_name'],
                        'player_id': matched_player['player_id'],
                        'position': matched_player['position'],
                        'team': matched_player['team'],
                        'player_status': 'STARTER',  # From confirmed lineup
                        'bookmaker': odds_entry['bookmaker'],
                        'bookmaker_key': odds_entry['bookmaker_key'],
                        'over_under': odds_entry['over_under'],
                        'points_line': odds_entry['points_line'],
                        'odds': odds_entry['odds'],
                        'under_odds': odds_entry.get('under_odds'),
                        'last_update': odds_entry['last_update']
                    })
            else:
                # Player not in lineup - create entry with BENCH status
                # Use team information from The Odds API response
                player_name = player_odds_data['name']
                
                # Get team names from The Odds API response
                odds_home_team = odds_data.get('home_team', '')
                odds_away_team = odds_data.get('away_team', '')
                
                # Get team abbreviations from our database game
                home_team_abbr = game.get('home_team', '')
                away_team_abbr = game.get('away_team', '')
                
                # Convert The Odds API team names to abbreviations
                from app.domain.value_objects.team_names import get_team_abbreviation
                
                # Try to match The Odds API team names with our abbreviations
                if odds_home_team:
                    odds_home_abbr = get_team_abbreviation(odds_home_team)
                    if not odds_home_abbr:
                        odds_home_abbr = home_team_abbr  # Fallback to game data
                else:
                    odds_home_abbr = home_team_abbr
                
                if odds_away_team:
                    odds_away_abbr = get_team_abbreviation(odds_away_team)
                    if not odds_away_abbr:
                        odds_away_abbr = away_team_abbr  # Fallback to game data
                else:
                    odds_away_abbr = away_team_abbr
                
                # We don't know which team the player belongs to from The Odds API
                # For now, save in home team as default (will be corrected when lineup is confirmed)
                # When the lineup is confirmed, the player will be moved to the correct team and position
                team_abbr = home_team_abbr or away_team_abbr
                
                if not team_abbr:
                    logger.warning(f"Cannot determine team for player {player_name} in game {game_id}")
                    continue
                
                for odds_entry in player_odds_data['odds']:
                    matched_players.append({
                        'player_name': player_name,
                        'player_id': 0,  # Unknown ID from odds
                        'position': 'BENCH',  # No position known
                        'team': team_abbr,
                        'player_status': 'BENCH',
                        'bookmaker': odds_entry['bookmaker'],
                        'bookmaker_key': odds_entry['bookmaker_key'],
                        'over_under': odds_entry['over_under'],
                        'points_line': odds_entry['points_line'],
                        'odds': odds_entry['odds'],
                        'under_odds': odds_entry.get('under_odds'),
                        'last_update': odds_entry['last_update']
                    })
                    
                    # Save to database with BENCH status if no lineup exists
                    # These players will remain BENCH until lineup is confirmed
                    # If they appear in the confirmed lineup, they'll be updated to STARTER with correct team/position
                    if not has_lineup and game_date:
                        try:
                            # Save player with BENCH status (not confirmed, from odds only)
                            # When lineup is loaded later, if this player is in the lineup, 
                            # they'll be updated to STARTER with confirmed=True and correct team/position
                            # If player is not in the confirmed lineup, they'll remain BENCH
                            self.lineup_repository.save_lineup_for_game(
                                game_id=game_id,
                                lineup_date=game_date,
                                team_abbr=team_abbr,
                                position='BENCH',  # Position unknown until lineup is confirmed
                                player_id=0,  # Will need to be updated when lineup is confirmed
                                player_name=player_name,
                                confirmed=False,  # Not confirmed, just from odds
                                player_status='BENCH'  # BENCH until lineup confirms they're STARTER
                            )
                        except Exception as e:
                            logger.warning(f"Could not save BENCH player {player_name} for team {team_abbr}: {e}")
        
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
        # Normalize names (remove special characters, handle apostrophes)
        def normalize_name(name: str) -> str:
            # Remove apostrophes and normalize whitespace
            normalized = name.replace("'", "").replace("'", "").replace("'", "")
            # Remove extra spaces
            normalized = " ".join(normalized.split())
            return normalized
        
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

