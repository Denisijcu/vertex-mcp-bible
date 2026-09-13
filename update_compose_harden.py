with open("infra/docker-compose.yml", "r", encoding="utf-8") as f:
    content = f.read()

# Añadimos el servicio mcp-harden antes de la sección de redes/volúmenes
new_service = """  mcp-harden:
    build:
      context: ../
      dockerfile: servers/05-mcp-harden/Dockerfile
    container_name: mcp-server-harden
    ports:
      - "8005:8000"
    environment:
      - MCP_SECRET=vertex-super-secret-key-2026
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:rw"
    networks:
      - mcp_secure_net
    restart: unless-stopped

networks:"""

content = content.replace("networks:", new_service)

with open("infra/docker-compose.yml", "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("[+] docker-compose.yml actualizado con mcp-harden (Puerto 8005).")