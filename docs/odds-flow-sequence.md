# Diagrama de Secuencia: Flujo "Cargar Odds"

```mermaid
sequenceDiagram
    participant User as Usuario
    participant Frontend as Frontend app.js
    participant Backend as Backend API
    participant OddsController as OddsController
    participant OddsService as OddsService
    participant GameRepo as GameRepository
    participant LineupRepo as LineupRepository
    participant OddsAPI as The Odds API
    participant NBAClient as NBA API Client
    participant PlayerStats as PlayerStatsService
    participant DB as Base de Datos

    User->>Frontend: Click "Cargar Odds"
    
    Note over Frontend: Verificar Depth Charts
    Frontend->>Backend: GET /nba/depth-charts/check
    Backend-->>Frontend: {has_depth_charts: true}
    
    Note over Frontend: Obtener Odds del Juego
    Frontend->>Backend: GET /nba/games/{game_id}/odds
    Backend->>OddsController: get_player_points_odds_game_id
    
    Note over OddsController: 1. Obtener Info del Juego
    OddsController->>OddsService: get_player_points_odds_for_game_game_id
    OddsService->>GameRepo: get_game_by_id_game_id
    GameRepo->>DB: SELECT * FROM games WHERE game_id = ?
    DB-->>GameRepo: {home_team, away_team, game_date, ...}
    GameRepo-->>OddsService: Game data
    
    Note over OddsService: 2. Obtener Lineup Actual
    OddsService->>LineupRepo: get_lineup_by_game_id_game_id
    LineupRepo->>DB: SELECT * FROM game_lineups WHERE game_id = ?
    DB-->>LineupRepo: {STARTERS: [...], BENCH: [...]}
    LineupRepo-->>OddsService: Lineup data o null
    
    Note over OddsService: 3. Buscar Event ID en The Odds API
    OddsService->>OddsAPI: GET /v4/sports/basketball_nba/events
    Note right of OddsAPI: Retorna lista de eventos<br/>con: id, home_team, away_team,<br/>commence_time
    OddsAPI-->>OddsService: [{id, home_team, away_team, ...}, ...]
    
    Note over OddsService: Matching por nombre de equipos y fecha
    OddsService->>OddsService: _find_odds_api_event_id_game
    Note right of OddsService: Compara nombres de equipos<br/>y fechas para encontrar<br/>el event_id correcto
    
    Note over OddsService: 4. Obtener Odds de Jugadores
    OddsService->>OddsAPI: GET /v4/sports/basketball_nba/events/{event_id}/odds?markets=player_points&regions=us
    Note right of OddsAPI: Retorna odds de FanDuel<br/>con: player_name, points_line,<br/>over_odds, under_odds
    OddsAPI-->>OddsService: {bookmakers: [{key: 'fanduel', markets: [{key: 'player_points', outcomes: [...]}]}]}
    
    Note over OddsService: 5. Obtener Rosters de NBA API
    OddsService->>NBAClient: get_team_players_home_team_abbr
    NBAClient->>NBAClient: get_team_name_team_abbr
    NBAClient->>NBAClient: teams.get_teams buscar team_id
    NBAClient->>NBAClient: CommonTeamRoster_team_id, season
    Note right of NBAClient: Llama a stats.nba.com<br/>para obtener roster completo
    NBAClient-->>OddsService: [{id: NBA_ID, full_name, position, ...}, ...]
    
    OddsService->>NBAClient: get_team_players_away_team_abbr
    NBAClient-->>OddsService: [{id: NBA_ID, full_name, position, ...}, ...]
    
    Note over OddsService: 6. Matching de Jugadores
    OddsService->>OddsService: _match_players_with_odds
    
    loop Para cada jugador en las odds
        alt Jugador está en STARTERS
            Note over OddsService: Actualizar points_line<br/>para jugador STARTER
            OddsService->>LineupRepo: update_points_line_for_player_game_id, player_id, points_line
            LineupRepo->>DB: UPDATE game_lineups SET points_line = ? WHERE ...
            DB-->>LineupRepo: OK
            
            Note over OddsService: Calcular OVER/UNDER History
            OddsService->>PlayerStats: calculate_over_under_history_nba_player_id, points_line
            PlayerStats->>NBAClient: get_player_last_n_games_nba_player_id, n=10
            NBAClient->>NBAClient: PlayerGameLog_player_id, season
            Note right of NBAClient: Llama a stats.nba.com<br/>para obtener game log
            NBAClient-->>PlayerStats: [{GAME_DATE, PTS, MATCHUP, ...}, ...]
            PlayerStats->>PlayerStats: Compara PTS vs points_line<br/>en últimos 10 juegos
            PlayerStats-->>OddsService: {over_count, under_count, total_games, ...}
            
        else Jugador NO está en STARTERS
            Note over OddsService: Buscar en rosters NBA por nombre
            OddsService->>OddsService: _find_matching_player_in_list_player_name, nba_rosters
            
            alt Jugador encontrado en roster NBA
                Note over OddsService: Guardar como BENCH<br/>con ID oficial NBA
                OddsService->>PlayerStats: calculate_over_under_history_nba_player_id, points_line
                PlayerStats->>NBAClient: get_player_last_n_games_nba_player_id, n=10
                NBAClient-->>PlayerStats: Game log data
                PlayerStats-->>OddsService: OVER/UNDER history
                
                OddsService->>LineupRepo: save_bench_player_for_game_game_id, nba_player_id, player_name, points_line
                LineupRepo->>DB: INSERT INTO game_lineups position='BENCH-{id}', player_id=NBA_ID, points_line, ...
                DB-->>LineupRepo: OK
            else Jugador NO encontrado
                Note over OddsService: Skip - no se puede determinar equipo
            end
        end
    end
    
    OddsService-->>OddsController: {success: true, matched_players: [...]}
    OddsController-->>Backend: JSON response
    Backend-->>Frontend: {success: true, game_id, event_id, matched_players}
    
    Note over Frontend: Recargar juegos con lineups actualizados
    Frontend->>Backend: GET /nba/lineups?date=YYYY-MM-DD
    Backend->>LineupRepo: get_lineups_by_date_date
    LineupRepo->>DB: SELECT * FROM game_lineups WHERE lineup_date = ?
    DB-->>LineupRepo: Lineups con points_line y over_under_history
    LineupRepo-->>Backend: Games with lineups
    Backend-->>Frontend: {success: true, games: [...]}
    
    Frontend->>Frontend: displayGames_games, hasLineups=true
    Note right of Frontend: Muestra jugadores con:<br/>- points_line<br/>- OVER/UNDER history<br/>- Status STARTER/BENCH
    Frontend-->>User: UI actualizada con odds y estadísticas
```

