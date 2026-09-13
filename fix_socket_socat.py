import os

# 1. Inyectar Socat en el Dockerfile
dockerfile_content = """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app

# Instalar socat para el puente de red interno
RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash vertex_mcp
WORKDIR /app

COPY servers/04-mcp-infra/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core_shared/ /app/core_shared/
COPY servers/04-mcp-infra/main.py /app/main.py

RUN chown -R vertex_mcp:vertex_mcp /app

# HACK TACTICO V3: Socat TCP Proxy
# socat (root) hace puente entre un puerto TCP y el socket de Docker.
# uvicorn (vertex_mcp) consume la API desde el puerto TCP de manera segura.
RUN echo '#!/bin/bash\\n\\
socat TCP-LISTEN:2375,fork,bind=127.0.0.1 UNIX-CONNECT:/var/run/docker.sock &\\n\\
exec runuser -u vertex_mcp -- uvicorn main:app --host 0.0.0.0 --port 8000' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
"""
with open("servers/04-mcp-infra/Dockerfile", "w", encoding="utf-8", newline="\n") as f:
    f.write(dockerfile_content)

# 2. Modificar main.py para apuntar al puente TCP
with open("servers/04-mcp-infra/main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

main_code = main_code.replace(
    "return docker.from_env()",
    "return docker.DockerClient(base_url='tcp://127.0.0.1:2375')"
)

with open("servers/04-mcp-infra/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(main_code)

print("[+] Arquitectura 'Socat TCP Proxy' aplicada al Nodo 04.")