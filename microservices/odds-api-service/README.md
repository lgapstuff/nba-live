# Odds API Microservice

Microservicio independiente para la integración con The Odds API.

## Endpoints

- `GET /` - Health check básico
- `GET /api/v1/health` - Health check detallado
- `GET /api/v1/events?sport=basketball_nba` - Obtener eventos
- `GET /api/v1/events/<event_id>/odds?regions=us&markets=player_points,player_assists,player_rebounds` - Obtener odds de player props
- `GET /api/v1/scores?sport=basketball_nba&days_from=1&event_ids=...` - Obtener scores

## Desarrollo Local

```bash
docker-compose up --build
```

El servicio estará disponible en `http://localhost:8003`
