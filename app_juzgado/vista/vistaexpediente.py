from flask import Blueprint, render_template, request, flash, jsonify
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

# Crear un Blueprint
vistaexpediente = Blueprint('idvistaexpediente', __name__, template_folder='templates')

@vistaexpediente.route('/expediente', methods=['GET', 'POST'])
def vista_expediente():
    expedientes = []
    radicado_buscar = ""
    estado_filtro = ""
    orden_fecha = "DESC"
    limite = "50"
    fecha_desde = ""
    fecha_hasta = ""
    tipo_fecha = "ingreso"
    mensaje = ""
    resumen = None
    resumen_filtro = None
    paginacion = None
    
    # Parámetros de paginación
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    
    # Parámetros para mantener la búsqueda en paginación
    radicado_paginacion = request.args.get('radicado')
    estado_paginacion = request.args.get('estado')
    orden_paginacion = request.args.get('orden', 'DESC')
    limite_paginacion = request.args.get('limite', '50')
    fecha_desde_paginacion = request.args.get('fecha_desde', '')
    fecha_hasta_paginacion = request.args.get('fecha_hasta', '')
    tipo_fecha_paginacion = request.args.get('tipo_fecha', 'ingreso')
    
    if request.method == 'POST':
        tipo_busqueda = request.form.get('tipo_busqueda', 'radicado')
        
        if tipo_busqueda == 'radicado':
            # Búsqueda por radicado (funcionalidad existente)
            radicado_buscar = request.form.get('radicado', '').strip()
            
            if radicado_buscar:
                try:
                    expedientes_completos = buscar_expedientes(radicado_buscar)
                    if not expedientes_completos:
                        mensaje = f"No se encontraron expedientes con el radicado: {radicado_buscar}"
                        expedientes = []
                        paginacion = None
                    else:
                        if len(expedientes_completos) == 1:
                            total_ingresos = len(expedientes_completos[0]['ingresos'])
                            total_estados = len(expedientes_completos[0]['estados'])
                            mensaje = f"Expediente encontrado con {total_ingresos} ingreso(s) y {total_estados} estado(s)"
                            expedientes = expedientes_completos
                            paginacion = None
                        else:
                            # Crear resumen para múltiples expedientes
                            resumen = crear_resumen_expedientes(expedientes_completos, radicado_buscar)
                            mensaje = f"Se encontraron {len(expedientes_completos)} expedientes diferentes con el radicado corto: {radicado_buscar}"
                            
                            # Aplicar paginación
                            expedientes, paginacion = paginar_resultados(expedientes_completos, pagina, por_pagina)
                            paginacion['tipo_busqueda'] = 'radicado'
                            paginacion['radicado'] = radicado_buscar
                except Exception as e:
                    mensaje = f"Error en la búsqueda: {str(e)}"
                    flash(mensaje, 'error')
                    expedientes = []
                    paginacion = None
            else:
                mensaje = "Por favor ingrese un radicado para buscar"
                flash(mensaje, 'warning')
                expedientes = []
                paginacion = None
                
        elif tipo_busqueda == 'estado':
            # Nueva funcionalidad: Filtrar por estado
            estado_filtro = request.form.get('estado_filtro', '').strip()
            orden_fecha = request.form.get('orden_fecha', 'DESC')
            limite = request.form.get('limite', '50')
            fecha_desde = request.form.get('fecha_desde', '').strip()
            fecha_hasta = request.form.get('fecha_hasta', '').strip()
            tipo_fecha = request.form.get('tipo_fecha', 'ingreso')
            
            if estado_filtro:
                try:
                    expedientes_completos = filtrar_por_estado(estado_filtro, orden_fecha, int(limite), fecha_desde, fecha_hasta, tipo_fecha)
                    if not expedientes_completos:
                        mensaje = f"No se encontraron expedientes con el estado: {estado_filtro}"
                        expedientes = []
                        paginacion = None
                    else:
                        # Crear resumen para filtros
                        resumen_filtro = {
                            'estado_filtrado': estado_filtro,
                            'total_encontrados': len(expedientes_completos),
                            'orden': 'Más reciente primero' if orden_fecha == 'DESC' else 'Más antiguo primero',
                            'limite': limite
                        }
                        mensaje = f"Se encontraron {len(expedientes_completos)} expedientes con estado: {estado_filtro}"
                        
                        # Aplicar paginación
                        expedientes, paginacion = paginar_resultados(expedientes_completos, pagina, por_pagina)
                        paginacion['tipo_busqueda'] = 'estado'
                        paginacion['estado'] = estado_filtro
                        paginacion['orden'] = orden_fecha
                        paginacion['limite'] = limite
                except Exception as e:
                    mensaje = f"Error en el filtro: {str(e)}"
                    flash(mensaje, 'error')
                    expedientes = []
                    paginacion = None
            else:
                mensaje = "Por favor seleccione un estado para filtrar"
                flash(mensaje, 'warning')
                expedientes = []
                paginacion = None
                
    elif radicado_paginacion:
        # GET request con paginación para búsqueda por radicado
        try:
            expedientes_completos = buscar_expedientes(radicado_paginacion)
            if expedientes_completos:
                radicado_buscar = radicado_paginacion
                if len(expedientes_completos) > 1:
                    resumen = crear_resumen_expedientes(expedientes_completos, radicado_paginacion)
                    mensaje = f"Se encontraron {len(expedientes_completos)} expedientes diferentes con el radicado corto: {radicado_paginacion}"
                    expedientes, paginacion = paginar_resultados(expedientes_completos, pagina, por_pagina)
                    paginacion['tipo_busqueda'] = 'radicado'
                    paginacion['radicado'] = radicado_paginacion
                else:
                    expedientes = expedientes_completos
                    paginacion = None
        except Exception as e:
            mensaje = f"Error en la búsqueda: {str(e)}"
            flash(mensaje, 'error')
            
    elif estado_paginacion:
        # GET request con paginación para filtro por estado
        try:
            expedientes_completos = filtrar_por_estado(estado_paginacion, orden_paginacion, int(limite_paginacion), 
                                                     fecha_desde_paginacion, fecha_hasta_paginacion, tipo_fecha_paginacion)
            if expedientes_completos:
                estado_filtro = estado_paginacion
                orden_fecha = orden_paginacion
                limite = limite_paginacion
                fecha_desde = fecha_desde_paginacion
                fecha_hasta = fecha_hasta_paginacion
                tipo_fecha = tipo_fecha_paginacion
                
                resumen_filtro = {
                    'estado_filtrado': estado_paginacion,
                    'total_encontrados': len(expedientes_completos),
                    'orden': 'Más reciente primero' if orden_paginacion == 'DESC' else 'Más antiguo primero',
                    'limite': limite_paginacion
                }
                mensaje = f"Se encontraron {len(expedientes_completos)} expedientes con estado: {estado_paginacion}"
                
                expedientes, paginacion = paginar_resultados(expedientes_completos, pagina, por_pagina)
                paginacion['tipo_busqueda'] = 'estado'
                paginacion['estado'] = estado_paginacion
                paginacion['orden'] = orden_paginacion
                paginacion['limite'] = limite_paginacion
        except Exception as e:
            mensaje = f"Error en el filtro: {str(e)}"
            flash(mensaje, 'error')
    
    return render_template('expediente.html', 
                         expedientes=expedientes, 
                         radicado_buscar=radicado_buscar,
                         estado_filtro=estado_filtro,
                         orden_fecha=orden_fecha,
                         limite=limite,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         tipo_fecha=tipo_fecha,
                         mensaje=mensaje,
                         resumen=resumen,
                         resumen_filtro=resumen_filtro,
                         paginacion=paginacion)

