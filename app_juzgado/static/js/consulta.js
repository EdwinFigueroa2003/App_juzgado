/**
 * JavaScript para la página de Consulta Pública
 * Sistema de Gestión Judicial
 */

// Variables globales
let expedientesCache = [];
let turnosCache = [];
let paginacionActual = {};
let nombreBusquedaActual = '';

/**
 * Configuración de la aplicación
 */
const CONFIG = {
    API_BASE_URL: '/api',
    DEBOUNCE_DELAY: 300,
    MIN_SEARCH_LENGTH: 3
};

/**
 * Obtiene el token CSRF del meta tag
 * @returns {string|null} Token CSRF
 */
function getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : null;
}

/**
 * Configura headers por defecto para las peticiones fetch
 * @returns {Object} Headers configurados
 */
function getDefaultHeaders() {
    const headers = {
        'Content-Type': 'application/json',
    };
    
    const csrfToken = getCSRFToken();
    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }
    
    return headers;
}

/**
 * Inicializa la aplicación cuando el DOM está listo
 */
function inicializarApp() {
    configurarEventListeners();
    configurarValidaciones();
    console.log('Aplicación de consulta pública inicializada');
}

/**
 * Configura todos los event listeners
 */
function configurarEventListeners() {
    // Formulario de búsqueda por radicado
    const formRadicado = document.getElementById('form-radicado');
    if (formRadicado) {
        formRadicado.addEventListener('submit', manejarBusquedaRadicado);
    }

    // Formulario de búsqueda por nombres
    const formNombres = document.getElementById('form-nombres');
    if (formNombres) {
        formNombres.addEventListener('submit', manejarBusquedaNombres);
    }

    // Botón de cargar turnos
    const btnTurnos = document.getElementById('btn-cargar-turnos');
    if (btnTurnos) {
        btnTurnos.addEventListener('click', cargarTurnos);
    }

    // Limpiar resultados al cambiar de pestaña
    const tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', limpiarResultados);
    });
}

/**
 * Configura las validaciones de formularios
 */
function configurarValidaciones() {
    const inputRadicado = document.getElementById('radicado');
    const inputNombre = document.getElementById('nombre');

    if (inputRadicado) {
        inputRadicado.addEventListener('input', validarRadicado);
    }

    if (inputNombre) {
        inputNombre.addEventListener('input', debounce(validarNombre, CONFIG.DEBOUNCE_DELAY));
    }
}

/**
 * Maneja la búsqueda por radicado
 * @param {Event} event - Evento del formulario
 */
async function manejarBusquedaRadicado(event) {
    event.preventDefault();
    
    const radicado = document.getElementById('radicado').value.trim();
    
    if (!radicado) {
        mostrarError('Por favor ingrese un número de radicado');
        return;
    }

    mostrarCargando();
    
    try {
        const expedientes = await buscarPorRadicado(radicado);
        mostrarResultadosExpedientes(expedientes);
    } catch (error) {
        console.error('Error en búsqueda por radicado:', error);
        mostrarError('Error al buscar el expediente. Para mayor información de esta consulta, llevela a la ventanilla de juzgado');
    }
}

/**
 * Maneja la búsqueda por nombres
 * @param {Event} event - Evento del formulario
 */
async function manejarBusquedaNombres(event) {
    event.preventDefault();
    
    const nombre = document.getElementById('nombre').value.trim();
    
    if (!nombre || nombre.length < CONFIG.MIN_SEARCH_LENGTH) {
        mostrarError(`Por favor ingrese al menos ${CONFIG.MIN_SEARCH_LENGTH} caracteres`);
        return;
    }

    nombreBusquedaActual = nombre;
    mostrarCargando();
    
    try {
        const resultado = await buscarPorNombre(nombre, 1);
        if (resultado.expedientes) {
            mostrarResultadosExpedientes(resultado.expedientes, resultado.paginacion);
        }
    } catch (error) {
        console.error('Error en búsqueda por nombre:', error);
        mostrarError('Error al buscar expedientes. Intente nuevamente.');
    }
}

