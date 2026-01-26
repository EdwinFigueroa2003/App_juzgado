from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
import sys
import os
import logging
from datetime import datetime, date

# Configurar logging específico para actualizarexpediente
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.auth import login_required

# Crear un Blueprint
vistaactualizarexpediente = Blueprint('idvistaactualizarexpediente', __name__, template_folder='templates')

def obtener_roles_activos():
    """Obtiene la lista de roles disponibles"""
    logger.info("=== INICIO obtener_roles_activos ===")
    try:
        conn = obtener_conexion()
        logger.info("Conexión a BD establecida correctamente")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nombre_rol 
            FROM roles 
            ORDER BY nombre_rol
        """)
        
        roles = cursor.fetchall()
        logger.info(f"Roles obtenidos: {len(roles)} registros")
        cursor.close()
        conn.close()
        
        result = [{'id': r[0], 'nombre_rol': r[1]} for r in roles]
        logger.info(f"=== FIN obtener_roles_activos - Retornando {len(result)} roles ===")
        return result
        
    except Exception as e:
        logger.error(f"ERROR en obtener_roles_activos: {str(e)}")
        return []

def _detectar_columnas_disponibles(cursor):
    """Detecta las columnas disponibles en la tabla expediente"""
    try:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'expediente'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Columnas disponibles en tabla expediente: {columns}")
        return columns
    except Exception as e:
        logger.error(f"Error detectando columnas: {str(e)}")
        return []

def _detectar_columna_tipo(cursor):
    """Retorna el nombre de la columna existente entre 'tipo_solicitud' y 'tipo_tramite', o None"""
    try:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'expediente' AND column_name IN ('tipo_solicitud', 'tipo_tramite')
        """)
        cols = [r[0] for r in cursor.fetchall()]
        if 'tipo_solicitud' in cols:
            return 'tipo_solicitud'
        if 'tipo_tramite' in cols:
            return 'tipo_tramite'
        return None
    except Exception:
        return None

