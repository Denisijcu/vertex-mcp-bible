import urllib.request
import urllib.error
import json

URL = "http://localhost:8004/api/v1/mcp/infra/execute"
HEADERS = {
    "Content-Type": "application/json",
    "X-MCP-Access-Token": "vertex-super-secret-key-2026"
}

def send_payload(method_name):
    payload = {
        "jsonrpc": "2.0",
        "method": method_name,
        "params": {},
        "id": f"test-{method_name}"
    }
    req = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), headers=HEADERS, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"[-] ERROR HTTP {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[-] ERROR DE CONEXIÓN: {str(e)}")

print("\n[+] 1. Ejecutando Telemetría del Sistema Host (psutil)...")
send_payload("system_health")

print("\n[+] 2. Ejecutando Auditoría de Seguridad de Contenedores (Docker Socket)...")
send_payload("audit_containers")