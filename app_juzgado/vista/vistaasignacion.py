from flask import Blueprint, render_template, request, flash, redirect, url_for, session
import hashlib
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.auth import login_required, get_current_user

# Crear un Blueprint
vistaasignacion = Blueprint('idvistaasignacion', __name__, template_folder='templates')

@vistaasignacion.route('/asignacion')
@login_required
def vista_asignacion():
    usuario_actual = get_current_user()
    expedientes_asignados = []
    # Inicializar estadísticas con valores por defecto
    estadisticas = {
        'total': 0,
        'activos': 0,
        'inactivos': 0,
        'pendientes': 0,
        'salieron': 0,
        'completados': 0,
        'en_proceso': 0,
        'sin_informacion': 0,
        'porcentaje_activos': 0,
        'porcentaje_completados': 0,
        'rol': None
    }
    mensaje = ""
    info_usuario = {'rol': None, 'nombre': 'Usuario', 'correo': '', 'usuario': '', 'activo': True}
    
    if not usuario_actual:
        flash('Error: No se pudo obtener la información del usuario', 'error')
        return redirect(url_for('idvistalogin.vista_login'))
    
    try:
        # Obtener información del rol del usuario
        info_usuario = obtener_info_usuario_con_rol(usuario_actual['id'])
        
        if not info_usuario:
            mensaje = "Usuario no encontrado en el sistema"
            flash(mensaje, 'error')
            info_usuario = {'rol': None, 'nombre': usuario_actual.get('nombre', 'Usuario'), 'correo': usuario_actual.get('correo', ''), 'usuario': usuario_actual.get('usuario', ''), 'activo': True}
        elif not info_usuario['rol']:
            mensaje = "No tienes un rol asignado. Contacta al administrador para que te asigne un rol."
            flash(mensaje, 'warning')
        else:
            # Obtener expedientes asignados según el rol
            expedientes_asignados = obtener_expedientes_por_usuario(usuario_actual['id'], info_usuario['rol'])
            estadisticas = calcular_estadisticas_usuario(expedientes_asignados, info_usuario['rol'])
            
            if not expedientes_asignados:
                mensaje = f"No tienes expedientes asignados como {info_usuario['rol']}"
            else:
                mensaje = f"Tienes {len(expedientes_asignados)} expediente(s) asignado(s) como {info_usuario['rol']}"
    
    except Exception as e:
        mensaje = f"Error al cargar expedientes: {str(e)}"
        flash(mensaje, 'error')
        info_usuario = {'rol': None, 'nombre': usuario_actual.get('nombre', 'Usuario'), 'correo': usuario_actual.get('correo', ''), 'usuario': usuario_actual.get('usuario', ''), 'activo': True}
        # Las estadísticas ya están inicializadas con valores por defecto
    
    return render_template('asignacion.html', 
                         usuario=info_usuario,
                         expedientes=expedientes_asignados,
                         estadisticas=estadisticas,
                         mensaje=mensaje)

