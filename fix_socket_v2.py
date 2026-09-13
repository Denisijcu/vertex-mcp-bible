import os

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

# HACK TACTICO V2: Dynamic GID Mapping
# Leemos el ID del grupo dueño del socket de Windows, nos unimos a él, y lanzamos uvicorn.
RUN echo '#!/bin/bash\\n\\
SOCKET_GID=$(stat -c "%g" /var/run/docker.sock 2>/dev/null || echo "0")\\n\\
groupadd -g $SOCKET_GID docker_sock_group 2>/dev/null || true\\n\\
usermod -aG docker_sock_group vertex_mcp 2>/dev/null || true\\n\\
exec runuser -u vertex_mcp -- uvicorn main:app --host 0.0.0.0 --port 8000' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
"""
with open("servers/04-mcp-infra/Dockerfile", "w", encoding="utf-8", newline="\n") as f:
    f.write(dockerfile_content)

print("[+] Arquitectura 'Dynamic GID Mapping' aplicada al Nodo 04.")