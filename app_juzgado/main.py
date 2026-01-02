#main.py
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os


from vista.vistahome import vistahome
from vista.vistaexpediente import vistaexpediente
from vista.vistasubirexpediente import vistasubirexpediente
from vista.vistaactualizarexpediente import vistaactualizarexpediente
from vista.vistalogin import vistalogin
from vista.vistaroles import vistaroles
from vista.vistaasignacion import vistaasignacion
from vista.vistausuarios import vistausuarios
from vista.vistasecurity import vistasecurity

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
#secret_key = secrets.token_hex(32)
#app.secret_key = secret_key
# Configuración desde variables de entorno
app.secret_key = os.getenv('SECRET_KEY')
app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('CSRF_SECRET_KEY')


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
    app.run(debug=True)
