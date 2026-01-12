/**
 * Validador de contraseñas en tiempo real
 */

class PasswordValidator {
    constructor() {
        this.debounceTimer = null;
        this.debounceDelay = 500; // 500ms de delay
    }

    /**
     * Inicializa el validador en un campo de contraseña
     * @param {string} passwordFieldId - ID del campo de contraseña
     * @param {string} resultContainerId - ID del contenedor para mostrar resultados
     */
    init(passwordFieldId, resultContainerId) {
        const passwordField = document.getElementById(passwordFieldId);
        const resultContainer = document.getElementById(resultContainerId);

        if (!passwordField || !resultContainer) {
            console.error('Password field or result container not found');
            return;
        }

        // Agregar event listeners
        passwordField.addEventListener('input', (e) => {
            this.validatePasswordDebounced(e.target.value, resultContainer);
        });

        passwordField.addEventListener('focus', () => {
            resultContainer.style.display = 'block';
        });

        // Crear estructura inicial del contenedor de resultados
        this.createResultStructure(resultContainer);
    }

    /**
     * Crea la estructura HTML para mostrar los resultados
     * @param {HTMLElement} container - Contenedor de resultados
     */
    createResultStructure(container) {
        container.innerHTML = `
            <div class="password-strength-container" style="display: none;">
                <div class="strength-bar-container">
                    <div class="strength-bar">
                        <div class="strength-fill" style="width: 0%; background-color: #dc3545;"></div>
                    </div>
                    <span class="strength-text">Muy Débil</span>
                </div>
                <div class="validation-messages">
                    <div class="errors-list"></div>
                    <div class="suggestions-list"></div>
                </div>
            </div>
        `;
    }

    /**
     * Valida contraseña con debounce
     * @param {string} password - Contraseña a validar
     * @param {HTMLElement} resultContainer - Contenedor de resultados
     */
    validatePasswordDebounced(password, resultContainer) {
        // Limpiar timer anterior
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Si la contraseña está vacía, ocultar resultados
        if (!password.trim()) {
            resultContainer.querySelector('.password-strength-container').style.display = 'none';
            return;
        }

        // Configurar nuevo timer
        this.debounceTimer = setTimeout(() => {
            this.validatePassword(password, resultContainer);
        }, this.debounceDelay);
    }

