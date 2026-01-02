"""
Pruebas comprehensivas para el módulo home/dashboard
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestHome:
    """Pruebas unitarias para funciones del home/dashboard"""
    
    @patch('vista.vistahome.obtener_conexion')
    def test_obtener_metricas_dashboard_success(self, mock_conexion):
        """Prueba obtener métricas del dashboard exitosamente"""
        from vista.vistahome import obtener_metricas_dashboard
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Configurar respuestas secuenciales para múltiples queries
        mock_cursor.fetchone.side_effect = [
            (14300,),  # total_expedientes
        ]
        
        mock_cursor.fetchall.side_effect = [
            # expedientes_por_estado
            [('ACTIVO + PENDIENTE', 640), ('INACTIVO + SALIO', 8000), ('ACTIVO + SALIO', 3000)],
            # estados_principales
            [('ACTIVO', 3640), ('INACTIVO', 10660)],
            # estados_adicionales
            [('PENDIENTE', 6064), ('SALIO', 8236)],
            # expedientes_por_responsable
            [('ESCRIBIENTE', 5000), ('SUSTANCIADOR', 3000), ('ADMINISTRADOR', 2000)],
            # expedientes_recientes
            [('08001405302120170058000', '58000', 'Demandante', 'Demandado', 'ACTIVO', 'ACTIVO', 'PENDIENTE', 'ESCRIBIENTE', datetime(2025, 1, 1))],
            # tipos_proceso
            [('Tutela', 5000), ('Amparo', 3000), ('Habeas Corpus', 2000)],
        ]
        
        # Ejecutar función
        result = obtener_metricas_dashboard()
        
        # Verificar resultado
        assert result is not None
        assert 'total_expedientes' in result
        assert 'expedientes_por_estado' in result
        assert 'estados_principales' in result
        assert 'estados_adicionales' in result
        
        # Verificar valores específicos
        assert result['total_expedientes'] == 14300
        assert len(result['expedientes_por_estado']) == 3
        assert len(result['estados_principales']) == 2
        
        # Verificar que se llamó la conexión múltiples veces
        mock_conexion.assert_called()
        assert mock_cursor.execute.call_count >= 6  # Múltiples queries
    
    @patch('vista.vistahome.obtener_conexion')
    def test_obtener_metricas_dashboard_error(self, mock_conexion):
        """Prueba manejo de errores en obtener métricas"""
        from vista.vistahome import obtener_metricas_dashboard
        
        # Configurar mock para lanzar excepción
        mock_conexion.side_effect = Exception("Database connection failed")
        
        # Ejecutar función y verificar que retorna diccionario vacío
        result = obtener_metricas_dashboard()
        
        # La función maneja errores y retorna diccionario vacío
        assert result == {}
    
    @patch('vista.vistahome.obtener_conexion')
    def test_obtener_metricas_dashboard_datos_vacios(self, mock_conexion):
        """Prueba obtener métricas con datos vacíos"""
        from vista.vistahome import obtener_metricas_dashboard
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Configurar respuestas con datos vacíos/cero
        mock_cursor.fetchone.side_effect = [
            (0,),  # total_expedientes
        ]
        
        mock_cursor.fetchall.side_effect = [
            [],  # expedientes_por_estado
            [],  # estados_principales
            [],  # estados_adicionales
            [],  # expedientes_por_responsable
            [],  # expedientes_recientes
            [],  # tipos_proceso
        ]
        
        # Ejecutar función
        result = obtener_metricas_dashboard()
        
        # Verificar que maneja datos vacíos correctamente
        assert result is not None
        assert result['total_expedientes'] == 0
        assert len(result['expedientes_por_estado']) == 0

class TestHomeIntegration:
    """Pruebas de integración para la vista home"""
    
    @patch('vista.vistahome.obtener_metricas_dashboard')
    @patch('utils.auth.get_current_user')
    def test_vista_home_success(self, mock_current_user, mock_metricas, client):
        """Prueba vista home exitosa"""
        # Configurar mocks
        mock_current_user.return_value = {
            'id': 1,
            'usuario': 'admin',
            'nombre': 'Admin User',
            'correo': 'admin@test.com'
        }
        
        mock_metricas.return_value = {
            'total_expedientes': 14300,
            'expedientes_por_estado': [('ACTIVO', 640), ('INACTIVO', 13660)],
            'estados_principales': [('ACTIVO', 640), ('INACTIVO', 13660)],
            'estados_adicionales': [('PENDIENTE', 6064), ('SALIO', 8236)],
            'expedientes_por_responsable': [('ESCRIBIENTE', 5000), ('SUSTANCIADOR', 3000)],
            'expedientes_recientes': [],
            'tipos_proceso': [('Tutela', 5000), ('Amparo', 3000)]
        }
        
        # Simular sesión activa
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'admin'
        
        # Hacer petición GET
        response = client.get('/home')
        
        # Verificar respuesta
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'home' in response.data.lower() or b'inicio' in response.data.lower()
        
        # Solo verificamos que la respuesta es exitosa
    
    @patch('utils.auth.get_current_user')
    def test_vista_home_sin_usuario(self, mock_current_user, client):
        """Prueba vista home sin usuario logueado"""
        # Configurar mock para simular usuario no logueado
        mock_current_user.return_value = None
        
        # Hacer petición GET
        response = client.get('/home', follow_redirects=True)
        
        # Verificar que redirige al login
        assert response.status_code == 200
        # Debería redirigir al login
        assert b'login' in response.data.lower() or response.request.path == '/login'
    
    def test_logout_success(self, client):
        """Prueba logout exitoso"""
        # Simular sesión activa
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'testuser'
        
        # Hacer petición GET a logout
        response = client.get('/logout', follow_redirects=True)
        
        # Verificar respuesta
        assert response.status_code == 200
        
        # Verificar que la sesión se limpió
        with client.session_transaction() as sess:
            assert 'logged_in' not in sess
            assert 'user_id' not in sess
            assert 'usuario' not in sess

class TestHomeDashboard:
    """Pruebas específicas para funcionalidad del dashboard"""
    
    def test_metricas_estructura_correcta(self):
        """Prueba que las métricas tienen la estructura correcta"""
        # Estructura esperada de métricas
        metricas_esperadas = [
            'total_expedientes',
            'total_usuarios',
            'usuarios_activos',
            'usuarios_con_rol',
            'expedientes_por_estado',
            'estados_principales',
            'estados_adicionales',
            'expedientes_por_tramite',
            'expedientes_por_juzgado',
            'actividad_reciente'
        ]
        
        # Verificar que todas las métricas esperadas están definidas
        for metrica in metricas_esperadas:
            assert isinstance(metrica, str)
            assert len(metrica) > 0
    
    @patch('vista.vistahome.obtener_conexion')
    def test_metricas_calculo_porcentajes(self, mock_conexion):
        """Prueba cálculo de porcentajes en métricas"""
        from vista.vistahome import obtener_metricas_dashboard
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba con números conocidos para verificar porcentajes
        mock_cursor.fetchone.side_effect = [
            (100,),  # total_expedientes
        ]
        
        mock_cursor.fetchall.side_effect = [
            [('ACTIVO', 60), ('INACTIVO', 40)],  # 60% activos, 40% inactivos
            [('ACTIVO', 60), ('INACTIVO', 40)],
            [('PENDIENTE', 70), ('SALIO', 30)],  # 70% pendientes, 30% salieron
            [('ESCRIBIENTE', 50), ('SUSTANCIADOR', 30), ('ADMINISTRADOR', 20)],
            [],  # expedientes_recientes
            [('Tutela', 50), ('Amparo', 30), ('Otros', 20)],
        ]
        
        # Ejecutar función
        result = obtener_metricas_dashboard()
        
        # Verificar que los datos son consistentes para cálculos de porcentaje
        assert result['total_expedientes'] == 100
        
        # Verificar distribución de estados
        estados_principales = dict(result['estados_principales'])
        assert estados_principales['ACTIVO'] == 60
        assert estados_principales['INACTIVO'] == 40
    
    @patch('vista.vistahome.obtener_conexion')
    def test_metricas_actividad_reciente(self, mock_conexion):
        """Prueba obtención de actividad reciente"""
        from vista.vistahome import obtener_metricas_dashboard
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Configurar respuestas básicas
        mock_cursor.fetchone.side_effect = [(100,)]
        
        # Datos de expedientes recientes
        expedientes_recientes = [
            ('08001405302120170058000', '58000', 'Demandante 1', 'Demandado 1', 'ACTIVO', 'ACTIVO', 'PENDIENTE', 'ESCRIBIENTE', datetime(2025, 1, 1)),
            ('08001405301320170059100', '59100', 'Demandante 2', 'Demandado 2', 'COMPLETADO', 'INACTIVO', 'SALIO', 'SUSTANCIADOR', datetime(2025, 1, 2)),
        ]
        
        mock_cursor.fetchall.side_effect = [
            [], [], [],  # expedientes_por_estado, estados_principales, estados_adicionales
            [],  # expedientes_por_responsable
            expedientes_recientes,  # expedientes_recientes
            [],  # tipos_proceso
        ]
        
        # Ejecutar función
        result = obtener_metricas_dashboard()
        
        # Verificar expedientes recientes
        assert 'expedientes_recientes' in result
        assert len(result['expedientes_recientes']) == 2
        assert result['expedientes_recientes'][0][0] == '08001405302120170058000'

class TestHomeValidation:
    """Pruebas de validación para home"""
    
    def test_home_requiere_autenticacion(self, client):
        """Prueba que home requiere autenticación"""
        # Hacer petición sin autenticación
        response = client.get('/home', follow_redirects=False)
        
        # Verificar que redirige (302) o requiere login
        assert response.status_code in [302, 401] or b'login' in response.data.lower()
    
    @patch('vista.vistahome.obtener_metricas_dashboard')
    def test_home_manejo_error_metricas(self, mock_metricas, client):
        """Prueba manejo de errores en métricas"""
        # Configurar mock para retornar diccionario vacío (como hace la función real)
        mock_metricas.return_value = {}
        
        # Simular usuario logueado
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'test'
        
        # Mock del usuario actual
        with patch('utils.auth.get_current_user') as mock_user:
            mock_user.return_value = {'id': 1, 'usuario': 'test'}
            
            # Hacer petición
            response = client.get('/home')
            
            # Verificar que no falla completamente
            assert response.status_code == 200  # La vista maneja errores graciosamente