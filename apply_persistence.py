import os

# 1. Crear el directorio físico en Windows donde residirá la memoria de la IA
os.makedirs("data/chroma", exist_ok=True)

# 2. Inyectar PersistentClient en el nodo Vector
vector_code = """from fastapi import FastAPI, Depends, HTTPException
import uvicorn
import chromadb
from core_shared.security import verify_mcp_token
from core_shared.mcp_protocol import MCPBaseRequest, MCPBaseResponse
from core_shared.logging_config import setup_secure_logger

logger = setup_secure_logger("mcp-vector")
app = FastAPI(title="MCP Vector & Data Science Node", version="1.1.0")

# Inicializar ChromaDB con PERSISTENCIA EN DISCO
chroma_client = chromadb.PersistentClient(path="/app/chroma_data")
collection = chroma_client.get_or_create_collection(name="vertex_knowledge_base")

@app.post("/api/v1/mcp/vector/execute", response_model=MCPBaseResponse)
async def execute_vector_ops(
    request: MCPBaseRequest, 
    token: str = Depends(verify_mcp_token)
):
    logger.info(f"Operacion Vectorial Solicitada: '{request.method}'")
    
    try:
        if request.method == "add_document":
            doc_id = request.params.get("doc_id")
            text = request.params.get("text")
            
            if not doc_id or not text:
                raise ValueError("Faltan parametros obligatorios: 'doc_id' y 'text'")
            
            collection.add(documents=[text], ids=[doc_id])
            return MCPBaseResponse(
                id=request.id, 
                result={"status": "Contexto vectorizado y guardado en disco exitosamente", "doc_id": doc_id}
            )
            
        elif request.method == "search_context":
            query = request.params.get("query")
            n_results = int(request.params.get("n_results", 1))
            
            if not query:
                raise ValueError("Falta el parametro obligatorio: 'query'")
            
            results = collection.query(query_texts=[query], n_results=n_results)
            return MCPBaseResponse(
                id=request.id, 
                result={"query": query, "matches": results["documents"]}
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Metodo no reconocido: {request.method}")

    except Exception as e:
        logger.error(f"Falla en el motor vectorial: {str(e)}")
        return MCPBaseResponse(id=request.id, error={"code": 500, "message": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
with open("servers/02-mcp-vector/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(vector_code)

# 3. Actualizar Docker Compose con el Volumen de Persistencia y silenciar telemetría
compose_code = """version: '3.8'

services:
  api-gateway:
    image: traefik:v3.0
    container_name: mcp-api-gateway
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
    ports:
      - "8000:80"
      - "8080:8080"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
    networks:
      - mcp_secure_net

  mcp-recon:
    build:
      context: ../
      dockerfile: servers/01-mcp-recon/Dockerfile
    container_name: mcp-server-recon
    ports:
      - "8001:8000"
    environment:
      - MCP_SECRET=vertex-super-secret-key-2026
    networks:
      - mcp_secure_net
    restart: unless-stopped

  mcp-vector:
    build:
      context: ../
      dockerfile: servers/02-mcp-vector/Dockerfile
    container_name: mcp-server-vector
    ports:
      - "8002:8000"
    environment:
      - MCP_SECRET=vertex-super-secret-key-2026
      - ANONYMIZED_TELEMETRY=False
    volumes:
      - ../data/chroma:/app/chroma_data   # VOLUMEN DE PERSISTENCIA
    networks:
      - mcp_secure_net
    restart: unless-stopped

  mcp-orchestrator:
    build:
      context: ../
      dockerfile: servers/03-mcp-orchestrator/Dockerfile
    container_name: mcp-server-orchestrator
    ports:
      - "8003:8000"
    environment:
      - MCP_SECRET=vertex-super-secret-key-2026
    networks:
      - mcp_secure_net
    restart: unless-stopped

networks:
  mcp_secure_net:
    driver: bridge
"""
with open("infra/docker-compose.yml", "w", encoding="utf-8", newline="\n") as f:
    f.write(compose_code)

print("[+] Archivos regenerados. Memoria persistente configurada en el directorio '/data/chroma'.")