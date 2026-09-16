import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OracleAI Core"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/oracle_ai_db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "vertex-oracle-secret-key-2026")
    
    class Config:
        case_sensitive = True

settings = Settings()
