# NBA API - Rosters cURL Commands para Postman

Este documento contiene los comandos cURL para obtener rosters de equipos NBA directamente desde la API de stats.nba.com.

## Endpoint

La API de NBA usa el endpoint `CommonTeamRoster` que está disponible en:
```
https://stats.nba.com/stats/commonteamroster
```

## Parámetros Requeridos

- `TeamID`: ID numérico del equipo (ver tabla abajo)
- `Season`: Temporada en formato "YYYY-YY" (ej: "2024-25")

## Headers Necesarios

La API de NBA requiere headers específicos para evitar bloqueos:

```
Accept: application/json, text/plain, */*
Accept-Language: en-US,en;q=0.9
Origin: https://www.nba.com
Referer: https://www.nba.com/
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

## Mapeo de Team IDs

| Abreviatura | Nombre Completo | Team ID |
|------------|----------------|---------|
| ATL | Atlanta Hawks | 1610612737 |
| BOS | Boston Celtics | 1610612738 |
| BKN | Brooklyn Nets | 1610612751 |
| CHA | Charlotte Hornets | 1610612766 |
| CHI | Chicago Bulls | 1610612741 |
| CLE | Cleveland Cavaliers | 1610612739 |
| DET | Detroit Pistons | 1610612765 |
| IND | Indiana Pacers | 1610612754 |
| MIA | Miami Heat | 1610612748 |
| MIL | Milwaukee Bucks | 1610612749 |
| NY | New York Knicks | 1610612752 |
| ORL | Orlando Magic | 1610612753 |
| PHI | Philadelphia 76ers | 1610612755 |
| TOR | Toronto Raptors | 1610612761 |
| WAS | Washington Wizards | 1610612764 |
| DAL | Dallas Mavericks | 1610612742 |
| DEN | Denver Nuggets | 1610612743 |
| GS | Golden State Warriors | 1610612744 |
| HOU | Houston Rockets | 1610612745 |
| LAC | Los Angeles Clippers | 1610612746 |
| LAL | Los Angeles Lakers | 1610612747 |
| MEM | Memphis Grizzlies | 1610612763 |
| MIN | Minnesota Timberwolves | 1610612750 |
| NO | New Orleans Pelicans | 1610612740 |
| OKC | Oklahoma City Thunder | 1610612760 |
| PHO | Phoenix Suns | 1610612756 |
| POR | Portland Trail Blazers | 1610612757 |
| SAC | Sacramento Kings | 1610612758 |
| SA | San Antonio Spurs | 1610612759 |
| UTA | Utah Jazz | 1610612762 |

## Ejemplos de cURL

### Ejemplo 1: Roster de Los Angeles Lakers (LAL) - Temporada 2024-25

```bash
curl -X GET "https://stats.nba.com/stats/commonteamroster?TeamID=1610612747&Season=2024-25" \
  -H "Accept: application/json, text/plain, */*" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Origin: https://www.nba.com" \
  -H "Referer: https://www.nba.com/" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
```

### Ejemplo 2: Roster de Milwaukee Bucks (MIL) - Temporada 2024-25

```bash
curl -X GET "https://stats.nba.com/stats/commonteamroster?TeamID=1610612749&Season=2024-25" \
  -H "Accept: application/json, text/plain, */*" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Origin: https://www.nba.com" \
  -H "Referer: https://www.nba.com/" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
```

### Ejemplo 3: Roster de Boston Celtics (BOS) - Temporada 2024-25

```bash
curl -X GET "https://stats.nba.com/stats/commonteamroster?TeamID=1610612738&Season=2024-25" \
  -H "Accept: application/json, text/plain, */*" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Origin: https://www.nba.com" \
  -H "Referer: https://www.nba.com/" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
```

## Uso en Postman

### Configuración de la Request

1. **Método**: GET
2. **URL**: `https://stats.nba.com/stats/commonteamroster`
3. **Parámetros (Query Params)**:
   - `TeamID`: [ID del equipo de la tabla arriba]
   - `Season`: `2024-25` (o la temporada que necesites)

4. **Headers**:
   - `Accept`: `application/json, text/plain, */*`
   - `Accept-Language`: `en-US,en;q=0.9`
   - `Origin`: `https://www.nba.com`
   - `Referer`: `https://www.nba.com/`
   - `User-Agent`: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`

### Formato de Respuesta

La respuesta viene en formato JSON con la siguiente estructura:

```json
{
  "resource": "commonteamroster",
  "parameters": {
    "TeamID": 1610612747,
    "Season": "2024-25"
  },
  "resultSets": [
    {
      "name": "CommonTeamRoster",
      "headers": [
        "TeamID",
        "SEASON",
        "LeagueID",
        "PLAYER",
        "NUM",
        "POSITION",
        "HEIGHT",
        "WEIGHT",
        "BIRTH_DATE",
        "AGE",
        "EXP",
        "SCHOOL",
        "PLAYER_ID"
      ],
      "rowSet": [
        [
          1610612747,
          "2024-25",
          "00",
          "LeBron James",
          "23",
          "F",
          "6-9",
          "250",
          "1984-12-30T00:00:00",
          39,
          "21",
          "St. Vincent-St. Mary HS (OH)",
          2544
        ],
        // ... más jugadores
      ]
    },
    {
      "name": "Coaches",
      "headers": [
        "TEAM_ID",
        "SEASON",
        "COACH_ID",
        "FIRST_NAME",
        "LAST_NAME",
        "COACH_NAME",
        "COACH_CODE",
        "IS_ASSISTANT",
        "COACH_TYPE",
        "SCHOOL",
        "SORT_SEQUENCE"
      ],
      "rowSet": [
        // ... información de coaches
      ]
    }
  ]
}
```

## Notas Importantes

1. **Rate Limiting**: La API de NBA puede tener rate limiting. Se recomienda agregar delays entre requests (0.5-1 segundo).

2. **Temporada Actual**: Para obtener la temporada actual automáticamente:
   - Si estamos antes de octubre: temporada anterior (ej: si es enero 2025, usar "2024-25")
   - Si estamos en octubre o después: temporada actual (ej: si es octubre 2024, usar "2024-25")

3. **Timeouts**: La API puede ser lenta. Considera usar timeouts de 30-60 segundos.

4. **CORS**: Si pruebas desde un navegador, puede haber problemas de CORS. Postman no tiene este problema.

## Script Python para Generar Todos los cURLs

Si necesitas generar todos los curls para todos los equipos, puedes usar este script:

```python
teams = {
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

season = "2024-25"

for abbr, team_id in teams.items():
    curl = f'''curl -X GET "https://stats.nba.com/stats/commonteamroster?TeamID={team_id}&Season={season}" \\
  -H "Accept: application/json, text/plain, */*" \\
  -H "Accept-Language: en-US,en;q=0.9" \\
  -H "Origin: https://www.nba.com" \\
  -H "Referer: https://www.nba.com/" \\
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"'''
    print(f"# {abbr}")
    print(curl)
    print()
```

