from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
import sys
import os
from datetime import datetime

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.auth import hash_password, validate_password, login_required, admin_required
from utils.security_validators import SecurityValidator, validate_form
from utils.rate_limiter import rate_limit

vistausuarios = Blueprint('idvistausuarios', __name__, template_folder='templates')

def obtener_todos_usuarios():
    """Obtener todos los usuarios con sus roles"""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        query = """
        SELECT u.id, u.usuario, u.correo, u.fecha_registro, u.administrador,
               r.nombre_rol, u.nombre, u.activo
        FROM usuarios u
        LEFT JOIN roles r ON u.rol_id = r.id
        ORDER BY u.fecha_registro DESC
        """
        cursor.execute(query)
        usuarios = cursor.fetchall()
        return usuarios
    except Exception as e:
        print(f"Error al obtener usuarios: {e}")
        return []
    finally:
        cursor.close()
        conexion.close()

def obtener_roles():
    """Obtener todos los roles disponibles"""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("SELECT id, nombre_rol FROM roles ORDER BY nombre_rol")
        roles = cursor.fetchall()
        return roles
    except Exception as e:
        print(f"Error al obtener roles: {e}")
        return []
    finally:
        cursor.close()
        conexion.close()

def obtener_usuario_por_id(usuario_id):
    """Obtener un usuario específico por ID"""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        query = """
        SELECT u.id, u.usuario, u.correo, u.fecha_registro, u.administrador, u.rol_id,
               r.nombre_rol, u.nombre, u.activo
        FROM usuarios u
        LEFT JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
        """
        cursor.execute(query, (usuario_id,))
        usuario = cursor.fetchone()
        return usuario
    except Exception as e:
        print(f"Error al obtener usuario: {e}")
        return None
    finally:
        cursor.close()
        conexion.close()

