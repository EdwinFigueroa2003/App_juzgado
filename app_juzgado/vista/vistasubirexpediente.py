from flask import Blueprint, render_template, request, flash, redirect, url_for
import pandas as pd
import os, re
from werkzeug.utils import secure_filename
import sys
import logging
from datetime import datetime

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
            
            # Crear directorio de uploads si no existe
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            logger.info(f"Directorio de uploads verificado: {UPLOAD_FOLDER}")
            
            # Guardar archivo
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            logger.info(f"Guardando archivo en: {filepath}")
            file.save(filepath)
            
            # Procesar según el modo
            if modo_actualizacion:
                logger.info("Procesando archivo en MODO ACTUALIZACIÓN")
                resultados = procesar_excel_actualizacion(filepath)
            else:
                logger.info("Procesando archivo en MODO CREACIÓN")
                # Verificar si el archivo tiene múltiples pestañas (ingreso y estados)
                try:
                    excel_file = pd.ExcelFile(filepath)
                    hojas_disponibles = excel_file.sheet_names
                    logger.info(f"Hojas disponibles en el archivo: {hojas_disponibles}")
                    excel_file.close()
                    
                    # Verificar si tiene pestañas específicas para ingreso y estados
                    tiene_pestaña_ingreso = any(hoja.lower() in ['ingreso', 'ingresos'] for hoja in hojas_disponibles)
                    tiene_pestaña_estados = any(hoja.lower() in ['estado', 'estados'] for hoja in hojas_disponibles)
                    
                    if tiene_pestaña_ingreso and tiene_pestaña_estados:
                        logger.info("Detectado archivo Excel con pestañas múltiples (ingreso y estados)")
                        resultados = procesar_excel_multiples_pestañas(filepath, hojas_disponibles)
                    else:
                        logger.info("Procesando archivo Excel con formato tradicional")
                        resultados = procesar_excel_expedientes(filepath)
                        
                except Exception as e:
                    logger.warning(f"Error verificando estructura del Excel: {e}")
                    logger.info("Procesando como archivo Excel tradicional")
                    resultados = procesar_excel_expedientes(filepath)
            
            logger.info(f"Resultados del procesamiento: {resultados}")
            
            # Eliminar archivo temporal con manejo de errores
            logger.info("Eliminando archivo temporal")
            try:
                os.remove(filepath)
                logger.info("Archivo temporal eliminado correctamente")
            except PermissionError:
                logger.warning(f"No se pudo eliminar el archivo temporal {filepath} - puede estar en uso")
                # Intentar eliminar después de un breve delay
                import time
                time.sleep(1)
                try:
                    os.remove(filepath)
                    logger.info("Archivo temporal eliminado en segundo intento")
                except:
                    logger.warning(f"Archivo temporal {filepath} no se pudo eliminar - se eliminará automáticamente")
            except Exception as e:
                logger.warning(f"Error eliminando archivo temporal: {str(e)}")
            
            # Crear mensaje de resultado más detallado
            if modo_actualizacion:
                # Mensaje para modo actualización
                mensaje_resultado = f'Archivo procesado en MODO ACTUALIZACIÓN. '
                mensaje_resultado += f'{resultados["actualizados"]} expedientes actualizados exitosamente'
                
                if resultados.get("no_encontrados", 0) > 0:
                    mensaje_resultado += f', {resultados["no_encontrados"]} radicados no encontrados'
                
                if resultados["errores"] > 0:
                    mensaje_resultado += f', {resultados["errores"]} errores'
                
                mensaje_resultado += f' de {resultados["total_filas"]} filas procesadas.'
                
                # Mostrar radicados no encontrados si existen
                if resultados.get("radicados_no_encontrados") and len(resultados["radicados_no_encontrados"]) > 0:
                    radicados_lista = ', '.join(resultados["radicados_no_encontrados"])
                    mensaje_resultado += f' Radicados NO encontrados: {radicados_lista}'
                    if resultados.get("no_encontrados", 0) > len(resultados["radicados_no_encontrados"]):
                        mensaje_resultado += f' (y {resultados["no_encontrados"] - len(resultados["radicados_no_encontrados"])} más)'
                
            elif 'hoja_usada' in resultados:
                # Formato tradicional
                mensaje_resultado = f'Archivo procesado usando hoja "{resultados["hoja_usada"]}". '
                mensaje_resultado += f'{resultados["procesados"]} expedientes agregados exitosamente'
                
                if resultados["errores"] > 0:
                    mensaje_resultado += f', {resultados["errores"]} filas omitidas por errores de validación'
                
                mensaje_resultado += f' de {resultados["total_filas"]} filas procesadas.'
                
                # Mostrar detalles de expedientes rechazados
                if resultados.get("rechazados_detalle"):
                    detalles = resultados["rechazados_detalle"]
                    
                    if detalles.get("duplicados"):
                        mensaje_resultado += f' DUPLICADOS ({len(detalles["duplicados"])}): {", ".join(detalles["duplicados"][:5])}'
                        if len(detalles["duplicados"]) > 5:
                            mensaje_resultado += f' (y {len(detalles["duplicados"]) - 5} más)'
                    
                    if detalles.get("radicado_invalido"):
                        mensaje_resultado += f' RADICADO INVÁLIDO ({len(detalles["radicado_invalido"])}): {", ".join(detalles["radicado_invalido"][:5])}'
                        if len(detalles["radicado_invalido"]) > 5:
                            mensaje_resultado += f' (y {len(detalles["radicado_invalido"]) - 5} más)'
                    
                    if detalles.get("campos_faltantes"):
                        mensaje_resultado += f' CAMPOS FALTANTES ({len(detalles["campos_faltantes"])}): {", ".join(detalles["campos_faltantes"][:5])}'
                        if len(detalles["campos_faltantes"]) > 5:
                            mensaje_resultado += f' (y {len(detalles["campos_faltantes"]) - 5} más)'
            else:
                # Formato múltiples pestañas
                mensaje_resultado = f'Archivo procesado con múltiples pestañas. '
                mensaje_resultado += f'{resultados["expedientes_procesados"]} expedientes procesados, '
                mensaje_resultado += f'{resultados["ingresos_procesados"]} ingresos agregados, '
                mensaje_resultado += f'{resultados["estados_procesados"]} estados agregados.'
                
                if resultados["errores"] > 0:
                    mensaje_resultado += f' {resultados["errores"]} errores encontrados.'
            
            flash(mensaje_resultado, 'success' if resultados["errores"] == 0 else 'warning')
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
                    flash(f'⚠️ El radicado {radicado_completo} ya existe en la base de datos. Demandante: {dem_ante}, Demandado: {dem_ado}', 'error.' 'Para realizar cambios al expediente escrito ir a "Actualizar expedientes".' )
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

