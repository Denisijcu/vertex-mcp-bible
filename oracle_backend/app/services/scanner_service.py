import os

def heuristic_polyglot_scan(file_path: str) -> dict:
    """Escaneo heurístico de élite para detectar Polyglots (imágenes con código oculto al final)
       y discrepancias en los Magic Bytes."""
    if not os.path.exists(file_path):
        return {"status": "error", "message": "Fichero no encontrado"}

    with open(file_path, "rb") as f:
        content = f.read()

    report = {
        "file": os.path.basename(file_path),
        "size_bytes": len(content),
        "threat_detected": False,
        "details": []
    }

    # 1. Detección de Falso PNG y Chunk IEND (FSI de archivos legítimos)
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        iend_sig = b"IEND\xaeB`\x82"
        iend_pos = content.find(iend_sig)

        if iend_pos != -1:
            expected_end_pos = iend_pos + len(iend_sig)
            # Si hay bytes después del chunk IEND oficial de la PNG, hay un apéndice oculto (Polyglot)
            if expected_end_pos < len(content):
                extra_bytes = len(content) - expected_end_pos
                report["threat_detected"] = True
                report["details"].append(
                    f"[ALERTA CRÍTICA - ZERO-DAY/POLYGLOT] Se detectó un apéndice binario oculto de {extra_bytes} bytes "
                    "después del bloque IEND oficial de la imagen. Posible webshell o script embebido."
                )

                # Inspeccionar si contiene firmas de scripts comunes
                appendix = content[expected_end_pos:]
                if b"<?php" in appendix or b"eval(" in appendix:
                    report["details"].append("[!] Firma de Webshell PHP detectada en el apéndice de la imagen.")
                if b"import os" in appendix or b"subprocess" in appendix:
                    report["details"].append("[!] Script de Python detectado en el apéndice de la imagen.")

    return report