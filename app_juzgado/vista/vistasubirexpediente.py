from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, send_from_directory, Response, jsonify
import pandas as pd
import os, re
from werkzeug.utils import secure_filename
import sys
import logging
from datetime import datetime
from io import BytesIO

# Configurar logging específico para subirexpediente
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.auth import login_required

# Crear un Blueprint
vistasubirexpediente = Blueprint('idvistasubirexpediente', __name__, template_folder='templates')

# Configuración para subida de archivos
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validar_radicado_completo(radicado):
    """
    Valida que el radicado completo tenga exactamente 23 dígitos numéricos
    
    Args:
        radicado (str): El radicado a validar
        
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    if not radicado:
        return True, ""  # Radicado vacío es válido (puede usar radicado corto)
    
    radicado = str(radicado).strip()
    
    if not radicado.isdigit():
        return False, "El radicado completo debe contener solo números"
    
    if len(radicado) != 23:
        return False, f"El radicado completo debe tener exactamente 23 dígitos. El ingresado tiene {len(radicado)} dígitos"
    
    return True, ""

def obtener_roles_activos():
    """Obtiene la lista de roles disponibles"""
    logger.info("=== INICIO obtener_roles_activos ===")
    try:
        conn = obtener_conexion()
        logger.info("Conexión a BD establecida correctamente")
        cursor = conn.cursor()
        
        query = """
            SELECT id, nombre_rol 
            FROM roles 
            ORDER BY nombre_rol
        """
        logger.info(f"Ejecutando query: {query}")
        cursor.execute(query)
        
        roles = cursor.fetchall()
        logger.info(f"Roles obtenidos: {len(roles)} registros")
        for rol in roles:
            logger.debug(f"Rol encontrado: ID={rol[0]}, Nombre={rol[1]}")
        
        cursor.close()
        conn.close()
        logger.info("Conexión cerrada correctamente")
        
        result = [{'id': r[0], 'nombre_rol': r[1]} for r in roles]
        logger.info(f"=== FIN obtener_roles_activos - Retornando {len(result)} roles ===")
        return result
        
    except Exception as e:
        logger.error(f"ERROR en obtener_roles_activos: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        return []

@vistasubirexpediente.route('/subirexpediente', methods=['GET', 'POST'])
@login_required
def vista_subirexpediente():
    logger.info("=== INICIO vista_subirexpediente ===")
    logger.info(f"Método de request: {request.method}")
    
    if request.method == 'POST':
        logger.info("Procesando POST request")
        # Verificar si es subida de archivo o formulario manual
        if 'archivo_excel' in request.files:
            logger.info("Detectado archivo Excel en request")
            return procesar_archivo_excel()
        else:
            logger.info("Detectado formulario manual")
            return procesar_formulario_manual()
    
    logger.info("Procesando GET request - cargando formulario")
    # Obtener roles para el menú desplegable
    try:
        roles = obtener_roles_activos()
        logger.info(f"Roles obtenidos para template: {len(roles)}")
        logger.info("=== FIN vista_subirexpediente - Renderizando template ===")
        return render_template('subirexpediente.html', roles=roles)
    except Exception as e:
        logger.error(f"ERROR cargando template: {str(e)}")
        flash(f'Error cargando la página: {str(e)}', 'error')
        return redirect(url_for('idvistahome.home'))

@vistasubirexpediente.route('/listar_reportes')
@login_required
def listar_reportes():
    """
    Lista todos los reportes disponibles en la base de datos
    
    Returns:
        JSON con lista de reportes
    """
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Obtener reportes ordenados por fecha (más recientes primero)
        cursor.execute("""
            SELECT 
                id, 
                nombre_archivo, 
                tipo_reporte, 
                total_filas, 
                actualizados, 
                sin_cambios,
                no_encontrados,
                errores_validacion, 
                errores_tecnicos,
                fecha_generacion,
                usuario_id
            FROM reportes_actualizacion
            ORDER BY fecha_generacion DESC
            LIMIT 50
        """)
        
        reportes = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Formatear resultados
        reportes_lista = []
        for reporte in reportes:
            reportes_lista.append({
                'id': reporte[0],
                'nombre_archivo': reporte[1],
                'tipo_reporte': reporte[2],
                'total_filas': reporte[3],
                'actualizados': reporte[4],
                'sin_cambios': reporte[5],
                'no_encontrados': reporte[6],
                'errores_validacion': reporte[7],
                'errores_tecnicos': reporte[8],
                'fecha_generacion': reporte[9].strftime('%Y-%m-%d %H:%M:%S') if reporte[9] else None,
                'usuario_id': reporte[10]
            })
        
        from flask import jsonify
        return jsonify({'reportes': reportes_lista, 'total': len(reportes_lista)})
        
    except Exception as e:
        logger.error(f"Error listando reportes: {e}")
        from flask import jsonify
        return jsonify({'error': str(e)}), 500

@vistasubirexpediente.route('/descargar_reporte_bd/<int:reporte_id>')
@login_required
def descargar_reporte_bd(reporte_id):
    """
    Descarga un reporte desde la base de datos
    
    Args:
        reporte_id: ID del reporte en la tabla reportes_actualizacion
    """
    try:
        logger.info(f"Descargando reporte ID: {reporte_id}")
        
        # Obtener reporte de la base de datos
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nombre_archivo, contenido, tipo_reporte, fecha_generacion
            FROM reportes_actualizacion
            WHERE id = %s
        """, (reporte_id,))
        
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not resultado:
            logger.error(f"Reporte ID {reporte_id} no encontrado en BD")
            flash('Reporte no encontrado', 'error')
            return redirect(url_for('idvistasubirexpediente.vista_subirexpediente'))
        
        nombre_archivo, contenido, tipo_reporte, fecha_generacion = resultado
        
        logger.info(f"✅ Reporte encontrado: {nombre_archivo} (tipo: {tipo_reporte})")
        
        # Crear respuesta con el contenido del reporte
        response = Response(
            contenido,
            mimetype='text/plain; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{nombre_archivo}"'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error descargando reporte desde BD: {e}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'Error descargando reporte: {str(e)}', 'error')
        return redirect(url_for('idvistasubirexpediente.vista_subirexpediente'))

