import os

# 1. Crear el directorio del servidor de vectores
os.makedirs("servers/02-mcp-vector", exist_ok=True)

# 2. Dockerfile para mcp-vector (Base limpia)
dockerfile_content = """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app

RUN useradd -m -s /bin/bash vertex_mcp
WORKDIR /app

COPY servers/02-mcp-vector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core_shared/ /app/core_shared/
COPY servers/02-mcp-vector/main.py /app/main.py

RUN chown -R vertex_mcp:vertex_mcp /app
USER vertex_mcp

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
with open("servers/02-mcp-vector/Dockerfile", "w", encoding="utf-8", newline="\n") as f:
    f.write(dockerfile_content)

# 3. requirements.txt (Solo lo básico por ahora, luego añadimos ChromaDB)
requirements_content = """fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.4
"""
with open("servers/02-mcp-vector/requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(requirements_content)

# 4. main.py (Esqueleto de FastAPI heredando la seguridad de Vertex)
main_content = """from fastapi import FastAPI, Depends
import uvicorn
from core_shared.security import verify_mcp_token

app = FastAPI(title="MCP Vector / Data Science Node", version="1.0.0")

@app.get("/health")
def health_check():
    return {"status": "Vector Node Online"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
with open("servers/02-mcp-vector/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(main_content)

print("[+] Esqueleto del servidor 'mcp-vector' generado correctamente.")