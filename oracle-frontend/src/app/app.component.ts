import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OracleService } from './services/oracle';
import { SpeechService } from './services/speech.service';
import { FileUploadComponent } from './components/file-upload/file-upload.component';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { McpServerManagerComponent } from './components/mcp-server-manager/mcp-server-manager.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, FileUploadComponent, McpServerManagerComponent],
  template: `
    <div class="dashboard-container">
      <header class="tactical-header">
        <div class="logo-area">
          <h1>VERTEX CODERS // <span>VIC & ORACLE-AI DEFENSE CORE</span></h1>
          <p class="subtitle">Plataforma Autónoma de Ciberseguridad Ofensiva y Hardening</p>
        </div>
        <div class="header-actions">
          <!-- Botones de Navegación de Vistas -->
          <button 
            class="btn-nav-toggle" 
            [class.active]="currentView === 'mission'"
            (click)="currentView = 'mission'">
            🛡️ Consola Táctica
          </button>
          <button 
            class="btn-nav-toggle" 
            [class.active]="currentView === 'mcp'"
            (click)="currentView = 'mcp'">
            ⚙️ Gestor MCP
          </button>

          <!-- Interruptor Global de Voz -->
          <button 
            class="btn-audio-toggle" 
            (click)="speechService.speechEnabled = !speechService.speechEnabled"
            [class.active]="speechService.speechEnabled"
            title="Activar/Desactivar síntesis de voz">
            {{ speechService.speechEnabled ? '🔊 VOZ ACTIVA' : '🔇 VOZ SILENCIADA' }}
          </button>
          <div class="status-badge" [class.online]="isOnline">
            <span class="pulse-dot"></span>
            {{ isOnline ? 'CORE ONLINE' : 'CONECTANDO...' }}
          </div>
        </div>
      </header>

      <!-- VISTA 1: CONSOLA DE MISIONES TÁCTICAS -->
      <main class="grid-layout" *ngIf="currentView === 'mission'">
        <section class="control-panel">
          <h2>Consola de Misiones Tácticas</h2>
          
          <div class="form-group">
            <label>Objetivo / Host / Contenedor</label>
            <input [(ngModel)]="targetIp" placeholder="127.0.0.1" />
          </div>

          <div class="form-group">
            <div class="label-with-mic">
              <label>Descripción de la Misión / Prompt</label>
              <button 
                type="button" 
                class="btn-mic" 
                [class.listening]="speechService.isListening"
                (click)="toggleVoiceCommand()"
                title="Dictar comando por voz">
                {{ speechService.isListening ? '🔴 ESCUCHANDO...' : '🎤 COMANDO DE VOZ' }}
              </button>
            </div>
            <textarea [(ngModel)]="taskDescription" rows="3" placeholder="Ej: Auditoría general de infraestructura..."></textarea>
          </div>

          <!-- Módulo de Subida de Archivos -->
          <app-file-upload 
            (fileLoaded)="onFileLoaded($event)" 
            (fileCleared)="onFileCleared()">
          </app-file-upload>

          <button class="btn-primary" (click)="runMission()" [disabled]="loading">
            {{ loading ? 'EJECUTANDO ANÁLISIS PROFUNDO...' : 'LANZAR MISIÓN TÁCTICA' }}
          </button>

          <!-- Atajos Rápidos -->
          <div class="shortcuts-section">
            <h3>Atajos Rápidos de Auditoría</h3>
            <div class="chips-container">
              <button class="chip" (click)="setShortcut('Auditoría general de infraestructura y Docker')">🐳 Auditoría Docker</button>
              <button class="chip" (click)="setShortcut('Análisis de seguridad del puerto 8000')">🌐 Puerto 8000</button>
              <button class="chip" (click)="setShortcut('Revisión de escalada de privilegios y contenedores en root')">👑 Revisión de Root</button>
            </div>
          </div>

          <!-- Guía de Ayuda Colapsable -->
          <div class="help-section">
            <h3 (click)="toggleHelp()" class="help-toggle">
              📖 Guía de Consultas Soportadas {{ showHelp ? '▲' : '▼' }}
            </h3>
            <div class="help-content" *ngIf="showHelp">
              <ul>
                <li><strong>Auditorías de Red:</strong> Escaneos de puertos y vectores.</li>
                <li><strong>Hardening:</strong> Validación de privilegios de usuario.</li>
                <li><strong>Análisis de Voz:</strong> Dicta comandos directamente al micro.</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- Consola de Salida o Reproductor de Animaciones Manim -->
        <section class="output-console">
          <div class="console-header">
            <h3>Reporte de Inteligencia / Salida de VIC</h3>
            <div class="console-actions" *ngIf="missionOutput && !loading">
              <!-- Botón Speaker por demanda con resumen inteligente -->
              <button class="btn-secondary btn-speak-output" (click)="speakOutput()" title="Reproducir reporte en voz alta">
                🔊 Escuchar Reporte
              </button>
              <button class="btn-secondary" (click)="copyOutput()">Copiar Reporte</button>
            </div>
          </div>
          <div class="console-body">
            <!-- Reproductor de video dinámico con un único archivo maestro 'video.mp4' y texto de marketing -->
            <div *ngIf="loading" class="execution-status-container">
              <video autoplay loop muted playsinline class="manim-video">
                <source src="assets/animations/video.mp4" type="video/mp4">
                Tu navegador no soporta reproducción de video táctico.
              </video>
              
              <div class="terminal-status-box">
                <p class="status-text status-text-warning">{{ currentStatusText }}</p>
              </div>
            </div>

            <!-- Consola de texto tradicional cuando finaliza (Corregido desbordamiento de texto) -->
            <pre *ngIf="!loading" class="terminal-report-output">{{ missionOutput || 'Esperando órdenes de misión o archivos adjuntos para iniciar análisis táctico...' }}</pre>
          </div>
        </section>
      </main>

      <!-- VISTA 2: GESTOR DE SERVIDORES MCP -->
      <main *ngIf="currentView === 'mcp'">
        <app-mcp-server-manager></app-mcp-server-manager>
      </main>
    </div>
  `,
  styles: [`
    .dashboard-container { background-color: #07090e; color: #00ff66; font-family: 'Courier New', Courier, monospace; padding: 1.5rem 2rem; min-height: 100vh; }
    .tactical-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1e293b; padding-bottom: 1rem; margin-bottom: 1.5rem; }
    .header-actions { display: flex; align-items: center; gap: 1rem; }
    .logo-area h1 { margin: 0; font-size: 1.4rem; color: #f8fafc; }
    .logo-area h1 span { color: #38bdf8; }
    .subtitle { margin: 0.2rem 0 0 0; font-size: 0.8rem; color: #64748b; }
    .btn-audio-toggle { background: #1e293b; border: 1px solid #334155; color: #94a3b8; font-size: 0.75rem; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-family: inherit; font-weight: bold; transition: all 0.2s; }
    .btn-audio-toggle.active { background: rgba(56, 189, 248, 0.2); border-color: #38bdf8; color: #38bdf8; }
    .status-badge { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.8rem; background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #ef4444; font-size: 0.8rem; font-weight: bold; border-radius: 4px; }
    .status-badge.online { background: rgba(16, 185, 129, 0.2); border-color: #10b981; color: #10b981; }
    .pulse-dot { width: 8px; height: 8px; background-color: currentColor; border-radius: 50%; box-shadow: 0 0 8px currentColor; }
    .grid-layout { display: grid; grid-template-columns: 380px 1fr; gap: 1.5rem; }
    .control-panel, .output-console { background: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 1.25rem; }
    .control-panel h2 { font-size: 1rem; color: #38bdf8; margin-top: 0; border-bottom: 1px dashed #1e293b; padding-bottom: 0.5rem; }
    .form-group { margin-bottom: 1rem; }
    .label-with-mic { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem; }
    .form-group label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; margin: 0; }
    .btn-mic { background: #1e293b; border: 1px solid #334155; color: #38bdf8; font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer; font-family: inherit; font-weight: bold; transition: all 0.2s; }
    .btn-mic:hover { background: #334155; }
    .btn-mic.listening { background: rgba(239, 68, 68, 0.2); border-color: #ef4444; color: #ef4444; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    input, textarea { width: 100%; background: #020617; border: 1px solid #334155; color: #e2e8f0; padding: 0.6rem; border-radius: 4px; font-family: inherit; font-size: 0.85rem; box-sizing: border-box; }
    input:focus, textarea:focus { outline: none; border-color: #38bdf8; }
    .btn-primary { width: 100%; background: #0284c7; color: white; border: none; padding: 0.75rem; font-weight: bold; border-radius: 4px; cursor: pointer; font-family: inherit; transition: background 0.2s; margin-top: 0.5rem; }
    .btn-primary:hover { background: #0ea5e9; }
    .btn-primary:disabled { background: #475569; cursor: not-allowed; }
    .shortcuts-section { margin-top: 1.5rem; border-top: 1px solid #1e293b; padding-top: 1rem; }
    .shortcuts-section h3, .help-section h3 { font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; }
    .chips-container { display: flex; flex-wrap: wrap; gap: 0.4rem; }
    .chip { background: #1e293b; border: 1px solid #334155; color: #cbd5e1; padding: 0.3rem 0.6rem; font-size: 0.7rem; border-radius: 12px; cursor: pointer; font-family: inherit; transition: all 0.2s; }
    .chip:hover { background: #38bdf8; color: #0f172a; border-color: #38bdf8; }
    .help-section { margin-top: 1rem; border-top: 1px solid #1e293b; padding-top: 0.75rem; }
    .help-toggle { cursor: pointer; user-select: none; }
    .help-toggle:hover { color: #38bdf8; }
    .help-content ul { margin: 0.5rem 0 0 1rem; padding: 0; font-size: 0.75rem; color: #94a3b8; }
    .help-content li { margin-bottom: 0.3rem; }
    .output-console { display: flex; flex-direction: column; }
    .console-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem; margin-bottom: 1rem; }
    .console-header h3 { margin: 0; font-size: 0.9rem; color: #38bdf8; }
    .console-actions { display: flex; gap: 0.5rem; }
    .btn-secondary { background: #1e293b; color: #e2e8f0; border: 1px solid #475569; padding: 0.25rem 0.6rem; font-size: 0.75rem; border-radius: 4px; cursor: pointer; font-family: inherit; }
    .btn-secondary:hover { background: #334155; }
    .btn-speak-output { border-color: #38bdf8; color: #38bdf8; background: rgba(56, 189, 248, 0.1); }
    .btn-speak-output:hover { background: rgba(56, 189, 248, 0.2); }
    .console-body { flex: 1; background: #020617; border: 1px solid #1e293b; border-radius: 4px; padding: 1rem; overflow-y: auto; max-height: 700px; display: flex; flex-direction: column; justify-content: flex-start; align-items: stretch; }
    .btn-nav-toggle { background: #1e293b; border: 1px solid #334155; color: #94a3b8; font-size: 0.75rem; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-family: inherit; font-weight: bold; transition: all 0.2s; }
    .btn-nav-toggle.active { background: rgba(56, 189, 248, 0.2); border-color: #38bdf8; color: #38bdf8; }
    /* Corrección crítica para evitar que el reporte se corte a la derecha */
    .terminal-report-output { 
      white-space: pre-wrap; 
      word-break: break-word; 
      overflow-x: auto; 
      color: #00ff66; 
      margin: 0; 
      font-size: 0.85rem; 
      line-height: 1.4; 
      width: 100%; 
      text-align: left; 
    }
    
    /* Contenedor dinámico de ejecución con animación táctica */
    .execution-status-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
      padding: 1rem;
      animation: fadeIn 0.4s ease-in-out;
    }

    .manim-video {
      width: 100%;
      max-height: 340px;
      border-radius: 6px;
      border: 1px solid #1e293b;
      object-fit: contain;
      background: #000;
      box-shadow: 0 0 20px rgba(0, 242, 255, 0.15);
    }

    /* Caja de estado con borde y efecto de parpadeo táctico */
    .terminal-status-box {
      margin-top: 1rem;
      background: rgba(2, 6, 23, 0.85);
      border: 1px solid #facc15;
      border-radius: 6px;
      padding: 0.75rem 1.25rem;
      width: 100%;
      max-width: 700px;
      text-align: center;
      box-shadow: 0 0 12px rgba(250, 204, 21, 0.25);
    }

    .status-text {
      font-size: 0.8rem;
      font-family: 'Courier New', Courier, monospace;
      margin: 0;
      font-weight: bold;
      line-height: 1.4;
      letter-spacing: 0.5px;
    }

    .status-text-warning {
      color: #facc15;
      text-shadow: 0 0 8px rgba(250, 204, 21, 0.6);
      animation: terminalPulseWarning 1.8s infinite ease-in-out;
    }

    @keyframes terminalPulseWarning {
      0% { opacity: 0.75; text-shadow: 0 0 4px rgba(250, 204, 21, 0.4); }
      50% { opacity: 1; text-shadow: 0 0 12px rgba(250, 204, 21, 0.9); }
      100% { opacity: 0.75; text-shadow: 0 0 4px rgba(250, 204, 21, 0.4); }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `]
})
export class AppComponent implements OnInit, OnDestroy {
  isOnline = false;
  taskDescription = 'Auditoría general de infraestructura';
  targetIp = '127.0.0.1';
  missionOutput = '';
  loading = false;
  showHelp = false;
  fileContentPayload = '';
  currentStatusText = 'ESTADO (RUNNING)... Gemma procesando razonamiento profundo. VIC analizando vectores de ataque. Este proceso puede tomar varios minutos; el reporte aparecerá inmediatamente al finalizar.';
  currentView = 'mission';
  private pollSub?: Subscription;