/**
 * Busca expedientes por radicado
 * @param {string} radicado - Número de radicado
 * @returns {Promise<Array>} Lista de expedientes
 */
async function buscarPorRadicado(radicado) {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/buscar_expediente`, {
            method: 'POST',
            headers: getDefaultHeaders(),
            body: JSON.stringify({ radicado: radicado })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error en la búsqueda');
        }

        return data.expedientes || [];
    } catch (error) {
        console.error('Error en buscarPorRadicado:', error);
        throw error;
    }
}

/**
 * Busca expedientes por nombre
 * @param {string} nombre - Nombre a buscar
 * @param {number} pagina - Número de página
 * @returns {Promise<Object>} Resultado con expedientes y paginación
 */
async function buscarPorNombre(nombre, pagina = 1) {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/buscar_por_nombres`, {
            method: 'POST',
            headers: getDefaultHeaders(),
            body: JSON.stringify({ nombre: nombre, pagina: pagina })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error en la búsqueda');
        }

        return {
            expedientes: data.expedientes || [],
            paginacion: data.paginacion || {}
        };
    } catch (error) {
        console.error('Error en buscarPorNombre:', error);
        throw error;
    }
}

/**
 * Carga los turnos del día
 */
async function cargarTurnos() {
    mostrarCargando();
    
    try {
        const turnos = await obtenerTurnosDelDia();
        mostrarResultadosTurnos(turnos);
    } catch (error) {
        console.error('Error al cargar turnos:', error);
        mostrarError('Error al cargar los turnos del día');
    }
}

/**
 * Obtiene los turnos del día actual
 * @returns {Promise<Array>} Lista de turnos
 */
async function obtenerTurnosDelDia() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/turnos_del_dia`, {
            headers: getDefaultHeaders()
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al obtener turnos');
        }

        return data.turnos || [];
    } catch (error) {
        console.error('Error en obtenerTurnosDelDia:', error);
        throw error;
    }
}

/**
 * Muestra los resultados de expedientes
 * @param {Array} expedientes - Lista de expedientes
 * @param {Object} paginacion - Información de paginación
 */
function mostrarResultadosExpedientes(expedientes, paginacion = null) {
    const container = document.getElementById('resultados');
    const resultadosContainer = document.getElementById('resultados-container');
    const paginacionContainer = document.getElementById('paginacion-container');
    
    if (!container || !resultadosContainer) return;
    
    ocultarCargando();
    resultadosContainer.style.display = 'block';
    
    if (expedientes.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <i class="fas fa-search"></i>
                <h4>No se encontraron expedientes</h4>
                <p>No hay expedientes que coincidan con su búsqueda.</p>
            </div>
        `;
        if (paginacionContainer) paginacionContainer.style.display = 'none';
        return;
    }
    
    const expedientesHTML = expedientes.map(exp => `
        <div class="expediente-card">
            <div class="expediente-header">
                <span class="radicado-badge">${exp.numero_radicado}</span>
                <span class="estado-badge estado-${exp.estado.toLowerCase()}">${obtenerTextoEstado(exp.estado)}</span>
            </div>
            <div class="expediente-info">
                <h5><i class="fas fa-gavel me-2"></i>Información del Expediente</h5>
                <p><strong>Demandante:</strong> ${exp.demandante}</p>
                <p><strong>Demandado:</strong> ${exp.demandado}</p>
                <p><strong>Fecha de Ingreso:</strong> ${exp.fecha_ingreso}</p>
                ${exp.turno ? `<p><strong>Turno:</strong> ${exp.turno}</p>` : ''}
                ${exp.actuacion && exp.actuacion !== 'Sin actuaciones' ? `<p><strong>Actuación:</strong> ${exp.actuacion}</p>` : ''}
            </div>
        </div>
    `).join('');
    
    container.innerHTML = expedientesHTML;
    
    // Mostrar paginación si hay datos
    if (paginacion && paginacion.total_paginas > 1) {
        paginacionActual = paginacion;
        mostrarPaginacion(paginacion);
        if (paginacionContainer) paginacionContainer.style.display = 'block';
    } else {
        if (paginacionContainer) paginacionContainer.style.display = 'none';
    }
}

