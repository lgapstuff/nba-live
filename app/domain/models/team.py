"""
Team entity (stub).
"""
from dataclasses import dataclass
from typing import Optional

from app.domain.value_objects.team_abbr import TeamAbbr


@dataclass
class Team:
    """
    Team entity representing an NBA team.
    
    This is a stub for future implementation.
    """
    team_abbr: TeamAbbr
    team_name: Optional[str] = None
    city: Optional[str] = None



