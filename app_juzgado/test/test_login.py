"""
Pruebas para el módulo de login y autenticación
"""

import pytest
from unittest.mock import patch, Mock
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vista.vistalogin import hash_password, verificar_usuario

class TestLogin:
    """Clase de pruebas para el sistema de login"""
    
    def test_hash_password_consistency(self):
        """Prueba que el hash de contraseñas sea consistente"""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # El mismo password debe generar el mismo hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produce 64 caracteres hex
        
        # Passwords diferentes deben generar hashes diferentes
        different_hash = hash_password("different_password")
        assert hash1 != different_hash
    
    @patch('vista.vistalogin.obtener_conexion')
    def test_verificar_usuario_success(self, mock_conexion):
        """Prueba verificación exitosa de usuario"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular usuario encontrado con contraseña hasheada
        password_hash = hash_password("test123")
        mock_cursor.fetchone.return_value = (
            1, 'testuser', 'test@example.com', password_hash, 'Test User', True, False
        )
        
        # Ejecutar función
        result = verificar_usuario('testuser', 'test123')
        
        # Verificar resultado
        assert result is not None
        assert result['id'] == 1
        assert result['usuario'] == 'testuser'
        assert result['correo'] == 'test@example.com'
        assert result['nombre'] == 'Test User'
        assert result['administrador'] == False
        
        # Verificar que se actualizó la última sesión
        assert mock_cursor.execute.call_count == 2  # SELECT + UPDATE
        mock_conn.commit.assert_called_once()
    
    @patch('vista.vistalogin.obtener_conexion')
    def test_verificar_usuario_password_incorrecta(self, mock_conexion):
        """Prueba verificación con contraseña incorrecta"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular usuario encontrado con contraseña diferente
        password_hash = hash_password("correct_password")
        mock_cursor.fetchone.return_value = (
            1, 'testuser', 'test@example.com', password_hash, 'Test User', True, False
        )
        
        # Ejecutar función con contraseña incorrecta
        result = verificar_usuario('testuser', 'wrong_password')
        
        # Verificar que retorna None
        assert result is None
        
        # Verificar que NO se actualizó la última sesión
        mock_conn.commit.assert_not_called()
    
    @patch('vista.vistalogin.obtener_conexion')
    def test_verificar_usuario_no_existe(self, mock_conexion):
        """Prueba verificación de usuario que no existe"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Usuario no encontrado
        
        # Ejecutar función
        result = verificar_usuario('nonexistent', 'password')
        
        # Verificar que retorna None
        assert result is None
    
    @patch('vista.vistalogin.obtener_conexion')
    def test_verificar_usuario_inactivo(self, mock_conexion):
        """Prueba verificación de usuario inactivo"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Usuario inactivo no se encuentra
        
        # Ejecutar función
        result = verificar_usuario('inactive_user', 'password')
        
        # Verificar que retorna None (usuario inactivo no se encuentra)
        assert result is None
    
    @patch('vista.vistalogin.obtener_conexion')
    def test_verificar_usuario_por_email(self, mock_conexion):
        """Prueba verificación de usuario por email"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular usuario encontrado por email
        password_hash = hash_password("test123")
        mock_cursor.fetchone.return_value = (
            1, 'testuser', 'test@example.com', password_hash, 'Test User', True, False
        )
        
        # Ejecutar función con email
        result = verificar_usuario('test@example.com', 'test123')
        
        # Verificar resultado
        assert result is not None
        assert result['usuario'] == 'testuser'
        assert result['correo'] == 'test@example.com'
    
    @patch('vista.vistalogin.obtener_conexion')
    def test_verificar_usuario_migracion_password_plana(self, mock_conexion):
        """Prueba migración de contraseña plana a hash"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular usuario con contraseña plana (menos de 64 caracteres)
        mock_cursor.fetchone.return_value = (
            1, 'testuser', 'test@example.com', 'plaintext123', 'Test User', True, False
        )
        
        # Ejecutar función
        result = verificar_usuario('testuser', 'plaintext123')
        
        # Verificar resultado
        assert result is not None
        assert result['usuario'] == 'testuser'
        
        # Verificar que se actualizó la contraseña a hash
        assert mock_cursor.execute.call_count == 2  # SELECT + UPDATE
        mock_conn.commit.assert_called_once()
    
    @patch('vista.vistalogin.obtener_conexion')
    def test_verificar_usuario_error_db(self, mock_conexion):
        """Prueba manejo de errores de base de datos"""
        # Configurar mock para lanzar excepción
        mock_conexion.side_effect = Exception("Database connection error")
        
        # Ejecutar función
        result = verificar_usuario('testuser', 'password')
        
        # Verificar que retorna None en caso de error
        assert result is None

class TestLoginIntegration:
    """Pruebas de integración para el sistema de login"""
    
    def test_login_page_get(self, client):
        """Prueba GET a la página de login"""
        response = client.get('/login')
        
        assert response.status_code == 200
        assert b'Iniciar Sesi\xc3\xb3n' in response.data
        assert b'Usuario o Email' in response.data
        assert b'Contrase\xc3\xb1a' in response.data
    
    @patch('vista.vistalogin.verificar_usuario')
    def test_login_post_success(self, mock_verificar, client):
        """Prueba POST exitoso al login"""
        # Configurar mock
        mock_verificar.return_value = {
            'id': 1,
            'usuario': 'testuser',
            'correo': 'test@example.com',
            'nombre': 'Test User',
            'administrador': False
        }
        
        # Datos del formulario
        form_data = {
            'username': 'testuser',
            'password': 'password123'
        }
        
        # Hacer petición POST
        response = client.post('/login', data=form_data, follow_redirects=True)
        
        # Verificar redirección exitosa
        assert response.status_code == 200
        mock_verificar.assert_called_once_with('testuser', 'password123')
    
    @patch('vista.vistalogin.verificar_usuario')
    def test_login_post_failure(self, mock_verificar, client):
        """Prueba POST fallido al login"""
        # Configurar mock para fallo
        mock_verificar.return_value = None
        
        # Datos del formulario
        form_data = {
            'username': 'wronguser',
            'password': 'wrongpassword'
        }
        
        # Hacer petición POST
        response = client.post('/login', data=form_data)
        
        # Verificar que se mantiene en login
        assert response.status_code == 200
        assert b'Usuario/email o contrase\xc3\xb1a incorrectos' in response.data
    
    def test_login_post_campos_vacios(self, client):
        """Prueba POST con campos vacíos"""
        # Datos del formulario vacíos
        form_data = {
            'username': '',
            'password': ''
        }
        
        # Hacer petición POST
        response = client.post('/login', data=form_data)
        
        # Verificar mensaje de error
        assert response.status_code == 200
        assert b'Por favor ingrese usuario/email y contrase\xc3\xb1a' in response.data
    
    def test_login_redirect_if_logged_in(self, client):
        """Prueba redirección si ya está logueado"""
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
        
        # Hacer petición GET
        response = client.get('/login', follow_redirects=True)
        
        # Verificar redirección
        assert response.status_code == 200