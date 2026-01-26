// Admin Dashboard JavaScript - Bootstrap 5 Compatible
$(document).ready(function() {
    console.log('🚀 Inicializando Admin Dashboard con Bootstrap 5');
    
    // Activar tooltips (Bootstrap 5 syntax)
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Verificar que jQuery y Bootstrap están cargados
    console.log('jQuery version:', $.fn.jquery);
    console.log('Bootstrap disponible:', typeof bootstrap !== 'undefined');
    
    // Inicializar tabs con Bootstrap 5
    $('#adminTabs a').on('click', function (e) {
        e.preventDefault();
        console.log('🔄 Tab clickeado:', $(this).attr('id'));
        
        // Usar Bootstrap 5 Tab API
        const tabTrigger = new bootstrap.Tab(this);
        tabTrigger.show();
    });
    
    // Activar el primer tab por defecto
    const firstTab = new bootstrap.Tab(document.querySelector('#usuarios-tab'));
    firstTab.show();
    
    // Manejar clicks en botones de collapse
    $(document).on('click', '.collapse-btn', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const $button = $(this);
        const target = $button.attr('data-bs-target');
        const $icon = $button.find('i');
        const $targetElement = $(target);
        
        console.log('🔽 Click en collapse button, target:', target);
        
        if ($targetElement.length > 0) {
            // Usar Bootstrap 5 Collapse
            const collapseElement = document.querySelector(target);
            let bsCollapse = bootstrap.Collapse.getInstance(collapseElement);
            
            if (!bsCollapse) {
                bsCollapse = new bootstrap.Collapse(collapseElement, {
                    toggle: false
                });
            }
            
            // Toggle el collapse
            if ($targetElement.hasClass('show')) {
                bsCollapse.hide();
                $icon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
                console.log('📁 Colapsando:', target);
            } else {
                bsCollapse.show();
                $icon.removeClass('fa-chevron-down').addClass('fa-chevron-up');
                console.log('📂 Expandiendo:', target);
            }
            
        } else {
            console.log('❌ Target no encontrado:', target);
        }
    });
    
    // Verificar elementos cuando se active el tab responsables
    $('#responsables-tab').on('shown.bs.tab', function() {
        setTimeout(function() {
            const collapseButtons = $('.collapse-btn');
            const collapseElements = $('.collapse');
            
            console.log('📊 Elementos en tab responsables:');
            console.log('   - Botones collapse:', collapseButtons.length);
            console.log('   - Elementos collapse:', collapseElements.length);
            
            collapseButtons.each(function(index) {
                const target = $(this).attr('data-bs-target');
                const exists = $(target).length > 0;
                console.log(`   - Botón ${index + 1}: ${target} -> ${exists ? '✅' : '❌'}`);
            });
        }, 100);
    });
    
    console.log('✅ Admin dashboard inicializado correctamente');
});