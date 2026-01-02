/* =======================================
   JAVASCRIPT CONSOLIDADO - APLICACIÓN JUDICIAL
   Funciones centralizadas para toda la aplicación
   ======================================= */

/* =======================================
   FUNCIONES GENERALES
   ======================================= */

// Función para hacer scroll a los detalles
function scrollToDetails() {
    const resultados = document.querySelector('#resultados-expedientes');
    if (resultados) {
        resultados.scrollIntoView({ behavior: 'smooth' });
    }
}

// Función para scroll suave a los resultados
function scrollToResults() {
    const resultados = document.getElementById('resultados-expedientes');
    if (resultados) {
        resultados.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Función para activar la pestaña de filtros usando Bootstrap 5
function activarTabFiltros() {
    const filtrarTab = document.getElementById('filtrar-tab');
    if (filtrarTab) {
        // Usar Bootstrap 5 Tab API
        const tab = new bootstrap.Tab(filtrarTab);
        tab.show();
    }
}

/* =======================================
   FUNCIONES DE EXPEDIENTES
   ======================================= */

// Función para copiar radicado al clipboard
function copiarRadicado(radicado) {
    navigator.clipboard.writeText(radicado).then(function() {
        // Mostrar mensaje de éxito
        const toast = document.createElement('div');
        toast.className = 'alert alert-success position-fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        toast.innerHTML = '<i class="fas fa-check"></i> Radicado copiado: ' + radicado;
        document.body.appendChild(toast);
        
        setTimeout(function() {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 3000);
    }).catch(function(err) {
        console.error('Error al copiar radicado: ', err);
        // Fallback para navegadores que no soportan clipboard API
        const textArea = document.createElement('textarea');
        textArea.value = radicado;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        // Mostrar mensaje de éxito
        const toast = document.createElement('div');
        toast.className = 'alert alert-success position-fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        toast.innerHTML = '<i class="fas fa-check"></i> Radicado copiado: ' + radicado;
        document.body.appendChild(toast);
        
        setTimeout(function() {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 3000);
    });
}

// Función para alternar detalles del expediente en vista de filtros
function toggleExpedienteDetails(expedienteId) {
    const detailsDiv = document.querySelector('.expediente-details[data-expediente-id="' + expedienteId + '"]');
    
    // Buscar el botón de varias maneras para asegurar que lo encontramos
    let button = document.querySelector('button[onclick*="toggleExpedienteDetails(\'' + expedienteId + '\')"]');
    if (!button) {
        // Buscar dentro del card que contiene este expediente
        const card = detailsDiv ? detailsDiv.closest('.card') : null;
        if (card) {
            const buttons = card.querySelectorAll('button');
            for (let btn of buttons) {
                if (btn.textContent.includes('Ver más') || btn.textContent.includes('Ver menos')) {
                    button = btn;
                    break;
                }
            }
        }
    }
    
    if (!detailsDiv) {
        console.error('No se encontró el elemento de detalles para el expediente:', expedienteId);
        return;
    }
    
    if (!button) {
        console.error('No se encontró el botón para el expediente:', expedienteId);
        return;
    }
    
    // Verificar si está oculto
    const isHidden = detailsDiv.classList.contains('expediente-details-hidden') || 
                     detailsDiv.style.display === 'none' || 
                     getComputedStyle(detailsDiv).display === 'none';
    
    if (isHidden) {
        // Mostrar detalles
        detailsDiv.classList.remove('expediente-details-hidden');
        detailsDiv.style.display = 'block';
        button.innerHTML = '<i class="fas fa-eye-slash"></i> Ver menos';
        button.title = 'Ocultar detalles';
        
        // Scroll suave hacia los detalles
        setTimeout(function() {
            detailsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    } else {
        // Ocultar detalles
        detailsDiv.classList.add('expediente-details-hidden');
        detailsDiv.style.display = 'none';
        button.innerHTML = '<i class="fas fa-eye"></i> Ver más';
        button.title = 'Ver detalles completos';
    }
}

// Función para imprimir expediente
function imprimirExpediente(expedienteId) {
    const expediente = document.querySelector('[data-expediente-id="' + expedienteId + '"]');
    if (expediente) {
        const ventanaImpresion = window.open('', '_blank');
        ventanaImpresion.document.write(
            '<html>' +
                '<head>' +
                    '<title>Expediente ' + expedienteId + '</title>' +
                    '<style>' +
                        'body { font-family: Arial, sans-serif; margin: 20px; }' +
                        '.table { width: 100%; border-collapse: collapse; }' +
                        '.table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }' +
                        '.table th { background-color: #f8f9fa; }' +
                    '</style>' +
                '</head>' +
                '<body>' +
                    expediente.innerHTML +
                '</body>' +
            '</html>'
        );
        ventanaImpresion.document.close();
        ventanaImpresion.print();
    }
}

/* =======================================
   FUNCIONES DE TEXTO EXPANDIBLE
   ======================================= */

// Función para alternar entre vista previa y texto completo del auto/resolución
function toggleAutoText(button) {
    const container = button.closest('.auto-text-container');
    if (!container) return;
    
    const preview = container.querySelector('.auto-preview');
    const full = container.querySelector('.auto-full');
    
    if (!preview || !full) return;
    
    if (full.style.display === 'none') {
        // Mostrar texto completo
        preview.style.display = 'none';
        full.style.display = 'block';
        button.innerHTML = '<i class="fas fa-compress"></i> Ver menos';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-outline-secondary');
    } else {
        // Mostrar vista previa
        preview.style.display = 'inline';
        full.style.display = 'none';
        button.innerHTML = '<i class="fas fa-expand"></i> Ver completo';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-outline-primary');
    }
}

// Función para alternar entre vista previa y texto completo de observaciones
function toggleObservacionesText(button) {
    const container = button.closest('.observaciones-container');
    if (!container) return;
    
    const preview = container.querySelector('.observaciones-preview');
    const full = container.querySelector('.observaciones-full');
    
    if (!preview || !full) return;
    
    if (full.style.display === 'none') {
        // Mostrar texto completo
        preview.style.display = 'none';
        full.style.display = 'block';
        button.innerHTML = '<i class="fas fa-compress"></i> Ver menos';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-outline-secondary');
    } else {
        // Mostrar vista previa
        preview.style.display = 'inline';
        full.style.display = 'none';
        button.innerHTML = '<i class="fas fa-expand"></i> Ver completo';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-outline-primary');
    }
}

// Función para alternar entre vista previa y texto completo de observaciones de ingresos
function toggleObservacionesIngresoText(button) {
    const container = button.closest('.observaciones-ingreso-container');
    if (!container) return;
    
    const preview = container.querySelector('.observaciones-ingreso-preview');
    const full = container.querySelector('.observaciones-ingreso-full');
    
    if (!preview || !full) return;
    
    if (full.style.display === 'none') {
        // Mostrar texto completo
        preview.style.display = 'none';
        full.style.display = 'block';
        button.innerHTML = '<i class="fas fa-compress"></i> Ver menos';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-outline-secondary');
    } else {
        // Mostrar vista previa
        preview.style.display = 'inline';
        full.style.display = 'none';
        button.innerHTML = '<i class="fas fa-expand"></i> Ver completo';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-outline-primary');
    }
}

// Función para alternar entre vista previa y texto completo de observaciones de estados
function toggleObservacionesEstadoText(button) {
    const container = button.closest('.observaciones-estado-container');
    if (!container) return;
    
    const preview = container.querySelector('.observaciones-estado-preview');
    const full = container.querySelector('.observaciones-estado-full');
    
    if (!preview || !full) return;
    
    if (full.style.display === 'none') {
        // Mostrar texto completo
        preview.style.display = 'none';
        full.style.display = 'block';
        button.innerHTML = '<i class="fas fa-compress"></i> Ver menos';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-outline-secondary');
    } else {
        // Mostrar vista previa
        preview.style.display = 'inline';
        full.style.display = 'none';
        button.innerHTML = '<i class="fas fa-expand"></i> Ver completo';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-outline-primary');
    }
}

/* =======================================
   FUNCIONES DE PAGINACIÓN
   ======================================= */

// Función para mostrar indicador de carga en paginación
function mostrarCargaPaginacion(enlace) {
    // Agregar indicador de carga
    const spinner = document.createElement('span');
    spinner.className = 'spinner-border spinner-border-sm mr-2';
    spinner.setAttribute('role', 'status');
    spinner.setAttribute('aria-hidden', 'true');
    
    enlace.insertBefore(spinner, enlace.firstChild);
    enlace.classList.add('disabled');
    
    return true; // Permitir que el enlace continúe
}

/* =======================================
   FUNCIONES DE ACTUALIZAR EXPEDIENTE
   ======================================= */

function quitarResponsable() {
    if (confirm('¿Está seguro de que desea quitar el responsable de este expediente?\n\nEsto dejará el expediente sin asignar a ningún rol.')) {
        // Enviar el formulario oculto para quitar responsable
        const form = document.getElementById('form-quitar-responsable');
        if (form) {
            form.submit();
        }
    }
}

// Función alternativa para usar el selector
function cambiarResponsable() {
    const selector = document.getElementById('rol_responsable');
    if (!selector) return true;
    
    if (selector.value === '') {
        // Si selecciona "Sin Asignar", mostrar confirmación
        if (confirm('¿Confirma que desea dejar este expediente sin responsable asignado?')) {
            // Mantener la selección
            return true;
        } else {
            // Revertir la selección si cancela
            selector.selectedIndex = selector.selectedIndex > 0 ? selector.selectedIndex : 0;
            return false;
        }
    }
    return true;
}

// Función para alternar ingresos adicionales en actualizar expediente
function toggleIngresosAdicionales() {
    const ingresosAdicionales = document.getElementById('ingresos-adicionales');
    const button = event.target.closest('button');
    
    if (!ingresosAdicionales || !button) return;
    
    if (ingresosAdicionales.style.display === 'none') {
        // Mostrar ingresos adicionales
        ingresosAdicionales.style.display = '';
        button.innerHTML = '<i class="fas fa-eye-slash"></i> Ver menos';
        button.classList.remove('btn-outline-info');
        button.classList.add('btn-outline-secondary');
    } else {
        // Ocultar ingresos adicionales
        ingresosAdicionales.style.display = 'none';
        const totalIngresos = document.querySelectorAll('#ingresos-adicionales tr').length + 2;
        button.innerHTML = '<i class="fas fa-eye"></i> Ver todos (' + totalIngresos + ')';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-outline-info');
    }
}

// Función para alternar estados adicionales en actualizar expediente
function toggleEstadosAdicionales() {
    const estadosAdicionales = document.getElementById('estados-adicionales');
    const button = event.target.closest('button');
    
    if (!estadosAdicionales || !button) return;
    
    if (estadosAdicionales.style.display === 'none') {
        // Mostrar estados adicionales
        estadosAdicionales.style.display = '';
        button.innerHTML = '<i class="fas fa-eye-slash"></i> Ver menos';
        button.classList.remove('btn-outline-warning');
        button.classList.add('btn-outline-secondary');
    } else {
        // Ocultar estados adicionales
        estadosAdicionales.style.display = 'none';
        const totalEstados = document.querySelectorAll('#estados-adicionales tr').length + 2;
        button.innerHTML = '<i class="fas fa-eye"></i> Ver todos (' + totalEstados + ')';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-outline-warning');
    }
}

/* =======================================
   FUNCIONES DE LOGIN
   ======================================= */

// Auto-focus en el campo de usuario del login
function inicializarLogin() {
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.focus();
    }
    
    // Efecto de loading en el botón al enviar
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function() {
            const btn = document.querySelector('button[type="submit"]');
            if (btn) {
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Iniciando sesión...';
                btn.disabled = true;
            }
        });
    }
}

/* =======================================
   FUNCIONES DE DASHBOARD
   ======================================= */

// Función para crear gráfico de estados
function crearGraficoEstados(labels, data) {
    const ctx = document.getElementById('estadosChart');
    if (ctx && labels && data) {
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#4e73df',
                        '#1cc88a', 
                        '#36b9cc',
                        '#f6c23e',
                        '#e74a3b',
                        '#858796'
                    ],
                    hoverBackgroundColor: [
                        '#2e59d9',
                        '#17a673',
                        '#2c9faf',
                        '#f4b619',
                        '#e02424',
                        '#6c757d'
                    ],
                    hoverBorderColor: "rgba(234, 236, 244, 1)",
                }],
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                cutout: '80%',
            },
        });
    }
}

