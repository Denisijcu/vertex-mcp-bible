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
      - "8000:80"
      - "8080:8080"
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
      - "8001:8000"   # BYPASS RECON
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.recon.rule=PathPrefix(`/api/v1/mcp/recon`)"
      - "traefik.http.services.recon.loadbalancer.server.port=8000"
    environment:
      - MCP_SECRET=vertex-super-secret-key-2026
    networks:
      - mcp_secure_net
    restart: unless-stopped

  mcp-vector:
    build:
      context: ../
      dockerfile: servers/02-mcp-vector/Dockerfile
    container_name: mcp-server-vector
    ports:
      - "8002:8000"   # BYPASS VECTOR
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.vector.rule=PathPrefix(`/api/v1/mcp/vector`)"
      - "traefik.http.services.vector.loadbalancer.server.port=8000"
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
print("[+] Orquestador regenerado. Nodos Recon (8001) y Vector (8002) en linea.")