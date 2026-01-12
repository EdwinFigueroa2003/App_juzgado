from flask import Blueprint, render_template, request, flash, jsonify
import sys
import os
from datetime import datetime, timedelta, date


def parse_date(value):
    """Convierte distintos formatos a datetime o devuelve None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    
    s = str(value).strip()
    if not s:
        return None
    
    # Intentar formatos comunes
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S.%f'):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None

def normalize_date(fecha_valor):
    """Convierte cualquier tipo de fecha a datetime.date"""
    if fecha_valor is None:
        return None
    
    if isinstance(fecha_valor, date):
        return fecha_valor
    elif isinstance(fecha_valor, datetime):
        return fecha_valor.date()
    else:
        try:
            # Intentar parsear como string
            if isinstance(fecha_valor, str):
                return datetime.strptime(fecha_valor, '%Y-%m-%d').date()
            return fecha_valor
        except:
            return None

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

# Crear un Blueprint
vistaexpediente = Blueprint('idvistaexpediente', __name__, template_folder='templates')

def calcular_estado_expediente(expediente_id, cursor):
    """
    Calcula el estado del expediente basado en la nueva lógica:
    - Si está en ingresos o actuaciones → Activo Pendiente
    - Si está en estados → Activo Resuelto (si < 1 año) o Inactivo Resuelto (si > 1 año)
    - Los expedientes siempre están activos, lo que cambia es el sub-estado
    
    Returns: (estado, descripcion)
    """
    
    try:
        # Verificar si tiene ingresos
        cursor.execute("""
            SELECT COUNT(*), MAX(fecha_ingreso) 
            FROM ingresos 
            WHERE expediente_id = %s
        """, (expediente_id,))
        
        ingresos_count, ultima_fecha_ingreso = cursor.fetchone()
        # Normalizar a datetime.date usando normalize_date
        ultima_fecha_ingreso = normalize_date(ultima_fecha_ingreso)
        
        # Verificar si tiene actuaciones
        cursor.execute("""
            SELECT COUNT(*), MAX(fecha_actuacion) 
            FROM actuaciones 
            WHERE expediente_id = %s
        """, (expediente_id,))
        
        actuaciones_count, ultima_fecha_actuacion = cursor.fetchone()
        # Normalizar a datetime.date usando normalize_date
        ultima_fecha_actuacion = normalize_date(ultima_fecha_actuacion)
        
        # Verificar si tiene estados
        cursor.execute("""
            SELECT COUNT(*), MAX(fecha_estado) 
            FROM estados 
            WHERE expediente_id = %s
        """, (expediente_id,))
        
        estados_count, ultima_fecha_estado = cursor.fetchone()
        # Normalizar a datetime.date usando normalize_date
        ultima_fecha_estado = normalize_date(ultima_fecha_estado)
        
        # Lógica de estados según las nuevas reglas
        if (ingresos_count > 0 or actuaciones_count > 0) and estados_count == 0:
            # Solo ingresos/actuaciones → Activo Pendiente
            if ingresos_count > 0 and actuaciones_count > 0:
                return "Activo Pendiente", f"En trámite - {ingresos_count} ingreso(s), {actuaciones_count} actuación(es)"
            elif ingresos_count > 0:
                return "Activo Pendiente", f"En trámite - {ingresos_count} ingreso(s)"
            else:
                return "Activo Pendiente", f"En trámite - {actuaciones_count} actuación(es)"
        
        elif estados_count > 0 and ingresos_count == 0 and actuaciones_count == 0:
            # Solo estados → Verificar si es reciente o antiguo
            if ultima_fecha_estado:
                # Convertir a datetime si es necesario
                if isinstance(ultima_fecha_estado, str):
                    try:
                        ultima_fecha_estado = datetime.strptime(ultima_fecha_estado, '%Y-%m-%d').date()
                    except:
                        ultima_fecha_estado = None
                
                if ultima_fecha_estado:
                    dias_desde_ultimo_estado = (datetime.now().date() - ultima_fecha_estado).days
                    
                    if dias_desde_ultimo_estado <= 365:
                        # Menos de 1 año → Activo Resuelto
                        return "Activo Resuelto", f"Resuelto hace {dias_desde_ultimo_estado} días - {estados_count} estado(s)"
                    else:
                        # Más de 1 año → Inactivo Resuelto
                        return "Inactivo Resuelto", f"Resuelto hace {dias_desde_ultimo_estado} días (>1 año) - {estados_count} estado(s)"
            
            # Si no se puede determinar la fecha, asumir activo resuelto
            return "Activo Resuelto", f"Resuelto - {estados_count} estado(s)"

        elif (ingresos_count > 0 or actuaciones_count > 0) and estados_count > 0:
            # Tiene ingresos/actuaciones y estados → Verificar cuál es más reciente
            # Encontrar la fecha más reciente entre ingresos y actuaciones
            fecha_mas_reciente_actividad = None
            if ultima_fecha_ingreso and ultima_fecha_actuacion:
                fecha_mas_reciente_actividad = max(ultima_fecha_ingreso, ultima_fecha_actuacion)
            elif ultima_fecha_ingreso:
                fecha_mas_reciente_actividad = ultima_fecha_ingreso
            elif ultima_fecha_actuacion:
                fecha_mas_reciente_actividad = ultima_fecha_actuacion
            
            if fecha_mas_reciente_actividad and ultima_fecha_estado:
                if fecha_mas_reciente_actividad > ultima_fecha_estado:
                    # Actividad más reciente → Activo Pendiente
                    desc_actividad = []
                    if ingresos_count > 0:
                        desc_actividad.append(f"{ingresos_count} ingreso(s)")
                    if actuaciones_count > 0:
                        desc_actividad.append(f"{actuaciones_count} actuación(es)")
                    return "Activo Pendiente", f"Reingresó después del último estado - {', '.join(desc_actividad)}, {estados_count} estado(s)"
                else:
                    # Estado más reciente → Aplicar lógica de estados
                    if isinstance(ultima_fecha_estado, str):
                        try:
                            ultima_fecha_estado = datetime.strptime(ultima_fecha_estado, '%Y-%m-%d').date()
                        except:
                            ultima_fecha_estado = None
                    
                    if ultima_fecha_estado:
                        dias_desde_ultimo_estado = (datetime.now().date() - ultima_fecha_estado).days
                        desc_actividad = []
                        if ingresos_count > 0:
                            desc_actividad.append(f"{ingresos_count} ingreso(s)")
                        if actuaciones_count > 0:
                            desc_actividad.append(f"{actuaciones_count} actuación(es)")
                        
                        if dias_desde_ultimo_estado <= 365:
                            return "Activo Resuelto", f"Resuelto hace {dias_desde_ultimo_estado} días - {', '.join(desc_actividad)}, {estados_count} estado(s)"
                        else:
                            return "Inactivo Resuelto", f"Resuelto hace {dias_desde_ultimo_estado} días (>1 año) - {', '.join(desc_actividad)}, {estados_count} estado(s)"
                    else:
                        desc_actividad = []
                        if ingresos_count > 0:
                            desc_actividad.append(f"{ingresos_count} ingreso(s)")
                        if actuaciones_count > 0:
                            desc_actividad.append(f"{actuaciones_count} actuación(es)")
                        return "Activo Resuelto", f"Resuelto - {', '.join(desc_actividad)}, {estados_count} estado(s)"
            else:
                # Si no hay fechas, usar contadores
                desc_actividad = []
                if ingresos_count > 0:
                    desc_actividad.append(f"{ingresos_count} ingreso(s)")
                if actuaciones_count > 0:
                    desc_actividad.append(f"{actuaciones_count} actuación(es)")
                return "Activo Pendiente", f"En trámite - {', '.join(desc_actividad)}, {estados_count} estado(s)"
        
        # Por defecto (sin ingresos, actuaciones ni estados)
        return "Pendiente", "Sin movimiento registrado"
        
    except Exception as e:
        print(f"Error calculando estado para expediente {expediente_id}: {e}")
        return "Error", "No se pudo determinar el estado"


@vistaexpediente.route('/expediente', methods=['GET', 'POST'])
def vista_expediente():
    expedientes = []
    radicado_buscar = ""
    estado_filtro = ""
    mensaje = ""
    
    if request.method == 'POST':
        tipo_busqueda = request.form.get('tipo_busqueda', 'radicado')
        
        if tipo_busqueda == 'radicado':
            # Búsqueda por radicado
            radicado_buscar = request.form.get('radicado', '').strip()
            
            if radicado_buscar:
                try:
                    expedientes = buscar_expedientes(radicado_buscar)
                    if not expedientes:
                        mensaje = f"No se encontraron expedientes con el radicado: {radicado_buscar}"
                    else:
                        mensaje = f"Se encontraron {len(expedientes)} expediente(s)"
                except Exception as e:
                    mensaje = f"Error en la búsqueda: {str(e)}"
                    flash(mensaje, 'error')
            else:
                mensaje = "Por favor ingrese un radicado para buscar"
                flash(mensaje, 'warning')
        
        elif tipo_busqueda == 'estado':
            # Filtrar por estado
            estado_filtro = request.form.get('estado_filtro', '').strip()
            orden_fecha = request.form.get('orden_fecha', 'DESC')
            limite = int(request.form.get('limite', 50))
            
            if estado_filtro:
                try:
                    expedientes = filtrar_por_estado(estado_filtro, orden_fecha=orden_fecha, limite=limite)
                    if not expedientes:
                        mensaje = f"No se encontraron expedientes con el estado: {estado_filtro}"
                    else:
                        mensaje = f"Se encontraron {len(expedientes)} expedientes con estado: {estado_filtro}"
                        
                        # Crear resumen_filtro para mostrar el botón "Ver más"
                        resumen_filtro = {
                            'estado_filtrado': estado_filtro,
                            'total_encontrados': len(expedientes),
                            'orden': 'Más reciente primero' if orden_fecha == 'DESC' else 'Más antiguo primero',
                            'limite': limite
                        }
                except Exception as e:
                    mensaje = f"Error en el filtro: {str(e)}"
                    flash(mensaje, 'error')
            else:
                mensaje = "Por favor seleccione un estado para filtrar"
                flash(mensaje, 'warning')
    
    return render_template('expediente.html', 
                         expedientes=expedientes, 
                         radicado_buscar=radicado_buscar,
                         estado_filtro=estado_filtro,
                         mensaje=mensaje,
                         resumen_filtro=locals().get('resumen_filtro', None))


def buscar_expedientes(radicado):
    """Busca expedientes por radicado completo o corto con TODA la información relacionada"""
    try:
        print(f"DEBUG: Buscando expedientes con radicado: {radicado}")
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Limpiar el radicado: eliminar espacios en blanco
        radicado_limpio = radicado.strip() if radicado else ''
        print(f"DEBUG: Radicado limpio: '{radicado_limpio}'")
        
        # Determinar si es búsqueda por radicado completo o corto
        es_radicado_completo = len(radicado_limpio) > 15  # Los radicados completos son largos
        print(f"DEBUG: Es radicado completo: {es_radicado_completo}")
        
        # Primero obtener los expedientes básicos
        if es_radicado_completo:
            # Búsqueda de radicado completo: intentar exacto primero, luego sin espacios
            query_expedientes = """
                SELECT 
                    e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                    e.juzgado_origen, e.fecha_ingreso, e.estado
                FROM expediente e
                WHERE e.radicado_completo = %s
                   OR REPLACE(e.radicado_completo, ' ', '') = %s
                   OR e.radicado_completo LIKE %s
                ORDER BY e.radicado_completo
            """
            radicado_sin_espacios = radicado_limpio.replace(' ', '')
            parametros = (radicado_limpio, radicado_sin_espacios, f'%{radicado_limpio}%')
        else:
            # Búsqueda de radicado corto o búsqueda parcial
            query_expedientes = """
                SELECT 
                    e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                    e.juzgado_origen, e.fecha_ingreso, e.estado
                FROM expediente e
                WHERE e.radicado_corto = %s OR e.radicado_completo LIKE %s
                ORDER BY e.radicado_completo NULLS LAST
            """
            parametros = (radicado_limpio, f'%{radicado_limpio}%')
        
        print(f"DEBUG: Ejecutando consulta con parámetros: {parametros}")
        cursor.execute(query_expedientes, parametros)
        expedientes_base = cursor.fetchall()
        
        print(f"DEBUG: Expedientes base encontrados: {len(expedientes_base)}")
        
        if not expedientes_base:
            cursor.close()
            conn.close()
            return []
        
        # Procesar cada expediente y obtener toda su información relacionada
        expedientes_completos = []
        
        for exp_row in expedientes_base:
            exp_id = exp_row[0]
            print(f"DEBUG: Procesando expediente ID: {exp_id}")
            
            parsed_fecha_ingreso = exp_row[6]  # Usar directamente el valor de la BD
            expediente = {
                'id': exp_row[0],
                'radicado_completo': exp_row[1],
                'radicado_corto': exp_row[2],
                'demandante': exp_row[3],
                'demandado': exp_row[4],
                'juzgado_origen': exp_row[5],
                'fecha_ingreso': parsed_fecha_ingreso,
                'estado': exp_row[7],  # Estado original de la tabla
                'fecha_actuacion': None,  # Se calculará dinámicamente
                'ingresos': [],
                'estados': [],
                'actuaciones': [],
                'estadisticas': {}
            }
            
            # Obtener ingresos con manejo de errores
            try:
                cursor.execute("""
                    SELECT fecha_ingreso, observaciones, solicitud, fechas, 
                           actuacion_id, ubicacion, fecha_estado_auto
                    FROM ingresos 
                    WHERE expediente_id = %s
                    ORDER BY fecha_ingreso ASC
                """, (exp_id,))
                
                ingresos_raw = cursor.fetchall()
                print(f"DEBUG: Ingresos encontrados: {len(ingresos_raw)}")
                
                expediente['ingresos'] = [
                    {
                        'fecha_ingreso': row[0],  # Usar directamente el valor de la BD
                        'observaciones': row[1],
                        'solicitud': row[2],
                        'fechas': row[3],
                        'actuacion_id': row[4],
                        'ubicacion': row[5],
                        'fecha_estado_auto': normalize_date(row[6]),  # Normalizar la fecha
                        'juzgado_origen': expediente['juzgado_origen']
                    }
                    for row in ingresos_raw
                ]
            except Exception as e:
                print(f"ERROR obteniendo ingresos para expediente {exp_id}: {e}")
                expediente['ingresos'] = []
            
            # Obtener estados con manejo de errores
            try:
                cursor.execute("""
                    SELECT fecha_estado, clase, auto_anotacion, observaciones, 
                           actuacion_id, ingresos_id, fecha_auto
                    FROM estados 
                    WHERE expediente_id = %s
                    ORDER BY fecha_estado ASC
                """, (exp_id,))
                
                estados_raw = cursor.fetchall()
                print(f"DEBUG: Estados encontrados: {len(estados_raw)}")
                
                expediente['estados'] = [
                    {
                        'fecha_estado': row[0],
                        'clase': row[1],
                        'auto_anotacion': row[2],
                        'observaciones': row[3],
                        'actuacion_id': row[4],
                        'ingresos_id': row[5],
                        'fecha_auto': row[6],
                        'demandante': expediente['demandante'],
                        'demandado': expediente['demandado']
                    }
                    for row in estados_raw
                ]
                
            except Exception as e:
                print(f"ERROR obteniendo estados para expediente {exp_id}: {e}")
                expediente['estados'] = []
            
            # Obtener actuaciones con manejo de errores
            try:
                cursor.execute("""
                    SELECT numero_actuacion, descripcion_actuacion, tipo_origen, 
                           archivo_origen, fecha_actuacion
                    FROM actuaciones 
                    WHERE expediente_id = %s
                    ORDER BY tipo_origen, numero_actuacion
                """, (exp_id,))
                
                actuaciones_raw = cursor.fetchall()
                print(f"DEBUG: Actuaciones encontradas: {len(actuaciones_raw)}")
                
                expediente['actuaciones'] = [
                    {
                        'numero_actuacion': row[0],
                        'descripcion_actuacion': row[1],
                        'tipo_origen': row[2],
                        'archivo_origen': row[3],
                        'fecha_actuacion': row[4]  # Usar directamente sin parse_date
                    }
                    for row in actuaciones_raw
                ]
                
            except Exception as e:
                print(f"ERROR obteniendo actuaciones para expediente {exp_id}: {e}")
                expediente['actuaciones'] = []
            
            # Calcular estado actual con la nueva lógica
            try:
                estado_actual, descripcion_estado = calcular_estado_expediente(exp_id, cursor)
                expediente['estado_actual'] = estado_actual
                expediente['descripcion_estado'] = descripcion_estado
                print(f"DEBUG: Estado calculado: {estado_actual} - {descripcion_estado}")
            except Exception as e:
                print(f"ERROR calculando estado para expediente {exp_id}: {e}")
                expediente['estado_actual'] = 'Error'
                expediente['descripcion_estado'] = 'Error al calcular estado'
            
            # Calcular estadísticas del expediente
            expediente['estadisticas'] = {
                'total_ingresos': len(expediente['ingresos']),
                'total_estados': len(expediente['estados']),
                'total_actuaciones': len(expediente['actuaciones'])
            }
            
            # Calcular fecha de última actuación dinámicamente
            fechas_actuacion = []
            
            # Agregar fechas de ingresos
            for ingreso in expediente['ingresos']:
                fecha_normalizada = normalize_date(ingreso['fecha_ingreso'])
                if fecha_normalizada:
                    fechas_actuacion.append(fecha_normalizada)
            
            # Agregar fechas de estados
            for estado in expediente['estados']:
                fecha_normalizada = normalize_date(estado['fecha_estado'])
                if fecha_normalizada:
                    fechas_actuacion.append(fecha_normalizada)
            
            # Agregar fechas de actuaciones
            for actuacion in expediente['actuaciones']:
                fecha_normalizada = normalize_date(actuacion['fecha_actuacion'])
                if fecha_normalizada:
                    fechas_actuacion.append(fecha_normalizada)
            
            # Establecer la fecha de última actuación
            if fechas_actuacion:
                expediente['fecha_actuacion'] = max(fechas_actuacion)
            else:
                expediente['fecha_actuacion'] = normalize_date(expediente['fecha_ingreso'])  # Fallback
            
            expedientes_completos.append(expediente)
        
        cursor.close()
        conn.close()
        
        print(f"DEBUG: Expedientes completos procesados: {len(expedientes_completos)}")
        return expedientes_completos
        
    except Exception as e:
        print(f"ERROR en buscar_expedientes: {e}")
        import traceback
        traceback.print_exc()
        # Retornar lista vacía en caso de error para evitar que la aplicación se rompa
        return []


def filtrar_por_estado(estado, orden_fecha='DESC', limite=50, fecha_desde=None, fecha_hasta=None, tipo_fecha='ingreso'):
    """Filtra expedientes por estado con la nueva lógica de estados"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Construir la consulta base
        where_conditions = []
        parametros = []
        
        # Filtro por estado según la nueva lógica
        if estado == "ACTIVO PENDIENTE" or estado == "ACTIVO":
            # Expedientes que tienen ingresos o actuaciones (están en trámite)
            where_conditions.append("""
                (EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
                 OR EXISTS (SELECT 1 FROM actuaciones a WHERE a.expediente_id = e.id))
            """)
            if estado == "ACTIVO PENDIENTE":
                # Solo los que no tienen estados o el último ingreso/actuación es más reciente que el último estado
                where_conditions.append("""
                    (NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                     OR 
                     GREATEST(
                         COALESCE((SELECT MAX(i2.fecha_ingreso) FROM ingresos i2 WHERE i2.expediente_id = e.id), DATE '1900-01-01'),
                         COALESCE((SELECT MAX(a2.fecha_actuacion) FROM actuaciones a2 WHERE a2.expediente_id = e.id), DATE '1900-01-01'),
                         COALESCE(e.fecha_ingreso, DATE '1900-01-01')
                     ) > 
                     (SELECT MAX(s2.fecha_estado) FROM estados s2 WHERE s2.expediente_id = e.id))
                """)
        
        elif estado == "ACTIVO RESUELTO":
            # Expedientes con estados y última fecha de estado < 1 año
            # Y que no tengan actividad más reciente (ingresos/actuaciones)
            where_conditions.append("EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)")
            where_conditions.append("""
                (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) > 
                (CURRENT_DATE - INTERVAL '1 year')
            """)
            # Verificar que el estado sea más reciente que cualquier actividad
            where_conditions.append("""
                (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) >= 
                COALESCE(
                    (SELECT MAX(i.fecha_ingreso) FROM ingresos i WHERE i.expediente_id = e.id),
                    (SELECT MAX(a.fecha_actuacion) FROM actuaciones a WHERE a.expediente_id = e.id),
                    '1900-01-01'::date
                )
            """)
        
        elif estado == "INACTIVO RESUELTO" or estado == "INACTIVO":
            # Expedientes con estados y última fecha de estado > 1 año
            # Y que no tengan actividad más reciente (ingresos/actuaciones)
            where_conditions.append("EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)")
            where_conditions.append("""
                (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) <= 
                (CURRENT_DATE - INTERVAL '1 year')
            """)
            # Verificar que el estado sea más reciente que cualquier actividad
            where_conditions.append("""
                (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) >= 
                COALESCE(
                    (SELECT MAX(i.fecha_ingreso) FROM ingresos i WHERE i.expediente_id = e.id),
                    (SELECT MAX(a.fecha_actuacion) FROM actuaciones a WHERE a.expediente_id = e.id),
                    '1900-01-01'::date
                )
            """)
        
        elif estado == "PENDIENTE":
            # Expedientes sin ingresos, estados ni actuaciones
            where_conditions.append("NOT EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)")
            where_conditions.append("NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)")
            where_conditions.append("NOT EXISTS (SELECT 1 FROM actuaciones a WHERE a.expediente_id = e.id)")
        
        # Construir la consulta completa
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        orden_sql = 'DESC' if orden_fecha == 'DESC' else 'ASC'
        
        query = f"""
            SELECT 
                e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                e.juzgado_origen, e.fecha_ingreso, e.estado,
                GREATEST(
                    COALESCE((SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id), DATE '1900-01-01'),
                    COALESCE((SELECT MAX(i.fecha_ingreso) FROM ingresos i WHERE i.expediente_id = e.id), DATE '1900-01-01'),
                    COALESCE((SELECT MAX(a.fecha_actuacion) FROM actuaciones a WHERE a.expediente_id = e.id), DATE '1900-01-01'),
                    COALESCE(e.fecha_ingreso, CURRENT_DATE)
                ) as fecha_orden
            FROM expediente e
            WHERE {where_clause}
            ORDER BY fecha_orden {orden_sql}
            LIMIT %s
        """
        
        parametros.append(limite)
        cursor.execute(query, parametros)
        resultados_principales = cursor.fetchall()
        
        # Para cada expediente, obtener toda su información relacionada
        expedientes_completos = []
        
        for row in resultados_principales:
            exp_id = row[0]
            
            expediente = {
                'id': row[0],
                'radicado_completo': row[1],
                'radicado_corto': row[2],
                'demandante': row[3],
                'demandado': row[4],
                'juzgado_origen': row[5],
                'fecha_ingreso': row[6],
                'estado': row[7],  # Estado original de la tabla
                'fecha_actuacion': row[8],  # Fecha calculada dinámicamente en la consulta
                'ingresos': [],
                'estados': [],
                'actuaciones': [],
                'estadisticas': {}
            }
            
            # Obtener ingresos
            cursor.execute("""
                SELECT fecha_ingreso, observaciones, solicitud, fechas, 
                       actuacion_id, ubicacion, fecha_estado_auto
                FROM ingresos 
                WHERE expediente_id = %s
                ORDER BY fecha_ingreso ASC
            """, (exp_id,))
            
            expediente['ingresos'] = [
                {
                    'fecha_ingreso': row[0],
                    'observaciones': row[1],
                    'solicitud': row[2],
                    'fechas': row[3],
                    'actuacion_id': row[4],
                    'ubicacion': row[5],
                    'fecha_estado_auto': normalize_date(row[6]),  # Normalizar la fecha
                    'juzgado_origen': expediente['juzgado_origen']
                }
                for row in cursor.fetchall()
            ]
            
            # Obtener estados
            cursor.execute("""
                SELECT fecha_estado, clase, auto_anotacion, observaciones, 
                       actuacion_id, ingresos_id, fecha_auto
                FROM estados 
                WHERE expediente_id = %s
                ORDER BY fecha_estado ASC
            """, (exp_id,))
            
            expediente['estados'] = [
                {
                    'fecha_estado': row[0],
                    'clase': row[1],
                    'auto_anotacion': row[2],
                    'observaciones': row[3],
                    'actuacion_id': row[4],
                    'ingresos_id': row[5],
                    'fecha_auto': row[6],
                    'demandante': expediente['demandante'],
                    'demandado': expediente['demandado']
                }
                for row in cursor.fetchall()
            ]
            
            # Obtener actuaciones
            cursor.execute("""
                SELECT numero_actuacion, descripcion_actuacion, tipo_origen, 
                       archivo_origen, fecha_actuacion
                FROM actuaciones 
                WHERE expediente_id = %s
                ORDER BY tipo_origen, numero_actuacion
            """, (exp_id,))
            
            expediente['actuaciones'] = [
                {
                    'numero_actuacion': row[0],
                    'descripcion_actuacion': row[1],
                    'tipo_origen': row[2],
                    'archivo_origen': row[3],
                    'fecha_actuacion': row[4]
                }
                for row in cursor.fetchall()
            ]
            
            # Calcular estado actual con la nueva lógica
            estado_actual, descripcion_estado = calcular_estado_expediente(exp_id, cursor)
            expediente['estado_actual'] = estado_actual
            expediente['descripcion_estado'] = descripcion_estado
            
            # Estadísticas básicas
            expediente['estadisticas'] = {
                'total_ingresos': len(expediente['ingresos']),
                'total_estados': len(expediente['estados']),
                'total_actuaciones': len(expediente['actuaciones'])
            }
            
            expedientes_completos.append(expediente)
        
        cursor.close()
        conn.close()
        
        return expedientes_completos
        
    except Exception as e:
        print(f"Error en filtrar_por_estado: {e}")
        raise e