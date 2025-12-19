@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo   DEMO AUTOMATICA - Agent 2
echo   Consistency ^& Conflict Analyzer
echo ========================================
echo.
echo Questa demo avviera' automaticamente:
echo  1. Docker con tutti i servizi
echo  2. n8n (workflow visuale)
echo  3. Kafka UI (monitoraggio messaggi)
echo.
echo E aprira' automaticamente le pagine web!
echo.
pause

REM Check if .env exists, if not create from template
if not exist .env (
 echo [1/6] Creazione file .env da template...
 copy .env.docker .env >nul
 echo OK File .env creato
 echo.
)

echo [2/6] Build immagini Docker...
docker-compose build

if errorlevel 1 (
 echo X Errore durante il build
 pause
 exit /b 1
)

echo.
echo [3/6] Avvio servizi (con n8n e Kafka UI)...
docker-compose up -d

if errorlevel 1 (
 echo X Errore durante l'avvio
 pause
 exit /b 1
)

echo.
echo [4/6] Attesa inizializzazione servizi...
echo Attendo 30 secondi per il startup completo...
timeout /t 30 /nobreak >nul

echo.
echo [5/6] Verifica health status...
docker-compose ps

echo.
echo [6/6] Apertura pagine web...
echo.

REM Aspetta ancora un po' per essere sicuri che n8n sia pronto
timeout /t 5 /nobreak >nul

REM Apri n8n nel browser predefinito
echo Apertura n8n (workflow visuale)...
start http://127.0.0.1:5678

REM Aspetta 2 secondi
timeout /t 2 /nobreak >nul

REM Apri Kafka UI
echo Apertura Kafka UI (monitoraggio messaggi)...
start http://localhost:8080

REM Aspetta 2 secondi
timeout /t 2 /nobreak >nul

REM Apri anche API Docs (opzionale)
echo Apertura API Docs (Swagger)...
start http://localhost:8002/docs

echo.
echo ========================================
echo OK Demo avviata con successo!
echo ========================================
echo.
echo Pagine aperte nel browser:
echo  1. n8n Workflow:     http://127.0.0.1:5678
echo  2. Kafka UI:         http://localhost:8080
echo  3. API Docs:         http://localhost:8002/docs
echo.
echo Servizi attivi:
echo  - Agent 2 API:       http://localhost:8002
echo  - Health Check:      http://localhost:8002/health
echo.
echo ========================================
echo PROSSIMI PASSI:
echo ========================================
echo.
echo 1. In n8n (http://127.0.0.1:5678):
echo    - Se prima volta: crea account (email/password)
echo    - Clicca "Workflows" ^> "Import from File"
echo    - Seleziona: n8n\workflow_demo_simple.json
echo    - Clicca "Execute Workflow" per vedere l'analisi
echo.
echo 2. In Kafka UI (http://localhost:8080):
echo    - Vai su "Topics"
echo    - Clicca "agent1-output" per vedere input
echo    - Clicca "agent2-output" per vedere risultati
echo.
echo 3. Per testare Agent 2:
echo    - Usa il workflow n8n (interfaccia visuale)
echo    - Oppure: docker exec -it agent2-api curl http://localhost:8002/health
echo.
echo ========================================
echo.
echo Per fermare tutto: docker-stop.bat
echo Per vedere logs: docker-logs.bat
echo.
pause
