# Guía de Importación de Schedule

Esta guía explica cómo importar el schedule de juegos de NBA desde un archivo JSON a la base de datos MySQL.

## Configuración Inicial

1. **Asegúrate de que MySQL esté corriendo:**
   ```bash
   docker-compose up -d mysql
   ```

2. **Espera a que MySQL esté listo** (puede tardar unos segundos)

3. **Las tablas se crean automáticamente** al iniciar la aplicación Flask, pero también puedes crearlas manualmente:
   ```bash
   docker-compose exec api python scripts/init_db.py
   ```

## Formato del JSON

El servicio acepta diferentes formatos de JSON. Aquí hay algunos ejemplos:

### Formato Principal (Recomendado): Objeto con 'season' y 'schedule'
```json
{
  "season": 2026,
  "schedule": [
    {
      "gameId": 7316,
      "game_date": "2026-04-12 20:30:00",
      "away_team": "CHI",
      "home_team": "DAL",
      "winner": "",
      "away_score": 0,
      "home_score": 0
    },
    {
      "gameId": 7317,
      "game_date": "2026-04-12 20:30:00",
      "away_team": "MEM",
      "home_team": "HOU",
      "winner": "",
      "away_score": 0,
      "home_score": 0
    }
  ]
}
```

**Notas sobre este formato:**
- El campo `season` se extrae del nivel superior y se aplica a todos los juegos
- El campo `game_date` contiene fecha y hora juntas (`YYYY-MM-DD HH:MM:SS`) y se separa automáticamente
- Si `winner` está vacío, el status se establece como "Scheduled", si tiene valor, se marca como "Finished"

### Formato Alternativo 1: Lista de juegos
```json
[
  {
    "gameId": "0012300123",
    "homeTeam": "LAL",
    "awayTeam": "BOS",
    "gameDate": "2024-01-15",
    "gameTime": "20:00:00",
    "status": "Scheduled"
  }
]
```

### Formato Alternativo 2: Objeto con clave 'games'
```json
{
  "games": [
    {
      "gameId": "0012300123",
      "homeTeam": "LAL",
      "awayTeam": "BOS",
      "gameDate": "2024-01-15"
    }
  ]
}
```

## Métodos de Importación

### Método 1: Script de línea de comandos

```bash
# Desde dentro del contenedor
docker-compose exec api python scripts/import_schedule.py /ruta/al/archivo.json

# O si el archivo está en tu máquina local, monta un volumen primero
docker-compose exec api python scripts/import_schedule.py /app/data/schedule.json
```

### Método 2: Endpoint POST (subir archivo)

```bash
curl -X POST http://localhost:8000/nba/schedule/import \
  -F "file=@/ruta/al/archivo.json"
```

### Método 3: Endpoint POST (JSON en body)

```bash
curl -X POST http://localhost:8000/nba/schedule/import \
  -H "Content-Type: application/json" \
  -d @/ruta/al/archivo.json
```

### Método 4: Endpoint POST (ruta de archivo)

```bash
curl -X POST "http://localhost:8000/nba/schedule/import?json_path=/app/data/schedule.json"
```

## Consultar Juegos por Fecha

Una vez importado el schedule, puedes consultar los juegos por fecha:

```bash
curl "http://localhost:8000/nba/games?date=2024-01-15"
```

Respuesta:
```json
{
  "success": true,
  "date": "2024-01-15",
  "count": 5,
  "games": [
    {
      "game_id": "0012300123",
      "home_team": "LAL",
      "away_team": "BOS",
      "game_date": "2024-01-15",
      "game_time": "20:00:00",
      "status": "Scheduled",
      "season": "2023-24",
      "season_type": "Regular Season",
      "home_team_name": "Los Angeles Lakers",
      "away_team_name": "Boston Celtics"
    }
  ]
}
```

## Campos Soportados

El servicio normaliza automáticamente diferentes nombres de campos:

- **gameId**: `gameId`, `game_id`, `id`, `GameID` (puede ser número o string)
- **homeTeam**: `homeTeam`, `home_team`, `HOME_TEAM`, `hTeam.abbreviation`, `home.abbreviation`
- **awayTeam**: `awayTeam`, `away_team`, `AWAY_TEAM`, `vTeam.abbreviation`, `away.abbreviation`
- **gameDate**: 
  - `gameDate`, `game_date`, `date`, `GAME_DATE`
  - Si viene en formato `YYYY-MM-DD HH:MM:SS`, se separa automáticamente en fecha y hora
- **gameTime**: `gameTime`, `game_time`, `time`, `GAME_TIME` (o extraído de `game_date`)
- **status**: 
  - `status`, `gameStatus`, `STATUS`
  - Si existe `winner` y está vacío → "Scheduled", si tiene valor → "Finished"
- **season**: Se extrae del nivel superior del JSON o de cada juego individual

## Notas

- Los juegos se insertan con `ON DUPLICATE KEY UPDATE`, por lo que puedes re-importar el mismo archivo sin duplicados
- El campo `game_id` debe ser único
- Si un juego no tiene `game_id`, se omite durante la importación

