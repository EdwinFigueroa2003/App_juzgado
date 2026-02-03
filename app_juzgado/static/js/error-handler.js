/**
 * Manejador de errores del lado del cliente
 * Mejora la experiencia del usuario cuando ocurren errores
 */

class ErrorHandler {
    constructor() {
        this.initializeErrorHandling();
        this.setupCSRFTokenRefresh();
    }

    initializeErrorHandling() {
        // Interceptar errores AJAX para mostrar mensajes amigables
        $(document).ajaxError((event, xhr, settings, thrownError) => {
            if (xhr.status === 400 && xhr.responseText.includes('CSRF')) {
                this.showCSRFError();
            } else if (xhr.status === 403) {
                this.showAccessDeniedError();
            } else if (xhr.status === 500) {
                this.showServerError();
            }
        });

        // Manejar errores de red
        window.addEventListener('offline', () => {
            this.showNetworkError('offline');
        });

        window.addEventListener('online', () => {
            this.hideNetworkError();
        });
    }

    setupCSRFTokenRefresh() {
        // Refrescar token CSRF automáticamente cada 30 minutos
        setInterval(() => {
            this.refreshCSRFToken();
        }, 30 * 60 * 1000);
    }

    showCSRFError() {
        const modal = this.createErrorModal({
            title: 'Token de Seguridad Expirado',
            message: 'Tu sesión ha expirado por seguridad. La página se recargará automáticamente.',
            type: 'warning',
            autoReload: true,
            countdown: 5
        });
        modal.show();
    }

    showAccessDeniedError() {
        const modal = this.createErrorModal({
            title: 'Acceso Denegado',
            message: 'No tienes permisos para realizar esta acción.',
            type: 'danger',
            actions: [
                {
                    text: 'Iniciar Sesión',
                    class: 'btn-primary',
                    action: () => window.location.href = '/login'
                },
                {
                    text: 'Volver al Inicio',
                    class: 'btn-secondary',
                    action: () => window.location.href = '/'
                }
            ]
        });
        modal.show();
    }

    showServerError() {
        const modal = this.createErrorModal({
            title: 'Error del Servidor',
            message: 'Se ha producido un error interno. Por favor, intenta nuevamente.',
            type: 'warning',
            actions: [
                {
                    text: 'Reintentar',
                    class: 'btn-warning',
                    action: () => window.location.reload()
                },
                {
                    text: 'Volver al Inicio',
                    class: 'btn-secondary',
                    action: () => window.location.href = '/'
                }
            ]
        });
        modal.show();
    }

    showNetworkError(type) {
        const message = type === 'offline' 
            ? 'Sin conexión a internet. Verifica tu conexión de red.'
            : 'Error de conexión. Verifica tu conexión de red.';

        const toast = this.createToast({
            title: 'Problema de Conexión',
            message: message,
            type: 'warning',
            persistent: type === 'offline'
        });
        toast.show();
    }

    hideNetworkError() {
        // Ocultar toast de error de red cuando se recupere la conexión
        $('.toast[data-error-type="network"]').toast('hide');
        
        const toast = this.createToast({
            title: 'Conexión Restaurada',
            message: 'La conexión a internet se ha restablecido.',
            type: 'success',
            duration: 3000
        });
        toast.show();
    }

    createErrorModal(options) {
        const modalId = 'errorModal' + Date.now();
        let actionsHtml = '';
        
        if (options.actions) {
            actionsHtml = options.actions.map(action => 
                `<button type="button" class="btn ${action.class}" data-action="${action.text}">${action.text}</button>`
            ).join(' ');
        }

        let countdownHtml = '';
        if (options.autoReload && options.countdown) {
            countdownHtml = `<div class="mt-3">
                <small class="text-muted">
                    <i class="fas fa-clock"></i> 
                    Recargando automáticamente en <span id="countdown-${modalId}">${options.countdown}</span> segundos
                </small>
            </div>`;
        }

        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" role="dialog">
                <div class="modal-dialog modal-dialog-centered" role="document">
                    <div class="modal-content">
                        <div class="modal-header bg-${options.type} text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-exclamation-triangle"></i>
                                ${options.title}
                            </h5>
                        </div>
                        <div class="modal-body">
                            <p>${options.message}</p>
                            ${countdownHtml}
                        </div>
                        <div class="modal-footer">
                            ${actionsHtml}
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Cerrar</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        $('body').append(modalHtml);
        const modal = $(`#${modalId}`);

        // Configurar acciones
        if (options.actions) {
            options.actions.forEach(action => {
                modal.find(`[data-action="${action.text}"]`).click(action.action);
            });
        }

        // Configurar auto-reload
        if (options.autoReload && options.countdown) {
            let countdown = options.countdown;
            const countdownElement = $(`#countdown-${modalId}`);
            
            const timer = setInterval(() => {
                countdown--;
                countdownElement.text(countdown);
                
                if (countdown <= 0) {
                    clearInterval(timer);
                    window.location.reload();
                }
            }, 1000);
        }

        // Limpiar modal al cerrarse
        modal.on('hidden.bs.modal', () => {
            modal.remove();
        });

        return modal;
    }

    createToast(options) {
        const toastId = 'toast' + Date.now();
        const toastHtml = `
            <div class="toast" id="${toastId}" role="alert" data-error-type="network" 
                 style="position: fixed; top: 20px; right: 20px; z-index: 1050;">
                <div class="toast-header bg-${options.type} text-white">
                    <strong class="mr-auto">
                        <i class="fas fa-wifi"></i>
                        ${options.title}
                    </strong>
                    <button type="button" class="ml-2 mb-1 close text-white" data-dismiss="toast">
                        <span>&times;</span>
                    </button>
                </div>
                <div class="toast-body">
                    ${options.message}
                </div>
            </div>
        `;

        $('body').append(toastHtml);
        const toast = $(`#${toastId}`);

        // Configurar duración
        const duration = options.persistent ? false : (options.duration || 5000);
        
        toast.on('hidden.bs.toast', () => {
            toast.remove();
        });

        return {
            show: () => toast.toast({ delay: duration }).toast('show'),
            hide: () => toast.toast('hide')
        };
    }

    async refreshCSRFToken() {
        try {
            const response = await fetch('/csrf-token', {
                method: 'GET',
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                // Actualizar todos los tokens CSRF en la página
                $('input[name="csrf_token"]').val(data.csrf_token);
                $('meta[name="csrf-token"]').attr('content', data.csrf_token);
            }
        } catch (error) {
            console.warn('No se pudo refrescar el token CSRF:', error);
        }
    }
}

// Inicializar el manejador de errores cuando el DOM esté listo
$(document).ready(() => {
    new ErrorHandler();
});

// Exportar para uso global
window.ErrorHandler = ErrorHandler;