// Auto-refresh del dashboard cada 5 minutos
function iniciarAutoRefreshDashboard() {
    setTimeout(function() {
        location.reload();
    }, 300000); // 5 minutos
}

/* =======================================
   FUNCIONES DE ROLES
   ======================================= */

let accionPendiente = null;

function asignarRol(usuarioId, rol_id) {
    const nombreRol = rol_id === 'ESCRIBIENTE' ? 'Escribiente' : 'Sustanciador';
    const mensajeElement = document.getElementById('mensaje-confirmacion');
    if (mensajeElement) {
        mensajeElement.textContent = `¿Está seguro de que desea asignar el rol de ${nombreRol} a este usuario?`;
    }
    
    accionPendiente = function() {
        const usuarioIdInput = document.getElementById('usuario_id_asignar');
        const rolInput = document.getElementById('rol_asignar');
        const form = document.getElementById('form-asignar-rol');
        
        if (usuarioIdInput) usuarioIdInput.value = usuarioId;
        if (rolInput) rolInput.value = rol_id;
        if (form) form.submit();
    };
    
    // Usar Bootstrap 5 modal API
    const modal = document.getElementById('modalConfirmacion');
    if (modal) {
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
}

function removerRol(usuarioId) {
    const mensajeElement = document.getElementById('mensaje-confirmacion');
    if (mensajeElement) {
        mensajeElement.textContent = '¿Está seguro de que desea remover el rol de este usuario?';
    }
    
    accionPendiente = function() {
        const usuarioIdInput = document.getElementById('usuario_id_remover');
        const form = document.getElementById('form-remover-rol');
        
        if (usuarioIdInput) usuarioIdInput.value = usuarioId;
        if (form) form.submit();
    };
    
    // Usar Bootstrap 5 modal API
    const modal = document.getElementById('modalConfirmacion');
    if (modal) {
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
}

function asignarRolesAleatorios() {
    const mensajeElement = document.getElementById('mensaje-confirmacion');
    if (mensajeElement) {
        mensajeElement.innerHTML = 
            '<strong>¿Está seguro de que desea asignar roles aleatorios a TODOS los usuarios?</strong><br>' +
            '<small class="text-muted">Esta acción asignará aleatoriamente roles de Escribiente o Sustanciador a todos los usuarios del sistema.</small>';
    }
    
    accionPendiente = function() {
        const form = document.getElementById('form-roles-aleatorios');
        if (form) form.submit();
    };
    
    // Usar Bootstrap 5 modal API
    const modal = document.getElementById('modalConfirmacion');
    if (modal) {
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
}

function removerTodosRoles() {
    const mensajeElement = document.getElementById('mensaje-confirmacion');
    if (mensajeElement) {
        mensajeElement.innerHTML = 
            '<strong>¿Está seguro de que desea remover TODOS los roles asignados?</strong><br>' +
            '<small class="text-muted">Esta acción dejará a todos los usuarios sin rol asignado.</small>';
    }
    
    accionPendiente = function() {
        const form = document.getElementById('form-remover-todos-roles');
        if (form) form.submit();
    };
    
    // Usar Bootstrap 5 modal API
    const modal = document.getElementById('modalConfirmacion');
    if (modal) {
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
}

/* =======================================
   FUNCIONES DE ASIGNACIÓN MASIVA
   ======================================= */

// Funciones para asignación masiva
function mostrarCampoValor() {
    const criterio = document.getElementById('criterio_masivo');
    const campoTexto = document.getElementById('valor_criterio');
    const campoEstado = document.getElementById('valor_estado');
    const ayuda = document.getElementById('ayuda_criterio');
    
    if (!criterio || !campoTexto || !campoEstado || !ayuda) return;
    
    // Ocultar todos los campos primero
    campoTexto.style.display = 'none';
    campoEstado.style.display = 'none';
    ayuda.style.display = 'none';
    
    // Limpiar valores
    campoTexto.value = '';
    campoEstado.value = '';
    
    // Mostrar el campo apropiado según el criterio
    switch(criterio.value) {
        case 'estado':
            campoEstado.style.display = 'block';
            ayuda.style.display = 'block';
            ayuda.textContent = 'Selecciona el estado para asignar expedientes';
            break;
        case 'tipo_tramite':
            campoTexto.style.display = 'block';
            campoTexto.placeholder = 'Ej: Tutela, Amparo, etc.';
            ayuda.style.display = 'block';
            ayuda.textContent = 'Ingresa el tipo de trámite (búsqueda parcial)';
            break;
        case 'juzgado_origen':
            campoTexto.style.display = 'block';
            campoTexto.placeholder = 'Ej: Juzgado 1, Tribunal, etc.';
            ayuda.style.display = 'block';
            ayuda.textContent = 'Ingresa el juzgado de origen (búsqueda parcial)';
            break;
        case 'sin_responsable':
        case 'todos':
            // No necesitan campo adicional
            break;
    }
}

function confirmarAsignacionMasiva() {
    const criterio = document.getElementById('criterio_masivo');
    const rol = document.getElementById('rol_masivo');
    const valorTexto = document.getElementById('valor_criterio');
    const valorEstado = document.getElementById('valor_estado');
    
    if (!criterio || !rol) return false;
    
    const valor = (valorTexto ? valorTexto.value : '') || (valorEstado ? valorEstado.value : '');
    
    let mensaje = '';
    
    // Manejar limpieza de responsables
    if (rol.value === 'LIMPIAR') {
        switch(criterio.value) {
            case 'sin_responsable':
                mensaje = `Los expedientes sin responsable ya no tienen responsable asignado. Esta acción no tendrá efecto.`;
                alert(mensaje);
                return false;
            case 'estado':
                mensaje = `¿Está seguro de QUITAR el responsable a todos los expedientes con estado "${valor}"?\n\nEsto dejará estos expedientes sin responsable asignado.`;
                break;
            case 'tipo_tramite':
                mensaje = `¿Está seguro de QUITAR el responsable a todos los expedientes que contengan "${valor}" en el tipo de trámite?\n\nEsto dejará estos expedientes sin responsable asignado.`;
                break;
            case 'juzgado_origen':
                mensaje = `¿Está seguro de QUITAR el responsable a todos los expedientes que contengan "${valor}" en el juzgado de origen?\n\nEsto dejará estos expedientes sin responsable asignado.`;
                break;
            case 'todos':
                mensaje = `ADVERTENCIA EXTREMA \n\n¿Está COMPLETAMENTE SEGURO de QUITAR TODOS los responsables de TODOS los expedientes del sistema?\n\nEsta acción dejará TODOS los expedientes sin responsable asignado.\nEsta operación es IRREVERSIBLE.\n\nEscriba "LIMPIAR TODO" para continuar:`;
                const confirmacionLimpiar = prompt(mensaje);
                return confirmacionLimpiar === 'LIMPIAR TODO';
            default:
                alert('Debe seleccionar un criterio válido');
                return false;
        }
        return confirm(mensaje);
    }
    
    // Manejar asignación aleatoria
    if (rol.value === 'ALEATORIO') {
        switch(criterio.value) {
            case 'sin_responsable':
                mensaje = `¿Está seguro de asignar roles ALEATORIOS (ESCRIBIENTE/SUSTANCIADOR) a TODOS los expedientes que no tienen responsable asignado?\n\nCada expediente recibirá un rol aleatorio.`;
                break;
            case 'estado':
                mensaje = `¿Está seguro de asignar roles ALEATORIOS (ESCRIBIENTE/SUSTANCIADOR) a todos los expedientes con estado "${valor}"?\n\nCada expediente recibirá un rol aleatorio.`;
                break;
            case 'tipo_tramite':
                mensaje = `¿Está seguro de asignar roles ALEATORIOS (ESCRIBIENTE/SUSTANCIADOR) a todos los expedientes que contengan "${valor}" en el tipo de trámite?\n\nCada expediente recibirá un rol aleatorio.`;
                break;
            case 'juzgado_origen':
                mensaje = `¿Está seguro de asignar roles ALEATORIOS (ESCRIBIENTE/SUSTANCIADOR) a todos los expedientes que contengan "${valor}" en el juzgado de origen?\n\nCada expediente recibirá un rol aleatorio.`;
                break;
            case 'todos':
                mensaje = `ADVERTENCIA CRÍTICA \n\n¿Está COMPLETAMENTE SEGURO de asignar roles ALEATORIOS (ESCRIBIENTE/SUSTANCIADOR) a TODOS los expedientes del sistema?\n\nEsta acción afectará TODOS los expedientes sin excepción.\nCada expediente recibirá un rol aleatorio.\n\nEscriba "CONFIRMAR ALEATORIO" para continuar:`;
                const confirmacion = prompt(mensaje);
                return confirmacion === 'CONFIRMAR ALEATORIO';
            default:
                alert('Debe seleccionar un criterio válido');
                return false;
        }
        return confirm(mensaje);
    }
    
    // Manejar asignación de rol específico (lógica original)
    switch(criterio.value) {
        case 'sin_responsable':
            mensaje = `¿Está seguro de asignar el rol "${rol.value}" a TODOS los expedientes que no tienen responsable asignado?`;
            break;
        case 'estado':
            mensaje = `¿Está seguro de asignar el rol "${rol.value}" a todos los expedientes con estado "${valor}"?`;
            break;
        case 'tipo_tramite':
            mensaje = `¿Está seguro de asignar el rol "${rol.value}" a todos los expedientes que contengan "${valor}" en el tipo de trámite?`;
            break;
        case 'juzgado_origen':
            mensaje = `¿Está seguro de asignar el rol "${rol.value}" a todos los expedientes que contengan "${valor}" en el juzgado de origen?`;
            break;
        case 'todos':
            mensaje = `ADVERTENCIA CRÍTICA \n\n¿Está COMPLETAMENTE SEGURO de asignar el rol "${rol.value}" a TODOS los expedientes del sistema?\n\nEsta acción afectará TODOS los expedientes sin excepción.\n\nEscriba "CONFIRMAR" para continuar:`;
            const confirmacion = prompt(mensaje);
            return confirmacion === 'CONFIRMAR';
        default:
            alert('Debe seleccionar un criterio válido');
            return false;
    }
    
    return confirm(mensaje);
}

function limpiarFormularioMasivo() {
    const criterio = document.getElementById('criterio_masivo');
    const rol = document.getElementById('rol_masivo');
    const valorTexto = document.getElementById('valor_criterio');
    const valorEstado = document.getElementById('valor_estado');
    
    if (criterio) criterio.value = '';
    if (rol) rol.value = '';
    if (valorTexto) valorTexto.value = '';
    if (valorEstado) valorEstado.value = '';
    
    mostrarCampoValor();
}

/* =======================================
   FUNCIONES DE ASIGNACIÓN
   ======================================= */

function verDetalleExpediente(radicado) {
    // Redirigir a la página de expedientes con el radicado pre-cargado
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/expediente';
    
    const inputTipo = document.createElement('input');
    inputTipo.type = 'hidden';
    inputTipo.name = 'tipo_busqueda';
    inputTipo.value = 'radicado';
    
    const inputRadicado = document.createElement('input');
    inputRadicado.type = 'hidden';
    inputRadicado.name = 'radicado';
    inputRadicado.value = radicado;
    
    form.appendChild(inputTipo);
    form.appendChild(inputRadicado);
    document.body.appendChild(form);
    form.submit();
}

function actualizarExpediente(expedienteId) {
    // Funcionalidad para escribientes
    window.location.href = `/actualizarexpediente?id=${expedienteId}`;
}

function revisarExpediente(expedienteId) {
    // Funcionalidad para sustanciadores
    alert(`Funcionalidad de revisión para expediente ${expedienteId} - En desarrollo`);
}

// Filtro rápido por estado
function filtrarPorEstado(estado) {
    const filas = document.querySelectorAll('.expediente-row');
    filas.forEach(fila => {
        const estadoExpediente = fila.dataset.estado;
        if (estado === 'todos' || estadoExpediente === estado) {
            fila.style.display = '';
        } else {
            fila.style.display = 'none';
        }
    });
}

/* =======================================
   FUNCIONES DE GESTIÓN DE USUARIOS
   ======================================= */

// Función para abrir modal de cambiar contraseña
function abrirModalPassword(usuarioId, nombreUsuario) {
    const passwordUsuarioId = document.getElementById('password_usuario_id');
    const passwordUsuarioNombre = document.getElementById('password_usuario_nombre');
    const nuevaPassword = document.getElementById('nueva_password');
    
    if (passwordUsuarioId && passwordUsuarioNombre && nuevaPassword) {
        passwordUsuarioId.value = usuarioId;
        passwordUsuarioNombre.textContent = nombreUsuario;
        nuevaPassword.value = '';
        
        const modal = new bootstrap.Modal(document.getElementById('modalCambiarPassword'));
        modal.show();
    }
}

// Función para abrir modal de cambiar rol
function abrirModalRol(usuarioId, nombreUsuario, rolActualId) {
    const rolUsuarioId = document.getElementById('rol_usuario_id');
    const rolUsuarioNombre = document.getElementById('rol_usuario_nombre');
    const selectRol = document.getElementById('nuevo_rol_id');
    
    if (rolUsuarioId && rolUsuarioNombre && selectRol) {
        rolUsuarioId.value = usuarioId;
        rolUsuarioNombre.textContent = nombreUsuario;
        selectRol.value = rolActualId || '';
        
        const modal = new bootstrap.Modal(document.getElementById('modalCambiarRol'));
        modal.show();
    }
}

// Función para validar formulario de nuevo usuario
function validarFormularioUsuario() {
    const nombreUsuario = document.getElementById('nombre_usuario');
    const correo = document.getElementById('correo');
    const password = document.getElementById('password');
    
    if (!nombreUsuario || !correo || !password) return true;
    
    // Validar nombre de usuario
    if (nombreUsuario.value.length < 3) {
        alert('El nombre de usuario debe tener al menos 3 caracteres');
        nombreUsuario.focus();
        return false;
    }
    
    // Validar correo
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(correo.value)) {
        alert('Por favor ingrese un correo electrónico válido');
        correo.focus();
        return false;
    }
    
    // Validar contraseña
    if (password.value.length < 6) {
        alert('La contraseña debe tener al menos 6 caracteres');
        password.focus();
        return false;
    }
    
    return true;
}

/* =======================================
   EVENT LISTENERS GLOBALES
   ======================================= */

// Mantener la pestaña activa después del submit
document.addEventListener('DOMContentLoaded', function () {
    // Inicializar funciones específicas según la página
    inicializarLogin(); // Para la página de login
    
    // Verificar si hay un indicador de que se debe activar la pestaña de filtros
    const activarFiltros = document.querySelector('[data-activar-filtros="true"]');
    if (activarFiltros) {
        activarTabFiltros();
    }
    
    // Añadir evento al selector de responsable
    const selector = document.getElementById('rol_responsable');
    if (selector) {
        selector.addEventListener('change', cambiarResponsable);
    }
    
    // Event listeners para modales de confirmación (roles)
    const btnConfirmar = document.getElementById('btn-confirmar');
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', function() {
            if (accionPendiente) {
                accionPendiente();
                accionPendiente = null;
            }
            // Cerrar modal usando Bootstrap 5 API
            const modal = document.getElementById('modalConfirmacion');
            if (modal) {
                const bootstrapModal = bootstrap.Modal.getInstance(modal);
                if (bootstrapModal) {
                    bootstrapModal.hide();
                }
            }
        });
    }
    
    // Event listener para botón cancelar del modal
    const btnCancelar = document.getElementById('btn-cancelar');
    if (btnCancelar) {
        btnCancelar.addEventListener('click', function() {
            accionPendiente = null;
            // Cerrar modal usando Bootstrap 5 API
            const modal = document.getElementById('modalConfirmacion');
            if (modal) {
                const bootstrapModal = bootstrap.Modal.getInstance(modal);
                if (bootstrapModal) {
                    bootstrapModal.hide();
                }
            }
        });
    }
    
    // Event listener para botón X de cerrar modal
    const modalConfirmacion = document.getElementById('modalConfirmacion');
    if (modalConfirmacion) {
        modalConfirmacion.addEventListener('hidden.bs.modal', function() {
            accionPendiente = null;
        });
    }
    
    // Agregar indicadores de carga a los enlaces de paginación
    const enlacesPaginacion = document.querySelectorAll('.pagination .page-link');
    enlacesPaginacion.forEach(enlace => {
        enlace.addEventListener('click', function(e) {
            if (!this.closest('.page-item').classList.contains('disabled') && 
                !this.closest('.page-item').classList.contains('active')) {
                mostrarCargaPaginacion(this);
            }
        });
    });
    
    // Auto-cerrar alertas después de 5 segundos
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            if (alert.classList.contains('alert-dismissible')) {
                alert.style.transition = 'opacity 0.5s';
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.parentNode.removeChild(alert);
                    }
                }, 500);
            }
        });
    }, 5000);
});

