import json
import os
from typing import Any, Dict, List, Tuple

import httpx

from app.services.mcp_executor import MCPProcessExecutor

# LM Studio, endpoint OpenAI-compatible (mismo que usa el resto del backend soberano).
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")
LM_MODEL = os.getenv("LM_MODEL", "gemma")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))
MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "6"))

SEP = "__"  # separador server__tool en el nombre de funcion (unicidad entre servers)

SYSTEM_PROMPT = (
    "Eres VIC (Vertex Intelligence Core), un analista de ciberseguridad de elite "
    "para Vertex Coders. Tienes acceso a herramientas MCP; usalas cuando la tarea "
    "lo requiera, extrayendo los argumentos del mensaje del usuario. Cuando tengas "
    "los resultados, redacta una respuesta clara, analitica y profesional en espanol. "
    "No inventes datos: basate unicamente en lo que devuelvan las herramientas."
)


async def _build_tools(active_servers: dict) -> Tuple[List[dict], Dict[str, tuple]]:
    """
    Abre sesion MCP con cada server activo, lista sus tools y las convierte al
    formato 'tools' de la API OpenAI que LM Studio consume. Devuelve la lista y un
    mapa func_name -> (server_name, tool_name, config) para el despacho inverso.
    """
    openai_tools: List[dict] = []
    tool_map: Dict[str, tuple] = {}

    for server_name, config in active_servers.items():
        listing = await MCPProcessExecutor.list_tools(server_name, config)
        if listing.get("status") != "success":
            continue
        for t in listing.get("tools", []):
            func_name = f"{server_name}{SEP}{t['name']}"
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                },
            })
            tool_map[func_name] = (server_name, t["name"], config)

    return openai_tools, tool_map


async def _call_llm(messages: List[dict], tools: List[dict]) -> dict:
    payload: Dict[str, Any] = {
        "model": LM_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        resp = await client.post(LM_STUDIO_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


async def run_agent(prompt: str, active_servers: dict) -> Dict[str, Any]:
    """
    Loop de function calling controlado por el backend:
      1. Se le pasan al modelo el prompt del usuario y TODAS las tools de los servers activos.
      2. El modelo decide que tool llamar y con que argumentos (los extrae del texto).
      3. El backend ejecuta la tool via cliente MCP y le devuelve el resultado al modelo.
      4. Se repite hasta que el modelo entrega su respuesta final (sin mas tool_calls).

    El usuario solo escribe en lenguaje natural; no elige funciones ni pasa parametros.
    """
    tools, tool_map = await _build_tools(active_servers)

    messages: List[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    trace: List[str] = []

    for _ in range(MAX_ITERATIONS):
        data = await _call_llm(messages, tools)
        msg = data["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            return {
                "status": "success",
                "report": (msg.get("content") or "").strip() or "(el modelo devolvio una respuesta vacia)",
                "trace": trace,
            }

        # El mensaje del asistente con sus tool_calls debe preceder a los resultados
        messages.append({
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            fn = tc.get("function", {})
            fname = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}

            if fname not in tool_map:
                tool_content = f"[error] Herramienta desconocida: {fname}"
            else:
                server_name, tool_name, config = tool_map[fname]
                res = await MCPProcessExecutor.call_tool(server_name, config, tool_name, args)
                if res.get("status") == "success":
                    tool_content = res.get("content", "")
                else:
                    tool_content = f"[error] {res.get('detail', 'fallo desconocido')}"
                trace.append(f"{server_name}/{tool_name}({args}) -> {tool_content}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", fname),
                "content": str(tool_content),
            })

    return {
        "status": "success",
        "report": "[!] El agente alcanzo el maximo de iteraciones sin cerrar la respuesta.\n\nTraza de herramientas:\n" + "\n".join(trace),
        "trace": trace,
    }
