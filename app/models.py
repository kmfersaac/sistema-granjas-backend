from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TipoUsuario(str, Enum):
    ADMIN = "admin"
    CAPTURA = "captura"

class EstatusFolio(str, Enum):
    ACTIVO = "Activo"
    PENDIENTE = "Pendiente"
    VENCIDO = "Vencido"
    CANCELADO = "Cancelado"

class TipoProduccion(str, Enum):
    CICLO_COMPLETO = "Ciclo Completo"
    ENGORDA = "Engorda"
    CRIA = "Cría"
    REPRODUCCION = "Reproducción"

class TipoEstablecimiento(str, Enum):
    RASTRO = "Rastro"
    MATADERO = "Matadero"
    MERCADO = "Mercado"
    OTRO = "Otro"

class EstatusUnidad(str, Enum):
    ACTIVA = "Activa"
    INACTIVA = "Inactiva"
    SUSPENDIDA = "Suspendida"
    EN_CONSTRUCCION = "En Construcción"

class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    asociaciones_permitidas: List[str] = []  # Lista de asociaciones que puede ver/editar
    tipo_usuario: TipoUsuario = TipoUsuario.CAPTURA

class UsuarioCreate(UsuarioBase):
    password: str

class Usuario(UsuarioBase):
    id_usuario: int
    activo: bool
    fecha_creacion: datetime

    class Config:
        from_attributes = True

class GranjaBase(BaseModel):
    # Campos básicos (visibles para todos)
    asociacion: Optional[str] = None
    estratificacion: Optional[str] = None
    clave_municipio_inegi: Optional[str] = None
    municipio: str
    nombre_granja: str
    propietario_ap_paterno: str
    propietario_ap_materno: Optional[str] = None
    propietario_nombres: str
    clave_registro_produccion: Optional[str] = None
    estatus_folio: Optional[EstatusFolio] = None
    
    # Campos de producción (visibles para todos)
    tipo_produccion: TipoProduccion
    numero_casetas: int
    capacidad_instalada: int
    poblacion_cerdos_s: Optional[int] = 0
    poblacion_cerdos_hr: Optional[int] = 0
    poblacion_cerdos_hrzo: Optional[int] = 0
    poblacion_cerdos_l: Optional[int] = 0
    poblacion_cerdos_d: Optional[int] = 0
    poblacion_cerdos_e: Optional[int] = 0
    poblacion_total: Optional[int] = 0
    
    # Campos de destino (visibles para todos)
    tipo_establecimiento_destino: Optional[TipoEstablecimiento] = None
    nombre_establecimiento_destino: Optional[str] = None
    ubicacion_establecimiento_destino: Optional[str] = None
    
    # Ubicación (visible para todos)
    ubicacion_granja: Optional[str] = None
    georreferenciacion_ln: Optional[float] = None
    georreferenciacion_lo: Optional[float] = None

class GranjaCreate(GranjaBase):
    # Campos solo admin (opcionales para creación)
    estatus_anterior: Optional[EstatusUnidad] = None
    estatus_actual: Optional[EstatusUnidad] = None
    registro_censo: Optional[bool] = False

class GranjaUpdate(BaseModel):
    # Campos editables por captura (incluye asociación, estratificación, clave INEGI)
    asociacion: Optional[str] = None
    estratificacion: Optional[str] = None
    clave_municipio_inegi: Optional[str] = None
    municipio: Optional[str] = None
    nombre_granja: Optional[str] = None
    propietario_ap_paterno: Optional[str] = None
    propietario_ap_materno: Optional[str] = None
    propietario_nombres: Optional[str] = None
    clave_registro_produccion: Optional[str] = None
    estatus_folio: Optional[EstatusFolio] = None
    tipo_produccion: Optional[TipoProduccion] = None
    numero_casetas: Optional[int] = None
    capacidad_instalada: Optional[int] = None
    poblacion_cerdos_s: Optional[int] = None
    poblacion_cerdos_hr: Optional[int] = None
    poblacion_cerdos_hrzo: Optional[int] = None
    poblacion_cerdos_l: Optional[int] = None
    poblacion_cerdos_d: Optional[int] = None
    poblacion_cerdos_e: Optional[int] = None
    poblacion_total: Optional[int] = None
    tipo_establecimiento_destino: Optional[TipoEstablecimiento] = None
    nombre_establecimiento_destino: Optional[str] = None
    ubicacion_establecimiento_destino: Optional[str] = None
    ubicacion_granja: Optional[str] = None
    georreferenciacion_ln: Optional[float] = None
    georreferenciacion_lo: Optional[float] = None

class GranjaAdminUpdate(BaseModel):
    # Campos exclusivos para admin (SOLO los 3 campos restringidos)
    estatus_anterior: Optional[EstatusUnidad] = None
    estatus_actual: Optional[EstatusUnidad] = None
    registro_censo: Optional[bool] = None

class Granja(GranjaBase):
    id_granja: int
    # Campos solo admin (ocultos para captura)
    estatus_anterior: Optional[EstatusUnidad] = None
    estatus_actual: Optional[EstatusUnidad] = None
    registro_censo: Optional[bool] = None
    # Auditoría
    creado_por: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True

class GranjaPublica(GranjaBase):
    """Versión pública de Granja (sin campos admin para usuarios captura)"""
    id_granja: int
    creado_por: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    tipo_usuario: str