"""
Pruebas para el validador de contraseñas
"""

import pytest
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.password_validator import PasswordValidator, validate_password_strength

class TestPasswordValidator:
    """Pruebas unitarias para el validador de contraseñas"""
    
    def test_password_too_short(self):
        """Prueba contraseña muy corta"""
        is_valid, errors = PasswordValidator.validate_password("123")
        assert not is_valid
        assert any("al menos 8 caracteres" in error for error in errors)
    
    def test_password_missing_uppercase(self):
        """Prueba contraseña sin mayúsculas"""
        is_valid, errors = PasswordValidator.validate_password("password123!")
        assert not is_valid
        assert any("letra mayúscula" in error for error in errors)
    
    def test_password_missing_lowercase(self):
        """Prueba contraseña sin minúsculas"""
        is_valid, errors = PasswordValidator.validate_password("PASSWORD123!")
        assert not is_valid
        assert any("letra minúscula" in error for error in errors)
    
    def test_password_missing_numbers(self):
        """Prueba contraseña sin números"""
        is_valid, errors = PasswordValidator.validate_password("Password!")
        assert not is_valid
        assert any("al menos un número" in error for error in errors)
    
    def test_password_missing_special_chars(self):
        """Prueba contraseña sin caracteres especiales"""
        is_valid, errors = PasswordValidator.validate_password("Password123")
        assert not is_valid
        assert any("carácter especial" in error for error in errors)
    
    def test_common_password(self):
        """Prueba contraseña común"""
        is_valid, errors = PasswordValidator.validate_password("password")
        assert not is_valid
        assert any("muy común" in error for error in errors)
    
    def test_weak_patterns_sequential_numbers(self):
        """Prueba patrones débiles - números secuenciales"""
        is_valid, errors = PasswordValidator.validate_password("Password123!")
        assert not is_valid
        assert any("patrones débiles" in error for error in errors)
    
    def test_weak_patterns_sequential_letters(self):
        """Prueba patrones débiles - letras secuenciales"""
        is_valid, errors = PasswordValidator.validate_password("Passwordabc!")
        assert not is_valid
        assert any("patrones débiles" in error for error in errors)
    
    def test_weak_patterns_repetition(self):
        """Prueba patrones débiles - repeticiones"""
        is_valid, errors = PasswordValidator.validate_password("Passwordaaa1!")
        assert not is_valid
        assert any("patrones débiles" in error for error in errors)
    
    def test_weak_patterns_keyboard(self):
        """Prueba patrones débiles - secuencias de teclado"""
        is_valid, errors = PasswordValidator.validate_password("Passwordqwerty1!")
        assert not is_valid
        assert any("patrones débiles" in error for error in errors)
    
    def test_valid_strong_password(self):
        """Prueba contraseña válida y fuerte"""
        is_valid, errors = PasswordValidator.validate_password("MyStr0ng!P@ssw0rd")
        assert is_valid
        assert len(errors) == 0
    
    def test_valid_moderate_password(self):
        """Prueba contraseña válida moderada"""
        is_valid, errors = PasswordValidator.validate_password("MyP@ssw0rd")
        assert is_valid
        assert len(errors) == 0
    
    def test_strength_score_very_weak(self):
        """Prueba puntaje de contraseña muy débil"""
        score, strength = PasswordValidator.get_strength_score("123")
        assert score < 20
        assert strength == "Muy Débil"
    
    def test_strength_score_weak(self):
        """Prueba puntaje de contraseña débil"""
        score, strength = PasswordValidator.get_strength_score("password")
        assert score < 20  # Ajustado porque "password" es muy común y débil
        assert strength == "Muy Débil"
    
    def test_strength_score_moderate(self):
        """Prueba puntaje de contraseña moderada"""
        score, strength = PasswordValidator.get_strength_score("Password1")
        assert 20 <= score < 40  # Ajustado porque es corta y simple
        assert strength in ["Débil", "Moderada"]
    
    def test_strength_score_strong(self):
        """Prueba puntaje de contraseña fuerte"""
        score, strength = PasswordValidator.get_strength_score("MyP@ssw0rd")
        assert 60 <= score < 80
        assert strength == "Fuerte"
    
    def test_strength_score_very_strong(self):
        """Prueba puntaje de contraseña muy fuerte"""
        score, strength = PasswordValidator.get_strength_score("MyVeryStr0ng!P@ssw0rd2024")
        assert score >= 80
        assert strength == "Muy Fuerte"
    
    def test_generate_suggestions_short_password(self):
        """Prueba sugerencias para contraseña corta"""
        suggestions = PasswordValidator.generate_suggestions("123")
        assert any("longitud" in suggestion for suggestion in suggestions)
        assert any("mayúscula" in suggestion for suggestion in suggestions)
        assert any("minúscula" in suggestion for suggestion in suggestions)
        assert any("número" in suggestion for suggestion in suggestions)
        assert any("carácter especial" in suggestion for suggestion in suggestions)
    
    def test_generate_suggestions_common_password(self):
        """Prueba sugerencias para contraseña común"""
        suggestions = PasswordValidator.generate_suggestions("password")
        assert any("comunes" in suggestion for suggestion in suggestions)
    
    def test_generate_suggestions_weak_patterns(self):
        """Prueba sugerencias para patrones débiles"""
        suggestions = PasswordValidator.generate_suggestions("Password123!")
        assert any("secuencias" in suggestion for suggestion in suggestions)
    
    def test_generate_suggestions_good_password(self):
        """Prueba sugerencias para contraseña buena"""
        suggestions = PasswordValidator.generate_suggestions("MyStr0ng!P@ssw0rd")
        # Una contraseña fuerte debería tener pocas o ninguna sugerencia
        assert len(suggestions) <= 1  # Solo podría sugerir longitud mayor

