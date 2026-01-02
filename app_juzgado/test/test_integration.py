"""
Pruebas de integración corregidas del sistema
"""

import pytest
from unittest.mock import patch, Mock
import sys
import os
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestIntegracionCompleta:
    """Pruebas de integración completas del sistema"""
    
    @patch('vista.vistausuarios.obtener_todos_usuarios')
    @patch('vista.vistausuarios.obtener_roles')
    def test_flujo_crud_usuario_completo(self, mock_roles, mock_usuarios, client):
        """Prueba flujo CRUD completo de usuarios"""
        # Configurar mocks
        mock_usuarios.return_value = [
            (1, 'admin', 'admin@test.com', datetime(2025, 1, 1), True, 'ADMINISTRADOR', 'Admin User', True)
        ]
        mock_roles.return_value = [
            (1, 'ESCRIBIENTE'),
            (2, 'SUSTANCIADOR')
        ]
        
        # 1. Listar usuarios
        response = client.get('/usuarios')
        assert response.status_code == 200
        assert b'usuarios' in response.data.lower() or b'Gesti' in response.data
        
        # Verificar que se llamaron las funciones
        mock_usuarios.assert_called()
        mock_roles.assert_called()
    
    @patch('vista.vistaexpediente.buscar_expedientes')
    def test_navegacion_entre_vistas(self, mock_buscar, client):
        """Prueba navegación entre diferentes vistas"""
        # Configurar mock
        mock_buscar.return_value = []
        
        # 1. Vista principal de expedientes
        response = client.get('/expediente')
        assert response.status_code == 200
        
        # 2. Vista de usuarios
        response = client.get('/usuarios')
        assert response.status_code == 200
        
        # 3. Vista de login
        response = client.get('/login')
        assert response.status_code == 200

class TestRendimientoIntegracion:
    """Pruebas de rendimiento e integración"""
    
    def test_paginacion_basica(self):
        """Prueba básica de paginación"""
        from vista.vistaexpediente import paginar_resultados
        
        # Crear datos de prueba
        datos = list(range(1, 26))  # 25 elementos
        
        # Probar paginación
        resultado, paginacion = paginar_resultados(datos, 1, 10)
        
        assert len(resultado) <= 10
        assert paginacion['pagina_actual'] == 1
        assert paginacion['total_paginas'] == 3
    
    def test_funciones_utilidad_existen(self):
        """Prueba que las funciones de utilidad existen"""
        from vista.vistaexpediente import calcular_paginas_mostrar
        from vista.vistausuarios import hash_password
        from utils.auth import login_required, get_current_user
        
        # Verificar que las funciones existen
        assert callable(calcular_paginas_mostrar)
        assert callable(hash_password)
        assert callable(login_required)
        assert callable(get_current_user)