@vistausuarios.route('/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def vista_usuarios():
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        if accion == 'agregar_usuario':
            return agregar_usuario()
        elif accion == 'eliminar_usuario':
            return eliminar_usuario()
        elif accion == 'cambiar_password':
            return cambiar_password()
        elif accion == 'toggle_admin':
            return toggle_admin()
        elif accion == 'cambiar_rol':
            return cambiar_rol()
    
    # GET request - mostrar la página
    usuarios = obtener_todos_usuarios()
    roles = obtener_roles()
    
    # Calcular estadísticas
    total_usuarios = len(usuarios)
    administradores = sum(1 for u in usuarios if u[4])  # campo administrador
    usuarios_normales = total_usuarios - administradores
    usuarios_sin_rol = sum(1 for u in usuarios if not u[5])  # sin rol asignado
    
    estadisticas = {
        'total_usuarios': total_usuarios,
        'administradores': administradores,
        'usuarios_normales': usuarios_normales,
        'usuarios_sin_rol': usuarios_sin_rol
    }
    
    return render_template('usuarios.html', 
                         usuarios=usuarios, 
                         roles=roles, 
                         estadisticas=estadisticas)

@rate_limit(max_attempts=5, window_seconds=300)  # 5 intentos por 5 minutos
def agregar_usuario():
    """Agregar un nuevo usuario"""
    # 🔒 SEGURIDAD: Validar y sanitizar todos los inputs
    form_data = {
        'nombre_completo': request.form.get('nombre_completo', '').strip(),
        'nombre_usuario': request.form.get('nombre_usuario', '').strip(),
        'correo': request.form.get('correo', '').strip(),
        'password': request.form.get('password', '').strip(),
        'rol_id': request.form.get('rol_id'),
        'es_admin': request.form.get('es_admin') == 'on'
    }
    
    # Validar campos requeridos
    required_fields = ['nombre_completo', 'nombre_usuario', 'correo', 'password']
    validation = SecurityValidator.validate_form_data(form_data, required_fields)
    
    if not validation['valid']:
        for field, error in validation['errors'].items():
            flash(f'Error en {field}: {error}', 'error')
        return redirect(url_for('idvistausuarios.vista_usuarios'))
    
    # Usar datos sanitizados
    sanitized_data = validation['sanitized_data']
    nombre_completo = sanitized_data['nombre_completo']
    nombre_usuario = sanitized_data['nombre_usuario']
    correo = sanitized_data['correo']
    password = sanitized_data['password']
    rol_id = form_data['rol_id']
    es_admin = form_data['es_admin']
    
    # Validar contraseña con el nuevo sistema
    validation_result = validate_password(password)
    if not validation_result['is_valid']:
        for error in validation_result['errors']:
            flash(error, 'error')
        return redirect(url_for('idvistausuarios.vista_usuarios'))
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # Verificar si el usuario o correo ya existen
        cursor.execute("SELECT id FROM usuarios WHERE usuario = %s OR correo = %s", 
                      (nombre_usuario, correo))
        if cursor.fetchone():
            flash('El nombre de usuario o correo ya están en uso', 'error')
            return redirect(url_for('idvistausuarios.vista_usuarios'))
        
        # Insertar nuevo usuario
        password_hash = hash_password(password)
        rol_id_final = int(rol_id) if rol_id and rol_id != '' else None
        
        query = """
        INSERT INTO usuarios (nombre, usuario, correo, contrasena, rol_id, administrador, activo, fecha_registro)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (nombre_completo, nombre_usuario, correo, password_hash, rol_id_final, es_admin, True, datetime.now()))
        conexion.commit()
        
        # Mostrar información de fortaleza de contraseña
        score, strength = validation_result['score'], validation_result['strength']
        flash(f'Usuario {nombre_usuario} creado exitosamente. Fortaleza de contraseña: {strength} ({score}/100)', 'success')
        
    except Exception as e:
        conexion.rollback()
        flash(f'Error al crear usuario: {str(e)}', 'error')
        print(f"Error al agregar usuario: {e}")
    finally:
        cursor.close()
        conexion.close()
    
    return redirect(url_for('idvistausuarios.vista_usuarios'))

def eliminar_usuario():
    """Eliminar un usuario"""
    usuario_id = request.form.get('usuario_id')
    
    if not usuario_id:
        flash('ID de usuario no válido', 'error')
        return redirect(url_for('idvistausuarios.vista_usuarios'))
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # Obtener información del usuario antes de eliminarlo
        cursor.execute("SELECT usuario FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('idvistausuarios.vista_usuarios'))
        
        # Eliminar usuario
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conexion.commit()
        
        flash(f'Usuario {usuario[0]} eliminado exitosamente', 'success')
        
    except Exception as e:
        conexion.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'error')
        print(f"Error al eliminar usuario: {e}")
    finally:
        cursor.close()
        conexion.close()
    
    return redirect(url_for('idvistausuarios.vista_usuarios'))

def cambiar_password():
    """Cambiar contraseña de un usuario"""
    usuario_id = request.form.get('usuario_id')
    nueva_password = request.form.get('nueva_password', '').strip()
    
    if not usuario_id or not nueva_password:
        flash('Datos incompletos para cambiar contraseña', 'error')
        return redirect(url_for('idvistausuarios.vista_usuarios'))
    
    # Validar nueva contraseña con el sistema mejorado
    validation_result = validate_password(nueva_password)
    if not validation_result['is_valid']:
        for error in validation_result['errors']:
            flash(error, 'error')
        return redirect(url_for('idvistausuarios.vista_usuarios'))
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # Obtener información del usuario
        cursor.execute("SELECT usuario FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('idvistausuarios.vista_usuarios'))
        
        # Actualizar contraseña
        password_hash = hash_password(nueva_password)
        cursor.execute("UPDATE usuarios SET contrasena = %s WHERE id = %s", (password_hash, usuario_id))
        conexion.commit()
        
        # Mostrar información de fortaleza de contraseña
        score, strength = validation_result['score'], validation_result['strength']
        flash(f'Contraseña de {usuario[0]} actualizada exitosamente. Fortaleza: {strength} ({score}/100)', 'success')
        
    except Exception as e:
        conexion.rollback()
        flash(f'Error al cambiar contraseña: {str(e)}', 'error')
        print(f"Error al cambiar contraseña: {e}")
    finally:
        cursor.close()
        conexion.close()
    
    return redirect(url_for('idvistausuarios.vista_usuarios'))

def toggle_admin():
    """Alternar privilegios de administrador"""
    usuario_id = request.form.get('usuario_id')
    
    if not usuario_id:
        flash('ID de usuario no válido', 'error')
        return redirect(url_for('idvistausuarios.vista_usuarios'))
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # Obtener estado actual del usuario
        cursor.execute("SELECT usuario, administrador FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('idvistausuarios.vista_usuarios'))
        
        # Alternar estado de administrador
        nuevo_estado = not usuario[1]
        cursor.execute("UPDATE usuarios SET administrador = %s WHERE id = %s", (nuevo_estado, usuario_id))
        conexion.commit()
        
        estado_texto = "administrador" if nuevo_estado else "usuario normal"
        flash(f'{usuario[0]} ahora es {estado_texto}', 'success')
        
    except Exception as e:
        conexion.rollback()
        flash(f'Error al cambiar privilegios: {str(e)}', 'error')
        print(f"Error al toggle admin: {e}")
    finally:
        cursor.close()
        conexion.close()
    
    return redirect(url_for('idvistausuarios.vista_usuarios'))

def cambiar_rol():
    """Cambiar rol de un usuario"""
    usuario_id = request.form.get('usuario_id')
    nuevo_rol_id = request.form.get('nuevo_rol_id')
    
    if not usuario_id:
        flash('ID de usuario no válido', 'error')
        return redirect(url_for('idvistausuarios.vista_usuarios'))
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # Obtener información del usuario
        cursor.execute("SELECT usuario FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('idvistausuarios.vista_usuarios'))
        
        # Actualizar rol
        rol_id_final = int(nuevo_rol_id) if nuevo_rol_id and nuevo_rol_id != '' else None
        cursor.execute("UPDATE usuarios SET rol_id = %s WHERE id = %s", (rol_id_final, usuario_id))
        conexion.commit()
        
        if rol_id_final:
            cursor.execute("SELECT nombre_rol FROM roles WHERE id = %s", (rol_id_final,))
            rol = cursor.fetchone()
            rol_nombre = rol[0] if rol else "desconocido"
            flash(f'Rol de {usuario[0]} cambiado a {rol_nombre}', 'success')
        else:
            flash(f'Rol removido de {usuario[0]}', 'success')
        
    except Exception as e:
        conexion.rollback()
        flash(f'Error al cambiar rol: {str(e)}', 'error')
        print(f"Error al cambiar rol: {e}")
    finally:
        cursor.close()
        conexion.close()
    
    return redirect(url_for('idvistausuarios.vista_usuarios'))

@vistausuarios.route('/api/validate-password', methods=['POST'])
def api_validate_password():
    """API para validar contraseña en tiempo real"""
    try:
        print(f"[DEBUG] API validate-password llamada")
        print(f"[DEBUG] Content-Type: {request.content_type}")
        print(f"[DEBUG] Method: {request.method}")
        
        # Verificar si es JSON
        if not request.is_json:
            print(f"[ERROR] Request no es JSON. Content-Type: {request.content_type}")
            return jsonify({
                'is_valid': False,
                'errors': ['Content-Type debe ser application/json'],
                'score': 0,
                'strength': 'Error',
                'suggestions': []
            }), 400
        
        data = request.get_json()
        print(f"[DEBUG] Data recibida: {data}")
        
        if not data:
            print(f"[ERROR] No se pudo parsear JSON")
            return jsonify({
                'is_valid': False,
                'errors': ['Datos JSON inválidos'],
                'score': 0,
                'strength': 'Error',
                'suggestions': []
            }), 400
        
        password = data.get('password', '')
        print(f"[DEBUG] Password length: {len(password)}")
        
        if not password:
            print(f"[DEBUG] Password vacía")
            return jsonify({
                'is_valid': False,
                'errors': ['Contraseña requerida'],
                'score': 0,
                'strength': 'Muy Débil',
                'suggestions': ['Ingrese una contraseña']
            })
        
        print(f"[DEBUG] Validando contraseña...")
        validation_result = validate_password(password)
        print(f"[DEBUG] Resultado validación: {validation_result}")
        
        return jsonify(validation_result)
        
    except Exception as e:
        print(f"[ERROR] Excepción en api_validate_password: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'is_valid': False,
            'errors': [f'Error interno del servidor: {str(e)}'],
            'score': 0,
            'strength': 'Error',
            'suggestions': []
        }), 500