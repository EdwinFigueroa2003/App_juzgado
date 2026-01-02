#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades de autenticación para el sistema
"""

from functools import wraps
from flask import session, redirect, url_for, flash
import hashlib
from .password_validator import PasswordValidator, validate_password_strength

def login_required(f):
    """Decorador para requerir login en las rutas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Debe iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('idvistalogin.vista_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Obtiene la información del usuario actual de la sesión"""
    if session.get('logged_in'):
        return {
            'id': session.get('user_id'),
            'usuario': session.get('usuario'),
            'correo': session.get('correo'),
            'nombre': session.get('nombre')
        }
    return None

def hash_password(password):
    """Función mejorada para hashear contraseñas"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password):
    """
    Valida una contraseña según los criterios de seguridad establecidos
    
    Args:
        password (str): Contraseña a validar
        
    Returns:
        dict: Información de validación con is_valid, errors, score, strength, suggestions
    """
    return validate_password_strength(password)

def check_password_strength(password):
    """
    Verifica la fortaleza de una contraseña
    
    Args:
        password (str): Contraseña a verificar
        
    Returns:
        tuple: (score, strength_description)
    """
    return PasswordValidator.get_strength_score(password)

def is_admin():
    """
    Verifica si el usuario actual es administrador
    
    Returns:
        bool: True si el usuario es administrador, False en caso contrario
    """
    return session.get('administrador', False)

def admin_required(f):
    """Decorador para requerir permisos de administrador en las rutas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Debe iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('idvistalogin.vista_login'))
        
        if not session.get('administrador', False):
            flash('No tiene permisos para acceder a esta página', 'error')
            return redirect(url_for('idvistahome.vista_home'))
        
        return f(*args, **kwargs)
    return decorated_function