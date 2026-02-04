from flask import Blueprint, render_template, request, abort
from flask_wtf.csrf import CSRFError

# Blueprint para pruebas de errores
vistatest = Blueprint('vistatest', __name__, template_folder='templates')

@vistatest.route('/test/error-400-external')
def test_error_400_external():
    """Forzar error 400 para usuarios completamente externos"""
    # Simular que es una página externa
    request.endpoint = 'vistaconsulta.consulta_publica'
    return render_template('errors/400_external.html', csrf_error=True, reason="Sesión expirada (PRUEBA)"), 400

@vistatest.route('/test/error-400-public')
def test_error_400_public():
    """Forzar error 400 para páginas públicas"""
    # Simular que es una página pública
    request.endpoint = 'vistaconsulta.consulta_publica'
    return render_template('errors/400_public.html', csrf_error=True, reason="Token CSRF inválido (PRUEBA)"), 400

@vistatest.route('/test/error-400-private')
def test_error_400_private():
    """Forzar error 400 para páginas privadas"""
    # Simular que es una página privada
    request.endpoint = 'idvistaexpediente.vista_expediente'
    return render_template('errors/400.html', csrf_error=True, reason="Token CSRF inválido (PRUEBA)"), 400

@vistatest.route('/test/error-403')
def test_error_403():
    """Forzar error 403"""
    return render_template('errors/403.html'), 403

@vistatest.route('/test/error-404')
def test_error_404():
    """Forzar error 404"""
    return render_template('errors/404.html'), 404

@vistatest.route('/test/error-500')
def test_error_500():
    """Forzar error 500"""
    return render_template('errors/500.html'), 500

@vistatest.route('/test/csrf-error-public')
def test_csrf_error_public():
    """Forzar error CSRF específico para páginas públicas"""
    # Simular CSRFError
    error = CSRFError("The CSRF token is missing.")
    # Simular que es una página pública
    request.endpoint = 'vistaconsulta.consulta_publica'
    return render_template('errors/400_public.html', csrf_error=True, reason=str(error)), 400

@vistatest.route('/test/csrf-error-private')
def test_csrf_error_private():
    """Forzar error CSRF específico para páginas privadas"""
    # Simular CSRFError
    error = CSRFError("The CSRF tokens do not match.")
    # Simular que es una página privada
    request.endpoint = 'idvistaexpediente.vista_expediente'
    return render_template('errors/400.html', csrf_error=True, reason=str(error)), 400

@vistatest.route('/test/menu')
def test_menu():
    """Página de pruebas con enlaces a todos los errores"""
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Menú de Pruebas de Errores</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-10">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h3 class="mb-0">
                                <i class="fas fa-bug"></i>
                                Menú de Pruebas de Errores
                            </h3>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h5><i class="fas fa-shield-alt text-warning"></i> Errores CSRF (400)</h5>
                                    <div class="list-group mb-4">
                                        <a href="/test/error-400-external" class="list-group-item list-group-item-action">
                                            <i class="fas fa-globe text-success"></i>
                                            Error 400 - Usuario Externo
                                            <small class="d-block text-muted">Para ciudadanos sin acceso al sistema</small>
                                        </a>
                                        <a href="/test/error-400-public" class="list-group-item list-group-item-action">
                                            <i class="fas fa-users text-info"></i>
                                            Error 400 - Usuario Público Interno
                                            <small class="d-block text-muted">Para usuarios con acceso limitado</small>
                                        </a>
                                        <a href="/test/error-400-private" class="list-group-item list-group-item-action">
                                            <i class="fas fa-user-shield text-warning"></i>
                                            Error 400 - Usuario Privado
                                            <small class="d-block text-muted">Para administradores del sistema</small>
                                        </a>
                                        <a href="/test/csrf-error-public" class="list-group-item list-group-item-action">
                                            <i class="fas fa-exclamation-triangle text-danger"></i>
                                            CSRF Error - Página Pública
                                            <small class="d-block text-muted">Error específico de CSRF</small>
                                        </a>
                                        <a href="/test/csrf-error-private" class="list-group-item list-group-item-action">
                                            <i class="fas fa-exclamation-triangle text-danger"></i>
                                            CSRF Error - Página Privada
                                            <small class="d-block text-muted">Error específico de CSRF</small>
                                        </a>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <h5><i class="fas fa-exclamation-circle text-danger"></i> Otros Errores</h5>
                                    <div class="list-group mb-4">
                                        <a href="/test/error-403" class="list-group-item list-group-item-action">
                                            <i class="fas fa-ban text-danger"></i>
                                            Error 403 - Acceso Denegado
                                        </a>
                                        <a href="/test/error-404" class="list-group-item list-group-item-action">
                                            <i class="fas fa-search text-info"></i>
                                            Error 404 - Página No Encontrada
                                        </a>
                                        <a href="/test/error-500" class="list-group-item list-group-item-action">
                                            <i class="fas fa-server text-warning"></i>
                                            Error 500 - Error Interno
                                        </a>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="alert alert-info">
                                <h6><i class="fas fa-info-circle"></i> Instrucciones:</h6>
                                <ul class="mb-0">
                                    <li><strong>Páginas Públicas:</strong> Usan base_public.html (sin menú admin)</li>
                                    <li><strong>Páginas Privadas:</strong> Usan base.html (con menú admin)</li>
                                    <li><strong>Auto-recarga:</strong> Las páginas públicas se recargan en 15s, las privadas en 30s</li>
                                    <li><strong>Navegación:</strong> Cada error tiene botones específicos para su contexto</li>
                                </ul>
                            </div>
                            
                            <div class="text-center">
                                <a href="/consulta" class="btn btn-success me-2">
                                    <i class="fas fa-search"></i> Ir a Consulta Pública
                                </a>
                                <a href="/home" class="btn btn-primary">
                                    <i class="fas fa-home"></i> Ir a Dashboard
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''