def crear_resumen_expedientes(expedientes, radicado_buscar):
    """Crea un resumen cuando hay múltiples expedientes"""
    resumen = {
        'radicado_buscado': radicado_buscar,
        'total_expedientes': len(expedientes),
        'total_ingresos': sum(len(exp['ingresos']) for exp in expedientes),
        'total_estados': sum(len(exp['estados']) for exp in expedientes),
        'expedientes_resumen': []
    }
    
    for exp in expedientes:
        resumen['expedientes_resumen'].append({
            'radicado_completo': exp['radicado_completo'],
            'demandante': exp['demandante'],
            'demandado': exp['demandado'],
            'ingresos': len(exp['ingresos']),
            'estados': len(exp['estados'])
        })
    
    return resumen

def paginar_resultados(expedientes, pagina, por_pagina):
    """Pagina los resultados de expedientes"""
    total = len(expedientes)
    inicio = (pagina - 1) * por_pagina
    fin = inicio + por_pagina
    
    expedientes_pagina = expedientes[inicio:fin]
    
    # Calcular información de paginación
    total_paginas = (total + por_pagina - 1) // por_pagina  # Redondeo hacia arriba
    
    paginacion = {
        'pagina_actual': pagina,
        'por_pagina': por_pagina,
        'total_items': total,
        'total_paginas': total_paginas,
        'tiene_anterior': pagina > 1,
        'tiene_siguiente': pagina < total_paginas,
        'pagina_anterior': pagina - 1 if pagina > 1 else None,
        'pagina_siguiente': pagina + 1 if pagina < total_paginas else None,
        'inicio_item': inicio + 1,
        'fin_item': min(fin, total),
        'paginas_mostrar': calcular_paginas_mostrar(pagina, total_paginas)
    }
    
    return expedientes_pagina, paginacion

