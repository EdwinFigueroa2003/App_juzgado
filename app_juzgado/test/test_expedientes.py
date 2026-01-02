"""
Pruebas corregidas para el módulo de expedientes
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestExpedientes:
    """Pruebas unitarias para funciones de expedientes"""
    
    @patch('vista.vistaexpediente.obtener_conexion')
    def test_buscar_expedientes_por_radicado(self, mock_conexion):
        """Prueba buscar expedientes por radicado"""
        from vista.vistaexpediente import buscar_expedientes
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba con todos los campos esperados (18 campos)
        mock_cursor.fetchall.return_value = [
            (1, '08001405302120170058000', '58000', 'Demandante Test', 'Demandado Test',
             'ACTIVO', 'Ubicación Test', 'Tutela', 'Juzgado 1', 'ESCRIBIENTE',
             '2025-01-01', '2025-01-01', '2025-01-01', 'Observaciones test', 5,
             'ACTIVO', 'PENDIENTE', '2025-01-01'),
        ]
        
        # Mock para las consultas adicionales (ingresos, estados, tramites)
        mock_cursor.fetchall.side_effect = [
            # Primera consulta: expediente principal
            [(1, '08001405302120170058000', '58000', 'Demandante Test', 'Demandado Test',
              'ACTIVO', 'Ubicación Test', 'Tutela', 'Juzgado 1', 'ESCRIBIENTE',
              '2025-01-01', '2025-01-01', '2025-01-01', 'Observaciones test', 5,
              'ACTIVO', 'PENDIENTE', '2025-01-01')],
            # Segunda consulta: ingresos
            [],
            # Tercera consulta: estados
            [],
            # Cuarta consulta: tramites
            [],
            # Quinta consulta: estadísticas
            [(5, 2, 1, 2)]
        ]
        
        # Ejecutar función
        result = buscar_expedientes('08001405302120170058000')
        
        # Verificar resultado
        assert len(result) == 1
        assert result[0]['radicado_completo'] == '08001405302120170058000'
        
        # Verificar que se llamó la conexión
        mock_conexion.assert_called_once()
    
    @patch('vista.vistaexpediente.obtener_conexion')
    def test_filtrar_por_estado(self, mock_conexion):
        """Prueba filtrar expedientes por estado"""
        from vista.vistaexpediente import filtrar_por_estado
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Datos de prueba con todos los campos esperados (18 campos + fecha_orden)
        mock_cursor.fetchall.return_value = [
            (1, '08001405302120170058000', '58000', 'Demandante 1', 'Demandado 1',
             'ACTIVO', 'Ubicación 1', 'Tutela', 'Juzgado 1', 'ESCRIBIENTE',
             '2025-01-01', '2025-01-01', '2025-01-01', 'Observaciones 1', 5,
             'ACTIVO', 'PENDIENTE', '2025-01-01', '2025-01-01'),
            (2, '08001405301320170059100', '59100', 'Demandante 2', 'Demandado 2',
             'ACTIVO', 'Ubicación 2', 'Amparo', 'Juzgado 2', 'SUSTANCIADOR',
             '2025-01-02', '2025-01-02', '2025-01-02', 'Observaciones 2', 3,
             'ACTIVO', 'PENDIENTE', '2025-01-02', '2025-01-02'),
        ]
        
        # Mock para las consultas adicionales de cada expediente
        mock_cursor.fetchall.side_effect = [
            # Primera consulta: expedientes principales
            [(1, '08001405302120170058000', '58000', 'Demandante 1', 'Demandado 1',
              'ACTIVO', 'Ubicación 1', 'Tutela', 'Juzgado 1', 'ESCRIBIENTE',
              '2025-01-01', '2025-01-01', '2025-01-01', 'Observaciones 1', 5,
              'ACTIVO', 'PENDIENTE', '2025-01-01', '2025-01-01'),
             (2, '08001405301320170059100', '59100', 'Demandante 2', 'Demandado 2',
              'ACTIVO', 'Ubicación 2', 'Amparo', 'Juzgado 2', 'SUSTANCIADOR',
              '2025-01-02', '2025-01-02', '2025-01-02', 'Observaciones 2', 3,
              'ACTIVO', 'PENDIENTE', '2025-01-02', '2025-01-02')],
            # Consultas adicionales para cada expediente (ingresos, estados, tramites, estadísticas)
            [], [], [], [(5, 2, 1, 2)],  # Expediente 1
            [], [], [], [(3, 1, 1, 1)],  # Expediente 2
        ]
        
        # Ejecutar función
        result = filtrar_por_estado('ACTIVO')
        
        # Verificar resultado
        assert len(result) == 2
        assert result[0]['radicado_completo'] == '08001405302120170058000'
        assert result[1]['radicado_completo'] == '08001405301320170059100'
        
        # Verificar que se llamó la conexión
        mock_conexion.assert_called_once()
    
    def test_paginar_resultados(self):
        """Prueba paginación de resultados"""
        from vista.vistaexpediente import paginar_resultados
        
        # Lista de 25 elementos
        elementos = list(range(1, 26))
        
        # Página 1, 10 elementos por página
        resultado_pagina, paginacion = paginar_resultados(elementos, 1, 10)
        
        # Verificar que devuelve tupla con datos y paginación
        assert len(resultado_pagina) <= 10
        assert 1 in resultado_pagina  # Primer elemento
        assert paginacion['pagina_actual'] == 1
        assert paginacion['total_paginas'] == 3
    
    def test_calcular_paginas_mostrar(self):
        """Prueba cálculo de páginas a mostrar"""
        from vista.vistaexpediente import calcular_paginas_mostrar
        
        # Caso normal
        paginas = calcular_paginas_mostrar(5, 10)
        assert 5 in paginas
        assert len(paginas) <= 5
        
        # Caso con pocas páginas
        paginas = calcular_paginas_mostrar(2, 3)
        assert paginas == [1, 2, 3]

class TestExpedientesIntegration:
    """Pruebas de integración para la vista de expedientes"""
    
    @patch('vista.vistaexpediente.buscar_expedientes')
    def test_vista_expedientes_get(self, mock_buscar, client):
        """Prueba GET request a la vista de expedientes"""
        # Configurar mock
        mock_buscar.return_value = []
        
        # Hacer petición GET
        response = client.get('/expediente')
        
        # Verificar respuesta
        assert response.status_code == 200
        assert b'expediente' in response.data.lower() or b'radicado' in response.data.lower()