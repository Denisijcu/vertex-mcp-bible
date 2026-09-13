import urllib.request
import json

URL = "http://localhost:8005/api/v1/mcp/harden/execute"
HEADERS = {
    "Content-Type": "application/json",
    "X-MCP-Access-Token": "vertex-super-secret-key-2026"
}

payload = {
    "jsonrpc": "2.0",
    "method": "generate_hardening_patch",
    "params": {"image": "postgres:16-alpine"},
    "id": "test-harden-01"
}

req = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), headers=HEADERS, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"[-] Error: {str(e)}")