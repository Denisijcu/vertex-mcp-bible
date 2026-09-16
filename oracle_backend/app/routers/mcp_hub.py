from fastapi import APIRouter, HTTPException, Body
from app.services.mcp_manager import mcp_service
from app.services.mcp_executor import MCPProcessExecutor

router = APIRouter(prefix="/mcp-hub", tags=["MCP Intelligence Hub"])


@router.get("/servers/active")
async def get_active_mcp_servers():
    """Devuelve la lista de servidores MCP actualmente sincronizados y activos."""
    return {
        "active_servers": mcp_service.get_active_servers()
    }


def _resolve_server(server_name: str) -> dict:
    active_servers = mcp_service.get_active_servers()
    if not server_name or server_name not in active_servers:
        raise HTTPException(
            status_code=404,
            detail=f"El servidor MCP '{server_name}' no esta activo o no fue sincronizado.",
        )
    return active_servers[server_name]


@router.post("/servers/tools")
async def list_server_tools(payload: dict = Body(...)):
    """Abre una sesion MCP con el server y devuelve su catalogo de herramientas."""
    server_name = payload.get("server_name")
    server_config = _resolve_server(server_name)
    return await MCPProcessExecutor.list_tools(server_name, server_config)


@router.post("/servers/test-call")
async def test_mcp_server_call(payload: dict = Body(...)):
    """
    Invoca una herramienta de un servidor MCP local via stdio.

    Body esperado:
      { "server_name": "vertex-cyber-mcp",
        "tool_name": "scan_file",
        "arguments": { ... } }

    Si se omite 'tool_name', devuelve el catalogo de herramientas del server
    (equivalente a /servers/tools), util para descubrir que se puede invocar.
    """
    server_name = payload.get("server_name")
    server_config = _resolve_server(server_name)

    tool_name = payload.get("tool_name")
    arguments = payload.get("arguments", {}) or {}

    if not tool_name:
        return await MCPProcessExecutor.list_tools(server_name, server_config)

    return await MCPProcessExecutor.call_tool(server_name, server_config, tool_name, arguments)
