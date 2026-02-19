/**
 * JavaScript para el Dashboard del Home
 * Maneja gráficos, auto-refresh y funcionalidades interactivas
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar gráfico de estados si hay datos
    initEstadosChart();
    
    // Configurar auto-refresh
    setupAutoRefresh();
    
    // Agregar efectos de hover a las tarjetas
    setupCardEffects();
    
    // Formatear números grandes
    formatNumbers();
});

/**
 * Inicializa el gráfico de dona para estados
 */
function initEstadosChart() {
    const ctx = document.getElementById('estadosChart');
    if (!ctx) return;
    
    // Obtener datos del template (se pasan desde Python)
    const estadosData = window.estadosChartData;
    if (!estadosData || estadosData.labels.length === 0) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: estadosData.labels,
            datasets: [{
                data: estadosData.data,
                backgroundColor: [
                    '#4e73df', /* Pendiente */
                    '#1cc88a', /* Activo Pendiente */
                    '#36b9cc', /* Inactivo Resuelto */
                    '#f6c23e'  /* Activo Resuelto */
                ],
                hoverBackgroundColor: [
                    '#2e59d9',
                    '#17a673',
                    '#2c9faf',
                    '#f4b619'
                ],
                hoverBorderColor: "rgba(234, 236, 244, 1)",
                borderWidth: 2
            }],
        },
        options: {
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#333',
                    bodyColor: '#333',
                    borderColor: '#ddd',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '70%',
            responsive: true,
            animation: {
                animateRotate: true,
                duration: 1000
            }
        },
    });
}

/**
 * Configura el auto-refresh de la página
 */
function setupAutoRefresh() {
    // Auto-refresh cada 5 minutos (300000 ms)
    setTimeout(function() {
        // Mostrar notificación antes de refrescar
        showRefreshNotification();
        
        // Refrescar después de 3 segundos
        setTimeout(function() {
            location.reload();
        }, 3000);
    }, 300000);
}

/**
 * Muestra una notificación de refresh
 */
function showRefreshNotification() {
    const notification = document.createElement('div');
    notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        <i class="fas fa-sync-alt fa-spin"></i>
        Actualizando datos del dashboard...
        <button type="button" class="close" data-dismiss="alert">
            <span>&times;</span>
        </button>
    `;
    
    document.body.appendChild(notification);
}

/**
 * Agrega efectos de hover a las tarjetas
 */
function setupCardEffects() {
    const cards = document.querySelectorAll('.card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 0.75rem 1.5rem rgba(0, 0, 0, 0.2)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 0.5rem 1rem rgba(0, 0, 0, 0.15)';
        });
    });
}

/**
 * Formatea números grandes con separadores de miles
 */
function formatNumbers() {
    const numberElements = document.querySelectorAll('.format-number');
    
    numberElements.forEach(element => {
        const number = parseInt(element.textContent);
        if (!isNaN(number)) {
            element.textContent = number.toLocaleString();
        }
    });
}

/**
 * Actualiza una métrica específica
 */
function updateMetric(metricId, newValue) {
    const element = document.getElementById(metricId);
    if (element) {
        // Animación de cambio
        element.style.transform = 'scale(1.1)';
        element.style.color = '#1cc88a';
        
        setTimeout(() => {
            element.textContent = newValue.toLocaleString();
            element.style.transform = 'scale(1)';
            element.style.color = '';
        }, 300);
    }
}

/**
 * Maneja errores de carga de gráficos
 */
window.addEventListener('error', function(e) {
    if (e.target.tagName === 'SCRIPT' && e.target.src.includes('chart')) {
        console.warn('Error cargando Chart.js, ocultando gráficos');
        const chartContainers = document.querySelectorAll('.chart-pie');
        chartContainers.forEach(container => {
            container.innerHTML = '<p class="text-center text-muted">Gráfico no disponible</p>';
        });
    }
});

/**
 * Funciones de utilidad para el dashboard
 */
const DashboardUtils = {
    /**
     * Refresca solo las métricas sin recargar la página completa
     */
    refreshMetrics: function() {
        // Implementar llamada AJAX para actualizar métricas
        console.log('Refrescando métricas...');
    },
    
    /**
     * Exporta datos del dashboard
     */
    exportData: function() {
        console.log('Exportando datos del dashboard...');
    },
    
    /**
     * Cambia el tema del dashboard
     */
    toggleTheme: function() {
        document.body.classList.toggle('dark-theme');
    }
};