  constructor(
    private oracleService: OracleService,
    public speechService: SpeechService
  ) { }

  ngOnInit() {
    this.checkHealth();

    setTimeout(() => {
      this.speechService.speak("Sistema VIC activado y listo para operaciones.");
    }, 1000);
  }

  ngOnDestroy() { if (this.pollSub) this.pollSub.unsubscribe(); }

  checkHealth() {
    this.oracleService.getHealthCheck().subscribe({
      next: (res) => this.isOnline = res.status === 'online',
      error: () => this.isOnline = false
    });
  }

  setShortcut(prompt: string) {
    this.taskDescription = prompt;
  }

  toggleHelp() { this.showHelp = !this.showHelp; }

  toggleVoiceCommand() {
    if (this.speechService.isListening) {
      this.speechService.stopListening();
    } else {
      this.speechService.startListening(
        (transcript) => {
          this.taskDescription = transcript;
          if (this.taskDescription.trim()) {
            this.runMission();
          }
        },
        (error) => {
          console.error('Error de reconocimiento de voz:', error);
          alert('No se pudo activar el micrófono o el navegador no soporta Web Speech API.');
        }
      );
    }
  }

  onFileLoaded(fileData: { name: string, content: string, isBinary: boolean, rawFile?: File }) {
    if (fileData.isBinary && fileData.rawFile) {
      this.currentStatusText = `[*] Ejecutando análisis heurístico políglota en ${fileData.name}...`;

      // Llamamos al backend FastAPI para analizar los Magic Bytes y apéndices ocultos
      this.oracleService.scanPolyglotFile(fileData.rawFile).subscribe({
        next: (res: any) => {
          let reportText = `### REPORTE FORENSE DE POLYGLOT / MAGIC BYTES\n`;
          reportText += `- **Fichero:** ${res.file}\n`;
          reportText += `- **Tamaño:** ${res.size_bytes} bytes\n`;
          reportText += `- **Amenaza Detectada:** ${res.threat_detected ? '🚨 SÍ (CRÍTICO)' : '✅ NINGUNA'}\n\n`;

          if (res.details && res.details.length > 0) {
            reportText += `**Hallazgos Detallados:**\n`;
            res.details.forEach((detail: string) => {
              reportText += `* ${detail}\n`;
            });
          } else {
            reportText += `* Estructura de bytes limpia. No se encontraron apéndices sospechosos tras el marcador IEND.\n`;
          }

          this.missionOutput = reportText;
          this.loading = false;
        },
        error: (err) => {
          this.missionOutput = `[!] Error ejecutando el escaneo forense en el backend: ${err.message || 'Fallo de red'}`;
          this.loading = false;
        }
      });
    } else {
      // Archivo de texto plano o script tradicional
      const base64Content = btoa(unescape(encodeURIComponent(fileData.content)));
      this.fileContentPayload = ` [PAYLOAD BASE64: ${fileData.name}] ${base64Content}`;
      this.taskDescription = `Decodifica el payload adjunto del archivo ${fileData.name}, audítalo y genera el reporte de hardening.`;
    }
  }