/**
 * Muestra los resultados de turnos
 * @param {Array} turnos - Lista de turnos
 */
function mostrarResultadosTurnos(turnos) {
    const container = document.getElementById('resultados');
    const resultadosContainer = document.getElementById('resultados-container');
    
    if (!container || !resultadosContainer) return;
    
    ocultarCargando();
    resultadosContainer.style.display = 'block';
    
    if (turnos.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <i class="fas fa-calendar-times"></i>
                <h4>No hay turnos programados</h4>
                <p>No se encontraron turnos para el día de hoy.</p>
            </div>
        `;
        return;
    }
    
    const turnosHTML = turnos.map(turno => `
        <div class="expediente-card">
            <div class="expediente-header">
                <span class="radicado-badge">${turno.numero_radicado}</span>
                <span class="estado-badge estado-${turno.estado.toLowerCase()}">${obtenerTextoEstado(turno.estado)}</span>
            </div>
            <div class="expediente-info">
                <h5><i class="fas fa-calendar-check me-2"></i>Turno: ${turno.turno}</h5>
                <p><strong>Demandante:</strong> ${turno.demandante}</p>
                <p><strong>Demandado:</strong> ${turno.demandado}</p>
                <p><strong>Fecha:</strong> ${turno.fecha_actuacion}</p>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = turnosHTML;
}

/**
 * Muestra el indicador de carga
 */
function mostrarCargando() {
    const loading = document.getElementById('loading');
    const resultados = document.getElementById('resultados');
    const resultadosContainer = document.getElementById('resultados-container');
    
    if (resultadosContainer) resultadosContainer.style.display = 'block';
    if (loading) loading.style.display = 'block';
    if (resultados) resultados.innerHTML = '';
}

/**
 * Oculta el indicador de carga
 */
function ocultarCargando() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'none';
}

/**
 * Limpia los resultados de búsqueda
 */
function limpiarResultados() {
    const resultadosContainer = document.getElementById('resultados-container');
    const resultados = document.getElementById('resultados');
    
    if (resultadosContainer) resultadosContainer.style.display = 'none';
    if (resultados) resultados.innerHTML = '';
}

/**
 * Muestra un mensaje de error
 * @param {string} mensaje - Mensaje de error
 */
