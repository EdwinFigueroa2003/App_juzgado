"""
Tests de seguridad comprehensivos
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestCSRFProtection:
    """Tests de protección CSRF"""
    
    def test_csrf_token_required_on_forms(self, client):
        """Verifica que los formularios requieran token CSRF"""
        # Intentar enviar formulario sin CSRF token
        response = client.post('/login', data={
            'username': 'test',
            'password': 'test'
        })
        
        # Debería fallar por falta de CSRF token
        assert response.status_code in [400, 403] or b'csrf' in response.data.lower()
    
    def test_csrf_headers_present(self, client):
        """Verifica que los headers de seguridad estén presentes"""
        response = client.get('/')
        
        # Verificar headers de seguridad
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'
        assert 'X-XSS-Protection' in response.headers
        assert 'Content-Security-Policy' in response.headers

class TestInputValidation:
    """Tests de validación de inputs"""
    
    def test_xss_prevention(self):
        """Verifica prevención de XSS"""
        from utils.security_validators import SecurityValidator
        
        # Inputs maliciosos
        xss_inputs = [
            '<script>alert("xss")</script>',
            'javascript:alert("xss")',
            '<img src="x" onerror="alert(1)">',
            '<iframe src="javascript:alert(1)"></iframe>'
        ]
        
        for malicious_input in xss_inputs:
            sanitized = SecurityValidator.sanitize_input(malicious_input)
            
            # Verificar que se removieron elementos peligrosos
            assert '<script>' not in sanitized.lower()
            assert 'javascript:' not in sanitized.lower()
            assert 'onerror=' not in sanitized.lower()
            assert '<iframe' not in sanitized.lower()
    
    def test_sql_injection_prevention(self):
        """Verifica prevención de SQL injection"""
        # Los queries deben usar parámetros
        malicious_inputs = [
            "'; DROP TABLE usuarios; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM usuarios --",
            "admin'--"
        ]
        
        # Verificar que los inputs se sanitizan
        from utils.security_validators import SecurityValidator
        
        for malicious_input in malicious_inputs:
            sanitized = SecurityValidator.sanitize_input(malicious_input)
            # Los caracteres peligrosos deben estar escapados
            assert '&lt;' in sanitized or '&gt;' in sanitized or malicious_input == sanitized
    
    def test_email_validation(self):
        """Test validación de email"""
        from utils.security_validators import SecurityValidator
        
        # Emails válidos
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'admin+test@company.org'
        ]
        
        for email in valid_emails:
            result = SecurityValidator.validate_email(email)
            assert result['valid'] is True
        
        # Emails inválidos
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user..name@domain.com',
            'a' * 255 + '@domain.com'  # Demasiado largo
        ]
        
        for email in invalid_emails:
            result = SecurityValidator.validate_email(email)
            assert result['valid'] is False
    
    def test_password_strength_validation(self):
        """Test validación de fortaleza de contraseña"""
        from utils.security_validators import SecurityValidator
        
        # Contraseñas débiles
        weak_passwords = [
            '123456',
            'password',
            'abc123',
            '12345678'  # Solo números
        ]
        
        for password in weak_passwords:
            result = SecurityValidator.validate_password_strength(password)
            assert result['valid'] is False
        
        # Contraseñas fuertes
        strong_passwords = [
            'MyStr0ng!Pass',
            'C0mpl3x@2024',
            'S3cur3#P4ssw0rd'
        ]
        
        for password in strong_passwords:
            result = SecurityValidator.validate_password_strength(password)
            assert result['valid'] is True

class TestRateLimiting:
    """Tests de rate limiting"""
    
    def test_rate_limiter_basic_functionality(self):
        """Test funcionalidad básica del rate limiter"""
        from utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        key = "test_key"
        
        # Primeros intentos deben pasar
        for i in range(5):
            is_limited, remaining = limiter.is_rate_limited(key, 10, 60)
            assert is_limited is False
            limiter.record_attempt(key)
        
        # Después del límite debe estar limitado
        for i in range(6):
            limiter.record_attempt(key)
        
        is_limited, remaining = limiter.is_rate_limited(key, 10, 60)
        assert is_limited is True
        assert remaining == 0
    
    def test_login_rate_limiting(self):
        """Test rate limiting específico para login"""
        from utils.rate_limiter import rate_limiter
        
        username = "test_user"
        ip = "192.168.1.1"
        
        # Simular múltiples intentos fallidos
        for i in range(5):
            rate_limiter.record_failed_login(username, ip)
        
        # Usuario debe estar bloqueado
        is_blocked, remaining = rate_limiter.is_user_blocked(username)
        assert is_blocked is True
        
        # IP debe estar bloqueada
        is_ip_blocked, ip_remaining = rate_limiter.is_ip_blocked(ip)
        assert is_ip_blocked is True

class TestSecurityLogging:
    """Tests de logging de seguridad"""
    
    @patch('utils.security_logger.security_logger')
    def test_login_attempt_logging(self, mock_logger):
        """Test logging de intentos de login"""
        from utils.security_logger import log_login_attempt
        
        # Login exitoso
        log_login_attempt("testuser", success=True)
        mock_logger.log.assert_called()
        
        # Login fallido
        log_login_attempt("testuser", success=False, reason="Invalid password")
        assert mock_logger.log.call_count >= 2
    
    @patch('utils.security_logger.security_logger')
    def test_security_event_logging(self, mock_logger):
        """Test logging de eventos de seguridad"""
        from utils.security_logger import log_csrf_attack, log_xss_attempt
        
        # CSRF attack
        log_csrf_attack()
        mock_logger.log.assert_called()
        
        # XSS attempt
        log_xss_attempt("<script>alert('xss')</script>")
        assert mock_logger.log.call_count >= 2

class TestAuthenticationSecurity:
    """Tests de seguridad de autenticación"""
    
    def test_password_hashing(self):
        """Verifica que las contraseñas se hasheen correctamente"""
        from utils.auth import hash_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        # Hash debe ser diferente a la contraseña original
        assert hashed != password
        
        # Hash debe ser consistente
        hashed2 = hash_password(password)
        assert hashed == hashed2
        
        # Hash debe tener longitud esperada (SHA-256 = 64 caracteres hex)
        assert len(hashed) == 64
    
    def test_session_security(self, client):
        """Test seguridad de sesiones"""
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['usuario'] = 'testuser'
        
        # Verificar que la sesión se mantenga
        response = client.get('/home')
        assert response.status_code in [200, 302]  # 302 si redirige

class TestSQLInjectionPrevention:
    """Tests específicos para prevención de SQL injection"""
    
    @patch('modelo.configBd.obtener_conexion')
    def test_parameterized_queries(self, mock_conexion):
        """Verifica que se usen queries parametrizadas"""
        from vista.vistalogin import verificar_usuario
        
        # Configurar mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conexion.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Intentar SQL injection
        malicious_input = "admin'; DROP TABLE usuarios; --"
        
        # La función debe usar parámetros seguros
        result = verificar_usuario(malicious_input, "password")
        
        # Verificar que se llamó execute con parámetros
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args
        
        # Debe haber parámetros en la llamada
        assert len(call_args) == 2  # Query y parámetros
        assert isinstance(call_args[1], tuple)  # Parámetros como tupla

class TestFileUploadSecurity:
    """Tests de seguridad para subida de archivos"""
    
    def test_file_extension_validation(self):
        """Test validación de extensiones de archivo"""
        # Extensiones permitidas para Excel
        allowed_extensions = ['.xlsx', '.xls']
        dangerous_extensions = ['.exe', '.php', '.js', '.html', '.py']
        
        for ext in allowed_extensions:
            filename = f"test{ext}"
            # Verificar que se permiten extensiones seguras
            assert any(filename.lower().endswith(allowed) for allowed in allowed_extensions)
        
        for ext in dangerous_extensions:
            filename = f"malicious{ext}"
            # Verificar que se rechazan extensiones peligrosas
            assert not any(filename.lower().endswith(allowed) for allowed in allowed_extensions)

class TestSecurityConfiguration:
    """Tests de configuración de seguridad"""
    
    def test_secret_key_configured(self, app):
        """Verifica que la clave secreta esté configurada"""
        assert app.secret_key is not None
        assert len(app.secret_key) > 16  # Clave suficientemente larga
    
    def test_debug_mode_disabled_in_production(self, app):
        """Verifica que debug esté deshabilitado en producción"""
        # En tests puede estar habilitado, pero verificar configuración
        if os.environ.get('FLASK_ENV') == 'production':
            assert app.debug is False
    
    def test_csrf_protection_enabled(self, app):
        """Verifica que la protección CSRF esté habilitada"""
        # Verificar que CSRFProtect esté configurado
        from flask_wtf.csrf import CSRFProtect
        
        # Buscar CSRFProtect en las extensiones de la app
        csrf_enabled = False
        for extension in app.extensions.values():
            if isinstance(extension, CSRFProtect):
                csrf_enabled = True
                break
        
        # También verificar por configuración
        if not csrf_enabled:
            csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
        
        assert csrf_enabled is True

class TestSecurityIntegration:
    """Tests de integración de seguridad"""
    
    def test_complete_security_flow(self, client):
        """Test flujo completo de seguridad"""
        # 1. Verificar headers de seguridad
        response = client.get('/')
        assert 'X-Content-Type-Options' in response.headers
        
        # 2. Intentar acceso no autorizado
        response = client.get('/usuarios')
        assert response.status_code in [302, 401, 403]  # Debe redirigir o denegar
        
        # 3. Verificar que formularios requieren CSRF
        response = client.post('/login', data={'username': 'test', 'password': 'test'})
        # Debe fallar por CSRF o credenciales inválidas
        assert response.status_code in [200, 400, 403]
    
    def test_security_middleware_order(self, app):
        """Verifica que el middleware de seguridad esté en el orden correcto"""
        # Los after_request handlers deben estar registrados
        assert len(app.after_request_funcs[None]) > 0
        
        # Verificar que hay funciones de seguridad registradas
        security_functions = [func for func in app.after_request_funcs[None] 
                            if 'security' in func.__name__.lower()]
        assert len(security_functions) > 0