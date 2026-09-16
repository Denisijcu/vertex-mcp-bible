import os
from typing import Any, Dict, List

import httpx

# LM Studio expone un endpoint OpenAI-compatible. Desde el backend suelto en
# Windows se alcanza por localhost (a diferencia del orquestador dockerizado,
# que usaba host.docker.internal). Todo configurable por env var.
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")
LM_MODEL = os.getenv("LM_MODEL", "gemma")

# Gemma 12B en la 1660 Ti es lenta; damos margen amplio. Como corre en background
# task (el usuario recibe su task_id al instante), un timeout largo no molesta.
SYNTHESIS_TIMEOUT = float(os.getenv("SYNTHESIS_TIMEOUT", "600"))

# Misma voz que usa el orquestador dockerizado, para que los reportes salgan
# con el estilo que ya conoces.
SYSTEM_PROMPT = (
    "Eres VIC (Vertex Intelligence Core), un analista de ciberseguridad de elite "
    "para Vertex Coders. Se analitico, directo y profesional."
)


def _build_tools_block(tool_results: List[Dict[str, Any]]) -> str:
    """Formatea los resultados de las herramientas para meterlos en el prompt."""
    if not tool_results:
        return "(No se ejecuto ninguna herramienta local.)"

    lines = []
    for r in tool_results:
        name = f"{r.get('server', '?')}/{r.get('tool', '?')}"
        if r.get("status") == "success":
            lines.append(f"### Herramienta: {name}\n{r.get('content', '(sin salida)')}")
        else:
            detail = r.get("detail", "error desconocido")
            lines.append(f"### Herramienta: {name} [FALLO]\n{detail}")
    return "\n\n".join(lines)


async def synthesize_report(task: str, tool_results: List[Dict[str, Any]]) -> str:
    """
    Llama a Gemma (LM Studio) para redactar un reporte tactico sobre los
    resultados que el backend ya ejecuto. Gemma NO ejecuta herramientas: solo
    analiza lo que se le entrega ya masticado. Asi esquivamos por completo el
    problema de timeout del tool-calling dentro de LM Studio.
    """
    tools_block = _build_tools_block(tool_results)

    prompt = (
        f"MISION: {task}\n\n"
        f"RESULTADOS DE HERRAMIENTAS EJECUTADAS POR EL CORE:\n{tools_block}\n\n"
        "Redacta un Reporte Tactico Completo en Markdown. Incluye:\n"
        "1. Resumen Ejecutivo\n"
        "2. Analisis de los resultados de cada herramienta\n"
        "3. Hallazgos y correlaciones relevantes\n"
        "4. Recomendaciones Estrategicas.\n"
        "Basate UNICAMENTE en los resultados entregados; no inventes datos que no aparezcan."
    )

    payload = {
        "model": LM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=SYNTHESIS_TIMEOUT) as client:
        resp = await client.post(LM_STUDIO_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Respuesta estandar OpenAI-compatible
    choices = data.get("choices", [])
    if choices and "message" in choices[0]:
        return choices[0]["message"].get("content", "").strip() or "(Gemma devolvio una respuesta vacia.)"
    return f"(Respuesta inesperada de LM Studio: {data})"