def obtener_info_usuario_con_rol(usuario_id):
    """Obtiene la información del usuario incluyendo su rol"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        query = """
            SELECT u.id, u.nombre, u.correo, u.usuario, r.nombre_rol as rol, u.activo
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE u.id = %s
        """
        
        cursor.execute(query, (usuario_id,))
        resultado = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if resultado:
            return {
                'id': resultado[0],
                'nombre': resultado[1],
                'correo': resultado[2],
                'usuario': resultado[3],
                'rol': resultado[4],
                'activo': resultado[5]
            }
        
        return None
        
    except Exception as e:
        print(f"Error en obtener_info_usuario_con_rol: {e}")
        raise e

def obtener_expedientes_por_usuario(usuario_id, rol_usuario):
    """Obtiene los expedientes asignados a un usuario según su rol"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Ahora buscamos por el rol del usuario en la columna responsable
        # La columna responsable ahora contiene el nombre del rol (ESCRIBIENTE/SUSTANCIADOR)
        query = """
            SELECT 
                e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                e.estado_actual, e.estado_principal, e.estado_adicional, e.ubicacion_actual, 
                e.tipo_tramite, e.juzgado_origen, e.responsable, e.fecha_ultima_actualizacion,
                e.fecha_ultima_actuacion_real,
                COUNT(i.id) as total_ingresos,
                COUNT(s.id) as total_estados,
                MAX(i.fecha_ingreso) as ultimo_ingreso,
                MAX(s.fecha_estado) as ultimo_estado
            FROM expedientes e
            LEFT JOIN ingresos_expediente i ON e.id = i.expediente_id
            LEFT JOIN estados_expediente s ON e.id = s.expediente_id
            WHERE e.responsable = %s
            GROUP BY e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                     e.estado_actual, e.estado_principal, e.estado_adicional, e.ubicacion_actual, 
                     e.tipo_tramite, e.juzgado_origen, e.responsable, e.fecha_ultima_actualizacion,
                     e.fecha_ultima_actuacion_real
            ORDER BY 
                CASE 
                    WHEN e.estado_principal = 'ACTIVO' THEN 1
                    WHEN e.estado_principal = 'INACTIVO' AND e.estado_adicional = 'PENDIENTE' THEN 2
                    WHEN e.estado_principal = 'INACTIVO' AND e.estado_adicional = 'SALIO' THEN 3
                    WHEN e.estado_actual = 'EN_PROCESO' THEN 4
                    WHEN e.estado_actual = 'PENDIENTE' THEN 5
                    WHEN e.estado_actual = 'COMPLETADO' THEN 6
                    ELSE 7
                END,
                e.fecha_ultima_actualizacion DESC
        """
        
        cursor.execute(query, (rol_usuario,))
        resultados = cursor.fetchall()
        
        expedientes = []
        for row in resultados:
            expedientes.append({
                'id': row[0],
                'radicado_completo': row[1],
                'radicado_corto': row[2],
                'demandante': row[3],
                'demandado': row[4],
                'estado_actual': row[5] or 'SIN_INFORMACION',
                'estado_principal': row[6],
                'estado_adicional': row[7],
                'ubicacion_actual': row[8],
                'tipo_tramite': row[9],
                'juzgado_origen': row[10],
                'responsable': row[11],
                'fecha_ultima_actualizacion': row[12],
                'fecha_ultima_actuacion_real': row[13],
                'total_ingresos': row[14] or 0,
                'total_estados': row[15] or 0,
                'ultimo_ingreso': row[16],
                'ultimo_estado': row[17]
            })
        
        cursor.close()
        conn.close()
        
        return expedientes
        
    except Exception as e:
        print(f"Error en obtener_expedientes_por_usuario: {e}")
        raise e

def calcular_estadisticas_usuario(expedientes, rol_usuario):
    """Calcula estadísticas de los expedientes del usuario usando nuevos estados"""
    if not expedientes:
        return {
            'total': 0,
            'activos': 0,
            'inactivos': 0,
            'pendientes': 0,
            'salieron': 0,
            'completados': 0,
            'en_proceso': 0,
            'sin_informacion': 0,
            'porcentaje_activos': 0,
            'rol': rol_usuario
        }
    
    total = len(expedientes)
    
    # Nuevos estados
    activos = len([e for e in expedientes if e.get('estado_principal') == 'ACTIVO'])
    inactivos = len([e for e in expedientes if e.get('estado_principal') == 'INACTIVO'])
    pendientes = len([e for e in expedientes if e.get('estado_adicional') == 'PENDIENTE'])
    salieron = len([e for e in expedientes if e.get('estado_adicional') == 'SALIO'])
    
    # Estados antiguos (para compatibilidad)
    completados = len([e for e in expedientes if e['estado_actual'] in ['COMPLETADO', 'FINALIZADO', 'TERMINADO', 'PROCESADO_AZURE']])
    en_proceso = len([e for e in expedientes if e['estado_actual'] in ['EN_PROCESO', 'PENDIENTE', 'EN PROCESO', 'ACTIVO']])
    sin_informacion = len([e for e in expedientes if e['estado_actual'] in ['SIN_INFORMACION', 'SIN INFORMACION', 'SIN_TRAMITE', 'SIN TRAMITE'] or not e['estado_actual']])
    
    porcentaje_activos = round((activos / total) * 100, 1) if total > 0 else 0
    porcentaje_completados = round((completados / total) * 100, 1) if total > 0 else 0
    
    return {
        'total': total,
        'activos': activos,
        'inactivos': inactivos,
        'pendientes': pendientes,
        'salieron': salieron,
        'completados': completados,
        'en_proceso': en_proceso,
        'sin_informacion': sin_informacion,
        'porcentaje_activos': porcentaje_activos,
        'porcentaje_completados': porcentaje_completados,
        'rol': rol_usuario
    }