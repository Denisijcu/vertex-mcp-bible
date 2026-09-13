import urllib.request
import urllib.error
import json

URL = "http://localhost:8003/api/v1/mcp/orchestrate/execute"
HEADERS = {
    "Content-Type": "application/json",
    "X-MCP-Access-Token": "vertex-super-secret-key-2026"
}

payload = {
    "jsonrpc": "2.0",
    "method": "run_audit",
    "params": {
        "task": "¿Quién es el CEO de Vertex Coders y qué proyecto está desarrollando?",
        "target": "127.0.0.1"
    },
    "id": "test-langgraph"
}

req = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), headers=HEADERS, method='POST')

print("\n[+] Desplegando Asalto Multi-Agente (LangGraph Orchestrator)...")
print("[!] El cerebro está coordinando a Recon y Vector internamente. Espera unos segundos...\n")

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        # Usamos ensure_ascii=False para que los acentos se vean perfectos en tu consola
        print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"[-] ERROR HTTP {e.code}: {e.read().decode('utf-8')}")
except urllib.error.URLError as e:
    print(f"[-] ERROR DE CONEXIÓN: {e.reason}")