def limpiar_reportes_antiguos(dias=30):
    """
    Limpia reportes antiguos de la base de datos
    
    Args:
        dias: Número de días para considerar un reporte como antiguo (default: 30)
    
    Returns:
        int: Número de reportes eliminados
    """
    try:
        logger.info(f"🧹 Iniciando limpieza de reportes antiguos (>{dias} días)")
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Eliminar reportes más antiguos que X días
        cursor.execute("""
            DELETE FROM reportes_actualizacion
            WHERE fecha_generacion < NOW() - INTERVAL '%s days'
            RETURNING id
        """, (dias,))
        
        reportes_eliminados = cursor.fetchall()
        cantidad_eliminados = len(reportes_eliminados)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Limpieza completada: {cantidad_eliminados} reportes eliminados")
        
        return cantidad_eliminados
        
    except Exception as e:
        logger.error(f"❌ Error limpiando reportes antiguos: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return 0

def procesar_archivo_excel():
    """Procesa la subida de archivo Excel"""
    logger.info("=== INICIO procesar_archivo_excel ===")
    
    # Detectar si es modo actualización
    modo_actualizacion = request.form.get('modo_actualizacion') == 'true'
    logger.info(f"Modo de operación: {'ACTUALIZACIÓN' if modo_actualizacion else 'CREACIÓN'}")
    
    try:
        file = request.files['archivo_excel']
        logger.info(f"Archivo recibido: {file.filename}")
        
        if file.filename == '':
            logger.warning("No se seleccionó ningún archivo")
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            logger.info(f"Archivo válido: {file.filename}")
            
            # Leer archivo directamente desde memoria (sin guardarlo en disco)
            # Esto funciona tanto en local como en cloud (Railway, Heroku, etc.)
            logger.info("Leyendo archivo desde memoria")
            file_content = BytesIO(file.read())
            filename = secure_filename(file.filename)
            
            # Procesar según el modo
            if modo_actualizacion:
                logger.info("Procesando archivo en MODO ACTUALIZACIÓN")
                
                # Verificar si el archivo tiene múltiples pestañas (ingreso y estados)
                try:
                    with pd.ExcelFile(file_content) as excel_file:
                        hojas_disponibles = excel_file.sheet_names
                        logger.info(f"Hojas disponibles en el archivo: {hojas_disponibles}")
                    
                    # Resetear el puntero del BytesIO para poder leerlo nuevamente
                    file_content.seek(0)
                    
                    # Verificar si tiene pestañas específicas para ingreso y estados
                    tiene_pestaña_ingreso = any(hoja.lower() in ['ingreso', 'ingresos'] for hoja in hojas_disponibles)
                    tiene_pestaña_estados = any(hoja.lower() in ['estado', 'estados'] for hoja in hojas_disponibles)
                    
                    if tiene_pestaña_ingreso or tiene_pestaña_estados:
                        logger.info("Detectado archivo Excel con pestañas múltiples en modo ACTUALIZACIÓN")
                        resultados = procesar_excel_actualizacion_multiples_pestañas(file_content, hojas_disponibles)
                    else:
                        logger.info("Procesando archivo Excel con formato tradicional en modo ACTUALIZACIÓN")
                        resultados = procesar_excel_actualizacion(file_content)
                        
                except Exception as e:
                    logger.warning(f"Error verificando estructura del Excel: {e}")
                    logger.info("Procesando como archivo Excel tradicional en modo ACTUALIZACIÓN")
                    file_content.seek(0)
                    resultados = procesar_excel_actualizacion(file_content)
            else:
                logger.info("Procesando archivo en MODO CREACIÓN")
                # Verificar si el archivo tiene múltiples pestañas (ingreso y estados)
                try:
                    with pd.ExcelFile(file_content) as excel_file:
                        hojas_disponibles = excel_file.sheet_names
                        logger.info(f"Hojas disponibles en el archivo: {hojas_disponibles}")
                    
                    # Resetear el puntero del BytesIO
                    file_content.seek(0)
                    
                    # Verificar si tiene pestañas específicas para ingreso y estados
                    tiene_pestaña_ingreso = any(hoja.lower() in ['ingreso', 'ingresos'] for hoja in hojas_disponibles)
                    tiene_pestaña_estados = any(hoja.lower() in ['estado', 'estados'] for hoja in hojas_disponibles)
                    
                    if tiene_pestaña_ingreso and tiene_pestaña_estados:
                        logger.info("Detectado archivo Excel con pestañas múltiples (ingreso y estados)")
                        resultados = procesar_excel_multiples_pestañas(file_content, hojas_disponibles)
                    else:
                        logger.info("Procesando archivo Excel con formato tradicional")
                        resultados = procesar_excel_expedientes(file_content)
                        
                except Exception as e:
                    logger.warning(f"Error verificando estructura del Excel: {e}")
                    logger.info("Procesando como archivo Excel tradicional")
                    file_content.seek(0)
                    resultados = procesar_excel_expedientes(file_content)
            
            logger.info(f"Resultados del procesamiento: {resultados}")
            
            # Ya no es necesario eliminar archivo temporal porque se procesó desde memoria
            logger.info("Archivo procesado desde memoria - no hay archivos temporales que eliminar")
            
            # 🧹 LIMPIEZA AUTOMÁTICA: Eliminar reportes antiguos (>30 días)
            try:
                reportes_eliminados = limpiar_reportes_antiguos(dias=90)
                if reportes_eliminados > 0:
                    logger.info(f"🧹 Limpieza automática: {reportes_eliminados} reportes antiguos eliminados")
            except Exception as e:
                logger.warning(f"Error en limpieza automática de reportes: {e}")
            
            # Crear mensaje de resultado más detallado
            # Detectar tipo de resultado basado en las claves presentes
            if 'actualizados' in resultados:
                # Formato tradicional de actualización (hoja única)
                mensaje_resultado = f'Archivo procesado en MODO ACTUALIZACIÓN. '
                mensaje_resultado += f'{resultados["actualizados"]} expedientes actualizados exitosamente'
                
                if resultados.get("sin_cambios", 0) > 0:
                    mensaje_resultado += f', {resultados["sin_cambios"]} sin cambios (valores idénticos)'
                
                if resultados.get("no_encontrados", 0) > 0:
                    mensaje_resultado += f', {resultados["no_encontrados"]} radicados no encontrados'
                
                if resultados["errores"] > 0:
                    mensaje_resultado += f', {resultados["errores"]} errores'
                
                mensaje_resultado += f' de {resultados["total_filas"]} filas procesadas.'
                
                # Información sobre reporte de errores
                if resultados.get("tiene_errores") and resultados.get("reporte_path"):
                    reporte_filename = os.path.basename(resultados["reporte_path"])
                    mensaje_resultado += f' Se generó un reporte detallado de errores.'
                
                # Mostrar primeros errores detallados
                if resultados.get("errores_detallados") and len(resultados["errores_detallados"]) > 0:
                    flash(mensaje_resultado, 'warning' if resultados["errores"] > 0 else 'success')
                    
                    # Crear mensaje adicional con detalle de errores
                    errores_msg = "DETALLE DE ERRORES:\n"
                    for i, error in enumerate(resultados["errores_detallados"][:5], 1):  # Solo primeros 5
                        errores_msg += f"\n{i}. Fila {error['fila']}: {error['radicado']} - {error['motivo']}"
                    
                    if len(resultados["errores_detallados"]) > 5:
                        errores_msg += f"\n... y {len(resultados['errores_detallados']) - 5} errores más"
                    
                    flash(errores_msg, 'info')
                    
                    # Agregar mensaje con enlace de descarga
                    # Reporte guardado en BD - disponible en botón "Descargar Reportes de Errores"
                    if resultados.get("reporte_id"):
                        logger.info(f"Reporte guardado con ID: {resultados['reporte_id']}")
                else:
                    flash(mensaje_resultado, 'warning' if resultados["errores"] > 0 else 'success')
                
            elif 'expedientes_actualizados' in resultados or 'ingresos_agregados' in resultados:
                # Formato múltiples pestañas en modo actualización
                mensaje_resultado = f'Archivo procesado con múltiples pestañas en modo ACTUALIZACIÓN. '
                
                if 'ingresos_agregados' in resultados:
                    mensaje_resultado += f'{resultados["ingresos_agregados"]} ingresos agregados, '
                
                if 'estados_agregados' in resultados:
                    mensaje_resultado += f'{resultados["estados_agregados"]} estados agregados, '
                
                if resultados.get("errores", 0) > 0:
                    mensaje_resultado += f'{resultados["errores"]} errores encontrados'
                else:
                    mensaje_resultado += 'sin errores'
                
                mensaje_resultado += f' de {resultados.get("total_filas", 0)} filas procesadas.'
                
                flash(mensaje_resultado, 'success' if resultados.get("errores", 0) == 0 else 'warning')
                
                # Mostrar detalle de errores si existen
                if resultados.get("errores_detallados") and len(resultados["errores_detallados"]) > 0:
                    errores_msg = "DETALLE DE ERRORES:\n"
                    for i, error in enumerate(resultados["errores_detallados"][:5], 1):  # Solo primeros 5
                        errores_msg += f"\n{i}. Fila {error['fila']} (Hoja: {error.get('hoja', 'N/A')}): {error['radicado']} - {error['motivo']}"
                    
                    if len(resultados["errores_detallados"]) > 5:
                        errores_msg += f"\n... y {len(resultados['errores_detallados']) - 5} errores más"
                    
                    flash(errores_msg, 'info')
                
                # Reporte guardado en BD - disponible en botón "Descargar Reportes de Errores"
                if resultados.get("reporte_id"):
                    logger.info(f"Reporte guardado con ID: {resultados['reporte_id']}")
                
            elif 'hoja_usada' in resultados:
                # Formato tradicional - Excel Nuevos
                mensaje_resultado = f'Archivo procesado usando hoja "{resultados["hoja_usada"]}". '
                mensaje_resultado += f'{resultados["procesados"]} expedientes agregados exitosamente'
                
                if resultados["errores"] > 0:
                    mensaje_resultado += f', {resultados["errores"]} filas omitidas por errores de validación'
                
                mensaje_resultado += f' de {resultados["total_filas"]} filas procesadas.'
                
                # Mostrar mensaje principal
                flash(mensaje_resultado, 'success' if resultados["errores"] == 0 else 'warning')
                
                # Mostrar detalles de expedientes rechazados
                if resultados.get("rechazados_detalle"):
                    detalles = resultados["rechazados_detalle"]
                    
                    detalles_msg = "DETALLE DE RECHAZOS:\n"
                    
                    if detalles.get("duplicados"):
                        detalles_msg += f'\nDUPLICADOS ({len(detalles["duplicados"])}): {", ".join(detalles["duplicados"][:5])}'
                        if len(detalles["duplicados"]) > 5:
                            detalles_msg += f' (y {len(detalles["duplicados"]) - 5} más)'
                    
                    if detalles.get("radicado_invalido"):
                        detalles_msg += f'\nRADICADO INVÁLIDO ({len(detalles["radicado_invalido"])}): {", ".join(detalles["radicado_invalido"][:5])}'
                        if len(detalles["radicado_invalido"]) > 5:
                            detalles_msg += f' (y {len(detalles["radicado_invalido"]) - 5} más)'
                    
                    if detalles.get("campos_faltantes"):
                        detalles_msg += f'\nCAMPOS FALTANTES ({len(detalles["campos_faltantes"])}): {", ".join(detalles["campos_faltantes"][:5])}'
                        if len(detalles["campos_faltantes"]) > 5:
                            detalles_msg += f' (y {len(detalles["campos_faltantes"]) - 5} más)'
                    
                    flash(detalles_msg, 'info')
                
                # Reporte guardado en BD - disponible en botón "Descargar Reportes de Errores"
                if resultados.get("reporte_id"):
                    logger.info(f"Reporte guardado con ID: {resultados['reporte_id']}")
            else:
                # Formato múltiples pestañas (creación)
                mensaje_resultado = f'Archivo procesado con múltiples pestañas. '
                mensaje_resultado += f'{resultados["expedientes_procesados"]} expedientes procesados, '
                mensaje_resultado += f'{resultados["ingresos_procesados"]} ingresos agregados, '
                mensaje_resultado += f'{resultados["estados_procesados"]} estados agregados.'
                
                if resultados["errores"] > 0:
                    mensaje_resultado += f' {resultados["errores"]} errores encontrados.'
                
                flash(mensaje_resultado, 'success' if resultados["errores"] == 0 else 'warning')
                
                # Mostrar detalle de errores si existen
                if resultados.get("errores_detallados") and len(resultados["errores_detallados"]) > 0:
                    errores_msg = "DETALLE DE ERRORES:\n"
                    for i, error in enumerate(resultados["errores_detallados"][:5], 1):  # Solo primeros 5
                        errores_msg += f"\n{i}. Fila {error['fila']} (Hoja: {error.get('hoja', 'N/A')}): {error['radicado']} - {error['motivo']}"
                    
                    if len(resultados["errores_detallados"]) > 5:
                        errores_msg += f"\n... y {len(resultados['errores_detallados']) - 5} errores más"
                    
                    flash(errores_msg, 'info')
                
                # Reporte guardado en BD - disponible en botón "Descargar Reportes de Errores"
                if resultados.get("reporte_id"):
                    logger.info(f"Reporte guardado con ID: {resultados['reporte_id']}")
            
            logger.info("=== FIN procesar_archivo_excel - ÉXITO ===")
            return redirect(url_for('idvistasubirexpediente.vista_subirexpediente'))
            
        else:
            logger.warning(f"Tipo de archivo no permitido: {file.filename}")
            flash('Tipo de archivo no permitido. Use archivos .xlsx o .xls', 'error')
            return redirect(request.url)
            
    except Exception as e:
        logger.error(f"ERROR en procesar_archivo_excel: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        flash(f'Error procesando archivo: {str(e)}', 'error')
        return redirect(request.url)

def procesar_formulario_manual():
    """Procesa el formulario manual de expediente"""
    logger.info("=== INICIO procesar_formulario_manual ===")
    
    try:
        # Obtener datos del formulario
        radicado_completo = request.form.get('radicado_completo', '').strip()
        radicado_corto = request.form.get('radicado_corto', '').strip()
        demandante = request.form.get('demandante', '').strip()
        demandado = request.form.get('demandado', '').strip()
        estado_actual = request.form.get('estado_actual', '').strip()
        ubicacion = request.form.get('ubicacion', '').strip()
        tipo_solicitud = request.form.get('tipo_solicitud', '').strip()
        juzgado_origen = request.form.get('juzgado_origen', '').strip()
        responsable = request.form.get('responsable', '').strip()
        observaciones = request.form.get('observaciones', '').strip()
        
        # Nuevos campos para ingreso y estado
        fecha_ingreso = request.form.get('fecha_ingreso', '').strip()
        motivo_ingreso = request.form.get('motivo_ingreso', '').strip()
        observaciones_ingreso = request.form.get('observaciones_ingreso', '').strip()
        
        logger.info("Datos del formulario recibidos:")
        logger.info(f"  - radicado_completo: '{radicado_completo}'")
        logger.info(f"  - radicado_corto: '{radicado_corto}'")
        logger.info(f"  - demandante: '{demandante}'")
        logger.info(f"  - demandado: '{demandado}'")
        logger.info(f"  - estado_actual: '{estado_actual}'")
        logger.info(f"  - ubicacion: '{ubicacion}'")
        logger.info(f"  - tipo_solicitud: '{tipo_solicitud}'")
        logger.info(f"  - juzgado_origen: '{juzgado_origen}'")
        logger.info(f"  - responsable: '{responsable}'")
        logger.info(f"  - fecha_ingreso: '{fecha_ingreso}'")
        logger.info(f"  - motivo_ingreso: '{motivo_ingreso}'")
        
        # Validaciones básicas
        if not radicado_completo and not radicado_corto:
            logger.warning("Validación fallida: No se proporcionó ningún radicado")
            flash('Debe proporcionar al menos un radicado (completo o corto)', 'error')
            return redirect(request.url)
        
        # Validación específica del radicado completo (debe tener exactamente 23 dígitos)
        if radicado_completo:
            es_valido, mensaje_error = validar_radicado_completo(radicado_completo)
            if not es_valido:
                logger.warning(f"Validación fallida: {mensaje_error}")
                flash(mensaje_error, 'error')
                return redirect(request.url)
            
            logger.info(f"✅ Radicado completo válido: {radicado_completo} (23 dígitos)")
        
        # Validar campos requeridos
        if not demandante:
            logger.warning("Validación fallida: Demandante es requerido")
            flash('El demandante es un campo requerido', 'error')
            return redirect(request.url)
        
        if not demandado:
            logger.warning("Validación fallida: Demandado es requerido")
            flash('El demandado es un campo requerido', 'error')
            return redirect(request.url)
        
        logger.info("Validaciones básicas pasadas - iniciando inserción en BD")
        
        # Insertar en base de datos
        conn = obtener_conexion()
        logger.info("Conexión a BD establecida")
        cursor = conn.cursor()
        
        try:
            # VALIDACIÓN DE DUPLICADOS: Verificar si el radicado_completo ya existe
            if radicado_completo:
                cursor.execute("""
                    SELECT id, radicado_completo, demandante, demandado 
                    FROM expediente 
                    WHERE radicado_completo = %s
                """, (radicado_completo,))
                
                expediente_existente = cursor.fetchone()
                
                if expediente_existente:
                    exp_id, rad, dem_ante, dem_ado = expediente_existente
                    logger.warning(f"DUPLICADO DETECTADO: Radicado {radicado_completo} ya existe (ID: {exp_id})")
                    flash(f'⚠️ El radicado {radicado_completo} ya existe en la base de datos. Demandante: {dem_ante}, Demandado: {dem_ado}. Para realizar cambios al expediente ir a "Actualizar expedientes".', 'error')
                    cursor.close()
                    conn.close()
                    return redirect(request.url)
                else:
                    logger.info(f"✅ Radicado {radicado_completo} no existe - puede proceder con la inserción")
            
            # Verificar estructura actual de la tabla
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'expediente'
            """)
            
            available_columns = [row[0] for row in cursor.fetchall()]
            logger.info(f"Columnas disponibles en tabla expediente: {available_columns}")
            
            # Construir query dinámicamente basado en columnas disponibles
            base_columns = ['radicado_completo', 'radicado_corto', 'demandante', 'demandado', 'estado', 'responsable']
            optional_columns = ['ubicacion', 'tipo_solicitud', 'observaciones', 'fecha_ingreso']
            
            # Filtrar solo las columnas que existen en la tabla
            columns_to_insert = []
            values_to_insert = []
            placeholders = []
            
            # Columnas base (siempre intentar insertar)
            for col in base_columns:
                if col in available_columns:
                    columns_to_insert.append(col)
                    placeholders.append('%s')
                    
                    if col == 'radicado_completo':
                        values_to_insert.append(radicado_completo or None)
                    elif col == 'radicado_corto':
                        values_to_insert.append(radicado_corto or None)
                    elif col == 'demandante':
                        values_to_insert.append(demandante or None)
                    elif col == 'demandado':
                        values_to_insert.append(demandado or None)
                    elif col == 'estado':
                        values_to_insert.append(estado_actual or None)
                    elif col == 'responsable':
                        values_to_insert.append(responsable or None)
            
            # Columnas opcionales (solo si existen en la tabla)
            if 'ubicacion' in available_columns and ubicacion:
                columns_to_insert.append('ubicacion')
                placeholders.append('%s')
                values_to_insert.append(ubicacion)
            
            if 'tipo_solicitud' in available_columns and tipo_solicitud:
                columns_to_insert.append('tipo_solicitud')
                placeholders.append('%s')
                values_to_insert.append(tipo_solicitud)
            
            if 'observaciones' in available_columns and observaciones:
                columns_to_insert.append('observaciones')
                placeholders.append('%s')
                values_to_insert.append(observaciones)
            
            # Manejar fecha_ingreso si existe en la tabla
            if 'fecha_ingreso' in available_columns:
                from datetime import datetime, date
                
                if fecha_ingreso:
                    try:
                        fecha_ingreso_obj = datetime.strptime(fecha_ingreso, '%Y-%m-%d').date()
                        logger.info(f"Fecha de ingreso parseada: {fecha_ingreso_obj}")
                    except Exception as date_error:
                        logger.warning(f"Error parseando fecha '{fecha_ingreso}': {date_error}")
                        fecha_ingreso_obj = date.today()
                        logger.info(f"Usando fecha actual: {fecha_ingreso_obj}")
                else:
                    fecha_ingreso_obj = date.today()
                    logger.info(f"Usando fecha actual (no proporcionada): {fecha_ingreso_obj}")
                
                columns_to_insert.append('fecha_ingreso')
                placeholders.append('%s')
                values_to_insert.append(fecha_ingreso_obj)
            
            # Manejar juzgado_origen (puede ser integer en la BD)
            if 'juzgado_origen' in available_columns and juzgado_origen:
                columns_to_insert.append('juzgado_origen')
                placeholders.append('%s')
                
                # Intentar convertir a integer si es posible
                try:
                    juzgado_origen_int = int(juzgado_origen)
                    values_to_insert.append(juzgado_origen_int)
                    logger.info(f"juzgado_origen convertido a integer: {juzgado_origen_int}")
                except ValueError:
                    # Si no se puede convertir, usar como texto (si la columna lo permite)
                    values_to_insert.append(juzgado_origen)
                    logger.info(f"juzgado_origen usado como texto: {juzgado_origen}")
            
            # Construir y ejecutar query
            query = f"""
                INSERT INTO expediente 
                ({', '.join(columns_to_insert)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """
            
            logger.info(f"Query construido: {query}")
            logger.info(f"Valores: {values_to_insert}")
            
            cursor.execute(query, values_to_insert)
            expediente_id = cursor.fetchone()[0]
            logger.info(f"Expediente insertado con ID: {expediente_id}")
            
            # Intentar insertar en tablas relacionadas si existen
            try:
                # Verificar si existe tabla ingresos_expediente
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'ingresos_expediente'
                """)
                
                if cursor.fetchone():
                    logger.info("Tabla ingresos_expediente existe - insertando registro")
                    cursor.execute("""
                        INSERT INTO ingresos_expediente 
                        (expediente_id, fecha_ingreso, motivo_ingreso, observaciones_ingreso)
                        VALUES (%s, %s, %s, %s)
                    """, (expediente_id, fecha_ingreso_obj if 'fecha_ingreso_obj' in locals() else date.today(), 
                          motivo_ingreso or 'Ingreso manual del expediente',
                          observaciones_ingreso or observaciones or 'Expediente ingresado manualmente'))
                    logger.info("Registro de ingreso insertado")
                else:
                    logger.info("Tabla ingresos_expediente no existe - saltando inserción")
                
                # Verificar si existe tabla estados_expediente
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'estados_expediente'
                """)
                
                if cursor.fetchone() and estado_actual:
                    logger.info("Tabla estados_expediente existe - insertando estado inicial")
                    cursor.execute("""
                        INSERT INTO estados_expediente 
                        (expediente_id, estado, fecha_estado, observaciones)
                        VALUES (%s, %s, %s, %s)
                    """, (expediente_id, estado_actual, fecha_ingreso_obj if 'fecha_ingreso_obj' in locals() else date.today(), 
                          f'Estado inicial: {estado_actual}'))
                    logger.info("Estado inicial insertado")
                else:
                    logger.info("Tabla estados_expediente no existe o no se proporcionó estado - saltando inserción")
                    
            except Exception as related_error:
                logger.warning(f"Error insertando en tablas relacionadas (no crítico): {str(related_error)}")
            
            # Manejar asignación de turno si el estado es 'Activo Pendiente'
            if estado_actual == 'Activo Pendiente' and 'turno' in available_columns:
                logger.info("🎫 Expediente creado con estado 'Activo Pendiente' - asignando turno automáticamente")
                
                # Obtener el siguiente turno disponible
                cursor.execute("""
                    SELECT COALESCE(MAX(turno), 0) 
                    FROM expediente 
                    WHERE estado = 'Activo Pendiente' 
                      AND turno IS NOT NULL
                """)
                
                resultado = cursor.fetchone()
                ultimo_turno = resultado[0] if resultado and resultado[0] is not None else 0
                siguiente_turno = ultimo_turno + 1
                
                logger.info(f"📊 Último turno asignado: {ultimo_turno}, Siguiente turno: {siguiente_turno}")
                
                # Asignar turno al expediente recién creado
                cursor.execute("""
                    UPDATE expediente 
                    SET turno = %s 
                    WHERE id = %s
                """, (siguiente_turno, expediente_id))
                
                logger.info(f"✅ Turno {siguiente_turno} asignado exitosamente al expediente {expediente_id}")
                flash(f'Expediente creado exitosamente con ID: {expediente_id}. Turno asignado: {siguiente_turno}', 'success')
            else:
                if estado_actual != 'Activo Pendiente':
                    logger.info(f"ℹ️ No se asigna turno - Estado es '{estado_actual}' (solo se asigna para 'Activo Pendiente')")
                else:
                    logger.info("ℹ️ No se asigna turno - Columna 'turno' no existe en la tabla")
                
                flash(f'Expediente creado exitosamente con ID: {expediente_id}.', 'success')
            
            conn.commit()
            logger.info("Transacción confirmada (COMMIT)")
            logger.info("=== FIN procesar_formulario_manual - ÉXITO ===")
            return redirect(url_for('idvistasubirexpediente.vista_subirexpediente'))
            
        except Exception as db_error:
            conn.rollback()
            logger.error(f"ERROR en transacción BD - ROLLBACK ejecutado")
            logger.error(f"Error específico: {str(db_error)}")
            logger.error(f"Tipo de error: {type(db_error).__name__}")
            raise db_error
        finally:
            cursor.close()
            conn.close()
            logger.info("Conexión BD cerrada")
        
    except Exception as e:
        logger.error(f"ERROR GENERAL en procesar_formulario_manual: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        flash(f'Error creando expediente: {str(e)}', 'error')
        return redirect(request.url)

def procesar_excel_actualizacion(file_content):
    """
    Procesa un archivo Excel para ACTUALIZAR expedientes existentes

    Busca expedientes por radicado_completo y actualiza sus campos.
    No crea expedientes nuevos.

    Args:
        file_content: BytesIO object con el contenido del archivo Excel

    Returns:
        dict: Estadísticas del procesamiento (actualizados, no_encontrados, errores)
    """
    logger.info("=== INICIO procesar_excel_actualizacion ===")

    try:
        # Leer Excel - intentar diferentes nombres de hojas
        logger.info("Intentando leer archivo Excel...")

        try:
            file_content.seek(0)
            with pd.ExcelFile(file_content) as excel_file:
                hojas_disponibles = excel_file.sheet_names
                logger.info(f"Hojas disponibles en el archivo: {hojas_disponibles}")
        except Exception as e:
            logger.error(f"Error leyendo archivo Excel: {str(e)}")
            raise Exception(f"Error leyendo archivo Excel: {str(e)}")

        # Definir columnas posibles para radicado
        columnas_radicado = [
            "RADICADO MODIFICADO",
            'radicado_completo',
            'RadicadoUnicoLimpio',
            'RADICADO COMPLETO',
            'RADICADO_COMPLETO',
            'Radicado Completo',
            'RADICADO_MODIFICADO_OFI',
            'radicado',
            'Radicado'
        ]

        # Intentar diferentes nombres de hojas en orden de prioridad
        nombres_hojas_posibles = [
            "estados",
            "Estados",                  # Prioridad 6 - Común en actualizaciones
            "Estado",
            "Resumen por Expediente",  # Prioridad 1
            "Resumen",                  # Prioridad 2
            "Expedientes",              # Prioridad 3
            "Actualizacion",            # Prioridad 4
            "Actualización",            # Prioridad 5
            "Hoja1",                    # Prioridad 8
            "Sheet1",                   # Prioridad 9
            "dato",                     # Prioridad 10
            "HOJA1",                    # Prioridad 11
            "DATOS",                    # Prioridad 12
            "ESTADOS",                  # Prioridad 13
            "ESTADO"                    # Prioridad 14
        ]

        df = None
        hoja_usada = None
        col_radicado_usada = None

        # Primero, intentar con hojas prioritarias
        for nombre_hoja in nombres_hojas_posibles:
            if nombre_hoja in hojas_disponibles:
                try:
                    logger.info(f"Intentando leer hoja prioritaria: '{nombre_hoja}'")
                    file_content.seek(0)
                    df_temp = pd.read_excel(file_content, sheet_name=nombre_hoja)

                    # Verificar si tiene columna de radicado
                    for col_req in columnas_radicado:
                        if col_req in df_temp.columns:
                            df = df_temp
                            hoja_usada = nombre_hoja
                            col_radicado_usada = col_req
                            logger.info(f"✓ Hoja prioritaria '{nombre_hoja}' leída exitosamente con columna '{col_req}'")
                            break

                    if df is not None:
                        break
                except Exception as e:
                    logger.warning(f"Error leyendo hoja '{nombre_hoja}': {str(e)}")
                    continue

        # Si no encontró en hojas prioritarias, buscar en TODAS las hojas hasta encontrar una con RADICADO COMPLETO
        if df is None:
            logger.info("No se encontró en hojas prioritarias. Buscando en todas las hojas por columna RADICADO COMPLETO...")

            for nombre_hoja in hojas_disponibles:
                try:
                    logger.info(f"Intentando leer hoja: '{nombre_hoja}'")
                    file_content.seek(0)
                    df_temp = pd.read_excel(file_content, sheet_name=nombre_hoja)
                    logger.debug(f"  Columnas en hoja '{nombre_hoja}': {list(df_temp.columns)}")

                    # Verificar si tiene columna de radicado
                    for col_req in columnas_radicado:
                        if col_req in df_temp.columns:
                            df = df_temp
                            hoja_usada = nombre_hoja
                            col_radicado_usada = col_req
                            logger.info(f"✓ Hoja '{nombre_hoja}' tiene columna '{col_req}' - usando esta hoja")
                            break

                    if df is not None:
                        break
                except Exception as e:
                    logger.warning(f"Error leyendo hoja '{nombre_hoja}': {str(e)}")
                    continue

        if df is None:
            raise Exception(f"No se encontró ninguna hoja con columna de radicado. Hojas disponibles: {hojas_disponibles}")

        logger.info(f"Excel leído correctamente usando hoja '{hoja_usada}' con columna '{col_radicado_usada}'. Filas: {len(df)}, Columnas: {len(df.columns)}")
        logger.info(f"Columnas disponibles: {list(df.columns)}")

        # Continuar con el resto de la lógica de actualización...
        # (El resto del código permanece igual, solo cambia cómo se lee el archivo)

        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # 🚀 OPTIMIZACIÓN: Cargar todos los expedientes en memoria UNA SOLA VEZ
        logger.info("🚀 Cargando expedientes en memoria para búsqueda rápida...")
        
        # Extraer todos los radicados del Excel (normalizados)
        radicados_excel = []
        for index, row in df.iterrows():
            radicado = extraer_valor_flexible(row, df.columns, 
                ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio', 'RADICADO_MODIFICADO_OFI'])
            if radicado:
                radicado_normalizado = re.sub(r'[^0-9]', '', str(radicado).strip())
                if radicado_normalizado:
                    radicados_excel.append(radicado_normalizado)
        
        # Remover duplicados
        radicados_excel = list(set(radicados_excel))
        logger.info(f"📊 {len(radicados_excel)} radicados únicos a buscar")
        
        # UNA SOLA CONSULTA para todos los expedientes
        cursor.execute("""
            SELECT id, radicado_completo 
            FROM expediente 
            WHERE radicado_completo = ANY(%s)
        """, (radicados_excel,))
        
        # Crear diccionario en memoria: {radicado: expediente_id}
        expedientes_cache = {row[1]: row[0] for row in cursor.fetchall()}
        logger.info(f"✅ {len(expedientes_cache)} expedientes cargados en memoria")
        logger.info(f"⚡ Ahora procesando filas con búsqueda instantánea...")

        actualizados = 0
        no_encontrados = 0
        sin_cambios = 0
        errores = 0
        errores_detallados = []

        # Mapeo de columnas Excel a columnas BD
        mapeo_columnas = {
            'RADICADO COMPLETO': 'radicado_completo',
            'radicado_completo': 'radicado_completo',
            'RadicadoUnicoLimpio': 'radicado_completo',
            'RADICADO_MODIFICADO_OFI': 'radicado_completo',
            'DEMANDANTE': 'demandante',
            'DEMANDANTE_HOMOLOGADO': 'demandante',
            'DEMANDADO': 'demandado',
            'DEMANDADO_HOMOLOGADO': 'demandado',
            'CLASE': 'clase',
            'clase': 'clase',
            'FECHA INGRESO': 'fecha_ingreso',
            'fecha_ingreso': 'fecha_ingreso',
            'FECHA_INGRESO': 'fecha_ingreso',
            'FECHA ESTADO': 'fecha_estado',
            'fecha_estado': 'fecha_estado',
            'FECHA_ESTADO': 'fecha_estado',
            'SOLICITUD': 'solicitud',
            'solicitud': 'solicitud',
        }

        # Procesar cada fila
        for index, row in df.iterrows():
            try:
                # Extraer radicado
                radicado_completo = extraer_valor_flexible(row, df.columns,
                    ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio', 'RADICADO_MODIFICADO_OFI'])

                if not radicado_completo:
                    logger.debug(f"Fila {index + 2} sin radicado - saltando")
                    errores += 1
                    errores_detallados.append({
                        'fila': index + 2,
                        'radicado': 'N/A',
                        'motivo': 'Radicado vacío'
                    })
                    continue

                # Normalizar radicado
                radicado_completo = re.sub(r'[^0-9]', '', str(radicado_completo).strip())

                # 🚀 BÚSQUEDA EN MEMORIA (instantánea, sin query a BD)
                expediente_id = expedientes_cache.get(radicado_completo)

                if not expediente_id:
                    logger.debug(f"Expediente {radicado_completo} no encontrado")
                    no_encontrados += 1
                    errores_detallados.append({
                        'fila': index + 2,
                        'radicado': radicado_completo,
                        'motivo': 'Expediente no encontrado en BD'
                    })
                    continue

                # Construir UPDATE dinámico
                campos_actualizar = {}
                for col_excel, col_bd in mapeo_columnas.items():
                    if col_excel in df.columns:
                        valor = row[col_excel]
                        if pd.notna(valor) and valor != '':
                            # Convertir fechas si es necesario
                            if 'fecha' in col_bd.lower():
                                valor = extraer_fecha_flexible(row, df.columns, [col_excel])
                            campos_actualizar[col_bd] = valor

                if campos_actualizar:
                    # Construir query UPDATE
                    set_clause = ', '.join([f"{col} = %s" for col in campos_actualizar.keys()])
                    valores = list(campos_actualizar.values()) + [expediente_id]

                    query = f"UPDATE expediente SET {set_clause} WHERE id = %s"
                    cursor.execute(query, valores)

                    if cursor.rowcount > 0:
                        actualizados += 1
                        logger.debug(f"✅ Expediente {radicado_completo} actualizado")
                    else:
                        sin_cambios += 1
                else:
                    sin_cambios += 1

            except Exception as e:
                logger.error(f"❌ Error procesando fila {index + 2}: {e}")
                errores += 1
                errores_detallados.append({
                    'fila': index + 2,
                    'radicado': radicado_completo if 'radicado_completo' in locals() else 'N/A',
                    'motivo': f'Error técnico: {str(e)}'
                })
                continue

        conn.commit()
        cursor.close()
        conn.close()

        resultados = {
            'expedientes_actualizados': actualizados,
            'no_encontrados': no_encontrados,
            'sin_cambios': sin_cambios,
            'errores': errores,
            'total_filas': len(df),
            'errores_detallados': errores_detallados
        }

        logger.info(f"=== FIN procesar_excel_actualizacion ===")
        logger.info(f"Resultados: {resultados}")

        return resultados

    except Exception as e:
        logger.error(f"ERROR en procesar_excel_actualizacion: {str(e)}")
        raise e



def procesar_excel_actualizacion_multiples_pestañas(file_content, hojas_disponibles):
    """
    Procesa un archivo Excel con múltiples pestañas en MODO ACTUALIZACIÓN:
    - Pestaña 'ingreso': Actualiza información de expedientes y agrega nuevos ingresos
    - Pestaña 'estados': Agrega nuevos estados a expedientes existentes
    
    Usa transacciones individuales por fila para evitar que un error detenga todo el proceso.
    
    Args:
        file_content: BytesIO object con el contenido del archivo Excel
        hojas_disponibles: Lista de nombres de hojas disponibles
    """
    logger.info("=== INICIO procesar_excel_actualizacion_multiples_pestañas ===")
    logger.info(f"Hojas disponibles: {hojas_disponibles}")
    
    try:
        resultados = {
            'expedientes_actualizados': 0,
            'ingresos_agregados': 0,
            'estados_agregados': 0,
            'errores': 0,
            'total_filas': 0,
            'errores_detallados': [],
            'ingresos_exitosos': [],  # Lista para rastrear ingresos exitosos
            'estados_exitosos': []     # Lista para rastrear estados exitosos
        }
        
        # Procesar pestaña de ingresos (si existe)
        pestaña_ingreso = None
        for hoja in hojas_disponibles:
            if hoja.lower() in ['ingreso', 'ingresos', 'INGRESO', 'INGRESOS']:
                pestaña_ingreso = hoja
                break
        
        if pestaña_ingreso:
            logger.info(f"Procesando pestaña de ingresos: {pestaña_ingreso}")
            try:
                # Resetear puntero y leer desde BytesIO
                file_content.seek(0)
                with pd.ExcelFile(file_content) as excel_file:
                    df_ingresos = pd.read_excel(excel_file, sheet_name=pestaña_ingreso)
                logger.info(f"Pestaña '{pestaña_ingreso}' leída: {len(df_ingresos)} filas")
                resultados['total_filas'] += len(df_ingresos)
                
                # 🚀 OPTIMIZACIÓN: Cargar todos los expedientes en memoria UNA SOLA VEZ
                logger.info("🚀 Cargando expedientes en memoria para búsqueda rápida...")
                
                # Extraer todos los radicados del Excel (normalizados)
                radicados_excel = []
                for index, row in df_ingresos.iterrows():
                    radicado = extraer_valor_flexible(row, df_ingresos.columns, 
                        ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio', 'RADICADO_MODIFICADO_OFI'])
                    if radicado:
                        radicado_normalizado = re.sub(r'[^0-9]', '', str(radicado).strip())
                        if radicado_normalizado:
                            radicados_excel.append(radicado_normalizado)
                
                # Remover duplicados
                radicados_excel = list(set(radicados_excel))
                logger.info(f"📊 {len(radicados_excel)} radicados únicos a buscar")
                
                # UNA SOLA CONSULTA para todos los expedientes
                conn_cache = obtener_conexion()
                cursor_cache = conn_cache.cursor()
                
                cursor_cache.execute("""
                    SELECT id, radicado_completo 
                    FROM expediente 
                    WHERE radicado_completo = ANY(%s)
                """, (radicados_excel,))
                
                # Crear diccionario en memoria: {radicado: expediente_id}
                expedientes_cache = {row[1]: row[0] for row in cursor_cache.fetchall()}
                cursor_cache.close()
                conn_cache.close()
                
                logger.info(f"✅ {len(expedientes_cache)} expedientes cargados en memoria")
                logger.info(f"⚡ Ahora procesando filas con búsqueda instantánea...")
                
                # Usar UNA SOLA conexión para todas las filas
                conn_ingresos = obtener_conexion()
                cursor_ingresos = conn_ingresos.cursor()
                
                # Verificar si existe tabla ingresos (UNA SOLA VEZ)
                cursor_ingresos.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = 'ingresos'
                """)
                
                if not cursor_ingresos.fetchone():
                    logger.warning("Tabla 'ingresos' no existe en la BD")
                    resultados['errores'] += len(df_ingresos)
                    cursor_ingresos.close()
                    conn_ingresos.close()
                else:
                    # Caché en memoria para duplicados DENTRO DEL MISMO ARCHIVO
                    ingresos_insertados_cache = set()
                    
                    # Procesar cada fila de ingresos con búsqueda en memoria (RÁPIDO)
                    for index, row in df_ingresos.iterrows():
                        try:
                            
                            # Extraer radicado
                            radicado_completo = extraer_valor_flexible(row, df_ingresos.columns, 
                                ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio', 'RADICADO_MODIFICADO_OFI'])
                            
                            if not radicado_completo:
                                logger.debug(f"Fila {index + 2} sin radicado - saltando")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_ingreso,
                                    'radicado': 'N/A',
                                    'motivo': 'Radicado vacío'
                                })
                                continue
                            
                            # Normalizar radicado
                            radicado_completo = re.sub(r'[^0-9]', '', str(radicado_completo).strip())
                            
                            # 🚀 BÚSQUEDA EN MEMORIA (instantánea, sin query a BD)
                            expediente_id = expedientes_cache.get(radicado_completo)
                            
                            if not expediente_id:
                                logger.debug(f"Expediente {radicado_completo} no encontrado")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_ingreso,
                                    'radicado': radicado_completo,
                                    'motivo': 'Expediente no encontrado en BD'
                                })
                                continue
                            
                            # Extraer datos del ingreso
                            fecha_ingreso = extraer_fecha_flexible(row, df_ingresos.columns, 
                                ['FECHA INGRESO', 'fecha_ingreso', 'FECHA_INGRESO', 'Fecha Ingreso'])
                            solicitud = extraer_valor_flexible(row, df_ingresos.columns, 
                                ['SOLICITUD', 'solicitud', 'Solicitud', 'TIPO_SOLICITUD'])
                            observaciones = extraer_valor_flexible(row, df_ingresos.columns, 
                                ['OBSERVACIONES', 'observaciones', 'Observaciones'])
                            
                            if not fecha_ingreso:
                                logger.debug(f"Fila {index + 2}: Fecha de ingreso inválida")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_ingreso,
                                    'radicado': radicado_completo,
                                    'motivo': 'Fecha de ingreso inválida o vacía'
                                })
                                continue
                            
                            if not solicitud:
                                logger.debug(f"Fila {index + 2}: Solicitud vacía")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_ingreso,
                                    'radicado': radicado_completo,
                                    'motivo': 'Solicitud vacía'
                                })
                                continue
                            
                            # Estandarizar observaciones (usar NULL si está vacía)
                            obs_normalized = observaciones if observaciones and str(observaciones).strip() else None
                            
                            # Verificar duplicado en MEMORIA PRIMERO (dentro del mismo archivo)
                            cache_key = (expediente_id, fecha_ingreso, solicitud, obs_normalized)
                            if cache_key in ingresos_insertados_cache:
                                logger.debug(f"⚠️ Ingreso duplicado EN EL ARCHIVO para {radicado_completo} - saltando FILA (no se insertará)")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_ingreso,
                                    'radicado': radicado_completo,
                                    'motivo': 'Ingreso duplicado dentro del archivo (ya fue procesado)'
                                })
                                continue
                            
                            # Verificar si ya existe un ingreso IDÉNTICO en BD (uploads previos)
                            # IMPORTANTE: Validar con los MISMOS valores que se van a insertar
                            cursor_ingresos.execute("""
                                SELECT id FROM ingresos 
                                WHERE expediente_id = %s 
                                AND fecha_ingreso = %s 
                                AND solicitud = %s
                                AND (observaciones IS NULL AND %s IS NULL OR observaciones = %s)
                            """, (expediente_id, fecha_ingreso, solicitud, obs_normalized, obs_normalized))
                            
                            if cursor_ingresos.fetchone():
                                logger.debug(f"⚠️ Ingreso duplicado en BD para expediente {radicado_completo} - saltando FILA (no se insertará)")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_ingreso,
                                    'radicado': radicado_completo,
                                    'motivo': 'Ingreso duplicado (información idéntica ya existe en BD)'
                                })
                                continue
                            
                            # Insertar nuevo ingreso
                            cursor_ingresos.execute("""
                                INSERT INTO ingresos (expediente_id, fecha_ingreso, solicitud, observaciones)
                                VALUES (%s, %s, %s, %s)
                            """, (expediente_id, fecha_ingreso, solicitud, obs_normalized))
                            
                            conn_ingresos.commit()
                            ingresos_insertados_cache.add(cache_key)  # Agregar al caché
                            resultados['ingresos_agregados'] += 1
                            logger.debug(f"✅ Ingreso agregado para expediente {radicado_completo}")
                            
                            # Registrar ingreso exitoso para el reporte
                            resultados['ingresos_exitosos'].append({
                                'fila': index + 2,
                                'radicado': radicado_completo,
                                'fecha_ingreso': str(fecha_ingreso),
                                'solicitud': solicitud[:50] if solicitud and len(solicitud) > 50 else solicitud  # Limitar longitud
                            })
                            
                        except Exception as e:
                            logger.error(f"❌ Error procesando fila {index + 2} de ingresos: {e}")
                            resultados['errores'] += 1
                            resultados['errores_detallados'].append({
                                'fila': index + 2,
                                'hoja': pestaña_ingreso,
                                'radicado': radicado_completo if 'radicado_completo' in locals() else 'N/A',
                                'motivo': f'Error técnico: {str(e)}'
                            })
                            conn_ingresos.rollback()  # Revierte solo esta fila
                            continue
                    
                    # Cerrar conexión de ingresos al final (después de procesar TODAS las filas)
                    cursor_ingresos.close()
                    conn_ingresos.close()
                    logger.info(f"✅ Conexión de ingresos cerrada correctamente")
                
            except Exception as e:
                logger.error(f"Error procesando pestaña de ingresos: {e}")
                resultados['errores'] += 1
        
        # Procesar pestaña de estados (si existe)
        pestaña_estados = None
        for hoja in hojas_disponibles:
            if hoja.lower() in ['estado', 'estados', 'ESTADO', 'ESTADOS']:
                pestaña_estados = hoja
                break
        
        if pestaña_estados:
            logger.info(f"Procesando pestaña de estados: {pestaña_estados}")
            try:
                # Resetear puntero y leer desde BytesIO
                file_content.seek(0)
                with pd.ExcelFile(file_content) as excel_file:
                    df_estados = pd.read_excel(excel_file, sheet_name=pestaña_estados)
                logger.info(f"Pestaña '{pestaña_estados}' leída: {len(df_estados)} filas")
                resultados['total_filas'] += len(df_estados)
                
                # 🚀 OPTIMIZACIÓN: Cargar todos los expedientes en memoria UNA SOLA VEZ
                logger.info("🚀 Cargando expedientes en memoria para búsqueda rápida...")
                
                # Extraer todos los radicados del Excel (normalizados)
                radicados_excel_estados = []
                for index, row in df_estados.iterrows():
                    radicado = extraer_valor_flexible(row, df_estados.columns, 
                        ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio', 'RADICADO_MODIFICADO_OFI'])
                    if radicado:
                        radicado_normalizado = re.sub(r'[^0-9]', '', str(radicado).strip())
                        if radicado_normalizado:
                            radicados_excel_estados.append(radicado_normalizado)
                
                # Remover duplicados
                radicados_excel_estados = list(set(radicados_excel_estados))
                logger.info(f"📊 {len(radicados_excel_estados)} radicados únicos a buscar")
                
                # UNA SOLA CONSULTA para todos los expedientes
                conn_cache_estados = obtener_conexion()
                cursor_cache_estados = conn_cache_estados.cursor()
                
                cursor_cache_estados.execute("""
                    SELECT id, radicado_completo 
                    FROM expediente 
                    WHERE radicado_completo = ANY(%s)
                """, (radicados_excel_estados,))
                
                # Crear diccionario en memoria: {radicado: expediente_id}
                expedientes_cache_estados = {row[1]: row[0] for row in cursor_cache_estados.fetchall()}
                cursor_cache_estados.close()
                conn_cache_estados.close()
                
                logger.info(f"✅ {len(expedientes_cache_estados)} expedientes cargados en memoria")
                logger.info(f"⚡ Ahora procesando filas con búsqueda instantánea...")
                
                # Usar UNA SOLA conexión para todas las filas DE ESTADOS
                conn_estados = obtener_conexion()
                cursor_estados = conn_estados.cursor()
                
                # Verificar si existe tabla estados (UNA SOLA VEZ)
                cursor_estados.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = 'estados'
                """)
                
                if not cursor_estados.fetchone():
                    logger.warning("Tabla 'estados' no existe en la BD")
                    resultados['errores'] += len(df_estados)
                    cursor_estados.close()
                    conn_estados.close()
                else:
                    # Caché en memoria para duplicados DENTRO DEL MISMO ARCHIVO
                    estados_insertados_cache = set()
                    
                    # Procesar cada fila de estados con búsqueda en memoria (RÁPIDO)
                    for index, row in df_estados.iterrows():
                        try:
                            radicado_completo = extraer_valor_flexible(row, df_estados.columns, 
                                ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio', 'RADICADO_MODIFICADO_OFI'])
                        
                            if not radicado_completo:
                                logger.debug(f"Fila {index + 2} sin radicado - saltando")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_estados,
                                    'radicado': 'N/A',
                                    'motivo': 'Radicado vacío'
                                })
                                continue
                            
                            # Normalizar radicado
                            radicado_completo = re.sub(r'[^0-9]', '', str(radicado_completo).strip())
                            
                            # 🚀 BÚSQUEDA EN MEMORIA (instantánea, sin query a BD)
                            expediente_id = expedientes_cache_estados.get(radicado_completo)
                            
                            if not expediente_id:
                                logger.debug(f"Expediente {radicado_completo} no encontrado")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_estados,
                                    'radicado': radicado_completo,
                                    'motivo': 'Expediente no encontrado en BD'
                                })
                                continue
                            
                            # Extraer datos del estado
                            clase = extraer_valor_flexible(row, df_estados.columns, 
                                ['CLASE', 'clase', 'Clase', 'ESTADO_TRAMITE', 'Estado_Tramite'])
                            fecha_estado = extraer_fecha_flexible(row, df_estados.columns, 
                                ['FECHA ESTADO', 'fecha_estado', 'FECHA_ESTADO', 'Fecha Estado'])
                            auto_anotacion = extraer_valor_flexible(row, df_estados.columns, 
                                ['AUTO / ANOTACION', 'auto_anotacion', 'AUTO_ANOTACION', 'AUTO', 'ANOTACION'])
                            observaciones = extraer_valor_flexible(row, df_estados.columns, 
                                ['OBSERVACIONES', 'observaciones', 'Observaciones'])
                            
                            # Validar campos requeridos
                            if not clase:
                                logger.debug(f"Fila {index + 2}: Clase vacía")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_estados,
                                    'radicado': radicado_completo,
                                    'motivo': 'Clase vacía'
                                })
                                continue
                            
                            if not fecha_estado:
                                logger.debug(f"Fila {index + 2}: Fecha de estado inválida")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_estados,
                                    'radicado': radicado_completo,
                                    'motivo': 'Fecha de estado inválida o vacía'
                                })
                                continue
                            
                            if not auto_anotacion:
                                logger.debug(f"Fila {index + 2}: Auto/Anotación vacía")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_estados,
                                    'radicado': radicado_completo,
                                    'motivo': 'Auto/Anotación vacía'
                                })
                                continue
                            
                            # Verificar duplicado en MEMORIA PRIMERO (dentro del mismo archivo)
                            cache_key = (expediente_id, fecha_estado, clase, auto_anotacion)
                            if cache_key in estados_insertados_cache:
                                logger.debug(f"⚠️ Estado duplicado EN EL ARCHIVO para {radicado_completo} - saltando")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_estados,
                                    'radicado': radicado_completo,
                                    'motivo': 'Estado duplicado dentro del archivo (ya fue procesado)'
                                })
                                continue
                            
                            # Estandarizar observaciones para estados (usar NULL si está vacía)
                            obs_estado_normalized = observaciones if observaciones and str(observaciones).strip() else None
                            
                            # Verificar si ya existe un estado IDÉNTICO en BD (uploads previos)
                            # Esto evita duplicados exactos de información
                            cursor_estados.execute("""
                                SELECT id FROM estados 
                                WHERE expediente_id = %s 
                                AND fecha_estado = %s 
                                AND clase = %s
                                AND auto_anotacion = %s
                                AND (observaciones IS NULL AND %s IS NULL OR observaciones = %s)
                            """, (expediente_id, fecha_estado, clase, auto_anotacion, obs_estado_normalized, obs_estado_normalized))
                            
                            if cursor_estados.fetchone():
                                logger.debug(f"⚠️ Estado duplicado en BD para expediente {radicado_completo} - saltando FILA (no se insertará)")
                                resultados['errores'] += 1
                                resultados['errores_detallados'].append({
                                    'fila': index + 2,
                                    'hoja': pestaña_estados,
                                    'radicado': radicado_completo,
                                    'motivo': 'Estado duplicado (información idéntica ya existe en BD)'
                                })
                                continue
                            
                            # Insertar nuevo estado
                            cursor_estados.execute("""
                                INSERT INTO estados (expediente_id, clase, fecha_estado, auto_anotacion, observaciones)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (expediente_id, clase, fecha_estado, auto_anotacion, obs_estado_normalized))
                            
                            conn_estados.commit()
                            estados_insertados_cache.add(cache_key)  # Agregar al caché
                            resultados['estados_agregados'] += 1
                            logger.debug(f"✅ Estado agregado para expediente {radicado_completo}")
                            
                            # Registrar estado exitoso para el reporte
                            resultados['estados_exitosos'].append({
                                'fila': index + 2,
                                'radicado': radicado_completo,
                                'fecha_estado': str(fecha_estado),
                                'clase': clase[:50] if clase and len(clase) > 50 else clase,  # Limitar longitud
                                'auto_anotacion': auto_anotacion[:50] if auto_anotacion and len(auto_anotacion) > 50 else auto_anotacion
                            })
                            
                            # 🔄 ACTUALIZAR AUTOMÁTICAMENTE EL CAMPO 'estado' EN TABLA EXPEDIENTE
                            # Basado en la lógica de actualizar_estados_expedientes.py
                            try:
                                # Obtener última fecha de ingreso
                                cursor_estados.execute("""
                                    SELECT MAX(fecha_ingreso) 
                                    FROM ingresos 
                                    WHERE expediente_id = %s
                                """, (expediente_id,))
                                
                                result_ingreso = cursor_estados.fetchone()
                                ultima_fecha_ingreso = result_ingreso[0] if result_ingreso else None
                                
                                # Obtener última fecha de estado (incluyendo el que acabamos de insertar)
                                cursor_estados.execute("""
                                    SELECT MAX(fecha_estado) 
                                    FROM estados 
                                    WHERE expediente_id = %s
                                """, (expediente_id,))
                                
                                result_estado = cursor_estados.fetchone()
                                ultima_fecha_estado = result_estado[0] if result_estado else None
                                
                                # Calcular estado correcto
                                estado_nuevo = None
                                
                                if ultima_fecha_ingreso and ultima_fecha_estado:
                                    # Normalizar fechas para comparación
                                    from datetime import datetime, date
                                    
                                    if isinstance(ultima_fecha_ingreso, str):
                                        ultima_fecha_ingreso = datetime.strptime(ultima_fecha_ingreso, '%Y-%m-%d').date()
                                    elif isinstance(ultima_fecha_ingreso, datetime):
                                        ultima_fecha_ingreso = ultima_fecha_ingreso.date()
                                    
                                    if isinstance(ultima_fecha_estado, str):
                                        ultima_fecha_estado = datetime.strptime(ultima_fecha_estado, '%Y-%m-%d').date()
                                    elif isinstance(ultima_fecha_estado, datetime):
                                        ultima_fecha_estado = ultima_fecha_estado.date()
                                    
                                    if ultima_fecha_ingreso > ultima_fecha_estado:
                                        # Ingreso más reciente → Activo Pendiente
                                        estado_nuevo = "Activo Pendiente"
                                    else:
                                        # Estado más reciente → Verificar antigüedad
                                        dias_desde_ultimo_estado = (date.today() - ultima_fecha_estado).days
                                        
                                        if dias_desde_ultimo_estado <= 365:
                                            estado_nuevo = "Activo Resuelto"
                                        else:
                                            estado_nuevo = "Inactivo Resuelto"
                                
                                elif ultima_fecha_estado:
                                    # Solo hay estados → Verificar antigüedad
                                    from datetime import datetime, date
                                    
                                    if isinstance(ultima_fecha_estado, str):
                                        ultima_fecha_estado = datetime.strptime(ultima_fecha_estado, '%Y-%m-%d').date()
                                    elif isinstance(ultima_fecha_estado, datetime):
                                        ultima_fecha_estado = ultima_fecha_estado.date()
                                    
                                    dias_desde_ultimo_estado = (date.today() - ultima_fecha_estado).days
                                    
                                    if dias_desde_ultimo_estado <= 365:
                                        estado_nuevo = "Activo Resuelto"
                                    else:
                                        estado_nuevo = "Inactivo Resuelto"
                                
                                elif ultima_fecha_ingreso:
                                    # Solo hay ingresos → Activo Pendiente
                                    estado_nuevo = "Activo Pendiente"
                                
                                # Actualizar el campo estado en expediente
                                if estado_nuevo:
                                    cursor_estados.execute("""
                                        UPDATE expediente 
                                        SET estado = %s 
                                        WHERE id = %s
                                    """, (estado_nuevo, expediente_id))
                                    
                                    conn_estados.commit()
                                    logger.debug(f"🔄 Estado del expediente actualizado a: {estado_nuevo}")
                                    
                                    # 🎫 GESTIÓN DE TURNOS: Si el estado cambió a Resuelto, eliminar turno y recalcular
                                    if estado_nuevo in ["Activo Resuelto", "Inactivo Resuelto"]:
                                        try:
                                            # Verificar si el expediente tenía turno asignado
                                            cursor_estados.execute("""
                                                SELECT turno FROM expediente WHERE id = %s
                                            """, (expediente_id,))
                                            
                                            result_turno = cursor_estados.fetchone()
                                            turno_anterior = result_turno[0] if result_turno else None
                                            
                                            if turno_anterior:
                                                logger.debug(f"🎫 Expediente tenía turno {turno_anterior} - eliminando y recalculando")
                                                
                                                # 1. Eliminar turno del expediente resuelto
                                                cursor_estados.execute("""
                                                    UPDATE expediente 
                                                    SET turno = NULL 
                                                    WHERE id = %s
                                                """, (expediente_id,))
                                                
                                                # 2. Recalcular turnos de expedientes con estado "Activo Pendiente"
                                                # Obtener todos los expedientes con turno, ordenados por turno actual
                                                cursor_estados.execute("""
                                                    SELECT id, turno 
                                                    FROM expediente 
                                                    WHERE estado = 'Activo Pendiente' 
                                                      AND turno IS NOT NULL 
                                                    ORDER BY turno
                                                """)
                                                
                                                expedientes_con_turno = cursor_estados.fetchall()
                                                
                                                # Reasignar turnos secuencialmente (1, 2, 3, ...)
                                                for nuevo_turno, (exp_id, turno_viejo) in enumerate(expedientes_con_turno, start=1):
                                                    if turno_viejo != nuevo_turno:
                                                        cursor_estados.execute("""
                                                            UPDATE expediente 
                                                            SET turno = %s 
                                                            WHERE id = %s
                                                        """, (nuevo_turno, exp_id))
                                                
                                                conn_estados.commit()
                                                logger.debug(f"✅ Turnos recalculados: {len(expedientes_con_turno)} expedientes actualizados")
                                            else:
                                                logger.debug(f"ℹ️ Expediente no tenía turno asignado - no se requiere recálculo")
                                        
                                        except Exception as turno_error:
                                            logger.warning(f"⚠️ Error gestionando turnos para expediente {expediente_id}: {turno_error}")
                                            # No detener el proceso, el estado ya fue actualizado correctamente
                                
                            except Exception as update_error:
                                logger.warning(f"⚠️ Error actualizando estado del expediente {expediente_id}: {update_error}")
                                # No detener el proceso, el estado ya fue insertado correctamente
                            
                            
                        except Exception as e:
                            logger.error(f"❌ Error procesando fila {index + 2} de estados: {e}")
                            resultados['errores'] += 1
                            resultados['errores_detallados'].append({
                                'fila': index + 2,
                                'hoja': pestaña_estados,
                                'radicado': radicado_completo if 'radicado_completo' in locals() else 'N/A',
                                'motivo': f'Error técnico: {str(e)}'
                            })
                            conn_estados.rollback()  # Revierte solo esta fila
                            continue
                    
                    # Cerrar conexión de estados al final (después de procesar TODAS las filas)
                    cursor_estados.close()
                    conn_estados.close()
                    logger.info(f"✅ Conexión de estados cerrada correctamente")
                
            except Exception as e:
                logger.error(f"Error procesando pestaña de estados: {e}")
                resultados['errores'] += 1
        
        logger.info(f"=== FIN procesar_excel_actualizacion_multiples_pestañas ===")
        logger.info(f"Resultados: {resultados}")
        
        # 📊 GUARDAR REPORTE EN BASE DE DATOS si hay errores
        if resultados.get('errores_detallados') and len(resultados['errores_detallados']) > 0:
            try:
                logger.info("📝 Generando reporte de errores en BD...")
                
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Construir contenido del reporte
                contenido_reporte = "=" * 80 + "\n"
                contenido_reporte += "REPORTE DE ACTUALIZACIÓN - MÚLTIPLES PESTAÑAS\n"
                contenido_reporte += "=" * 80 + "\n\n"
                contenido_reporte += f"Fecha de procesamiento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                contenido_reporte += f"Total de filas procesadas: {resultados['total_filas']}\n"
                contenido_reporte += f"Ingresos agregados: {resultados['ingresos_agregados']}\n"
                contenido_reporte += f"Estados agregados: {resultados['estados_agregados']}\n"
                contenido_reporte += f"Total de errores: {resultados['errores']}\n\n"
                
                # SECCIÓN DE REGISTROS EXITOSOS
                if resultados.get('ingresos_exitosos') or resultados.get('estados_exitosos'):
                    contenido_reporte += "=" * 80 + "\n"
                    contenido_reporte += "REGISTROS PROCESADOS EXITOSAMENTE\n"
                    contenido_reporte += "=" * 80 + "\n\n"
                    
                    # Ingresos exitosos
                    if resultados.get('ingresos_exitosos'):
                        contenido_reporte += f"INGRESOS AGREGADOS ({len(resultados['ingresos_exitosos'])}):\n"
                        contenido_reporte += "-" * 80 + "\n"
                        for i, ingreso in enumerate(resultados['ingresos_exitosos'][:100], 1):  # Limitar a 100
                            contenido_reporte += f"{i}. Fila {ingreso['fila']} - Radicado: {ingreso['radicado']}\n"
                            contenido_reporte += f"   Fecha: {ingreso['fecha_ingreso']} | Solicitud: {ingreso['solicitud']}\n\n"
                        
                        if len(resultados['ingresos_exitosos']) > 100:
                            contenido_reporte += f"   ... y {len(resultados['ingresos_exitosos']) - 100} ingresos más\n\n"
                    
                    # Estados exitosos
                    if resultados.get('estados_exitosos'):
                        contenido_reporte += f"ESTADOS AGREGADOS ({len(resultados['estados_exitosos'])}):\n"
                        contenido_reporte += "-" * 80 + "\n"
                        for i, estado in enumerate(resultados['estados_exitosos'][:100], 1):  # Limitar a 100
                            contenido_reporte += f"{i}. Fila {estado['fila']} - Radicado: {estado['radicado']}\n"
                            contenido_reporte += f"   Fecha: {estado['fecha_estado']} | Clase: {estado['clase']}\n"
                            contenido_reporte += f"   Auto/Anotación: {estado['auto_anotacion']}\n\n"
                        
                        if len(resultados['estados_exitosos']) > 100:
                            contenido_reporte += f"   ... y {len(resultados['estados_exitosos']) - 100} estados más\n\n"
                
                # SECCIÓN DE ERRORES
                contenido_reporte += "=" * 80 + "\n"
                contenido_reporte += "DETALLE DE ERRORES\n"
                contenido_reporte += "=" * 80 + "\n\n"
                
                if resultados['errores_detallados']:
                    for i, error in enumerate(resultados['errores_detallados'], 1):
                        contenido_reporte += f"{i}. Fila {error['fila']} - Hoja: {error.get('hoja', 'N/A')}\n"
                        contenido_reporte += f"   Radicado: {error['radicado']}\n"
                        contenido_reporte += f"   Motivo: {error['motivo']}\n\n"
                else:
                    contenido_reporte += "No se encontraron errores.\n\n"
                
                contenido_reporte += "=" * 80 + "\n"
                
                # Obtener usuario_id de la sesión
                from flask import session
                usuario_id = session.get('usuario_id') if 'session' in dir() else None
                
                # Insertar reporte en la base de datos
                conn_reporte = obtener_conexion()
                cursor_reporte = conn_reporte.cursor()
                
                reporte_filename = f"reporte_actualizacion_multiples_{timestamp}.txt"
                
                cursor_reporte.execute("""
                    INSERT INTO reportes_actualizacion 
                    (nombre_archivo, contenido, tipo_reporte, total_filas, actualizados, 
                     sin_cambios, no_encontrados, errores_validacion, errores_tecnicos, usuario_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    reporte_filename,
                    contenido_reporte,
                    'actualizacion_multiples',
                    resultados['total_filas'],
                    resultados['ingresos_agregados'] + resultados['estados_agregados'],  # actualizados
                    0,  # sin_cambios
                    0,  # no_encontrados
                    resultados['errores'],  # errores_validacion
                    0,  # errores_tecnicos
                    usuario_id
                ))
                
                reporte_id = cursor_reporte.fetchone()[0]
                conn_reporte.commit()
                cursor_reporte.close()
                conn_reporte.close()
                
                logger.info(f"📊 Reporte de actualización guardado en BD con ID: {reporte_id}")
                
                # Agregar ID del reporte a los resultados
                resultados['reporte_id'] = reporte_id
                resultados['tiene_errores'] = True
                
            except Exception as e:
                logger.error(f"Error guardando reporte de actualización en BD: {e}")
        
        return resultados
        
    except Exception as e:
        logger.error(f"ERROR en procesar_excel_actualizacion_multiples_pestañas: {str(e)}")
        raise e

def procesar_excel_expedientes(file_content):
    """
    Procesa un archivo Excel con expedientes
    
    Args:
        file_content: BytesIO object con el contenido del archivo Excel
    """
    logger.info("=== INICIO procesar_excel_expedientes ===")
    
    try:
        # Leer Excel - intentar diferentes nombres de hojas
        logger.info("Intentando leer archivo Excel...")
        
        # Primero, obtener la lista de hojas disponibles
        try:
            file_content.seek(0)
            with pd.ExcelFile(file_content) as excel_file:
                hojas_disponibles = excel_file.sheet_names
                logger.info(f"Hojas disponibles en el archivo: {hojas_disponibles}")
        except Exception as e:
            logger.error(f"Error leyendo archivo Excel: {str(e)}")
            raise Exception(f"Error leyendo archivo Excel: {str(e)}")
        
        hoja_trimestre = next(
            (h for h in hojas_disponibles if re.match(r"^\d{4}-Q[1-4]$", h)),
            None
        )

        # Intentar diferentes nombres de hojas en orden de prioridad
        nombres_hojas_posibles = [
            "Resumen por Expediente",
            "Resumen",
            "Expedientes", 
            "Hoja1",
            "Sheet1",
            hoja_trimestre,
            hojas_disponibles[0] if hojas_disponibles else None  # Primera hoja como fallback
        ]
        
        df = None
        hoja_usada = None
        
        for nombre_hoja in nombres_hojas_posibles:
            if nombre_hoja and nombre_hoja in hojas_disponibles:
                try:
                    logger.info(f"Intentando leer hoja: '{nombre_hoja}'")
                    file_content.seek(0)
                    df = pd.read_excel(file_content, sheet_name=nombre_hoja)
                    hoja_usada = nombre_hoja
                    logger.info(f"✓ Hoja '{nombre_hoja}' leída exitosamente")
                    break
                except Exception as e:
                    logger.warning(f"Error leyendo hoja '{nombre_hoja}': {str(e)}")
                    continue
        
        if df is None:
            raise Exception(f"No se pudo leer ninguna hoja del archivo. Hojas disponibles: {hojas_disponibles}")
        
        logger.info(f"Excel leído correctamente usando hoja '{hoja_usada}'. Filas: {len(df)}, Columnas: {len(df.columns)}")
        logger.info(f"Columnas disponibles: {list(df.columns)}")
        
        # Verificar si tiene las columnas mínimas necesarias
        # Nuevos requisitos: RADICADO COMPLETO, DEMANDANTE, DEMANDADO, FECHA INGRESO, SOLICITUD
        
        # Validar RADICADO COMPLETO
        columnas_radicado = ['radicado_completo', 'radicado_corto', 'RadicadoUnicoLimpio', 'RadicadoUnicoCompleto', 'RADICADO COMPLETO', 'RADICADO_MODIFICADO_OFI']
        radicado_encontrado = False
        for col_req in columnas_radicado:
            if col_req in df.columns:
                radicado_encontrado = True
                break
        
        # Validar DEMANDANTE
        columnas_demandante = ['DEMANDANTE_HOMOLOGADO', 'DEMANDANTE', 'demandante', 'Demandante']
        demandante_encontrado = False
        for col_req in columnas_demandante:
            if col_req in df.columns:
                demandante_encontrado = True
                break
        
        # Validar DEMANDADO
        columnas_demandado = ['DEMANDADO_HOMOLOGADO', 'DEMANDADO', 'demandado', 'Demandado']
        demandado_encontrado = False
        for col_req in columnas_demandado:
            if col_req in df.columns:
                demandado_encontrado = True
                break
        
        # Validar FECHA INGRESO
        columnas_fecha = ['FECHA INGRESO', 'FECHA_INGRESO', 'fecha_ingreso', 'Fecha Ingreso', 'FECHA DE INGRESO']
        fecha_encontrada = False
        for col_req in columnas_fecha:
            if col_req in df.columns:
                fecha_encontrada = True
                break
        
        # Validar SOLICITUD
        columnas_solicitud = ['SOLICITUD', 'solicitud', 'Solicitud', 'TIPO_SOLICITUD', 'tipo_solicitud']
        solicitud_encontrada = False
        for col_req in columnas_solicitud:
            if col_req in df.columns:
                solicitud_encontrada = True
                break
        
        # Verificar que todas las columnas requeridas estén presentes
        columnas_faltantes = []
        if not radicado_encontrado:
            columnas_faltantes.append("RADICADO COMPLETO")
        if not demandante_encontrado:
            columnas_faltantes.append("DEMANDANTE")
        if not demandado_encontrado:
            columnas_faltantes.append("DEMANDADO")
        if not fecha_encontrada:
            columnas_faltantes.append("FECHA INGRESO")
        if not solicitud_encontrada:
            columnas_faltantes.append("SOLICITUD")
        
        if columnas_faltantes:
            logger.error(f"Faltan columnas requeridas: {columnas_faltantes}")
            flash(f'El archivo Excel debe contener las siguientes columnas requeridas: {", ".join(columnas_faltantes)}. Columnas disponibles: {", ".join(df.columns)}', 'error')
            return redirect(url_for('idvistasubirexpediente.vista_subirexpediente'))
        
        logger.info("✅ Todas las columnas requeridas están presentes")
        columnas_encontradas = ["Validación exitosa"]  # Para mantener compatibilidad con el código siguiente
        
        conn = obtener_conexion()
        logger.info("Conexión a BD establecida para procesamiento masivo")
        cursor = conn.cursor()
        
        # Verificar estructura de la tabla
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'expediente'
        """)
        
        available_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Columnas disponibles en tabla expediente: {available_columns}")
        
        # 🚀 OPTIMIZACIÓN: Cargar radicados existentes en memoria UNA SOLA VEZ
        logger.info("🚀 Cargando radicados existentes en memoria para verificación de duplicados...")
        cursor.execute("SELECT radicado_completo FROM expediente WHERE radicado_completo IS NOT NULL")
        radicados_existentes = set(row[0] for row in cursor.fetchall())
        logger.info(f"✅ {len(radicados_existentes)} radicados existentes cargados en memoria")
        logger.info(f"⚡ Verificación de duplicados será instantánea...")
        
        procesados = 0
        errores = 0
        
        # Tracking detallado de rechazados
        rechazados_detalle = {
            'duplicados': [],
            'radicado_invalido': [],
            'campos_faltantes': []
        }
        
        logger.info("Iniciando procesamiento fila por fila...")
        for index, row in df.iterrows():
            try:
                logger.debug(f"Procesando fila {index + 1}")
                
                # Mapear columnas del Excel de forma más flexible
                radicado_completo = None
                radicado_corto = None
                
                # Intentar diferentes nombres de columnas para radicado completo
                for col_name in ['RadicadoUnicoLimpio', 'RADICADO COMPLETO', 'radicado_completo', 'RADICADO_COMPLETO', 'Radicado Completo']:
                    if col_name in df.columns and pd.notna(row.get(col_name)):
                        radicado_completo = str(row.get(col_name)).strip()
                        break
                
                # Intentar diferentes nombres de columnas para radicado corto
                for col_name in ['RadicadoUnicoCompleto', 'RADICADO_MODIFICADO_OFI', 'radicado_corto', 'RADICADO_CORTO', 'Radicado Corto']:
                    if col_name in df.columns and pd.notna(row.get(col_name)):
                        radicado_corto = str(row.get(col_name)).strip()
                        break
                
                # Intentar diferentes nombres para demandante
                demandante = None
                for col_name in ['DEMANDANTE_HOMOLOGADO', 'DEMANDANTE', 'demandante', 'Demandante']:
                    if col_name in df.columns and pd.notna(row.get(col_name)):
                        demandante = str(row.get(col_name)).strip()
                        break
                
                # Intentar diferentes nombres para demandado
                demandado = None
                for col_name in ['DEMANDADO_HOMOLOGADO', 'DEMANDADO', 'demandado', 'Demandado']:
                    if col_name in df.columns and pd.notna(row.get(col_name)):
                        demandado = str(row.get(col_name)).strip()
                        break
                
                # Procesar FECHA INGRESO (requerida)
                fecha_ingreso = None
                for col_name in ['FECHA INGRESO', 'FECHA_INGRESO', 'fecha_ingreso', 'Fecha Ingreso', 'FECHA DE INGRESO']:
                    if col_name in df.columns and pd.notna(row.get(col_name)):
                        fecha_valor = row.get(col_name)
                        # Intentar convertir a fecha si es necesario
                        try:
                            if isinstance(fecha_valor, str):
                                # Intentar diferentes formatos de fecha
                                from datetime import datetime
                                for formato in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                                    try:
                                        fecha_ingreso = datetime.strptime(fecha_valor.strip(), formato).date()
                                        break
                                    except ValueError:
                                        continue
                            else:
                                # Si ya es un objeto datetime o date
                                fecha_ingreso = fecha_valor
                        except Exception as e:
                            logger.warning(f"Error procesando fecha en fila {index + 1}: {e}")
                        break
                
                # Procesar SOLICITUD (requerida)
                solicitud = None
                for col_name in ['SOLICITUD', 'solicitud', 'Solicitud', 'TIPO_SOLICITUD', 'tipo_solicitud']:
                    if col_name in df.columns and pd.notna(row.get(col_name)):
                        solicitud = str(row.get(col_name)).strip()
                        break
                
                logger.debug(f"  Radicado completo: '{radicado_completo}'")
                logger.debug(f"  Radicado corto: '{radicado_corto}'")
                logger.debug(f"  Demandante: '{demandante}'")
                logger.debug(f"  Demandado: '{demandado}'")
                logger.debug(f"  Fecha ingreso: '{fecha_ingreso}'")
                logger.debug(f"  Solicitud: '{solicitud}'")
                
                # Validar campos requeridos
                if not radicado_completo and not radicado_corto:
                    logger.debug(f"  Saltando fila {index + 1} - sin radicado")
                    rechazados_detalle['campos_faltantes'].append(f"Fila {index + 1}: Sin radicado")
                    errores += 1
                    continue
                
                # 🚀 VERIFICACIÓN DE DUPLICADOS EN MEMORIA (instantánea, sin query a BD)
                if radicado_completo:
                    if radicado_completo in radicados_existentes:
                        logger.debug(f"  Saltando fila {index + 1} - radicado duplicado: {radicado_completo}")
                        rechazados_detalle['duplicados'].append(radicado_completo)
                        errores += 1
                        continue
                
                # Validación específica del radicado completo (debe tener exactamente 23 dígitos)
                if radicado_completo:
                    es_valido, mensaje_error = validar_radicado_completo(radicado_completo)
                    if not es_valido:
                        logger.debug(f"  Saltando fila {index + 1} - {mensaje_error}")
                        rechazados_detalle['radicado_invalido'].append(f"{radicado_completo} ({len(radicado_completo)} dígitos)")
                        errores += 1
                        continue
                    
                    logger.debug(f"  ✅ Radicado completo válido: {radicado_completo} (23 dígitos)")
                
                if not demandante:
                    logger.debug(f"  Saltando fila {index + 1} - sin demandante")
                    rechazados_detalle['campos_faltantes'].append(f"Fila {index + 1}: Sin demandante")
                    errores += 1
                    continue
                
                if not demandado:
                    logger.debug(f"  Saltando fila {index + 1} - sin demandado")
                    rechazados_detalle['campos_faltantes'].append(f"Fila {index + 1}: Sin demandado")
                    errores += 1
                    continue
                
                if not fecha_ingreso:
                    logger.debug(f"  Saltando fila {index + 1} - sin fecha de ingreso")
                    rechazados_detalle['campos_faltantes'].append(f"Fila {index + 1}: Sin fecha de ingreso")
                    errores += 1
                    continue
                
                if not solicitud:
                    logger.debug(f"  Saltando fila {index + 1} - sin solicitud")
                    rechazados_detalle['campos_faltantes'].append(f"Fila {index + 1}: Sin solicitud")
                    errores += 1
                    continue
                
                # Construir query dinámicamente basado en columnas disponibles
                columns_to_insert = []
                values_to_insert = []
                placeholders = []
                
                # Columnas base requeridas (siempre insertar)
                base_data = {
                    'radicado_completo': radicado_completo,
                    'radicado_corto': radicado_corto,
                    'demandante': demandante,
                    'demandado': demandado,
                    'fecha_ingreso': fecha_ingreso
                }
                
                for col, value in base_data.items():
                    if col in available_columns and value:
                        columns_to_insert.append(col)
                        placeholders.append('%s')
                        values_to_insert.append(value)
                
                # Insertar solicitud en tipo_solicitud si existe esa columna
                if 'tipo_solicitud' in available_columns and solicitud:
                    columns_to_insert.append('tipo_solicitud')
                    placeholders.append('%s')
                    values_to_insert.append(solicitud)
                
                # Columnas opcionales con mapeo flexible (excluyendo tipo_solicitud que ya se procesó)
                optional_mappings = {
                    'estado': ['ESTADO_EXPEDIENTE', 'estado', 'ESTADO', 'Estado'],
                    'responsable': ['RESPONSABLE', 'responsable', 'Responsable'],
                    'ubicacion': ['UBICACION', 'ubicacion', 'Ubicacion'],
                    'observaciones': ['OBSERVACIONES', 'observaciones', 'Observaciones']
                }
                
                for db_col, excel_cols in optional_mappings.items():
                    if db_col in available_columns:
                        for excel_col in excel_cols:
                            if excel_col in df.columns and pd.notna(row.get(excel_col)):
                                value = str(row.get(excel_col)).strip()
                                if value:
                                    columns_to_insert.append(db_col)
                                    placeholders.append('%s')
                                    values_to_insert.append(value)
                                    break
                
                # Manejar juzgado_origen (puede ser integer en la BD)
                juzgado_origen_cols = ['JuzgadoOrigen', 'juzgado_origen', 'JUZGADO_ORIGEN', 'Juzgado Origen', 'J. ORIGEN']
                for col_name in juzgado_origen_cols:
                    if col_name in df.columns and pd.notna(row.get(col_name)) and 'juzgado_origen' in available_columns:
                        juzgado_value = str(row.get(col_name)).strip()
                        if juzgado_value:
                            columns_to_insert.append('juzgado_origen')
                            placeholders.append('%s')
                            
                            # Intentar convertir a integer si es posible
                            try:
                                juzgado_origen_int = int(juzgado_value)
                                values_to_insert.append(juzgado_origen_int)
                            except ValueError:
                                values_to_insert.append(juzgado_value)
                            break
                
                # Construir y ejecutar query
                if columns_to_insert:  # Solo insertar si hay columnas válidas
                    query = f"""
                        INSERT INTO expediente 
                        ({', '.join(columns_to_insert)})
                        VALUES ({', '.join(placeholders)})
                        RETURNING id
                    """
                    
                    logger.debug(f"  Ejecutando inserción con columnas: {columns_to_insert}")
                    cursor.execute(query, values_to_insert)
                    
                    # Obtener el ID del expediente insertado
                    expediente_id = cursor.fetchone()[0]
                    
                    # Manejar asignación de turno si el estado es 'Activo Pendiente'
                    estado_expediente = None
                    for i, col in enumerate(columns_to_insert):
                        if col == 'estado':
                            estado_expediente = values_to_insert[i]
                            break
                    
                    if estado_expediente == 'Activo Pendiente' and 'turno' in available_columns:
                        logger.debug(f"  🎫 Expediente {expediente_id} creado con estado 'Activo Pendiente' - asignando turno")
                        
                        # Obtener el siguiente turno disponible
                        cursor.execute("""
                            SELECT MAX(turno) 
                            FROM expediente 
                            WHERE estado = 'Activo Pendiente' AND turno IS NOT NULL
                        """)
                        
                        resultado = cursor.fetchone()
                        ultimo_turno = resultado[0] if resultado and resultado[0] is not None else 0
                        siguiente_turno = ultimo_turno + 1
                        
                        # Asignar turno al expediente recién creado
                        cursor.execute("""
                            UPDATE expediente 
                            SET turno = %s 
                            WHERE id = %s
                        """, (siguiente_turno, expediente_id))
                        
                        logger.debug(f"  ✅ Turno {siguiente_turno} asignado al expediente {expediente_id}")
                    
                    # 📥 INSERTAR AUTOMÁTICAMENTE EN TABLA INGRESOS
                    # Verificar si existe la tabla ingresos
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name = 'ingresos'
                    """)
                    
                    if cursor.fetchone():
                        logger.debug(f"  📥 Insertando ingreso automático para expediente {expediente_id}")
                        
                        # Preparar datos para inserción en ingresos
                        # fecha_ingreso ya está disponible de la fila del Excel
                        # solicitud ya está disponible de la fila del Excel
                        # observaciones ya está disponible de la fila del Excel (si existe)
                        
                        # Extraer observaciones si no se hizo antes
                        observaciones_ingreso = None
                        for col_name in ['OBSERVACIONES', 'observaciones', 'Observaciones']:
                            if col_name in df.columns and pd.notna(row.get(col_name)):
                                observaciones_ingreso = str(row.get(col_name)).strip()
                                break
                        
                        # Si no hay observaciones, usar un valor por defecto
                        if not observaciones_ingreso:
                            observaciones_ingreso = 'Ingreso desde Excel - Carga masiva'
                        
                        try:
                            cursor.execute("""
                                INSERT INTO ingresos (expediente_id, fecha_ingreso, solicitud, observaciones)
                                VALUES (%s, %s, %s, %s)
                            """, (expediente_id, fecha_ingreso, solicitud, observaciones_ingreso))
                            
                            logger.debug(f"  ✅ Ingreso creado para expediente {expediente_id}")
                        except Exception as ingreso_error:
                            logger.warning(f"  ⚠️ Error insertando ingreso para expediente {expediente_id}: {ingreso_error}")
                            # No detener el proceso, solo registrar el error
                    else:
                        logger.debug(f"  ℹ️ Tabla 'ingresos' no existe - saltando inserción de ingreso")
                    
                    # 📤 INSERTAR AUTOMÁTICAMENTE EN TABLA ESTADOS (si hay estado)
                    if estado_expediente:
                        cursor.execute("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_name = 'estados'
                        """)
                        
                        if cursor.fetchone():
                            logger.debug(f"  📤 Insertando estado inicial para expediente {expediente_id}")
                            
                            try:
                                cursor.execute("""
                                    INSERT INTO estados (expediente_id, clase, fecha_estado, auto_anotacion, observaciones)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (
                                    expediente_id, 
                                    estado_expediente,  # clase = estado del expediente
                                    fecha_ingreso,  # fecha_estado = fecha de ingreso
                                    f'Estado inicial: {estado_expediente}',  # auto_anotacion
                                    'Estado inicial desde Excel - Carga masiva'  # observaciones
                                ))
                                
                                logger.debug(f"  ✅ Estado inicial creado para expediente {expediente_id}")
                            except Exception as estado_error:
                                logger.warning(f"  ⚠️ Error insertando estado para expediente {expediente_id}: {estado_error}")
                                # No detener el proceso, solo registrar el error
                        else:
                            logger.debug(f"  ℹ️ Tabla 'estados' no existe - saltando inserción de estado")
                    
                    # Agregar radicado al cache para evitar duplicados en el mismo archivo
                    if radicado_completo:
                        radicados_existentes.add(radicado_completo)
                    
                    procesados += 1
                    if procesados % 100 == 0:  # Log cada 100 registros procesados
                        logger.info(f"Procesados {procesados} expedientes...")
                else:
                    logger.debug(f"  Saltando fila {index + 1} - sin datos válidos para insertar")
                
            except Exception as row_error:
                errores += 1
                logger.error(f"Error procesando fila {index + 1}: {str(row_error)}")
                logger.error(f"Datos de la fila: {dict(row)}")
                continue
        
        conn.commit()
        logger.info("Transacción masiva confirmada (COMMIT)")
        
        cursor.close()
        conn.close()
        logger.info("Conexión cerrada")
        
        # 📊 GUARDAR REPORTE EN BASE DE DATOS si hay errores o expedientes procesados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reporte_id = None
        
        if errores > 0 or procesados > 0:
            try:
                # Reabrir conexión para guardar reporte
                conn = obtener_conexion()
                cursor = conn.cursor()
                
                # Construir contenido del reporte
                contenido_reporte = "=" * 80 + "\n"
                contenido_reporte += "REPORTE DE CARGA DE EXPEDIENTES NUEVOS\n"
                contenido_reporte += "=" * 80 + "\n"
                contenido_reporte += f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                contenido_reporte += f"Hoja utilizada: {hoja_usada}\n"
                contenido_reporte += "\n"
                contenido_reporte += "RESUMEN:\n"
                contenido_reporte += "-" * 80 + "\n"
                contenido_reporte += f"Total de filas procesadas: {len(df)}\n"
                contenido_reporte += f"Expedientes creados exitosamente: {procesados}\n"
                contenido_reporte += f"Expedientes rechazados: {errores}\n"
                contenido_reporte += "\n"
                
                # Detalle de rechazos
                if rechazados_detalle:
                    contenido_reporte += "DETALLE DE RECHAZOS:\n"
                    contenido_reporte += "=" * 80 + "\n"
                    
                    # Duplicados
                    if rechazados_detalle.get('duplicados'):
                        contenido_reporte += f"\nDUPLICADOS ({len(rechazados_detalle['duplicados'])}):\n"
                        contenido_reporte += "-" * 40 + "\n"
                        for i, radicado in enumerate(rechazados_detalle['duplicados'], 1):
                            contenido_reporte += f"{i}. {radicado}\n"
                    
                    # Radicados inválidos
                    if rechazados_detalle.get('radicado_invalido'):
                        contenido_reporte += f"\nRADICADO INVÁLIDO ({len(rechazados_detalle['radicado_invalido'])}):\n"
                        contenido_reporte += "-" * 40 + "\n"
                        for i, detalle in enumerate(rechazados_detalle['radicado_invalido'], 1):
                            contenido_reporte += f"{i}. {detalle}\n"
                    
                    # Campos faltantes
                    if rechazados_detalle.get('campos_faltantes'):
                        contenido_reporte += f"\nCAMPOS FALTANTES ({len(rechazados_detalle['campos_faltantes'])}):\n"
                        contenido_reporte += "-" * 40 + "\n"
                        for i, detalle in enumerate(rechazados_detalle['campos_faltantes'], 1):
                            contenido_reporte += f"{i}. {detalle}\n"
                
                contenido_reporte += "\n" + "=" * 80 + "\n"
                contenido_reporte += "FIN DEL REPORTE\n"
                contenido_reporte += "=" * 80 + "\n"
                
                # Obtener usuario_id de la sesión si está disponible
                from flask import session
                usuario_id = session.get('usuario_id') if 'session' in dir() else None
                
                # Calcular errores por tipo
                errores_duplicados = len(rechazados_detalle.get('duplicados', []))
                errores_radicado_invalido = len(rechazados_detalle.get('radicado_invalido', []))
                errores_campos_faltantes = len(rechazados_detalle.get('campos_faltantes', []))
                
                # Insertar reporte en la base de datos
                reporte_filename = f"reporte_carga_nuevos_{timestamp}.txt"
                
                cursor.execute("""
                    INSERT INTO reportes_actualizacion 
                    (nombre_archivo, contenido, tipo_reporte, total_filas, actualizados, 
                     sin_cambios, no_encontrados, errores_validacion, errores_tecnicos, usuario_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    reporte_filename,
                    contenido_reporte,
                    'carga_nuevos',
                    len(df),
                    procesados,  # actualizados = expedientes creados
                    0,  # sin_cambios (no aplica para carga nueva)
                    0,  # no_encontrados (no aplica para carga nueva)
                    errores_duplicados + errores_radicado_invalido + errores_campos_faltantes,  # errores_validacion
                    errores - (errores_duplicados + errores_radicado_invalido + errores_campos_faltantes),  # errores_tecnicos
                    usuario_id
                ))
                
                reporte_id = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(f"📊 Reporte de carga guardado en BD con ID: {reporte_id}")
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                logger.error(f"Error guardando reporte de carga en BD: {e}")
                if conn:
                    conn.rollback()
                    conn.close()
        
        result = {
            'procesados': procesados,
            'errores': errores,
            'hoja_usada': hoja_usada,
            'total_filas': len(df),
            'rechazados_detalle': rechazados_detalle,
            'reporte_id': reporte_id,
            'tiene_errores': errores > 0
        }
        
        logger.info(f"=== FIN procesar_excel_expedientes - Resultado: {result} ===")
        return result
        
    except Exception as e:
        logger.error(f"ERROR GENERAL en procesar_excel_expedientes: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        raise Exception(f"Error leyendo archivo Excel: {str(e)}")

def procesar_excel_multiples_pestañas(file_content, hojas_disponibles):
    """
    Procesa un archivo Excel con múltiples pestañas:
    - Pestaña 'ingreso': Información actual de expedientes
    - Pestaña 'estados': RADICADO COMPLETO, CLASE, DEMANDANTE, DEMANDADO, FECHA ESTADO, AUTO / ANOTACION
    
    Args:
        file_content: BytesIO object con el contenido del archivo Excel
        hojas_disponibles: Lista de nombres de hojas disponibles
    """
    logger.info("=== INICIO procesar_excel_multiples_pestañas ===")
    logger.info(f"Hojas disponibles: {hojas_disponibles}")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Verificar estructura de las tablas
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'expediente'
        """)
        expediente_columns = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('ingresos', 'estados')
        """)
        tablas_relacionadas = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Columnas en tabla expediente: {expediente_columns}")
        logger.info(f"Tablas relacionadas disponibles: {tablas_relacionadas}")
        
        resultados = {
            'expedientes_procesados': 0,
            'ingresos_procesados': 0,
            'estados_procesados': 0,
            'errores': 0,
            'errores_detallados': []  # Agregar lista consolidada de errores
        }
        
        # Procesar pestaña de ingresos
        pestaña_ingreso = None
        for hoja in hojas_disponibles:
            if hoja.lower() in ['ingreso', 'ingresos', 'INGRESO', 'INGRESOS']:
                pestaña_ingreso = hoja
                break
        
        if pestaña_ingreso:
            logger.info(f"Procesando pestaña de ingresos: {pestaña_ingreso}")
            try:
                # Usar context manager para asegurar cierre del archivo
                with pd.ExcelFile(filepath) as excel_file:
                    df_ingresos = pd.read_excel(excel_file, sheet_name=pestaña_ingreso)
                logger.info(f"Pestaña '{pestaña_ingreso}' leída: {len(df_ingresos)} filas, columnas: {list(df_ingresos.columns)}")
                
                # Procesar expedientes desde la pestaña de ingresos
                resultado_ingresos = procesar_pestaña_ingresos(df_ingresos, cursor, expediente_columns)
                resultados['expedientes_procesados'] += resultado_ingresos['procesados']
                resultados['ingresos_procesados'] += resultado_ingresos['ingresos_creados']
                resultados['errores'] += resultado_ingresos['errores']
                
                # Consolidar errores detallados
                if resultado_ingresos.get('errores_detallados'):
                    resultados['errores_detallados'].extend(resultado_ingresos['errores_detallados'])
                
            except Exception as e:
                logger.error(f"Error procesando pestaña de ingresos: {e}")
                resultados['errores'] += 1
        
        # Procesar pestaña de estados
        pestaña_estados = None
        for hoja in hojas_disponibles:
            if hoja.lower() in ['estado', 'estados', 'ESTADO', 'ESTADOS']:
                pestaña_estados = hoja
                break
        
        if pestaña_estados and 'estados' in tablas_relacionadas:
            logger.info(f"Procesando pestaña de estados: {pestaña_estados}")
            try:
                # Usar context manager para asegurar cierre del archivo
                with pd.ExcelFile(filepath) as excel_file:
                    df_estados = pd.read_excel(excel_file, sheet_name=pestaña_estados)
                logger.info(f"Pestaña '{pestaña_estados}' leída: {len(df_estados)} filas, columnas: {list(df_estados.columns)}")
                
                # Procesar estados
                resultado_estados = procesar_pestaña_estados(df_estados, cursor)
                resultados['estados_procesados'] += resultado_estados['procesados']
                resultados['errores'] += resultado_estados['errores']
                
            except Exception as e:
                logger.error(f"Error procesando pestaña de estados: {e}")
                resultados['errores'] += 1
        elif pestaña_estados and 'estados' not in tablas_relacionadas:
            logger.warning("Pestaña de estados encontrada pero tabla 'estados' no existe en la BD")
            resultados['errores'] += 1
        
        conn.commit()
        logger.info("Transacción confirmada (COMMIT)")
        
        cursor.close()
        conn.close()
        
        # 📊 GUARDAR REPORTE EN BASE DE DATOS si hay errores
        if resultados.get('errores_detallados') and len(resultados['errores_detallados']) > 0:
            try:
                logger.info("📝 Generando reporte de errores en BD...")
                
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Construir contenido del reporte
                contenido_reporte = "=" * 80 + "\n"
                contenido_reporte += "REPORTE DE CARGA NUEVA - MÚLTIPLES PESTAÑAS\n"
                contenido_reporte += "=" * 80 + "\n\n"
                contenido_reporte += f"Fecha de procesamiento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                contenido_reporte += f"Expedientes procesados: {resultados['expedientes_procesados']}\n"
                contenido_reporte += f"Ingresos procesados: {resultados['ingresos_procesados']}\n"
                contenido_reporte += f"Estados procesados: {resultados['estados_procesados']}\n"
                contenido_reporte += f"Total de errores: {resultados['errores']}\n\n"
                
                contenido_reporte += "=" * 80 + "\n"
                contenido_reporte += "DETALLE DE ERRORES\n"
                contenido_reporte += "=" * 80 + "\n\n"
                
                for i, error in enumerate(resultados['errores_detallados'], 1):
                    contenido_reporte += f"{i}. Fila {error['fila']} - Hoja: {error.get('hoja', 'N/A')}\n"
                    contenido_reporte += f"   Radicado: {error['radicado']}\n"
                    contenido_reporte += f"   Motivo: {error['motivo']}\n\n"
                
                contenido_reporte += "=" * 80 + "\n"
                
                # Obtener usuario_id de la sesión
                from flask import session
                usuario_id = session.get('usuario_id') if 'session' in dir() else None
                
                # Insertar reporte en la base de datos
                conn_reporte = obtener_conexion()
                cursor_reporte = conn_reporte.cursor()
                
                reporte_filename = f"reporte_carga_multiples_{timestamp}.txt"
                
                cursor_reporte.execute("""
                    INSERT INTO reportes_actualizacion 
                    (nombre_archivo, contenido, tipo_reporte, total_filas, actualizados, 
                     sin_cambios, no_encontrados, errores_validacion, errores_tecnicos, usuario_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    reporte_filename,
                    contenido_reporte,
                    'carga_multiples',
                    resultados['expedientes_procesados'] + resultados['errores'],  # total_filas
                    resultados['expedientes_procesados'],  # actualizados (expedientes creados)
                    0,  # sin_cambios
                    0,  # no_encontrados
                    resultados['errores'],  # errores_validacion
                    0,  # errores_tecnicos
                    usuario_id
                ))
                
                reporte_id = cursor_reporte.fetchone()[0]
                conn_reporte.commit()
                cursor_reporte.close()
                conn_reporte.close()
                
                logger.info(f"📊 Reporte de carga guardado en BD con ID: {reporte_id}")
                
                # Agregar ID del reporte a los resultados
                resultados['reporte_id'] = reporte_id
                resultados['tiene_errores'] = True
                
            except Exception as e:
                logger.error(f"Error guardando reporte de carga en BD: {e}")
        
        logger.info(f"=== FIN procesar_excel_multiples_pestañas - Resultado: {resultados} ===")
        return resultados
        
    except Exception as e:
        logger.error(f"ERROR GENERAL en procesar_excel_multiples_pestañas: {str(e)}")
        raise Exception(f"Error procesando archivo Excel con múltiples pestañas: {str(e)}")

def procesar_pestaña_ingresos(df, cursor, expediente_columns):
    """Procesa la pestaña de ingresos con información actual de expedientes"""
    logger.info("=== INICIO procesar_pestaña_ingresos ===")
    
    resultado = {
        'procesados': 0,
        'ingresos_creados': 0,
        'errores': 0,
        'errores_detallados': []  # Agregar lista de errores detallados
    }
    
    try:
        # Verificar columnas requeridas para ingresos
        columnas_requeridas = ['RADICADO COMPLETO', 'DEMANDANTE', 'DEMANDADO', 'FECHA INGRESO', 'SOLICITUD']
        columnas_faltantes = []
        
        for col_req in columnas_requeridas:
            encontrada = False
            for col_df in df.columns:
                if col_req.lower() in col_df.lower() or col_df.lower() in col_req.lower():
                    encontrada = True
                    break
            if not encontrada:
                columnas_faltantes.append(col_req)
        
        if columnas_faltantes:
            logger.error(f"Faltan columnas requeridas en pestaña ingresos: {columnas_faltantes}")
            resultado['errores'] = len(df)
            return resultado
        
        logger.info("✅ Todas las columnas requeridas están presentes en pestaña ingresos")
        
        # 🚀 OPTIMIZACIÓN: Cargar expedientes existentes en memoria UNA SOLA VEZ
        logger.info("🚀 Cargando expedientes existentes en memoria...")
        cursor.execute("SELECT id, radicado_completo FROM expediente WHERE radicado_completo IS NOT NULL")
        expedientes_cache = {row[1]: row[0] for row in cursor.fetchall()}
        logger.info(f"✅ {len(expedientes_cache)} expedientes cargados en memoria")
        
        # Procesar cada fila con búsqueda en memoria (RÁPIDO)
        for index, row in df.iterrows():
            try:
                # Extraer datos con mapeo flexible
                radicado_completo = extraer_valor_flexible(row, df.columns, ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio'])
                demandante = extraer_valor_flexible(row, df.columns, ['DEMANDANTE', 'demandante', 'DEMANDANTE_HOMOLOGADO'])
                demandado = extraer_valor_flexible(row, df.columns, ['DEMANDADO', 'demandado', 'DEMANDADO_HOMOLOGADO'])
                fecha_ingreso = extraer_fecha_flexible(row, df.columns, ['FECHA INGRESO', 'fecha_ingreso', 'FECHA_INGRESO'])
                solicitud = extraer_valor_flexible(row, df.columns, ['SOLICITUD', 'solicitud', 'TIPO_SOLICITUD'])
                
                # Validaciones básicas
                if not radicado_completo or not demandante or not demandado or not fecha_ingreso or not solicitud:
                    logger.debug(f"Saltando fila {index + 2} - faltan datos requeridos")
                    resultado['errores'] += 1
                    resultado['errores_detallados'].append({
                        'fila': index + 2,
                        'hoja': 'ingreso',
                        'radicado': radicado_completo or 'N/A',
                        'motivo': 'Faltan datos requeridos (demandante, demandado, fecha o solicitud)'
                    })
                    continue
                
                # Validar radicado completo
                es_valido, mensaje_error = validar_radicado_completo(radicado_completo)
                if not es_valido:
                    logger.debug(f"Saltando fila {index + 2} - {mensaje_error}")
                    resultado['errores'] += 1
                    resultado['errores_detallados'].append({
                        'fila': index + 2,
                        'hoja': 'ingreso',
                        'radicado': radicado_completo,
                        'motivo': mensaje_error
                    })
                    continue
                
                # 🚀 BÚSQUEDA EN MEMORIA (instantánea, sin query a BD)
                expediente_id = expedientes_cache.get(radicado_completo)
                
                if expediente_id:
                    logger.debug(f"Expediente {radicado_completo} ya existe (ID: {expediente_id})")
                else:
                    # Crear nuevo expediente
                    expediente_id = crear_expediente_desde_ingreso(cursor, expediente_columns, {
                        'radicado_completo': radicado_completo,
                        'demandante': demandante,
                        'demandado': demandado,
                        'fecha_ingreso': fecha_ingreso,
                        'tipo_solicitud': solicitud,
                        'estado': extraer_valor_flexible(row, df.columns, ['ESTADO', 'estado', 'ESTADO_EXPEDIENTE']),
                        'responsable': extraer_valor_flexible(row, df.columns, ['RESPONSABLE', 'responsable']),
                        'ubicacion': extraer_valor_flexible(row, df.columns, ['UBICACION', 'ubicacion']),
                        'observaciones': extraer_valor_flexible(row, df.columns, ['OBSERVACIONES', 'observaciones'])
                    })
                    
                    if expediente_id:
                        # Agregar al caché para evitar duplicados en el mismo archivo
                        expedientes_cache[radicado_completo] = expediente_id
                        resultado['procesados'] += 1
                        logger.debug(f"Expediente creado: {radicado_completo} (ID: {expediente_id})")
                    else:
                        resultado['errores'] += 1
                        resultado['errores_detallados'].append({
                            'fila': index + 2,
                            'hoja': 'ingreso',
                            'radicado': radicado_completo,
                            'motivo': 'Error al crear expediente en BD'
                        })
                        continue
                
                # Crear registro en tabla ingresos si existe
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables WHERE table_name = 'ingresos'
                """)
                
                if cursor.fetchone():
                    try:
                        cursor.execute("""
                            INSERT INTO ingresos (expediente_id, fecha_ingreso, solicitud, observaciones)
                            VALUES (%s, %s, %s, %s)
                        """, (expediente_id, fecha_ingreso, solicitud, 
                              extraer_valor_flexible(row, df.columns, ['OBSERVACIONES', 'observaciones']) or 'Ingreso desde Excel'))
                        
                        resultado['ingresos_creados'] += 1
                        logger.debug(f"Ingreso creado para expediente {expediente_id}")
                        
                    except Exception as ingreso_error:
                        logger.warning(f"Error creando ingreso para expediente {expediente_id}: {ingreso_error}")
                
            except Exception as row_error:
                logger.error(f"Error procesando fila {index + 2} en pestaña ingresos: {row_error}")
                resultado['errores'] += 1
                resultado['errores_detallados'].append({
                    'fila': index + 2,
                    'hoja': 'ingreso',
                    'radicado': radicado_completo if 'radicado_completo' in locals() else 'N/A',
                    'motivo': f'Error técnico: {str(row_error)}'
                })
                continue
        
        logger.info(f"=== FIN procesar_pestaña_ingresos - Resultado: {resultado} ===")
        return resultado
        
    except Exception as e:
        logger.error(f"ERROR en procesar_pestaña_ingresos: {str(e)}")
        resultado['errores'] = len(df)
        return resultado

