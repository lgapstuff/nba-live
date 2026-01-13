"""
Player photo URL generator for NBA players.
Note: FantasyNerds player_id may not match their photo CDN IDs.
This is a placeholder - you may need to map FantasyNerds player_id to NBA.com player_id
or use a different photo source.
"""
from typing import Optional


def get_player_photo_url(player_id: int, size: str = "medium") -> Optional[str]:
    """
    Get player photo URL. 
    
    Tries multiple sources:
    1. FantasyNerds CDN (for FantasyNerds player IDs)
    2. NBA.com CDN (for NBA player IDs, typically 6-7 digits)
    
    Args:
        player_id: Player ID (could be FantasyNerds or NBA ID)
        size: Photo size - "small", "medium", or "large" (default: "medium")
        
    Returns:
        URL to player photo or None if unavailable
    """
    if not player_id:
        return None
    
    # NBA player IDs are typically 6-7 digits (e.g., 2544, 201939)
    # FantasyNerds IDs are typically smaller (1-4 digits)
    # Try NBA.com first if ID looks like NBA ID (>= 1000)
    if player_id >= 1000:
        # Try NBA.com CDN format
        # Format: https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png
        nba_url = f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png"
        # Note: We return this but the frontend will handle fallback if it fails
        return nba_url
    
    # Try FantasyNerds CDN (for FantasyNerds player IDs)
    # Format: https://www.fantasynerds.com/images/nba/players_{size}/{player_id}.png
    fantasynerds_url = f"https://www.fantasynerds.com/images/nba/players_{size}/{player_id}.png"
    
    return fantasynerds_url


def get_player_photo_url_by_name(player_name: str) -> Optional[str]:
    """
    Alternative: Get player photo URL by name (if available from other sources).
    
    Args:
        player_name: Full player name
        
    Returns:
        URL to player photo or None
    """
    # This would require a name-to-photo mapping service
    # Could use NBA.com search or other APIs
    return None


def get_player_photo_url_small(player_id: int) -> str:
    """
    Get small player photo URL from FantasyNerds.
    
    Args:
        player_id: Player ID from FantasyNerds API
        
    Returns:
        URL to small player photo
    """
    return get_player_photo_url(player_id, "small")


def get_player_photo_url_large(player_id: int) -> str:
    """
    Get large player photo URL from FantasyNerds.
    
    Args:
        player_id: Player ID from FantasyNerds API
        
    Returns:
        URL to large player photo
    """
    return get_player_photo_url(player_id, "large")

