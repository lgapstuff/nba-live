#!/bin/bash

# Script de despliegue para producción
# Uso: ./scripts/deploy.sh

set -e  # Salir si hay errores

echo "🚀 Iniciando despliegue de NBA Live API..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.prod.yml no encontrado${NC}"
    echo "Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar que existe .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: Archivo .env no encontrado${NC}"
    echo "Asegúrate de crear un archivo .env con las variables de entorno necesarias"
    read -p "¿Continuar de todas formas? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Verificar que Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker no está corriendo${NC}"
    exit 1
fi

# Verificar que Docker Compose está instalado
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker Compose no está instalado${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Verificaciones completadas${NC}"

# Preguntar si hacer backup de la base de datos
read -p "¿Hacer backup de la base de datos antes de desplegar? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Creando backup de la base de datos..."
    mkdir -p backups
    docker exec nba-edge-mysql mysqldump -u ${MYSQL_USER:-nba_user} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE:-nba_edge} > backups/backup_$(date +%Y%m%d_%H%M%S).sql 2>/dev/null || echo -e "${YELLOW}⚠️  No se pudo hacer backup (puede ser la primera vez)${NC}"
fi

# Detener contenedores existentes
echo "🛑 Deteniendo contenedores existentes..."
docker compose -f docker-compose.prod.yml down

# Construir y levantar contenedores
echo "🔨 Construyendo y levantando contenedores..."
docker compose -f docker-compose.prod.yml up -d --build

# Esperar a que los servicios estén listos
echo "⏳ Esperando a que los servicios estén listos..."
sleep 10

# Verificar estado de los contenedores
echo "📊 Estado de los contenedores:"
docker compose -f docker-compose.prod.yml ps

# Verificar salud de los servicios
echo ""
echo "🏥 Verificando salud de los servicios..."

# Verificar MySQL
if docker exec nba-edge-mysql mysqladmin ping -h localhost --silent; then
    echo -e "${GREEN}✓ MySQL está funcionando${NC}"
else
    echo -e "${RED}❌ MySQL no está respondiendo${NC}"
fi

# Verificar API principal
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API principal está funcionando${NC}"
else
    echo -e "${YELLOW}⚠️  API principal no responde (puede estar iniciando)${NC}"
fi

echo ""
echo -e "${GREEN}✅ Despliegue completado!${NC}"
echo ""
echo "Para ver los logs:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "Para detener los servicios:"
echo "  docker compose -f docker-compose.prod.yml down"
echo ""
