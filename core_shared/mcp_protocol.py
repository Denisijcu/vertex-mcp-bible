from pydantic import BaseModel, Field, model_validator
from typing import Any, Dict, Optional
from .security import sanitize_shell_input

class MCPBaseRequest(BaseModel):
    jsonrpc: str = Field(default="2.0", pattern="^2.0$")
    method: str = Field(..., description="Accion a ejecutar")
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