def procesar_pestaña_estados(df, cursor):
    """
    Procesa la pestaña de estados con columnas requeridas:
    RADICADO COMPLETO, CLASE, FECHA ESTADO, AUTO / ANOTACION
    """
    logger.info("=== INICIO procesar_pestaña_estados ===")
    
    resultado = {
        'procesados': 0,
        'errores': 0
    }
    
    try:
        # Verificar columnas requeridas para estados (solo las esenciales)
        columnas_requeridas = ['RADICADO COMPLETO', 'CLASE', 'FECHA ESTADO', 'AUTO / ANOTACION']
        columnas_faltantes = []
        
        for col_req in columnas_requeridas:
            encontrada = False
            for col_df in df.columns:
                if col_req.lower().replace(' / ', '_').replace(' ', '_') in col_df.lower().replace(' / ', '_').replace(' ', '_'):
                    encontrada = True
                    break
            if not encontrada:
                columnas_faltantes.append(col_req)
        
        if columnas_faltantes:
            logger.error(f"Faltan columnas requeridas en pestaña estados: {columnas_faltantes}")
            resultado['errores'] = len(df)
            return resultado
        
        logger.info("✅ Todas las columnas requeridas están presentes en pestaña estados")
        
        # Procesar cada fila
        for index, row in df.iterrows():
            try:
                # Extraer datos con mapeo flexible (solo los requeridos)
                radicado_completo = extraer_valor_flexible(row, df.columns, ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio'])
                clase = extraer_valor_flexible(row, df.columns, ['CLASE', 'clase'])
                fecha_estado = extraer_fecha_flexible(row, df.columns, ['FECHA ESTADO', 'fecha_estado', 'FECHA_ESTADO'])
                auto_anotacion = extraer_valor_flexible(row, df.columns, ['AUTO / ANOTACION', 'auto_anotacion', 'AUTO_ANOTACION', 'AUTO', 'ANOTACION'])
                
                # Extraer datos opcionales para observaciones
                demandante = extraer_valor_flexible(row, df.columns, ['DEMANDANTE', 'demandante'])
                demandado = extraer_valor_flexible(row, df.columns, ['DEMANDADO', 'demandado'])
                observaciones = extraer_valor_flexible(row, df.columns, ['OBSERVACIONES', 'observaciones'])
                
                # Validaciones básicas (solo campos requeridos)
                if not radicado_completo or not clase or not fecha_estado or not auto_anotacion:
                    logger.debug(f"Saltando fila {index + 1} - faltan datos requeridos para estado (radicado: {radicado_completo}, clase: {clase}, fecha: {fecha_estado}, auto: {auto_anotacion})")
                    resultado['errores'] += 1
                    continue
                
                # Buscar el expediente por radicado completo
                cursor.execute("""
                    SELECT id FROM expediente WHERE radicado_completo = %s
                """, (radicado_completo,))
                
                expediente_existente = cursor.fetchone()
                
                if not expediente_existente:
                    logger.debug(f"Expediente {radicado_completo} no encontrado para crear estado")
                    resultado['errores'] += 1
                    continue
                
                expediente_id = expediente_existente[0]
                
                # Crear observaciones combinadas si hay demandante/demandado
                observaciones_finales = observaciones or ""
                if demandante or demandado:
                    info_adicional = f"Estado desde Excel"
                    if demandante:
                        info_adicional += f" - Demandante: {demandante}"
                    if demandado:
                        info_adicional += f" - Demandado: {demandado}"
                    
                    if observaciones_finales:
                        observaciones_finales = f"{observaciones_finales}. {info_adicional}"
                    else:
                        observaciones_finales = info_adicional
                
                # Crear registro en tabla estados
                try:
                    cursor.execute("""
                        INSERT INTO estados (expediente_id, clase, fecha_estado, auto_anotacion, observaciones)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (expediente_id, clase, fecha_estado, auto_anotacion, observaciones_finales))
                    
                    resultado['procesados'] += 1
                    logger.debug(f"Estado creado para expediente {radicado_completo} (ID: {expediente_id})")
                    
                except Exception as estado_error:
                    logger.error(f"Error creando estado para expediente {expediente_id}: {estado_error}")
                    resultado['errores'] += 1
                    continue
                
            except Exception as row_error:
                logger.error(f"Error procesando fila {index + 1} en pestaña estados: {row_error}")
                resultado['errores'] += 1
                continue
        
        logger.info(f"=== FIN procesar_pestaña_estados - Resultado: {resultado} ===")
        return resultado
        
    except Exception as e:
        logger.error(f"ERROR en procesar_pestaña_estados: {str(e)}")
        resultado['errores'] = len(df)
        return resultado

def extraer_valor_flexible(row, columnas_df, posibles_nombres):
    """Extrae un valor de una fila usando nombres de columnas flexibles"""
    for nombre in posibles_nombres:
        for col_df in columnas_df:
            if nombre.lower().replace(' ', '_') in col_df.lower().replace(' ', '_') or col_df.lower().replace(' ', '_') in nombre.lower().replace(' ', '_'):
                valor = row.get(col_df)
                if pd.notna(valor) and str(valor).strip():
                    return str(valor).strip()
    return None

def extraer_fecha_flexible(row, columnas_df, posibles_nombres):
    """Extrae una fecha de una fila usando nombres de columnas flexibles"""
    from datetime import datetime
    
    for nombre in posibles_nombres:
        for col_df in columnas_df:
            if nombre.lower().replace(' ', '_') in col_df.lower().replace(' ', '_') or col_df.lower().replace(' ', '_') in nombre.lower().replace(' ', '_'):
                fecha_valor = row.get(col_df)
                if pd.notna(fecha_valor):
                    try:
                        if isinstance(fecha_valor, str):
                            # Intentar diferentes formatos de fecha
                            for formato in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                                try:
                                    return datetime.strptime(fecha_valor.strip(), formato).date()
                                except ValueError:
                                    continue
                        else:
                            # Si ya es un objeto datetime o date
                            if hasattr(fecha_valor, 'date'):
                                return fecha_valor.date()
                            else:
                                return fecha_valor
                    except Exception:
                        continue
    return None

def crear_expediente_desde_ingreso(cursor, expediente_columns, datos):
    """Crea un nuevo expediente desde los datos de ingreso"""
    try:
        # Construir query dinámicamente basado en columnas disponibles
        columns_to_insert = []
        values_to_insert = []
        placeholders = []
        
        # Mapeo de datos a columnas de BD
        mapeo_columnas = {
            'radicado_completo': datos.get('radicado_completo'),
            'demandante': datos.get('demandante'),
            'demandado': datos.get('demandado'),
            'fecha_ingreso': datos.get('fecha_ingreso'),
            'tipo_solicitud': datos.get('tipo_solicitud'),
            'estado': datos.get('estado') or 'Activo Pendiente',  # Estado por defecto
            'responsable': datos.get('responsable'),
            'ubicacion': datos.get('ubicacion'),
            'observaciones': datos.get('observaciones')
        }
        
        for col, value in mapeo_columnas.items():
            if col in expediente_columns and value:
                columns_to_insert.append(col)
                placeholders.append('%s')
                values_to_insert.append(value)
        
        if not columns_to_insert:
            logger.error("No hay columnas válidas para insertar expediente")
            return None
        
        # Construir y ejecutar query
        query = f"""
            INSERT INTO expediente 
            ({', '.join(columns_to_insert)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """
        
        cursor.execute(query, values_to_insert)
        expediente_id = cursor.fetchone()[0]
        
        # Manejar asignación de turno si el estado es 'Activo Pendiente'
        if datos.get('estado') == 'Activo Pendiente' or (not datos.get('estado') and 'turno' in expediente_columns):
            # Obtener el siguiente turno disponible
            cursor.execute("""
                SELECT MAX(turno) 
                FROM expediente 
                WHERE estado = 'Activo Pendiente' AND turno IS NOT NULL
            """)
            
            resultado = cursor.fetchone()
            ultimo_turno = resultado[0] if resultado and resultado[0] is not None else 0
            siguiente_turno = ultimo_turno + 1
            
            # Asignar turno al expediente recién creado
            cursor.execute("""
                UPDATE expediente 
                SET turno = %s 
                WHERE id = %s
            """, (siguiente_turno, expediente_id))
            
            logger.debug(f"✅ Turno {siguiente_turno} asignado al expediente {expediente_id}")
        
        return expediente_id
        
    except Exception as e:
        logger.error(f"Error creando expediente desde ingreso: {str(e)}")
        return None