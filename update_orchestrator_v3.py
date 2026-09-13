import os

main_code = """from typing import TypedDict, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException
import uvicorn
import httpx

from core_shared.security import verify_mcp_token
from core_shared.mcp_protocol import MCPBaseRequest, MCPBaseResponse
from core_shared.logging_config import setup_secure_logger

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = setup_secure_logger("mcp-orchestrator")
app = FastAPI(title="MCP Multi-Agent Orchestrator (LangGraph & LLM)", version="3.0.0")

# 1. Expandimos el estado para incluir la telemetria de Docker
class AgentState(TypedDict):
    task: str
    target: str
    recon_data: Dict[str, Any]
    vector_data: Dict[str, Any]
    infra_data: Dict[str, Any]
    final_report: str

RECON_URL = "http://mcp-server-recon:8000/api/v1/mcp/recon/execute"
VECTOR_URL = "http://mcp-server-vector:8000/api/v1/mcp/vector/execute"
INFRA_URL = "http://mcp-server-infra:8000/api/v1/mcp/infra/execute"
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

async def node_recon(state: AgentState) -> AgentState:
    logger.info(f"[LangGraph] Ejecutando Nodo Recon sobre objetivo: {state['target']}")
    res = await call_node(RECON_URL, "nmap_fast_scan", {"target": state["target"]})
    state["recon_data"] = res.get("result", {"error": "Fallo en nodo recon"})
    return state

async def node_vector(state: AgentState) -> AgentState:
    logger.info(f"[LangGraph] Consultando base de conocimientos para: {state['task']}")
    res = await call_node(VECTOR_URL, "search_context", {"query": state["task"], "n_results": 1})
    state["vector_data"] = res.get("result", {"error": "Fallo en nodo vector"})
    return state

# 2. NUEVO NODO: Consultamos a mcp-infra
async def node_infra(state: AgentState) -> AgentState:
    logger.info(f"[LangGraph] Ejecutando Auditoria de Infraestructura Docker")
    res = await call_node(INFRA_URL, "audit_containers", {})
    state["infra_data"] = res.get("result", {"error": "Fallo en nodo infra"})
    return state

async def node_synthesize(state: AgentState) -> AgentState:
    logger.info("[LangGraph] Activando motor LLM para sintesis tactica...")
    recon_out = state.get("recon_data", {}).get("output", "Sin datos de red")
    vector_matches = state.get("vector_data", {}).get("matches", [["Sin contexto previo"]])
    infra_containers = state.get("infra_data", {}).get("containers", [])
    
    # Filtramos los contenedores con riesgo para optimizar la memoria del LLM
    risky_containers = [c for c in infra_containers if c.get("security_risk")]
    if not risky_containers and infra_containers:
        infra_summary = "Todos los contenedores cumplen con el estandar de seguridad de Vertex (No root/No privilegiados)."
    else:
        infra_summary = f"ADVERTENCIA - Contenedores con riesgo detectado (Ejecutando como root): {risky_containers}"
    
    llm = ChatOpenAI(
        base_url="http://host.docker.internal:1234/v1",
        api_key="lm-studio-local",
        temperature=0.3,
        model="gemma"
    )
    
    prompt = f"MISION ORIGINAL: {state['task']}\\nOBJETIVO: {state['target']}\\n\\nCONTEXTO ESTRATEGICO:\\n{vector_matches}\\n\\nNMAP (SUPERFICIE DE RED):\\n{recon_out}\\n\\nAUDITORIA DOCKER (INFRAESTRUCTURA):\\n{infra_summary}\\n\\nRedacta un Reporte Tactico Completo en Markdown. Incluye:\\n1. Resumen Ejecutivo\\n2. Analisis de Red (Nmap)\\n3. Auditoria de Contenedores (Señala los riesgos en la infraestructura de Vertex Coders)\\n4. Recomendaciones Estrategicas."

    messages = [
        SystemMessage(content="Eres VIC (Vertex Intelligence Core). Eres un analista de ciberseguridad ofensiva de elite para Vertex Coders. Sé analítico, directo y profesional."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        state["final_report"] = response.content
    except Exception as e:
        logger.error(f"Falla LLM: {str(e)}")
        state["final_report"] = "ERROR LLM: " + str(e)
        
    return state

# 3. CONSTRUCCIÓN DEL NUEVO GRAFO
workflow = StateGraph(AgentState)
workflow.add_node("recon_node", node_recon)
workflow.add_node("vector_node", node_vector)
workflow.add_node("infra_node", node_infra)
workflow.add_node("synthesize_node", node_synthesize)

workflow.set_entry_point("recon_node")
workflow.add_edge("recon_node", "vector_node")
workflow.add_edge("vector_node", "infra_node")
workflow.add_edge("infra_node", "synthesize_node")
workflow.add_edge("synthesize_node", END)

app_graph = workflow.compile()

@app.post("/api/v1/mcp/orchestrate/execute", response_model=MCPBaseResponse)
async def orchestrate_task(request: MCPBaseRequest, token: str = Depends(verify_mcp_token)):
    task_desc = request.params.get("task", "Auditoria estandar")
    target_host = request.params.get("target", "127.0.0.1")
    
    initial_state = {
        "task": task_desc,
        "target": target_host,
        "recon_data": {},
        "vector_data": {},
        "infra_data": {},
        "final_report": ""
    }
    
    try:
        final_state = await app_graph.ainvoke(initial_state)
        return MCPBaseResponse(
            id=request.id,
            result={"status": "Inteligencia Generada", "report": final_state["final_report"]}
        )
    except Exception as e:
        logger.error(f"Error critico en orquestacion: {str(e)}")
        return MCPBaseResponse(id=request.id, error={"code": 500, "message": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
with open("servers/03-mcp-orchestrator/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(main_code)

print("[+] Grafo actualizado: recon -> vector -> infra -> synthesize (LLM).")