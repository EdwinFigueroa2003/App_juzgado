from flask import Blueprint, render_template, request, flash, redirect, url_for, session
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.auth import hash_password
from utils.rate_limiter import login_rate_limit, record_failed_login_attempt, clear_login_attempts
from utils.security_validators import SecurityValidator
from utils.security_logger import log_login_attempt, log_blocked_attempt, log_unauthorized_access

# Crear un Blueprint
vistalogin = Blueprint('idvistalogin', __name__, template_folder='templates')

def verificar_usuario(username_or_email, password):
    """Verifica las credenciales del usuario"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Buscar usuario por nombre de usuario o correo
        cursor.execute("""
            SELECT id, usuario, correo, contrasena, nombre, activo, administrador
            FROM usuarios 
            WHERE (usuario = %s OR correo = %s) AND activo = TRUE
        """, (username_or_email, username_or_email))
        
        user = cursor.fetchone()
        
        if user:
            user_id, usuario, correo, contrasena_bd, nombre, activo, administrador = user
            
            # Verificar contraseña hasheada
            password_hash = hash_password(password)
            
            # Verificar si la contraseña coincide (hash vs hash)
            if contrasena_bd == password_hash:
                # Actualizar último acceso
                cursor.execute("""
                    UPDATE usuarios 
                    SET fecha_ultima_sesion = CURRENT_TIMESTAMP 
                    WHERE id = %s
                """, (user_id,))
                conn.commit()
                
                cursor.close()
                conn.close()
                
                return {
                    'id': user_id,
                    'usuario': usuario,
                    'correo': correo,
                    'nombre': nombre,
                    'administrador': administrador
                }
            
            # Si no coincide con hash, verificar si es contraseña plana (para migración)
            elif contrasena_bd == password and len(contrasena_bd) < 64:
                print(f"Migrando contraseña plana a hash para usuario: {usuario}")
                
                # Actualizar contraseña a hash
                cursor.execute("""
                    UPDATE usuarios 
                    SET contrasena = %s, fecha_ultima_sesion = CURRENT_TIMESTAMP 
                    WHERE id = %s
                """, (password_hash, user_id))
                conn.commit()
                
                cursor.close()
                conn.close()
                
                return {
                    'id': user_id,
                    'usuario': usuario,
                    'correo': correo,
                    'nombre': nombre,
                    'administrador': administrador
                }
        
        cursor.close()
        conn.close()
        return None
        
    except Exception as e:
        print(f"Error verificando usuario: {e}")
        return None

@vistalogin.route('/login', methods=['GET', 'POST'])
@login_rate_limit
def vista_login():
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # 🔒 SEGURIDAD: Validar y sanitizar inputs
        if not username_or_email or not password:
            flash('Por favor ingrese usuario/email y contraseña', 'error')
            return render_template('login.html')
        
        # Sanitizar input del usuario
        username_or_email = SecurityValidator.sanitize_input(username_or_email)
        
        # Validar longitud para prevenir ataques
        if len(username_or_email) > 254 or len(password) > 128:
            flash('Credenciales inválidas', 'error')
            record_failed_login_attempt(username_or_email)
            return render_template('login.html')
        
        # Verificar credenciales
        user = verificar_usuario(username_or_email, password)
        
        if user:
            # 🔒 SEGURIDAD: Limpiar intentos fallidos en login exitoso
            clear_login_attempts(username_or_email)
            
            # 🔒 SEGURIDAD: Log login exitoso
            log_login_attempt(username_or_email, success=True)
            
            # Crear sesión
            session['user_id'] = user['id']
            session['usuario'] = user['usuario']
            session['correo'] = user['correo']
            session['nombre'] = user['nombre']
            session['administrador'] = user['administrador']
            session['logged_in'] = True
            
            flash(f'¡Bienvenido {user["nombre"]}!', 'success')
            return redirect(url_for('idvistahome.vista_home'))
        else:
            # 🔒 SEGURIDAD: Registrar intento fallido y log
            record_failed_login_attempt(username_or_email)
            log_login_attempt(username_or_email, success=False, reason="Invalid credentials")
            flash('Usuario/email o contraseña incorrectos', 'error')
            return render_template('login.html')
    
    # Si ya está logueado, redirigir al home
    if session.get('logged_in'):
        return redirect(url_for('idvistahome.vista_home'))
    
    return render_template('login.html')