  onFileCleared() {
    this.fileContentPayload = '';
  }

  copyOutput() {
    navigator.clipboard.writeText(this.missionOutput);
    alert('Reporte copiado al portapapeles.');
  }

  speakOutput() {
    if (this.missionOutput) {
      this.speechService.speak(this.missionOutput);
    }
  }

  runMission() {
    this.loading = true;
    this.currentStatusText = `ESTADO (RUNNING)... Gemma procesando razonamiento profundo. VIC analizando vectores de ataque. Este proceso puede tomar varios minutos; el reporte aparecerá inmediatamente al finalizar.`;

    this.speechService.speak("ESTADO (RUNNING). Gemma procesando razonamiento profundo. Espere el despliegue del reporte.");

    console.log("🔥 Disparando misión desde Angular...");

    const rawPrompt = this.taskDescription + this.fileContentPayload;
    const finalPrompt = rawPrompt.replace(/[\r\n]+/g, ' ');

    this.oracleService.executeTask(finalPrompt, this.targetIp).subscribe({
      next: (res: any) => {
        const taskId = res.task_id;
        if (!taskId) {
          this.missionOutput = '[!] Error crítico: No se obtuvo el ID de la tarea.';
          this.loading = false;
          return;
        }

        this.currentStatusText = `ESTADO (RUNNING) [ID: ${taskId}]... Gemma procesando razonamiento profundo. Análisis en curso; el reporte se desplegará al concluir.`;

        this.pollSub = interval(4000).pipe(
          switchMap(() => this.oracleService.getTaskStatus(taskId)),
          takeWhile((statusRes: any) => statusRes.status === 'QUEUED' || statusRes.status === 'RUNNING', true)
        ).subscribe({
          next: (statusRes: any) => {
            if (statusRes.status === 'COMPLETED') {
              let finalReport = statusRes.report;
              if (typeof finalReport === 'string' && finalReport.includes("'report':")) {
                const match = finalReport.match(/'report':\s*'(.*)'/s);
                if (match && match[1]) {
                  finalReport = match[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
                }
              }
              this.missionOutput = finalReport || '[!] Reporte vacío.';
              this.loading = false;

              if (this.pollSub) this.pollSub.unsubscribe();
            } else if (statusRes.status === 'FAILED') {
              this.missionOutput = `[!] Fallo en la misión: ${statusRes.report}`;
              this.loading = false;
              if (this.pollSub) this.pollSub.unsubscribe();
            } else {
              this.currentStatusText = `ESTADO (${statusRes.status})... Gemma procesando razonamiento profundo. Misión en ejecución activa.`;
            }
          },
          error: (err) => {
            this.missionOutput = `[!] Error de sondeo: ${err.statusText || 'Conexión interrumpida'}`;
            this.loading = false;
          }
        });
      },
      error: (err) => {
        this.missionOutput = `[!] Error de conexión con OracleAI: ${err.statusText || 'Fallo de red'}`;
        this.loading = false;
      }
    });
  }
}