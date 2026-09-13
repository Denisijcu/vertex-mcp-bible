import urllib.request
import urllib.error
import json

# Apuntamos directo a FastAPI (Bypass del Gateway)
url = "http://localhost:8001/api/v1/mcp/recon/execute"

# Cabeceras con tu token maestro
headers = {
    "Content-Type": "application/json",
    "X-MCP-Access-Token": "vertex-super-secret-key-2026"
}

# Payload exacto del MCP Protocol
payload = {
    "jsonrpc": "2.0",
    "method": "nmap_fast_scan",
    "params": {"target": "127.0.0.1"},
    "id": "test-direct"
}

# Construimos la petición blindada
req = urllib.request.Request(
    url, 
    data=json.dumps(payload).encode('utf-8'), 
    headers=headers, 
    method='POST'
)

print(f"[!] Disparando asalto directo a: {url} ...")

try:
    with urllib.request.urlopen(req) as response:
        result = response.read().decode('utf-8')
        print("\n[+] VICTORIA. Respuesta del Nodo MCP:\n")
        # Imprimimos el JSON formateado bonito
        print(json.dumps(json.loads(result), indent=2))
        
except urllib.error.HTTPError as e:
    error_body = e.read().decode('utf-8')
    print(f"\n[-] EL SERVIDOR RECHAZO EL ATAQUE (HTTP {e.code}):")
    print(error_body)
except urllib.error.URLError as e:
    print(f"\n[-] FALLO DE CONEXION (El puerto 8001 esta cerrado): {e.reason}")