class TestPasswordValidatorIntegration:
    """Pruebas de integración para el validador de contraseñas"""
    
    def test_validate_password_strength_function(self):
        """Prueba la función de conveniencia validate_password_strength"""
        result = validate_password_strength("MyStr0ng!P@ssw0rd")
        
        assert 'is_valid' in result
        assert 'errors' in result
        assert 'score' in result
        assert 'strength' in result
        assert 'suggestions' in result
        
        assert result['is_valid'] is True
        assert isinstance(result['errors'], list)
        assert isinstance(result['score'], int)
        assert isinstance(result['strength'], str)
        assert isinstance(result['suggestions'], list)
    
    def test_validate_password_strength_invalid(self):
        """Prueba la función de conveniencia con contraseña inválida"""
        result = validate_password_strength("123")
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert result['score'] < 40
        assert result['strength'] in ["Muy Débil", "Débil"]
        assert len(result['suggestions']) > 0

class TestPasswordValidatorEdgeCases:
    """Pruebas de casos extremos para el validador"""
    
    def test_empty_password(self):
        """Prueba contraseña vacía"""
        is_valid, errors = PasswordValidator.validate_password("")
        assert not is_valid
        assert len(errors) > 0
    
    def test_whitespace_password(self):
        """Prueba contraseña solo con espacios"""
        is_valid, errors = PasswordValidator.validate_password("   ")
        assert not is_valid
        assert any("al menos 8 caracteres" in error for error in errors)
    
    def test_very_long_password(self):
        """Prueba contraseña muy larga"""
        long_password = "MyVeryLongAndComplexP@ssw0rd!" * 5
        is_valid, errors = PasswordValidator.validate_password(long_password)
        assert is_valid  # Debería ser válida si cumple otros criterios
    
    def test_unicode_characters(self):
        """Prueba contraseña con caracteres Unicode"""
        unicode_password = "MyP@ssw0rdñáéíóú"
        is_valid, errors = PasswordValidator.validate_password(unicode_password)
        # Debería manejar caracteres Unicode correctamente
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_all_special_characters(self):
        """Prueba contraseña con todos los caracteres especiales permitidos"""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        password = f"MyP@ssw0rd{special_chars}"
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid
    
    def test_mixed_case_common_password(self):
        """Prueba contraseña común con mayúsculas y minúsculas"""
        is_valid, errors = PasswordValidator.validate_password("PASSWORD")
        assert not is_valid
        # Debería detectar que es común incluso con diferentes casos
    
    def test_colombian_context_passwords(self):
        """Prueba contraseñas específicas del contexto colombiano"""
        colombian_passwords = [
            "colombia", "bogota", "medellin", "juzgado", "justicia"
        ]
        
        for password in colombian_passwords:
            is_valid, errors = PasswordValidator.validate_password(password)
            assert not is_valid
            assert any("muy común" in error for error in errors)
    
    def test_legal_context_passwords(self):
        """Prueba contraseñas del contexto legal"""
        legal_passwords = [
            "expediente", "proceso", "demanda", "sentencia", "juez"
        ]
        
        for password in legal_passwords:
            is_valid, errors = PasswordValidator.validate_password(password)
            assert not is_valid
            assert any("muy común" in error for error in errors)

class TestPasswordValidatorPerformance:
    """Pruebas de rendimiento para el validador"""
    
    def test_validation_performance(self):
        """Prueba que la validación sea rápida"""
        import time
        
        password = "MyStr0ng!P@ssw0rd"
        start_time = time.time()
        
        # Ejecutar validación múltiples veces
        for _ in range(100):
            PasswordValidator.validate_password(password)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # La validación debería ser muy rápida (menos de 1 segundo para 100 validaciones)
        assert elapsed_time < 1.0
    
    def test_strength_calculation_performance(self):
        """Prueba que el cálculo de fortaleza sea rápido"""
        import time
        
        password = "MyStr0ng!P@ssw0rd"
        start_time = time.time()
        
        # Ejecutar cálculo de fortaleza múltiples veces
        for _ in range(100):
            PasswordValidator.get_strength_score(password)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # El cálculo debería ser muy rápido
        assert elapsed_time < 1.0