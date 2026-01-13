# Script PowerShell para reiniciar la base de datos en Docker
# Uso: .\scripts\reset_db_docker.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Reiniciando base de datos en Docker..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Ejecutar el script de reset dentro del contenedor de la API
docker compose exec api python scripts/reset_database.py

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Base de datos reiniciada exitosamente!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green


