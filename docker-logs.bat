@echo off
echo ========================================
echo Agent 2 - Docker Logs Viewer
echo ========================================
echo.
echo Seleziona quale container visualizzare:
echo.
echo 1. Agent 2 API
echo 2. Agent 2 Consumer (Kafka)
echo 3. Kafka Broker
echo 4. Zookeeper
echo 5. Tutti (interleaved)
echo 6. N8N
echo 7. Kafka UI
echo.

set /p CHOICE="Scelta (1-7): "

if "%CHOICE%"=="1" (
 echo.
 echo === Agent 2 API Logs ===
 docker logs -f --tail 100 agent2-api
)

if "%CHOICE%"=="2" (
 echo.
 echo === Agent 2 Consumer Logs ===
 docker logs -f --tail 100 agent2-consumer
)

if "%CHOICE%"=="3" (
 echo.
 echo === Kafka Broker Logs ===
 docker logs -f --tail 100 agent2-kafka
)

if "%CHOICE%"=="4" (
 echo.
 echo === Zookeeper Logs ===
 docker logs -f --tail 100 agent2-zookeeper
)

if "%CHOICE%"=="5" (
 echo.
 echo === All Logs ===
 docker-compose -f docker-compose.prod.yml logs -f --tail 50
)

if "%CHOICE%"=="6" (
 echo.
 echo === N8N Logs ===
 docker logs -f --tail 100 agent2-n8n
)

if "%CHOICE%"=="7" (
 echo.
 echo === Kafka UI Logs ===
 docker logs -f --tail 100 agent2-kafka-ui
)

pause
