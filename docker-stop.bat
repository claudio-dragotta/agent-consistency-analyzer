@echo off
echo ========================================
echo Stopping Agent 2 Docker Stack
echo ========================================
echo.

set /p CONFIRM="Fermare tutti i container? (s/N): "
if /i not "%CONFIRM%"=="s" (
 echo Operazione annullata.
 pause
 exit /b 0
)

echo.
echo Stopping containers...
docker-compose -f docker-compose.prod.yml down

echo.
echo ========================================
echo Stack fermato
echo ========================================
echo.

set /p CLEANUP="Rimuovere anche i volumi (dati)? (s/N): "
if /i "%CLEANUP%"=="s" (
 echo.
 echo Rimozione volumi...
 docker-compose -f docker-compose.prod.yml down -v
 echo OK Volumi rimossi
)

echo.
pause
