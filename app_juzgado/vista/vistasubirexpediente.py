from flask import Blueprint, render_template, request, flash, redirect, url_for
import pandas as pd
import os
from werkzeug.utils import secure_filename
import sys

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

@vistasubirexpediente.route('/subirexpediente', methods=['GET', 'POST'])
@login_required
def vista_subirexpediente():
    if request.method == 'POST':
        # Verificar si es subida de archivo o formulario manual
        if 'archivo_excel' in request.files:
            return procesar_archivo_excel()
        else:
            return procesar_formulario_manual()
    
    # Obtener roles para el menú desplegable
    roles = obtener_roles_activos()
    
    return render_template('subirexpediente.html', roles=roles)

def procesar_archivo_excel():
    """Procesa la subida de archivo Excel"""
    file = request.files['archivo_excel']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        try:
            # Crear directorio de uploads si no existe
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            # Guardar archivo
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Procesar Excel
            resultados = procesar_excel_expedientes(filepath)
            
            # Eliminar archivo temporal
            os.remove(filepath)
            
            flash(f'Archivo procesado exitosamente. {resultados["procesados"]} expedientes agregados.', 'success')
            return redirect(url_for('idvistasubirexpediente.vista_subirexpediente'))
            
        except Exception as e:
            flash(f'Error procesando archivo: {str(e)}', 'error')
            return redirect(request.url)
    else:
        flash('Tipo de archivo no permitido. Use archivos .xlsx o .xls', 'error')
        return redirect(request.url)

def procesar_formulario_manual():
    """Procesa el formulario manual de expediente"""
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
        
        # Validaciones básicas
        if not radicado_completo and not radicado_corto:
            flash('Debe proporcionar al menos un radicado (completo o corto)', 'error')
            return redirect(request.url)
        
        # Insertar en base de datos
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        try:
            # 1. Insertar expediente principal
            query = """
                INSERT INTO expediente 
                (radicado_completo, radicado_corto, demandante, demandado, 
                 estado, ubicacion, tipo_solicitud, juzgado_origen, 
                 responsable, observaciones)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            cursor.execute(query, (
                radicado_completo or None,
                radicado_corto or None,
                demandante or None,
                demandado or None,
                estado_actual or None,
                ubicacion or None,
                tipo_solicitud or None,
                juzgado_origen or None,
                responsable or None,
                observaciones or None
            ))
            
            expediente_id = cursor.fetchone()[0]
            
            # 2. Insertar ingreso inicial (obligatorio)
            from datetime import datetime, date
            
            # Si no se proporciona fecha de ingreso, usar fecha actual
            if fecha_ingreso:
                try:
                    fecha_ingreso_obj = datetime.strptime(fecha_ingreso, '%Y-%m-%d').date()
                except:
                    fecha_ingreso_obj = date.today()
            else:
                fecha_ingreso_obj = date.today()
            
            # Si no se proporciona motivo, usar uno por defecto
            if not motivo_ingreso:
                motivo_ingreso = 'Ingreso manual del expediente'
            
            # Si no se proporcionan observaciones de ingreso, usar las generales
            if not observaciones_ingreso:
                observaciones_ingreso = observaciones or 'Expediente ingresado manualmente'
            
            cursor.execute("""
                INSERT INTO ingresos_expediente 
                (expediente_id, fecha_ingreso, motivo_ingreso, observaciones_ingreso)
                VALUES (%s, %s, %s, %s)
            """, (expediente_id, fecha_ingreso_obj, motivo_ingreso, observaciones_ingreso))
            
            # 3. Insertar estado inicial (si se proporciona)
            if estado_actual:
                cursor.execute("""
                    INSERT INTO estados_expediente 
                    (expediente_id, estado, fecha_estado, observaciones)
                    VALUES (%s, %s, %s, %s)
                """, (expediente_id, estado_actual, fecha_ingreso_obj, f'Estado inicial: {estado_actual}'))
            
            conn.commit()
            
            flash(f'Expediente creado exitosamente con ID: {expediente_id}. Se crearon los registros de ingreso y estado correspondientes.', 'success')
            return redirect(url_for('idvistasubirexpediente.vista_subirexpediente'))
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
        
    except Exception as e:
        flash(f'Error creando expediente: {str(e)}', 'error')
        return redirect(request.url)

def procesar_excel_expedientes(filepath):
    """Procesa un archivo Excel con expedientes"""
    try:
        # Leer Excel - usar la hoja "Resumen por Expediente"
        df = pd.read_excel(filepath, sheet_name="Resumen por Expediente")
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        procesados = 0
        errores = 0
        
        for _, row in df.iterrows():
            try:
                # Mapear columnas del Excel (usando los nombres correctos de la hoja resumen)
                radicado_completo = str(row.get('RadicadoUnicoLimpio', '')).strip() if pd.notna(row.get('RadicadoUnicoLimpio')) else None
                radicado_corto = str(row.get('RadicadoUnicoCompleto', '')).strip() if pd.notna(row.get('RadicadoUnicoCompleto')) else None
                demandante = str(row.get('DEMANDANTE_HOMOLOGADO', '')).strip() if pd.notna(row.get('DEMANDANTE_HOMOLOGADO')) else None
                demandado = str(row.get('DEMANDADO_HOMOLOGADO', '')).strip() if pd.notna(row.get('DEMANDADO_HOMOLOGADO')) else None
                
                if not radicado_completo and not radicado_corto:
                    continue  # Saltar filas sin radicado
                
                # Insertar expediente
                query = """
                    INSERT INTO expediente 
                    (radicado_completo, radicado_corto, demandante, demandado, 
                     estado, ubicacion, tipo_solicitud, juzgado_origen, 
                     responsable, observaciones)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(query, (
                    radicado_completo,
                    radicado_corto,
                    demandante,
                    demandado,
                    str(row.get('ESTADO_EXPEDIENTE', '')).strip() if pd.notna(row.get('ESTADO_EXPEDIENTE')) else None,
                    str(row.get('UBICACION', '')).strip() if pd.notna(row.get('UBICACION')) else None,
                    str(row.get('SOLICITUD', '')).strip() if pd.notna(row.get('SOLICITUD')) else None,
                    str(row.get('JuzgadoOrigen', '')).strip() if pd.notna(row.get('JuzgadoOrigen')) else None,
                    str(row.get('RESPONSABLE', '')).strip() if pd.notna(row.get('RESPONSABLE')) else None,
                    str(row.get('OBSERVACIONES', '')).strip() if pd.notna(row.get('OBSERVACIONES')) else None
                ))
                
                procesados += 1
                
            except Exception as e:
                errores += 1
                print(f"Error procesando fila: {e}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'procesados': procesados,
            'errores': errores
        }
        
    except Exception as e:
        raise Exception(f"Error leyendo archivo Excel: {str(e)}")