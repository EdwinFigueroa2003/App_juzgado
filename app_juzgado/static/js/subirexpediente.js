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
});