#main.py
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os

# Cargar variables de entorno ANTES de importar otros módulos
load_dotenv()  # Busca .env en directorio actual
load_dotenv(dotenv_path='app_juzgado/.env')  # También busca en app_juzgado/.env

from vista.vistahome import vistahome
from vista.vistaexpediente import vistaexpediente
from vista.vistasubirexpediente import vistasubirexpediente
from vista.vistaactualizarexpediente import vistaactualizarexpediente
from vista.vistalogin import vistalogin
from vista.vistaroles import vistaroles
from vista.vistaasignacion import vistaasignacion
from vista.vistausuarios import vistausuarios
from vista.vistasecurity import vistasecurity
from vista.vistaconsulta import vistaconsulta
from vista.vistatest import vistatest  # Blueprint de pruebas

app = Flask(__name__)

# Configuración desde variables de entorno
app.secret_key = os.getenv('SECRET_KEY')
app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('CSRF_SECRET_KEY')

# Debug info para desarrollo
if os.getenv('FLASK_ENV') == 'development':
    print("🔧 Modo desarrollo activado")
    print(f"   SECRET_KEY: {'✅ Configurada' if app.secret_key else '❌ No configurada'}")
    print(f"   CSRF_SECRET_KEY: {'✅ Configurada' if app.config.get('WTF_CSRF_SECRET_KEY') else '❌ No configurada'}")

# 🔒 SEGURIDAD: Protección CSRF
csrf = CSRFProtect(app)

# Exentar APIs públicas del CSRF
csrf.exempt('vistaconsulta.buscar_expediente')
csrf.exempt('vistaconsulta.buscar_por_nombres')
csrf.exempt('vistaconsulta.turnos_del_dia')
csrf.exempt('vistaconsulta.turnos_publicos')

# 🔒 SEGURIDAD: Headers de seguridad
@app.after_request
def add_security_headers(response):
    # Headers básicos de seguridad
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://code.jquery.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    return response

app.register_blueprint(vistahome)
app.register_blueprint(vistaexpediente)
app.register_blueprint(vistasubirexpediente)
app.register_blueprint(vistaactualizarexpediente)
app.register_blueprint(vistalogin)
app.register_blueprint(vistaroles)
app.register_blueprint(vistaasignacion)
app.register_blueprint(vistausuarios)
app.register_blueprint(vistasecurity)
app.register_blueprint(vistaconsulta)
app.register_blueprint(vistatest)  # Blueprint de pruebas

# 🔒 MANEJADOR ESPECÍFICO PARA ERRORES CSRF
from flask_wtf.csrf import CSRFError

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Maneja específicamente errores de CSRF token"""
    # Detectar si es una página pública
    is_public_page = (
        request.endpoint and 
        ('consulta' in request.endpoint or 
         'turnos_publicos' in request.endpoint or
         request.path.startswith('/consulta') or
         request.path.startswith('/api/buscar'))
    )
    
    if is_public_page:
        return render_template('errors/400_public.html', csrf_error=True, reason=str(e)), 400
    else:
        return render_template('errors/400.html', csrf_error=True, reason=str(e)), 400

# 🚨 MANEJADORES DE ERRORES
@app.errorhandler(400)
def bad_request_error(error):
    """Maneja errores 400 - Bad Request (incluyendo CSRF token mismatch)"""
    # Detectar si es una página pública (consulta)
    is_public_page = (
        request.endpoint and 
        ('consulta' in request.endpoint or 
         'turnos_publicos' in request.endpoint or
         request.path.startswith('/consulta') or
         request.path.startswith('/api/buscar'))
    )
    
    if is_public_page:
        return render_template('errors/400_public.html', csrf_error=True), 400
    else:
        return render_template('errors/400.html', csrf_error=True), 400

@app.errorhandler(403)
def forbidden_error(error):
    """Maneja errores 403 - Forbidden"""
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    """Maneja errores 404 - Not Found"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Maneja errores 500 - Internal Server Error"""
    return render_template('errors/500.html'), 500

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/csrf-token')
def csrf_token():
    """Endpoint para obtener un nuevo token CSRF"""
    from flask_wtf.csrf import generate_csrf
    return {'csrf_token': generate_csrf()}

if __name__ == '__main__':
    # Configuración para Railway
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
