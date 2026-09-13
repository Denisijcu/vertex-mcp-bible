import os
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
    forbidden_patterns = [r";", r"\|", r"&", r"`", r"\$", r"\n", r"\r", r">", r"<"]
    for pattern in forbidden_patterns:
        if re.search(pattern, value):
            raise ValueError(f"Violacion de seguridad detectada: {pattern}")
    return value
