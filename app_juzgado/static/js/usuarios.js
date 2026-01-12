/**
 * JavaScript para la gestión de usuarios
 * Maneja modales, validaciones y eventos de la vista de usuarios
 */

// Función para alternar visibilidad de contraseña
function togglePasswordVisibility(fieldId) {
    const field = document.getElementById(fieldId);
    const button = field.parentNode.querySelector('.password-toggle i');
    
    if (field.type === 'password') {
        field.type = 'text';
        button.className = 'fas fa-eye-slash';
    } else {
        field.type = 'password';
        button.className = 'fas fa-eye';
    }
}

// Función para filtrar usuarios en tiempo real
function filtrarUsuarios() {
    const input = document.getElementById('buscadorUsuarios');
    const filter = input.value.toLowerCase();
    const table = document.querySelector('.table tbody');
    const rows = table.getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const cells = row.getElementsByTagName('td');
        let found = false;

        // Buscar en todas las celdas de la fila
        for (let j = 0; j < cells.length - 1; j++) { // -1 para excluir la columna de acciones
            const cellText = cells[j].textContent || cells[j].innerText;
            if (cellText.toLowerCase().indexOf(filter) > -1) {
                found = true;
                break;
            }
        }

        row.style.display = found ? '' : 'none';
    }
}

// Función para limpiar búsqueda
function limpiarBusquedaUsuarios() {
    document.getElementById('buscadorUsuarios').value = '';
    filtrarUsuarios();
}

// Función para abrir modal de cambiar contraseña
function abrirModalCambiarPassword(usuarioId, usuarioNombre) {
    // Llenar el modal con los datos del usuario
    document.getElementById('password_usuario_id').value = usuarioId;
    document.getElementById('password_usuario_nombre').textContent = usuarioNombre;
    
    // Limpiar el campo de contraseña
    document.getElementById('nueva_password').value = '';
    
    // Limpiar validaciones previas
    const validationDiv = document.getElementById('nueva_password-validation');
    if (validationDiv) {
        validationDiv.innerHTML = '';
    }
    
    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById('modalCambiarPassword'));
    modal.show();
}

// Función para abrir modal de cambiar rol
function abrirModalCambiarRol(usuarioId, usuarioNombre) {
    // Llenar el modal con los datos del usuario
    document.getElementById('rol_usuario_id').value = usuarioId;
    document.getElementById('rol_usuario_nombre').textContent = usuarioNombre;
    
    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById('modalCambiarRol'));
    modal.show();
}

// Función para confirmar eliminación de usuario
function confirmarEliminarUsuario(usuarioId, usuarioNombre) {
    if (confirm(`¿Está seguro de que desea eliminar al usuario "${usuarioNombre}"?\n\nEsta acción no se puede deshacer.`)) {
        // Crear formulario dinámico para enviar la eliminación
        const form = document.createElement('form');
        form.method = 'POST';
        form.style.display = 'none';
        
        // CSRF Token
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        form.appendChild(csrfInput);
        
        // Acción
        const accionInput = document.createElement('input');
        accionInput.type = 'hidden';
        accionInput.name = 'accion';
        accionInput.value = 'eliminar_usuario';
        form.appendChild(accionInput);
        
        // Usuario ID
        const usuarioInput = document.createElement('input');
        usuarioInput.type = 'hidden';
        usuarioInput.name = 'usuario_id';
        usuarioInput.value = usuarioId;
        form.appendChild(usuarioInput);
        
        document.body.appendChild(form);
        form.submit();
    }
}

// Función para alternar privilegios de administrador
function toggleAdmin(usuarioId, usuarioNombre, esAdmin) {
    const accion = esAdmin ? 'quitar privilegios de administrador a' : 'otorgar privilegios de administrador a';
    
    if (confirm(`¿Está seguro de que desea ${accion} "${usuarioNombre}"?`)) {
        // Crear formulario dinámico
        const form = document.createElement('form');
        form.method = 'POST';
        form.style.display = 'none';
        
        // CSRF Token
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        form.appendChild(csrfInput);
        
        // Acción
        const accionInput = document.createElement('input');
        accionInput.type = 'hidden';
        accionInput.name = 'accion';
        accionInput.value = 'toggle_admin';
        form.appendChild(accionInput);
        
        // Usuario ID
        const usuarioInput = document.createElement('input');
        usuarioInput.type = 'hidden';
        usuarioInput.name = 'usuario_id';
        usuarioInput.value = usuarioId;
        form.appendChild(usuarioInput);
        
        document.body.appendChild(form);
        form.submit();
    }
}

// Inicialización cuando el DOM está listo
document.addEventListener('DOMContentLoaded', function() {
    // Event listeners para botones de cambiar contraseña
    document.querySelectorAll('.btn-cambiar-password').forEach(button => {
        button.addEventListener('click', function() {
            const usuarioId = this.getAttribute('data-usuario-id');
            const usuarioNombre = this.getAttribute('data-usuario-nombre');
            abrirModalCambiarPassword(usuarioId, usuarioNombre);
        });
    });
    
    // Event listeners para botones de cambiar rol
    document.querySelectorAll('.btn-cambiar-rol').forEach(button => {
        button.addEventListener('click', function() {
            const usuarioId = this.getAttribute('data-usuario-id');
            const usuarioNombre = this.getAttribute('data-usuario-nombre');
            abrirModalCambiarRol(usuarioId, usuarioNombre);
        });
    });
    
    // Event listeners para botones de eliminar usuario
    document.querySelectorAll('.btn-eliminar-usuario').forEach(button => {
        button.addEventListener('click', function() {
            const usuarioId = this.getAttribute('data-usuario-id');
            const usuarioNombre = this.getAttribute('data-usuario-nombre');
            confirmarEliminarUsuario(usuarioId, usuarioNombre);
        });
    });
    
    // Event listeners para botones de toggle admin
    document.querySelectorAll('.btn-toggle-admin').forEach(button => {
        button.addEventListener('click', function() {
            const usuarioId = this.getAttribute('data-usuario-id');
            const usuarioNombre = this.getAttribute('data-usuario-nombre');
            const esAdmin = this.getAttribute('data-es-admin') === 'true';
            toggleAdmin(usuarioId, usuarioNombre, esAdmin);
        });
    });
    
    // Validación de formulario de agregar usuario
    const formAgregar = document.querySelector('#modalAgregarUsuario form');
    if (formAgregar) {
        formAgregar.addEventListener('submit', async function(e) {
            const passwordField = document.getElementById('password');
            if (passwordField && passwordField.value) {
                const isValid = await window.passwordValidator.validateBeforeSubmit('password');
                if (!isValid) {
                    e.preventDefault();
                    alert('Por favor corrija los errores en la contraseña antes de continuar.');
                    return false;
                }
            }
        });
    }
    
    // Validación de formulario de cambiar contraseña
    const formCambiar = document.querySelector('#modalCambiarPassword form');
    if (formCambiar) {
        formCambiar.addEventListener('submit', async function(e) {
            const passwordField = document.getElementById('nueva_password');
            if (passwordField && passwordField.value) {
                const isValid = await window.passwordValidator.validateBeforeSubmit('nueva_password');
                if (!isValid) {
                    e.preventDefault();
                    alert('Por favor corrija los errores en la contraseña antes de continuar.');
                    return false;
                }
            }
        });
    }
    
    // Inicializar tooltips si Bootstrap está disponible
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});