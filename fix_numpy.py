reqs = """fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.4
chromadb==0.4.24
numpy==1.26.4
"""
with open("servers/02-mcp-vector/requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(reqs)

print("[+] Dependencias actualizadas: NumPy fijado en v1.26.4 para compatibilidad con ChromaDB.")