function mostrarError(mensaje) {
    ocultarCargando();
    
    const container = document.getElementById('resultados');
    const resultadosContainer = document.getElementById('resultados-container');
    
    if (resultadosContainer) resultadosContainer.style.display = 'block';
    
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${mensaje}
            </div>
        `;
    }
}

/**
 * Valida el campo de radicado
 * @param {Event} event - Evento del input
 */
function validarRadicado(event) {
    const input = event.target;
    const valor = input.value.trim();
    
    // Permitir números, guiones y espacios
    input.value = valor.replace(/[^0-9\-\s]/g, '');
}

/**
 * Valida el campo de nombre
 * @param {Event} event - Evento del input
 */
function validarNombre(event) {
    const input = event.target;
    const valor = input.value.trim();
    
    if (valor.length > 0 && valor.length < CONFIG.MIN_SEARCH_LENGTH) {
        input.setCustomValidity(`Mínimo ${CONFIG.MIN_SEARCH_LENGTH} caracteres`);
    } else {
        input.setCustomValidity('');
    }
}

/**
 * Obtiene el texto del estado del expediente
 * @param {string} estado - Estado del expediente
 * @returns {string} Texto del estado
 */
function obtenerTextoEstado(estado) {
    const estados = {
        'activo': 'Activo',
        'pendiente': 'Pendiente',
        'terminado': 'Terminado',
        'en_tramite': 'En Trámite',
        'archivado': 'Archivado',
        'suspendido': 'Suspendido'
    };
    
    return estados[estado.toLowerCase()] || estado;
}

/**
 * Muestra los controles de paginación
 * @param {Object} paginacion - Información de paginación
 */
function mostrarPaginacion(paginacion) {
    // Actualizar información
    document.getElementById('inicio-item').textContent = paginacion.inicio_item;
    document.getElementById('fin-item').textContent = paginacion.fin_item;
    document.getElementById('total-items').textContent = paginacion.total_items;
    document.getElementById('pagina-actual').textContent = paginacion.pagina_actual;
    document.getElementById('total-paginas').textContent = paginacion.total_paginas;
    
    // Botón anterior
    const btnAnterior = document.getElementById('btn-anterior');
    if (paginacion.tiene_anterior) {
        btnAnterior.classList.remove('disabled');
        btnAnterior.querySelector('a').onclick = (e) => {
            e.preventDefault();
            irAPagina(paginacion.pagina_anterior);
        };
    } else {
        btnAnterior.classList.add('disabled');
        btnAnterior.querySelector('a').onclick = (e) => e.preventDefault();
    }
    
    // Botón siguiente - obtener referencia ANTES de modificar
    const btnSiguiente = document.getElementById('btn-siguiente');
    
    // Limpiar números de página anteriores (si existen)
    const paginationList = document.getElementById('pagination-list');
    const paginasAnteriores = paginationList.querySelectorAll('li.page-item:not(#btn-anterior):not(#btn-siguiente)');
    paginasAnteriores.forEach(li => li.remove());
    
    // Generar HTML para números de página
    let paginasHTML = '';
    for (let num of paginacion.paginas_mostrar) {
        if (num === paginacion.pagina_actual) {
            paginasHTML += `
                <li class="page-item active">
                    <span class="page-link">${num}</span>
                </li>
            `;
        } else {
            paginasHTML += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="irAPagina(${num}); return false;">${num}</a>
                </li>
            `;
        }
    }
    
    // Insertar números de página ANTES del botón siguiente
    btnSiguiente.insertAdjacentHTML('beforebegin', paginasHTML);
    
    // Configurar botón siguiente
    if (paginacion.tiene_siguiente) {
        btnSiguiente.classList.remove('disabled');
        btnSiguiente.querySelector('a').onclick = (e) => {
            e.preventDefault();
            irAPagina(paginacion.pagina_siguiente);
        };
    } else {
        btnSiguiente.classList.add('disabled');
        btnSiguiente.querySelector('a').onclick = (e) => e.preventDefault();
    }
}

/**
 * Navega a una página específica
 * @param {number} pagina - Número de página
 */
async function irAPagina(pagina) {
    mostrarCargando();
    try {
        const resultado = await buscarPorNombre(nombreBusquedaActual, pagina);
        if (resultado.expedientes !== undefined) {
            mostrarResultadosExpedientes(resultado.expedientes, resultado.paginacion);
            // Scroll al inicio de resultados
            document.getElementById('resultados-container').scrollIntoView({ behavior: 'smooth' });
        }
    } catch (error) {
        console.error('Error al navegar a página:', error);
        mostrarError('Error al cargar los expedientes.');
    }
}

/**
 * Función debounce para optimizar las búsquedas
 * @param {Function} func - Función a ejecutar
 * @param {number} delay - Retraso en milisegundos
 * @returns {Function} Función con debounce
 */
function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * Maneja errores globales de JavaScript
 */
window.addEventListener('error', function(event) {
    console.error('Error en consulta pública:', event.error);
    mostrarError('Ha ocurrido un error inesperado');
});

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', inicializarApp);