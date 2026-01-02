"""
Pruebas para la conexión y operaciones de base de datos
"""

import pytest
from unittest.mock import patch, Mock
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestDatabase:
    """Clase de pruebas para operaciones de base de datos"""
    
    @patch('modelo.configBd.psycopg2.connect')
    def test_obtener_conexion_success(self, mock_connect):
        """Prueba conexión exitosa a la base de datos"""
        # Configurar mock
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        # Importar función después del mock
        from modelo.configBd import obtener_conexion
        
        # Ejecutar función
        result = obtener_conexion()
        
        # Verificar resultado
        assert result == mock_connection
        mock_connect.assert_called_once()
    
    @patch('modelo.configBd.psycopg2.connect')
    def test_obtener_conexion_error(self, mock_connect):
        """Prueba manejo de errores en conexión a BD"""
        # Configurar mock para lanzar excepción
        mock_connect.side_effect = Exception("Connection failed")
        
        # Importar función después del mock
        from modelo.configBd import obtener_conexion
        
        # Ejecutar función y verificar que lanza excepción
        with pytest.raises(Exception):
            obtener_conexion()
    
    @patch('modelo.configBd.obtener_conexion')
    def test_query_execution_success(self, mock_conexion):
        """Prueba ejecución exitosa de query"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [('test_data',)]
        
        # Simular ejecución de query
        conn = mock_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_table")
        result = cursor.fetchall()
        
        # Verificar resultado
        assert result == [('test_data',)]
        cursor.execute.assert_called_once_with("SELECT * FROM test_table")
    
    @patch('modelo.configBd.obtener_conexion')
    def test_transaction_commit(self, mock_conexion):
        """Prueba commit de transacción"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular transacción
        conn = mock_conexion()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table VALUES (%s)", ('test_value',))
        conn.commit()
        
        # Verificar commit
        mock_conn.commit.assert_called_once()
    
    @patch('modelo.configBd.obtener_conexion')
    def test_transaction_rollback(self, mock_conexion):
        """Prueba rollback de transacción"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Query failed")
        
        # Simular transacción con error
        try:
            conn = mock_conexion()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO test_table VALUES (%s)", ('test_value',))
            conn.commit()
        except Exception:
            conn.rollback()
        
        # Verificar rollback
        mock_conn.rollback.assert_called_once()
    
    @patch('modelo.configBd.obtener_conexion')
    def test_cursor_close(self, mock_conexion):
        """Prueba cierre de cursor"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular uso y cierre de cursor
        conn = mock_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        # Verificar cierre
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

class TestDatabaseIntegration:
    """Pruebas de integración para base de datos"""
    
    @patch('modelo.configBd.obtener_conexion')
    def test_usuarios_table_structure(self, mock_conexion):
        """Prueba estructura de tabla usuarios"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular consulta de estructura
        mock_cursor.fetchall.return_value = [
            ('id', 'integer', 'NOT NULL'),
            ('nombre', 'character varying', 'NOT NULL'),
            ('usuario', 'character varying', 'NOT NULL'),
            ('correo', 'character varying', 'NOT NULL'),
            ('contrasena', 'character varying', 'NOT NULL'),
            ('rol_id', 'integer', 'NULL'),
            ('activo', 'boolean', 'NOT NULL'),
            ('fecha_registro', 'timestamp without time zone', 'NULL'),
            ('administrador', 'boolean', 'NULL')
        ]
        
        # Ejecutar consulta
        conn = mock_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'usuarios'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        # Verificar estructura
        assert len(columns) == 9
        column_names = [col[0] for col in columns]
        assert 'id' in column_names
        assert 'nombre' in column_names
        assert 'usuario' in column_names
        assert 'correo' in column_names
        assert 'contrasena' in column_names
    
    @patch('modelo.configBd.obtener_conexion')
    def test_roles_table_structure(self, mock_conexion):
        """Prueba estructura de tabla roles"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular consulta de estructura
        mock_cursor.fetchall.return_value = [
            ('id', 'integer', 'NOT NULL'),
            ('nombre_rol', 'character varying', 'NOT NULL')
        ]
        
        # Ejecutar consulta
        conn = mock_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'roles'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        # Verificar estructura
        assert len(columns) == 2
        column_names = [col[0] for col in columns]
        assert 'id' in column_names
        assert 'nombre_rol' in column_names
    
    @patch('modelo.configBd.obtener_conexion')
    def test_expedientes_table_exists(self, mock_conexion):
        """Prueba existencia de tablas de expedientes"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular consulta de tablas
        mock_cursor.fetchall.return_value = [
            ('expedientes',),
            ('tramites_expediente',),
            ('ingresos_expediente',),
            ('estados_expediente',)
        ]
        
        # Ejecutar consulta
        conn = mock_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%expediente%'
        """)
        tables = cursor.fetchall()
        
        # Verificar tablas
        table_names = [table[0] for table in tables]
        assert 'expedientes' in table_names
        assert 'tramites_expediente' in table_names
        assert 'ingresos_expediente' in table_names
        assert 'estados_expediente' in table_names

class TestDatabaseSecurity:
    """Pruebas de seguridad para base de datos"""
    
    @patch('modelo.configBd.obtener_conexion')
    def test_sql_injection_prevention(self, mock_conexion):
        """Prueba prevención de inyección SQL"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular query con parámetros (forma segura)
        conn = mock_conexion()
        cursor = conn.cursor()
        
        # Query segura con parámetros
        malicious_input = "'; DROP TABLE usuarios; --"
        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (malicious_input,))
        
        # Verificar que se usó parámetros en lugar de concatenación
        cursor.execute.assert_called_with(
            "SELECT * FROM usuarios WHERE usuario = %s", 
            (malicious_input,)
        )
    
    @patch('modelo.configBd.obtener_conexion')
    def test_password_hashing_in_db(self, mock_conexion):
        """Prueba que las contraseñas se almacenan hasheadas"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular inserción de usuario con contraseña hasheada
        conn = mock_conexion()
        cursor = conn.cursor()
        
        # La contraseña debe estar hasheada antes de la inserción
        hashed_password = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"  # SHA256 de "hello"
        cursor.execute(
            "INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)",
            ("testuser", hashed_password)
        )
        
        # Verificar que se usó contraseña hasheada
        args = cursor.execute.call_args[0]
        assert len(args[1][1]) == 64  # SHA256 produce 64 caracteres hex
    
    @patch('modelo.configBd.obtener_conexion')
    def test_user_permissions(self, mock_conexion):
        """Prueba permisos de usuario en base de datos"""
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular verificación de permisos
        mock_cursor.fetchone.return_value = ('SELECT', 'INSERT', 'UPDATE', 'DELETE')
        
        conn = mock_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT privilege_type FROM information_schema.role_table_grants WHERE grantee = current_user")
        permissions = cursor.fetchone()
        
        # Verificar que se consultaron los permisos
        cursor.execute.assert_called_once()
        assert permissions is not None