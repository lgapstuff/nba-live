"""
Team abbreviation value object (stub).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TeamAbbr:
    """
    Value object representing a team abbreviation.
    
    This is a stub for future implementation.
    """
    value: str
    
    def __post_init__(self):
        """Validate team abbreviation."""
        if not self.value:
            raise ValueError("Team abbreviation cannot be empty")
        if len(self.value) > 3:
            raise ValueError("Team abbreviation must be 3 characters or less")



