# NBA API Microservice

Microservicio independiente para la integración con la API de NBA (usando nba_api library).

## Endpoints

- `GET /` - Health check básico
- `GET /api/v1/health` - Health check detallado
- `GET /api/v1/players/<player_id>/game-log?season=2023-24&season_type=Regular Season` - Game log de un jugador
- `GET /api/v1/players/<player_id>/last-games?n=10&season=2023-24` - Últimos N juegos de un jugador
- `GET /api/v1/players/find-by-name?name=LeBron James` - Buscar ID de jugador por nombre
- `GET /api/v1/teams/<team_abbr>/players?season=2023-24` - Obtener jugadores de un equipo
- `GET /api/v1/games/<game_id>/boxscore?player_ids=123,456` - Boxscore en vivo
- `GET /api/v1/games/find-game-id?home_team=LAL&away_team=BOS&game_date=2024-01-15` - Buscar GameID

## Desarrollo Local

```bash
docker-compose up --build
```

El servicio estará disponible en `http://localhost:8002`
