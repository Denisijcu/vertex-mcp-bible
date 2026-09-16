import { Injectable, NgZone } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class SpeechService {
  private recognition: any;
  public isListening = false;
  public speechEnabled = true; // Interruptor opcional para activar/desactivar la voz de VIC

  constructor(private ngZone: NgZone) {
    const windowRef: any = window;
    const SpeechRecognition = windowRef.SpeechRecognition || windowRef.webkitSpeechRecognition;
    
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.lang = 'es-ES';
      this.recognition.interimResults = false;
      this.recognition.maxAlternatives = 1;
    }
  }

  // --- MÉTODOS DE RECONOCIMIENTO (MIC) ---
  startListening(callback: (text: string) => void, onError: (error: any) => void) {
    if (!this.recognition) {
      onError('El navegador no soporta Web Speech API.');
      return;
    }

    this.isListening = true;
    this.recognition.onresult = (event: any) => {
      const speechToText = event.results[0][0].transcript;
      this.ngZone.run(() => {
        this.isListening = false;
        callback(speechToText);
      });
    };

    this.recognition.onerror = (event: any) => {
      this.ngZone.run(() => {
        this.isListening = false;
        onError(event.error);
      });
    };

    this.recognition.onend = () => {
      this.ngZone.run(() => {
        this.isListening = false;
      });
    };

    try {
      this.recognition.start();
    } catch (err) {
      this.isListening = false;
      onError(err);
    }
  }

  stopListening() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    }
  }

  // --- MÉTODOS DE SÍNTESIS DE VOZ (SPEAKER) ---
  speak(text: string) {
    if (!this.speechEnabled || !('speechSynthesis' in window)) return;

    // Cancelar cualquier locución previa para que no se encimen los reportes
    window.speechSynthesis.cancel();

    // Limpiamos un poco el texto de caracteres Markdown pesados para que la locución sea natural
    const cleanText = text
      .replace(/[*#-_`]/g, '')
      .replace(/https?:\/\/\S+/g, 'enlace')
      .substring(0, 400); // Leemos un resumen o los primeros caracteres clave para no hacer la locución eterna

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'es-ES';
    utterance.rate = 1.05; // Velocidad táctica ligeramente dinámica
    utterance.pitch = 0.9;  // Tono un poco más firme y sobrio

    window.speechSynthesis.speak(utterance);
  }

  stopSpeaking() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }
}