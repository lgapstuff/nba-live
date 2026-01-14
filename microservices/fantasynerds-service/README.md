# FantasyNerds Microservice

Microservicio independiente para la integración con la API de FantasyNerds.

## Estructura

```
fantasynerds-service/
├── app/
│   ├── config/
│   │   └── settings.py          # Configuración
│   ├── infrastructure/
│   │   └── clients/
│   │       └── fantasynerds_client.py  # Cliente HTTP para FantasyNerds API
│   ├── interface/
│   │   └── http/
│   │       └── controllers/
│   │           └── fantasynerds_controller.py  # Endpoints REST
│   └── main.py                   # Factory de la aplicación Flask
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.py
└── README.md
```

## Endpoints

- `GET /` - Health check básico
- `GET /api/v1/health` - Health check detallado
- `GET /api/v1/games/<date>` - Obtener juegos para una fecha (YYYY-MM-DD)
- `GET /api/v1/lineups/date/<date>` - Obtener lineups para una fecha (YYYY-MM-DD)
- `GET /api/v1/lineups/game/<game_id>` - Obtener lineups para un juego específico
- `GET /api/v1/depth-charts` - Obtener depth charts de todos los equipos

## Desarrollo Local

1. Copiar `.env.example` a `.env` y configurar las variables:
```bash
cp .env.example .env
```

2. Ejecutar con Docker Compose:
```bash
docker-compose up --build
```

3. O ejecutar directamente con Python:
```bash
pip install -r requirements.txt
python run.py
```

El servicio estará disponible en `http://localhost:8001`

## Ejemplo de Uso

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Obtener lineups para una fecha
curl http://localhost:8001/api/v1/lineups/date/2024-01-15

# Obtener depth charts
curl http://localhost:8001/api/v1/depth-charts
```

## Base de Datos Compartida

Este microservicio se conecta a la misma base de datos MySQL que el API principal. 
La configuración de la base de datos se hace a través de variables de entorno.

## Integración con API Gateway

El API Gateway principal (nba-live) consumirá este servicio a través de HTTP:

```python
# En el API Gateway
response = requests.get("http://fantasynerds-service:8001/api/v1/lineups/date/2024-01-15")
```
