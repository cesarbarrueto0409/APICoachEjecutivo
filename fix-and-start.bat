@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   API COACH EJECUTIVO - DOCKER START
echo ========================================
echo.

REM Verificar si Docker esta instalado
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker no esta instalado o no esta en el PATH
    echo Por favor instala Docker Desktop desde: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Verificar si Docker esta corriendo
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker no esta corriendo
    echo Por favor inicia Docker Desktop y espera a que este listo
    pause
    exit /b 1
)

REM Verificar si existe el archivo .env
if not exist ".env" (
    echo ERROR: No se encuentra el archivo .env
    echo Por favor crea un archivo .env con las variables de entorno necesarias
    pause
    exit /b 1
)

echo Paso 1: Deteniendo contenedores existentes...
docker-compose down
if errorlevel 1 (
    echo ADVERTENCIA: Error al detener contenedores (puede ser normal si no habia contenedores corriendo)
)

echo.
echo Paso 2: Limpiando imagenes antiguas...
docker-compose down --rmi local --volumes --remove-orphans
if errorlevel 1 (
    echo ADVERTENCIA: Error al limpiar imagenes antiguas
)

echo.
echo Paso 3: Reconstruyendo imagen (esto puede tomar unos minutos)...
docker-compose build --no-cache
if errorlevel 1 (
    echo ERROR: Fallo al construir la imagen Docker
    echo Revisa los logs arriba para mas detalles
    pause
    exit /b 1
)

echo.
echo Paso 4: Iniciando servicios con uvicorn...
echo El servidor estara disponible en: http://localhost:8000
echo Documentacion API en: http://localhost:8000/docs
echo.
echo Presiona Ctrl+C para detener el servidor
echo.
docker-compose up
if errorlevel 1 (
    echo ERROR: Fallo al iniciar los servicios
    echo Revisa los logs arriba para mas detalles
    pause
    exit /b 1
)

echo.
echo ========================================
echo   SERVIDOR DETENIDO
echo ========================================
pause
