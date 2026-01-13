# NBA Edge API – Project Context & Architecture (MVP)

Este documento sirve como **contexto técnico y funcional** para inicializar el proyecto. Está diseñado para pegarse como **README.md** o como input inicial en Cursor, con el objetivo de que cualquier generador/colaborador entienda **qué se va a construir**, **con qué stack**, y **cómo debe organizarse el código**.

---

## 1. Objetivo del MVP

Construir un backend en **Flask** que consuma **FantasyNerds NBA API** para:

1. Obtener los **juegos del día**.
2. Obtener **lineups** por juego (al menos **starters**).
3. Exponer endpoints internos propios para:

   * listar juegos del día,
   * expandir un juego,
   * ver starters por equipo.

> ⚠️ Este MVP **NO** implementa apuestas, odds ni lógica de edge. Solo prepara la **base de datos estructurada** (schedule + starters).

---

## 2. Stack Obligatorio

* **Python 3.12+**
* **Flask** (framework HTTP)
* **Dockerfile**
* **docker-compose.yml**
* **.env** para configuración
* **Arquitectura DDD (Domain Driven Design)**
* Gestión simple de dependencias: `requirements.txt`

---

## 3. Objetivo del Primer Commit

* Tener lista **toda la estructura DDD**.
* Tener el servidor Flask corriendo vía **Docker Compose**.
* Exponer **un único endpoint de prueba**:

```
GET /health
```

Respuesta:

```json
{
  "status": "ok",
  "message": "hello from flask"
}
```

* **No** implementar aún lógica real de NBA ni consumo de FantasyNerds.
* Solo dejar **stubs, contratos e interfaces** listos.

---

## 4. Arquitectura (DDD / Clean-ish)

### Capas

1. **Domain**

   * Núcleo del negocio.
   * Entidades, Value Objects, reglas, contratos (ports).
   * ❌ No depende de Flask ni de HTTP.

2. **Application**

   * Casos de uso (services).
   * Orquesta Domain + ports.
   * No conoce detalles de infraestructura.

3. **Infrastructure**

   * Implementaciones concretas (clientes HTTP, cache, repositorios).
   * Aquí vivirá la integración con FantasyNerds.

4. **Interface / API**

   * Flask app, blueprints, controllers.
   * Manejo de errores y schemas HTTP.

---

## 5. Estructura de Carpetas

```
nba-edge-api/
  app/
    __init__.py
    main.py                      # create_app() (Flask factory)
    config/
      __init__.py
      settings.py                # Carga .env y configura Flask
    interface/
      __init__.py
      http/
        __init__.py
        blueprints/
          __init__.py
          health_bp.py           # GET /health
          nba_bp.py              # Placeholder para NBA endpoints
        controllers/
          __init__.py
          health_controller.py
        errors/
          __init__.py
          handlers.py            # Error handlers globales
    application/
      __init__.py
      services/
        __init__.py
        nba_lineups_service.py   # Use-case stub
    domain/
      __init__.py
      models/
        __init__.py
        game.py                  # Entity stub
        team.py                  # Entity stub
        player.py                # Entity stub
      value_objects/
        __init__.py
        game_id.py               # VO stub
        team_abbr.py             # VO stub
      ports/
        __init__.py
        fantasynerds_port.py     # Interface / contract
      exceptions/
        __init__.py
        domain_exceptions.py
    infrastructure/
      __init__.py
      clients/
        __init__.py
        fantasynerds_client.py   # HTTP client stub
      repositories/
        __init__.py
        lineup_repository.py     # Stub
      cache/
        __init__.py
        cache_provider.py        # In-memory cache stub
  tests/
    __init__.py
    test_health.py
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  requirements.txt
  README.md
```

---

## 6. Configuración (.env)

Archivo `.env.example`:

```
FLASK_ENV=development
FLASK_DEBUG=1
APP_HOST=0.0.0.0
APP_PORT=8000

# Third-party
FANTASYNERDS_API_KEY=replace_me

# Future use
CACHE_TTL_SECONDS=120
```

---

## 7. Docker

### Dockerfile (requisitos)

* Base: `python:3.12-slim`
* Instalar dependencias desde `requirements.txt`
* Copiar código
* Exponer `APP_PORT`
* Comando de arranque con Flask (via `create_app()`)

### docker-compose.yml (requisitos)

* Servicio `api`
* Cargar variables desde `.env`
* Mapear puertos `${APP_PORT}:${APP_PORT}`
* Volumen montado para desarrollo local (opcional, recomendado)

---

## 8. Endpoints del MVP

### Health Check

```
GET /health
```

Respuesta:

```json
{
  "status": "ok",
  "message": "hello from flask"
}
```

> No se deben crear más endpoints hasta que la estructura esté validada.

---

## 9. Estándares de Código

* Logging básico a stdout.
* Manejo global de errores (404 / 500) con JSON.
* Separación estricta de capas.
* Nada de lógica de negocio en controllers.

---

## 10. Roadmap Posterior (No MVP)

* Integrar FantasyNerds real (lineups por fecha).
* Exponer:

  * `GET /nba/games?date=YYYY-MM-DD`
  * `GET /nba/lineups?date=YYYY-MM-DD`
  * `GET /nba/games/{gameId}/lineups`
* Integrar APIs de odds (fase 2).
* Persistir snapshots (opening vs live).

---

## 11. Definición de "Listo" para el MVP

* La app corre con Docker Compose.
* `/health` responde correctamente.
* La estructura DDD está completa.
* El proyecto está listo para empezar a implementar casos de uso reales.

---

## Quick Start

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Build and run with Docker Compose:
   ```bash
   docker-compose up --build
   ```

3. Test the health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

---

**Este documento es la fuente de verdad inicial del proyecto.**



