@echo off
REM ==============================================================================
REM VERTEX INTELLIGENCE CORE (VIC) - MCP MONOREPO MAKE (WINDOWS BATCH)
REM ==============================================================================
SET COMPOSE_FILE=infra\docker-compose.yml

IF "%1"=="build-recon" GOTO build-recon
IF "%1"=="up" GOTO up
IF "%1"=="down" GOTO down
IF "%1"=="logs-recon" GOTO logs-recon
IF "%1"=="test-recon" GOTO test-recon
IF "%1"=="clean" GOTO clean
GOTO help

:build-recon
echo [+] Compilando imagen Docker para mcp-recon (Hardened)...
docker-compose -f %COMPOSE_FILE% build mcp-recon
GOTO end

:up
echo [+] Levantando perimetro de red y servidores MCP...
docker-compose -f %COMPOSE_FILE% up -d
GOTO end

:down
echo [-] Derribando infraestructura...
docker-compose -f %COMPOSE_FILE% down --remove-orphans
GOTO end

:logs-recon
docker logs -f mcp-server-recon
GOTO end

:test-recon
echo [!] Iniciando asalto de prueba a traves de Traefik (Puerto 8000)...
curl.exe -s -X POST http://localhost:8000/api/v1/mcp/recon/execute ^
     -H "Content-Type: application/json" ^
     -H "X-MCP-Access-Token: vertex-super-secret-key-2026" ^
     -d "{\"jsonrpc\":\"2.0\",\"method\":\"nmap_fast_scan\",\"params\":{\"target\":\"127.0.0.1\"},\"id\":\"test-001\"}"
GOTO end

:clean
echo [!] Limpiando recursos huerfanos de Docker...
docker system prune -f
GOTO end

:help
echo Vertex MCP Bible - Gestion de Nodos (Windows)
echo -------------------------------------------------
echo Comandos disponibles:
echo   make build-recon : Compila la imagen segura de mcp-recon
echo   make up          : Levanta la infraestructura
echo   make down        : Apaga los contenedores
echo   make logs-recon  : Muestra logs de mcp-recon
echo   make test-recon  : Lanza un payload de prueba
echo   make clean       : Limpia Docker

:end