    /**
     * Valida contraseña llamando a la API
     * @param {string} password - Contraseña a validar
     * @param {HTMLElement} resultContainer - Contenedor de resultados
     */
    async validatePassword(password, resultContainer) {
        try {
            console.log('[DEBUG] Validando contraseña, longitud:', password.length);
            
            const requestData = { password: password };
            console.log('[DEBUG] Enviando datos:', requestData);
            
            const response = await fetch('/api/validate-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            console.log('[DEBUG] Response status:', response.status);
            console.log('[DEBUG] Response ok:', response.ok);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[ERROR] Response no ok:', errorText);
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log('[DEBUG] Resultado recibido:', result);
            this.displayResults(result, resultContainer);

        } catch (error) {
            console.error('[ERROR] Error validating password:', error);
            this.displayError(resultContainer, error.message);
        }
    }

    /**
     * Muestra los resultados de validación
     * @param {Object} result - Resultado de la validación
     * @param {HTMLElement} container - Contenedor de resultados
     */
    displayResults(result, container) {
        const strengthContainer = container.querySelector('.password-strength-container');
        const strengthFill = container.querySelector('.strength-fill');
        const strengthText = container.querySelector('.strength-text');
        const errorsList = container.querySelector('.errors-list');
        const suggestionsList = container.querySelector('.suggestions-list');

        // Mostrar contenedor
        strengthContainer.style.display = 'block';

        // Actualizar barra de fortaleza
        const score = result.score || 0;
        const strength = result.strength || 'Muy Débil';
        
        strengthFill.style.width = `${score}%`;
        strengthFill.style.backgroundColor = this.getStrengthColor(score);
        strengthText.textContent = `${strength} (${score}/100)`;

        // Mostrar errores
        errorsList.innerHTML = '';
        if (result.errors && result.errors.length > 0) {
            const errorsTitle = document.createElement('div');
            errorsTitle.className = 'validation-title text-danger';
            errorsTitle.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Problemas:';
            errorsList.appendChild(errorsTitle);

            result.errors.forEach(error => {
                const errorItem = document.createElement('div');
                errorItem.className = 'validation-item text-danger';
                errorItem.innerHTML = `<i class="fas fa-times"></i> ${error}`;
                errorsList.appendChild(errorItem);
            });
        }

        // Mostrar sugerencias
        suggestionsList.innerHTML = '';
        if (result.suggestions && result.suggestions.length > 0) {
            const suggestionsTitle = document.createElement('div');
            suggestionsTitle.className = 'validation-title text-info';
            suggestionsTitle.innerHTML = '<i class="fas fa-lightbulb"></i> Sugerencias:';
            suggestionsList.appendChild(suggestionsTitle);

            result.suggestions.forEach(suggestion => {
                const suggestionItem = document.createElement('div');
                suggestionItem.className = 'validation-item text-info';
                suggestionItem.innerHTML = `<i class="fas fa-arrow-right"></i> ${suggestion}`;
                suggestionsList.appendChild(suggestionItem);
            });
        }

        // Si la contraseña es válida, mostrar mensaje de éxito
        if (result.is_valid) {
            const successItem = document.createElement('div');
            successItem.className = 'validation-item text-success';
            successItem.innerHTML = '<i class="fas fa-check"></i> ¡Contraseña válida!';
            errorsList.appendChild(successItem);
        }
    }

    /**
     * Muestra error de validación
     * @param {HTMLElement} container - Contenedor de resultados
     * @param {string} errorMessage - Mensaje de error específico
     */
    displayError(container, errorMessage = 'Error al validar contraseña') {
        const strengthContainer = container.querySelector('.password-strength-container');
        const errorsList = container.querySelector('.errors-list');
        
        strengthContainer.style.display = 'block';
        errorsList.innerHTML = `
            <div class="validation-item text-danger">
                <i class="fas fa-exclamation-triangle"></i> ${errorMessage}
            </div>
        `;
    }

    /**
     * Obtiene el color según la fortaleza de la contraseña
     * @param {number} score - Puntaje de fortaleza (0-100)
     * @returns {string} Color CSS
     */
    getStrengthColor(score) {
        if (score >= 80) return '#28a745'; // Verde - Muy Fuerte
        if (score >= 60) return '#20c997'; // Verde claro - Fuerte
        if (score >= 40) return '#ffc107'; // Amarillo - Moderada
        if (score >= 20) return '#fd7e14'; // Naranja - Débil
        return '#dc3545'; // Rojo - Muy Débil
    }

    /**
     * Valida formulario antes del envío
     * @param {string} passwordFieldId - ID del campo de contraseña
     * @returns {boolean} True si la contraseña es válida
     */
    async validateBeforeSubmit(passwordFieldId) {
        const passwordField = document.getElementById(passwordFieldId);
        if (!passwordField) {
            console.error('[ERROR] Campo de contraseña no encontrado:', passwordFieldId);
            return false;
        }

        const password = passwordField.value;
        if (!password.trim()) {
            console.log('[DEBUG] Contraseña vacía en validateBeforeSubmit');
            return false;
        }

        try {
            console.log('[DEBUG] Validando antes del envío, longitud:', password.length);
            
            const response = await fetch('/api/validate-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ password: password })
            });

            console.log('[DEBUG] Response status en validateBeforeSubmit:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[ERROR] Error en validateBeforeSubmit:', errorText);
                return false;
            }

            const result = await response.json();
            console.log('[DEBUG] Resultado validateBeforeSubmit:', result);
            return result.is_valid;

        } catch (error) {
            console.error('[ERROR] Error validating password before submit:', error);
            return false;
        }
    }
}

// Crear instancia global
window.passwordValidator = new PasswordValidator();

// Inicializar automáticamente cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Buscar campos de contraseña y inicializar validación
    const passwordFields = document.querySelectorAll('input[type="password"][data-validate="true"]');
    
    passwordFields.forEach((field, index) => {
        const fieldId = field.id || `password-field-${index}`;
        field.id = fieldId;
        
        // Crear contenedor de resultados si no existe
        let resultContainer = document.getElementById(`${fieldId}-validation`);
        if (!resultContainer) {
            resultContainer = document.createElement('div');
            resultContainer.id = `${fieldId}-validation`;
            resultContainer.className = 'password-validation-results mt-2';
            field.parentNode.insertBefore(resultContainer, field.nextSibling);
        }
        
        // Inicializar validador
        window.passwordValidator.init(fieldId, `${fieldId}-validation`);
    });
});