import subprocess
from fastapi import FastAPI, Depends, HTTPException
import uvicorn

from core_shared.security import verify_mcp_token
from core_shared.mcp_protocol import MCPBaseRequest, MCPBaseResponse
from core_shared.logging_config import setup_secure_logger

logger = setup_secure_logger("mcp-recon")

app = FastAPI(title="MCP Reconnaissance Node", version="1.0.0")

@app.post("/api/v1/mcp/recon/execute", response_model=MCPBaseResponse)
async def execute_recon(request: MCPBaseRequest, token: str = Depends(verify_mcp_token)):
    logger.info(f"Peticion recibida: Accion '{request.method}'")
    target = request.params.get("target")
    if not target:
        raise HTTPException(status_code=400, detail="El parametro 'target' es obligatorio.")

    if request.method == "nmap_fast_scan":
        cmd = ["nmap", "-F", "-T4", target]
    elif request.method == "gobuster_scan":
        cmd = ["gobuster", "dir", "-u", f"http://{target}", "-w", "/usr/share/wordlists/dirb/common.txt", "-q"]
    else:
        raise HTTPException(status_code=400, detail=f"Metodo no reconocido.")

    try:
        # Ejecucion segura sin shell
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        return MCPBaseResponse(id=request.id, result={"tool": request.method, "target": target, "output": result.stdout})
    except subprocess.TimeoutExpired:
        return MCPBaseResponse(id=request.id, error={"code": 504, "message": "Timeout en ejecucion"})
    except Exception as e:
        return MCPBaseResponse(id=request.id, error={"code": 500, "message": "Fallo interno en nodo"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
