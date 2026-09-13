import os

compose_code = """version: '3.8'

services:
  api-gateway:
    image: traefik:v3.0
    container_name: mcp-api-gateway
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
    ports:
      - "8000:80"     # Tráfico a través de Traefik (Perímetro)
      - "8080:8080"   # Dashboard de Traefik
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
    networks:
      - mcp_secure_net

  mcp-recon:
    build:
      context: ../
      dockerfile: servers/01-mcp-recon/Dockerfile
    container_name: mcp-server-recon
    ports:
      - "8001:8000"   # BYPASS: Puerto directo a FastAPI para pruebas
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=mcp_secure_net"
      - "traefik.http.routers.recon.rule=PathPrefix(`/api/v1/mcp/recon`)"
      - "traefik.http.routers.recon.entrypoints=web"
      - "traefik.http.services.recon.loadbalancer.server.port=8000"
    environment:
      - MCP_SECRET=vertex-super-secret-key-2026
    networks:
      - mcp_secure_net
    restart: unless-stopped

networks:
  mcp_secure_net:
    driver: bridge
"""

with open("infra/docker-compose.yml", "w", encoding="utf-8", newline="\n") as f:
    f.write(compose_code)

print("[+] Archivo docker-compose.yml regenerado con Bypass (Puerto 8001) y red forzada.")