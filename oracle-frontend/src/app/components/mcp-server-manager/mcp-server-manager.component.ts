import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OracleService } from '../../services/oracle'; // Ajusta la ruta relativa según dónde esté tu service

interface McpServerConfig {
  command: string;
  args: string[];
  env?: { [key: string]: string };
}

interface McpRegistry {
  mcpServers: { [key: string]: McpServerConfig };
}

interface ToolProp {
  key: string;
  type: string;
  required: boolean;
}

@Component({
  selector: 'app-mcp-server-manager',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="mcp-manager-container">
      <div class="mcp-header">
        <h3>🛡️ VIC // MCP Server Registry & Intelligence Hub</h3>
        <p class="subtitle">Gestión centralizada de servidores Model Context Protocol (Estándar Claude / LM Studio)</p>
      </div>

      <div class="mcp-grid">
        <!-- Panel Izquierdo: Editor JSON -->
        <div class="editor-panel">
          <div class="panel-toolbar">
            <span class="panel-title">mcpServers.json</span>
            <button class="btn-tactical" (click)="loadDefaultJson()">Restaurar Default</button>
          </div>
          <textarea 
            [(ngModel)]="rawJsonConfig" 
            rows="22" 
            placeholder="Pega aquí tu configuración JSON de servidores MCP..."
            (input)="parseConfig()">
          </textarea>
          <div class="editor-actions">
            <button class="btn-primary" (click)="saveConfiguration()">💾 Sincronizar con Core</button>
            <span class="status-msg" [class.error]="hasJsonError">{{ parseStatusMessage }}</span>
          </div>
        </div>

        <!-- Panel Derecho: Estado y Switches de Servidores -->
        <div class="servers-list-panel">
          <div class="panel-toolbar">
            <span class="panel-title">Servidores Detectados ({{ serverKeys.length }})</span>
            <span class="active-badge">Activos: {{ activeCount }} / {{ serverKeys.length }}</span>
          </div>

          <div class="servers-scrollbox">
            <div *ngFor="let name of serverKeys" class="server-card" [class.disabled]="!serverStates[name]">
              <div class="server-card-header">
                <span class="server-name">{{ name }}</span>
                <label class="switch">
                  <input type="checkbox" [(ngModel)]="serverStates[name]" (change)="updateActiveCount()">
                  <span class="slider round"></span>
                </label>
              </div>
              <div class="server-card-body">
                <p><strong>Comando:</strong> <code>{{ parsedServers[name].command }}</code></p>
                <p><strong>Args:</strong> <span class="args-text">{{ parsedServers[name].args.join(' ') }}</span></p>
                <div *ngIf="parsedServers[name].env" class="env-block">
                  <small>Variables de entorno configuradas</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel Inferior: Invocación Directa de Herramientas -->
      <div class="invoke-panel">
        <div class="panel-toolbar">
          <span class="panel-title">⚡ Invocación Directa de Herramientas</span>
          <span class="invoke-hint-inline">Ejecuta un tool de un server local (stdio) vía el Core</span>
        </div>

        <div class="invoke-selectors">
          <div class="invoke-field">
            <label>Servidor activo</label>
            <select [(ngModel)]="invokeServer" (change)="loadTools()">
              <option value="">-- Selecciona un server --</option>
              <option *ngFor="let name of activeServerKeys" [value]="name">{{ name }}</option>
            </select>
          </div>

          <div class="invoke-field" *ngIf="invokeTools.length > 0">
            <label>Herramienta ({{ invokeTools.length }})</label>
            <select [(ngModel)]="invokeToolName" (change)="onToolChange()">
              <option value="">-- Selecciona una tool --</option>
              <option *ngFor="let t of invokeTools" [value]="t.name">{{ t.name }}</option>
            </select>
          </div>
        </div>

        <div *ngIf="isLoadingTools" class="invoke-hint">⏳ Abriendo sesión MCP y cargando herramientas...</div>

        <div *ngIf="selectedToolDescription" class="tool-desc">
          <small>{{ selectedToolDescription }}</small>
        </div>

        <!-- Formulario dinámico generado desde el input_schema de la tool -->
        <div *ngIf="selectedToolProps.length > 0" class="args-form">
          <div *ngFor="let prop of selectedToolProps" class="arg-field">
            <label>
              {{ prop.key }}
              <span class="type-tag">{{ prop.type }}</span>
              <span *ngIf="prop.required" class="req">*</span>
            </label>
            <input *ngIf="prop.type !== 'boolean'"
                   [(ngModel)]="invokeArgs[prop.key]"
                   [placeholder]="placeholderFor(prop.type)">
            <label *ngIf="prop.type === 'boolean'" class="checkbox-inline">
              <input type="checkbox" [(ngModel)]="invokeArgs[prop.key]"> activar
            </label>
          </div>
        </div>

        <button *ngIf="invokeToolName" class="btn-primary invoke-btn" (click)="invokeTool()" [disabled]="isInvoking">
          {{ isInvoking ? '⚙️ Invocando...' : '⚡ Invocar Herramienta' }}
        </button>

        <div *ngIf="invokeResult && invokeResult.status === 'success'" class="invoke-result success">
          <span class="result-label">✅ Resultado</span>
          <pre>{{ invokeResult.content }}</pre>
        </div>
        <div *ngIf="invokeError" class="invoke-result error">
          <span class="result-label">🛑 Error</span>
          <pre>{{ invokeError }}</pre>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .mcp-manager-container { background: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 1.5rem; color: #e2e8f0; font-family: 'Courier New', Courier, monospace; margin-top: 1.5rem; }
    .mcp-header { border-bottom: 1px solid #1e293b; padding-bottom: 0.75rem; margin-bottom: 1.25rem; }
    .mcp-header h3 { margin: 0; color: #38bdf8; font-size: 1.1rem; }
    .subtitle { margin: 0.2rem 0 0 0; font-size: 0.75rem; color: #64748b; }
    
    .mcp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
    @media (max-width: 1024px) { .mcp-grid { grid-template-columns: 1fr; } }

    .editor-panel, .servers-list-panel { background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 1rem; display: flex; flex-direction: column; }
    .panel-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem; }
    .panel-title { font-size: 0.85rem; color: #38bdf8; font-weight: bold; text-transform: uppercase; }
    
    textarea { width: 100%; background: #07090e; border: 1px solid #334155; color: #00ff66; padding: 0.75rem; border-radius: 4px; font-family: inherit; font-size: 0.8rem; box-sizing: border-box; resize: vertical; line-height: 1.4; }
    textarea:focus { outline: none; border-color: #38bdf8; }

    .editor-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem; }
    .btn-tactical { background: #1e293b; border: 1px solid #475569; color: #cbd5e1; font-size: 0.7rem; padding: 0.3rem 0.6rem; border-radius: 4px; cursor: pointer; font-family: inherit; }
    .btn-tactical:hover { background: #334155; }
    .btn-primary { background: #0284c7; color: white; border: none; padding: 0.5rem 1rem; font-weight: bold; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 0.75rem; }
    .btn-primary:hover { background: #0ea5e9; }
    .btn-primary:disabled { background: #334155; cursor: not-allowed; }

    .status-msg { font-size: 0.75rem; color: #10b981; font-weight: bold; }
    .status-msg.error { color: #ef4444; }

    .servers-scrollbox { flex: 1; max-height: 480px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem; padding-right: 0.25rem; }
    .server-card { background: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; padding: 0.75rem; transition: all 0.2s; }
    .server-card.disabled { opacity: 0.4; border-color: #1e293b; }
    .server-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; border-bottom: 1px dashed #1e293b; padding-bottom: 0.3rem; }
    .server-name { color: #f8fafc; font-weight: bold; font-size: 0.85rem; }
    
    .server-card-body p { margin: 0.2rem 0; font-size: 0.75rem; color: #94a3b8; word-break: break-all; }
    .server-card-body code { color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 0.1rem 0.3rem; border-radius: 3px; }
    .args-text { color: #cbd5e1; }
    .env-block { margin-top: 0.4rem; background: rgba(250, 204, 21, 0.1); border-left: 2px solid #facc15; padding: 0.2rem 0.4rem; }
    .env-block small { color: #facc15; font-size: 0.65rem; }
    
    .active-badge { font-size: 0.75rem; background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #10b981; padding: 0.1rem 0.5rem; border-radius: 4px; font-weight: bold; }

    .switch { position: relative; display: inline-block; width: 34px; height: 18px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #334155; transition: .2s; border-radius: 18px; }
    .slider:before { position: absolute; content: ""; height: 12px; width: 12px; left: 3px; bottom: 3px; background-color: white; transition: .2s; border-radius: 50%; }
    input:checked + .slider { background-color: #0284c7; }
    input:checked + .slider:before { transform: translateX(16px); }

    /* --- Panel de invocación --- */
    .invoke-panel { background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 1rem; margin-top: 1.5rem; }
    .invoke-hint-inline { font-size: 0.65rem; color: #64748b; }
    .invoke-selectors { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 0.75rem; }
    @media (max-width: 1024px) { .invoke-selectors { grid-template-columns: 1fr; } }
    .invoke-field { display: flex; flex-direction: column; gap: 0.3rem; }
    .invoke-field label { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; }
    .invoke-field select, .arg-field input { background: #07090e; border: 1px solid #334155; color: #e2e8f0; padding: 0.5rem; border-radius: 4px; font-family: inherit; font-size: 0.8rem; }
    .invoke-field select:focus, .arg-field input:focus { outline: none; border-color: #38bdf8; }
    .invoke-hint { font-size: 0.75rem; color: #facc15; margin: 0.5rem 0; }
    .tool-desc { background: rgba(56, 189, 248, 0.08); border-left: 2px solid #38bdf8; padding: 0.4rem 0.6rem; margin: 0.5rem 0; }
    .tool-desc small { color: #cbd5e1; font-size: 0.72rem; }

    .args-form { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.75rem; margin: 0.75rem 0; }
    .arg-field { display: flex; flex-direction: column; gap: 0.25rem; }
    .arg-field label { font-size: 0.72rem; color: #e2e8f0; display: flex; align-items: center; gap: 0.3rem; }
    .type-tag { font-size: 0.6rem; color: #38bdf8; background: rgba(56, 189, 248, 0.12); padding: 0.05rem 0.3rem; border-radius: 3px; }
    .req { color: #ef4444; font-weight: bold; }
    .checkbox-inline { font-size: 0.72rem; color: #cbd5e1; display: flex; align-items: center; gap: 0.4rem; }

    .invoke-btn { margin-top: 0.5rem; }
    .invoke-result { margin-top: 1rem; border-radius: 4px; padding: 0.75rem; }
    .invoke-result.success { background: rgba(16, 185, 129, 0.08); border: 1px solid #10b981; }
    .invoke-result.error { background: rgba(239, 68, 68, 0.08); border: 1px solid #ef4444; }
    .result-label { font-size: 0.72rem; font-weight: bold; display: block; margin-bottom: 0.4rem; }
    .invoke-result.success .result-label { color: #10b981; }
    .invoke-result.error .result-label { color: #ef4444; }
    .invoke-result pre { margin: 0; color: #e2e8f0; font-size: 0.8rem; white-space: pre-wrap; word-break: break-word; }
  `]
})
export class McpServerManagerComponent implements OnInit {
  rawJsonConfig = '';
  serverKeys: string[] = [];
  parsedServers: { [key: string]: McpServerConfig } = {};
  serverStates: { [key: string]: boolean } = {};
  activeCount = 0;
  parseStatusMessage = 'JSON Válido y Sincronizado';
  hasJsonError = false;

  // --- Estado de la invocación directa ---
  invokeServer = '';
  invokeTools: any[] = [];
  invokeToolName = '';
  invokeArgs: { [key: string]: any } = {};
  invokeResult: any = null;
  invokeError = '';
  isLoadingTools = false;
  isInvoking = false;

  constructor(private oracleService: OracleService) {}

  ngOnInit() {
    this.loadDefaultJson();
  }

  loadDefaultJson() {
    const sampleConfig: McpRegistry = {
      mcpServers: {
        "mi-calculadora": {
          "command": "node",
          "args": ["H:/mcp-calculator/server.js"]
        },
        "vertex-cyber-mcp": {
          "command": "G:\\Astra\\vertex-cyber-mcp\\.venv\\Scripts\\python.exe",
          "args": ["-m", "vertex_cyber_mcp.server"],
          "env": {
            "VCMCP_ALLOWED_ROOTS": "G:\\Astra\\security-lab",
            "VCMCP_ENABLE_SEMGREP": "true"
          }
        },
        "tello": {
          "command": "H:\\mcp-drone\\venv\\Scripts\\python.exe",
          "args": ["H:\\mcp-drone\\tello_server.py"],
          "env": { "TELLO_MOCK": "1" }
        }
      }
    };
    this.rawJsonConfig = JSON.stringify(sampleConfig, null, 2);
    this.parseConfig();
  }

  parseConfig() {
    try {
      const parsed: McpRegistry = JSON.parse(this.rawJsonConfig);
      if (parsed && parsed.mcpServers) {
        this.parsedServers = parsed.mcpServers;
        this.serverKeys = Object.keys(this.parsedServers);
        
        for (const key of this.serverKeys) {
          if (this.serverStates[key] === undefined) {
            this.serverStates[key] = true;
          }
        }
        this.updateActiveCount();
        this.hasJsonError = false;
        this.parseStatusMessage = 'JSON Válido y Sincronizado';
      } else {
        throw new Error("Falta la raíz 'mcpServers'");
      }
    } catch (err: any) {
      this.hasJsonError = true;
      this.parseStatusMessage = 'Error en sintaxis JSON';
    }
  }

  updateActiveCount() {
    this.activeCount = this.serverKeys.filter(k => this.serverStates[k]).length;
  }

  get activeServerKeys(): string[] {
    return this.serverKeys.filter(k => this.serverStates[k]);
  }

  saveConfiguration() {
    if (this.hasJsonError) {
      alert('Corrige los errores en el JSON antes de sincronizar.');
      return;
    }

    try {
      const parsed: McpRegistry = JSON.parse(this.rawJsonConfig);
      const activeServers: { [key: string]: McpServerConfig } = {};

      // Filtrar solo los servidores que tienen el switch encendido
      for (const key of this.serverKeys) {
        if (this.serverStates[key] && parsed.mcpServers[key]) {
          activeServers[key] = parsed.mcpServers[key];
        }
      }

      const payloadToSync = {
        mcpServers: activeServers
      };

      console.log('Sincronizando servidores MCP activos con FastAPI:', payloadToSync);

      // Conectamos el servicio HTTP de Angular para enviarlo al backend en el puerto 8015
      this.oracleService.syncMcpServers(payloadToSync).subscribe({
        next: (res) => {
          console.log('Respuesta del Core:', res);
          alert(`¡Servidores MCP sincronizados con éxito! ${Object.keys(activeServers).length} servidores habilitados para el motor de inferencia.`);
        },
        error: (err) => {
          console.error('Error al sincronizar con el backend:', err);
          alert('Error al sincronizar con el backend: ' + (err.error?.detail || err.message));
        }
      });

    } catch (err: any) {
      alert('Error al procesar la configuración para el Core.');
    }
  }

  // --- Invocación directa ---

  loadTools() {
    this.invokeTools = [];
    this.invokeToolName = '';
    this.invokeArgs = {};
    this.invokeResult = null;
    this.invokeError = '';
    if (!this.invokeServer) { return; }

    this.isLoadingTools = true;
    this.oracleService.listServerTools(this.invokeServer).subscribe({
      next: (res) => {
        this.isLoadingTools = false;
        if (res.status === 'success') {
          this.invokeTools = res.tools || [];
        } else {
          this.invokeError = res.detail || 'No se pudieron cargar las herramientas.';
        }
      },
      error: (err) => {
        this.isLoadingTools = false;
        this.invokeError = err.error?.detail || err.message;
      }
    });
  }

  onToolChange() {
    this.invokeArgs = {};
    this.invokeResult = null;
    this.invokeError = '';
  }

  get selectedTool(): any {
    return this.invokeTools.find(t => t.name === this.invokeToolName) || null;
  }

  get selectedToolDescription(): string {
    return this.selectedTool?.description || '';
  }

  get selectedToolProps(): ToolProp[] {
    const schema = this.selectedTool?.input_schema;
    if (!schema || !schema.properties) { return []; }
    const required: string[] = schema.required || [];
    return Object.keys(schema.properties).map(key => ({
      key,
      type: schema.properties[key].type || 'string',
      required: required.includes(key)
    }));
  }

  placeholderFor(type: string): string {
    if (type === 'array') { return 'CSV o JSON: 1,2,3'; }
    if (type === 'integer' || type === 'number') { return 'número'; }
    return type;
  }

  invokeTool() {
    if (!this.invokeServer || !this.invokeToolName) { return; }
    this.isInvoking = true;
    this.invokeResult = null;
    this.invokeError = '';

    // Coaccionamos cada argumento al tipo declarado en el schema
    const args: { [key: string]: any } = {};
    for (const prop of this.selectedToolProps) {
      const raw = this.invokeArgs[prop.key];
      if (raw === undefined || raw === '') { continue; }

      if (prop.type === 'number' || prop.type === 'integer') {
        args[prop.key] = Number(raw);
      } else if (prop.type === 'boolean') {
        args[prop.key] = !!raw;
      } else if (prop.type === 'array') {
        try {
          args[prop.key] = JSON.parse(raw);
        } catch {
          args[prop.key] = String(raw).split(',').map((s: string) => {
            const n = Number(s.trim());
            return isNaN(n) ? s.trim() : n;
          });
        }
      } else {
        args[prop.key] = raw;
      }
    }

    this.oracleService.callServerTool(this.invokeServer, this.invokeToolName, args).subscribe({
      next: (res) => {
        this.isInvoking = false;
        this.invokeResult = res;
        if (res.status !== 'success') {
          this.invokeError = res.detail || 'Error en la invocación.';
        }
      },
      error: (err) => {
        this.isInvoking = false;
        this.invokeError = err.error?.detail || err.message;
      }
    });
  }
}
