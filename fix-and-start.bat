@echo off
echo ========================================
echo   API COACH EJECUTIVO - DOCKER START
echo ========================================
echo.
echo Paso 1: Deteniendo contenedores existentes...
docker-compose down

echo.
echo Paso 2: Reconstruyendo imagen (esto puede tomar unos minutos)...
docker-compose build --no-cache

echo.
echo Paso 3: Iniciando servicios con uvicorn...
echo El servidor estara disponible en: http://localhost:8000
echo Documentacion API en: http://localhost:8000/docs
echo.
docker-compose up

echo.
echo ========================================
echo   SERVIDOR DETENIDO
echo ========================================
pause
