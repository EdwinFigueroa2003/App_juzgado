#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para el control de acceso basado en roles de administrador
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import session
import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

class TestAdminAccessControl:
    """Tests para verificar el control de acceso de administradores"""
    
    @pytest.fixture
    def client(self):
        """Cliente de prueba de Flask"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    
    def test_admin_sidebar_visibility(self, client):
        """Test que verifica que los menús de admin solo aparecen para administradores"""
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'admin_user'
            sess['administrador'] = True
            sess['nombre'] = 'Admin User'
        
        response = client.get('/home')
        assert response.status_code == 200
        
        # Verificar que los menús de admin aparecen
        assert b'Gesti\xc3\xb3n de roles' in response.data
        assert b'Gesti\xc3\xb3n de usuarios' in response.data
        assert b'Seguridad' in response.data
    
    def test_non_admin_sidebar_visibility(self, client):
        """Test que verifica que los menús de admin NO aparecen para usuarios normales"""
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 2
            sess['usuario'] = 'normal_user'
            sess['administrador'] = False
            sess['nombre'] = 'Normal User'
        
        response = client.get('/home')
        assert response.status_code == 200
        
        # Verificar que los menús de admin NO aparecen
        assert b'Gesti\xc3\xb3n de roles' not in response.data
        assert b'Gesti\xc3\xb3n de usuarios' not in response.data
        # El menú de seguridad no debería aparecer para usuarios normales
        response_text = response.data.decode('utf-8')
        admin_security_menu = 'href="/security-dashboard"' in response_text
        assert not admin_security_menu
    
    def test_admin_routes_access_for_admin(self, client):
        """Test que verifica que los administradores pueden acceder a rutas protegidas"""
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'admin_user'
            sess['administrador'] = True
            sess['nombre'] = 'Admin User'
        
        # Test acceso a gestión de roles
        with patch('app_juzgado.vista.vistaroles.obtener_usuarios_con_roles') as mock_usuarios:
            mock_usuarios.return_value = []
            response = client.get('/roles')
            assert response.status_code == 200
        
        # Test acceso a gestión de usuarios
        with patch('app_juzgado.vista.vistausuarios.obtener_todos_usuarios') as mock_usuarios, \
             patch('app_juzgado.vista.vistausuarios.obtener_roles') as mock_roles:
            mock_usuarios.return_value = []
            mock_roles.return_value = []
            response = client.get('/usuarios')
            assert response.status_code == 200
        
        # Test acceso a dashboard de seguridad
        with patch('app_juzgado.utils.security_logger.get_security_stats') as mock_stats:
            mock_stats.return_value = {
                'total_attempts': 0,
                'failed_attempts': 0,
                'blocked_ips': 0,
                'blocked_users': 0,
                'recent_attempts': []
            }
            response = client.get('/security-dashboard')
            assert response.status_code == 200
    
    def test_admin_routes_blocked_for_non_admin(self, client):
        """Test que verifica que los usuarios normales NO pueden acceder a rutas de admin"""
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 2
            sess['usuario'] = 'normal_user'
            sess['administrador'] = False
            sess['nombre'] = 'Normal User'
        
        # Test bloqueo de gestión de roles
        response = client.get('/roles')
        assert response.status_code == 302  # Redirect
        assert '/home' in response.location
        
        # Test bloqueo de gestión de usuarios
        response = client.get('/usuarios')
        assert response.status_code == 302  # Redirect
        assert '/home' in response.location
        
        # Test bloqueo de dashboard de seguridad
        response = client.get('/security-dashboard')
        assert response.status_code == 302  # Redirect
        assert '/home' in response.location
    
    def test_admin_routes_blocked_for_unauthenticated(self, client):
        """Test que verifica que usuarios no autenticados son redirigidos al login"""
        # Test sin sesión
        response = client.get('/roles')
        assert response.status_code == 302  # Redirect
        assert '/login' in response.location
        
        response = client.get('/usuarios')
        assert response.status_code == 302  # Redirect
        assert '/login' in response.location
        
        response = client.get('/security-dashboard')
        assert response.status_code == 302  # Redirect
        assert '/login' in response.location
    
    def test_admin_api_routes_protection(self, client):
        """Test que verifica que las rutas API también están protegidas"""
        # Test sin autenticación
        response = client.get('/api/estadisticas-roles')
        assert response.status_code == 302  # Redirect to login
        
        # Test con usuario normal
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 2
            sess['usuario'] = 'normal_user'
            sess['administrador'] = False
            sess['nombre'] = 'Normal User'
        
        response = client.get('/api/estadisticas-roles')
        assert response.status_code == 302  # Redirect to home
        
        # Test con administrador
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'admin_user'
            sess['administrador'] = True
            sess['nombre'] = 'Admin User'
        
        with patch('app_juzgado.vista.vistaroles.obtener_usuarios_con_roles') as mock_usuarios:
            mock_usuarios.return_value = []
            response = client.get('/api/estadisticas-roles')
            assert response.status_code == 200
    
    def test_session_administrador_field(self, client):
        """Test que verifica que el campo administrador se maneja correctamente en la sesión"""
        # Test con administrador = True
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['administrador'] = True
        
        with client.application.test_request_context():
            with client.session_transaction() as sess:
                assert sess.get('administrador') == True
        
        # Test con administrador = False
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['administrador'] = False
        
        with client.application.test_request_context():
            with client.session_transaction() as sess:
                assert sess.get('administrador') == False
        
        # Test sin campo administrador (debería ser False por defecto)
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            # No establecer administrador
        
        with client.application.test_request_context():
            with client.session_transaction() as sess:
                assert sess.get('administrador', False) == False

if __name__ == '__main__':
    pytest.main([__file__])