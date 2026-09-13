from fastapi import FastAPI, Depends, HTTPException
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
