@echo off
echo ========================================
echo   REPARANDO Y REINICIANDO DOCKER
echo ========================================
echo.
echo Paso 1: Deteniendo contenedores...
docker-compose -f docker-compose.cloud.yml down

echo.
echo Paso 2: Reconstruyendo imagen (esto puede tomar unos minutos)...
docker-compose -f docker-compose.cloud.yml build --no-cache

echo.
echo Paso 3: Iniciando servicios...
docker-compose -f docker-compose.cloud.yml up

echo.
echo ========================================
echo   COMPLETADO
echo ========================================