def procesar_excel_actualizacion(filepath):
    """
    Procesa un archivo Excel para ACTUALIZAR expedientes existentes
    
    Busca expedientes por radicado_completo y actualiza sus campos.
    No crea expedientes nuevos.
    
    Args:
        filepath: Ruta del archivo Excel
        
    Returns:
        dict: Estadísticas del procesamiento (actualizados, no_encontrados, errores)
    """
    logger.info("=== INICIO procesar_excel_actualizacion ===")
    logger.info(f"Archivo a procesar: {filepath}")
    
    try:
        # Leer Excel - intentar diferentes nombres de hojas
        logger.info("Intentando leer archivo Excel...")
        
        try:
            excel_file = pd.ExcelFile(filepath)
            hojas_disponibles = excel_file.sheet_names
            logger.info(f"Hojas disponibles en el archivo: {hojas_disponibles}")
            excel_file.close()
        except Exception as e:
            logger.error(f"Error leyendo archivo Excel: {str(e)}")
            raise Exception(f"Error leyendo archivo Excel: {str(e)}")
        
        # Intentar diferentes nombres de hojas en orden de prioridad
        nombres_hojas_posibles = [
            "Resumen por Expediente",
            "Resumen",
            "Expedientes",
            "Actualizacion",
            "Actualización",
            "Hoja1",
            "Sheet1",
            hojas_disponibles[0] if hojas_disponibles else None
        ]
        
        df = None
        hoja_usada = None
        
        for nombre_hoja in nombres_hojas_posibles:
            if nombre_hoja and nombre_hoja in hojas_disponibles:
                try:
                    logger.info(f"Intentando leer hoja: '{nombre_hoja}'")
                    df = pd.read_excel(filepath, sheet_name=nombre_hoja)
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
        
        # Validar que tenga al menos la columna RADICADO COMPLETO
        columnas_radicado = ['radicado_completo', 'RadicadoUnicoLimpio', 'RADICADO COMPLETO', 'RADICADO_COMPLETO', 'Radicado Completo']
        radicado_encontrado = False
        col_radicado_usada = None
        
        for col_req in columnas_radicado:
            if col_req in df.columns:
                radicado_encontrado = True
                col_radicado_usada = col_req
                break
        
        if not radicado_encontrado:
            logger.error("No se encontró columna de RADICADO COMPLETO")
            raise Exception(f'El archivo Excel debe contener una columna de RADICADO COMPLETO. Columnas disponibles: {", ".join(df.columns)}')
        
        logger.info(f"✅ Columna de radicado encontrada: '{col_radicado_usada}'")
        
        conn = obtener_conexion()
        logger.info("Conexión a BD establecida para procesamiento de actualizaciones")
        cursor = conn.cursor()
        
        # Verificar estructura de la tabla
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'expediente'
        """)
        
        available_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Columnas disponibles en tabla expediente: {available_columns}")
        
        actualizados = 0
        no_encontrados = 0
        errores = 0
        radicados_no_encontrados = []
        
        logger.info("Iniciando procesamiento de actualizaciones fila por fila...")
        
        for index, row in df.iterrows():
            try:
                logger.debug(f"Procesando fila {index + 1}")
                
                # Obtener radicado completo
                radicado_completo = None
                if pd.notna(row.get(col_radicado_usada)):
                    radicado_completo = str(row.get(col_radicado_usada)).strip()
                
                if not radicado_completo:
                    logger.debug(f"  Saltando fila {index + 1} - sin radicado")
                    errores += 1
                    continue
                
                logger.debug(f"  Buscando expediente con radicado: '{radicado_completo}'")
                
                # Buscar si el expediente existe
                cursor.execute("""
                    SELECT id 
                    FROM expediente 
                    WHERE radicado_completo = %s
                """, (radicado_completo,))
                
                resultado = cursor.fetchone()
                
                if not resultado:
                    logger.debug(f"  ⚠️ Expediente NO encontrado: {radicado_completo}")
                    no_encontrados += 1
                    radicados_no_encontrados.append(radicado_completo)
                    continue
                
                expediente_id = resultado[0]
                logger.debug(f"  ✓ Expediente encontrado (ID: {expediente_id})")
                
                # Construir UPDATE dinámicamente con los campos disponibles
                campos_actualizar = []
                valores_actualizar = []
                
                # Mapear columnas del Excel a campos de la BD
                mapeo_columnas = {
                    'demandante': ['DEMANDANTE_HOMOLOGADO', 'DEMANDANTE', 'demandante', 'Demandante'],
                    'demandado': ['DEMANDADO_HOMOLOGADO', 'DEMANDADO', 'demandado', 'Demandado'],
                    'estado': ['ESTADO', 'estado', 'Estado', 'ESTADO_ACTUAL', 'estado_actual'],
                    'responsable': ['RESPONSABLE', 'responsable', 'Responsable'],
                    'observaciones': ['OBSERVACIONES', 'observaciones', 'Observaciones'],
                    'ubicacion': ['UBICACION', 'ubicacion', 'Ubicación', 'UBICACIÓN']
                }
                
                # Procesar cada campo actualizable
                for campo_bd, posibles_columnas in mapeo_columnas.items():
                    if campo_bd in available_columns:
                        for col_excel in posibles_columnas:
                            if col_excel in df.columns and pd.notna(row.get(col_excel)):
                                valor = str(row.get(col_excel)).strip()
                                if valor:  # Solo actualizar si no está vacío
                                    campos_actualizar.append(f"{campo_bd} = %s")
                                    valores_actualizar.append(valor)
                                    logger.debug(f"    Actualizando {campo_bd}: '{valor}'")
                                break
                
                # Procesar FECHA INGRESO si existe
                if 'fecha_ingreso' in available_columns:
                    for col_name in ['FECHA INGRESO', 'FECHA_INGRESO', 'fecha_ingreso', 'Fecha Ingreso']:
                        if col_name in df.columns and pd.notna(row.get(col_name)):
                            fecha_valor = row.get(col_name)
                            try:
                                from datetime import datetime
                                if isinstance(fecha_valor, str):
                                    for formato in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                                        try:
                                            fecha_ingreso = datetime.strptime(fecha_valor.strip(), formato).date()
                                            campos_actualizar.append("fecha_ingreso = %s")
                                            valores_actualizar.append(fecha_ingreso)
                                            logger.debug(f"    Actualizando fecha_ingreso: '{fecha_ingreso}'")
                                            break
                                        except ValueError:
                                            continue
                                else:
                                    campos_actualizar.append("fecha_ingreso = %s")
                                    valores_actualizar.append(fecha_valor)
                                    logger.debug(f"    Actualizando fecha_ingreso: '{fecha_valor}'")
                            except Exception as e:
                                logger.warning(f"Error procesando fecha en fila {index + 1}: {e}")
                            break
                
                # Si hay campos para actualizar, ejecutar UPDATE
                if campos_actualizar:
                    query = f"""
                        UPDATE expediente 
                        SET {', '.join(campos_actualizar)}
                        WHERE id = %s
                    """
                    valores_actualizar.append(expediente_id)
                    
                    logger.debug(f"  Ejecutando UPDATE con {len(campos_actualizar)} campo(s)")
                    cursor.execute(query, valores_actualizar)
                    
                    actualizados += 1
                    logger.debug(f"  ✅ Expediente {radicado_completo} actualizado exitosamente")
                else:
                    logger.debug(f"  ℹ️ No hay campos para actualizar en fila {index + 1}")
                    errores += 1
                
            except Exception as e:
                logger.error(f"Error procesando fila {index + 1}: {str(e)}")
                errores += 1
                continue
        
        # Commit de todas las actualizaciones
        conn.commit()
        logger.info(f"✅ Transacción confirmada - {actualizados} expedientes actualizados")
        
        cursor.close()
        conn.close()
        
        # Preparar resultados
        resultados = {
            'actualizados': actualizados,
            'no_encontrados': no_encontrados,
            'errores': errores,
            'total_filas': len(df),
            'hoja_usada': hoja_usada,
            'radicados_no_encontrados': radicados_no_encontrados[:10]  # Solo primeros 10
        }
        
        logger.info(f"=== FIN procesar_excel_actualizacion ===")
        logger.info(f"Resultados: {actualizados} actualizados, {no_encontrados} no encontrados, {errores} errores")
        
        return resultados
        
    except Exception as e:
        logger.error(f"ERROR en procesar_excel_actualizacion: {str(e)}")
        raise e

def procesar_excel_expedientes(filepath):
    """Procesa un archivo Excel con expedientes"""
    logger.info("=== INICIO procesar_excel_expedientes ===")
    logger.info(f"Archivo a procesar: {filepath}")
    
    try:
        # Leer Excel - intentar diferentes nombres de hojas
        logger.info("Intentando leer archivo Excel...")
        
        # Primero, obtener la lista de hojas disponibles
        try:
            excel_file = pd.ExcelFile(filepath)
            hojas_disponibles = excel_file.sheet_names
            logger.info(f"Hojas disponibles en el archivo: {hojas_disponibles}")
            excel_file.close()  # Cerrar el archivo para liberar recursos
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
                    df = pd.read_excel(filepath, sheet_name=nombre_hoja)
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
                
                # VALIDACIÓN DE DUPLICADOS: Verificar si el radicado_completo ya existe
                if radicado_completo:
                    cursor.execute("""
                        SELECT id 
                        FROM expediente 
                        WHERE radicado_completo = %s
                    """, (radicado_completo,))
                    
                    if cursor.fetchone():
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
        
        result = {
            'procesados': procesados,
            'errores': errores,
            'hoja_usada': hoja_usada,
            'total_filas': len(df),
            'rechazados_detalle': rechazados_detalle
        }
        
        logger.info(f"=== FIN procesar_excel_expedientes - Resultado: {result} ===")
        return result
        
    except Exception as e:
        logger.error(f"ERROR GENERAL en procesar_excel_expedientes: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        raise Exception(f"Error leyendo archivo Excel: {str(e)}")

def procesar_excel_multiples_pestañas(filepath, hojas_disponibles):
    """
    Procesa un archivo Excel con múltiples pestañas:
    - Pestaña 'ingreso': Información actual de expedientes
    - Pestaña 'estados': RADICADO COMPLETO, CLASE, DEMANDANTE, DEMANDADO, FECHA ESTADO, AUTO / ANOTACION
    """
    logger.info("=== INICIO procesar_excel_multiples_pestañas ===")
    logger.info(f"Archivo: {filepath}")
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
            'errores': 0
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
                df_ingresos = pd.read_excel(filepath, sheet_name=pestaña_ingreso)
                logger.info(f"Pestaña '{pestaña_ingreso}' leída: {len(df_ingresos)} filas, columnas: {list(df_ingresos.columns)}")
                
                # Procesar expedientes desde la pestaña de ingresos
                resultado_ingresos = procesar_pestaña_ingresos(df_ingresos, cursor, expediente_columns)
                resultados['expedientes_procesados'] += resultado_ingresos['procesados']
                resultados['ingresos_procesados'] += resultado_ingresos['ingresos_creados']
                resultados['errores'] += resultado_ingresos['errores']
                
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
                df_estados = pd.read_excel(filepath, sheet_name=pestaña_estados)
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
        'errores': 0
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
        
        # Procesar cada fila
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
                    logger.debug(f"Saltando fila {index + 1} - faltan datos requeridos")
                    resultado['errores'] += 1
                    continue
                
                # Validar radicado completo
                es_valido, mensaje_error = validar_radicado_completo(radicado_completo)
                if not es_valido:
                    logger.debug(f"Saltando fila {index + 1} - {mensaje_error}")
                    resultado['errores'] += 1
                    continue
                
                # Verificar si el expediente ya existe
                cursor.execute("""
                    SELECT id FROM expediente WHERE radicado_completo = %s
                """, (radicado_completo,))
                
                expediente_existente = cursor.fetchone()
                
                if expediente_existente:
                    expediente_id = expediente_existente[0]
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
                        resultado['procesados'] += 1
                        logger.debug(f"Expediente creado: {radicado_completo} (ID: {expediente_id})")
                    else:
                        resultado['errores'] += 1
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
                logger.error(f"Error procesando fila {index + 1} en pestaña ingresos: {row_error}")
                resultado['errores'] += 1
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