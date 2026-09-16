import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-file-upload',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="file-upload-container">
      <label class="upload-label">📥 Cargar Payload, Script o Imagen Forense (Esteganografía)</label>
      <div class="dropzone" (click)="fileInput.click()">
        <input 
          type="file" 
          #fileInput 
          (change)="onFileSelected($event)" 
          style="display: none;" 
        />
        <span *ngIf="!selectedFile" class="dropzone-text">
          Adjuntar script (.py, .php) o imagen (.png, .jpg) para análisis forense
        </span>
        <span *ngIf="selectedFile" class="file-selected">
          📎 {{ selectedFile.name }} ({{ fileType }})
          <button class="btn-remove" (click)="clearFile($event)">✕</button>
        </span>
      </div>
    </div>
  `,
  styles: [`
    .file-upload-container { margin-bottom: 1rem; }
    .upload-label { display: block; font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.3rem; text-transform: uppercase; }
    .dropzone { background: #020617; border: 1px dashed #475569; padding: 0.75rem; border-radius: 4px; text-align: center; cursor: pointer; transition: border-color 0.2s; }
    .dropzone:hover { border-color: #38bdf8; }
    .dropzone-text { font-size: 0.75rem; color: #64748b; }
    .file-selected { display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: #38bdf8; }
    .btn-remove { background: transparent; border: none; color: #ef4444; cursor: pointer; font-weight: bold; font-size: 0.9rem; }
  `]
})
export class FileUploadComponent {
  selectedFile: File | null = null;
  fileType = '';

  @Output() fileLoaded = new EventEmitter<{ name: string, content: string, isBinary: boolean }>();
  @Output() fileCleared = new EventEmitter<void>();

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      const extension = file.name.split('.').pop()?.toLowerCase() || '';
      const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(extension);

      const reader = new FileReader();
      if (isImage) {
        this.fileType = `Imagen Forense / Polyglot (.${extension})`;
        reader.onload = (e: any) => {
          // Extraemos el DataURL (Base64 de la imagen) para que VIC analice su estructura binaria o posibles polyglots
          const base64Data = e.target.result;
          this.fileLoaded.emit({ name: file.name, content: base64Data, isBinary: true });
        };
        reader.readAsDataURL(file);
      } else {
        this.fileType = `Payload / Script (.${extension})`;
        reader.onload = (e: any) => {
          const rawText = e.target.result;
          this.fileLoaded.emit({ name: file.name, content: rawText, isBinary: false });
        };
        reader.readAsText(file);
      }
    }
  }

  clearFile(event: Event) {
    event.stopPropagation();
    this.selectedFile = null;
    this.fileType = '';
    this.fileCleared.emit();
  }
}