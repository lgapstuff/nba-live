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
    
    WARNING: FantasyNerds player_id may not work directly with their photo CDN.
    You may need to:
    1. Check if FantasyNerds API returns photo URL directly
    2. Map FantasyNerds player_id to NBA.com player_id
    3. Use player name to search for photos
    4. Use a different photo API
    
    Args:
        player_id: Player ID from FantasyNerds API
        size: Photo size - "small", "medium", or "large" (default: "medium")
        
    Returns:
        URL to player photo or None if unavailable
    """
    if not player_id:
        return None
    
    # Try FantasyNerds CDN (may not work for all players)
    # Format: https://www.fantasynerds.com/images/nba/players_{size}/{player_id}.png
    fantasynerds_url = f"https://www.fantasynerds.com/images/nba/players_{size}/{player_id}.png"
    
    # Note: This may return placeholder images for some players
    # Consider implementing a mapping service or using NBA.com player IDs
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

