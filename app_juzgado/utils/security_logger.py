"""
Sistema de logging de seguridad para auditoría
"""

import logging
import os
from datetime import datetime
from flask import request, session
from functools import wraps

# Configurar logger de seguridad
def setup_security_logger():
    """Configura el logger de seguridad"""
    
    # Crear directorio de logs si no existe
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configurar logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    
    # Evitar duplicar handlers
    if not security_logger.handlers:
        # Handler para archivo de seguridad
        security_file = os.path.join(logs_dir, 'security.log')
        file_handler = logging.FileHandler(security_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Handler para archivo de errores críticos
        critical_file = os.path.join(logs_dir, 'security_critical.log')
        critical_handler = logging.FileHandler(critical_file, encoding='utf-8')
        critical_handler.setLevel(logging.ERROR)
        
        # Formato de logs
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        critical_handler.setFormatter(formatter)
        
        security_logger.addHandler(file_handler)
        security_logger.addHandler(critical_handler)
    
    return security_logger

# Instancia global del logger
security_logger = setup_security_logger()

class SecurityEvent:
    """Tipos de eventos de seguridad"""
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGIN_BLOCKED = "LOGIN_BLOCKED"
    CSRF_ATTACK = "CSRF_ATTACK"
    XSS_ATTEMPT = "XSS_ATTEMPT"
    SQL_INJECTION_ATTEMPT = "SQL_INJECTION_ATTEMPT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    USER_CREATED = "USER_CREATED"
    USER_DELETED = "USER_DELETED"
    ROLE_CHANGED = "ROLE_CHANGED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"

def get_client_info():
    """Obtiene información del cliente"""
    return {
        'ip': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'endpoint': request.endpoint,
        'method': request.method,
        'url': request.url
    }

def get_user_info():
    """Obtiene información del usuario actual"""
    if session.get('logged_in'):
        return {
            'user_id': session.get('user_id'),
            'username': session.get('usuario'),
            'is_admin': session.get('administrador', False)
        }
    return {'user_id': None, 'username': 'Anonymous', 'is_admin': False}

def log_security_event(event_type, message, level=logging.INFO, extra_data=None):
    """
    Registra un evento de seguridad
    
    Args:
        event_type: Tipo de evento (SecurityEvent)
        message: Mensaje descriptivo
        level: Nivel de logging
        extra_data: Datos adicionales
    """
    try:
        client_info = get_client_info()
        user_info = get_user_info()
        
        log_data = {
            'event': event_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'client_ip': client_info['ip'],
            'user_agent': client_info['user_agent'],
            'endpoint': client_info['endpoint'],
            'method': client_info['method'],
            'user_id': user_info['user_id'],
            'username': user_info['username'],
            'is_admin': user_info['is_admin']
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        # Formatear mensaje de log
        log_message = f"{event_type} | IP: {client_info['ip']} | User: {user_info['username']} | {message}"
        
        if extra_data:
            log_message += f" | Extra: {extra_data}"
        
        security_logger.log(level, log_message)
        
    except Exception as e:
        # Fallback logging si hay error
        security_logger.error(f"Error logging security event: {e}")

def log_login_attempt(username, success=True, reason=None):
    """Registra intento de login"""
    if success:
        log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            f"Successful login for user: {username}"
        )
    else:
        log_security_event(
            SecurityEvent.LOGIN_FAILED,
            f"Failed login attempt for user: {username}",
            level=logging.WARNING,
            extra_data={'reason': reason}
        )

def log_blocked_attempt(username, block_type="rate_limit"):
    """Registra intento bloqueado"""
    log_security_event(
        SecurityEvent.LOGIN_BLOCKED,
        f"Blocked login attempt for user: {username}",
        level=logging.ERROR,
        extra_data={'block_type': block_type}
    )

def log_csrf_attack():
    """Registra intento de ataque CSRF"""
    log_security_event(
        SecurityEvent.CSRF_ATTACK,
        "CSRF attack attempt detected",
        level=logging.ERROR
    )

def log_xss_attempt(input_data):
    """Registra intento de XSS"""
    log_security_event(
        SecurityEvent.XSS_ATTEMPT,
        "XSS attack attempt detected",
        level=logging.ERROR,
        extra_data={'input_data': input_data[:100]}  # Limitar longitud
    )

def log_sql_injection_attempt(query_data):
    """Registra intento de SQL injection"""
    log_security_event(
        SecurityEvent.SQL_INJECTION_ATTEMPT,
        "SQL injection attempt detected",
        level=logging.ERROR,
        extra_data={'query_data': query_data[:100]}
    )

def log_rate_limit_exceeded(limit_type="general"):
    """Registra exceso de rate limit"""
    log_security_event(
        SecurityEvent.RATE_LIMIT_EXCEEDED,
        f"Rate limit exceeded: {limit_type}",
        level=logging.WARNING,
        extra_data={'limit_type': limit_type}
    )

def log_unauthorized_access(resource):
    """Registra acceso no autorizado"""
    log_security_event(
        SecurityEvent.UNAUTHORIZED_ACCESS,
        f"Unauthorized access attempt to: {resource}",
        level=logging.ERROR,
        extra_data={'resource': resource}
    )

def log_user_action(action, target_user=None, details=None):
    """Registra acciones de usuario importantes"""
    event_map = {
        'password_changed': SecurityEvent.PASSWORD_CHANGED,
        'user_created': SecurityEvent.USER_CREATED,
        'user_deleted': SecurityEvent.USER_DELETED,
        'role_changed': SecurityEvent.ROLE_CHANGED
    }
    
    event_type = event_map.get(action, SecurityEvent.SUSPICIOUS_ACTIVITY)
    message = f"User action: {action}"
    
    if target_user:
        message += f" for user: {target_user}"
    
    extra_data = {'action': action}
    if target_user:
        extra_data['target_user'] = target_user
    if details:
        extra_data['details'] = details
    
    log_security_event(event_type, message, extra_data=extra_data)

def security_audit(func):
    """
    Decorador para auditar funciones críticas de seguridad
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        function_name = func.__name__
        
        # Log inicio de función crítica
        log_security_event(
            SecurityEvent.SUSPICIOUS_ACTIVITY,
            f"Critical function called: {function_name}",
            extra_data={'function': function_name, 'args_count': len(args)}
        )
        
        try:
            result = func(*args, **kwargs)
            
            # Log éxito
            log_security_event(
                SecurityEvent.SUSPICIOUS_ACTIVITY,
                f"Critical function completed successfully: {function_name}",
                extra_data={'function': function_name, 'success': True}
            )
            
            return result
            
        except Exception as e:
            # Log error
            log_security_event(
                SecurityEvent.SUSPICIOUS_ACTIVITY,
                f"Critical function failed: {function_name} - {str(e)}",
                level=logging.ERROR,
                extra_data={'function': function_name, 'error': str(e)}
            )
            raise
    
    return wrapper

def get_security_stats():
    """
    Obtiene estadísticas de seguridad del log
    """
    try:
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        security_file = os.path.join(logs_dir, 'security.log')
        
        if not os.path.exists(security_file):
            return {'error': 'Log file not found'}
        
        stats = {
            'total_events': 0,
            'login_attempts': 0,
            'failed_logins': 0,
            'blocked_attempts': 0,
            'csrf_attacks': 0,
            'xss_attempts': 0,
            'sql_injection_attempts': 0,
            'rate_limit_exceeded': 0
        }
        
        with open(security_file, 'r', encoding='utf-8') as f:
            for line in f:
                stats['total_events'] += 1
                
                if 'LOGIN_SUCCESS' in line:
                    stats['login_attempts'] += 1
                elif 'LOGIN_FAILED' in line:
                    stats['failed_logins'] += 1
                elif 'LOGIN_BLOCKED' in line:
                    stats['blocked_attempts'] += 1
                elif 'CSRF_ATTACK' in line:
                    stats['csrf_attacks'] += 1
                elif 'XSS_ATTEMPT' in line:
                    stats['xss_attempts'] += 1
                elif 'SQL_INJECTION_ATTEMPT' in line:
                    stats['sql_injection_attempts'] += 1
                elif 'RATE_LIMIT_EXCEEDED' in line:
                    stats['rate_limit_exceeded'] += 1
        
        return stats
        
    except Exception as e:
        return {'error': f'Error reading security stats: {e}'}

# Inicializar logger al importar
setup_security_logger()