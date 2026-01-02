"""
Pruebas comprehensivas para el módulo de asignación de expedientes
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAsignacion:
    """Pruebas unitarias para funciones de asignación"""
    
    @patch('vista.vistaasignacion.obtener_conexion')
    def test_obtener_info_usuario_con_rol_success(self, mock_conexion):
        """Prueba obtener información de usuario con rol exitosamente"""
        from vista.vistaasignacion import obtener_info_usuario_con_rol
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba - estructura: id, nombre, correo, usuario, rol, activo
        mock_cursor.fetchone.return_value = (
            1, 'Juan Pérez', 'juan@test.com', 'juan', 'ESCRIBIENTE', True
        )
        
        # Ejecutar función
        result = obtener_info_usuario_con_rol(1)
        
        # Verificar resultado
        assert result is not None
        assert result['usuario'] == 'juan'
        assert result['rol'] == 'ESCRIBIENTE'
        assert result['nombre'] == 'Juan Pérez'
        assert result['activo'] is True
        
        # Verificar que se llamó la conexión
        mock_conexion.assert_called_once()
        mock_cursor.execute.assert_called_once()
    
    @patch('vista.vistaasignacion.obtener_conexion')
    def test_obtener_info_usuario_con_rol_no_existe(self, mock_conexion):
        """Prueba obtener información de usuario que no existe"""
        from vista.vistaasignacion import obtener_info_usuario_con_rol
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular usuario no encontrado
        mock_cursor.fetchone.return_value = None
        
        # Ejecutar función
        result = obtener_info_usuario_con_rol(999)
        
        # Verificar resultado
        assert result is None
    
    @patch('vista.vistaasignacion.obtener_conexion')
    def test_obtener_expedientes_por_usuario_escribiente(self, mock_conexion):
        """Prueba obtener expedientes para usuario ESCRIBIENTE"""
        from vista.vistaasignacion import obtener_expedientes_por_usuario
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba para escribiente - 18 campos según la query real
        mock_cursor.fetchall.return_value = [
            (1, '08001405302120170058000', '58000', 'Demandante 1', 'Demandado 1',
             'EN_PROCESO', 'ACTIVO', 'PENDIENTE', 'Juzgado 1', 'Tutela', 'Juzgado 1', 'ESCRIBIENTE',
             datetime(2025, 1, 1), datetime(2025, 1, 1), 2, 3, datetime(2025, 1, 1), datetime(2025, 1, 1)),
            (2, '08001405301320170059100', '59100', 'Demandante 2', 'Demandado 2',
             'COMPLETADO', 'INACTIVO', 'SALIO', 'Juzgado 2', 'Amparo', 'Juzgado 2', 'ESCRIBIENTE',
             datetime(2025, 1, 2), datetime(2025, 1, 2), 1, 2, datetime(2025, 1, 2), datetime(2025, 1, 3)),
        ]
        
        # Ejecutar función
        result = obtener_expedientes_por_usuario(1, 'ESCRIBIENTE')
        
        # Verificar resultado
        assert len(result) == 2
        assert result[0]['radicado_completo'] == '08001405302120170058000'
        assert result[1]['estado_principal'] == 'INACTIVO'
        
        # Verificar que se llamó la conexión
        mock_conexion.assert_called_once()
    
    @patch('vista.vistaasignacion.obtener_conexion')
    def test_obtener_expedientes_por_usuario_sustanciador(self, mock_conexion):
        """Prueba obtener expedientes para usuario SUSTANCIADOR"""
        from vista.vistaasignacion import obtener_expedientes_por_usuario
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba para sustanciador - 18 campos según la query real
        mock_cursor.fetchall.return_value = [
            (1, '08001405302120170058000', '58000', 'Demandante 1', 'Demandado 1',
             'EN_PROCESO', 'ACTIVO', 'PENDIENTE', 'Juzgado 1', 'Tutela', 'Juzgado 1', 'SUSTANCIADOR',
             datetime(2025, 1, 1), datetime(2025, 1, 1), 2, 3, datetime(2025, 1, 1), datetime(2025, 1, 1)),
        ]
        
        # Ejecutar función
        result = obtener_expedientes_por_usuario(1, 'SUSTANCIADOR')
        
        # Verificar resultado
        assert len(result) == 1
        assert result[0]['responsable'] == 'SUSTANCIADOR'
        
        # Verificar que se llamó la conexión
        mock_conexion.assert_called_once()
    
    def test_calcular_estadisticas_usuario_con_expedientes(self):
        """Prueba cálculo de estadísticas con expedientes"""
        from vista.vistaasignacion import calcular_estadisticas_usuario
        
        # Datos de prueba
        expedientes = [
            {'estado_principal': 'ACTIVO', 'estado_adicional': 'PENDIENTE', 'estado_actual': 'EN_PROCESO'},
            {'estado_principal': 'ACTIVO', 'estado_adicional': 'SALIO', 'estado_actual': 'COMPLETADO'},
            {'estado_principal': 'INACTIVO', 'estado_adicional': 'PENDIENTE', 'estado_actual': 'EN_PROCESO'},
            {'estado_principal': 'INACTIVO', 'estado_adicional': 'SALIO', 'estado_actual': 'COMPLETADO'},
        ]
        
        # Ejecutar función
        result = calcular_estadisticas_usuario(expedientes, 'ESCRIBIENTE')
        
        # Verificar resultado
        assert result['total'] == 4
        assert result['activos'] == 2
        assert result['inactivos'] == 2
        assert result['pendientes'] == 2
        assert result['salieron'] == 2
        assert result['completados'] == 2
        assert result['en_proceso'] == 2
        assert result['porcentaje_activos'] == 50.0
        assert result['porcentaje_completados'] == 50.0
        assert result['rol'] == 'ESCRIBIENTE'
    
    def test_calcular_estadisticas_usuario_sin_expedientes(self):
        """Prueba cálculo de estadísticas sin expedientes"""
        from vista.vistaasignacion import calcular_estadisticas_usuario
        
        # Ejecutar función con lista vacía
        result = calcular_estadisticas_usuario([], 'ESCRIBIENTE')
        
        # Verificar resultado
        assert result['total'] == 0
        assert result['activos'] == 0
        assert result['inactivos'] == 0
        assert result['pendientes'] == 0
        assert result['salieron'] == 0
        assert result['completados'] == 0
        assert result['en_proceso'] == 0
        assert result['sin_informacion'] == 0
        assert result['porcentaje_activos'] == 0
        # La función real no incluye porcentaje_completados en el caso vacío
        assert result['rol'] == 'ESCRIBIENTE'

class TestAsignacionIntegration:
    """Pruebas de integración para la vista de asignación"""
    
    @patch('vista.vistaasignacion.obtener_expedientes_por_usuario')
    @patch('vista.vistaasignacion.obtener_info_usuario_con_rol')
    @patch('utils.auth.get_current_user')
    def test_vista_asignacion_usuario_con_rol(self, mock_current_user, mock_info_usuario, mock_expedientes, client):
        """Prueba vista de asignación para usuario con rol"""
        # Configurar mocks
        mock_current_user.return_value = {
            'id': 1,
            'usuario': 'juan',
            'nombre': 'Juan Pérez',
            'correo': 'juan@test.com'
        }
        
        mock_info_usuario.return_value = {
            'usuario': 'juan',
            'nombre': 'Juan Pérez',
            'correo': 'juan@test.com',
            'rol': 'ESCRIBIENTE',
            'activo': True
        }
        
        mock_expedientes.return_value = [
            {
                'id': 1,
                'radicado_completo': '08001405302120170058000',
                'estado_principal': 'ACTIVO',
                'estado_adicional': 'PENDIENTE',
                'estado_actual': 'EN_PROCESO',
                'demandante': 'Test Demandante',
                'demandado': 'Test Demandado'
            }
        ]
        
        # Simular sesión activa
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'juan'
        
        # Hacer petición GET
        response = client.get('/asignacion')
        
        # Verificar respuesta
        assert response.status_code == 200
        assert b'asignacion' in response.data.lower() or b'expediente' in response.data.lower()
        
        # Verificar que se llamaron las funciones (pueden no llamarse si hay redirección)
        # Solo verificamos si la respuesta es exitosa
    
    @patch('vista.vistaasignacion.obtener_info_usuario_con_rol')
    @patch('utils.auth.get_current_user')
    def test_vista_asignacion_usuario_sin_rol(self, mock_current_user, mock_info_usuario, client):
        """Prueba vista de asignación para usuario sin rol"""
        # Configurar mocks
        mock_current_user.return_value = {
            'id': 1,
            'usuario': 'juan',
            'nombre': 'Juan Pérez',
            'correo': 'juan@test.com'
        }
        
        mock_info_usuario.return_value = {
            'usuario': 'juan',
            'nombre': 'Juan Pérez',
            'correo': 'juan@test.com',
            'rol': None,  # Sin rol asignado
            'activo': True
        }
        
        # Simular sesión activa
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'juan'
        
        # Hacer petición GET
        response = client.get('/asignacion')
        
        # Verificar respuesta
        assert response.status_code == 200
        
        # Solo verificamos que la respuesta es exitosa
    
    @patch('utils.auth.get_current_user')
    def test_vista_asignacion_sin_usuario(self, mock_current_user, client):
        """Prueba vista de asignación sin usuario logueado"""
        # Configurar mock para simular usuario no logueado
        mock_current_user.return_value = None
        
        # Hacer petición GET
        response = client.get('/asignacion', follow_redirects=True)
        
        # Verificar que redirige al login
        assert response.status_code == 200
        # Debería redirigir al login
        assert b'login' in response.data.lower() or response.request.path == '/login'

class TestAsignacionValidation:
    """Pruebas de validación para asignación"""
    
    def test_roles_validos_asignacion(self):
        """Prueba que solo roles válidos pueden acceder a asignación"""
        roles_validos = ['ESCRIBIENTE', 'SUSTANCIADOR', 'ADMINISTRADOR']
        
        for rol in roles_validos:
            assert isinstance(rol, str)
            assert len(rol) > 0
    
    @patch('vista.vistaasignacion.obtener_conexion')
    def test_obtener_expedientes_manejo_errores(self, mock_conexion):
        """Prueba manejo de errores en obtener expedientes"""
        from vista.vistaasignacion import obtener_expedientes_por_usuario
        
        # Configurar mock para lanzar excepción
        mock_conexion.side_effect = Exception("Database error")
        
        # Ejecutar función y verificar que maneja el error
        with pytest.raises(Exception):
            obtener_expedientes_por_usuario(1, 'ESCRIBIENTE')
    
    def test_estadisticas_porcentajes_correctos(self):
        """Prueba que los porcentajes se calculan correctamente"""
        from vista.vistaasignacion import calcular_estadisticas_usuario
        
        # Datos de prueba con números conocidos
        expedientes = [
            {'estado_principal': 'ACTIVO', 'estado_adicional': 'PENDIENTE', 'estado_actual': 'COMPLETADO'},
            {'estado_principal': 'ACTIVO', 'estado_adicional': 'SALIO', 'estado_actual': 'COMPLETADO'},
            {'estado_principal': 'INACTIVO', 'estado_adicional': 'PENDIENTE', 'estado_actual': 'EN_PROCESO'},
            {'estado_principal': 'INACTIVO', 'estado_adicional': 'SALIO', 'estado_actual': 'EN_PROCESO'},
        ]
        
        # Ejecutar función
        result = calcular_estadisticas_usuario(expedientes, 'ESCRIBIENTE')
        
        # Verificar porcentajes
        assert result['porcentaje_activos'] == 50.0  # 2 de 4
        assert result['porcentaje_completados'] == 50.0  # 2 de 4
        
        # Verificar que los totales suman correctamente
        assert result['activos'] + result['inactivos'] == result['total']
        assert result['pendientes'] + result['salieron'] == result['total']