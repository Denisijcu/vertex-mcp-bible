import uuid
import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.services.mcp_manager import mcp_service
from app.services.mcp_executor import MCPProcessExecutor
from app.services.synthesis_service import synthesize_report
from app.services.agent_service import run_agent
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


# =========================================================================
# FASE 2 - Mision local: el backend ejecuta herramientas MCP locales (stdio)
# y le pasa los resultados a Gemma para la sintesis. Gemma NO ejecuta tools,
# solo analiza lo ya ejecutado -> sin loop de agente, sin timeout de LM Studio.
# Reutiliza TASKS_DB y el polling de /mcp/tasks/{task_id}.
# =========================================================================

async def run_local_mission(task_id: str, body: dict):
    TASKS_DB[task_id] = {"status": "RUNNING", "report": None}
    try:
        task = body.get("task", "")
        invocations = body.get("invocations", []) or []
        active = mcp_service.get_active_servers()

        results = []
        for inv in invocations:
            server_name = inv.get("server_name")
            tool_name = inv.get("tool_name")
            arguments = inv.get("arguments", {}) or {}

            if not server_name or server_name not in active:
                results.append({
                    "server": server_name, "tool": tool_name,
                    "status": "error", "detail": "Server no activo o no sincronizado.",
                })
                continue

            res = await MCPProcessExecutor.call_tool(
                server_name, active[server_name], tool_name, arguments
            )
            results.append(res)

        report = await synthesize_report(task, results)
        TASKS_DB[task_id] = {
            "status": "COMPLETED",
            "report": report,
            "raw_results": results,
        }
    except Exception as exc:
        print(f"[LOCAL MISSION EXCEPTION] {repr(exc)}")
        TASKS_DB[task_id] = {
            "status": "FAILED",
            "report": f"Error en mision local: {str(exc)}",
        }


@router.post("/local-mission/execute", status_code=202)
async def local_mission(request: Request, background_tasks: BackgroundTasks):
    """
    Ejecuta una mision usando herramientas MCP locales + sintesis de Gemma.

    Body esperado:
      { "task": "analiza estos datos ...",
        "invocations": [
          {"server_name": "mi-calculadora", "tool_name": "media",
           "arguments": {"lista": [10, 20, 30]}}
        ] }
    """
    body = await request.json()
    task_id = str(uuid.uuid4())
    TASKS_DB[task_id] = {"status": "QUEUED", "report": None}
    background_tasks.add_task(run_local_mission, task_id, body)
    return {
        "task_id": task_id,
        "status": "QUEUED",
        "message": "Mision local despachada (herramientas + sintesis).",
    }


# =========================================================================
# MODO AGENTE - El modelo decide que herramientas usar (function calling).
# El usuario solo escribe en lenguaje natural; el loop lo maneja el backend
# (no LM Studio), asi se esquiva el timeout. Reutiliza TASKS_DB + polling.
# =========================================================================

async def run_agentic_mission(task_id: str, body: dict):
    TASKS_DB[task_id] = {"status": "RUNNING", "report": None}
    try:
        prompt = body.get("prompt") or body.get("task") or ""
        active = mcp_service.get_active_servers()
        result = await run_agent(prompt, active)
        TASKS_DB[task_id] = {
            "status": "COMPLETED",
            "report": result.get("report", ""),
            "trace": result.get("trace", []),
        }
    except Exception as exc:
        print(f"[AGENT EXCEPTION] {repr(exc)}")
        TASKS_DB[task_id] = {"status": "FAILED", "report": f"Error en el agente: {str(exc)}"}


@router.post("/agent/execute", status_code=202)
async def agentic_mission(request: Request, background_tasks: BackgroundTasks):
    """
    Modo agente: el usuario escribe en lenguaje natural y el modelo decide que
    herramientas MCP invocar (de los servers activos) y con que argumentos.

    Body esperado:  { "prompt": "analiza estos tiempos 12,15,340,11,14 y busca anomalias" }
    """
    body = await request.json()
    task_id = str(uuid.uuid4())
    TASKS_DB[task_id] = {"status": "QUEUED", "report": None}
    background_tasks.add_task(run_agentic_mission, task_id, body)
    return {
        "task_id": task_id,
        "status": "QUEUED",
        "message": "Mision agentica despachada (el modelo elige las herramientas).",
    }