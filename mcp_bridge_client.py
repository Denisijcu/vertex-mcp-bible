import sys
import json
import urllib.request

ORCHESTRATOR_URL = "http://localhost:8003/api/v1/mcp/orchestrate/execute"
TOKEN = "vertex-super-secret-key-2026"

def send_to_vic(task_desc, target_ip):
    payload = {
        "jsonrpc": "2.0",
        "method": "orchestrate_task",
        "params": {"task": task_desc, "target": target_ip},
        "id": "lm-studio-bridge"
    }
    headers = {
        "Content-Type": "application/json",
        "X-MCP-Access-Token": TOKEN
    }
    req = urllib.request.Request(ORCHESTRATOR_URL, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res.get("result", {}).get("report", "Sin respuesta del core")
    except Exception as e:
        return f"Error conectando con VIC en Docker: {str(e)}"

def main():
    # Bucle principal para escuchar peticiones de LM Studio por Stdio
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        
        try:
            data = json.loads(line)
            msg_id = data.get("id", 1)
            method = data.get("method", "")

            # Manejo del handshake inicial o listado de herramientas que pide LM Studio
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "vic-orchestrator-bridge", "version": "3.0.0"}
                    },
                    "id": msg_id
                }
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": [
                            {
                                "name": "orchestrate_task",
                                "description": "Ejecuta misiones tácticas de ciberseguridad y auditoría en VIC",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "task": {"type": "string", "description": "Descripción de la tarea táctica"},
                                        "target": {"type": "string", "description": "IP o host objetivo"}
                                    },
                                    "required": ["task"]
                                }
                            }
                        ]
                    },
                    "id": msg_id
                }
            elif method == "tools/call" or method == "orchestrate_task":
                params = data.get("params", {})
                arguments = params.get("arguments", params)
                task = arguments.get("task", "Auditoria general de infraestructura")
                target = arguments.get("target", "127.0.0.1")
                
                report = send_to_vic(task, target)
                
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [{"type": "text", "text": report}]
                    },
                    "id": msg_id
                }
            else:
                # Respuesta por defecto para notificaciones o pings
                response = {
                    "jsonrpc": "2.0",
                    "result": {},
                    "id": msg_id
                }
            
            print(json.dumps(response))
            sys.stdout.flush()
            
        except Exception as e:
            err_res = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": data.get("id", 1) if 'data' in locals() else 1
            }
            print(json.dumps(err_res))
            sys.stdout.flush()

if __name__ == "__main__":
    main()