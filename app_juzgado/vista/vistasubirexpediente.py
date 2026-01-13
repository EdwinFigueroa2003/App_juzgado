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
            
            # Procesar Excel
            logger.info("Iniciando procesamiento de Excel")
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
            
            flash(f'Archivo procesado exitosamente usando hoja "{resultados["hoja_usada"]}". {resultados["procesados"]} expedientes agregados de {resultados["total_filas"]} filas procesadas.', 'success')
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
        
        logger.info("Validaciones básicas pasadas - iniciando inserción en BD")
        
        # Insertar en base de datos
        conn = obtener_conexion()
        logger.info("Conexión a BD establecida")
        cursor = conn.cursor()
        
        try:
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
            
            conn.commit()
            logger.info("Transacción confirmada (COMMIT)")
            
            flash(f'Expediente creado exitosamente con ID: {expediente_id}.', 'success')
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
        columnas_requeridas = ['radicado_completo', 'radicado_corto', 'RadicadoUnicoLimpio', 'RadicadoUnicoCompleto', 'RADICADO COMPLETO', 'RADICADO_MODIFICADO_OFI']
        columnas_encontradas = []
        
        for col_req in columnas_requeridas:
            if col_req in df.columns:
                columnas_encontradas.append(col_req)
        
        if not columnas_encontradas:
            logger.warning("No se encontraron columnas de radicado estándar, intentando detectar automáticamente...")
            # Buscar columnas que contengan "radicado" en el nombre
            columnas_radicado = [col for col in df.columns if 'radicado' in col.lower()]
            if columnas_radicado:
                logger.info(f"Columnas de radicado detectadas: {columnas_radicado}")
                columnas_encontradas = columnas_radicado
            else:
                logger.warning("No se encontraron columnas de radicado. Usando las primeras columnas disponibles.")
        
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
                
                logger.debug(f"  Radicado completo: '{radicado_completo}'")
                logger.debug(f"  Radicado corto: '{radicado_corto}'")
                logger.debug(f"  Demandante: '{demandante}'")
                logger.debug(f"  Demandado: '{demandado}'")
                
                if not radicado_completo and not radicado_corto:
                    logger.debug(f"  Saltando fila {index + 1} - sin radicado")
                    continue  # Saltar filas sin radicado
                
                # Construir query dinámicamente basado en columnas disponibles
                columns_to_insert = []
                values_to_insert = []
                placeholders = []
                
                # Columnas base (siempre intentar insertar)
                base_data = {
                    'radicado_completo': radicado_completo,
                    'radicado_corto': radicado_corto,
                    'demandante': demandante,
                    'demandado': demandado
                }
                
                for col, value in base_data.items():
                    if col in available_columns and value:
                        columns_to_insert.append(col)
                        placeholders.append('%s')
                        values_to_insert.append(value)
                
                # Columnas opcionales con mapeo flexible
                optional_mappings = {
                    'estado': ['ESTADO_EXPEDIENTE', 'estado', 'ESTADO', 'Estado'],
                    'responsable': ['RESPONSABLE', 'responsable', 'Responsable'],
                    'ubicacion': ['UBICACION', 'ubicacion', 'Ubicacion'],
                    'tipo_solicitud': ['SOLICITUD', 'tipo_solicitud', 'TIPO_SOLICITUD', 'Tipo Solicitud'],
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
                juzgado_origen_cols = ['JuzgadoOrigen', 'juzgado_origen', 'JUZGADO_ORIGEN', 'Juzgado Origen']
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
                
                # Manejar fecha_ingreso si existe en la tabla
                if 'fecha_ingreso' in available_columns:
                    from datetime import date
                    values_to_insert.append(date.today())
                    columns_to_insert.append('fecha_ingreso')
                    placeholders.append('%s')
                
                # Construir y ejecutar query
                if columns_to_insert:  # Solo insertar si hay columnas válidas
                    query = f"""
                        INSERT INTO expediente 
                        ({', '.join(columns_to_insert)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    logger.debug(f"  Ejecutando inserción con columnas: {columns_to_insert}")
                    cursor.execute(query, values_to_insert)
                    
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
            'total_filas': len(df)
        }
        
        logger.info(f"=== FIN procesar_excel_expedientes - Resultado: {result} ===")
        return result
        
    except Exception as e:
        logger.error(f"ERROR GENERAL en procesar_excel_expedientes: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        raise Exception(f"Error leyendo archivo Excel: {str(e)}")