// Función para buscar el expediente original en la vista de consulta
function buscarExpedienteOriginal(radicado) {
    // Crear un formulario temporal para enviar la búsqueda
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '{{ url_for("idvistaexpediente.vista_expediente") }}';
    
    // Campo para el tipo de búsqueda
    const tipoBusqueda = document.createElement('input');
    tipoBusqueda.type = 'hidden';
    tipoBusqueda.name = 'tipo_busqueda';
    tipoBusqueda.value = 'radicado';
    form.appendChild(tipoBusqueda);
    
    // Campo para el radicado
    const radicadoInput = document.createElement('input');
    radicadoInput.type = 'hidden';
    radicadoInput.name = 'radicado';
    radicadoInput.value = radicado;
    form.appendChild(radicadoInput);
    
    // Agregar al DOM y enviar
    document.body.appendChild(form);
    form.submit();
}

// Auto-focus en el campo de búsqueda si no hay expediente cargado
document.addEventListener('DOMContentLoaded', function() {
    const radicadoBuscar = document.getElementById('radicado_buscar');
    if (radicadoBuscar && !document.querySelector('.card .card-header.bg-success')) {
        // Solo hacer focus si no hay expediente cargado (no hay card con header verde)
        radicadoBuscar.focus();
    }
    
    // Event listener para el botón "Ver Detalles"
    const btnVerDetalles = document.querySelector('.btn-ver-detalles');
    if (btnVerDetalles) {
        btnVerDetalles.addEventListener('click', function() {
            const radicado = this.getAttribute('data-radicado');
            if (radicado) {
                buscarExpedienteOriginal(radicado);
            }
        });
    }
});




