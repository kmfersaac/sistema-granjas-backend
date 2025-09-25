from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Union
from app.database import get_db
from app.models import Granja, GranjaCreate, GranjaUpdate, GranjaAdminUpdate, GranjaPublica
from app.auth import get_current_user
from app.utils.security import puede_editar_granja, puede_eliminar_granja, puede_modificar_campos_admin, filtrar_campos_admin
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Union[Granja, GranjaPublica]])
async def listar_granjas(
    skip: int = 0,
    limit: int = 100,
    asociacion: Optional[str] = Query(None),
    municipio: Optional[str] = Query(None),
    usuario_actual: dict = Depends(get_current_user),
):
    """Listar granjas con filtros según permisos del usuario"""
    with get_db() as conn:
        with conn.cursor() as cur:
            query = "SELECT * FROM granjas WHERE 1=1"
            params = []
            
            # Filtro por asociación para usuarios captura
            if usuario_actual['tipo_usuario'] == 'captura':
                if usuario_actual['asociaciones_permitidas']:
                    placeholders = ','.join(['%s'] * len(usuario_actual['asociaciones_permitidas']))
                    query += f" AND asociacion IN ({placeholders})"
                    params.extend(usuario_actual['asociaciones_permitidas'])
                else:
                    # Si no tiene asociaciones permitidas, no puede ver nada
                    return []
            
            # Filtros adicionales
            if asociacion:
                query += " AND asociacion = %s"
                params.append(asociacion)
            if municipio:
                query += " AND municipio = %s"
                params.append(municipio)
            
            query += " ORDER BY fecha_creacion DESC LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            
            cur.execute(query, params)
            granjas = cur.fetchall()
            
            # Filtrar SOLO los 3 campos admin según permisos
            granjas_filtradas = []
            for granja in granjas:
                granja_filtrada = filtrar_campos_admin(granja.copy(), usuario_actual)
                granjas_filtradas.append(granja_filtrada)
            
            return granjas_filtradas

