@echo off
echo ====================================
echo Test Interactive Loop Workflow
echo ====================================
echo.

echo [1/3] Verifico che i servizi siano attivi...
echo.

curl -s http://localhost:8002/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] Agent 2 API non risponde!
    echo.
    echo Soluzione:
    echo 1. Esegui START_DEMO.bat prima
    echo 2. Aspetta 30-60 secondi
    echo 3. Riprova questo script
    pause
    exit /b 1
)

echo [OK] Agent 2 API attivo
echo.

curl -s http://127.0.0.1:5678 >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] n8n non risponde!
    echo.
    echo Soluzione:
    echo 1. Esegui START_DEMO.bat prima
    echo 2. Aspetta 30-60 secondi
    echo 3. Riprova questo script
    pause
    exit /b 1
)

echo [OK] n8n attivo
echo.

echo [2/3] Invio modello demo al webhook...
echo.
echo IMPORTANTE:
echo - Devi aver importato workflow_complete_loop.json in n8n
echo - Devi aver attivato il workflow (interruttore verde)
echo.
echo Se non l'hai fatto:
echo 1. Apri http://127.0.0.1:5678
echo 2. Importa n8n/workflow_complete_loop.json
echo 3. Attiva il workflow
echo 4. Riprova questo script
echo.

timeout /t 5 /nobreak >nul

echo Invio richiesta...
curl -X POST http://127.0.0.1:5678/webhook/agent2-start ^
  -H "Content-Type: application/json" ^
  -d @input_agent\example_demo.json > response.html 2>nul

if %errorlevel% neq 0 (
    echo [ERRORE] Richiesta fallita!
    echo.
    echo Possibili cause:
    echo 1. Workflow non importato in n8n
    echo 2. Workflow non attivato
    echo 3. URL webhook errato
    echo.
    echo Controlla:
    echo - http://127.0.0.1:5678 (n8n deve essere accessibile)
    echo - Workflow deve avere interruttore verde (attivo)
    pause
    exit /b 1
)

echo [OK] Richiesta inviata con successo
echo.

echo [3/3] Apertura risultati nel browser...
echo.

if exist response.html (
    echo Risultato salvato in: response.html
    echo.
    echo Sto aprendo il form HTML nel browser...
    start response.html

    echo.
    echo ====================================
    echo TEST COMPLETATO
    echo ====================================
    echo.
    echo Cosa fare ora:
    echo 1. Controlla il form HTML aperto nel browser
    echo 2. Vedi i 3 problemi rilevati
    echo 3. Vedi le 3 domande generate
    echo 4. Rispondi alle domande nel form
    echo 5. Clicca "Invia Risposte"
    echo 6. Il workflow continua automaticamente
    echo.
    echo File temporaneo: response.html
    echo Puoi eliminarlo dopo il test.
    echo.
) else (
    echo [AVVISO] File response.html non trovato
    echo.
    echo Il webhook potrebbe aver risposto ma il file non è stato salvato.
    echo.
    echo Prova ad aprire direttamente:
    echo http://127.0.0.1:5678/webhook/agent2-start
    echo.
)

echo Link utili:
echo - n8n: http://127.0.0.1:5678
echo - Kafka UI: http://localhost:8080
echo - API Docs: http://localhost:8002/docs
echo.

pause
