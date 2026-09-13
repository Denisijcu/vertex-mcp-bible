import os

os.makedirs("servers/04-mcp-infra", exist_ok=True)

# 1. Dockerfile endurecido (Hardened)
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
USER vertex_mcp

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
with open("servers/04-mcp-infra/Dockerfile", "w", encoding="utf-8", newline="\n") as f:
    f.write(dockerfile_content)

# 2. Dependencias
requirements_content = """fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.4
docker==7.0.0
psutil==5.9.8
"""
with open("servers/04-mcp-infra/requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(requirements_content)

# 3. main.py (El Auditor)
main_content = """from fastapi import FastAPI, Depends, HTTPException
import uvicorn
import docker
import psutil
import platform
from core_shared.security import verify_mcp_token
from core_shared.mcp_protocol import MCPBaseRequest, MCPBaseResponse
from core_shared.logging_config import setup_secure_logger

logger = setup_secure_logger("mcp-infra")
app = FastAPI(title="MCP Infrastructure & SecOps Node", version="1.0.0")

def get_docker_client():
    try:
        return docker.from_env()
    except Exception as e:
        logger.error(f"Error conectando al socket de Docker: {e}")
        return None

@app.post("/api/v1/mcp/infra/execute", response_model=MCPBaseResponse)
async def execute_infra_ops(request: MCPBaseRequest, token: str = Depends(verify_mcp_token)):
    logger.info(f"Auditoria de Infraestructura Solicitada: '{request.method}'")
    
    try:
        if request.method == "audit_containers":
            client = get_docker_client()
            if not client:
                raise ValueError("No hay acceso al socket de Docker. Revisa los permisos de /var/run/docker.sock")
            
            containers_info = []
            for container in client.containers.list():
                # Extraccion de metadata de seguridad
                is_privileged = container.attrs['HostConfig']['Privileged']
                user = container.attrs['Config']['User'] or "root"
                
                # Flag de seguridad si corre como root o privilegiado
                security_warning = False
                if user == "root" or is_privileged:
                    security_warning = True
                
                containers_info.append({
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "user": user,
                    "is_privileged": is_privileged,
                    "security_risk": security_warning
                })
                
            return MCPBaseResponse(
                id=request.id, 
                result={"status": "Auditoria de contenedores completada", "containers": containers_info}
            )
            
        elif request.method == "system_health":
            health_data = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "ram_usage_mb": round(psutil.virtual_memory().used / (1024 * 1024), 2),
                "ram_total_mb": round(psutil.virtual_memory().total / (1024 * 1024), 2),
                "os": platform.system(),
                "architecture": platform.machine()
            }
            return MCPBaseResponse(
                id=request.id, 
                result={"status": "Telemetria de host capturada", "health": health_data}
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Metodo no reconocido: {request.method}")

    except Exception as e:
        logger.error(f"Falla en el modulo de infraestructura: {str(e)}")
        return MCPBaseResponse(id=request.id, error={"code": 500, "message": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
with open("servers/04-mcp-infra/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(main_content)

print("[+] Esqueleto del servidor 'mcp-infra' generado exitosamente.")