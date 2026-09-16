import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.scanner_service import heuristic_polyglot_scan

router = APIRouter(prefix="/security", tags=["Security & Forensics"])

TEMP_DIR = "temp_scans"
os.makedirs(TEMP_DIR, exist_ok=True)

@router.post("/scan-polyglot")
async def scan_polyglot_file(file: UploadFile = File(...)):
    """Recibe un archivo o imagen subida desde el frontend y ejecuta el escaneo heurístico políglota."""
    temp_file_path = os.path.join(TEMP_DIR, file.filename)
    
    try:
        # Guardamos temporalmente el archivo recibido para analizar sus bytes
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ejecutamos el análisis heurístico
        scan_report = heuristic_polyglot_scan(temp_file_path)
        return scan_report

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ejecutando análisis forense: {str(e)}")
    finally:
        # Limpieza del archivo temporal
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)