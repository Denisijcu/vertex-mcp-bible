import os

# 1. Crear el directorio del servidor 03
os.makedirs("servers/03-mcp-orchestrator", exist_ok=True)

# 2. Dockerfile para mcp-orchestrator
dockerfile_content = """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app

RUN useradd -m -s /bin/bash vertex_mcp
WORKDIR /app

COPY servers/03-mcp-orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core_shared/ /app/core_shared/
COPY servers/03-mcp-orchestrator/main.py /app/main.py

RUN chown -R vertex_mcp:vertex_mcp /app
USER vertex_mcp

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
with open("servers/03-mcp-orchestrator/Dockerfile", "w", encoding="utf-8", newline="\n") as f:
    f.write(dockerfile_content)

# 3. requirements.txt (FastAPI + LangChain + LangGraph + HTTPX)
requirements_content = """fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.4
langchain==0.1.14
langgraph==0.0.31
httpx==0.27.0
"""
with open("servers/03-mcp-orchestrator/requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(requirements_content)

# 4. main.py (Grafo de Estado con LangGraph y ruteo interno a Recon y Vector)
main_content = """from typing import TypedDict, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException
import uvicorn
import httpx

from core_shared.security import verify_mcp_token
from core_shared.mcp_protocol import MCPBaseRequest, MCPBaseResponse
from core_shared.logging_config import setup_secure_logger

from langgraph.graph import StateGraph, END

logger = setup_secure_logger("mcp-orchestrator")
app = FastAPI(title="MCP Multi-Agent Orchestrator (LangGraph)", version="1.0.0")

# Definición del Estado del Grafo Multi-Agente
class AgentState(TypedDict):
    task: str
    target: str
    recon_data: Dict[str, Any]
    vector_data: Dict[str, Any]
    final_report: str

# URLs internas dentro de la red Docker segura
RECON_URL = "http://mcp-server-recon:8000/api/v1/mcp/recon/execute"
VECTOR_URL = "http://mcp-server-vector:8000/api/v1/mcp/vector/execute"
SECRET_TOKEN = "vertex-super-secret-key-2026"

async def call_node(url: str, method: str, params: dict):
    headers = {"Content-Type": "application/json", "X-MCP-Access-Token": SECRET_TOKEN}
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": "orchestrator-call"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# Nodo 1: Ejecutar Reconocimiento de Red
async def node_recon(state: AgentState) -> AgentState:
    logger.info(f"[LangGraph] Ejecutando Nodo Recon sobre objetivo: {state['target']}")
    res = await call_node(RECON_URL, "nmap_fast_scan", {"target": state["target"]})
    state["recon_data"] = res.get("result", {"error": "Fallo en nodo recon"})
    return state

# Nodo 2: Consultar Memoria Vectorial (RAG)
async def node_vector(state: AgentState) -> AgentState:
    logger.info(f"[LangGraph] Consultando base de conocimientos para: {state['task']}")
    res = await call_node(VECTOR_URL, "search_context", {"query": state["task"], "n_results": 1})
    state["vector_data"] = res.get("result", {"error": "Fallo en nodo vector"})
    return state

# Nodo 3: Sintetizar Reporte Final
async def node_synthesize(state: AgentState) -> AgentState:
    logger.info("[LangGraph] Sintetizando reporte multi-agente...")
    recon_out = state.get("recon_data", {}).get("output", "Sin datos de red")
    vector_matches = state.get("vector_data", {}).get("matches", [["Sin contexto previo"]])
    
    report = (
        f"--- REPORTE TÁCTICO VIC ---\\n"
        f"Misión: {state['task']}\\n"
        f"Inteligencia Vectorial RAG: {vector_matches}\\n"
        f"Resultados de Escaneo Ofensivo:\\n{recon_out}"
    )
    state["final_report"] = report
    return state

# Construcción del StateGraph
workflow = StateGraph(AgentState)
workflow.add_node("recon_node", node_recon)
workflow.add_node("vector_node", node_vector)
workflow.add_node("synthesize_node", node_synthesize)

# Flujo concurrente/secuencial del grafo
workflow.set_entry_point("recon_node")
workflow.add_edge("recon_node", "vector_node")
workflow.add_edge("vector_node", "synthesize_node")
workflow.add_edge("synthesize_node", END)

app_graph = workflow.compile()

@app.post("/api/v1/mcp/orchestrate/execute", response_model=MCPBaseResponse)
async def orchestrate_task(request: MCPBaseRequest, token: str = Depends(verify_mcp_token)):
    task_desc = request.params.get("task", "Auditoría estándar")
    target_host = request.params.get("target", "127.0.0.1")
    
    initial_state = {
        "task": task_desc,
        "target": target_host,
        "recon_data": {},
        "vector_data": {},
        "final_report": ""
    }
    
    try:
        # Ejecución del Grafo LangGraph
        final_state = await app_graph.ainvoke(initial_state)
        return MCPBaseResponse(
            id=request.id,
            result={"status": "Grafo ejecutado con éxito", "report": final_state["final_report"]}
        )
    except Exception as e:
        logger.error(f"Error crítico en orquestación: {str(e)}")
        return MCPBaseResponse(id=request.id, error={"code": 500, "message": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
with open("servers/03-mcp-orchestrator/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(main_content)

print("[+] Esqueleto del servidor 'mcp-orchestrator' con LangGraph generado exitosamente.")