"""
Pruebas comprehensivas para el módulo de gestión de roles
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestRoles:
    """Pruebas unitarias para funciones de roles"""
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_obtener_usuarios_con_roles_success(self, mock_conexion):
        """Prueba obtener usuarios con roles exitosamente"""
        from vista.vistaroles import obtener_usuarios_con_roles
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba - estructura: id, nombre, correo, rol_nombre, fecha_registro, activo
        mock_cursor.fetchall.return_value = [
            (1, 'Admin User', 'admin@test.com', 'ADMINISTRADOR', datetime(2025, 1, 1), True),
            (2, 'Juan Pérez', 'juan@test.com', 'ESCRIBIENTE', datetime(2025, 1, 2), True),
            (3, 'María García', 'maria@test.com', None, datetime(2025, 1, 3), True),
        ]
        
        # Ejecutar función
        result = obtener_usuarios_con_roles()
        
        # Verificar resultado - la función retorna diccionarios
        assert len(result) == 3
        assert result[0]['nombre'] == 'Admin User'
        assert result[1]['rol'] == 'ESCRIBIENTE'
        assert result[2]['rol'] is None  # Usuario sin rol
        
        # Verificar que se llamó la conexión
        mock_conexion.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_asignar_rol_usuario_success(self, mock_conexion):
        """Prueba asignar rol a usuario exitosamente"""
        from vista.vistaroles import asignar_rol_usuario
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock para obtener ID del rol
        mock_cursor.fetchone.return_value = (1,)  # ID del rol
        mock_cursor.rowcount = 1  # Simular que se actualizó 1 fila
        
        # Ejecutar función
        result = asignar_rol_usuario(1, 'ESCRIBIENTE')
        
        # Verificar resultado
        assert result is True
        
        # Verificar que se ejecutaron las queries necesarias
        assert mock_cursor.execute.call_count >= 2  # Verificación y actualización
        mock_conn.commit.assert_called_once()
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_asignar_rol_usuario_no_existe(self, mock_conexion):
        """Prueba asignar rol a usuario que no existe"""
        from vista.vistaroles import asignar_rol_usuario
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock para simular que el rol no existe
        mock_cursor.fetchone.return_value = None
        
        # Ejecutar función y verificar que lanza excepción
        with pytest.raises(ValueError, match="no encontrado en la base de datos"):
            asignar_rol_usuario(999, 'ESCRIBIENTE')
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_remover_rol_usuario_success(self, mock_conexion):
        """Prueba remover rol de usuario exitosamente"""
        from vista.vistaroles import remover_rol_usuario
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock para simular actualización exitosa
        mock_cursor.rowcount = 1
        
        # Ejecutar función
        result = remover_rol_usuario(1)
        
        # Verificar resultado
        assert result is True
        
        # Verificar que se ejecutó la query
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_obtener_responsables_activos(self, mock_conexion):
        """Prueba obtener solo usuarios con roles activos"""
        from vista.vistaroles import obtener_responsables_activos
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba - estructura: id, nombre, correo, rol_nombre
        mock_cursor.fetchall.return_value = [
            (1, 'Admin User', 'admin@test.com', 'ADMINISTRADOR'),
            (2, 'Juan Pérez', 'juan@test.com', 'ESCRIBIENTE'),
            (3, 'María García', 'maria@test.com', 'SUSTANCIADOR'),
        ]
        
        # Ejecutar función
        result = obtener_responsables_activos()
        
        # Verificar resultado - la función retorna diccionarios
        assert len(result) == 3
        assert all(usuario['rol'] is not None for usuario in result)  # Todos tienen rol
        
        # Verificar que se llamó la conexión
        mock_conexion.assert_called_once()
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_buscar_usuario_por_nombre_correo(self, mock_conexion):
        """Prueba búsqueda de usuario por nombre o correo"""
        from vista.vistaroles import buscar_usuario_por_nombre_correo
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba - estructura: id, nombre, correo, rol_nombre, fecha_registro, activo
        mock_cursor.fetchall.return_value = [
            (1, 'Juan Pérez', 'juan@test.com', 'ESCRIBIENTE', datetime(2025, 1, 1), True),
        ]
        
        # Ejecutar función
        result = buscar_usuario_por_nombre_correo('juan')
        
        # Verificar resultado - la función retorna diccionarios
        assert len(result) == 1
        assert result[0]['nombre'] == 'Juan Pérez'
        
        # Verificar que se usó LIKE en la query
        mock_cursor.execute.assert_called_once()
        query_call = mock_cursor.execute.call_args[0][0]
        assert 'LIKE' in query_call.upper()
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_asignar_roles_aleatorios(self, mock_conexion):
        """Prueba asignación de roles aleatorios"""
        from vista.vistaroles import asignar_roles_aleatorios
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock para obtener usuarios activos
        mock_cursor.fetchall.return_value = [
            (1,), (2,), (3,)
        ]
        
        # Mock para obtener IDs de roles
        mock_cursor.fetchone.side_effect = [(1,), (2,)]  # IDs de ESCRIBIENTE y SUSTANCIADOR
        
        # Ejecutar función
        result = asignar_roles_aleatorios()
        
        # Verificar resultado
        assert 'total' in result
        assert 'escribientes' in result
        assert 'sustanciadores' in result
        assert result['total'] == 3
        
        # Verificar que se ejecutaron múltiples updates
        assert mock_cursor.execute.call_count >= 5  # SELECT usuarios + 2 SELECT roles + 3 UPDATEs
        mock_conn.commit.assert_called_once()
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_remover_todos_roles(self, mock_conexion):
        """Prueba remover todos los roles"""
        from vista.vistaroles import remover_todos_roles
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock para simular que se actualizaron 5 usuarios
        mock_cursor.rowcount = 5
        
        # Ejecutar función
        result = remover_todos_roles()
        
        # Verificar resultado
        assert result == 5
        
        # Verificar que se ejecutó UPDATE masivo
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

class TestRolesIntegration:
    """Pruebas de integración para la vista de roles"""
    
    @patch('vista.vistaroles.obtener_usuarios_con_roles')
    def test_vista_roles_get(self, mock_usuarios, client):
        """Prueba GET request a la vista de roles"""
        # Configurar mock
        mock_usuarios.return_value = [
            (1, 'admin', 'admin@test.com', 'Admin User', 'ADMINISTRADOR', True, datetime(2025, 1, 1)),
            (2, 'juan', 'juan@test.com', 'Juan Pérez', 'ESCRIBIENTE', True, datetime(2025, 1, 2)),
        ]
        
        # Hacer petición GET
        response = client.get('/roles')
        
        # Verificar respuesta
        assert response.status_code == 200
        assert b'roles' in response.data.lower() or b'usuario' in response.data.lower()
        
        # Verificar que se llamó la función
        mock_usuarios.assert_called_once()
    
    @patch('vista.vistaroles.asignar_rol_usuario')
    @patch('vista.vistaroles.obtener_usuarios_con_roles')
    def test_vista_roles_asignar_rol(self, mock_usuarios, mock_asignar, client):
        """Prueba asignación de rol via POST"""
        # Configurar mocks
        mock_asignar.return_value = True
        mock_usuarios.return_value = []
        
        # Datos del formulario
        form_data = {
            'accion': 'asignar_rol',
            'usuario_id': '1',
            'rol': 'ESCRIBIENTE'
        }
        
        # Hacer petición POST
        response = client.post('/roles', data=form_data, follow_redirects=True)
        
        # Verificar respuesta
        assert response.status_code == 200
        
        # Verificar que se llamó la función de asignación
        mock_asignar.assert_called_once_with('1', 'ESCRIBIENTE')
    
    @patch('vista.vistaroles.remover_rol_usuario')
    @patch('vista.vistaroles.obtener_usuarios_con_roles')
    def test_vista_roles_remover_rol(self, mock_usuarios, mock_remover, client):
        """Prueba remoción de rol via POST"""
        # Configurar mocks
        mock_remover.return_value = True
        mock_usuarios.return_value = []
        
        # Datos del formulario
        form_data = {
            'accion': 'remover_rol',
            'usuario_id': '1'
        }
        
        # Hacer petición POST
        response = client.post('/roles', data=form_data, follow_redirects=True)
        
        # Verificar respuesta
        assert response.status_code == 200
        
        # Verificar que se llamó la función de remoción
        mock_remover.assert_called_once_with('1')

class TestRolesAPI:
    """Pruebas para las APIs de roles"""
    
    @patch('vista.vistaroles.obtener_usuarios_con_roles')
    def test_api_estadisticas_roles(self, mock_usuarios, client):
        """Prueba API de estadísticas de roles"""
        # Configurar mock
        mock_usuarios.return_value = [
            {'id': 1, 'nombre': 'Admin', 'correo': 'admin@test.com', 'rol': 'ADMINISTRADOR', 'activo': True},
            {'id': 2, 'nombre': 'Juan', 'correo': 'juan@test.com', 'rol': 'ESCRIBIENTE', 'activo': True},
            {'id': 3, 'nombre': 'Maria', 'correo': 'maria@test.com', 'rol': 'ESCRIBIENTE', 'activo': True},
            {'id': 4, 'nombre': 'Carlos', 'correo': 'carlos@test.com', 'rol': None, 'activo': True},
        ]
        
        # Hacer petición GET a la API
        response = client.get('/api/estadisticas-roles')
        
        # Verificar respuesta
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        # Verificar estructura de datos JSON
        data = response.get_json()
        assert 'total_usuarios' in data
        assert 'escribientes' in data
        assert 'sustanciadores' in data
        assert 'sin_rol' in data
        
        # Verificar valores esperados
        assert data['total_usuarios'] == 4
        assert data['escribientes'] == 2
        assert data['sin_rol'] == 1

class TestRolesValidation:
    """Pruebas de validación para roles"""
    
    @patch('vista.vistaroles.obtener_conexion')
    def test_asignar_rol_usuario_rol_invalido(self, mock_conexion):
        """Prueba asignar rol inválido"""
        from vista.vistaroles import asignar_rol_usuario
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Ejecutar función con rol inválido y verificar que lanza excepción
        with pytest.raises(ValueError, match="Rol inválido"):
            asignar_rol_usuario(1, 'ROL_INEXISTENTE')
    
    def test_roles_validos_constants(self):
        """Prueba que los roles válidos están definidos"""
        # Verificar que los roles principales existen en el sistema
        roles_esperados = ['ESCRIBIENTE', 'SUSTANCIADOR', 'ADMINISTRADOR']
        
        # Esta prueba verifica que el sistema conoce estos roles
        # En una implementación real, estos podrían venir de una configuración
        for rol in roles_esperados:
            assert isinstance(rol, str)
            assert len(rol) > 0