"""
Pruebas específicas para la funcionalidad de búsqueda de usuarios
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestSearchFunctionality:
    """Pruebas para la funcionalidad de búsqueda"""
    
    def test_search_javascript_functions_exist(self):
        """Verificar que las funciones de búsqueda existen en el JavaScript"""
        js_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'js', 'base.js'
        )
        
        assert os.path.exists(js_file_path), "El archivo base.js debe existir"
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Verificar que las funciones de búsqueda existen
        assert 'function filtrarUsuarios()' in js_content, "Función filtrarUsuarios debe existir"
        assert 'function limpiarBusquedaUsuarios()' in js_content, "Función limpiarBusquedaUsuarios debe existir"
        assert 'function filtrarUsuariosRoles()' in js_content, "Función filtrarUsuariosRoles debe existir"
        assert 'function limpiarBusquedaRoles()' in js_content, "Función limpiarBusquedaRoles debe existir"
    
    def test_usuarios_template_has_search_elements(self):
        """Verificar que el template de usuarios tiene los elementos de búsqueda"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'templates', 'usuarios.html'
        )
        
        assert os.path.exists(template_path), "El template usuarios.html debe existir"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Verificar elementos de búsqueda
        assert 'id="buscadorUsuarios"' in template_content, "Input de búsqueda debe existir"
        assert 'onkeyup="filtrarUsuarios()"' in template_content, "Event handler debe existir"
        assert 'onclick="limpiarBusquedaUsuarios()"' in template_content, "Botón limpiar debe existir"
        assert 'id="tablaUsuarios"' in template_content, "Tabla de usuarios debe tener ID"
    
    @patch('vista.vistausuarios.obtener_conexion')
    def test_usuarios_view_basic_functionality(self, mock_conexion):
        """Prueba básica de la vista de usuarios"""
        from main import app
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock de datos de usuarios con datetime real
        mock_cursor.fetchall.return_value = [
            (1, 'admin', 'admin@test.com', datetime(2025, 1, 1), True, 'ADMINISTRADOR', 'Admin User', True),
            (2, 'juan', 'juan@test.com', datetime(2025, 1, 2), False, 'ESCRIBIENTE', 'Juan Pérez', True),
        ]
        
        # Mock de roles
        mock_cursor.fetchall.side_effect = [
            [  # Primera llamada para usuarios
                (1, 'admin', 'admin@test.com', datetime(2025, 1, 1), True, 'ADMINISTRADOR', 'Admin User', True),
                (2, 'juan', 'juan@test.com', datetime(2025, 1, 2), False, 'ESCRIBIENTE', 'Juan Pérez', True),
            ],
            [  # Segunda llamada para roles
                (1, 'ESCRIBIENTE'),
                (2, 'SUSTANCIADOR'),
            ]
        ]
        
        with app.test_client() as client:
            response = client.get('/usuarios')
            assert response.status_code == 200
            assert b'Gesti' in response.data or b'usuarios' in response.data.lower()
    
    def test_search_functionality_structure(self):
        """Verificar la estructura de la funcionalidad de búsqueda"""
        js_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'js', 'base.js'
        )
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Verificar que la función de búsqueda tiene la estructura correcta
        assert 'getElementById(\'buscadorUsuarios\')' in js_content
        assert 'getElementById(\'tablaUsuarios\')' in js_content
        assert 'getElementsByTagName(\'tr\')' in js_content
        assert 'toLowerCase()' in js_content
        assert 'indexOf(' in js_content
        assert 'style.display' in js_content

if __name__ == '__main__':
    pytest.main([__file__, '-v'])