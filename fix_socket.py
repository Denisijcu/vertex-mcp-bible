import os

# 1. Parchear el Dockerfile con el patrón Privilege Dropping
dockerfile_content = """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app

RUN useradd -m -s /bin/bash vertex_mcp
WORKDIR /app

COPY servers/04-mcp-infra/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core_shared/ /app/core_shared/
COPY servers/04-mcp-infra/main.py /app/main.py

RUN chown -R vertex_mcp:vertex_mcp /app

# HACK TÁCTICO: Privilege Dropping
# Entramos como root temporalmente, abrimos el socket y lanzamos la app como vertex_mcp
RUN echo '#!/bin/bash\\nchmod 666 /var/run/docker.sock 2>/dev/null || true\\nexec runuser -u vertex_mcp -- uvicorn main:app --host 0.0.0.0 --port 8000' > /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# Iniciamos el contenedor ejecutando el script (PID 1)
CMD ["/app/entrypoint.sh"]
"""
with open("servers/04-mcp-infra/Dockerfile", "w", encoding="utf-8", newline="\n") as f:
    f.write(dockerfile_content)

# 2. Modificar el volumen en docker-compose de ro a rw solo para mcp-infra
with open("infra/docker-compose.yml", "r", encoding="utf-8") as f:
    lines = f.readlines()

with open("infra/docker-compose.yml", "w", encoding="utf-8", newline="\n") as f:
    in_infra = False
    for line in lines:
        if "mcp-server-infra" in line:
            in_infra = True
        
        # Quitamos el :ro solo cuando estamos dentro de la sección de infra
        if in_infra and '"/var/run/docker.sock:/var/run/docker.sock:ro"' in line:
            line = line.replace(':ro"', '"')
            in_infra = False 
        
        f.write(line)

print("[+] Arquitectura 'Privilege Dropping' aplicada al Nodo 04 de Infraestructura.")