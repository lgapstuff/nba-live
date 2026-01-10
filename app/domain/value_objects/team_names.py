"""
Team name mappings for NBA teams.
Maps team abbreviations to full team names and logo URLs.
"""
from typing import Dict

# Mapeo completo de abreviaciones de equipos NBA a nombres completos
NBA_TEAM_NAMES: Dict[str, str] = {
    # Eastern Conference
    "ATL": "Atlanta Hawks",
    "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DET": "Detroit Pistons",
    "IND": "Indiana Pacers",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "NY": "New York Knicks",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "TOR": "Toronto Raptors",
    "WAS": "Washington Wizards",
    
    # Western Conference
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "GS": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "LAC": "Los Angeles Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIN": "Minnesota Timberwolves",
    "NO": "New Orleans Pelicans",
    "OKC": "Oklahoma City Thunder",
    "PHO": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SA": "San Antonio Spurs",
    "UTA": "Utah Jazz",
    
    # Variaciones comunes
    "GSW": "Golden State Warriors",  # Alternativa para GS
    "NOP": "New Orleans Pelicans",  # Alternativa para NO
    "PHX": "Phoenix Suns",  # Alternativa para PHO
    "NYK": "New York Knicks",  # Alternativa para NY
}


def get_team_name(abbreviation: str) -> str:
    """
    Get full team name from abbreviation.
    
    Args:
        abbreviation: Team abbreviation (e.g., "LAL", "BOS")
        
    Returns:
        Full team name or the abbreviation if not found
    """
    if not abbreviation:
        return ""
    
    # Normalize to uppercase
    abbrev_upper = abbreviation.upper().strip()
    return NBA_TEAM_NAMES.get(abbrev_upper, abbreviation)


# Mapeo de logos de equipos NBA (URLs públicas de NBA.com CDN)
NBA_TEAM_LOGOS: Dict[str, str] = {
    # Eastern Conference
    "ATL": "https://cdn.nba.com/logos/nba/1610612737/primary/L/logo.svg",
    "BOS": "https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg",
    "BKN": "https://cdn.nba.com/logos/nba/1610612751/primary/L/logo.svg",
    "CHA": "https://cdn.nba.com/logos/nba/1610612766/primary/L/logo.svg",
    "CHI": "https://cdn.nba.com/logos/nba/1610612741/primary/L/logo.svg",
    "CLE": "https://cdn.nba.com/logos/nba/1610612739/primary/L/logo.svg",
    "DET": "https://cdn.nba.com/logos/nba/1610612765/primary/L/logo.svg",
    "IND": "https://cdn.nba.com/logos/nba/1610612754/primary/L/logo.svg",
    "MIA": "https://cdn.nba.com/logos/nba/1610612748/primary/L/logo.svg",
    "MIL": "https://cdn.nba.com/logos/nba/1610612749/primary/L/logo.svg",
    "NY": "https://cdn.nba.com/logos/nba/1610612752/primary/L/logo.svg",
    "ORL": "https://cdn.nba.com/logos/nba/1610612753/primary/L/logo.svg",
    "PHI": "https://cdn.nba.com/logos/nba/1610612755/primary/L/logo.svg",
    "TOR": "https://cdn.nba.com/logos/nba/1610612761/primary/L/logo.svg",
    "WAS": "https://cdn.nba.com/logos/nba/1610612764/primary/L/logo.svg",
    
    # Western Conference
    "DAL": "https://cdn.nba.com/logos/nba/1610612742/primary/L/logo.svg",
    "DEN": "https://cdn.nba.com/logos/nba/1610612743/primary/L/logo.svg",
    "GS": "https://cdn.nba.com/logos/nba/1610612744/primary/L/logo.svg",
    "HOU": "https://cdn.nba.com/logos/nba/1610612745/primary/L/logo.svg",
    "LAC": "https://cdn.nba.com/logos/nba/1610612746/primary/L/logo.svg",
    "LAL": "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
    "MEM": "https://cdn.nba.com/logos/nba/1610612763/primary/L/logo.svg",
    "MIN": "https://cdn.nba.com/logos/nba/1610612750/primary/L/logo.svg",
    "NO": "https://cdn.nba.com/logos/nba/1610612740/primary/L/logo.svg",
    "OKC": "https://cdn.nba.com/logos/nba/1610612760/primary/L/logo.svg",
    "PHO": "https://cdn.nba.com/logos/nba/1610612756/primary/L/logo.svg",
    "POR": "https://cdn.nba.com/logos/nba/1610612757/primary/L/logo.svg",
    "SAC": "https://cdn.nba.com/logos/nba/1610612758/primary/L/logo.svg",
    "SA": "https://cdn.nba.com/logos/nba/1610612759/primary/L/logo.svg",
    "UTA": "https://cdn.nba.com/logos/nba/1610612762/primary/L/logo.svg",
    
    # Variaciones comunes
    "GSW": "https://cdn.nba.com/logos/nba/1610612744/primary/L/logo.svg",
    "NOP": "https://cdn.nba.com/logos/nba/1610612740/primary/L/logo.svg",
    "PHX": "https://cdn.nba.com/logos/nba/1610612756/primary/L/logo.svg",
    "NYK": "https://cdn.nba.com/logos/nba/1610612752/primary/L/logo.svg",
}


def get_team_logo_url(abbreviation: str) -> str:
    """
    Get team logo URL from abbreviation.
    
    Args:
        abbreviation: Team abbreviation (e.g., "LAL", "BOS")
        
    Returns:
        Logo URL or empty string if not found
    """
    if not abbreviation:
        return ""
    
    # Normalize to uppercase
    abbrev_upper = abbreviation.upper().strip()
    return NBA_TEAM_LOGOS.get(abbrev_upper, "")


def get_team_abbreviation(full_name: str) -> str:
    """
    Get team abbreviation from full team name.
    
    Args:
        full_name: Full team name (e.g., "Los Angeles Lakers", "Cleveland Cavaliers")
        
    Returns:
        Team abbreviation or empty string if not found
    """
    if not full_name:
        return ""
    
    # Normalize team name (case insensitive, remove extra spaces)
    normalized_name = " ".join(full_name.strip().split())
    
    # Create reverse mapping
    for abbrev, team_name in NBA_TEAM_NAMES.items():
        if team_name.lower() == normalized_name.lower():
            return abbrev
    
    # Try partial matching for cases like "Los Angeles Lakers" vs "Lakers"
    normalized_lower = normalized_name.lower()
    for abbrev, team_name in NBA_TEAM_NAMES.items():
        team_name_lower = team_name.lower()
        # Check if normalized_name contains key words from team_name
        team_keywords = [word for word in team_name_lower.split() if len(word) > 3]
        if team_keywords and all(keyword in normalized_lower for keyword in team_keywords):
            return abbrev
    
    return ""