/* =======================================
   FUNCIONES DE BÚSQUEDA - ROLES
   ======================================= */

// Función para filtrar usuarios en la vista de roles
function filtrarUsuariosRoles() {
    const filtro = document.getElementById('buscadorRoles').value.toLowerCase();
    const tabla = document.getElementById('tablaRoles');
    const filas = tabla.getElementsByTagName('tr');
    let usuariosVisibles = 0;
    
    // Empezar desde 1 para saltar el header
    for (let i = 1; i < filas.length; i++) {
        const fila = filas[i];
        const celdas = fila.getElementsByTagName('td');
        let mostrarFila = false;
        
        // Buscar en las primeras 4 celdas (nombre, correo, rol, estado)
        for (let j = 0; j < Math.min(4, celdas.length); j++) {
            const textoCelda = celdas[j].textContent || celdas[j].innerText;
            if (textoCelda.toLowerCase().indexOf(filtro) > -1) {
                mostrarFila = true;
                break;
            }
        }
        
        if (mostrarFila) {
            fila.style.display = '';
            usuariosVisibles++;
        } else {
            fila.style.display = 'none';
        }
    }
    
    // Mostrar mensaje si no hay resultados
    mostrarMensajeSinResultadosRoles(usuariosVisibles === 0 && filtro !== '');
}

