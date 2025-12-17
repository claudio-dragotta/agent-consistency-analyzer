@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo Agent 2 - Docker Deployment
echo ========================================
echo.

REM Check if .env exists, if not create from template
if not exist .env (
 echo Creazione file .env da template...
 copy .env.docker .env >nul
 echo OK File .env creato
 echo.
)

REM Check if user wants full stack or minimal
set /p MODE="Avvia stack completo con N8N e Kafka UI? (s/N): "
if /i "%MODE%"=="s" (
 set PROFILE=--profile full
 echo.
 echo Avvio stack COMPLETO...
) else (
 set PROFILE=
 echo.
 echo Avvio stack MINIMALE (solo Agent 2 + Kafka)...
)

echo.
echo [1/4] Build immagini Docker...
docker-compose -f docker-compose.prod.yml build

if errorlevel 1 (
 echo X Errore durante il build
 pause
 exit /b 1
)

echo.
echo [2/4] Avvio servizi...
docker-compose -f docker-compose.prod.yml up -d %PROFILE%

if errorlevel 1 (
 echo X Errore durante l'avvio
 pause
 exit /b 1
)

echo.
echo [3/4] Attesa inizializzazione servizi...
timeout /t 10 /nobreak >nul

echo.
echo [4/4] Verifica health status...
docker-compose -f docker-compose.prod.yml ps

echo.
echo ========================================
echo OK Deployment completato!
echo ========================================
echo.
echo Servizi disponibili:
echo - Agent 2 API: http://localhost:8002
echo - Health Check: http://localhost:8002/health
echo - API Docs: http://localhost:8002/docs

if /i "%MODE%"=="s" (
 echo - N8N: http://localhost:5678
 echo - Kafka UI: http://localhost:8080
)

echo.
echo Comandi utili:
echo - Logs Agent 2: docker logs -f agent2-api
echo - Logs Consumer: docker logs -f agent2-consumer
echo - Logs Kafka: docker logs -f agent2-kafka
echo - Stop tutto: docker-stop.bat
echo - Restart: docker-compose -f docker-compose.prod.yml restart
echo.
echo Per testare:
echo docker exec -it agent2-api curl http://localhost:8002/health
echo.

pause
