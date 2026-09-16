import os

# Definimos la estructura de directorios para el backend de OracleAI
dirs = [
    "oracle_backend/app/api/v1/endpoints",
    "oracle_backend/app/core",
    "oracle_backend/app/models",
    "oracle_backend/app/schemas",
    "oracle_backend/app/services",
    "oracle_backend/infra"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

# 1. requirements.txt
reqs = """fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.4
sqlalchemy==2.0.28
psycopg2-binary==2.9.9
chromadb==0.4.24
langchain==0.1.12
langgraph==0.0.26
httpx==0.27.0
"""
with open("oracle_backend/requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(reqs)

# 2. Configuración Core (oracle_backend/app/core/config.py)
config_code = """import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OracleAI Core"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/oracle_ai_db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "vertex-oracle-secret-key-2026")
    
    class Config:
        case_sensitive = True

settings = Settings()
"""
with open("oracle_backend/app/core/config.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(config_code)

# 3. Aplicación Principal FastAPI (oracle_backend/app/main.py)
main_code = """from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "system": "OracleAI Intelligence Core",
        "environment": "production-ready"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
"""
with open("oracle_backend/app/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(main_code)

# 4. Dockerfile para OracleAI Core (oracle_backend/Dockerfile)
dockerfile_code = """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app

RUN useradd -m -s /bin/bash vertex_oracle_user
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R vertex_oracle_user:vertex_oracle_user /app

USER vertex_oracle_user

EXPOSE 8010

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
"""
with open("oracle_backend/Dockerfile", "w", encoding="utf-8", newline="\n") as f:
    f.write(dockerfile_code)

print("[+] Estructura base de OracleAI generada con éxito en 'oracle_backend/'.")