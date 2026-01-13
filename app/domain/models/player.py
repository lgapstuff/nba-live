"""
Player entity (stub).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    """
    Player entity representing an NBA player.
    
    This is a stub for future implementation.
    """
    player_id: Optional[str] = None
    name: Optional[str] = None
    position: Optional[str] = None
    team: Optional[str] = None



