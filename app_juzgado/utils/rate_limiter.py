"""
Rate Limiter para prevenir ataques de fuerza bruta
"""

import time
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, flash, redirect, url_for
from typing import Dict, Tuple

class RateLimiter:
    """
    Rate limiter simple basado en memoria
    Para producción, usar Redis o similar
    """
    
    def __init__(self):
        # Almacenar intentos por IP
        self.attempts = defaultdict(deque)
        # Almacenar bloqueos temporales
        self.blocked_ips = {}
        # Almacenar intentos de login por usuario
        self.login_attempts = defaultdict(deque)
        self.blocked_users = {}
    
    def is_rate_limited(self, key: str, max_attempts: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Verifica si una clave está limitada por rate limiting
        
        Returns:
            (is_limited, remaining_attempts)
        """
        now = time.time()
        
        # Limpiar intentos antiguos
        while self.attempts[key] and self.attempts[key][0] < now - window_seconds:
            self.attempts[key].popleft()
        
        current_attempts = len(self.attempts[key])
        
        if current_attempts >= max_attempts:
            return True, 0
        
        return False, max_attempts - current_attempts
    
    def record_attempt(self, key: str):
        """Registra un intento"""
        self.attempts[key].append(time.time())
    
    def is_ip_blocked(self, ip: str) -> Tuple[bool, int]:
        """Verifica si una IP está bloqueada"""
        if ip in self.blocked_ips:
            block_until = self.blocked_ips[ip]
            if time.time() < block_until:
                return True, int(block_until - time.time())
            else:
                # Bloqueo expirado
                del self.blocked_ips[ip]
        
        return False, 0
    
    def block_ip(self, ip: str, duration_seconds: int):
        """Bloquea una IP temporalmente"""
        self.blocked_ips[ip] = time.time() + duration_seconds
    
    def is_user_blocked(self, username: str) -> Tuple[bool, int]:
        """Verifica si un usuario está bloqueado"""
        if username in self.blocked_users:
            block_until = self.blocked_users[username]
            if time.time() < block_until:
                return True, int(block_until - time.time())
            else:
                # Bloqueo expirado
                del self.blocked_users[username]
        
        return False, 0
    
    def block_user(self, username: str, duration_seconds: int):
        """Bloquea un usuario temporalmente"""
        self.blocked_users[username] = time.time() + duration_seconds
    
    def record_failed_login(self, username: str, ip: str):
        """Registra un intento de login fallido"""
        now = time.time()
        
        # Limpiar intentos antiguos (últimos 15 minutos)
        while (self.login_attempts[username] and 
               self.login_attempts[username][0] < now - 900):
            self.login_attempts[username].popleft()
        
        # Registrar intento
        self.login_attempts[username].append(now)
        
        # Verificar si debe bloquearse
        attempts_count = len(self.login_attempts[username])
        
        if attempts_count >= 5:  # 5 intentos fallidos
            # Bloquear usuario por 15 minutos
            self.block_user(username, 900)
            # Bloquear IP por 5 minutos
            self.block_ip(ip, 300)
    
    def clear_user_attempts(self, username: str):
        """Limpia intentos de un usuario (login exitoso)"""
        if username in self.login_attempts:
            self.login_attempts[username].clear()

# Instancia global del rate limiter
rate_limiter = RateLimiter()

def rate_limit(max_attempts: int = 10, window_seconds: int = 60, block_duration: int = 300):
    """
    Decorador para rate limiting
    
    Args:
        max_attempts: Máximo número de intentos
        window_seconds: Ventana de tiempo en segundos
        block_duration: Duración del bloqueo en segundos
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            # Verificar si la IP está bloqueada
            is_blocked, remaining_time = rate_limiter.is_ip_blocked(client_ip)
            if is_blocked:
                flash(f'IP bloqueada. Intente nuevamente en {remaining_time} segundos.', 'error')
                return redirect(url_for('idvistalogin.vista_login'))
            
            # Verificar rate limiting
            is_limited, remaining = rate_limiter.is_rate_limited(
                client_ip, max_attempts, window_seconds
            )
            
            if is_limited:
                # Bloquear IP
                rate_limiter.block_ip(client_ip, block_duration)
                flash('Demasiados intentos. IP bloqueada temporalmente.', 'error')
                return redirect(url_for('idvistalogin.vista_login'))
            
            # Registrar intento
            rate_limiter.record_attempt(client_ip)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def login_rate_limit(func):
    """
    Rate limiter específico para login
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method == 'POST':
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            username = request.form.get('username', '').lower().strip()
            
            # Verificar si la IP está bloqueada
            is_ip_blocked, ip_remaining = rate_limiter.is_ip_blocked(client_ip)
            if is_ip_blocked:
                flash(f'IP bloqueada. Intente nuevamente en {ip_remaining} segundos.', 'error')
                return redirect(url_for('idvistalogin.vista_login'))
            
            # Verificar si el usuario está bloqueado
            if username:
                is_user_blocked, user_remaining = rate_limiter.is_user_blocked(username)
                if is_user_blocked:
                    flash(f'Usuario bloqueado. Intente nuevamente en {user_remaining} segundos.', 'error')
                    return redirect(url_for('idvistalogin.vista_login'))
        
        return func(*args, **kwargs)
    
    return wrapper

def record_failed_login_attempt(username: str):
    """Registra un intento de login fallido"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    rate_limiter.record_failed_login(username, client_ip)

def clear_login_attempts(username: str):
    """Limpia intentos de login (login exitoso)"""
    rate_limiter.clear_user_attempts(username)