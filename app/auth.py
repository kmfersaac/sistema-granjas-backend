from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import get_db
from app.models import LoginRequest, Token, Usuario
from app.utils.security import (
    verify_password, 
    create_access_token, 
    get_password_hash,
    verify_token
)

router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM usuarios WHERE email = %s AND activo = TRUE", (login_data.email,))
            usuario = cur.fetchone()
            
            if not usuario or not verify_password(login_data.password, usuario['password_hash']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas"
                )
            
            access_token = create_access_token(data={"sub": usuario['email'], "id": usuario['id_usuario']})
            return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM usuarios WHERE id_usuario = %s AND activo = TRUE", (payload['id'],))
            usuario = cur.fetchone()
            
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario no encontrado"
                )
            
            return usuario