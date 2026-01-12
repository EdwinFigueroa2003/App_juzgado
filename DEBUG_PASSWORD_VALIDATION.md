# Debug de Validación de Contraseñas

## Problema Identificado
Error 400 en `/api/validate-password` cuando se intenta validar contraseñas en tiempo real.

## Cambios Realizados para Depuración

### 1. Backend (vistausuarios.py)
- ✅ Agregado logging detallado en `api_validate_password()`
- ✅ Verificación de Content-Type JSON
- ✅ Validación de datos recibidos
- ✅ Manejo de errores mejorado
- ✅ Logging de excepciones completas

### 2. Frontend (password-validator.js)
- ✅ Agregado logging en consola del navegador
- ✅ Logging de datos enviados y recibidos
- ✅ Mejor manejo de errores con mensajes específicos
- ✅ Logging en `validateBeforeSubmit()`

### 3. Archivo de Prueba
- ✅ Creado `test_password_api.py` para probar la API directamente

## Cómo Depurar

### Paso 1: Verificar Logs del Servidor
Cuando uses la funcionalidad de cambio de contraseñas, revisa la consola del servidor Flask para ver:
```
[DEBUG] API validate-password llamada
[DEBUG] Content-Type: application/json
[DEBUG] Method: POST
[DEBUG] Data recibida: {'password': 'tu_contraseña'}
[DEBUG] Password length: X
[DEBUG] Validando contraseña...
[DEBUG] Resultado validación: {...}
```

### Paso 2: Verificar Logs del Navegador
Abre las herramientas de desarrollador (F12) y ve a la pestaña Console para ver:
```
[DEBUG] Validando contraseña, longitud: X
[DEBUG] Enviando datos: {password: "..."}
[DEBUG] Response status: 200
[DEBUG] Response ok: true
[DEBUG] Resultado recibido: {...}
```

### Paso 3: Probar API Directamente
Ejecuta el script de prueba:
```bash
python test_password_api.py
```

### Paso 4: Verificar Red
En las herramientas de desarrollador, ve a la pestaña Network y busca las peticiones a `/api/validate-password` para ver:
- Status code
- Request headers
- Request payload
- Response

## Posibles Causas del Error 400

1. **Content-Type incorrecto**: El JavaScript no está enviando `application/json`
2. **Datos malformados**: El JSON no se está parseando correctamente
3. **CSRF Token**: Puede que se requiera token CSRF
4. **Ruta incorrecta**: La URL no está llegando al endpoint correcto

## Soluciones Potenciales

### Si el problema es CSRF Token:
Agregar token CSRF a las peticiones AJAX:
```javascript
const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

fetch('/api/validate-password', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({ password: password })
});
```

### Si el problema es la ruta:
Verificar que el blueprint esté registrado correctamente en main.py

### Si el problema persiste:
Crear una ruta de prueba simple para verificar conectividad:
```python
@vistausuarios.route('/api/test', methods=['GET'])
def api_test():
    return jsonify({'status': 'ok', 'message': 'API funcionando'})
```

## Estado Actual
- ✅ Logging agregado para depuración
- ✅ Manejo de errores mejorado
- ✅ Script de prueba creado
- ⏳ Pendiente: Ejecutar pruebas y revisar logs