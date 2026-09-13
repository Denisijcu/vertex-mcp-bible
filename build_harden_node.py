import os

os.makedirs("servers/05-mcp-harden", exist_ok=True)

# 1. Dockerfile con Socat y Privilege Dropping (igual que mcp-infra para mantener acceso al socket)
dockerfile_content = """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash vertex_mcp
WORKDIR /app

COPY servers/05-mcp-harden/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core_shared/ /app/core_shared/
COPY servers/05-mcp-harden/main.py /app/main.py

RUN chown -R vertex_mcp:vertex_mcp /app

RUN echo '#!/bin/bash\\n\\
socat TCP-LISTEN:2375,fork,bind=127.0.0.1 UNIX-CONNECT:/var/run/docker.sock &\\n\\
exec runuser -u vertex_mcp -- uvicorn main:app --host 0.0.0.0 --port 8000' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
"""
with open("servers/05-mcp-harden/Dockerfile", "w", encoding="utf-8", newline="\n") as f:
    f.write(dockerfile_content)

# 2. Requerimientos
requirements_content = """fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.4
docker==7.0.0
"""
with open("servers/05-mcp-harden/requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(requirements_content)

# 3. main.py (Motor de Hardening Automático)
main_content = """from fastapi import FastAPI, Depends, HTTPException
import uvicorn
import docker
from core_shared.security import verify_mcp_token
from core_shared.mcp_protocol import MCPBaseRequest, MCPBaseResponse
from core_shared.logging_config import setup_secure_logger

logger = setup_secure_logger("mcp-harden")
app = FastAPI(title="MCP Active Hardening & Remediation Node", version="1.0.0")

def get_docker_client():
    try:
        return docker.DockerClient(base_url='tcp://127.0.0.1:2375')
    except Exception as e:
        logger.error(f"Error conectando al puente Docker: {e}")
        return None

@app.post("/api/v1/mcp/harden/execute", response_model=MCPBaseResponse)
async def execute_hardening(request: MCPBaseRequest, token: str = Depends(verify_mcp_token)):
    logger.info(f"Peticion de Remediation Activa: '{request.method}'")
    
    try:
        if request.method == "generate_hardening_patch":
            target_image = request.params.get("image", "python:3.11-slim")
            
            # Plantilla estandar de Dockerfile seguro (Hardening de Vertex Coders)
            hardened_template = f\"\"\"# --- VERTEX CODERS SECURE DOCKERFILE TEMPLATE ---
FROM {target_image}

# 1. Variables de entorno optimizadas para seguridad
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

# 2. Creacion de usuario sin privilegios (Principio de Menor Privilegio)
RUN useradd -m -s /bin/bash vertex_secure_user
WORKDIR /app

# 3. Copia de dependencias y codigo con control estricto de dueños
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R vertex_secure_user:vertex_secure_user /app

# 4. Degradacion obligatoria de privilegios
USER vertex_secure_user

# 5. Restricciones de capacidades del Kernel recomendadas para docker-compose:
# cap_drop:
#   - ALL
# read_only: true
\"\"\"
            return MCPBaseResponse(
                id=request.id,
                result={
                    "status": "Parche de hardening generado con exito",
                    "target_image": target_image,
                    "hardening_patch": hardened_template
                }
            )
        else:
            raise HTTPException(status_code=400, detail=f"Metodo de remediacion no reconocido: {request.method}")

    except Exception as e:
        logger.error(f"Falla en el modulo de hardening: {str(e)}")
        return MCPBaseResponse(id=request.id, error={"code": 500, "message": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
with open("servers/05-mcp-harden/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(main_content)

print("[+] Nodo 05 (mcp-harden) generado con exito.")