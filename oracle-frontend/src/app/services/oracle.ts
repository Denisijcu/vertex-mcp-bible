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

  executeTask(prompt: string, targetIp: string, method: string = "standard_audit"): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp/orchestrate/execute`, {
      prompt: prompt,
      target_ip: targetIp,
      method: method
    });
  }

  getTaskStatus(taskId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/mcp/tasks/${taskId}`);
  }

  syncMcpServers(configPayload: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp/servers/sync`, configPayload);
  }

  // Devuelve los servidores MCP actualmente sincronizados/activos en el Core
  getActiveMcpServers(): Observable<any> {
    return this.http.get(`${this.apiUrl}/mcp-hub/servers/active`);
  }

  // Lista las herramientas que expone un servidor MCP local (hace handshake stdio)
  listServerTools(serverName: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp-hub/servers/tools`, {
      server_name: serverName
    });
  }

  // Invoca una herramienta concreta de un servidor MCP local con sus argumentos
  callServerTool(serverName: string, toolName: string, args: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp-hub/servers/test-call`, {
      server_name: serverName,
      tool_name: toolName,
      arguments: args
    });
  }

  // Fase 2: mision local — el backend ejecuta varias tools MCP y Gemma sintetiza
  localMission(task: string, invocations: any[]): Observable<any> {
    return this.http.post(`${this.apiUrl}/mcp/local-mission/execute`, {
      task: task,
      invocations: invocations
    });
  }

  // 🔍 Método para enviar archivos al escáner políglota de FastAPI
  scanPolyglotFile(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post(`${this.apiUrl}/security/scan-polyglot`, formData);
  }
}
