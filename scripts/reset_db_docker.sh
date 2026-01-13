#!/bin/bash
# Script para reiniciar la base de datos en Docker
# Uso: ./scripts/reset_db_docker.sh

echo "=========================================="
echo "Reiniciando base de datos en Docker..."
echo "=========================================="

# Ejecutar el script de reset dentro del contenedor de la API
docker compose exec api python scripts/reset_database.py

echo ""
echo "=========================================="
echo "Base de datos reiniciada exitosamente!"
echo "=========================================="


