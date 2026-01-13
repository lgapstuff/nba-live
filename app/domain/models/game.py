"""
Game entity (stub).
"""
from dataclasses import dataclass
from typing import Optional

from app.domain.value_objects.game_id import GameId


@dataclass
class Game:
    """
    Game entity representing an NBA game.
    
    This is a stub for future implementation.
    """
    game_id: GameId
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    game_date: Optional[str] = None
    status: Optional[str] = None



