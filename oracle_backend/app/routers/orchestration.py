import uuid
import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.services.mcp_manager import mcp_service
import os


router = APIRouter(prefix="/mcp", tags=["Orchestration"])

# Almacenamiento en memoria temporal para las tareas
TASKS_DB = {}

# Esquema estricto para atrapar el request de Angular y blindar el campo method
class OrchestrateRequest(BaseModel):
    prompt: str
    target_ip: str
    method: Optional[str] = "standard_audit"  # Valor por defecto si Angular no lo manda
    payload_file: Optional[str] = None

async def run_vic_task(task_id: str, body: dict):
    TASKS_DB[task_id] = {"status": "RUNNING", "report": None}
        # host.docker.internal solo resuelve DENTRO de un contenedor. Con el backend suelto
    # en Windows, el orquestador se alcanza por localhost. Env var para ambos modos.
    orchestrator_host = os.getenv("VIC_ORCHESTRATOR_HOST", "localhost")
    vic_orchestrator_url = f"http://{orchestrator_host}:8003/api/v1/mcp/orchestrate/execute"
    headers = {
        "X-MCP-Access-Token": "vertex-super-secret-key-2026",
        "Content-Type": "application/json"
    }
    
    # Construimos el payload en el formato JSON-RPC que el orquestador (8003) espera.
    # El orquestador valida como MCPBaseRequest y lee params.task / params.target.
    # Antes mandabamos prompt/target_ip planos y los ignoraba, cayendo a sus defaults
    # ("Auditoria estandar" / 127.0.0.1); por eso tu prompt nunca llegaba al LLM.
    mcp_payload = {
        "jsonrpc": "2.0",
        "method": body.get("method") or "standard_audit",
        "params": {
            "task": body.get("prompt", ""),
            "target": body.get("target_ip", "127.0.0.1"),
            "active_mcp_servers": mcp_service.get_active_servers()
        },
        "id": task_id
    }

    print(f"🔥 PAYLOAD FINAL ENVIADO A DOCKER (8003): {mcp_payload}")

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            response = await client.post(vic_orchestrator_url, json=mcp_payload, headers=headers)
            raw_text = response.text
            try:
                res_data = response.json()
            except Exception:
                res_data = raw_text

            output = ""
            if isinstance(res_data, dict):
                if "choices" in res_data and len(res_data["choices"]) > 0:
                    output = res_data["choices"][0].get("message", {}).get("content", "")
                elif "result" in res_data:
                    res_val = res_data["result"]
                    if isinstance(res_val, dict):
                        output = res_val.get("content", [{}])[0].get("text", str(res_val))
                    else:
                        output = str(res_val)
                else:
                    output = str(res_data)
            else:
                output = str(res_data)
            
            if not output.strip():
                output = raw_text

            TASKS_DB[task_id] = {"status": "COMPLETED", "report": output}
        except Exception as exc:
            print(f"[CRITICAL TASK EXCEPTION] {repr(exc)}")
            TASKS_DB[task_id] = {"status": "FAILED", "report": f"Error de comunicación con VIC: {str(exc)}"}

@router.post("/orchestrate/execute", status_code=202)
async def async_orchestrate(request: Request, background_tasks: BackgroundTasks):
    # Capturamos el JSON crudo tal cual lo manda Angular
    body = await request.json()
    
    # Si Angular no manda el método, lo inyectamos de forma segura aquí mismo
    if "method" not in body or not body["method"]:
        body["method"] = "standard_audit"
        
    print(f"🚀 PAYLOAD LISTO PARA DESPACHO: {body}")
    
    task_id = str(uuid.uuid4())
    TASKS_DB[task_id] = {"status": "QUEUED", "report": None}
    background_tasks.add_task(run_vic_task, task_id, body)
    
    return {
        "task_id": task_id,
        "status": "QUEUED",
        "message": "Misión despachada al clúster de VIC en segundo plano."
    }

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in TASKS_DB:
        raise HTTPException(status_code=404, detail="ID de tarea no encontrado.")
    return TASKS_DB[task_id]

@router.post("/servers/sync")
async def sync_mcp_servers(request: Request):
    payload = await request.json()
    count = mcp_service.sync_servers(payload)
    return {
        "status": "success",
        "synced_servers_count": count,
        "message": f"Sincronizados {count} servidores MCP correctamente con el Core."
    }