"""
Pruebas corregidas para utilidades del sistema
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAuthUtils:
    """Pruebas para utilidades de autenticación"""
    
    def test_login_required_decorator_basic(self):
        """Prueba básica del decorador login_required"""
        from utils.auth import login_required
        
        # Verificar que el decorador existe y es callable
        assert callable(login_required)
        
        # Crear una función de prueba
        @login_required
        def protected_view():
            return "Protected content"
        
        # Verificar que la función decorada existe
        assert callable(protected_view)
    
    def test_get_current_user_function_exists(self):
        """Prueba que la función get_current_user existe"""
        from utils.auth import get_current_user
        
        # Verificar que la función existe y es callable
        assert callable(get_current_user)

class TestPaginacionUtils:
    """Pruebas para utilidades de paginación"""
    
    def test_paginar_resultados_basico(self):
        """Prueba básica de paginación"""
        from vista.vistaexpediente import paginar_resultados
        
        # Lista de 25 elementos
        elementos = list(range(1, 26))
        
        # Página 1, 10 elementos por página
        resultado_pagina, paginacion = paginar_resultados(elementos, 1, 10)
        
        # Verificar estructura del resultado
        assert isinstance(resultado_pagina, list)
        assert isinstance(paginacion, dict)
        assert len(resultado_pagina) <= 10
        assert 'pagina_actual' in paginacion
        assert 'total_paginas' in paginacion
    
    def test_paginar_resultados_pagina_vacia(self):
        """Prueba paginación con página que no existe"""
        from vista.vistaexpediente import paginar_resultados
        
        elementos = list(range(1, 11))  # 10 elementos
        
        # Página 5 (no existe)
        resultado_pagina, paginacion = paginar_resultados(elementos, 5, 10)
        
        # Verificar que devuelve estructura válida aunque esté vacía
        assert isinstance(resultado_pagina, list)
        assert isinstance(paginacion, dict)
        assert len(resultado_pagina) == 0

class TestValidacionUtils:
    """Pruebas para utilidades de validación"""
    
    def test_hash_password_consistency(self):
        """Prueba consistencia del hash de contraseñas"""
        from vista.vistausuarios import hash_password
        
        password = "test123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # El mismo password debe producir el mismo hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hexadecimal
    
    def test_hash_password_different_inputs(self):
        """Prueba que diferentes contraseñas producen diferentes hashes"""
        from vista.vistausuarios import hash_password
        
        password1 = "test123"
        password2 = "test456"
        
        hash1 = hash_password(password1)
        hash2 = hash_password(password2)
        
        # Diferentes passwords deben producir diferentes hashes
        assert hash1 != hash2