// Función para limpiar búsqueda en roles
function limpiarBusquedaRoles() {
    document.getElementById('buscadorRoles').value = '';
    filtrarUsuariosRoles();
}

// Función para mostrar mensaje cuando no hay resultados en roles
function mostrarMensajeSinResultadosRoles(mostrar) {
    let mensajeExistente = document.getElementById('mensajeSinResultadosRoles');
    
    if (mostrar && !mensajeExistente) {
        const tabla = document.getElementById('tablaRoles');
        const tbody = tabla.getElementsByTagName('tbody')[0];
        
        const fila = document.createElement('tr');
        fila.id = 'mensajeSinResultadosRoles';
        fila.innerHTML = `
            <td colspan="5" class="text-center py-4 text-muted">
                <i class="fas fa-search fa-2x mb-2"></i>
                <p class="mb-0">No se encontraron usuarios que coincidan con la búsqueda</p>
            </td>
        `;
        tbody.appendChild(fila);
    } else if (!mostrar && mensajeExistente) {
        mensajeExistente.remove();
    }
}

/* =======================================
   FUNCIONES DE ROLES - ACCIONES
   ======================================= */

// Función para asignar rol a usuario
function asignarRol(usuarioId, rol) {
    if (confirm(`¿Está seguro de asignar el rol ${rol} a este usuario?`)) {
        const form = document.getElementById('form-asignar-rol');
        document.getElementById('usuario_id_asignar').value = usuarioId;
        document.getElementById('rol_asignar').value = rol;
        form.submit();
    }
}

