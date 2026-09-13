import os

# 1. Crear el directorio con guion bajo
os.makedirs("core_shared", exist_ok=True)

# 2. Archivo __init__.py (vacío, necesario para módulos en Python)
with open("core_shared/__init__.py", "w", encoding="utf-8", newline="\n") as f:
    f.write("")

# 3. Archivo security.py
security_code = """import os
import re
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-MCP-Access-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def verify_mcp_token(api_key: str = Security(api_key_header)):
    expected_token = os.getenv("MCP_SECRET", "vertex-super-secret-key-2026")
    if api_key != expected_token:
        raise HTTPException(status_code=403, detail="Acceso denegado al perímetro MCP.")
    return api_key

def sanitize_shell_input(value: str) -> str:
    forbidden_patterns = [r";", r"\\|", r"&", r"`", r"\\$", r"\\n", r"\\r", r">", r"<"]
    for pattern in forbidden_patterns:
        if re.search(pattern, value):
            raise ValueError(f"Violacion de seguridad detectada: {pattern}")
    return value
"""
with open("core_shared/security.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(security_code)

# 4. Archivo mcp_protocol.py
mcp_code = """from pydantic import BaseModel, Field, model_validator
from typing import Any, Dict, Optional
from .security import sanitize_shell_input

class MCPBaseRequest(BaseModel):
    jsonrpc: str = Field(default="2.0", pattern="^2.0$")
    method: str =
    params: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = None

    @model_validator(mode='after')
    def enforce_sanitization(self) -> 'MCPBaseRequest':
        for key, value in self.params.items():
            if isinstance(value, str):
                self.params[key] = sanitize_shell_input(value)
        return self

class MCPBaseResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
"""
with open("core_shared/mcp_protocol.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(mcp_code)

# 5. Archivo logging_config.py
log_code = """import logging
import sys

def setup_secure_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
"""
with open("core_shared/logging_config.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(log_code)

print("[+] Modulo core_shared generado exitosamente con formato estricto.")