@router.get("/{granja_id}", response_model=Union[Granja, GranjaPublica])
async def obtener_granja(
    granja_id: int,
    usuario_actual: dict = Depends(get_current_user),
):
    """Obtener una granja específica"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM granjas WHERE id_granja = %s", (granja_id,))
            granja = cur.fetchone()
            
            if not granja:
                raise HTTPException(status_code=404, detail="Granja no encontrada")
            
            # Verificar permisos de vista
            if usuario_actual['tipo_usuario'] == 'captura':
                if granja.get('asociacion') not in usuario_actual.get('asociaciones_permitidas', []):
                    raise HTTPException(status_code=403, detail="No tiene permisos para ver esta granja")
            
            # Filtrar SOLO los 3 campos admin
            granja_filtrada = filtrar_campos_admin(granja, usuario_actual)
            return granja_filtrada

@router.post("/", response_model=Granja)
async def crear_granja(
    granja: GranjaCreate,
    usuario_actual: dict = Depends(get_current_user),
):
    """Crear nueva granja"""
    with get_db() as conn:
        with conn.cursor() as cur:
            # Verificar permisos para los 3 campos admin
            campos_admin_restringidos = ['estatus_anterior', 'estatus_actual', 'registro_censo']
            
            if usuario_actual['tipo_usuario'] != 'admin':
                # Usuario captura no puede establecer los 3 campos admin
                for campo in campos_admin_restringidos:
                    if getattr(granja, campo) is not None:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"No tiene permisos para modificar el campo: {campo}"
                        )
            
            # Insertar granja
            columns = []
            values = []
            placeholders = []
            
            # Todos los campos excepto los 3 campos admin (para captura)
            campos_permitidos = [
                'asociacion', 'estratificacion', 'clave_municipio_inegi',  # Ahora permitidos para captura
                'municipio', 'nombre_granja', 'propietario_ap_paterno', 
                'propietario_ap_materno', 'propietario_nombres', 'tipo_produccion',
                'numero_casetas', 'capacidad_instalada', 'ubicacion_granja',
                'georreferenciacion_ln', 'georreferenciacion_lo', 'clave_registro_produccion',
                'estatus_folio', 'poblacion_cerdos_s', 'poblacion_cerdos_hr', 
                'poblacion_cerdos_hrzo', 'poblacion_cerdos_l', 'poblacion_cerdos_d',
                'poblacion_cerdos_e', 'poblacion_total', 'tipo_establecimiento_destino',
                'nombre_establecimiento_destino', 'ubicacion_establecimiento_destino'
            ]
            
            # Si es admin, agregar los 3 campos admin
            if usuario_actual['tipo_usuario'] == 'admin':
                campos_permitidos.extend(campos_admin_restringidos)
            
            for field in campos_permitidos:
                value = getattr(granja, field)
                if value is not None:
                    columns.append(field)
                    values.append(value)
                    placeholders.append('%s')
            
            # Campos de auditoría
            columns.extend(['creado_por', 'fecha_creacion', 'fecha_actualizacion'])
            values.extend([usuario_actual['id_usuario']])
            placeholders.extend(['%s', 'NOW()', 'NOW()'])
            
            query = f"""
                INSERT INTO granjas ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """
            
            cur.execute(query, values)
            nueva_granja = cur.fetchone()
            
            # Registrar en logs
            cur.execute("""
                INSERT INTO logs_cambios (id_usuario, id_granja, tabla_afectada, accion, campo_modificado)
                VALUES (%s, %s, 'granjas', 'INSERT', 'creación de registro')
            """, (usuario_actual['id_usuario'], nueva_granja['id_granja']))
            
            return nueva_granja

@router.put("/{granja_id}", response_model=Union[Granja, GranjaPublica])
async def actualizar_granja(
    granja_id: int,
    granja_update: GranjaUpdate,
    usuario_actual: dict = Depends(get_current_user),
):
    """Actualizar granja (campos básicos - incluye asociación, estratificación, clave INEGI)"""
    with get_db() as conn:
        with conn.cursor() as cur:
            # Verificar que la granja existe y el usuario tiene permisos
            cur.execute("SELECT * FROM granjas WHERE id_granja = %s", (granja_id,))
            granja_existente = cur.fetchone()
            
            if not granja_existente:
                raise HTTPException(status_code=404, detail="Granja no encontrada")
            
            if not puede_editar_granja(usuario_actual, granja_existente):
                raise HTTPException(status_code=403, detail="No tiene permisos para editar esta granja")
            
            # Construir query de actualización
            update_fields = []
            values = []
            
            for field, value in granja_update.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = %s")
                    values.append(value)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No hay campos para actualizar")
            
            values.append(granja_id)
            
            query = f"""
                UPDATE granjas 
                SET {', '.join(update_fields)}, fecha_actualizacion = NOW()
                WHERE id_granja = %s
                RETURNING *
            """
            
            cur.execute(query, values)
            granja_actualizada = cur.fetchone()
            
            # Registrar en logs
            cur.execute("""
                INSERT INTO logs_cambios (id_usuario, id_granja, tabla_afectada, accion)
                VALUES (%s, %s, 'granjas', 'UPDATE')
            """, (usuario_actual['id_usuario'], granja_id))
            
            # Filtrar SOLO los 3 campos admin antes de retornar
            return filtrar_campos_admin(granja_actualizada, usuario_actual)

@router.put("/{granja_id}/admin", response_model=Granja)
async def actualizar_campos_admin(
    granja_id: int,
    admin_update: GranjaAdminUpdate,
    usuario_actual: dict = Depends(get_current_user),
):
    """Actualizar SOLO los 3 campos de administración (solo admin)"""
    if not puede_modificar_campos_admin(usuario_actual):
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # Verificar que la granja existe
            cur.execute("SELECT * FROM granjas WHERE id_granja = %s", (granja_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Granja no encontrada")
            
            # Construir query de actualización
            update_fields = []
            values = []
            
            for field, value in admin_update.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = %s")
                    values.append(value)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No hay campos para actualizar")
            
            values.append(granja_id)
            
            query = f"""
                UPDATE granjas 
                SET {', '.join(update_fields)}, fecha_actualizacion = NOW()
                WHERE id_granja = %s
                RETURNING *
            """
            
            cur.execute(query, values)
            return cur.fetchone()

@router.delete("/{granja_id}")
async def eliminar_granja(
    granja_id: int,
    usuario_actual: dict = Depends(get_current_user),
):
    """Eliminar granja"""
    with get_db() as conn:
        with conn.cursor() as cur:
            # Verificar que la granja existe y permisos
            cur.execute("SELECT * FROM granjas WHERE id_granja = %s", (granja_id,))
            granja = cur.fetchone()
            
            if not granja:
                raise HTTPException(status_code=404, detail="Granja no encontrada")
            
            if not puede_eliminar_granja(usuario_actual, granja):
                raise HTTPException(status_code=403, detail="No tiene permisos para eliminar esta granja")
            
            # Eliminar
            cur.execute("DELETE FROM granjas WHERE id_granja = %s", (granja_id,))
            
            # Registrar en logs
            cur.execute("""
                INSERT INTO logs_cambios (id_usuario, id_granja, tabla_afectada, accion)
                VALUES (%s, %s, 'granjas', 'DELETE')
            """, (usuario_actual['id_usuario'], granja_id))
            
            return {"message": "Granja eliminada correctamente"}