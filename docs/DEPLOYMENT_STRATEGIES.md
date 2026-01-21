# Estrategias de Despliegue para NBA Live API

## Arquitectura Actual
- **API Gateway**: Puerto 8000 (aplicación principal)
- **Microservicios**: 
  - FantasyNerds Service (8001)
  - NBA API Service (8002)
  - Odds API Service (8003)
- **Base de Datos**: MySQL 8.0
- **Orquestación**: Docker Compose

---

## Opciones de Despliegue

### 🟢 Opción 1: VPS con Docker Compose + Nginx (Recomendada para empezar)

**Mejor para**: Proyectos pequeños/medianos, presupuesto limitado, control total

**Proveedores recomendados**:
- **DigitalOcean**: $12-24/mes (2-4GB RAM)
- **Linode**: $12-24/mes
- **Hetzner**: €4-8/mes (muy económico en Europa)
- **AWS Lightsail**: $10-20/mes

**Ventajas**:
- ✅ Simple de configurar
- ✅ Costo bajo
- ✅ Control total del servidor
- ✅ Fácil de mantener
- ✅ Perfecto para empezar

**Desventajas**:
- ⚠️ Escalado manual
- ⚠️ Sin auto-healing automático
- ⚠️ Necesitas gestionar backups manualmente

**Setup necesario**:
1. VPS con Ubuntu 22.04 LTS
2. Docker y Docker Compose instalados
3. Nginx como reverse proxy
4. Certbot para SSL (Let's Encrypt)
5. Firewall configurado (UFW)

---

### 🟡 Opción 2: Docker Swarm (Clustering)

**Mejor para**: Necesitas alta disponibilidad, múltiples servidores

**Ventajas**:
- ✅ Escalado horizontal
- ✅ Alta disponibilidad
- ✅ Load balancing integrado
- ✅ Rolling updates

**Desventajas**:
- ⚠️ Más complejo que Compose
- ⚠️ Necesitas múltiples servidores
- ⚠️ Configuración más avanzada

---

### 🔵 Opción 3: Kubernetes (Producción Enterprise)

**Mejor para**: Aplicaciones críticas, escalado automático, múltiples ambientes

**Proveedores**:
- **AWS EKS**: $0.10/hora por cluster + instancias
- **Google GKE**: Similar pricing
- **DigitalOcean Kubernetes**: $12/mes por nodo
- **Linode Kubernetes**: $12/mes por nodo

**Ventajas**:
- ✅ Escalado automático
- ✅ Auto-healing
- ✅ Rolling deployments
- ✅ Service mesh capabilities
- ✅ Estándar de la industria

**Desventajas**:
- ⚠️ Curva de aprendizaje alta
- ⚠️ Más caro
- ⚠️ Overhead de recursos
- ⚠️ Complejidad operacional

---

### 🟣 Opción 4: Cloud Managed Services

#### AWS ECS (Elastic Container Service)
- **Ventajas**: Integrado con AWS, Fargate (serverless)
- **Costo**: ~$50-100/mes para setup básico
- **Mejor para**: Ya usas AWS

#### Google Cloud Run
- **Ventajas**: Serverless, pago por uso
- **Costo**: Muy económico para tráfico bajo
- **Mejor para**: Tráfico variable, serverless

#### Azure Container Apps
- **Ventajas**: Serverless, auto-scaling
- **Costo**: Similar a Cloud Run
- **Mejor para**: Ecosistema Microsoft

---

## 🎯 Recomendación: Opción 1 (VPS + Docker Compose)

Para tu caso, recomiendo empezar con **Opción 1** porque:

1. **Es suficiente para empezar**: Tu aplicación no necesita escalado masivo inicialmente
2. **Costo efectivo**: $12-24/mes vs $50-200/mes en cloud managed
3. **Control total**: Puedes migrar después sin problemas
4. **Fácil de mantener**: Docker Compose es simple
5. **Profesional**: Muchas empresas usan esta arquitectura

---

## 📋 Setup Detallado: VPS + Docker Compose

### Paso 1: Preparar el Servidor

```bash
# Conectar al servidor
ssh root@tu-servidor.com

# Actualizar sistema
apt update && apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Instalar Docker Compose
apt install docker-compose-plugin -y

# Instalar Nginx
apt install nginx -y

# Instalar Certbot (SSL)
apt install certbot python3-certbot-nginx -y
```

### Paso 2: Configurar Firewall

```bash
# Configurar UFW
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### Paso 3: Clonar y Configurar la Aplicación

```bash
# Crear directorio
mkdir -p /opt/nba-live
cd /opt/nba-live

# Clonar repositorio (o subir archivos)
git clone tu-repo.git .

# Crear archivo .env de producción
nano .env
```

**Archivo `.env` de producción**:
```env
# Database
MYSQL_ROOT_PASSWORD=tu_password_seguro_aqui
MYSQL_DATABASE=nba_edge
MYSQL_USER=nba_user
MYSQL_PASSWORD=otro_password_seguro
MYSQL_PORT=3306

# Application
APP_PORT=8000
FLASK_ENV=production

# Microservices
FANTASYNERDS_SERVICE_PORT=8001
NBA_API_SERVICE_PORT=8002
ODDS_API_SERVICE_PORT=8003

# API Keys
FANTASYNERDS_API_KEY=tu_api_key
THE_ODDS_API_KEY=tu_api_key

# Service URLs (cloud)
FANTASYNERDS_SERVICE_URL=https://api-nba-fantasynerds.bravewater-0444722a.centralus.azurecontainerapps.io
NBA_API_SERVICE_URL=https://api-nba-cdn.bravewater-0444722a.centralus.azurecontainerapps.io
ODDS_API_SERVICE_URL=https://api-nba-odds.bravewater-0444722a.centralus.azurecontainerapps.io
```

### Paso 4: Modificar docker-compose.yml para Producción

Crear `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: nba-edge-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./backups:/backups  # Para backups
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - nba-network
    # NO exponer puerto 3306 públicamente en producción

  fantasynerds-service:
    build:
      context: ./microservices/fantasynerds-service
      dockerfile: Dockerfile
    container_name: fantasynerds-service
    env_file:
      - .env
    environment:
      - FLASK_APP=app.main:create_app
      - FLASK_ENV=production
      - MYSQL_HOST=mysql
      - APP_PORT=8001
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - nba-network
    # NO exponer puertos públicamente

  nba-api-service:
    build:
      context: ./microservices/nba-api-service
      dockerfile: Dockerfile
    container_name: nba-api-service
    env_file:
      - .env
    environment:
      - FLASK_APP=app.main:create_app
      - FLASK_ENV=production
      - MYSQL_HOST=mysql
      - APP_PORT=8002
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - nba-network

  odds-api-service:
    build:
      context: ./microservices/odds-api-service
      dockerfile: Dockerfile
    container_name: odds-api-service
    env_file:
      - .env
    environment:
      - FLASK_APP=app.main:create_app
      - FLASK_ENV=production
      - MYSQL_HOST=mysql
      - APP_PORT=8003
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - nba-network

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: nba-edge-api
    env_file:
      - .env
    environment:
      - FLASK_APP=app.main:create_app
      - FLASK_ENV=production
      - MYSQL_HOST=mysql
      - FANTASYNERDS_SERVICE_URL=https://api-nba-fantasynerds.bravewater-0444722a.centralus.azurecontainerapps.io
      - NBA_API_SERVICE_URL=https://api-nba-cdn.bravewater-0444722a.centralus.azurecontainerapps.io
      - ODDS_API_SERVICE_URL=https://api-nba-odds.bravewater-0444722a.centralus.azurecontainerapps.io
    depends_on:
      mysql:
        condition: service_healthy
      fantasynerds-service:
        condition: service_started
      nba-api-service:
        condition: service_started
      odds-api-service:
        condition: service_started
    restart: unless-stopped
    networks:
      - nba-network
    # Nginx manejará el acceso externo

networks:
  nba-network:
    driver: bridge

volumes:
  mysql_data:
```

### Paso 5: Configurar Nginx como Reverse Proxy

Crear `/etc/nginx/sites-available/nba-live`:

```nginx
upstream nba_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

    # Redirigir a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com www.tu-dominio.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/nba-live-access.log;
    error_log /var/log/nginx/nba-live-error.log;

    # API Proxy
    location / {
        proxy_pass http://nba_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (si los sirves desde Nginx)
    location /static/ {
        alias /opt/nba-live/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Activar configuración:
```bash
ln -s /etc/nginx/sites-available/nba-live /etc/nginx/sites-enabled/
nginx -t  # Verificar configuración
systemctl reload nginx
```

### Paso 6: Obtener SSL con Let's Encrypt

```bash
certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

### Paso 7: Iniciar la Aplicación

```bash
cd /opt/nba-live
docker compose -f docker-compose.prod.yml up -d --build
```

### Paso 8: Configurar Auto-start y Monitoreo

Crear servicio systemd `/etc/systemd/system/nba-live.service`:

```ini
[Unit]
Description=NBA Live API Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/nba-live
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Activar:
```bash
systemctl enable nba-live.service
systemctl start nba-live.service
```

---

## 🔄 Estrategia de Migración Futura

### Fase 1: VPS Simple (Ahora)
- Docker Compose en un servidor
- Nginx reverse proxy
- SSL con Let's Encrypt

### Fase 2: Mejoras (Cuando crezca)
- Agregar segundo servidor para alta disponibilidad
- Implementar Docker Swarm
- Configurar backups automáticos
- Agregar monitoreo (Prometheus + Grafana)

### Fase 3: Escala (Si es necesario)
- Migrar a Kubernetes
- Separar base de datos (RDS/Cloud SQL)
- Implementar CDN para static files
- Auto-scaling

---

## 📊 Comparación de Costos (Mensual)

| Opción | Costo Inicial | Escalabilidad | Complejidad |
|--------|---------------|----------------|-------------|
| VPS + Docker Compose | $12-24 | Media | Baja |
| Docker Swarm (2 servidores) | $24-48 | Alta | Media |
| Kubernetes (Managed) | $50-100+ | Muy Alta | Alta |
| AWS ECS | $50-150 | Muy Alta | Media-Alta |
| Google Cloud Run | $20-80 | Muy Alta | Baja |

---

## 🛡️ Consideraciones de Seguridad

1. **No exponer puertos de microservicios públicamente**
2. **Usar firewall (UFW)**
3. **SSL obligatorio (Let's Encrypt)**
4. **Backups automáticos de MySQL**
5. **Variables de entorno seguras (.env no en git)**
6. **Rate limiting en Nginx**
7. **Actualizar contenedores regularmente**

---

## 📝 Checklist de Despliegue

- [ ] Servidor VPS configurado
- [ ] Docker y Docker Compose instalados
- [ ] Nginx configurado como reverse proxy
- [ ] SSL configurado (Let's Encrypt)
- [ ] Firewall configurado
- [ ] Archivo .env de producción creado
- [ ] docker-compose.prod.yml configurado
- [ ] Aplicación desplegada y funcionando
- [ ] Backups configurados
- [ ] Monitoreo básico configurado
- [ ] DNS apuntando al servidor

---

## 🚀 Comandos Útiles

```bash
# Ver logs
docker compose -f docker-compose.prod.yml logs -f

# Reiniciar servicios
docker compose -f docker-compose.prod.yml restart

# Actualizar aplicación
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Backup MySQL
docker exec nba-edge-mysql mysqldump -u root -p nba_edge > backup_$(date +%Y%m%d).sql

# Ver estado
docker compose -f docker-compose.prod.yml ps
```

---

## 📚 Recursos Adicionales

- [Docker Compose Production Best Practices](https://docs.docker.com/compose/production/)
- [Nginx Reverse Proxy Guide](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [DigitalOcean Docker Tutorials](https://www.digitalocean.com/community/tags/docker)
