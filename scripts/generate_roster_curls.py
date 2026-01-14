#!/usr/bin/env python3
"""
Script para generar comandos cURL para obtener rosters de todos los equipos NBA.
Útil para probar en Postman o desde la línea de comandos.
"""

# Mapeo de abreviaciones a Team IDs
TEAMS = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751,
    "CHA": 1610612766, "CHI": 1610612741, "CLE": 1610612739,
    "DET": 1610612765, "IND": 1610612754, "MIA": 1610612748,
    "MIL": 1610612749, "NY": 1610612752, "ORL": 1610612753,
    "PHI": 1610612755, "TOR": 1610612761, "WAS": 1610612764,
    "DAL": 1610612742, "DEN": 1610612743, "GS": 1610612744,
    "HOU": 1610612745, "LAC": 1610612746, "LAL": 1610612747,
    "MEM": 1610612763, "MIN": 1610612750, "NO": 1610612740,
    "OKC": 1610612760, "PHO": 1610612756, "POR": 1610612757,
    "SAC": 1610612758, "SA": 1610612759, "UTA": 1610612762
}

# Nombres completos de equipos
TEAM_NAMES = {
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
    "UTA": "Utah Jazz"
}


def get_current_season():
    """Obtiene la temporada actual en formato YYYY-YY"""
    from datetime import datetime
    current_year = datetime.now().year
    if datetime.now().month < 10:
        # Antes de octubre, usar temporada anterior
        season = f"{current_year - 1}-{str(current_year)[2:]}"
    else:
        # Octubre o después, usar temporada actual
        season = f"{current_year}-{str(current_year + 1)[2:]}"
    return season


def generate_curl(team_abbr, team_id, season):
    """Genera un comando cURL para un equipo específico"""
    url = f"https://stats.nba.com/stats/commonteamroster?TeamID={team_id}&Season={season}"
    team_name = TEAM_NAMES.get(team_abbr, team_abbr)
    
    curl = f'''# {team_abbr} - {team_name}
curl -X GET "{url}" \\
  -H "Accept: application/json, text/plain, */*" \\
  -H "Accept-Language: en-US,en;q=0.9" \\
  -H "Origin: https://www.nba.com" \\
  -H "Referer: https://www.nba.com/" \\
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"'''
    
    return curl


def generate_postman_collection(season):
    """Genera un JSON para importar en Postman"""
    collection = {
        "info": {
            "name": "NBA Rosters API",
            "description": "Collection para obtener rosters de equipos NBA",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": []
    }
    
    for abbr, team_id in sorted(TEAMS.items()):
        team_name = TEAM_NAMES.get(abbr, abbr)
        request = {
            "name": f"{abbr} - {team_name}",
            "request": {
                "method": "GET",
                "header": [
                    {
                        "key": "Accept",
                        "value": "application/json, text/plain, */*"
                    },
                    {
                        "key": "Accept-Language",
                        "value": "en-US,en;q=0.9"
                    },
                    {
                        "key": "Origin",
                        "value": "https://www.nba.com"
                    },
                    {
                        "key": "Referer",
                        "value": "https://www.nba.com/"
                    },
                    {
                        "key": "User-Agent",
                        "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                ],
                "url": {
                    "raw": f"https://stats.nba.com/stats/commonteamroster?TeamID={team_id}&Season={season}",
                    "protocol": "https",
                    "host": ["stats", "nba", "com"],
                    "path": ["stats", "commonteamroster"],
                    "query": [
                        {
                            "key": "TeamID",
                            "value": str(team_id)
                        },
                        {
                            "key": "Season",
                            "value": season
                        }
                    ]
                }
            }
        }
        collection["item"].append(request)
    
    return collection


def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Genera comandos cURL para obtener rosters NBA")
    parser.add_argument("--season", type=str, help="Temporada en formato YYYY-YY (ej: 2024-25). Si no se especifica, usa la temporada actual.")
    parser.add_argument("--team", type=str, help="Abreviatura del equipo (ej: LAL, BOS). Si no se especifica, genera todos.")
    parser.add_argument("--postman", action="store_true", help="Genera un archivo JSON para importar en Postman")
    parser.add_argument("--output", type=str, help="Archivo de salida (solo para --postman)")
    
    args = parser.parse_args()
    
    season = args.season or get_current_season()
    
    if args.postman:
        collection = generate_postman_collection(season)
        output_file = args.output or "nba_rosters_postman_collection.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        print(f"[OK] Coleccion de Postman generada: {output_file}")
        print(f"   Importa este archivo en Postman: File > Import > {output_file}")
        return
    
    if args.team:
        team_abbr = args.team.upper()
        if team_abbr not in TEAMS:
            print(f"[ERROR] Equipo '{team_abbr}' no encontrado")
            print(f"   Equipos disponibles: {', '.join(sorted(TEAMS.keys()))}")
            return
        team_id = TEAMS[team_abbr]
        print(generate_curl(team_abbr, team_id, season))
    else:
        print(f"# Comandos cURL para obtener rosters NBA - Temporada {season}\n")
        print("# Copia y pega estos comandos en tu terminal o Postman\n")
        for abbr, team_id in sorted(TEAMS.items()):
            print(generate_curl(abbr, team_id, season))
            print()


if __name__ == "__main__":
    main()