def calcular_paginas_mostrar(pagina_actual, total_paginas, ventana=5):
    """Calcula qué páginas mostrar en la paginación"""
    if total_paginas <= ventana:
        return list(range(1, total_paginas + 1))
    
    # Calcular el rango de páginas a mostrar
    inicio = max(1, pagina_actual - ventana // 2)
    fin = min(total_paginas, inicio + ventana - 1)
    
    # Ajustar si estamos cerca del final
    if fin - inicio < ventana - 1:
        inicio = max(1, fin - ventana + 1)
    
    return list(range(inicio, fin + 1))

def filtrar_por_estado(estado, orden_fecha='DESC', limite=50, fecha_desde=None, fecha_hasta=None, tipo_fecha='ingreso'):
    """Filtra expedientes por estado con toda la información relacionada"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Construir la consulta según el tipo de estado
        # Mapear los valores del formulario a los valores reales en la BD
        if estado == 'ACTIVO':
            # Buscar expedientes con estado_actual que EMPIECE con ACTIVO
            where_clause = "e.estado_actual LIKE %s"
            parametros = ['ACTIVO%']
        elif estado == 'INACTIVO':
            # Buscar expedientes con estado_actual que EMPIECE con INACTIVO
            where_clause = "e.estado_actual LIKE %s"
            parametros = ['INACTIVO%']
        elif estado == 'PENDIENTE':
            # Buscar expedientes con estado_actual = PENDIENTE o que contenga PENDIENTE
            where_clause = "(e.estado_actual = %s OR e.estado_actual LIKE %s)"
            parametros = ['PENDIENTE', '%PENDIENTE%']
        elif estado == 'ACTIVO_PENDIENTE':
            # Buscar específicamente ACTIVO PENDIENTE
            where_clause = "e.estado_actual = %s"
            parametros = ['ACTIVO PENDIENTE']
        elif estado == 'INACTIVO_RESUELTO':
            # Buscar específicamente INACTIVO RESUELTO
            where_clause = "e.estado_actual = %s"
            parametros = ['INACTIVO RESUELTO']
        elif estado == 'SALIO' or estado == 'SALIÓ':
            # Filtrar por estado adicional SALIO (si existe esa columna)
            where_clause = "e.estado_adicional = %s"
            parametros = ['SALIO']
        elif estado == 'SIN_FECHA' or estado == 'SIN_DATOS':
            # Expedientes sin datos
            where_clause = "e.estado_actual = %s"
            parametros = ['SIN_DATOS']
        else:
            # Búsqueda exacta por estado_actual
            where_clause = "e.estado_actual = %s"
            parametros = [estado]
        
        # Determinar el campo de fecha para ordenar
        orden_sql = 'DESC' if orden_fecha == 'DESC' else 'ASC'
        
        # Construir filtros de fecha adicionales
        date_filters = []
        if fecha_desde or fecha_hasta:
            if tipo_fecha == 'ingreso':
                if fecha_desde:
                    date_filters.append("EXISTS (SELECT 1 FROM ingresos_expediente i WHERE i.expediente_id = e.id AND i.fecha_ingreso >= %s)")
                    parametros.append(fecha_desde)
                if fecha_hasta:
                    date_filters.append("EXISTS (SELECT 1 FROM ingresos_expediente i WHERE i.expediente_id = e.id AND i.fecha_ingreso <= %s)")
                    parametros.append(fecha_hasta)
            elif tipo_fecha == 'estado':
                if fecha_desde:
                    date_filters.append("EXISTS (SELECT 1 FROM estados_expediente es WHERE es.expediente_id = e.id AND es.fecha_estado >= %s)")
                    parametros.append(fecha_desde)
                if fecha_hasta:
                    date_filters.append("EXISTS (SELECT 1 FROM estados_expediente es WHERE es.expediente_id = e.id AND es.fecha_estado <= %s)")
                    parametros.append(fecha_hasta)
            elif tipo_fecha == 'ambas':
                fecha_conditions = []
                if fecha_desde:
                    fecha_conditions.append("(EXISTS (SELECT 1 FROM ingresos_expediente i WHERE i.expediente_id = e.id AND i.fecha_ingreso >= %s) OR EXISTS (SELECT 1 FROM estados_expediente es WHERE es.expediente_id = e.id AND es.fecha_estado >= %s))")
                    parametros.extend([fecha_desde, fecha_desde])
                if fecha_hasta:
                    fecha_conditions.append("(EXISTS (SELECT 1 FROM ingresos_expediente i WHERE i.expediente_id = e.id AND i.fecha_ingreso <= %s) OR EXISTS (SELECT 1 FROM estados_expediente es WHERE es.expediente_id = e.id AND es.fecha_estado <= %s))")
                    parametros.extend([fecha_hasta, fecha_hasta])
                date_filters.extend(fecha_conditions)
        
        # Combinar filtros
        all_filters = [where_clause]
        if date_filters:
            all_filters.extend(date_filters)
        
        combined_where = " AND ".join(all_filters)
        
        query = f"""
            SELECT 
                e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                e.estado_actual, e.ubicacion_actual, e.tipo_solicitud, e.juzgado_origen, e.responsable,
                e.fecha_ultima_actualizacion, e.fecha_creacion_registro, e.fecha_resolucion,
                e.observaciones, e.total_tramites,
                COALESCE(e.fecha_ultima_actualizacion, CURRENT_DATE) as fecha_orden
            FROM expedientes e
            WHERE {combined_where}
            ORDER BY fecha_orden {orden_sql}
            LIMIT %s
        """
        
        # Agregar límite a los parámetros
        parametros.append(limite)
        
        cursor.execute(query, parametros)
        resultados_principales = cursor.fetchall()
        
        # Para cada expediente, obtener toda su información relacionada
        expedientes_completos = []
        
        for row in resultados_principales:
            exp_id = row[0]
            
            try:
                expediente = {
                    'id': row[0],
                    'radicado_completo': row[1],
                    'radicado_corto': row[2],
                    'demandante': row[3],
                    'demandado': row[4],
                    'estado_actual': row[5] or 'SIN_INFORMACION',
                    'ubicacion_actual': row[6],
                    'tipo_solicitud': row[7],
                    'juzgado_origen': row[8],
                    'responsable': row[9],
                    'fecha_ultima_actualizacion': row[10],
                    'fecha_creacion_registro': row[11],
                    'fecha_resolucion': row[12],
                    'observaciones': row[13],
                    'total_tramites': row[14],
                    'estado_principal': None,  # Columna no existe, usar None
                    'estado_adicional': None,  # Columna no existe, usar None
                    'fecha_ultima_actuacion_real': None,  # Columna no existe, usar None
                    'ingresos': [],
                    'estados': [],
                    'tramites_detallados': [],
                    'estadisticas': {}
                }
            except Exception as e:
                print(f"Error creating expediente: {e}")
                continue
            
            # Obtener ingresos
            cursor.execute("""
                SELECT fecha_ingreso, motivo_ingreso, observaciones_ingreso, juzgado_origen
                FROM ingresos_expediente 
                WHERE expediente_id = %s
                ORDER BY fecha_ingreso ASC
            """, (exp_id,))
            
            expediente['ingresos'] = [
                {
                    'fecha_ingreso': row[0],
                    'motivo_ingreso': row[1],
                    'observaciones_ingreso': row[2],
                    'juzgado_origen': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # Obtener estados
            cursor.execute("""
                SELECT fecha_estado, estado, observaciones, juzgado_origen
                FROM estados_expediente 
                WHERE expediente_id = %s
                ORDER BY fecha_estado DESC
            """, (exp_id,))
            
            expediente['estados'] = [
                {
                    'fecha_estado': row[0],
                    'estado_registrado': row[1],
                    'observaciones_estado': row[2],
                    'juzgado_origen': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # Obtener algunos trámites detallados (limitados para rendimiento)
            if expediente['radicado_completo']:
                try:
                    cursor.execute("""
                        SELECT fecha_actuacion, estado_tramite, fecha_estado_notificacion, tramite_homologado
                        FROM tramites_expediente 
                        WHERE radicado_completo = %s
                        ORDER BY fecha_actuacion DESC NULLS LAST
                        LIMIT 10
                    """, (expediente['radicado_completo'],))
                    
                    expediente['tramites_detallados'] = [
                        {
                            'fecha_actuacion': row[0],
                            'estado_tramite': row[1],
                            'auto': row[2],
                            'fecha_estado_notificacion': row[3],
                            'tramite_homologado': row[4]
                        }
                        for row in cursor.fetchall()
                    ]
                except Exception as e:
                    print(f"Error obteniendo trámites detallados para {expediente['radicado_completo']}: {e}")
                    expediente['tramites_detallados'] = []
                
                # Calcular estadísticas básicas con manejo de errores
                try:
                    # Primero verificar si existen trámites para este radicado
                    cursor.execute("""
                        SELECT COUNT(*) FROM tramites_expediente 
                        WHERE radicado_completo = %s
                    """, (expediente['radicado_completo'],))
                    
                    tramites_count = cursor.fetchone()
                    if tramites_count and tramites_count[0] > 0:
                        # Usar múltiples consultas separadas para evitar el error tuple index
                        try:
                            # Total de trámites
                            cursor.execute("SELECT COUNT(*) FROM tramites_expediente WHERE radicado_completo = %s", 
                                         (expediente['radicado_completo'],))
                            total = cursor.fetchone()[0]
                            
                            # Trámites finalizados
                            cursor.execute("""SELECT COUNT(*) FROM tramites_expediente 
                                           WHERE radicado_completo = %s 
                                           AND (estado_tramite LIKE %s OR estado_tramite LIKE %s)""", 
                                         (expediente['radicado_completo'], '%FINALIZADO%', '%COMPLETADO%'))
                            finalizados = cursor.fetchone()[0]
                            
                            # Trámites pendientes
                            cursor.execute("""SELECT COUNT(*) FROM tramites_expediente 
                                           WHERE radicado_completo = %s 
                                           AND (estado_tramite LIKE %s OR estado_tramite LIKE %s)""", 
                                         (expediente['radicado_completo'], '%PENDIENTE%', '%PROCESO%'))
                            pendientes = cursor.fetchone()[0]
                            
                            # Trámites sin trámite (NUEVO)
                            cursor.execute("""SELECT COUNT(*) FROM tramites_expediente 
                                           WHERE radicado_completo = %s 
                                           AND (estado_tramite LIKE %s OR estado_tramite LIKE %s OR estado_tramite LIKE %s OR estado_tramite IS NULL OR estado_tramite = '')""", 
                                         (expediente['radicado_completo'], '%SIN_TRAMITE%', '%SIN TRAMITE%', '%SIN INFORMACIÓN%'))
                            sin_tramite = cursor.fetchone()[0]
                            
                            expediente['estadisticas'] = {
                                'total_tramites_detalle': total or 0,
                                'tramites_finalizados': finalizados or 0,
                                'tramites_pendientes': pendientes or 0,
                                'tramites_sin_tramite': sin_tramite or 0
                            }
                        except Exception as e:
                            print(f"Error en consultas separadas para {expediente['radicado_completo']}: {e}")
                            expediente['estadisticas'] = {
                                'total_tramites_detalle': 0,
                                'tramites_finalizados': 0,
                                'tramites_pendientes': 0,
                                'tramites_sin_tramite': 0
                            }
                    else:
                        # No hay trámites para este radicado
                        expediente['estadisticas'] = {
                            'total_tramites_detalle': 0,
                            'tramites_finalizados': 0,
                            'tramites_pendientes': 0,
                            'tramites_sin_tramite': 0
                        }
                except Exception as e:
                    print(f"Error calculando estadísticas para {expediente['radicado_completo']}: {e}")
                    expediente['estadisticas'] = {
                        'total_tramites_detalle': 0,
                        'tramites_finalizados': 0,
                        'tramites_pendientes': 0,
                        'tramites_sin_tramite': 0
                    }
            else:
                # No hay radicado completo, no se pueden obtener trámites
                expediente['tramites_detallados'] = []
                expediente['estadisticas'] = {
                    'total_tramites_detalle': 0,
                    'tramites_finalizados': 0,
                    'tramites_pendientes': 0,
                    'tramites_sin_tramite': 0
                }
            
            expedientes_completos.append(expediente)
        
        cursor.close()
        conn.close()
        
        return expedientes_completos
        
    except Exception as e:
        print(f"Error en filtrar_por_estado: {e}")
        raise e

def buscar_expedientes(radicado):
    """Busca expedientes por radicado completo o corto con TODA la información relacionada"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Limpiar el radicado: eliminar espacios en blanco
        radicado_limpio = radicado.strip() if radicado else ''
        
        # Determinar si es búsqueda por radicado completo o corto
        es_radicado_completo = len(radicado_limpio) > 15  # Los radicados completos son largos
        
        # Primero obtener los expedientes básicos
        if es_radicado_completo:
            # Búsqueda de radicado completo: intentar exacto primero, luego sin espacios
            query_expedientes = """
                SELECT 
                    e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                    e.estado_actual, e.ubicacion_actual, e.tipo_solicitud, e.juzgado_origen, e.responsable,
                    e.fecha_ultima_actualizacion, e.fecha_creacion_registro, e.fecha_resolucion,
                    e.observaciones, e.total_tramites
                FROM expedientes e
                WHERE e.radicado_completo = %s
                   OR REPLACE(e.radicado_completo, ' ', '') = %s
                   OR e.radicado_completo LIKE %s
                ORDER BY e.radicado_completo
            """
            radicado_sin_espacios = radicado_limpio.replace(' ', '')
            cursor.execute(query_expedientes, (radicado_limpio, radicado_sin_espacios, f'%{radicado_limpio}%'))
        else:
            # Búsqueda de radicado corto o búsqueda parcial
            query_expedientes = """
                SELECT 
                    e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                    e.estado_actual, e.ubicacion_actual, e.tipo_solicitud, e.juzgado_origen, e.responsable,
                    e.fecha_ultima_actualizacion, e.fecha_creacion_registro, e.fecha_resolucion,
                    e.observaciones, e.total_tramites
                FROM expedientes e
                WHERE e.radicado_corto = %s OR e.radicado_completo LIKE %s
                ORDER BY e.radicado_completo NULLS LAST
            """
            cursor.execute(query_expedientes, (radicado_limpio, f'%{radicado_limpio}%'))
        
        expedientes_base = cursor.fetchall()
        
        if not expedientes_base:
            return []
        
        # Procesar cada expediente y obtener toda su información relacionada
        expedientes_completos = []
        
        for exp_row in expedientes_base:
            exp_id = exp_row[0]
            
            expediente = {
                'id': exp_row[0],
                'radicado_completo': exp_row[1],
                'radicado_corto': exp_row[2],
                'demandante': exp_row[3],
                'demandado': exp_row[4],
                'estado_actual': exp_row[5],
                'ubicacion_actual': exp_row[6],
                'tipo_solicitud': exp_row[7],
                'juzgado_origen': exp_row[8],
                'responsable': exp_row[9],
                'fecha_ultima_actualizacion': exp_row[10],
                'fecha_creacion_registro': exp_row[11],
                'fecha_resolucion': exp_row[12],
                'observaciones': exp_row[13],
                'total_tramites': exp_row[14],
                'estado_principal': None,  # Columna no existe
                'estado_adicional': None,  # Columna no existe  
                'fecha_ultima_actuacion_real': None,  # Columna no existe
                'ingresos': [],
                'estados': [],
                'tramites_detallados': [],
                'estadisticas': {}
            }
            
            # Obtener ingresos con manejo de errores
            try:
                cursor.execute("""
                    SELECT fecha_ingreso, motivo_ingreso, observaciones_ingreso, juzgado_origen
                    FROM ingresos_expediente 
                    WHERE expediente_id = %s
                    ORDER BY fecha_ingreso ASC
                """, (exp_id,))
                
                expediente['ingresos'] = [
                    {
                        'fecha_ingreso': row[0],
                        'motivo_ingreso': row[1],
                        'observaciones_ingreso': row[2],
                        'juzgado_origen': row[3]
                    }
                    for row in cursor.fetchall()
                ]
            except Exception as e:
                print(f"Error obteniendo ingresos para expediente {exp_id}: {e}")
                expediente['ingresos'] = []
            
            # Obtener estados con manejo de errores
            try:
                cursor.execute("""
                    SELECT fecha_estado, estado, observaciones, juzgado_origen
                    FROM estados_expediente 
                    WHERE expediente_id = %s
                    ORDER BY fecha_estado ASC
                """, (exp_id,))
                
                expediente['estados'] = [
                    {
                        'fecha_estado': row[0],
                        'estado_registrado': row[1],
                        'observaciones_estado': row[2],
                        'juzgado_origen': row[3]
                    }
                    for row in cursor.fetchall()
                ]
            except Exception as e:
                print(f"Error obteniendo estados para expediente {exp_id}: {e}")
                expediente['estados'] = []
            
            # Obtener trámites detallados si existen con manejo de errores
            if expediente['radicado_completo']:
                try:
                    cursor.execute("""
                        SELECT fecha_actuacion, estado_tramite, fecha_estado_notificacion, tramite_homologado
                        FROM tramites_expediente 
                        WHERE radicado_completo = %s
                        ORDER BY fecha_actuacion DESC NULLS LAST
                        LIMIT 20
                    """, (expediente['radicado_completo'],))
                    
                    expediente['tramites_detallados'] = [
                        {
                            'fecha_actuacion': row[0],
                            'estado_tramite': row[1],
                            'auto': row[2],
                            'fecha_estado_notificacion': row[3],
                            'tramite_homologado': row[4]
                        }
                        for row in cursor.fetchall()
                    ]
                except Exception as e:
                    print(f"Error obteniendo trámites detallados para {expediente['radicado_completo']}: {e}")
                    expediente['tramites_detallados'] = []
            
            # Calcular estadísticas del expediente con manejo de errores
            if expediente['radicado_completo']:
                try:
                    # Primero verificar si existen trámites para este radicado
                    cursor.execute("""
                        SELECT COUNT(*) FROM tramites_expediente 
                        WHERE radicado_completo = %s
                    """, (expediente['radicado_completo'],))
                    
                    tramites_count = cursor.fetchone()
                    if tramites_count and tramites_count[0] > 0:
                        # Usar múltiples consultas separadas para evitar el error tuple index
                        try:
                            # Total de trámites
                            cursor.execute("SELECT COUNT(*) FROM tramites_expediente WHERE radicado_completo = %s", 
                                         (expediente['radicado_completo'],))
                            total = cursor.fetchone()[0]
                            
                            # Trámites finalizados
                            cursor.execute("""SELECT COUNT(*) FROM tramites_expediente 
                                           WHERE radicado_completo = %s 
                                           AND (estado_tramite LIKE %s OR estado_tramite LIKE %s)""", 
                                         (expediente['radicado_completo'], '%FINALIZADO%', '%COMPLETADO%'))
                            finalizados = cursor.fetchone()[0]
                            
                            # Trámites pendientes
                            cursor.execute("""SELECT COUNT(*) FROM tramites_expediente 
                                           WHERE radicado_completo = %s 
                                           AND (estado_tramite LIKE %s OR estado_tramite LIKE %s)""", 
                                         (expediente['radicado_completo'], '%PENDIENTE%', '%PROCESO%'))
                            pendientes = cursor.fetchone()[0]
                            
                            # Trámites sin trámite (NUEVO)
                            cursor.execute("""SELECT COUNT(*) FROM tramites_expediente 
                                           WHERE radicado_completo = %s 
                                           AND (estado_tramite LIKE %s OR estado_tramite LIKE %s OR estado_tramite LIKE %s OR estado_tramite IS NULL OR estado_tramite = '')""", 
                                         (expediente['radicado_completo'], '%SIN_TRAMITE%', '%SIN TRAMITE%', '%SIN INFORMACIÓN%'))
                            sin_tramite = cursor.fetchone()[0]
                            
                            # Fechas (primera y última actuación)
                            cursor.execute("SELECT MIN(fecha_actuacion), MAX(fecha_actuacion) FROM tramites_expediente WHERE radicado_completo = %s", 
                                         (expediente['radicado_completo'],))
                            fechas = cursor.fetchone()
                            
                            expediente['estadisticas'] = {
                                'total_tramites_detalle': total or 0,
                                'tramites_finalizados': finalizados or 0,
                                'tramites_pendientes': pendientes or 0,
                                'tramites_sin_tramite': sin_tramite or 0,
                                'primera_actuacion': fechas[0] if fechas else None,
                                'ultima_actuacion': fechas[1] if fechas else None
                            }
                        except Exception as e:
                            print(f"Error en consultas separadas para {expediente['radicado_completo']}: {e}")
                            expediente['estadisticas'] = {
                                'total_tramites_detalle': 0,
                                'tramites_finalizados': 0,
                                'tramites_pendientes': 0,
                                'tramites_sin_tramite': 0,
                                'primera_actuacion': None,
                                'ultima_actuacion': None
                            }
                    else:
                        # No hay trámites para este radicado
                        expediente['estadisticas'] = {
                            'total_tramites_detalle': 0,
                            'tramites_finalizados': 0,
                            'tramites_pendientes': 0,
                            'tramites_sin_tramite': 0,
                            'primera_actuacion': None,
                            'ultima_actuacion': None
                        }
                except Exception as e:
                    print(f"Error calculando estadísticas para {expediente['radicado_completo']}: {e}")
                    expediente['estadisticas'] = {
                        'total_tramites_detalle': 0,
                        'tramites_finalizados': 0,
                        'tramites_pendientes': 0,
                        'tramites_sin_tramite': 0,
                        'primera_actuacion': None,
                        'ultima_actuacion': None
                    }
            else:
                expediente['estadisticas'] = {
                    'total_tramites_detalle': 0,
                    'tramites_finalizados': 0,
                    'tramites_pendientes': 0,
                    'tramites_sin_tramite': 0,
                    'primera_actuacion': None,
                    'ultima_actuacion': None
                }
            
            expedientes_completos.append(expediente)
        
        cursor.close()
        conn.close()
        
        return expedientes_completos
        
    except Exception as e:
        print(f"Error en buscar_expedientes: {e}")
        # Retornar lista vacía en caso de error para evitar que la aplicación se rompa
        return []