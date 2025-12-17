@echo off
echo ========================================
echo Agent 2 - Scale Consumers
echo ========================================
echo.
echo Attualmente consumer attivi:
docker ps --filter "name=agent2-consumer" --format "table {{.Names}}\t{{.Status}}"
echo.

set /p REPLICAS="Numero di consumer da avviare (1-10): "

if %REPLICAS% LSS 1 (
 echo Errore: minimo 1 replica
 pause
 exit /b 1
)

if %REPLICAS% GTR 10 (
 echo Errore: massimo 10 repliche
 pause
 exit /b 1
)

echo.
echo Scaling a %REPLICAS% replica(s)...
docker-compose -f docker-compose.prod.yml up -d --scale agent2-consumer=%REPLICAS%

echo.
echo OK Scaling completato
echo.
echo Consumer attivi:
docker ps --filter "name=agent2-consumer" --format "table {{.Names}}\t{{.Status}}"
echo.
echo Performance attesa: %REPLICAS% x 4 workers = circa %REPLICAS%0 analisi/minuto
echo.

pause
