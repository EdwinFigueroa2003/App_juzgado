"""
Vista del dashboard de seguridad
"""

from flask import Blueprint, render_template, jsonify
import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auth import login_required, admin_required
from utils.security_logger import get_security_stats
from utils.rate_limiter import rate_limiter

# Crear un Blueprint
vistasecurity = Blueprint('idvistasecurity', __name__, template_folder='templates')

@vistasecurity.route('/security-dashboard')
@login_required
@admin_required
@login_required
def security_dashboard():
    """Dashboard de seguridad para administradores"""
    try:
        # Obtener estadísticas de seguridad
        security_stats = get_security_stats()
        
        # Obtener información del rate limiter
        rate_limit_stats = {
            'blocked_ips': len(rate_limiter.blocked_ips),
            'blocked_users': len(rate_limiter.blocked_users),
            'total_attempts': sum(len(attempts) for attempts in rate_limiter.attempts.values()),
            'login_attempts': sum(len(attempts) for attempts in rate_limiter.login_attempts.values())
        }
        
        # Calcular métricas de seguridad
        total_events = security_stats.get('total_events', 0)
        failed_logins = security_stats.get('failed_logins', 0)
        
        security_score = calculate_security_score(security_stats, rate_limit_stats)
        
        dashboard_data = {
            'security_stats': security_stats,
            'rate_limit_stats': rate_limit_stats,
            'security_score': security_score,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render_template('security_dashboard.html', data=dashboard_data)
        
    except Exception as e:
        print(f"Error en security dashboard: {e}")
        return render_template('security_dashboard.html', data={
            'error': 'Error al cargar datos de seguridad',
            'security_score': {'score': 0, 'level': 'Unknown'}
        })

@vistasecurity.route('/api/security-stats')
@login_required
def api_security_stats():
    """API para obtener estadísticas de seguridad en tiempo real"""
    try:
        security_stats = get_security_stats()
        
        rate_limit_stats = {
            'blocked_ips': len(rate_limiter.blocked_ips),
            'blocked_users': len(rate_limiter.blocked_users),
            'active_attempts': sum(len(attempts) for attempts in rate_limiter.attempts.values())
        }
        
        security_score = calculate_security_score(security_stats, rate_limit_stats)
        
        return jsonify({
            'success': True,
            'data': {
                'security_stats': security_stats,
                'rate_limit_stats': rate_limit_stats,
                'security_score': security_score,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

def calculate_security_score(security_stats, rate_limit_stats):
    """
    Calcula un score de seguridad basado en las estadísticas
    """
    try:
        score = 100  # Empezar con score perfecto
        
        # Penalizar por eventos de seguridad
        failed_logins = security_stats.get('failed_logins', 0)
        blocked_attempts = security_stats.get('blocked_attempts', 0)
        csrf_attacks = security_stats.get('csrf_attacks', 0)
        xss_attempts = security_stats.get('xss_attempts', 0)
        sql_injection_attempts = security_stats.get('sql_injection_attempts', 0)
        
        # Calcular penalizaciones
        if failed_logins > 10:
            score -= min(20, failed_logins * 0.5)
        
        if blocked_attempts > 0:
            score -= min(15, blocked_attempts * 2)
        
        if csrf_attacks > 0:
            score -= min(25, csrf_attacks * 5)
        
        if xss_attempts > 0:
            score -= min(20, xss_attempts * 3)
        
        if sql_injection_attempts > 0:
            score -= min(30, sql_injection_attempts * 10)
        
        # Penalizar por rate limiting activo
        if rate_limit_stats['blocked_ips'] > 0:
            score -= min(10, rate_limit_stats['blocked_ips'] * 2)
        
        if rate_limit_stats['blocked_users'] > 0:
            score -= min(10, rate_limit_stats['blocked_users'] * 2)
        
        # Asegurar que el score esté entre 0 y 100
        score = max(0, min(100, score))
        
        # Determinar nivel de seguridad
        if score >= 90:
            level = 'Excelente'
            color = 'success'
        elif score >= 75:
            level = 'Bueno'
            color = 'info'
        elif score >= 60:
            level = 'Regular'
            color = 'warning'
        else:
            level = 'Crítico'
            color = 'danger'
        
        return {
            'score': round(score, 1),
            'level': level,
            'color': color
        }
        
    except Exception as e:
        print(f"Error calculando security score: {e}")
        return {
            'score': 0,
            'level': 'Error',
            'color': 'secondary'
        }

@vistasecurity.route('/api/security-alerts')
@login_required
def api_security_alerts():
    """API para obtener alertas de seguridad activas"""
    try:
        alerts = []
        
        # Verificar IPs bloqueadas
        if len(rate_limiter.blocked_ips) > 0:
            alerts.append({
                'type': 'warning',
                'title': 'IPs Bloqueadas',
                'message': f'{len(rate_limiter.blocked_ips)} IP(s) están bloqueadas por intentos excesivos',
                'timestamp': datetime.now().isoformat()
            })
        
        # Verificar usuarios bloqueados
        if len(rate_limiter.blocked_users) > 0:
            alerts.append({
                'type': 'warning',
                'title': 'Usuarios Bloqueados',
                'message': f'{len(rate_limiter.blocked_users)} usuario(s) están bloqueados por intentos fallidos',
                'timestamp': datetime.now().isoformat()
            })
        
        # Verificar estadísticas de seguridad
        security_stats = get_security_stats()
        
        if security_stats.get('csrf_attacks', 0) > 0:
            alerts.append({
                'type': 'danger',
                'title': 'Ataques CSRF Detectados',
                'message': f'{security_stats["csrf_attacks"]} intento(s) de ataque CSRF detectados',
                'timestamp': datetime.now().isoformat()
            })
        
        if security_stats.get('xss_attempts', 0) > 0:
            alerts.append({
                'type': 'danger',
                'title': 'Intentos XSS Detectados',
                'message': f'{security_stats["xss_attempts"]} intento(s) de ataque XSS detectados',
                'timestamp': datetime.now().isoformat()
            })
        
        if security_stats.get('sql_injection_attempts', 0) > 0:
            alerts.append({
                'type': 'danger',
                'title': 'Intentos SQL Injection',
                'message': f'{security_stats["sql_injection_attempts"]} intento(s) de SQL injection detectados',
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'alerts': [],
            'count': 0
        })