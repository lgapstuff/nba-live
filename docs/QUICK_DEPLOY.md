# Guía Rápida de Despliegue

## 🚀 Despliegue Rápido en 5 Pasos

### Paso 1: Contratar VPS
Recomendaciones:
- **DigitalOcean**: Droplet de $12/mes (2GB RAM) - [Crear cuenta](https://m.do.co/c/your-ref)
- **Hetzner**: Cloud Server €4/mes (2GB RAM) - [Crear cuenta](https://hetzner.cloud)
- **Linode**: Nanode de $12/mes - [Crear cuenta](https://www.linode.com)

### Paso 2: Configurar Servidor
```bash
# Conectar al servidor
ssh root@tu-servidor-ip

# Ejecutar script de configuración
curl -fsSL https://raw.githubusercontent.com/tu-repo/nba-live/main/scripts/setup-server.sh | bash
```

O manualmente:
```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh

# Instalar Docker Compose
apt install docker-compose-plugin nginx certbot python3-certbot-nginx -y

# Configurar firewall
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
```

### Paso 3: Clonar y Configurar Aplicación
```bash
# Crear directorio
mkdir -p /opt/nba-live && cd /opt/nba-live

# Clonar repositorio
git clone https://github.com/tu-usuario/nba-live.git .

# Crear archivo .env
nano .env
```

**Contenido mínimo de `.env`**:
```env
MYSQL_ROOT_PASSWORD=password_seguro_aqui
MYSQL_DATABASE=nba_edge
MYSQL_USER=nba_user
MYSQL_PASSWORD=otro_password_seguro
FLASK_ENV=production
FANTASYNERDS_API_KEY=tu_api_key
THE_ODDS_API_KEY=tu_api_key
```

### Paso 4: Configurar Nginx y SSL
```bash
# Copiar configuración de Nginx
cp nginx/nba-live.conf /etc/nginx/sites-available/nba-live

# Editar y cambiar 'tu-dominio.com' por tu dominio real
nano /etc/nginx/sites-available/nba-live

# Activar configuración
ln -s /etc/nginx/sites-available/nba-live /etc/nginx/sites-enabled/
nginx -t

# Obtener SSL
certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

### Paso 5: Desplegar Aplicación
```bash
cd /opt/nba-live
./scripts/deploy.sh
```

O manualmente:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## ✅ Verificar Despliegue

```bash
# Ver estado de contenedores
docker compose -f docker-compose.prod.yml ps

# Ver logs
docker compose -f docker-compose.prod.yml logs -f

# Probar API
curl https://tu-dominio.com/health
```

## 🔄 Actualizar Aplicación

```bash
cd /opt/nba-live
git pull
./scripts/deploy.sh
```

## 📊 Monitoreo Básico

```bash
# Ver uso de recursos
docker stats

# Ver logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f api

# Verificar salud de servicios
curl http://localhost:8000/health
```

## 🛠️ Comandos Útiles

```bash
# Reiniciar servicios
docker compose -f docker-compose.prod.yml restart

# Detener servicios
docker compose -f docker-compose.prod.yml down

# Ver logs de un servicio específico
docker compose -f docker-compose.prod.yml logs -f api

# Acceder a MySQL
docker exec -it nba-edge-mysql mysql -u nba_user -p

# Backup de base de datos
docker exec nba-edge-mysql mysqldump -u nba_user -p nba_edge > backup.sql
```

## 🚨 Troubleshooting

### La API no responde
```bash
# Verificar que los contenedores están corriendo
docker compose -f docker-compose.prod.yml ps

# Ver logs de errores
docker compose -f docker-compose.prod.yml logs api

# Verificar Nginx
nginx -t
systemctl status nginx
```

### Error de conexión a MySQL
```bash
# Verificar que MySQL está corriendo
docker exec nba-edge-mysql mysqladmin ping -h localhost

# Ver logs de MySQL
docker compose -f docker-compose.prod.yml logs mysql
```

### SSL no funciona
```bash
# Verificar certificados
certbot certificates

# Renovar certificado
certbot renew

# Verificar configuración de Nginx
nginx -t
```

## 📝 Checklist Pre-Despliegue

- [ ] VPS contratado y accesible
- [ ] DNS apuntando al servidor (A record)
- [ ] Docker y Docker Compose instalados
- [ ] Nginx instalado y configurado
- [ ] Archivo .env creado con todas las variables
- [ ] SSL configurado (Let's Encrypt)
- [ ] Firewall configurado
- [ ] Aplicación desplegada y funcionando
- [ ] Pruebas de endpoints realizadas

## 💰 Costo Estimado Mensual

- **VPS**: $12-24/mes
- **Dominio**: $10-15/año (ya lo tienes)
- **Total**: ~$12-24/mes

## 🔐 Seguridad Post-Despliegue

1. **Cambiar contraseñas por defecto**
2. **Configurar backups automáticos**
3. **Monitorear logs regularmente**
4. **Mantener contenedores actualizados**
5. **Revisar configuración de firewall**

## 📚 Documentación Completa

Para más detalles, ver: [DEPLOYMENT_STRATEGIES.md](./DEPLOYMENT_STRATEGIES.md)
