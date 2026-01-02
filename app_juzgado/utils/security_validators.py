"""
Validadores de seguridad para inputs del usuario
"""

import re
import html
from typing import Optional, Dict, Any

class SecurityValidator:
    """Validador de seguridad para inputs del usuario"""
    
    # Patrones de validación
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,50}$')
    NAME_PATTERN = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]{2,100}$')
    RADICADO_PATTERN = re.compile(r'^[0-9]{23}$')
    
    # Caracteres peligrosos para XSS
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
    ]
    
    @staticmethod
    def sanitize_input(value: str) -> str:
        """
        Sanitiza input del usuario para prevenir XSS
        """
        if not value:
            return ""
        
        # Escapar HTML
        sanitized = html.escape(value.strip())
        
        # Remover patrones peligrosos
        for pattern in SecurityValidator.XSS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, Any]:
        """Valida formato de email"""
        if not email:
            return {"valid": False, "error": "Email es requerido"}
        
        email = email.strip().lower()
        
        if len(email) > 254:
            return {"valid": False, "error": "Email demasiado largo"}
        
        if not SecurityValidator.EMAIL_PATTERN.match(email):
            return {"valid": False, "error": "Formato de email inválido"}
        
        return {"valid": True, "sanitized": email}
    
    @staticmethod
    def validate_username(username: str) -> Dict[str, Any]:
        """Valida nombre de usuario"""
        if not username:
            return {"valid": False, "error": "Usuario es requerido"}
        
        username = username.strip()
        
        if len(username) < 3:
            return {"valid": False, "error": "Usuario debe tener al menos 3 caracteres"}
        
        if len(username) > 50:
            return {"valid": False, "error": "Usuario demasiado largo"}
        
        if not SecurityValidator.USERNAME_PATTERN.match(username):
            return {"valid": False, "error": "Usuario solo puede contener letras, números y guiones bajos"}
        
        return {"valid": True, "sanitized": username}
    
    @staticmethod
    def validate_name(name: str) -> Dict[str, Any]:
        """Valida nombre completo"""
        if not name:
            return {"valid": False, "error": "Nombre es requerido"}
        
        name = name.strip()
        
        if len(name) < 2:
            return {"valid": False, "error": "Nombre debe tener al menos 2 caracteres"}
        
        if len(name) > 100:
            return {"valid": False, "error": "Nombre demasiado largo"}
        
        if not SecurityValidator.NAME_PATTERN.match(name):
            return {"valid": False, "error": "Nombre contiene caracteres inválidos"}
        
        return {"valid": True, "sanitized": SecurityValidator.sanitize_input(name)}
    
    @staticmethod
    def validate_radicado(radicado: str) -> Dict[str, Any]:
        """Valida formato de radicado"""
        if not radicado:
            return {"valid": False, "error": "Radicado es requerido"}
        
        radicado = radicado.strip()
        
        if not SecurityValidator.RADICADO_PATTERN.match(radicado):
            return {"valid": False, "error": "Radicado debe tener exactamente 23 dígitos"}
        
        return {"valid": True, "sanitized": radicado}
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Valida fortaleza de contraseña"""
        if not password:
            return {"valid": False, "error": "Contraseña es requerida"}
        
        if len(password) < 8:
            return {"valid": False, "error": "Contraseña debe tener al menos 8 caracteres"}
        
        if len(password) > 128:
            return {"valid": False, "error": "Contraseña demasiado larga"}
        
        # Verificar complejidad
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        strength_score = sum([has_upper, has_lower, has_digit, has_special])
        
        if strength_score < 3:
            return {
                "valid": False, 
                "error": "Contraseña debe contener al menos 3 de: mayúsculas, minúsculas, números, símbolos"
            }
        
        return {"valid": True, "strength": strength_score}
    
    @staticmethod
    def validate_form_data(data: Dict[str, str], required_fields: list) -> Dict[str, Any]:
        """
        Valida datos de formulario completo
        """
        errors = {}
        sanitized_data = {}
        
        # Verificar campos requeridos
        for field in required_fields:
            if field not in data or not data[field].strip():
                errors[field] = f"{field} es requerido"
        
        # Validar y sanitizar cada campo
        for field, value in data.items():
            if not value:
                continue
                
            # Sanitizar input básico
            sanitized_value = SecurityValidator.sanitize_input(value)
            
            # Validaciones específicas por campo
            if field in ['email', 'correo']:
                validation = SecurityValidator.validate_email(value)
                if not validation['valid']:
                    errors[field] = validation['error']
                else:
                    sanitized_data[field] = validation['sanitized']
            
            elif field in ['username', 'usuario']:
                validation = SecurityValidator.validate_username(value)
                if not validation['valid']:
                    errors[field] = validation['error']
                else:
                    sanitized_data[field] = validation['sanitized']
            
            elif field in ['name', 'nombre', 'nombre_completo']:
                validation = SecurityValidator.validate_name(value)
                if not validation['valid']:
                    errors[field] = validation['error']
                else:
                    sanitized_data[field] = validation['sanitized']
            
            elif field in ['password', 'contrasena', 'nueva_password']:
                validation = SecurityValidator.validate_password_strength(value)
                if not validation['valid']:
                    errors[field] = validation['error']
                else:
                    sanitized_data[field] = value  # No sanitizar passwords
            
            elif field in ['radicado_completo', 'radicado']:
                validation = SecurityValidator.validate_radicado(value)
                if not validation['valid']:
                    errors[field] = validation['error']
                else:
                    sanitized_data[field] = validation['sanitized']
            
            else:
                # Sanitización general para otros campos
                sanitized_data[field] = sanitized_value
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "sanitized_data": sanitized_data
        }

# Decorador para validar formularios
def validate_form(required_fields: list):
    """
    Decorador para validar formularios automáticamente
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request, flash, redirect, url_for
            
            if request.method == 'POST':
                validation = SecurityValidator.validate_form_data(
                    request.form.to_dict(), 
                    required_fields
                )
                
                if not validation['valid']:
                    for field, error in validation['errors'].items():
                        flash(f"Error en {field}: {error}", 'error')
                    return redirect(request.url)
                
                # Agregar datos sanitizados al request
                request.sanitized_data = validation['sanitized_data']
            
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator