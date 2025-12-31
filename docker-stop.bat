@echo off
echo ========================================
echo Stopping Agent 2 Docker Stack
echo ========================================
echo.

REM Check Docker availability and compose command
where docker >nul 2>&1
if errorlevel 1 (
  echo [ERRORE] Docker non risulta installato o non e' nel PATH.
  echo Scarica Docker Desktop: https://www.docker.com/products/docker-desktop
  pause
  exit /b 1
)

set "DC=docker-compose"
docker-compose version >nul 2>&1
if errorlevel 1 (
  docker compose version >nul 2>&1
  if errorlevel 1 (
    echo [ERRORE] Ne' 'docker-compose' ne' 'docker compose' disponibili.
    pause
    exit /b 1
  ) else (
    set "DC=docker compose"
  )
)

set /p CONFIRM="Fermare tutti i container? (s/N): "
if /i not "%CONFIRM%"=="s" (
 echo Operazione annullata.
 pause
 exit /b 0
)

echo.
echo Stopping containers...
%DC% down

echo.
echo ========================================
echo Stack fermato
echo ========================================
echo.

set /p CLEANUP="Rimuovere anche i volumi (dati)? (s/N): "
if /i "%CLEANUP%"=="s" (
 echo.
 echo Rimozione volumi...
 %DC% down -v
 echo OK Volumi rimossi
)

echo.
pause
