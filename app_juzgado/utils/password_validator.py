#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de contraseñas con parámetros de seguridad
"""

import re
from typing import List, Tuple

class PasswordValidator:
    """Validador de contraseñas con reglas de seguridad"""
    
    # Configuración de validación
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL_CHARS = True
    
    # Lista de contraseñas comunes a evitar
    COMMON_PASSWORDS = {
        '123456', 'password', '123456789', '12345678', '12345', '1234567', 
        '1234567890', 'qwerty', 'abc123', 'million2', '000000', '1234',
        'iloveyou', 'aaron431', 'password1', 'qqww1122', '123123', 'omgpop',
        '123321', '654321', 'qwertyuiop', 'qwer1234', '123abc', 'Password',
        'admin', 'administrator', 'root', 'user', 'guest', 'test', 'demo',
        'welcome', 'login', 'pass', 'secret', 'master', 'super', 'default',
        'colombia', 'bogota', 'medellin', 'cali', 'barranquilla', 'cartagena',
        'bucaramanga', 'pereira', 'manizales', 'ibague', 'cucuta', 'villavicencio',
        'juzgado', 'justicia', 'derecho', 'abogado', 'tribunal', 'corte',
        'expediente', 'proceso', 'demanda', 'sentencia', 'juez', 'magistrado'
    }
    
    @classmethod
    def validate_password(cls, password: str) -> Tuple[bool, List[str]]:
        """
        Valida una contraseña según los criterios establecidos
        
        Args:
            password (str): Contraseña a validar
            
        Returns:
            Tuple[bool, List[str]]: (es_valida, lista_de_errores)
        """
        errors = []
        
        # 1. Verificar longitud mínima
        if len(password) < cls.MIN_LENGTH:
            errors.append(f'La contraseña debe tener al menos {cls.MIN_LENGTH} caracteres')
        
        # 2. Verificar complejidad básica
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append('La contraseña debe contener al menos una letra mayúscula')
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append('La contraseña debe contener al menos una letra minúscula')
        
        if cls.REQUIRE_NUMBERS and not re.search(r'\d', password):
            errors.append('La contraseña debe contener al menos un número')
        
        if cls.REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            errors.append('La contraseña debe contener al menos un carácter especial (!@#$%^&*()_+-=[]{}|;:,.<>?)')
        
        # 3. Verificar que no sea una contraseña común
        if password.lower() in cls.COMMON_PASSWORDS:
            errors.append('Esta contraseña es muy común y no es segura. Por favor elija una contraseña más única')
        
        # 4. Verificar patrones débiles adicionales
        if cls._has_weak_patterns(password):
            errors.append('La contraseña contiene patrones débiles (secuencias, repeticiones). Use una combinación más variada')
        
        return len(errors) == 0, errors
    
    @classmethod
    def _has_weak_patterns(cls, password: str) -> bool:
        """Detecta patrones débiles en la contraseña"""
        
        # Verificar secuencias numéricas (123, 456, etc.)
        for i in range(len(password) - 2):
            if password[i:i+3].isdigit():
                nums = [int(password[i+j]) for j in range(3)]
                if nums[1] == nums[0] + 1 and nums[2] == nums[1] + 1:
                    return True
                if nums[1] == nums[0] - 1 and nums[2] == nums[1] - 1:
                    return True
        
        # Verificar secuencias alfabéticas (abc, xyz, etc.)
        for i in range(len(password) - 2):
            if password[i:i+3].isalpha():
                chars = password[i:i+3].lower()
                if ord(chars[1]) == ord(chars[0]) + 1 and ord(chars[2]) == ord(chars[1]) + 1:
                    return True
                if ord(chars[1]) == ord(chars[0]) - 1 and ord(chars[2]) == ord(chars[1]) - 1:
                    return True
        
        # Verificar repeticiones excesivas (aaa, 111, etc.)
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True
        
        # Verificar patrones de teclado (qwerty, asdf, etc.)
        keyboard_patterns = ['qwerty', 'asdf', 'zxcv', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm']
        password_lower = password.lower()
        for pattern in keyboard_patterns:
            if pattern in password_lower or pattern[::-1] in password_lower:
                return True
        
        return False
    
    @classmethod
    def get_strength_score(cls, password: str) -> Tuple[int, str]:
        """
        Calcula un puntaje de fortaleza de la contraseña
        
        Args:
            password (str): Contraseña a evaluar
            
        Returns:
            Tuple[int, str]: (puntaje_0_100, descripcion_fortaleza)
        """
        score = 0
        
        # Longitud (hasta 25 puntos)
        if len(password) >= 8:
            score += min(25, len(password) * 2)
        
        # Variedad de caracteres (hasta 40 puntos)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            score += 10
        
        # Complejidad adicional (hasta 35 puntos)
        unique_chars = len(set(password))
        score += min(15, unique_chars)
        
        # Penalizar patrones débiles
        if cls._has_weak_patterns(password):
            score -= 20
        
        # Penalizar contraseñas comunes
        if password.lower() in cls.COMMON_PASSWORDS:
            score -= 30
        
        # Bonificación por longitud extra
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        score = max(0, min(100, score))
        
        # Determinar descripción
        if score >= 80:
            strength = "Muy Fuerte"
        elif score >= 60:
            strength = "Fuerte"
        elif score >= 40:
            strength = "Moderada"
        elif score >= 20:
            strength = "Débil"
        else:
            strength = "Muy Débil"
        
        return score, strength
    
    @classmethod
    def generate_suggestions(cls, password: str) -> List[str]:
        """
        Genera sugerencias para mejorar la contraseña
        
        Args:
            password (str): Contraseña a evaluar
            
        Returns:
            List[str]: Lista de sugerencias
        """
        suggestions = []
        
        if len(password) < cls.MIN_LENGTH:
            suggestions.append(f"Aumenta la longitud a al menos {cls.MIN_LENGTH} caracteres")
        
        if not re.search(r'[A-Z]', password):
            suggestions.append("Agrega al menos una letra mayúscula")
        
        if not re.search(r'[a-z]', password):
            suggestions.append("Agrega al menos una letra minúscula")
        
        if not re.search(r'\d', password):
            suggestions.append("Agrega al menos un número")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            suggestions.append("Agrega al menos un carácter especial")
        
        if password.lower() in cls.COMMON_PASSWORDS:
            suggestions.append("Evita contraseñas comunes, usa una combinación más única")
        
        if cls._has_weak_patterns(password):
            suggestions.append("Evita secuencias y repeticiones, varía más los caracteres")
        
        if len(password) < 12:
            suggestions.append("Considera usar una contraseña más larga (12+ caracteres) para mayor seguridad")
        
        return suggestions

def validate_password_strength(password: str) -> dict:
    """
    Función de conveniencia para validar contraseña y obtener información completa
    
    Args:
        password (str): Contraseña a validar
        
    Returns:
        dict: Información completa de validación
    """
    is_valid, errors = PasswordValidator.validate_password(password)
    score, strength = PasswordValidator.get_strength_score(password)
    suggestions = PasswordValidator.generate_suggestions(password)
    
    return {
        'is_valid': is_valid,
        'errors': errors,
        'score': score,
        'strength': strength,
        'suggestions': suggestions
    }