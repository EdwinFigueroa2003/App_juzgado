from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
import sys
import os
from datetime import datetime, date

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.auth import login_required

# Crear un Blueprint
vistaactualizarexpediente = Blueprint('idvistaactualizarexpediente', __name__, template_folder='templates')

def obtener_roles_activos():
    """Obtiene la lista de roles disponibles"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nombre_rol 
            FROM roles 
            ORDER BY nombre_rol
        """)
        
        roles = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [{'id': r[0], 'nombre_rol': r[1]} for r in roles]
        
    except Exception as e:
        print(f"Error obteniendo roles: {e}")
        return []

def _detectar_columna_tipo(cursor):
    """Retorna el nombre de la columna existente entre 'tipo_solicitud' y 'tipo_tramite', o None"""
    try:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'expedientes' AND column_name IN ('tipo_solicitud', 'tipo_tramite')
        """)
        cols = [r[0] for r in cursor.fetchall()]
        if 'tipo_solicitud' in cols:
            return 'tipo_solicitud'
        if 'tipo_tramite' in cols:
            return 'tipo_tramite'
        return None
    except Exception:
        return None

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
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Limpiar el radicado: eliminar espacios
        radicado_limpio = radicado.strip() if radicado else ''
        
        # Determinar si es radicado completo o corto
        es_radicado_completo = len(radicado_limpio) > 15
        
        if es_radicado_completo:
            # Búsqueda mejorada para radicado completo
            tipo_expr, tipo_select = _fragmento_tipo_select(cursor, 'e')
            query = f"""
                SELECT id, radicado_completo, radicado_corto, demandante, demandado,
                       estado_actual, estado_principal, estado_adicional, ubicacion_actual,
                       {tipo_select}, juzgado_origen, responsable, observaciones, fecha_ultima_actualizacion,
                       fecha_ultima_actuacion_real
                FROM expedientes 
                WHERE radicado_completo = %s
                   OR REPLACE(radicado_completo, ' ', '') = %s
                   OR radicado_completo LIKE %s
                LIMIT 1
            """
            cursor.execute(query, (radicado_limpio, radicado_limpio.replace(' ', ''), f'%{radicado_limpio}%'))
        else:
            tipo_expr, tipo_select = _fragmento_tipo_select(cursor, 'e')
            query = f"""
                SELECT id, radicado_completo, radicado_corto, demandante, demandado,
                       estado_actual, estado_principal, estado_adicional, ubicacion_actual,
                       {tipo_select}, juzgado_origen, responsable, observaciones, fecha_ultima_actualizacion,
                       fecha_ultima_actuacion_real
                FROM expedientes 
                WHERE radicado_corto = %s
                LIMIT 1
            """
            cursor.execute(query, (radicado_limpio,))
        
        result = cursor.fetchone()
        
        if result:
            expediente = {
                'id': result[0],
                'radicado_completo': result[1],
                'radicado_corto': result[2],
                'demandante': result[3],
                'demandado': result[4],
                'estado_actual': result[5],
                'estado_principal': result[6],
                'estado_adicional': result[7],
                'ubicacion_actual': result[8],
                'tipo_solicitud': result[9],
                'juzgado_origen': result[10],
                'responsable': result[11],
                'observaciones': result[12],
                'fecha_ultima_actualizacion': result[13],
                'fecha_ultima_actuacion_real': result[14]
            }
            
            # Obtener ingresos con ID para poder eliminarlos
            cursor.execute("""
                SELECT id, fecha_ingreso, motivo_ingreso, observaciones_ingreso
                FROM ingresos_expediente 
                WHERE expediente_id = %s
                ORDER BY fecha_ingreso DESC
            """, (expediente['id'],))
            expediente['ingresos'] = cursor.fetchall()
            
            # Obtener estados con ID para poder eliminarlos
            cursor.execute("""
                SELECT id, fecha_estado, estado, observaciones
                FROM estados_expediente 
                WHERE expediente_id = %s
                ORDER BY fecha_estado DESC
            """, (expediente['id'],))
            expediente['estados'] = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return expediente
        else:
            cursor.close()
            conn.close()
            return None
            
    except Exception as e:
        print(f"Error buscando expediente por radicado: {e}")
        return None

def buscar_expediente_por_id(expediente_id):
    """Busca un expediente por ID y devuelve sus datos completos"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, radicado_completo, radicado_corto, demandante, demandado,
                   estado_actual, estado_principal, estado_adicional, ubicacion_actual, 
                   , juzgado_origen, responsable, observaciones, fecha_ultima_actualizacion,
                   fecha_ultima_actuacion_real
            FROM expedientes 
            WHERE id = %s
        """, (expediente_id,))
        
        result = cursor.fetchone()
        
        if result:
            expediente = {
                'id': result[0],
                'radicado_completo': result[1],
                'radicado_corto': result[2],
                'demandante': result[3],
                'demandado': result[4],
                'estado_actual': result[5],
                'estado_principal': result[6],
                'estado_adicional': result[7],
                'ubicacion_actual': result[8],
                '': result[9],
                'juzgado_origen': result[10],
                'responsable': result[11],
                'observaciones': result[12],
                'fecha_ultima_actualizacion': result[13],
                'fecha_ultima_actuacion_real': result[14]
            }
            
            # Obtener ingresos con ID para poder eliminarlos
            cursor.execute("""
                SELECT id, fecha_ingreso, motivo_ingreso, observaciones_ingreso
                FROM ingresos_expediente 
                WHERE expediente_id = %s
                ORDER BY fecha_ingreso DESC
            """, (expediente['id'],))
            expediente['ingresos'] = cursor.fetchall()
            
            # Obtener estados con ID para poder eliminarlos
            cursor.execute("""
                SELECT id, fecha_estado, estado, observaciones
                FROM estados_expediente 
                WHERE expediente_id = %s
                ORDER BY fecha_estado DESC
            """, (expediente['id'],))
            expediente['estados'] = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return expediente
        else:
            cursor.close()
            conn.close()
            return None
            
    except Exception as e:
        print(f"Error buscando expediente por ID: {e}")
        return None

@vistaactualizarexpediente.route('/actualizarexpediente', methods=['GET', 'POST'])
@login_required
def vista_actualizarexpediente():
    expediente = None
    roles = obtener_roles_activos()
    estadisticas = obtener_estadisticas_expedientes()
    
    # Verificar si viene un radicado como parámetro GET (desde el enlace de expediente)
    radicado_get = request.args.get('radicado')
    buscar_id = request.args.get('buscar_id')
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        
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
        elif accion == 'asignacion_masiva':
            return asignacion_masiva()
    
    # Si viene un radicado como parámetro GET, buscar automáticamente el expediente
    elif radicado_get:
        expediente = buscar_expediente_por_radicado(radicado_get)
        if expediente:
            flash(f'Expediente cargado automáticamente: {expediente["radicado_completo"] or expediente["radicado_corto"]}', 'info')
        else:
            flash(f'No se encontró expediente con radicado: {radicado_get}', 'error')
    
    # Si viene un ID para buscar (después de actualizar)
    elif buscar_id:
        expediente = buscar_expediente_por_id(buscar_id)
        if expediente:
            flash(f'Expediente recargado: {expediente["radicado_completo"] or expediente["radicado_corto"]}', 'info')
    
    return render_template('actualizarexpediente.html', expediente=expediente, roles=roles, estadisticas=estadisticas)

def buscar_expediente_para_actualizar():
    """Busca un expediente para actualizar"""
    radicado = request.form.get('radicado_buscar', '').strip()
    
    if not radicado:
        flash('Debe ingresar un radicado para buscar', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Limpiar el radicado: eliminar espacios
        radicado_limpio = radicado.strip()
        
        # Determinar si es radicado completo o corto
        es_radicado_completo = len(radicado_limpio) > 15
        
        if es_radicado_completo:
            # Búsqueda mejorada para radicado completo
            cursor.execute("""
                SELECT id, radicado_completo, radicado_corto, demandante, demandado,
                       estado_actual, estado_principal, estado_adicional, ubicacion_actual, 
                       tipo_solicitud, juzgado_origen, responsable, observaciones, fecha_ultima_actualizacion,
                       fecha_ultima_actuacion_real
                FROM expedientes 
                WHERE radicado_completo = %s
                   OR REPLACE(radicado_completo, ' ', '') = %s
                   OR radicado_completo LIKE %s
            """, (radicado_limpio, radicado_limpio.replace(' ', ''), f'%{radicado_limpio}%'))
        else:
            cursor.execute("""
                SELECT id, radicado_completo, radicado_corto, demandante, demandado,
                       estado_actual, estado_principal, estado_adicional, ubicacion_actual, 
                       tipo_solicitud, juzgado_origen, responsable, observaciones, fecha_ultima_actualizacion,
                       fecha_ultima_actuacion_real
                FROM expedientes 
                WHERE radicado_corto = %s
                LIMIT 1
            """, (radicado_limpio,))
        
        result = cursor.fetchone()
        
        if result:
            expediente = {
                'id': result[0],
                'radicado_completo': result[1],
                'radicado_corto': result[2],
                'demandante': result[3],
                'demandado': result[4],
                'estado_actual': result[5],
                'estado_principal': result[6],
                'estado_adicional': result[7],
                'ubicacion_actual': result[8],
                'tipo_solicitud': result[9],
                'juzgado_origen': result[10],
                'responsable': result[11],
                'observaciones': result[12],
                'fecha_ultima_actualizacion': result[13],
                'fecha_ultima_actuacion_real': result[14]
            }
            
            # Obtener ingresos con ID para poder eliminarlos
            cursor.execute("""
                SELECT id, fecha_ingreso, motivo_ingreso, observaciones_ingreso
                FROM ingresos_expediente 
                WHERE expediente_id = %s
                ORDER BY fecha_ingreso DESC
            """, (expediente['id'],))
            expediente['ingresos'] = cursor.fetchall()
            
            # Obtener estados con ID para poder eliminarlos
            cursor.execute("""
                SELECT id, fecha_estado, estado, observaciones
                FROM estados_expediente 
                WHERE expediente_id = %s
                ORDER BY fecha_estado DESC
            """, (expediente['id'],))
            expediente['estados'] = cursor.fetchall()
            
            flash(f'Expediente encontrado: {expediente["radicado_completo"] or expediente["radicado_corto"]}', 'success')
        else:
            flash(f'No se encontró expediente con radicado: {radicado}', 'error')
            expediente = None
        
        cursor.close()
        conn.close()
        
        roles = obtener_roles_activos()
        estadisticas = obtener_estadisticas_expedientes()
        return render_template('actualizarexpediente.html', expediente=expediente, roles=roles, estadisticas=estadisticas)
        
    except Exception as e:
        flash(f'Error buscando expediente: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def actualizar_expediente():
    """Actualiza los datos básicos del expediente"""
    try:
        expediente_id = request.form.get('expediente_id')
        
        if not expediente_id:
            flash('ID de expediente no válido', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Obtener datos del formulario
        demandante = request.form.get('demandante', '').strip()
        demandado = request.form.get('demandado', '').strip()
        estado_actual = request.form.get('estado_actual', '').strip()
        ubicacion_actual = request.form.get('ubicacion_actual', '').strip()
        tipo_solicitud = request.form.get('tipo_solicitud', '').strip()
        juzgado_origen = request.form.get('juzgado_origen', '').strip()
        rol_responsable = request.form.get('rol_responsable', '').strip()  # Cambio: ahora es rol
        observaciones = request.form.get('observaciones', '').strip()
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE expedientes 
            SET demandante = %s, demandado = %s, estado_actual = %s,
                ubicacion_actual = %s, tipo_solicitud = %s, juzgado_origen = %s,
                responsable = %s, observaciones = %s,
                fecha_ultima_actualizacion = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (demandante, demandado, estado_actual, ubicacion_actual, 
              tipo_solicitud, juzgado_origen, rol_responsable, observaciones, expediente_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Expediente actualizado exitosamente', 'success')
        
        # Redirigir de vuelta con el expediente cargado
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente') + 
                       f'?buscar_id={expediente_id}')
        
    except Exception as e:
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
            INSERT INTO ingresos_expediente 
            (expediente_id, fecha_ingreso, motivo_ingreso, observaciones_ingreso)
            VALUES (%s, %s, %s, %s)
        """, (expediente_id, fecha_ingreso_obj, motivo_ingreso, observaciones_ingreso))
        
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
            INSERT INTO estados_expediente 
            (expediente_id, estado, fecha_estado, observaciones)
            VALUES (%s, %s, %s, %s)
        """, (expediente_id, nuevo_estado, fecha_estado_obj, observaciones_estado))
        
        # Actualizar estado actual del expediente
        cursor.execute("""
            UPDATE expedientes 
            SET estado_actual = %s, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
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
            SELECT COUNT(*) FROM ingresos_expediente 
            WHERE id = %s AND expediente_id = %s
        """, (ingreso_id, expediente_id))
        
        if cursor.fetchone()[0] == 0:
            flash('Ingreso no encontrado o no pertenece al expediente', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Eliminar el ingreso
        cursor.execute("""
            DELETE FROM ingresos_expediente 
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
            SELECT COUNT(*) FROM estados_expediente 
            WHERE id = %s AND expediente_id = %s
        """, (estado_id, expediente_id))
        
        if cursor.fetchone()[0] == 0:
            flash('Estado no encontrado o no pertenece al expediente', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        # Eliminar el estado
        cursor.execute("""
            DELETE FROM estados_expediente 
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
            UPDATE expedientes 
            SET responsable = NULL, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
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

