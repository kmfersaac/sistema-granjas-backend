from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from app.models import TipoUsuario

# Configuración de seguridad
SECRET_KEY = os.getenv("SECRET_KEY", "clave-secreta-temporal-cambiar-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas para uso práctico

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Funciones de verificación de permisos
def puede_editar_granja(usuario_actual, granja):
    """Verifica si el usuario puede editar esta granja específica"""
    if usuario_actual['tipo_usuario'] == TipoUsuario.ADMIN:
        return True
    
    # Usuario captura solo puede editar granjas de sus asociaciones
    if usuario_actual['tipo_usuario'] == TipoUsuario.CAPTURA:
        return granja.get('asociacion') in usuario_actual.get('asociaciones_permitidas', [])
    
    return False

def puede_eliminar_granja(usuario_actual, granja):
    """Verifica si el usuario puede eliminar esta granja"""
    return puede_editar_granja(usuario_actual, granja)

def puede_ver_campos_admin(usuario_actual):
    """Verifica si el usuario puede ver campos de administrador"""
    return usuario_actual['tipo_usuario'] == TipoUsuario.ADMIN

def puede_modificar_campos_admin(usuario_actual):
    """Verifica si el usuario puede modificar campos de administrador"""
    return usuario_actual['tipo_usuario'] == TipoUsuario.ADMIN

def filtrar_campos_admin(granja, usuario_actual):
    """Elimina SOLO los 3 campos admin si el usuario no es administrador"""
    if not puede_ver_campos_admin(usuario_actual):
        campos_ocultos = [
            'estatus_anterior', 
            'estatus_actual', 
            'registro_censo'
        ]
        for campo in campos_ocultos:
            granja.pop(campo, None)
    return granja