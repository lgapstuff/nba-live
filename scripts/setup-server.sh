#!/bin/bash

# Script para configurar un servidor Ubuntu desde cero
# Uso: Ejecutar en el servidor como root
# curl -fsSL https://raw.githubusercontent.com/tu-repo/setup-server.sh | bash

set -e

echo "🔧 Configurando servidor para NBA Live API..."

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Actualizar sistema
echo "📦 Actualizando sistema..."
apt update && apt upgrade -y

# Instalar dependencias básicas
echo "📦 Instalando dependencias básicas..."
apt install -y curl wget git ufw software-properties-common

# Instalar Docker
echo "🐳 Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker instalado${NC}"
else
    echo -e "${YELLOW}⚠️  Docker ya está instalado${NC}"
fi

# Instalar Docker Compose
echo "🐳 Instalando Docker Compose..."
if ! command -v docker compose &> /dev/null; then
    apt install -y docker-compose-plugin
    echo -e "${GREEN}✓ Docker Compose instalado${NC}"
else
    echo -e "${YELLOW}⚠️  Docker Compose ya está instalado${NC}"
fi

# Instalar Nginx
echo "🌐 Instalando Nginx..."
if ! command -v nginx &> /dev/null; then
    apt install -y nginx
    systemctl enable nginx
    echo -e "${GREEN}✓ Nginx instalado${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx ya está instalado${NC}"
fi

# Instalar Certbot para SSL
echo "🔒 Instalando Certbot..."
if ! command -v certbot &> /dev/null; then
    apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✓ Certbot instalado${NC}"
else
    echo -e "${YELLOW}⚠️  Certbot ya está instalado${NC}"
fi

# Configurar firewall
echo "🔥 Configurando firewall..."
ufw --force enable
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
echo -e "${GREEN}✓ Firewall configurado${NC}"

# Crear usuario no-root para Docker (opcional pero recomendado)
echo "👤 Configuración de usuario..."
read -p "¿Crear usuario no-root para ejecutar Docker? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Nombre de usuario: " username
    if id "$username" &>/dev/null; then
        echo -e "${YELLOW}⚠️  Usuario $username ya existe${NC}"
    else
        adduser --disabled-password --gecos "" $username
        usermod -aG docker $username
        usermod -aG sudo $username
        echo -e "${GREEN}✓ Usuario $username creado y agregado a grupos docker y sudo${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✅ Configuración del servidor completada!${NC}"
echo ""
echo "Próximos pasos:"
echo "1. Clonar tu repositorio en /opt/nba-live"
echo "2. Crear archivo .env con las variables de entorno"
echo "3. Configurar Nginx (ver docs/DEPLOYMENT_STRATEGIES.md)"
echo "4. Ejecutar: docker compose -f docker-compose.prod.yml up -d"
echo ""
