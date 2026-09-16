import json
import os
from typing import Dict, Any

class MCPManagerService:
    def __init__(self):
        self.active_servers: Dict[str, Any] = {}

    def sync_servers(self, config_payload: dict) -> int:
        """Sincroniza y almacena en memoria o archivo la configuración de servidores MCP activos."""
        self.active_servers = config_payload.get("mcpServers", {})
        
        # Opcional: Guardarlo localmente en el backend para que los subprocesos los lean
        config_path = "mcpServers_active.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.active_servers, f, indent=2)
            
        return len(self.active_servers)

    def get_active_servers(self) -> dict:
        return self.active_servers

mcp_service = MCPManagerService()