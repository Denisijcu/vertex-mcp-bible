from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import orchestration, security, mcp_hub

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0"
)

# EL CORS VA PRIMERO QUE TODO
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LUEGO LAS RUTAS BASE
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "system": "OracleAI Intelligence Core",
        "environment": "modular-async-architecture"
    }

# Y LUEGO LOS ROUTERS MODULARES
app.include_router(orchestration.router, prefix=settings.API_V1_STR)
app.include_router(security.router, prefix=settings.API_V1_STR)
app.include_router(mcp_hub.router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8015, reload=True)