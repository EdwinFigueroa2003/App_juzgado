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
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
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

@app.route('/')
def home():
    return render_template('login.html')

if __name__ == '__main__':
    # Configuración para Railway
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
