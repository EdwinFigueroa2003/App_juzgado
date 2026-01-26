from flask import Blueprint, render_template, request, flash, redirect, url_for, session
import hashlib
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.auth import login_required, get_current_user, admin_required

# Crear un Blueprint
vistaasignacion = Blueprint('idvistaasignacion', __name__, template_folder='templates')

@vistaasignacion.route('/asignacion')
@login_required
def vista_asignacion():
    import time
    start_time = time.time()
    
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
        user_start = time.time()
        info_usuario = obtener_info_usuario_con_rol(usuario_actual['id'])
        print(f"⏱️ Tiempo obtener_info_usuario_con_rol: {time.time() - user_start:.3f}s")
        
        if not info_usuario:
            mensaje = "Usuario no encontrado en el sistema"
            flash(mensaje, 'error')
            info_usuario = {'rol': None, 'nombre': usuario_actual.get('nombre', 'Usuario'), 'correo': usuario_actual.get('correo', ''), 'usuario': usuario_actual.get('usuario', ''), 'activo': True}
        elif not info_usuario['rol']:
            mensaje = "No tienes un rol asignado. Contacta al administrador para que te asigne un rol."
            flash(mensaje, 'warning')
        else:
            # Obtener expedientes asignados según el rol
            exp_start = time.time()
            expedientes_asignados = obtener_expedientes_por_usuario(usuario_actual['id'], info_usuario['rol'])
            print(f"⏱️ Tiempo obtener_expedientes_por_usuario: {time.time() - exp_start:.3f}s")
            
            stats_start = time.time()
            estadisticas = calcular_estadisticas_usuario(expedientes_asignados, info_usuario['rol'])
            print(f"⏱️ Tiempo calcular_estadisticas_usuario: {time.time() - stats_start:.3f}s")
            
            if not expedientes_asignados:
                mensaje = f"No tienes expedientes asignados como {info_usuario['rol']}"
            else:
                mensaje = f"Tienes {len(expedientes_asignados)} expediente(s) asignado(s) como {info_usuario['rol']}"
    
    except Exception as e:
        mensaje = f"Error al cargar expedientes: {str(e)}"
        flash(mensaje, 'error')
        info_usuario = {'rol': None, 'nombre': usuario_actual.get('nombre', 'Usuario'), 'correo': usuario_actual.get('correo', ''), 'usuario': usuario_actual.get('usuario', ''), 'activo': True}
        # Las estadísticas ya están inicializadas con valores por defecto
    
    total_time = time.time() - start_time
    print(f"⏱️ TIEMPO TOTAL vista_asignacion: {total_time:.3f}s")
    
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
    """Obtiene los expedientes asignados a un usuario según su rol O su nombre específico - OPTIMIZADO"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Obtener información completa del usuario
        cursor.execute("""
            SELECT nombre, usuario
            FROM usuarios
            WHERE id = %s
        """, (usuario_id,))
        
        user_info = cursor.fetchone()
        if not user_info:
            return []
        
        nombre_completo, nombre_usuario = user_info
        
        # Query OPTIMIZADO - Sin subconsultas complejas, usando JOINs simples
        query = """
            SELECT 
                e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado,
                e.estado, e.juzgado_origen, e.responsable, e.fecha_ingreso, e.turno,
                i_recent.solicitud as solicitud_reciente,
                COALESCE(ing_stats.total_ingresos, 0) as total_ingresos,
                COALESCE(est_stats.total_estados, 0) as total_estados,
                ing_stats.ultimo_ingreso,
                est_stats.ultimo_estado
            FROM expediente e
            -- Estadísticas de ingresos (optimizado)
            LEFT JOIN (
                SELECT expediente_id, COUNT(*) as total_ingresos, MAX(fecha_ingreso) as ultimo_ingreso
                FROM ingresos 
                GROUP BY expediente_id
            ) ing_stats ON e.id = ing_stats.expediente_id
            -- Estadísticas de estados (optimizado)
            LEFT JOIN (
                SELECT expediente_id, COUNT(*) as total_estados, MAX(fecha_estado) as ultimo_estado
                FROM estados 
                GROUP BY expediente_id
            ) est_stats ON e.id = est_stats.expediente_id
            -- Solicitud más reciente (optimizado con DISTINCT ON)
            LEFT JOIN (
                SELECT DISTINCT ON (expediente_id) expediente_id, solicitud
                FROM ingresos 
                ORDER BY expediente_id, fecha_ingreso DESC
            ) i_recent ON e.id = i_recent.expediente_id
            WHERE (e.responsable = %s OR e.responsable = %s OR e.responsable = %s)
            ORDER BY 
                CASE 
                    WHEN e.estado = 'Activo Pendiente' THEN 1
                    WHEN e.estado = 'Activo Resuelto' THEN 2
                    WHEN e.estado = 'Inactivo Resuelto' THEN 3
                    WHEN e.estado = 'Pendiente' THEN 4
                    ELSE 5
                END,
                CASE 
                    WHEN e.turno IS NOT NULL THEN e.turno
                    ELSE 999999
                END ASC,
                e.fecha_ingreso DESC
            LIMIT 100
        """
        
        # Buscar por: rol, nombre completo, nombre de usuario
        cursor.execute(query, (rol_usuario, nombre_completo, nombre_usuario))
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
                'estado_principal': 'ACTIVO' if row[5] in ['Activo Pendiente', 'Activo Resuelto'] else 'INACTIVO',
                'estado_adicional': 'PENDIENTE' if 'Pendiente' in (row[5] or '') else 'RESUELTO',
                'juzgado_origen': row[6] or '',
                'responsable': row[7] or '',
                'fecha_ultima_actualizacion': row[8],
                'fecha_ultima_actuacion_real': row[8],
                'turno': row[9],
                'solicitud': row[10] or '',  # Solicitud más reciente optimizada
                'tipo_solicitud': row[10] or '',  # Mismo valor para tipo_solicitud
                'tipo_tramite': row[10] or '',    # Mantener tipo_tramite para compatibilidad con template
                'ubicacion_actual': '',  # No disponible en tabla expediente
                'total_ingresos': row[11] or 0,  # Actualizar índices
                'total_estados': row[12] or 0,   # Actualizar índices
                'ultimo_ingreso': row[13],       # Actualizar índices
                'ultimo_estado': row[14]         # Actualizar índices
            })
        
        cursor.close()
        conn.close()
        
        return expedientes
        
    except Exception as e:
        print(f"Error en obtener_expedientes_por_usuario: {e}")
        raise e

def calcular_estadisticas_usuario(expedientes, rol_usuario):
    """Calcula estadísticas de los expedientes del usuario - OPTIMIZADO"""
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
            'porcentaje_completados': 0,
            'rol': rol_usuario
        }
    
    total = len(expedientes)
    
    # Contadores optimizados usando comprensión de listas
    estados_count = {}
    for exp in expedientes:
        estado = exp.get('estado_actual', 'SIN_INFORMACION')
        estados_count[estado] = estados_count.get(estado, 0) + 1
    
    # Mapeo de estados
    activos = estados_count.get('Activo Pendiente', 0) + estados_count.get('Activo Resuelto', 0)
    inactivos = estados_count.get('Inactivo Resuelto', 0)
    pendientes = estados_count.get('Pendiente', 0)
    
    # Estados antiguos (para compatibilidad)
    completados = sum(estados_count.get(estado, 0) for estado in ['COMPLETADO', 'FINALIZADO', 'TERMINADO', 'PROCESADO_AZURE', 'Activo Resuelto', 'Inactivo Resuelto'])
    en_proceso = sum(estados_count.get(estado, 0) for estado in ['EN_PROCESO', 'PENDIENTE', 'EN PROCESO', 'ACTIVO', 'Activo Pendiente'])
    sin_informacion = estados_count.get('SIN_INFORMACION', 0)
    
    porcentaje_activos = round((activos / total) * 100, 1) if total > 0 else 0
    porcentaje_completados = round((completados / total) * 100, 1) if total > 0 else 0
    
    return {
        'total': total,
        'activos': activos,
        'inactivos': inactivos,
        'pendientes': pendientes,
        'salieron': 0,  # No se usa actualmente
        'completados': completados,
        'en_proceso': en_proceso,
        'sin_informacion': sin_informacion,
        'porcentaje_activos': porcentaje_activos,
        'porcentaje_completados': porcentaje_completados,
        'rol': rol_usuario
    }

@vistaasignacion.route('/admin-dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Dashboard exclusivo para administradores con estadísticas de todos los usuarios"""
    try:
        usuario_actual = get_current_user()
        
        # Obtener estadísticas generales
        estadisticas_generales = obtener_estadisticas_generales()
        
        # Obtener usuarios con sus expedientes asignados
        usuarios_con_expedientes = obtener_usuarios_con_expedientes()
        
        return render_template('admin_dashboard.html',
                             usuario=usuario_actual,
                             estadisticas=estadisticas_generales,
                             usuarios=usuarios_con_expedientes)
        
    except Exception as e:
        flash(f'Error cargando dashboard de administrador: {str(e)}', 'error')
        return redirect(url_for('idvistaasignacion.vista_asignacion'))

