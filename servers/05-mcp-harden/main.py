from fastapi import FastAPI, Depends, HTTPException
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
            hardened_template = f"""# --- VERTEX CODERS SECURE DOCKERFILE TEMPLATE ---
FROM {target_image}

# 1. Variables de entorno optimizadas para seguridad
ENV PYTHONDONTWRITEBYTECODE=1 \
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
"""
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
