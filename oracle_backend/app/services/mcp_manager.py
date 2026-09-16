import json
import os
from typing import Dict, Any

# Se guarda en el CWD del backend (donde corres uvicorn: oracle_backend/).
CONFIG_PATH = "mcpServers_active.json"


class MCPManagerService:
    def __init__(self):
        self.active_servers: Dict[str, Any] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """
        Recupera los servidores sincronizados de una sesion anterior. Antes
        active_servers vivia solo en memoria y se vaciaba en cada reinicio del
        backend, obligando a re-sincronizar a mano. Ahora sobrevive.
        """
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.active_servers = data
        except Exception:
            # Si el archivo esta corrupto o ilegible, arrancamos vacio sin romper.
            self.active_servers = {}

    def sync_servers(self, config_payload: dict) -> int:
        """Sincroniza y persiste en disco la configuracion de servidores MCP activos."""
        self.active_servers = config_payload.get("mcpServers", {})

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.active_servers, f, indent=2)

        return len(self.active_servers)

    def get_active_servers(self) -> dict:
        return self.active_servers


mcp_service = MCPManagerService()
