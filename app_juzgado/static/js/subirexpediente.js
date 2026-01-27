// JavaScript simple para las pestañas de subir expediente

function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    
    // Ocultar todo el contenido de las pestañas
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    
    // Remover la clase "active" de todos los botones de pestañas
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    
    // Mostrar la pestaña actual y agregar clase "active" al botón que abrió la pestaña
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

// Función para validar radicado completo
function validarRadicadoCompleto(input) {
    const valor = input.value.trim();
    const esValido = /^[0-9]{23}$/.test(valor);
    
    // Remover clases previas
    input.classList.remove('is-valid', 'is-invalid');
    
    if (valor === '') {
        // Campo vacío - no mostrar validación
        return;
    }
    
    if (esValido) {
        input.classList.add('is-valid');
        input.setCustomValidity('');
    } else {
        input.classList.add('is-invalid');
        if (valor.length !== 23) {
            input.setCustomValidity(`El radicado debe tener exactamente 23 dígitos. Actualmente tiene ${valor.length} caracteres.`);
        } else if (!/^[0-9]+$/.test(valor)) {
            input.setCustomValidity('El radicado debe contener solo números.');
        }
    }
}

// Función para formatear entrada solo números
function soloNumeros(input) {
    // Remover cualquier carácter que no sea número
    input.value = input.value.replace(/[^0-9]/g, '');
    
    // Limitar a 23 caracteres
    if (input.value.length > 23) {
        input.value = input.value.substring(0, 23);
    }
    
    // Validar después de formatear
    validarRadicadoCompleto(input);
}

// Establecer fecha actual cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    // Activar la primera pestaña por defecto
    document.getElementsByClassName("tablinks")[0].click();
    
    // Establecer fecha actual en el campo de fecha de ingreso
    const fechaIngresoInput = document.getElementById('fecha_ingreso');
    if (fechaIngresoInput) {
        const today = new Date();
        const formattedDate = today.getFullYear() + '-' + 
                             String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                             String(today.getDate()).padStart(2, '0');
        fechaIngresoInput.value = formattedDate;
    }
    
    // Configurar validación de radicado completo
    const radicadoCompletoInput = document.getElementById('radicado_completo');
    if (radicadoCompletoInput) {
        // Validar en tiempo real mientras escribe
        radicadoCompletoInput.addEventListener('input', function() {
            soloNumeros(this);
        });
        
        // Validar cuando pierde el foco
        radicadoCompletoInput.addEventListener('blur', function() {
            validarRadicadoCompleto(this);
        });
        
        // Prevenir pegar texto no numérico
        radicadoCompletoInput.addEventListener('paste', function(e) {
            setTimeout(() => {
                soloNumeros(this);
            }, 10);
        });
    }
    
    // Validación del formulario antes de enviar
    const formularioManual = document.querySelector('form[action*="subirexpediente"]');
    if (formularioManual && !formularioManual.enctype) { // Solo para formulario manual, no para Excel
        formularioManual.addEventListener('submit', function(e) {
            const radicadoInput = document.getElementById('radicado_completo');
            if (radicadoInput && radicadoInput.value.trim()) {
                if (!/^[0-9]{23}$/.test(radicadoInput.value.trim())) {
                    e.preventDefault();
                    alert('El radicado completo debe tener exactamente 23 dígitos numéricos.');
                    radicadoInput.focus();
                    return false;
                }
            }
        });
    }
});