"""
Pruebas corregidas para el módulo de gestión de usuarios
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestUsuarios:
    """Pruebas unitarias para funciones de usuarios"""
    
    @patch('vista.vistausuarios.obtener_conexion')
    def test_obtener_todos_usuarios_success(self, mock_conexion):
        """Prueba obtener todos los usuarios exitosamente"""
        from vista.vistausuarios import obtener_todos_usuarios
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba con datetime real
        mock_cursor.fetchall.return_value = [
            (1, 'admin', 'admin@test.com', datetime(2025, 1, 1), True, 'ADMINISTRADOR', 'Admin User', True),
            (2, 'juan', 'juan@test.com', datetime(2025, 1, 2), False, 'ESCRIBIENTE', 'Juan Pérez', True),
        ]
        
        # Ejecutar función
        result = obtener_todos_usuarios()
        
        # Verificar resultado
        assert len(result) == 2
        assert result[0][1] == 'admin'
        assert result[1][1] == 'juan'
        
        # Verificar que se llamó la conexión
        mock_conexion.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()
    
    def test_hash_password(self):
        """Prueba la función de hash de contraseñas"""
        from vista.vistausuarios import hash_password
        
        password = "test123"
        hashed = hash_password(password)
        
        # Verificar que el hash es diferente a la contraseña original
        assert hashed != password
        assert len(hashed) == 64  # SHA256 produce 64 caracteres hexadecimales
        
        # Verificar que el mismo password produce el mismo hash
        assert hash_password(password) == hashed

class TestUsuariosIntegration:
    """Pruebas de integración para la vista de usuarios"""
    
    @patch('vista.vistausuarios.obtener_todos_usuarios')
    @patch('vista.vistausuarios.obtener_roles')
    def test_vista_usuarios_get(self, mock_roles, mock_usuarios, client):
        """Prueba GET request a la vista de usuarios"""
        # Configurar mocks con datos reales
        mock_usuarios.return_value = [
            (1, 'admin', 'admin@test.com', datetime(2025, 1, 1), True, 'ADMINISTRADOR', 'Admin User', True),
            (2, 'juan', 'juan@test.com', datetime(2025, 1, 2), False, 'ESCRIBIENTE', 'Juan Pérez', True),
        ]
        mock_roles.return_value = [
            (1, 'ESCRIBIENTE'),
            (2, 'SUSTANCIADOR'),
        ]
        
        # Hacer petición GET
        response = client.get('/usuarios')
        
        # Verificar respuesta
        assert response.status_code == 200
        assert b'usuarios' in response.data.lower() or b'Gesti' in response.data
        
        # Verificar que se llamaron las funciones
        mock_usuarios.assert_called_once()
        mock_roles.assert_called_once()