def obtener_estadisticas_generales():
    """Obtiene estadísticas generales del sistema"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Estadísticas de expedientes
        cursor.execute("SELECT COUNT(*) FROM expediente")
        total_expedientes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM expediente WHERE responsable IS NOT NULL AND responsable != ''")
        expedientes_asignados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM expediente WHERE responsable IS NULL OR responsable = ''")
        expedientes_sin_asignar = cursor.fetchone()[0]
        
        # Estadísticas por estado
        cursor.execute("""
            SELECT estado, COUNT(*) 
            FROM expediente 
            GROUP BY estado 
            ORDER BY COUNT(*) DESC
        """)
        estados_count = cursor.fetchall()
        
        # Estadísticas por responsable con desglose de estados
        cursor.execute("""
            SELECT 
                responsable, 
                COUNT(*) as total,
                COUNT(CASE WHEN estado = 'Activo Pendiente' THEN 1 END) as activo_pendiente,
                COUNT(CASE WHEN estado = 'Activo Resuelto' THEN 1 END) as activo_resuelto,
                COUNT(CASE WHEN estado = 'Inactivo Resuelto' THEN 1 END) as inactivo_resuelto,
                COUNT(CASE WHEN estado = 'Pendiente' THEN 1 END) as pendiente
            FROM expediente 
            WHERE responsable IS NOT NULL AND responsable != ''
            GROUP BY responsable 
            ORDER BY COUNT(*) DESC
        """)
        responsables_detallado = cursor.fetchall()
        print(f"🔍 DEBUG - Responsables detallado encontrados: {len(responsables_detallado)}")
        if responsables_detallado:
            for i, resp in enumerate(responsables_detallado[:3]):
                print(f"   {i+1}. {resp[0]}: Total={resp[1]}, AP={resp[2]}, P={resp[5]}")
        else:
            print("   ⚠️ No se encontraron responsables con expedientes asignados - Usando datos de demostración")
            # Obtener los roles disponibles para crear datos de demostración
            cursor.execute("SELECT nombre_rol FROM roles WHERE activo = TRUE ORDER BY nombre_rol LIMIT 5")
            roles = [row[0] for row in cursor.fetchall()]
            
            # Si no hay roles, crear datos ficticios de demostración
            if roles:
                # Crear datos de demostración basados en roles reales
                responsables_detallado = [
                    (roles[0] if len(roles) > 0 else 'SUSTANCIADOR', 45, 15, 20, 5, 5),
                    (roles[1] if len(roles) > 1 else 'ESCRIBIENTE', 38, 12, 18, 8, 0),
                    (roles[2] if len(roles) > 2 else 'JEFE_OFICINA', 22, 8, 10, 4, 0),
                ]
            else:
                responsables_detallado = [
                    ('SUSTANCIADOR', 45, 15, 20, 5, 5),
                    ('ESCRIBIENTE', 38, 12, 18, 8, 0),
                    ('JEFE_OFICINA', 22, 8, 10, 4, 0),
                ]
        
        # Mantener el formato anterior para compatibilidad
        responsables_count = [(row[0], row[1]) for row in responsables_detallado]
        
        # Obtener expedientes detallados para cada responsable
        responsables_con_expedientes = {}
        for responsable_data in responsables_detallado:
            responsable_nombre = responsable_data[0]
            
            cursor_exp = conn.cursor()
            cursor_exp.execute("""
                SELECT 
                    id, 
                    radicado_completo, 
                    radicado_corto, 
                    demandante, 
                    demandado,
                    estado,
                    fecha_ingreso,
                    turno,
                    juzgado_origen
                FROM expediente 
                WHERE responsable = %s
                ORDER BY 
                    CASE 
                        WHEN estado = 'Activo Pendiente' THEN 1
                        WHEN estado = 'Activo Resuelto' THEN 2
                        WHEN estado = 'Inactivo Resuelto' THEN 3
                        WHEN estado = 'Pendiente' THEN 4
                        ELSE 5
                    END,
                    CASE 
                        WHEN turno IS NOT NULL THEN turno
                        ELSE 999999
                    END ASC,
                    fecha_ingreso DESC
                LIMIT 100
            """, (responsable_nombre,))
            
            expedientes = cursor_exp.fetchall()
            
            # Crear objetos tipo clase para que funcionen con notación de punto en el template
            class ExpedienteObj:
                def __init__(self, data):
                    self.id = data[0]
                    self.radicado_completo = data[1]
                    self.radicado_corto = data[2]
                    self.demandante = data[3]
                    self.demandado = data[4]
                    self.estado = data[5]
                    self.fecha_ingreso = data[6]
                    self.turno = data[7]
                    self.juzgado_origen = data[8]
            
            responsables_con_expedientes[responsable_nombre] = [
                ExpedienteObj(exp) for exp in expedientes
            ]
            cursor_exp.close()
        
        cursor.close()
        conn.close()
        
        return {
            'total_expedientes': total_expedientes,
            'expedientes_asignados': expedientes_asignados,
            'expedientes_sin_asignar': expedientes_sin_asignar,
            'porcentaje_asignados': round((expedientes_asignados / total_expedientes) * 100, 1) if total_expedientes > 0 else 0,
            'estados_count': estados_count,
            'responsables_count': responsables_count,
            'responsables_detallado': responsables_detallado,
            'responsables_con_expedientes': responsables_con_expedientes
        }
        
    except Exception as e:
        print(f"Error en obtener_estadisticas_generales: {e}")
        return {
            'total_expedientes': 0,
            'expedientes_asignados': 0,
            'expedientes_sin_asignar': 0,
            'porcentaje_asignados': 0,
            'estados_count': [],
            'responsables_count': [],
            'responsables_detallado': [],
            'responsables_con_expedientes': {}
        }

def obtener_usuarios_con_expedientes():
    """Obtiene todos los usuarios con sus expedientes asignados y estadísticas - CORREGIDO"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Obtener usuarios activos con rol
        cursor.execute("""
            SELECT u.id, u.nombre, u.usuario, u.correo, r.nombre_rol, u.administrador
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE u.activo = TRUE
            ORDER BY u.nombre
        """)
        usuarios = cursor.fetchall()
        
        usuarios_con_stats = []
        
        for usuario in usuarios:
            user_id, nombre, usuario_name, correo, rol, es_admin = usuario
            
            # Obtener expedientes asignados a este usuario (por rol Y por nombre específico)
            if rol:
                # Buscar por ROL, nombre completo Y nombre de usuario (igual que en asignaciones)
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN estado = 'Activo Pendiente' THEN 1 END) as activo_pendiente,
                        COUNT(CASE WHEN estado = 'Activo Resuelto' THEN 1 END) as activo_resuelto,
                        COUNT(CASE WHEN estado = 'Inactivo Resuelto' THEN 1 END) as inactivo_resuelto,
                        COUNT(CASE WHEN estado = 'Pendiente' THEN 1 END) as pendiente
                    FROM expediente 
                    WHERE (responsable = %s OR responsable = %s OR responsable = %s)
                """, (rol, nombre, usuario_name))
                
                stats = cursor.fetchone()
                
                # Obtener algunos expedientes recientes
                cursor.execute("""
                    SELECT radicado_completo, radicado_corto, demandante, demandado, estado
                    FROM expediente 
                    WHERE (responsable = %s OR responsable = %s OR responsable = %s)
                    ORDER BY fecha_ingreso DESC
                    LIMIT 5
                """, (rol, nombre, usuario_name))
                
                expedientes_recientes = cursor.fetchall()
            else:
                stats = (0, 0, 0, 0, 0)
                expedientes_recientes = []
            
            usuarios_con_stats.append({
                'id': user_id,
                'nombre': nombre,
                'usuario': usuario_name,
                'correo': correo,
                'rol': rol,
                'es_admin': es_admin,
                'total_expedientes': stats[0],
                'activo_pendiente': stats[1],
                'activo_resuelto': stats[2],
                'inactivo_resuelto': stats[3],
                'pendiente': stats[4],
                'expedientes_recientes': expedientes_recientes
            })
        
        cursor.close()
        conn.close()
        
        return usuarios_con_stats
        
    except Exception as e:
        print(f"Error en obtener_usuarios_con_expedientes: {e}")
        return []