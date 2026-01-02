"""
Configuración de pytest para las pruebas del sistema de expedientes
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def app():
    """Fixture para crear una instancia de la aplicación Flask para pruebas"""
    from main import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    return flask_app

@pytest.fixture
def client(app):
    """Fixture para crear un cliente de prueba"""
    return app.test_client()

@pytest.fixture
def mock_db_connection():
    """Mock de conexión a base de datos"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor

@pytest.fixture
def sample_usuarios():
    """Datos de ejemplo para usuarios"""
    return [
        (1, 'admin', 'admin@test.com', datetime(2025, 1, 1), True, 'ADMINISTRADOR', 'Admin User', True),
        (2, 'juan', 'juan@test.com', datetime(2025, 1, 2), False, 'ESCRIBIENTE', 'Juan Pérez', True),
        (3, 'maria', 'maria@test.com', datetime(2025, 1, 3), False, 'SUSTANCIADOR', 'María García', True),
        (4, 'carlos', 'carlos@test.com', datetime(2025, 1, 4), False, None, 'Carlos López', False),
    ]

@pytest.fixture
def sample_roles():
    """Datos de ejemplo para roles"""
    return [
        (1, 'ESCRIBIENTE'),
        (2, 'SUSTANCIADOR'),
        (3, 'ADMINISTRADOR')
    ]

@pytest.fixture
def sample_expedientes():
    """Datos de ejemplo para expedientes"""
    return [
        ('08001405302120170058000', 'ACTIVO', 'PENDIENTE', datetime(2025, 1, 1)),
        ('08001405301320170059100', 'INACTIVO', 'SALIO', datetime(2024, 6, 1)),
        ('08001400300420150112500', 'ACTIVO', 'PENDIENTE', datetime(2025, 1, 15))
    ]

@pytest.fixture
def mock_hash_password():
    """Mock para la función de hash de contraseñas"""
    with patch('vista.vistausuarios.hash_password') as mock:
        mock.return_value = 'hashed_password_123'
        yield mock