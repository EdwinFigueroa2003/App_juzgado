# 🚀 Guía Completa de Despliegue en Railway

## Requisitos Previos

- Cuenta en [Railway.app](https://railway.app)
- Repositorio Git en GitHub (público o privado)
- Proyecto Git vinculado a Railway

## 📋 Checklist de Configuración

### ✅ Paso 1: Preparar el Repositorio

```bash
# Asegúrate que tengas estos archivos en el raíz del proyecto:
- .env.example          # Plantilla de variables de entorno
- .gitignore            # Archivos a excluir de Git
- .dockerignore         # Archivos a excluir del build
- Procfile              # Comando para iniciar la app
- railway.toml          # Configuración de Railway
- requirements.txt      # Dependencias de Python
- runtime.txt           # Versión de Python
```

### ✅ Paso 2: Verificar Variables de Entorno Locales

Crea un archivo `.env` en el raíz (NO se sube a Git):

```bash
cp .env.example .env
```

Edita `.env` con tus valores locales:

```ini
FLASK_ENV=development
SECRET_KEY=una-clave-aleatoria-segura-min-32-caracteres
CSRF_SECRET_KEY=otra-clave-aleatoria-segura-min-32-caracteres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=app_juzgado
DB_USER=postgres
DB_PASSWORD=tu-contraseña
```

### ✅ Paso 3: Generar Claves Secretas Seguras

Ejecuta en terminal Python:

```python
import secrets
print(secrets.token_hex(32))  # Para SECRET_KEY
print(secrets.token_hex(32))  # Para CSRF_SECRET_KEY
```

### ✅ Paso 4: Configurar en Railway

#### 4.1 - Crear Proyecto en Railway

1. Inicia sesión en [railway.app](https://railway.app)
2. Haz clic en "New Project"
3. Selecciona "Deploy from GitHub"
4. Conecta tu repositorio

#### 4.2 - Agregar PostgreSQL

1. En el proyecto de Railway, haz clic en "Add Service"
2. Selecciona "PostgreSQL"
3. Railway generará automáticamente la variable `DATABASE_URL`

#### 4.3 - Configurar Variables de Entorno

En Railway, ve a la pestaña "Variables" y agrega:

```
FLASK_ENV=production
SECRET_KEY=<tu-clave-secreta-generada>
CSRF_SECRET_KEY=<tu-clave-csrf-secreta-generada>
WEB_CONCURRENCY=2
```

**El `DATABASE_URL` se genera automáticamente al agregar PostgreSQL**

### ✅ Paso 5: Conectar Servicios

1. Abre el archivo `Procfile` en tu proyecto (ya está configurado)
2. Railway leerá automáticamente el comando de inicio
3. Los servicios se conectarán automáticamente a través de `DATABASE_URL`

## 🚀 Despliegue

### Primera Vez

1. Haz un `git push` a tu rama principal
2. Railway detectará cambios y iniciará el build automáticamente
3. Espera a que compile (2-3 minutos)
4. Una vez en verde, la app estará en línea

### Después del Primer Despliegue - IMPORTANTE ⚠️

**Necesitas crear las tablas de la base de datos UNA SOLA VEZ:**

#### Opción A: Desde Railway Shell

1. En tu proyecto Railway, ve a la pestaña "Shell"
2. Ejecuta:
   ```bash
   python railway_setup.py
   ```

#### Opción B: Desde tu Máquina Local

```bash
# Primero, configura la conexión a Railway (copia DATABASE_URL de Railway)
export DATABASE_URL=postgresql://user:password@host:port/database

# O en Windows PowerShell:
$env:DATABASE_URL = "postgresql://user:password@host:port/database"

# Luego ejecuta:
python railway_setup.py
```

## 📊 Monitoreo y Logs

### Ver Logs en Tiempo Real

1. Ve a tu proyecto en Railway
2. Haz clic en tu servicio web
3. Abre la pestaña "Logs"
4. Verás los logs de gunicorn y Flask en tiempo real

### Reiniciar la App

1. Ve a "Deployments"
2. Haz clic en el tres puntos del deployment actual
3. Selecciona "Redeploy"

## 🔧 Solución de Problemas

### Error: "Build failed"

```
Revisar los logs de Railway:
1. Ve a "Deployments"
2. Haz clic en el deployment fallido
3. Lee los logs de error
4. Asegúrate que requirements.txt incluya gunicorn
```

### Error: "Application failed to start"

```
Posibles causas:
1. Falta DATABASE_URL → Agrega servicio PostgreSQL
2. Faltan variables de entorno → Verifica SECRET_KEY y CSRF_SECRET_KEY
3. Tablas no creadas → Ejecuta railway_setup.py
```

### Error de Conexión a Base de Datos

```
1. Verifica DATABASE_URL está configurada
2. Asegúrate que PostgreSQL está en "Running" en Railway
3. Comprueba que railway_setup.py se ejecutó
4. Revisa que configBd.py usa DATABASE_URL
```

### App se detiene después de minutos

```
Posible causa: Timeout en health check
Solución:
1. En railway.toml aumenta healthcheckTimeout
2. Asegúrate que "/" (ruta raíz) responde en menos de 5 segundos
```

## 📝 Estructura de Archivos Verificada

```
app_juzgado/
├── main.py                 # Archivo principal de Flask
├── requirements.txt        # ✅ Dependencias (con gunicorn)
├── railway.toml            # ✅ Configuración Railway
├── Procfile                # ✅ Comando de inicio
├── gunicorn.conf.py        # ✅ Configuración Gunicorn
├── .env.example            # ✅ Plantilla de variables
├── .gitignore              # ✅ Archivos a excluir
├── .dockerignore           # ✅ Archivos a excluir del build
├── runtime.txt             # ✅ Versión de Python
├── railway_setup.py        # Script para crear tablas
├── modelo/
│   └── configBd.py         # ✅ Conecta con DATABASE_URL
└── [otros archivos]
```

## ✨ Comandos Útiles

### Generar nuevas claves seguras:
```bash
python -c "import secrets; print('SECRET_KEY:', secrets.token_hex(32)); print('CSRF_SECRET_KEY:', secrets.token_hex(32))"
```

### Probar localmente con gunicorn:
```bash
cd app_juzgado
gunicorn --config ../gunicorn.conf.py main:app
```

### Verificar que requirements.txt está completo:
```bash
pip list > requirements.txt
```

## 🔒 Seguridad

✅ Las claves secretas está en variables de entorno (no en el código)
✅ .env nunca se sube a Git (está en .gitignore)
✅ Gunicorn se ejecuta en puerto 0.0.0.0 (accesible desde Railway)
✅ Headers de seguridad están configurados en main.py

## 📞 Soporte

Si tienes problemas:

1. Revisa los logs de Railway
2. Verifica las variables de entorno
3. Asegúrate que railroad_setup.py se ejecutó
4. Comprueba la conexión a PostgreSQL

¡Tu app debería estar lista para producción! 🎉
