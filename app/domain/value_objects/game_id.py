"""
Game ID value object (stub).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GameId:
    """
    Value object representing a game identifier.
    
    This is a stub for future implementation.
    """
    value: str
    
    def __post_init__(self):
        """Validate game ID."""
        if not self.value:
            raise ValueError("Game ID cannot be empty")