// Función para remover rol de usuario
function removerRol(usuarioId) {
    if (confirm('¿Está seguro de remover el rol de este usuario?')) {
        const form = document.getElementById('form-remover-rol');
        document.getElementById('usuario_id_remover').value = usuarioId;
        form.submit();
    }
}

// Función para asignar roles aleatorios
function asignarRolesAleatorios() {
    if (confirm('¿Está seguro de asignar roles aleatorios a todos los usuarios?\n\nEsta acción sobrescribirá los roles actuales.')) {
        const form = document.getElementById('form-roles-aleatorios');
        form.submit();
    }
}

// Función para remover todos los roles
function removerTodosRoles() {
    if (confirm('¿Está COMPLETAMENTE SEGURO de remover todos los roles asignados?\n\nEsta acción NO se puede deshacer.')) {
        const form = document.getElementById('form-remover-todos-roles');
        form.submit();
    }
}

// ========================================
// FUNCIONES DE BÚSQUEDA DE USUARIOS
// ========================================

// Función para filtrar usuarios en la vista de usuarios
function filtrarUsuarios() {
    const filtro = document.getElementById('buscadorUsuarios').value.toLowerCase();
    const tabla = document.getElementById('tablaUsuarios');
    const filas = tabla.getElementsByTagName('tr');
    let usuariosVisibles = 0;
    
    // Empezar desde 1 para saltar el header
    for (let i = 1; i < filas.length; i++) {
        const fila = filas[i];
        const celdas = fila.getElementsByTagName('td');
        let mostrarFila = false;
        
        // Buscar en las primeras 6 celdas (ID, Usuario, Correo, Rol, Tipo, Fecha)
        for (let j = 0; j < Math.min(6, celdas.length); j++) {
            const textoCelda = celdas[j].textContent || celdas[j].innerText;
            if (textoCelda.toLowerCase().indexOf(filtro) > -1) {
                mostrarFila = true;
                break;
            }
        }
        
        if (mostrarFila) {
            fila.style.display = '';
            usuariosVisibles++;
        } else {
            fila.style.display = 'none';
        }
    }
    
    // Mostrar mensaje si no hay resultados (simplificado como en roles)
    // No necesitamos mensaje complejo, solo ocultar/mostrar filas
}

// Función para limpiar búsqueda de usuarios
function limpiarBusquedaUsuarios() {
    document.getElementById('buscadorUsuarios').value = '';
    filtrarUsuarios();
}

// Event listeners para botones de usuarios
document.addEventListener('DOMContentLoaded', function() {
    // Botones de cambiar contraseña
    const botonesPassword = document.querySelectorAll('.btn-cambiar-password');
    botonesPassword.forEach(boton => {
        boton.addEventListener('click', function() {
            const usuarioId = this.getAttribute('data-usuario-id');
            const usuarioNombre = this.getAttribute('data-usuario-nombre');
            abrirModalPassword(usuarioId, usuarioNombre);
        });
    });
    
    // Botones de cambiar rol
    const botonesRol = document.querySelectorAll('.btn-cambiar-rol');
    botonesRol.forEach(boton => {
        boton.addEventListener('click', function() {
            const usuarioId = this.getAttribute('data-usuario-id');
            const usuarioNombre = this.getAttribute('data-usuario-nombre');
            const rolActual = this.getAttribute('data-rol-actual');
            abrirModalRol(usuarioId, usuarioNombre, rolActual);
        });
    });
});