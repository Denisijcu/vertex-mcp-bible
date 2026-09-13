import os

# 1. Actualizar dependencias del orquestador
reqs = """fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.4
langchain==0.1.14
langgraph==0.0.31
httpx==0.27.0
langchain-openai==0.1.3
"""
with open("servers/03-mcp-orchestrator/requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(reqs)

# 2. Inyectar el modelo de lenguaje en el StateGraph
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
app = FastAPI(title="MCP Multi-Agent Orchestrator (LangGraph & LLM)", version="2.0.0")

class AgentState(TypedDict):
    task: str
    target: str
    recon_data: Dict[str, Any]
    vector_data: Dict[str, Any]
    final_report: str

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

# NODO CEREBRAL: Sintesis de IA con Gemma en LM Studio
async def node_synthesize(state: AgentState) -> AgentState:
    logger.info("[LangGraph] Activando motor LLM para sintesis tactica...")
    recon_out = state.get("recon_data", {}).get("output", "Sin datos de red")
    vector_matches = state.get("vector_data", {}).get("matches", [["Sin contexto previo"]])
    
    # Conexion a LM Studio en el host de Windows (host.docker.internal)
    llm = ChatOpenAI(
        base_url="http://host.docker.internal:1234/v1",
        api_key="lm-studio-local",
        temperature=0.3, # Baja temperatura para que sea analitico y preciso
        model="gemma" # LM Studio ignorara esto y usara el modelo cargado
    )
    
    prompt = f\"\"\"Analiza los siguientes datos recolectados y genera un Reporte Tactico de Inteligencia.
    
MISION ORIGINAL: {state['task']}
OBJETIVO ESCANEADO: {state['target']}

CONTEXTO ESTRATEGICO (RAG):
{vector_matches}

RESULTADOS DEL ESCANEO OFENSIVO (NMAP):
{recon_out}

Redacta tu respuesta como el analista jefe de Inteligencia Ofensiva de Vertex Coders. 
Estructura en Markdown:
1. Resumen Ejecutivo (fusionando la mision y el contexto RAG).
2. Analisis de Superficie de Ataque (interpretando los puertos Nmap).
3. Recomendaciones Tácticas.
Súper directo, profesional y en español.\"\"\"

    messages = [
        SystemMessage(content="Eres VIC (Vertex Intelligence Core), el sistema automatizado de Red Teaming y ciberseguridad de Vertex Coders. Eres directo, tecnico y profesional."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        state["final_report"] = response.content
    except Exception as e:
        logger.error(f"Falla en comunicacion con LM Studio: {str(e)}")
        state["final_report"] = f"ERROR DE CONEXION LLM: {str(e)}\n\nVerifica que LM Studio este ejecutando el servidor en el puerto 1234."
        
    return state

workflow = StateGraph(AgentState)
workflow.add_node("recon_node", node_recon)
workflow.add_node("vector_node", node_vector)
workflow.add_node("synthesize_node", node_synthesize)

workflow.set_entry_point("recon_node")
workflow.add_edge("recon_node", "vector_node")
workflow.add_edge("vector_node", "synthesize_node")
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

print("[+] Orquestador actualizado. LangChain apuntando a LM Studio (host.docker.internal:1234).")