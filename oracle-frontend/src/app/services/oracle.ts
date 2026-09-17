import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class OracleService {
  private apiUrl = 'http://localhost:8015/api/v1'; // Ajusta según tu puerto de FastAPI

  constructor(private http: HttpClient) {}

  getHealthCheck(): Observable<any> {
    return this.http.get('http://localhost:8015/health');
  }

  // Auditoría de infraestructura (grafo dockerizado, nodos recon/vector/infra)
  executeTask(prompt: string, targetIp: string, method: string = "standard_audit"): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp/orchestrate/execute`, {
      prompt: prompt,
      target_ip: targetIp,
      method: method
    });
  }

  // Modo agente: el usuario escribe en lenguaje natural y el modelo decide qué
  // herramientas MCP usar (function calling). No se eligen funciones ni parámetros.
  agentMission(prompt: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp/agent/execute`, {
      prompt: prompt
    });
  }

  getTaskStatus(taskId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/mcp/tasks/${taskId}`);
  }

  syncMcpServers(configPayload: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp/servers/sync`, configPayload);
  }

  // Devuelve los servidores MCP actualmente sincronizados y activos en el Core
  getActiveMcpServers(): Observable<any> {
    return this.http.get(`${this.apiUrl}/mcp-hub/servers/active`);
  }

  // Lista las herramientas que expone un servidor MCP local (usado en el Gestor MCP)
  listServerTools(serverName: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp-hub/servers/tools`, {
      server_name: serverName
    });
  }

  // Invoca una herramienta concreta de un servidor MCP local (prueba manual en el Gestor MCP)
  callServerTool(serverName: string, toolName: string, args: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp-hub/servers/test-call`, {
      server_name: serverName,
      tool_name: toolName,
      arguments: args
    });
  }

  // 🔍 Envía archivos al escáner políglota de FastAPI
  scanPolyglotFile(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post(`${this.apiUrl}/security/scan-polyglot`, formData);
  }
}
