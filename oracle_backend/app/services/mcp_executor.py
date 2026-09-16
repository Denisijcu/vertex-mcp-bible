import asyncio
import os
from typing import Any, Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Timeout global (handshake + operacion). Configurable por si un tool pesado
# (ej. semgrep en vertex-cyber-mcp) tarda mas de la cuenta.
TOOL_TIMEOUT = float(os.getenv("MCP_TOOL_TIMEOUT", "120"))


class MCPProcessExecutor:
    """
    Cliente MCP stdio real, apoyado en el SDK oficial (mcp v1.x).

    A diferencia de la version anterior (un solo write + communicate que esperaba
    la muerte del proceso), este hace el handshake completo del protocolo:
        initialize -> notifications/initialized -> tools/list | tools/call
    y mantiene la sesion viva mientras dura el intercambio. Es lo que exigen los
    servidores MCP spec-compliant como vertex-cyber-mcp o tello.
    """

    @staticmethod
    def _build_params(server_config: dict) -> StdioServerParameters:
        command = server_config.get("command")
        if not command:
            raise ValueError("El server_config no tiene 'command'.")
        args = server_config.get("args", []) or []
        custom_env = server_config.get("env", {}) or {}

        # Heredamos el entorno del sistema (PATH, SYSTEMROOT, etc. -- criticos en
        # Windows para que el .exe/node arranquen) y aplicamos las custom encima,
        # expandiendo variables tipo %PATH% o $PATH si las hubiera.
        merged_env = dict(os.environ)
        for k, v in custom_env.items():
            merged_env[k] = os.path.expandvars(str(v))

        return StdioServerParameters(command=command, args=args, env=merged_env)

    @staticmethod
    async def list_tools(server_name: str, server_config: dict) -> Dict[str, Any]:
        """Abre una sesion MCP y devuelve el catalogo de herramientas del server."""
        try:
            params = MCPProcessExecutor._build_params(server_config)

            async def _op():
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return [
                            {
                                "name": t.name,
                                "description": t.description,
                                "input_schema": t.inputSchema,
                            }
                            for t in result.tools
                        ]

            tools = await asyncio.wait_for(_op(), timeout=TOOL_TIMEOUT)
            return {"status": "success", "server": server_name, "tools": tools}

        except asyncio.TimeoutError:
            return {
                "status": "error",
                "server": server_name,
                "detail": f"Timeout ({TOOL_TIMEOUT}s) durante el handshake/list_tools.",
            }
        except Exception as exc:
            return {"status": "error", "server": server_name, "detail": repr(exc)}

    @staticmethod
    async def call_tool(
        server_name: str,
        server_config: dict,
        tool_name: str,
        arguments: dict,
    ) -> Dict[str, Any]:
        """Abre una sesion MCP, hace el handshake e invoca una herramienta concreta."""
        try:
            params = MCPProcessExecutor._build_params(server_config)

            async def _op():
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await session.call_tool(tool_name, arguments=arguments or {})

            result = await asyncio.wait_for(_op(), timeout=TOOL_TIMEOUT)

            # result.content es una lista de bloques (TextContent, ImageContent...).
            # Extraemos el texto donde lo haya y serializamos el resto.
            parts = []
            for block in result.content:
                text = getattr(block, "text", None)
                parts.append(text if text is not None else str(block))

            return {
                "status": "success",
                "server": server_name,
                "tool": tool_name,
                "is_error": bool(getattr(result, "isError", False)),
                "content": "\n".join(parts),
            }

        except asyncio.TimeoutError:
            return {
                "status": "error",
                "server": server_name,
                "detail": f"Timeout ({TOOL_TIMEOUT}s) ejecutando '{tool_name}'.",
            }
        except Exception as exc:
            return {"status": "error", "server": server_name, "detail": repr(exc)}
