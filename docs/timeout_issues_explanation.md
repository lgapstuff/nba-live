# Explicación de los Errores de Timeout

## Problema Identificado

La aplicación se queda colgada cuando intenta cargar datos de la API de NBA. Los errores que ves son:

### 1. **Timeouts en Game Logs** (El problema principal)
```
[NBA API] REQUEST ERROR: Error fetching game log for player XXXX
HTTPSConnectionPool (host='stats.nba.com', port=443): Read timed out. (read timeout=30)
```

**Endpoint que falla:** `stats.nba.com/stats/playergamelog`

**Cuándo ocurre:**
- Cuando el usuario hace clic en "Ver Últimos Juegos" para un jugador
- El endpoint `/nba/players/<player_id>/game-logs` intenta cargar desde NBA API si no hay suficientes en la BD
- El SDK `nba_api` no tiene timeout configurado, y cuando la API de NBA está lenta, se queda esperando indefinidamente

**Por qué se queda colgada la app:**
- Si hay 10-15 jugadores en un juego, se pueden hacer 10-15 peticiones
- Cada petición puede tardar 30+ segundos en dar timeout
- Las peticiones se hacen de forma síncrona, bloqueando el proceso
- La app espera todas las respuestas antes de continuar

### 2. **Jugadores sin NBA Player ID**
```
[NBA API] REQUEST: Could not find NBA player ID for [Player Name]
[OVER/UNDER] Could not find NBA player ID for [Player Name], will try with FantasyNerds ID
```

**Por qué ocurre:**
- Algunos jugadores nuevos o de G-League no están en la base de datos de la NBA API
- El sistema intenta buscar por nombre, pero si no los encuentra, usa el ID de FantasyNerds como fallback

**Impacto:** Menor, solo afecta el cálculo de OVER/UNDER para esos jugadores específicos

### 3. **No hay Game Logs Locales**
```
No game logs found locally for player XXXX
```

**Por qué ocurre:**
- Los game logs se cargan bajo demanda o cuando se carga un juego completo
- Si un jugador nunca ha sido consultado, no tiene game logs en la BD
- El sistema intenta cargarlos desde NBA API, pero si da timeout, no se guardan

## Soluciones Implementadas

### 1. Timeout en el Frontend
- Agregado timeout de 2 minutos en las peticiones de odds desde el frontend
- Mejorado el manejo de errores para que el loading siempre se oculte

### 2. Mejoras Necesarias en el Backend

#### A. Agregar timeout al SDK nba_api
El SDK `nba_api` usa `requests` internamente, pero no expone el timeout. Necesitamos:
- Wrappear las llamadas con timeout
- Usar `signal` o `threading` para forzar timeout si es necesario

#### B. Mejorar el endpoint de game logs
- Agregar timeout más corto (15-20 segundos)
- Si hay timeout, retornar los game logs que ya están en la BD (aunque sean pocos)
- No bloquear la respuesta esperando la API de NBA

#### C. Cargar game logs de forma asíncrona
- Cuando se carga un juego, cargar los game logs en background
- No esperar a que terminen para mostrar los odds
- Usar un sistema de cola o tareas en background

## Endpoints Afectados

1. **`GET /nba/players/<player_id>/game-logs`**
   - Intenta cargar desde NBA API si hay < 10 games en BD
   - **Problema:** Se queda esperando si la API da timeout

2. **`POST /nba/games/<game_id>/game-logs`**
   - Carga game logs para todos los jugadores de un juego
   - **Problema:** Puede tardar mucho si hay muchos jugadores

3. **`GET /nba/games/<game_id>/odds`**
   - Carga odds y calcula OVER/UNDER history
   - **Estado:** Ya usa `use_local_only=True` para evitar llamadas a NBA API durante la carga

## Recomendaciones

1. **Corto plazo:**
   - Agregar timeout explícito a las llamadas del SDK nba_api
   - Mejorar el manejo de errores para que no bloquee la app
   - Retornar datos parciales si hay timeout

2. **Mediano plazo:**
   - Implementar carga asíncrona de game logs
   - Pre-cargar game logs para jugadores comunes
   - Usar cache más agresivo

3. **Largo plazo:**
   - Considerar usar una API alternativa o proxy
   - Implementar sistema de cola para tareas pesadas
   - Monitorear y alertar sobre timeouts frecuentes