## Información que se obtiene de cada API

### The Odds API
- **Endpoint 1:** `GET /v4/sports/basketball_nba/events`
  - **Información obtenida:**
    - `id`: Event ID único
    - `home_team`: Nombre del equipo local
    - `away_team`: Nombre del equipo visitante
    - `commence_time`: Fecha y hora del juego
    - `sport_key`: "basketball_nba"

- **Endpoint 2:** `GET /v4/sports/basketball_nba/events/{event_id}/odds?markets=player_points&regions=us`
  - **Información obtenida:**
    - `bookmakers`: Lista de casas de apuestas
      - `key`: "fanduel"
      - `markets`: Lista de mercados
        - `key`: "player_points"
        - `outcomes`: Lista de jugadores
          - `description`: Nombre del jugador
          - `name`: "Over" o "Under"
          - `point`: Línea de puntos (points_line)
          - `price`: Odds (american format)

### NBA API (stats.nba.com)
- **Endpoint 1:** `CommonTeamRoster(team_id, season)`
  - **Información obtenida:**
    - `PLAYER_ID`: ID oficial de la NBA
    - `PLAYER`: Nombre completo del jugador
    - `POSITION`: Posición (PG, SG, SF, PF, C)
    - `NUM`: Número de camiseta
    - `TEAM_ID`: ID del equipo

- **Endpoint 2:** `PlayerGameLog(player_id, season)`
  - **Información obtenida:**
    - `GAME_DATE`: Fecha del juego
    - `MATCHUP`: Rival (ej: "LAL vs. BOS")
    - `PTS`: Puntos anotados
    - `MIN`: Minutos jugados
    - Otros estadísticas del juego

### Base de Datos Local
- **Tabla: `games`**
  - `game_id`: ID único del juego
  - `home_team`: Abreviación equipo local
  - `away_team`: Abreviación equipo visitante
  - `home_team_name`: Nombre completo equipo local
  - `away_team_name`: Nombre completo equipo visitante
  - `game_date`: Fecha del juego
  - `game_time`: Hora del juego

- **Tabla: `game_lineups`**
  - `game_id`: ID del juego
  - `team_abbr`: Abreviación del equipo
  - `position`: Posición (PG, SG, SF, PF, C, o BENCH-{id})
  - `player_id`: ID del jugador (NBA oficial o FantasyNerds)
  - `player_name`: Nombre del jugador
  - `player_status`: "STARTER" o "BENCH"
  - `points_line`: Línea de puntos de las odds
  - `over_under_history`: JSON con historial OVER/UNDER
  - `player_photo_url`: URL de foto del jugador

- **Tabla: `team_depth_charts`**
  - `team_abbr`: Abreviación del equipo
  - `season`: Temporada
  - `player_id`: ID oficial de la NBA
  - `player_name`: Nombre del jugador
  - `position`: Posición
  - `depth`: Profundidad en el roster

