import urllib.request
import urllib.error
import json
import time

URL = "http://localhost:8002/api/v1/mcp/vector/execute"
HEADERS = {
    "Content-Type": "application/json",
    "X-MCP-Access-Token": "vertex-super-secret-key-2026"
}

def send_payload(payload):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), headers=HEADERS, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"[-] ERROR HTTP {e.code}: {e.read().decode('utf-8')}")
        return None

print("\n[+] 1. Inyectando contexto en la base de datos vectorial (ChromaDB)...")
ingest_payload = {
    "jsonrpc": "2.0",
    "method": "add_document",
    "params": {
        "doc_id": "ctx-vertex-001",
        "text": "Vertex Coders LLC es una compañía tecnológica operando desde Miami, dirigida por Denis Sanchez Leyva. Su foco actual es el desarrollo de VIC (Vertex Intelligence Core) y la plataforma OracleAI para automatización de Red Teaming y seguridad IA."
    },
    "id": "test-ingest"
}
res_ingest = send_payload(ingest_payload)
print(json.dumps(res_ingest, indent=2))

time.sleep(1) # Damos un segundo para la indexacion

print("\n[+] 2. Ejecutando busqueda semantica (RAG)...")
search_payload = {
    "jsonrpc": "2.0",
    "method": "search_context",
    "params": {
        "query": "¿Qué plataformas está desarrollando la empresa en Miami y quién es el CEO?",
        "n_results": 1
    },
    "id": "test-search"
}
res_search = send_payload(search_payload)
print(json.dumps(res_search, indent=2))