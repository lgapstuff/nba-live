# NBA Lineups - Frontend

Aplicación web vanilla JavaScript para visualizar lineups de NBA.

## Características

- ✅ Visualización de juegos del día
- ✅ Lineups completos (5 posiciones por equipo)
- ✅ Fotos de jugadores
- ✅ Logos de equipos
- ✅ Información de equipos (nombres completos)
- ✅ Diseño responsive
- ✅ Carga automática desde FantasyNerds API

## Cómo usar

1. **Asegúrate de que la API esté corriendo:**
   ```bash
   docker-compose up -d
   ```

2. **Abre en el navegador:**
   ```
   http://localhost:8000
   ```

3. **Selecciona una fecha y haz clic en "Cargar Lineups"**

## Estructura

- `index.html` - Estructura HTML
- `styles.css` - Estilos CSS
- `app.js` - Lógica JavaScript (consumo de API)

## API Endpoint

La aplicación consume:
```
GET /nba/lineups?date=YYYY-MM-DD
```

## Personalización

Para cambiar la URL de la API, edita `app.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

