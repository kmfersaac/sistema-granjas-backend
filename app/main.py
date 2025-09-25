from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.database import init_db, get_db
from app.routes import granjas, usuarios
from app.auth import get_current_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar base de datos al iniciar
    init_db()
    yield

app = FastAPI(
    title="Sistema de Gestión de Granjas",
    description="API para reemplazar el Excel como fuente única de verdad",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción cambiar a tu dominio de Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(usuarios.router, prefix="/api/usuarios", tags=["Usuarios"])
app.include_router(granjas.router, prefix="/api/granjas", tags=["Granjas"])

@app.get("/")
async def root():
    return {"message": "Sistema de Gestión de Granjas API", "status": "activo"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "sistema-granjas-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)