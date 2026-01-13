"""
Domain-specific exceptions.
"""


class DomainException(Exception):
    """Base exception for domain layer."""
    pass


class GameNotFoundException(DomainException):
    """Raised when a game is not found."""
    pass


class InvalidGameIdException(DomainException):
    """Raised when a game ID is invalid."""
    pass


class TeamNotFoundException(DomainException):
    """Raised when a team is not found."""
    pass




