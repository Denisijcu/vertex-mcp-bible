# ==============================================================================
# VERTEX INTELLIGENCE CORE (VIC) - MCP MONOREPO MAKEFILE
# ==============================================================================
.PHONY: help build-recon up down logs-recon test-recon clean

# Variables de Infraestructura
COMPOSE_FILE = infra/docker-compose.yml

help:
	@echo "Vertex MCP Bible - Gestión de Nodos"
	@echo "-------------------------------------------------"
	@echo "Comandos disponibles:"
	@echo "  make build-recon : Compila la imagen segura de mcp-recon (incluye core_shared)"
	@echo "  make up          : Levanta la infraestructura (API Gateway + Nodos)"
	@echo "  make down        : Apaga los contenedores y destruye la red aislada"
	@echo "  make logs-recon  : Muestra logs en tiempo real del nodo ofensivo"
	@echo "  make test-recon  : Lanza un payload de prueba al nodo a través de Traefik"
	@echo "  make clean       : Limpia el sistema de contenedores huérfanos"

# ------------------------------------------------------------------------------
# CONSTRUCCIÓN Y DESPLIEGUE
# ------------------------------------------------------------------------------
build-recon:
	@echo "[+] Compilando imagen Docker para mcp-recon (Hardened)..."
	docker-compose -f $(COMPOSE_FILE) build mcp-recon

up:
	@echo "[+] Levantando perímetro de red y servidores MCP..."
	docker-compose -f $(COMPOSE_FILE) up -d

down:
	@echo "[-] Derribando infraestructura..."
	docker-compose -f $(COMPOSE_FILE) down --remove-orphans

clean:
	@echo "[!] Limpiando recursos huérfanos de Docker..."
	docker system prune -f

# ------------------------------------------------------------------------------
# OPERACIONES Y TESTING
# ------------------------------------------------------------------------------
logs-recon:
	docker logs -f mcp-server-recon

test-recon:
	@echo "[!] Iniciando asalto de prueba a través de Traefik (Puerto 8000)..."
	curl -s -X POST http://localhost:8000/api/v1/mcp/recon/execute \
	     -H "Content-Type: application/json" \
	     -H "X-MCP-Access-Token: vertex-super-secret-key-2026" \
	     -d '{"jsonrpc": "2.0", "method": "nmap_fast_scan", "params": {"target": "127.0.0.1"}, "id": "test-001"}' | jq .