def _detectar_columna_ubicacion(cursor):
    """Retorna el nombre de la columna existente entre 'ubicacion' y 'ubicacion_actual', o None"""
    try:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'expediente' AND column_name IN ('ubicacion', 'ubicacion_actual')
        """)
        cols = [r[0] for r in cursor.fetchall()]
        if 'ubicacion' in cols:
            return 'ubicacion'
        if 'ubicacion_actual' in cols:
            return 'ubicacion_actual'
        return None
    except Exception:
        return None

def _construir_select_expediente(cursor, alias=''):
    """Construye la parte SELECT para consultas de expediente basado en columnas disponibles"""
    available_columns = _detectar_columnas_disponibles(cursor)
    
    # Si no se proporciona alias, no usar prefijo
    prefix = f"{alias}." if alias else ""
    
    # Columnas base que siempre deben estar
    base_select = [
        f"{prefix}id",
        f"{prefix}radicado_completo", 
        f"{prefix}radicado_corto",
        f"{prefix}demandante",
        f"{prefix}demandado",
        f"{prefix}estado"
    ]
    
    # Columnas opcionales
    if 'ubicacion' in available_columns:
        base_select.append(f"{prefix}ubicacion")
    elif 'ubicacion_actual' in available_columns:
        base_select.append(f"{prefix}ubicacion_actual")
    else:
        base_select.append("NULL AS ubicacion")
    
    # Tipo de solicitud
    tipo_col = _detectar_columna_tipo(cursor)
    if tipo_col:
        base_select.append(f"{prefix}{tipo_col} AS tipo_solicitud")
    else:
        base_select.append("NULL AS tipo_solicitud")
    
    # Otras columnas opcionales
    optional_columns = ['juzgado_origen', 'responsable', 'observaciones', 'fecha_ingreso', 'turno']
    for col in optional_columns:
        if col in available_columns:
            base_select.append(f"{prefix}{col}")
        else:
            base_select.append(f"NULL AS {col}")
    
    return ", ".join(base_select)

def _fragmento_tipo_select(cursor, alias='e'):
    """Devuelve (tipo_expr, tipo_select) donde tipo_expr es la expresión para GROUP/WHERE y tipo_select es la parte SELECT con alias.
    Ejemplos: ('e.tipo_solicitud', 'e.tipo_solicitud AS tipo_solicitud') o
    ('COALESCE(e.tipo_solicitud, e.tipo_tramite)', 'COALESCE(e.tipo_solicitud, e.tipo_tramite) AS tipo_solicitud')
    Si no existe ninguna columna devuelve ("''", "'' AS tipo_solicitud")."""
    col = _detectar_columna_tipo(cursor)
    if col == 'tipo_solicitud':
        expr = f"{alias}.tipo_solicitud"
        return expr, f"{expr} AS tipo_solicitud"
    if col == 'tipo_tramite':
        expr = f"{alias}.tipo_tramite"
        return expr, f"{expr} AS tipo_solicitud"
    return "''", "'' AS tipo_solicitud"

def buscar_expediente_por_radicado(radicado):
    """Busca un expediente por radicado y devuelve sus datos completos"""
    logger.info("=== INICIO buscar_expediente_por_radicado ===")
    logger.info(f"Radicado a buscar: '{radicado}'")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Limpiar el radicado: eliminar espacios
        radicado_limpio = radicado.strip() if radicado else ''
        logger.info(f"Radicado limpio: '{radicado_limpio}'")
        
        # Determinar si es radicado completo o corto
        es_radicado_completo = len(radicado_limpio) > 15
        logger.info(f"Es radicado completo: {es_radicado_completo}")
        
        # Construir SELECT dinámico
        select_clause = _construir_select_expediente(cursor)
        logger.info(f"SELECT construido: {select_clause}")
        
        if es_radicado_completo:
            # Búsqueda mejorada para radicado completo
            query = f"""
                SELECT {select_clause}
                FROM expediente 
                WHERE radicado_completo = %s
                   OR REPLACE(radicado_completo, ' ', '') = %s
                   OR radicado_completo LIKE %s
                LIMIT 1
            """
            params = (radicado_limpio, radicado_limpio.replace(' ', ''), f'%{radicado_limpio}%')
        else:
            query = f"""
                SELECT {select_clause}
                FROM expediente 
                WHERE radicado_corto = %s
                LIMIT 1
            """
            params = (radicado_limpio,)
        
        logger.info(f"Query: {query}")
        logger.info(f"Parámetros: {params}")
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if result:
            logger.info(f"Expediente encontrado: {result}")
            
            # Mapear resultado dinámicamente
            available_columns = _detectar_columnas_disponibles(cursor)
            
            expediente = {
                'id': result[0],
                'radicado_completo': result[1],
                'radicado_corto': result[2],
                'demandante': result[3],
                'demandado': result[4],
                'estado_actual': result[5],
                'estado_principal': None,
                'estado_adicional': None,
                'ubicacion_actual': result[6] if result[6] is not None else '',
                'tipo_solicitud': result[7] if result[7] is not None else '',
                'juzgado_origen': result[8] if len(result) > 8 and result[8] is not None else '',
                'responsable': result[9] if len(result) > 9 else None,  # Mantener None si no hay responsable
                'observaciones': result[10] if len(result) > 10 and result[10] is not None else '',
                'fecha_ultima_actualizacion': None,
                'fecha_ultima_actuacion_real': result[11] if len(result) > 11 else None,
                'turno': result[12] if len(result) > 12 else None
            }
            
            logger.info(f"Expediente mapeado: {expediente}")
            
            # Verificar si existen tablas relacionadas
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('ingresos', 'estados', 'actuaciones')
            """)
            tablas_relacionadas = [row[0] for row in cursor.fetchall()]
            logger.info(f"Tablas relacionadas encontradas: {tablas_relacionadas}")
            
            # Obtener ingresos si la tabla existe
            if 'ingresos' in tablas_relacionadas:
                cursor.execute("""
                    SELECT id, fecha_ingreso, observaciones, solicitud, fechas, ubicacion
                    FROM ingresos 
                    WHERE expediente_id = %s
                    ORDER BY fecha_ingreso DESC
                """, (expediente['id'],))
                expediente['ingresos'] = cursor.fetchall()
                logger.info(f"Ingresos encontrados: {len(expediente['ingresos'])}")
            else:
                expediente['ingresos'] = []
                logger.info("Tabla ingresos no existe")
            
            # Obtener estados si la tabla existe
            if 'estados' in tablas_relacionadas:
                cursor.execute("""
                    SELECT id, fecha_estado, clase, auto_anotacion, observaciones
                    FROM estados 
                    WHERE expediente_id = %s
                    ORDER BY fecha_estado DESC
                """, (expediente['id'],))
                expediente['estados'] = cursor.fetchall()
                logger.info(f"Estados encontrados: {len(expediente['estados'])}")
            else:
                expediente['estados'] = []
                logger.info("Tabla estados no existe")
            
            # Obtener actuaciones si la tabla existe
            if 'actuaciones' in tablas_relacionadas:
                cursor.execute("""
                    SELECT id, numero_actuacion, descripcion_actuacion, fecha_actuacion, tipo_origen
                    FROM actuaciones 
                    WHERE expediente_id = %s
                    ORDER BY fecha_actuacion DESC
                """, (expediente['id'],))
                expediente['actuaciones'] = cursor.fetchall()
                logger.info(f"Actuaciones encontradas: {len(expediente['actuaciones'])}")
            else:
                expediente['actuaciones'] = []
                logger.info("Tabla actuaciones no existe")
            
            cursor.close()
            conn.close()
            logger.info("=== FIN buscar_expediente_por_radicado - ÉXITO ===")
            return expediente
        else:
            cursor.close()
            conn.close()
            logger.warning("=== FIN buscar_expediente_por_radicado - NO ENCONTRADO ===")
            return None
            
    except Exception as e:
        logger.error(f"ERROR en buscar_expediente_por_radicado: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        return None

def buscar_expediente_por_id(expediente_id):
    """Busca un expediente por ID y devuelve sus datos completos"""
    logger.info("=== INICIO buscar_expediente_por_id ===")
    logger.info(f"ID a buscar: {expediente_id}")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Construir SELECT dinámico
        select_clause = _construir_select_expediente(cursor)
        
        query = f"""
            SELECT {select_clause}
            FROM expediente 
            WHERE id = %s
        """
        
        logger.info(f"Query: {query}")
        cursor.execute(query, (expediente_id,))
        
        result = cursor.fetchone()
        
        if result:
            logger.info(f"Expediente encontrado: {result}")
            
            expediente = {
                'id': result[0],
                'radicado_completo': result[1],
                'radicado_corto': result[2],
                'demandante': result[3],
                'demandado': result[4],
                'estado_actual': result[5],
                'estado_principal': None,
                'estado_adicional': None,
                'ubicacion_actual': result[6] if result[6] is not None else '',
                'tipo_solicitud': result[7] if result[7] is not None else '',
                'juzgado_origen': result[8] if len(result) > 8 and result[8] is not None else '',
                'responsable': result[9] if len(result) > 9 else None,  # Mantener None si no hay responsable
                'observaciones': result[10] if len(result) > 10 and result[10] is not None else '',
                'fecha_ultima_actualizacion': None,
                'fecha_ultima_actuacion_real': result[11] if len(result) > 11 else None,
                'turno': result[12] if len(result) > 12 else None
            }
            
            # Verificar si existen tablas relacionadas
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('ingresos', 'estados', 'actuaciones')
            """)
            tablas_relacionadas = [row[0] for row in cursor.fetchall()]
            
            # Obtener ingresos si la tabla existe
            if 'ingresos' in tablas_relacionadas:
                cursor.execute("""
                    SELECT id, fecha_ingreso, observaciones, solicitud, fechas, ubicacion
                    FROM ingresos 
                    WHERE expediente_id = %s
                    ORDER BY fecha_ingreso DESC
                """, (expediente['id'],))
                expediente['ingresos'] = cursor.fetchall()
            else:
                expediente['ingresos'] = []
            
            # Obtener estados si la tabla existe
            if 'estados' in tablas_relacionadas:
                cursor.execute("""
                    SELECT id, fecha_estado, clase, auto_anotacion, observaciones
                    FROM estados 
                    WHERE expediente_id = %s
                    ORDER BY fecha_estado DESC
                """, (expediente['id'],))
                expediente['estados'] = cursor.fetchall()
            else:
                expediente['estados'] = []
            
            cursor.close()
            conn.close()
            logger.info("=== FIN buscar_expediente_por_id - ÉXITO ===")
            return expediente
        else:
            cursor.close()
            conn.close()
            logger.warning("=== FIN buscar_expediente_por_id - NO ENCONTRADO ===")
            return None
            
    except Exception as e:
        logger.error(f"ERROR en buscar_expediente_por_id: {str(e)}")
        return None

@vistaactualizarexpediente.route('/actualizarexpediente', methods=['GET', 'POST'])
@login_required
def vista_actualizarexpediente():
    logger.info("=== INICIO vista_actualizarexpediente ===")
    logger.info(f"Método: {request.method}")
    
    expediente = None
    roles = obtener_roles_activos()
    estadisticas = obtener_estadisticas_expedientes()
    
    # Verificar si viene un radicado como parámetro GET (desde el enlace de expediente)
    radicado_get = request.args.get('radicado')
    buscar_id = request.args.get('buscar_id')
    
    logger.info(f"Parámetros GET - radicado: '{radicado_get}', buscar_id: '{buscar_id}'")
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        logger.info(f"Acción POST: '{accion}'")
        
        if accion == 'buscar':
            return buscar_expediente_para_actualizar()
        elif accion == 'actualizar':
            return actualizar_expediente()
        elif accion == 'agregar_ingreso':
            return agregar_ingreso()
        elif accion == 'agregar_estado':
            return agregar_estado()
        elif accion == 'eliminar_ingreso':
            return eliminar_ingreso()
        elif accion == 'eliminar_estado':
            return eliminar_estado()
        elif accion == 'quitar_responsable':
            return quitar_responsable()
        elif accion == 'asignar_persona_especifica':
            return asignar_persona_especifica()
        elif accion == 'asignacion_masiva':
            return asignacion_masiva()
        elif accion == 'agregar_actuacion':
            return agregar_actuacion()
        elif accion == 'eliminar_actuacion':
            return eliminar_actuacion()
        elif accion == 'eliminar_expediente':
            return eliminar_expediente()
    
    # Si viene un radicado como parámetro GET, buscar automáticamente el expediente
    elif radicado_get:
        logger.info(f"Buscando expediente automáticamente por radicado: {radicado_get}")
        expediente = buscar_expediente_por_radicado(radicado_get)
        if expediente:
            flash(f'Expediente cargado automáticamente: {expediente["radicado_completo"] or expediente["radicado_corto"]}', 'info')
        else:
            flash(f'No se encontró expediente con radicado: {radicado_get}', 'error')
    
    # Si viene un ID para buscar (después de actualizar)
    elif buscar_id:
        logger.info(f"Buscando expediente por ID: {buscar_id}")
        expediente = buscar_expediente_por_id(buscar_id)
        if expediente:
            flash(f'Expediente recargado: {expediente["radicado_completo"] or expediente["radicado_corto"]}', 'info')
    
    logger.info("=== FIN vista_actualizarexpediente - Renderizando template ===")
    return render_template('actualizarexpediente.html', expediente=expediente, roles=roles, estadisticas=estadisticas)

@vistaactualizarexpediente.route('/api/buscar_personas', methods=['GET'])
@login_required
def api_buscar_personas():
    """API para buscar personas (usuarios) con autocompletado"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query or len(query) < 2:
            return jsonify([])
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Buscar usuarios que coincidan con la búsqueda (por nombre o usuario)
        cursor.execute("""
            SELECT DISTINCT nombre
            FROM usuarios
            WHERE (nombre IS NOT NULL AND nombre != '' AND nombre ILIKE %s)
               OR (usuario IS NOT NULL AND usuario != '' AND usuario ILIKE %s)
            ORDER BY nombre
            LIMIT 20
        """, (f'%{query}%', f'%{query}%'))
        
        personas = [row[0] for row in cursor.fetchall() if row[0]]
        
        # También incluir responsables únicos de expedientes que no estén en usuarios
        cursor.execute("""
            SELECT DISTINCT responsable
            FROM expediente
            WHERE responsable IS NOT NULL 
              AND responsable != ''
              AND responsable ILIKE %s
              AND responsable NOT IN (SELECT nombre FROM usuarios WHERE nombre IS NOT NULL)
            ORDER BY responsable
            LIMIT 10
        """, (f'%{query}%',))
        
        responsables_adicionales = [row[0] for row in cursor.fetchall()]
        
        # Combinar ambas listas sin duplicados
        todas_personas = list(dict.fromkeys(personas + responsables_adicionales))
        
        cursor.close()
        conn.close()
        
        logger.info(f"API buscar_personas: query='{query}', resultados={len(todas_personas)}")
        
        return jsonify(todas_personas[:20])  # Limitar a 20 resultados totales
        
    except Exception as e:
        logger.error(f"Error en api_buscar_personas: {str(e)}")
        return jsonify([]), 500

def buscar_expediente_para_actualizar():
    """Busca un expediente para actualizar"""
    logger.info("=== INICIO buscar_expediente_para_actualizar ===")
    
    radicado = request.form.get('radicado_buscar', '').strip()
    logger.info(f"Radicado recibido: '{radicado}'")
    
    if not radicado:
        logger.warning("No se proporcionó radicado")
        flash('Debe ingresar un radicado para buscar', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Limpiar el radicado: eliminar espacios
        radicado_limpio = radicado.strip()
        
        # Determinar si es radicado completo o corto
        es_radicado_completo = len(radicado_limpio) > 15
        logger.info(f"Es radicado completo: {es_radicado_completo}")
        
        # Construir SELECT dinámico
        select_clause = _construir_select_expediente(cursor)
        
        if es_radicado_completo:
            # Búsqueda mejorada para radicado completo
            query = f"""
                SELECT {select_clause}
                FROM expediente 
                WHERE radicado_completo = %s
                   OR REPLACE(radicado_completo, ' ', '') = %s
                   OR radicado_completo LIKE %s
            """
            params = (radicado_limpio, radicado_limpio.replace(' ', ''), f'%{radicado_limpio}%')
        else:
            query = f"""
                SELECT {select_clause}
                FROM expediente 
                WHERE radicado_corto = %s
                LIMIT 1
            """
            params = (radicado_limpio,)
        
        logger.info(f"Query: {query}")
        logger.info(f"Parámetros: {params}")
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if result:
            logger.info("Expediente encontrado")
            
            expediente = {
                'id': result[0],
                'radicado_completo': result[1],
                'radicado_corto': result[2],
                'demandante': result[3],
                'demandado': result[4],
                'estado_actual': result[5],
                'estado_principal': None,
                'estado_adicional': None,
                'ubicacion_actual': result[6] if result[6] is not None else '',
                'tipo_solicitud': result[7] if result[7] is not None else '',
                'juzgado_origen': result[8] if len(result) > 8 and result[8] is not None else '',
                'responsable': result[9] if len(result) > 9 else None,  # Mantener None si no hay responsable
                'observaciones': result[10] if len(result) > 10 and result[10] is not None else '',
                'fecha_ultima_actualizacion': None,
                'fecha_ultima_actuacion_real': result[11] if len(result) > 11 else None,
                'turno': result[12] if len(result) > 12 else None
            }
            
            # Verificar si existen tablas relacionadas
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('ingresos', 'estados', 'actuaciones')
            """)
            tablas_relacionadas = [row[0] for row in cursor.fetchall()]
            
            # Obtener ingresos si la tabla existe
            if 'ingresos' in tablas_relacionadas:
                cursor.execute("""
                    SELECT id, fecha_ingreso, observaciones, solicitud, fechas, ubicacion
                    FROM ingresos 
                    WHERE expediente_id = %s
                    ORDER BY fecha_ingreso DESC
                """, (expediente['id'],))
                expediente['ingresos'] = cursor.fetchall()
            else:
                expediente['ingresos'] = []
            
            # Obtener estados si la tabla existe
            if 'estados' in tablas_relacionadas:
                cursor.execute("""
                    SELECT id, fecha_estado, clase, auto_anotacion, observaciones
                    FROM estados 
                    WHERE expediente_id = %s
                    ORDER BY fecha_estado DESC
                """, (expediente['id'],))
                expediente['estados'] = cursor.fetchall()
            else:
                expediente['estados'] = []
            
            # Obtener actuaciones si la tabla existe
            if 'actuaciones' in tablas_relacionadas:
                cursor.execute("""
                    SELECT id, numero_actuacion, descripcion_actuacion, fecha_actuacion, tipo_origen
                    FROM actuaciones 
                    WHERE expediente_id = %s
                    ORDER BY fecha_actuacion DESC
                """, (expediente['id'],))
                expediente['actuaciones'] = cursor.fetchall()
            else:
                expediente['actuaciones'] = []
            
            flash(f'Expediente encontrado: {expediente["radicado_completo"] or expediente["radicado_corto"]}', 'success')
        else:
            logger.warning("Expediente no encontrado")
            flash(f'No se encontró expediente con radicado: {radicado}', 'error')
            expediente = None
        
        cursor.close()
        conn.close()
        
        roles = obtener_roles_activos()
        estadisticas = obtener_estadisticas_expedientes()
        logger.info("=== FIN buscar_expediente_para_actualizar ===")
        return render_template('actualizarexpediente.html', expediente=expediente, roles=roles, estadisticas=estadisticas)
        
    except Exception as e:
        logger.error(f"ERROR en buscar_expediente_para_actualizar: {str(e)}")
        flash(f'Error buscando expediente: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def actualizar_expediente():
    """Actualiza los datos básicos del expediente"""
    logger.info("=== INICIO actualizar_expediente ===")
    
    try:
        expediente_id = request.form.get('expediente_id')
        logger.info(f"ID del expediente: {expediente_id}")
        
        if not expediente_id:
            logger.warning("ID de expediente no válido")
            flash('ID de expediente no válido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Obtener datos del formulario
        demandante = request.form.get('demandante', '').strip()
        demandado = request.form.get('demandado', '').strip()
        estado_actual = request.form.get('estado_actual', '').strip()
        ubicacion_actual = request.form.get('ubicacion_actual', '').strip()
        tipo_solicitud = request.form.get('tipo_solicitud', '').strip()
        juzgado_origen = request.form.get('juzgado_origen', '').strip()
        rol_responsable = request.form.get('rol_responsable', '').strip()
        observaciones = request.form.get('observaciones', '').strip()
        radicado_completo = request.form.get('radicado_completo', '').strip()
        
        logger.info("Datos del formulario:")
        logger.info(f"  - radicado_completo: '{radicado_completo}'")
        logger.info(f"  - demandante: '{demandante}'")
        logger.info(f"  - demandado: '{demandado}'")
        logger.info(f"  - estado_actual: '{estado_actual}'")
        logger.info(f"  - ubicacion_actual: '{ubicacion_actual}'")
        logger.info(f"  - tipo_solicitud: '{tipo_solicitud}'")
        logger.info(f"  - juzgado_origen: '{juzgado_origen}'")
        logger.info(f"  - rol_responsable: '{rol_responsable}'")
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Detectar columnas disponibles
        available_columns = _detectar_columnas_disponibles(cursor)
        
        # Construir UPDATE dinámicamente
        update_fields = []
        update_values = []
        
        # Campos base que siempre deben estar
        base_fields = {
            'demandante': demandante,
            'demandado': demandado,
            'estado': estado_actual,
            'responsable': rol_responsable,
            'radicado_completo': radicado_completo
        }
        
        for field, value in base_fields.items():
            if field in available_columns:
                update_fields.append(f"{field} = %s")
                update_values.append(value)
        
        # Campos opcionales
        optional_fields = {}
        
        # Ubicación
        ubicacion_col = _detectar_columna_ubicacion(cursor)
        if ubicacion_col and ubicacion_actual:
            optional_fields[ubicacion_col] = ubicacion_actual
        
        # Tipo de solicitud
        tipo_col = _detectar_columna_tipo(cursor)
        if tipo_col and tipo_solicitud:
            optional_fields[tipo_col] = tipo_solicitud
        
        # Otros campos opcionales
        if 'juzgado_origen' in available_columns and juzgado_origen:
            optional_fields['juzgado_origen'] = juzgado_origen
        
        if 'observaciones' in available_columns and observaciones:
            optional_fields['observaciones'] = observaciones
        
        # Agregar campos opcionales al UPDATE
        for field, value in optional_fields.items():
            update_fields.append(f"{field} = %s")
            update_values.append(value)
        
        # Agregar ID al final
        update_values.append(expediente_id)
        
        if update_fields:
            query = f"""
                UPDATE expediente 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            logger.info(f"Query UPDATE: {query}")
            logger.info(f"Valores: {update_values}")
            
            cursor.execute(query, update_values)
            
            conn.commit()
            logger.info("Expediente actualizado correctamente")
            flash('Expediente actualizado exitosamente', 'success')
        else:
            logger.warning("No hay campos válidos para actualizar")
            flash('No hay campos válidos para actualizar', 'warning')
        
        cursor.close()
        conn.close()
        
        # Redirigir de vuelta con el expediente cargado
        logger.info("=== FIN actualizar_expediente - ÉXITO ===")
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        logger.error(f"ERROR en actualizar_expediente: {str(e)}")
        flash(f'Error actualizando expediente: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def agregar_ingreso():
    """Agrega un nuevo ingreso al expediente"""
    try:
        expediente_id = request.form.get('expediente_id')
        fecha_ingreso = request.form.get('nueva_fecha_ingreso', '').strip()
        motivo_ingreso = request.form.get('nuevo_motivo_ingreso', '').strip()
        observaciones_ingreso = request.form.get('nuevas_observaciones_ingreso', '').strip()
        
        if not expediente_id:
            flash('ID de expediente no válido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        if not fecha_ingreso:
            flash('La fecha de ingreso es obligatoria', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Convertir fecha
        try:
            fecha_ingreso_obj = datetime.strptime(fecha_ingreso, '%Y-%m-%d').date()
        except:
            flash('Formato de fecha inválido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ingresos 
            (expediente_id, fecha_ingreso, observaciones, solicitud)
            VALUES (%s, %s, %s, %s)
        """, (expediente_id, fecha_ingreso_obj, observaciones_ingreso, motivo_ingreso))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Ingreso agregado exitosamente', 'success')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        flash(f'Error agregando ingreso: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def agregar_estado():
    """Agrega un nuevo estado al expediente"""
    try:
        expediente_id = request.form.get('expediente_id')
        fecha_estado = request.form.get('nueva_fecha_estado', '').strip()
        nuevo_estado = request.form.get('nuevo_estado', '').strip()
        observaciones_estado = request.form.get('nuevas_observaciones_estado', '').strip()
        
        if not expediente_id:
            flash('ID de expediente no válido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        if not fecha_estado or not nuevo_estado:
            flash('La fecha y el estado son obligatorios', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Convertir fecha
        try:
            fecha_estado_obj = datetime.strptime(fecha_estado, '%Y-%m-%d').date()
        except:
            flash('Formato de fecha inválido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Insertar nuevo estado
        cursor.execute("""
            INSERT INTO estados 
            (expediente_id, clase, fecha_estado, auto_anotacion, observaciones)
            VALUES (%s, %s, %s, %s, %s)
        """, (expediente_id, nuevo_estado, fecha_estado_obj, observaciones_estado, observaciones_estado))
        
        # Actualizar estado actual del expediente
        cursor.execute("""
            UPDATE expediente 
            SET estado = %s
            WHERE id = %s
        """, (nuevo_estado, expediente_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Estado agregado y expediente actualizado exitosamente', 'success')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        flash(f'Error agregando estado: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def eliminar_ingreso():
    """Elimina un ingreso del expediente"""
    try:
        expediente_id = request.form.get('expediente_id')
        ingreso_id = request.form.get('ingreso_id')
        
        if not expediente_id or not ingreso_id:
            flash('IDs no válidos para eliminar ingreso', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Verificar que el ingreso pertenece al expediente
        cursor.execute("""
            SELECT COUNT(*) FROM ingresos 
            WHERE id = %s AND expediente_id = %s
        """, (ingreso_id, expediente_id))
        
        if cursor.fetchone()[0] == 0:
            flash('Ingreso no encontrado o no pertenece al expediente', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Eliminar el ingreso
        cursor.execute("""
            DELETE FROM ingresos 
            WHERE id = %s AND expediente_id = %s
        """, (ingreso_id, expediente_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Ingreso eliminado exitosamente', 'success')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        flash(f'Error eliminando ingreso: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def eliminar_estado():
    """Elimina un estado del expediente"""
    try:
        expediente_id = request.form.get('expediente_id')
        estado_id = request.form.get('estado_id')
        
        if not expediente_id or not estado_id:
            flash('IDs no válidos para eliminar estado', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Verificar que el estado pertenece al expediente
        cursor.execute("""
            SELECT COUNT(*) FROM estados 
            WHERE id = %s AND expediente_id = %s
        """, (estado_id, expediente_id))
        
        if cursor.fetchone()[0] == 0:
            flash('Estado no encontrado o no pertenece al expediente', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Eliminar el estado
        cursor.execute("""
            DELETE FROM estados 
            WHERE id = %s AND expediente_id = %s
        """, (estado_id, expediente_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Estado eliminado exitosamente', 'success')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        flash(f'Error eliminando estado: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def quitar_responsable():
    """Quita el responsable de un expediente"""
    try:
        expediente_id = request.form.get('expediente_id')
        
        if not expediente_id:
            flash('ID de expediente no válido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Quitar el responsable (establecer como NULL)
        cursor.execute("""
            UPDATE expediente 
            SET responsable = NULL
            WHERE id = %s
        """, (expediente_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Responsable removido exitosamente', 'success')
        
        # Redirigir de vuelta con el expediente cargado
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        flash(f'Error removiendo responsable: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def asignar_persona_especifica():
    """Asigna un expediente a una persona específica (nombre libre, sin importar rol)"""
    logger.info("=== INICIO asignar_persona_especifica ===")
    
    try:
        expediente_id = request.form.get('expediente_id')
        nombre_persona = request.form.get('nombre_persona_especifica', '').strip()
        
        logger.info(f"ID expediente: {expediente_id}")
        logger.info(f"Nombre persona: '{nombre_persona}'")
        
        if not expediente_id:
            flash('ID de expediente no válido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        if not nombre_persona:
            flash('Debe ingresar el nombre de la persona a asignar', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                           f'?buscar_id={expediente_id}')
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Verificar responsable actual antes de actualizar
        cursor.execute("SELECT responsable FROM expediente WHERE id = %s", (expediente_id,))
        responsable_anterior = cursor.fetchone()
        logger.info(f"Responsable anterior: {responsable_anterior[0] if responsable_anterior else 'N/A'}")
        
        # Asignar la persona específica al expediente
        cursor.execute("""
            UPDATE expediente 
            SET responsable = %s
            WHERE id = %s
        """, (nombre_persona, expediente_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"✓ UPDATE ejecutado: {cursor.rowcount} fila(s) afectada(s)")
            
            # Verificar que se guardó correctamente
            cursor.execute("SELECT responsable FROM expediente WHERE id = %s", (expediente_id,))
            responsable_nuevo = cursor.fetchone()
            logger.info(f"Responsable después de UPDATE: {responsable_nuevo[0] if responsable_nuevo else 'N/A'}")
            
            if responsable_nuevo and responsable_nuevo[0] == nombre_persona:
                logger.info(f"✅ Expediente {expediente_id} asignado a '{nombre_persona}' exitosamente")
                flash(f'Expediente asignado exitosamente a: {nombre_persona}', 'success')
            else:
                logger.error(f"⚠️ El responsable no coincide después del UPDATE")
                flash(f'Advertencia: La asignación puede no haberse guardado correctamente', 'warning')
        else:
            logger.warning(f"No se pudo actualizar el expediente {expediente_id}")
            flash('No se pudo asignar el expediente', 'warning')
        
        cursor.close()
        conn.close()
        
        logger.info("=== FIN asignar_persona_especifica - ÉXITO ===")
        
        # Redirigir de vuelta con el expediente cargado
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        logger.error(f"ERROR en asignar_persona_especifica: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        flash(f'Error asignando persona: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def asignacion_masiva():
    """Asigna responsables de manera masiva según criterios"""
    import random
    
    try:
        criterio = request.form.get('criterio_masivo', '').strip()
        valor_criterio = request.form.get('valor_criterio', '').strip()
        rol_asignar = request.form.get('rol_masivo', '').strip()
        cantidad_limite = request.form.get('cantidad_limite', '').strip()
        
        # Logging para debug
        logger.info("=== INICIO asignacion_masiva ===")
        logger.info(f"Criterio recibido: '{criterio}'")
        logger.info(f"Valor criterio recibido: '{valor_criterio}'")
        logger.info(f"Rol a asignar: '{rol_asignar}'")
        logger.info(f"Cantidad límite: '{cantidad_limite}'")
        logger.info(f"Todos los datos del formulario: {dict(request.form)}")
        
        if not criterio or not rol_asignar:
            logger.warning(f"Faltan datos: criterio='{criterio}', rol='{rol_asignar}'")
            flash('Debe seleccionar un criterio y un rol para la asignación masiva', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Convertir cantidad_limite a entero si se proporciona
        limite = None
        if cantidad_limite and cantidad_limite.isdigit():
            limite = int(cantidad_limite)
            if limite <= 0:
                flash('La cantidad debe ser un número positivo', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            logger.info(f"Límite aplicado: {limite}")
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Manejar asignación aleatoria
        if rol_asignar == 'ALEATORIO':
            logger.info("Ejecutando asignación aleatoria")
            return asignacion_aleatoria_masiva(criterio, valor_criterio, cursor, conn, limite)
        
        # Manejar limpieza de responsables
        if rol_asignar == 'LIMPIAR':
            logger.info("Ejecutando limpieza de responsables")
            return limpiar_responsables_masivo(criterio, valor_criterio, cursor, conn, limite)
        
        # Construir la consulta según el criterio (lógica original para roles específicos)
        if criterio == 'estado':
            logger.info(f"Procesando criterio 'estado' con valor: '{valor_criterio}'")
            if not valor_criterio:
                logger.warning(f"Valor de criterio vacío para estado: '{valor_criterio}'")
                flash('Debe especificar un estado para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expediente 
                SET responsable = %s
                WHERE estado = %s
            """
            params = (rol_asignar, valor_criterio)
            
            # Agregar límite si se especifica
            if limite:
                query += " AND id IN (SELECT id FROM expediente WHERE estado = %s ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (rol_asignar, valor_criterio, valor_criterio, limite)
            
            logger.info(f"Query a ejecutar: {query}")
            logger.info(f"Parámetros: {params}")
            cursor.execute(query, params)
            
        elif criterio == 'sin_responsable':
            query = """
                UPDATE expediente 
                SET responsable = %s
                WHERE responsable IS NULL OR responsable = ''
            """
            params = (rol_asignar,)
            
            # Agregar límite si se especifica
            if limite:
                query += " AND id IN (SELECT id FROM expediente WHERE responsable IS NULL OR responsable = '' ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (rol_asignar, limite)
            
            cursor.execute(query, params)
            
        elif criterio == 'tipo_solicitud':
            if not valor_criterio:
                flash('Debe especificar un tipo de trámite para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            # Determinar la columna real a usar (tipo_solicitud o tipo_tramite)
            tipo_col = _detectar_columna_tipo(cursor)
            if not tipo_col:
                flash('No existe columna `tipo_solicitud` ni `tipo_tramite` en la BD', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = f"""
                UPDATE expediente 
                SET responsable = %s
                WHERE {tipo_col} ILIKE %s
            """
            params = (rol_asignar, f'%{valor_criterio}%')
            
            # Agregar límite si se especifica
            if limite:
                query += f" AND id IN (SELECT id FROM expediente WHERE {tipo_col} ILIKE %s ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (rol_asignar, f'%{valor_criterio}%', f'%{valor_criterio}%', limite)
            
            cursor.execute(query, params)
            
        elif criterio == 'juzgado_origen':
            if not valor_criterio:
                flash('Debe especificar un juzgado de origen para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expediente 
                SET responsable = %s
                WHERE juzgado_origen ILIKE %s
            """
            params = (rol_asignar, f'%{valor_criterio}%')
            
            # Agregar límite si se especifica
            if limite:
                query += " AND id IN (SELECT id FROM expediente WHERE juzgado_origen ILIKE %s ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (rol_asignar, f'%{valor_criterio}%', f'%{valor_criterio}%', limite)
            
            cursor.execute(query, params)
            
        elif criterio == 'todos':
            if not confirm_todos():
                flash('Operación cancelada por el usuario', 'warning')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expediente 
                SET responsable = %s
            """
            params = (rol_asignar,)
            
            # Agregar límite si se especifica
            if limite:
                query += " WHERE id IN (SELECT id FROM expediente ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (rol_asignar, limite)
            
            cursor.execute(query, params)
        
        expedientes_actualizados = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if expedientes_actualizados > 0:
            mensaje = f'Asignación masiva exitosa: {expedientes_actualizados} expediente(s) asignado(s) al rol {rol_asignar}'
            if limite:
                mensaje += f' (limitado a {limite} expedientes)'
            flash(mensaje, 'success')
        else:
            flash('No se encontraron expedientes que cumplan con el criterio especificado', 'warning')
        
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
    except Exception as e:
        flash(f'Error en asignación masiva: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def limpiar_responsables_masivo(criterio, valor_criterio, cursor, conn, limite=None):
    """Limpia responsables de manera masiva según criterios"""
    try:
        expedientes_actualizados = 0
        
        if criterio == 'estado':
            if not valor_criterio:
                flash('Debe especificar un estado para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expediente 
                SET responsable = NULL
                WHERE estado = %s AND responsable IS NOT NULL
            """
            params = (valor_criterio,)
            
            # Agregar límite si se especifica
            if limite:
                query += " AND id IN (SELECT id FROM expediente WHERE estado = %s AND responsable IS NOT NULL ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (valor_criterio, valor_criterio, limite)
            
            cursor.execute(query, params)
            expedientes_actualizados = cursor.rowcount
            
        elif criterio == 'sin_responsable':
            # No tiene sentido limpiar expedientes que ya no tienen responsable
            flash('Los expedientes sin responsable ya no tienen responsable asignado', 'warning')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
        elif criterio == 'tipo_solicitud':
            if not valor_criterio:
                flash('Debe especificar un tipo de trámite para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            tipo_col = _detectar_columna_tipo(cursor)
            if not tipo_col:
                flash('No existe columna `tipo_solicitud` ni `tipo_tramite` en la BD', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = f"""
                UPDATE expediente 
                SET responsable = NULL
                WHERE {tipo_col} ILIKE %s AND responsable IS NOT NULL
            """
            params = (f'%{valor_criterio}%',)
            
            # Agregar límite si se especifica
            if limite:
                query += f" AND id IN (SELECT id FROM expediente WHERE {tipo_col} ILIKE %s AND responsable IS NOT NULL ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (f'%{valor_criterio}%', f'%{valor_criterio}%', limite)
            
            cursor.execute(query, params)
            expedientes_actualizados = cursor.rowcount
            
        elif criterio == 'juzgado_origen':
            if not valor_criterio:
                flash('Debe especificar un juzgado de origen para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expediente 
                SET responsable = NULL
                WHERE juzgado_origen ILIKE %s AND responsable IS NOT NULL
            """
            params = (f'%{valor_criterio}%',)
            
            # Agregar límite si se especifica
            if limite:
                query += " AND id IN (SELECT id FROM expediente WHERE juzgado_origen ILIKE %s AND responsable IS NOT NULL ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (f'%{valor_criterio}%', f'%{valor_criterio}%', limite)
            
            cursor.execute(query, params)
            expedientes_actualizados = cursor.rowcount
            
        elif criterio == 'todos':
            query = """
                UPDATE expediente 
                SET responsable = NULL
                WHERE responsable IS NOT NULL
            """
            params = ()
            
            # Agregar límite si se especifica
            if limite:
                query += " AND id IN (SELECT id FROM expediente WHERE responsable IS NOT NULL ORDER BY fecha_ingreso ASC LIMIT %s)"
                params = (limite,)
            
            cursor.execute(query, params)
            expedientes_actualizados = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if expedientes_actualizados > 0:
            mensaje = f'Limpieza masiva exitosa: Se removió el responsable de {expedientes_actualizados} expediente(s)'
            if limite:
                mensaje += f' (limitado a {limite} expedientes)'
            flash(mensaje, 'success')
        else:
            flash('No se encontraron expedientes con responsable asignado que cumplan con el criterio especificado', 'warning')
        
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
    except Exception as e:
        flash(f'Error en limpieza masiva: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def asignacion_aleatoria_masiva(criterio, valor_criterio, cursor, conn, limite=None):
    """Maneja la asignación aleatoria de roles"""
    import random
    
    try:
        # Obtener los expedientes que cumplen el criterio
        expedientes_ids = []
        
        if criterio == 'estado':
            if not valor_criterio:
                flash('Debe especificar un estado para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = "SELECT id FROM expediente WHERE estado = %s ORDER BY fecha_ingreso ASC"
            params = (valor_criterio,)
            if limite:
                query += " LIMIT %s"
                params = (valor_criterio, limite)
            
            cursor.execute(query, params)
            expedientes_ids = [row[0] for row in cursor.fetchall()]
            
        elif criterio == 'sin_responsable':
            query = "SELECT id FROM expediente WHERE responsable IS NULL OR responsable = '' ORDER BY fecha_ingreso ASC"
            params = ()
            if limite:
                query += " LIMIT %s"
                params = (limite,)
            
            cursor.execute(query, params)
            expedientes_ids = [row[0] for row in cursor.fetchall()]
            
        elif criterio == 'tipo_solicitud':
            if not valor_criterio:
                flash('Debe especificar un tipo de trámite para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            tipo_col = _detectar_columna_tipo(cursor)
            if not tipo_col:
                flash('No existe columna `tipo_solicitud` ni `tipo_tramite` en la BD', 'warning')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = f"SELECT id FROM expediente WHERE {tipo_col} ILIKE %s ORDER BY fecha_ingreso ASC"
            params = (f'%{valor_criterio}%',)
            if limite:
                query += " LIMIT %s"
                params = (f'%{valor_criterio}%', limite)
            
            cursor.execute(query, params)
            expedientes_ids = [row[0] for row in cursor.fetchall()]
            
        elif criterio == 'juzgado_origen':
            if not valor_criterio:
                flash('Debe especificar un juzgado de origen para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = "SELECT id FROM expediente WHERE juzgado_origen ILIKE %s ORDER BY fecha_ingreso ASC"
            params = (f'%{valor_criterio}%',)
            if limite:
                query += " LIMIT %s"
                params = (f'%{valor_criterio}%', limite)
            
            cursor.execute(query, params)
            expedientes_ids = [row[0] for row in cursor.fetchall()]
            
        elif criterio == 'todos':
            query = "SELECT id FROM expediente ORDER BY fecha_ingreso ASC"
            params = ()
            if limite:
                query += " LIMIT %s"
                params = (limite,)
            
            cursor.execute(query, params)
            expedientes_ids = [row[0] for row in cursor.fetchall()]
        
        if not expedientes_ids:
            flash('No se encontraron expedientes que cumplan con el criterio especificado', 'warning')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Asignar roles aleatorios
        roles_disponibles = ['ESCRIBIENTE', 'SUSTANCIADOR']
        contador_escribientes = 0
        contador_sustanciadores = 0
        
        for expediente_id in expedientes_ids:
            rol_aleatorio = random.choice(roles_disponibles)
            
            cursor.execute("""
                UPDATE expediente 
                SET responsable = %s
                WHERE id = %s
            """, (rol_aleatorio, expediente_id))
            
            if rol_aleatorio == 'ESCRIBIENTE':
                contador_escribientes += 1
            else:
                contador_sustanciadores += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        total_asignados = len(expedientes_ids)
        mensaje = f'Asignación aleatoria exitosa: {total_asignados} expediente(s) asignados. ESCRIBIENTES: {contador_escribientes}, SUSTANCIADORES: {contador_sustanciadores}'
        if limite:
            mensaje += f' (limitado a {limite} expedientes)'
        flash(mensaje, 'success')
        
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
    except Exception as e:
        flash(f'Error en asignación aleatoria: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def confirm_todos():
    """Función auxiliar para confirmar asignación a todos los expedientes"""
    # Esta función se usará con JavaScript en el frontend
    return True

def obtener_estadisticas_expedientes():
    """Obtiene estadísticas de expedientes para mostrar en asignación masiva"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Estadísticas generales
        cursor.execute("SELECT COUNT(*) FROM expediente")
        total_expedientes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM expediente WHERE responsable IS NULL OR responsable = ''")
        sin_responsable = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM expediente WHERE responsable = 'ESCRIBIENTE'")
        escribientes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM expediente WHERE responsable = 'SUSTANCIADOR'")
        sustanciadores = cursor.fetchone()[0]
        
        # Estados más comunes
        cursor.execute("""
            SELECT 
                COALESCE(estado, 'SIN_INFORMACION') as estado_combinado,
                COUNT(*) as cantidad 
            FROM expediente 
            GROUP BY estado_combinado
            ORDER BY cantidad DESC 
            LIMIT 8
        """)
        estados_comunes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            'total_expedientes': total_expedientes,
            'sin_responsable': sin_responsable,
            'escribientes': escribientes,
            'sustanciadores': sustanciadores,
            'estados_comunes': estados_comunes
        }
        
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return {
            'total_expedientes': 0,
            'sin_responsable': 0,
            'escribientes': 0,
            'sustanciadores': 0,
            'estados_comunes': []
        }

def agregar_actuacion():
    """Agrega una nueva actuación al expediente"""
    try:
        expediente_id = request.form.get('expediente_id')
        fecha_actuacion = request.form.get('nueva_fecha_actuacion', '').strip()
        numero_actuacion = request.form.get('nuevo_numero_actuacion', '').strip()
        descripcion_actuacion = request.form.get('nueva_descripcion_actuacion', '').strip()
        
        if not expediente_id:
            flash('ID de expediente no válido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        if not fecha_actuacion:
            flash('La fecha de actuación es obligatoria', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Convertir fecha
        try:
            fecha_actuacion_obj = datetime.strptime(fecha_actuacion, '%Y-%m-%d').date()
        except:
            flash('Formato de fecha inválido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO actuaciones 
            (expediente_id, fecha_actuacion, numero_actuacion, descripcion_actuacion, tipo_origen)
            VALUES (%s, %s, %s, %s, %s)
        """, (expediente_id, fecha_actuacion_obj, numero_actuacion, descripcion_actuacion, 'MANUAL'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Actuación agregada exitosamente', 'success')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        flash(f'Error agregando actuación: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def eliminar_actuacion():
    """Elimina una actuación del expediente"""
    try:
        expediente_id = request.form.get('expediente_id')
        actuacion_id = request.form.get('actuacion_id')
        
        if not expediente_id or not actuacion_id:
            flash('IDs no válidos para eliminar actuación', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Verificar que la actuación pertenece al expediente
        cursor.execute("""
            SELECT COUNT(*) FROM actuaciones 
            WHERE id = %s AND expediente_id = %s
        """, (actuacion_id, expediente_id))
        
        if cursor.fetchone()[0] == 0:
            flash('Actuación no encontrada o no pertenece al expediente', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Eliminar la actuación
        cursor.execute("""
            DELETE FROM actuaciones 
            WHERE id = %s AND expediente_id = %s
        """, (actuacion_id, expediente_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Actuación eliminada exitosamente', 'success')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
        flash(f'Error eliminando actuación: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
def eliminar_expediente():
    """Elimina un expediente completo y todos sus datos relacionados"""
    logger.info("=== INICIO eliminar_expediente ===")
    
    try:
        expediente_id = request.form.get('expediente_id')
        
        if not expediente_id:
            flash('ID de expediente no válido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        logger.info(f"Eliminando expediente ID: {expediente_id}")
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Obtener información del expediente antes de eliminarlo
        cursor.execute("""
            SELECT radicado_completo, radicado_corto, demandante, demandado
            FROM expediente 
            WHERE id = %s
        """, (expediente_id,))
        
        expediente_info = cursor.fetchone()
        
        if not expediente_info:
            flash('Expediente no encontrado', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        radicado = expediente_info[0] or expediente_info[1]
        demandante = expediente_info[2]
        demandado = expediente_info[3]
        
        logger.info(f"Expediente a eliminar: {radicado} - {demandante} vs {demandado}")
        
        # Eliminar en orden (tablas dependientes primero)
        tablas_a_limpiar = [
            ('actuaciones', 'expediente_id'),
            ('estados', 'expediente_id'), 
            ('ingresos', 'expediente_id'),
            ('expediente', 'id')
        ]
        
        registros_eliminados = {}
        
        for tabla, columna_id in tablas_a_limpiar:
            # Verificar si la tabla existe
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (tabla,))
            
            if cursor.fetchone()[0]:
                # Contar registros antes de eliminar
                cursor.execute(f"SELECT COUNT(*) FROM {tabla} WHERE {columna_id} = %s", (expediente_id,))
                count_antes = cursor.fetchone()[0]
                
                # Eliminar registros
                cursor.execute(f"DELETE FROM {tabla} WHERE {columna_id} = %s", (expediente_id,))
                registros_eliminados[tabla] = count_antes
                
                logger.info(f"Eliminados {count_antes} registros de tabla {tabla}")
            else:
                logger.warning(f"Tabla {tabla} no existe")
                registros_eliminados[tabla] = 0
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Mensaje de confirmación detallado
        mensaje_eliminacion = f"Expediente {radicado} eliminado exitosamente. "
        detalles = []
        
        if registros_eliminados.get('actuaciones', 0) > 0:
            detalles.append(f"{registros_eliminados['actuaciones']} actuaciones")
        if registros_eliminados.get('estados', 0) > 0:
            detalles.append(f"{registros_eliminados['estados']} estados")
        if registros_eliminados.get('ingresos', 0) > 0:
            detalles.append(f"{registros_eliminados['ingresos']} ingresos")
        
        if detalles:
            mensaje_eliminacion += f"Se eliminaron: {', '.join(detalles)}"
        
        flash(mensaje_eliminacion, 'success')
        logger.info(f"✅ Expediente {expediente_id} eliminado exitosamente")
        logger.info("=== FIN eliminar_expediente - ÉXITO ===")
        
        # Redirigir a la página principal sin expediente cargado
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
    except Exception as e:
        logger.error(f"ERROR en eliminar_expediente: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        flash(f'Error eliminando expediente: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))