def asignacion_masiva():
    """Asigna responsables de manera masiva según criterios"""
    import random
    
    try:
        criterio = request.form.get('criterio_masivo', '').strip()
        valor_criterio = request.form.get('valor_criterio', '').strip()
        rol_asignar = request.form.get('rol_masivo', '').strip()
        
        if not criterio or not rol_asignar:
            flash('Debe seleccionar un criterio y un rol para la asignación masiva', 'error')
            return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Manejar asignación aleatoria
        if rol_asignar == 'ALEATORIO':
            return asignacion_aleatoria_masiva(criterio, valor_criterio, cursor, conn)
        
        # Manejar limpieza de responsables
        if rol_asignar == 'LIMPIAR':
            return limpiar_responsables_masivo(criterio, valor_criterio, cursor, conn)
        
        # Construir la consulta según el criterio (lógica original para roles específicos)
        if criterio == 'estado':
            if not valor_criterio:
                flash('Debe especificar un estado para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expedientes 
                SET responsable = %s, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE estado_actual = %s
            """
            cursor.execute(query, (rol_asignar, valor_criterio))
            
        elif criterio == 'sin_responsable':
            query = """
                UPDATE expedientes 
                SET responsable = %s, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE responsable IS NULL OR responsable = ''
            """
            cursor.execute(query, (rol_asignar,))
            
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
                UPDATE expedientes 
                SET responsable = %s, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE {tipo_col} ILIKE %s
            """
            cursor.execute(query, (rol_asignar, f'%{valor_criterio}%'))
            
        elif criterio == 'juzgado_origen':
            if not valor_criterio:
                flash('Debe especificar un juzgado de origen para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expedientes 
                SET responsable = %s, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE juzgado_origen ILIKE %s
            """
            cursor.execute(query, (rol_asignar, f'%{valor_criterio}%'))
            
        elif criterio == 'todos':
            if not confirm_todos():
                flash('Operación cancelada por el usuario', 'warning')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expedientes 
                SET responsable = %s, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
            """
            cursor.execute(query, (rol_asignar,))
        
        expedientes_actualizados = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if expedientes_actualizados > 0:
            flash(f'Asignación masiva exitosa: {expedientes_actualizados} expediente(s) asignado(s) al rol {rol_asignar}', 'success')
        else:
            flash('No se encontraron expedientes que cumplan con el criterio especificado', 'warning')
        
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
    except Exception as e:
        flash(f'Error en asignación masiva: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))

def limpiar_responsables_masivo(criterio, valor_criterio, cursor, conn):
    """Limpia responsables de manera masiva según criterios"""
    try:
        expedientes_actualizados = 0
        
        if criterio == 'estado':
            if not valor_criterio:
                flash('Debe especificar un estado para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expedientes 
                SET responsable = NULL, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE estado_actual = %s AND responsable IS NOT NULL
            """
            cursor.execute(query, (valor_criterio,))
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
                UPDATE expedientes 
                SET responsable = NULL, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE {tipo_col} ILIKE %s AND responsable IS NOT NULL
            """
            cursor.execute(query, (f'%{valor_criterio}%',))
            expedientes_actualizados = cursor.rowcount
            
        elif criterio == 'juzgado_origen':
            if not valor_criterio:
                flash('Debe especificar un juzgado de origen para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            query = """
                UPDATE expedientes 
                SET responsable = NULL, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE juzgado_origen ILIKE %s AND responsable IS NOT NULL
            """
            cursor.execute(query, (f'%{valor_criterio}%',))
            expedientes_actualizados = cursor.rowcount
            
        elif criterio == 'todos':
            query = """
                UPDATE expedientes 
                SET responsable = NULL, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE responsable IS NOT NULL
            """
            cursor.execute(query)
            expedientes_actualizados = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if expedientes_actualizados > 0:
            flash(f'Limpieza masiva exitosa: Se removió el responsable de {expedientes_actualizados} expediente(s)', 'success')
        else:
            flash('No se encontraron expedientes con responsable asignado que cumplan con el criterio especificado', 'warning')
        
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
        
    except Exception as e:
        flash(f'Error en limpieza masiva: {str(e)}', 'error')
        return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
    """Maneja la asignación aleatoria de roles"""
    import random
    
    try:
        # Obtener los expedientes que cumplen el criterio
        expedientes_ids = []
        
        if criterio == 'estado':
            if not valor_criterio:
                flash('Debe especificar un estado para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            cursor.execute("SELECT id FROM expedientes WHERE estado_actual = %s", (valor_criterio,))
            expedientes_ids = [row[0] for row in cursor.fetchall()]
            
        elif criterio == 'sin_responsable':
            cursor.execute("SELECT id FROM expedientes WHERE responsable IS NULL OR responsable = ''")
            expedientes_ids = [row[0] for row in cursor.fetchall()]
            
        elif criterio == 'tipo_solicitud':
            if not valor_criterio:
                flash('Debe especificar un tipo de trámite para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            tipo_col = _detectar_columna_tipo(cursor)
            if not tipo_col:
                flash('No existe columna `tipo_solicitud` ni `tipo_tramite` en la BD', 'warning')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            cursor.execute(f"SELECT id FROM expedientes WHERE {tipo_col} ILIKE %s", (f'%{valor_criterio}%',))
            expedientes_ids = [row[0] for row in cursor.fetchall()]
            
        elif criterio == 'juzgado_origen':
            if not valor_criterio:
                flash('Debe especificar un juzgado de origen para el criterio seleccionado', 'error')
                return redirect(url_for('idvistaactualizarexpediente.vista_actualizarexpediente'))
            
            cursor.execute("SELECT id FROM expedientes WHERE juzgado_origen ILIKE %s", (f'%{valor_criterio}%',))
            expedientes_ids = [row[0] for row in cursor.fetchall()]
            
        elif criterio == 'todos':
            cursor.execute("SELECT id FROM expedientes")
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
                UPDATE expedientes 
                SET responsable = %s, fecha_ultima_actualizacion = CURRENT_TIMESTAMP
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
        flash(f'Asignación aleatoria exitosa: {total_asignados} expediente(s) asignados. '
              f'ESCRIBIENTES: {contador_escribientes}, SUSTANCIADORES: {contador_sustanciadores}', 'success')
        
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
        cursor.execute("SELECT COUNT(*) FROM expedientes")
        total_expedientes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM expedientes WHERE responsable IS NULL OR responsable = ''")
        sin_responsable = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM expedientes WHERE responsable = 'ESCRIBIENTE'")
        escribientes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM expedientes WHERE responsable = 'SUSTANCIADOR'")
        sustanciadores = cursor.fetchone()[0]
        
        # Estados más comunes
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN estado_principal IS NOT NULL AND estado_adicional IS NOT NULL THEN 
                        CONCAT(estado_principal, ' + ', estado_adicional)
                    WHEN estado_principal IS NOT NULL THEN estado_principal
                    WHEN estado_adicional IS NOT NULL THEN estado_adicional
                    ELSE COALESCE(estado_actual, 'SIN_INFORMACION')
                END as estado_combinado,
                COUNT(*) as cantidad 
            FROM expedientes 
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