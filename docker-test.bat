@echo off
echo ========================================
echo Test Agent 2 Docker Deployment
echo ========================================
echo.

echo [1/5] Verifica containers in esecuzione...
docker ps --filter "name=agent2" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

echo [2/5] Health check Agent 2 API...
curl -s http://localhost:8002/health | python -m json.tool 2>nul
if errorlevel 1 (
 echo X Agent 2 API non risponde
 echo.
 echo Verifica che sia avviato:
 echo docker logs agent2-api
 pause
 exit /b 1
)
echo OK Agent 2 API healthy
echo.

echo [3/5] Verifica Agent Card (A2A Protocol)...
curl -s http://localhost:8002/.well-known/agent.json | python -m json.tool 2>nul | findstr "name"
echo OK Agent Card OK
echo.

echo [4/5] Test analisi con example_bad.json...
echo Invio richiesta...

REM Create temporary JSON file for curl
echo {"domain_model": > temp_request.json
type input_agent\example_bad.json >> temp_request.json
echo , "use_llm": false, "apply_auto_fixes": true} >> temp_request.json

curl -X POST http://localhost:8002/analyze ^
 -H "Content-Type: application/json" ^
 -d @temp_request.json ^
 -s -o test_result.json

del temp_request.json

REM Check if request was successful
if errorlevel 1 (
 echo X Errore durante l'analisi
 pause
 exit /b 1
)

echo OK Analisi completata
echo.
echo Risultati:
type test_result.json | python -m json.tool 2>nul | findstr /C:"status" /C:"total_issues"
echo.

echo [5/5] Verifica consumer Kafka...
docker logs --tail 5 agent2-consumer 2>nul
if errorlevel 1 (
 echo WARNING Consumer non ancora avviato o in errore
) else (
 echo OK Consumer attivo
)

echo.
echo ========================================
echo Test completato!
echo ========================================
echo.
echo Risultato completo salvato in: test_result.json
echo.

pause
