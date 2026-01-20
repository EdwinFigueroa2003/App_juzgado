# App Juzgado - Despliegue en Railway

## 🚀 Configuración para Railway

### 1. Variables de Entorno Requeridas

En Railway, configura las siguientes variables de entorno:

```bash
# Flask
SECRET_KEY=80dd31050215cc24bff484e16c187285cde3c343a2fa19209907fa1d7633f376
CSRF_SECRET_KEY=d0fe14792ad9b5bc127c544422862fb1133da22f75fc035c6338567f90b24b93
FLASK_ENV=production

# Base de Datos (Railway PostgreSQL)
# DATABASE_URL se genera automáticamente cuando agregas PostgreSQL
```

### 2. Pasos de Despliegue

#### Paso 1: Crear Proyecto en Railway
1. Ve a [railway.app](https://railway.app)
2. Crea un nuevo proyecto
3. Conecta tu repositorio de GitHub

#### Paso 2: Agregar Base de Datos
1. En tu proyecto Railway, haz clic en "Add Service"
2. Selecciona "PostgreSQL"
3. Railway generará automáticamente `DATABASE_URL`

#### Paso 3: Configurar Variables de Entorno
En la sección "Variables" de tu servicio web, agrega:
```
SECRET_KEY=80dd31050215cc24bff484e16c187285cde3c343a2fa19209907fa1d7633f376
CSRF_SECRET_KEY=d0fe14792ad9b5bc127c544422862fb1133da22f75fc035c6338567f90b24b93
FLASK_ENV=production
```

#### Paso 4: Desplegar
Railway desplegará automáticamente usando el `Procfile`

#### Paso 5: ⚠️ IMPORTANTE - Crear Tablas
**Después del primer despliegue, DEBES ejecutar este comando UNA SOLA VEZ:**

En la consola de Railway (o localmente):
```bash
python railway_setup.py
```

Este script:
- ✅ Crea todas las tablas necesarias
- ✅ Crea roles básicos (ESCRIBIENTE, SUSTANCIADOR, ADMINISTRADOR)
- ✅ Crea usuario administrador inicial
- ✅ Configura índices para mejor rendimiento

### 3. Acceso Inicial

Después de ejecutar `railway_setup.py`:

**Usuario Administrador:**
- Usuario: `admin`
- Contraseña: `admin123`
- ⚠️ **CAMBIA LA CONTRASEÑA** después del primer login

### 4. Estructura del Proyecto

```
app_juzgado/
├── app_juzgado/           # Código principal
│   ├── main.py           # Punto de entrada
│   ├── modelo/           # Configuración BD
│   ├── vista/            # Controladores
│   ├── templates/        # Templates HTML
│   └── static/           # CSS/JS
├── requirements.txt      # Dependencias
├── Procfile             # Configuración Railway
├── railway_setup.py     # Script de inicialización
└── gunicorn.conf.py     # Configuración servidor
```

### 5. Comandos Útiles

```bash
# Desarrollo local
python app_juzgado/main.py

# Configurar BD en Railway (UNA SOLA VEZ)
python railway_setup.py

# Ver logs en Railway
railway logs

# Conectar a BD en Railway
railway connect
```

### 6. Características

- ✅ Flask con Gunicorn (producción)
- ✅ PostgreSQL con índices optimizados
- ✅ Protección CSRF
- ✅ Headers de seguridad
- ✅ Auto-scaling
- ✅ SSL automático
- ✅ Dominio personalizable

### 7. Troubleshooting

#### ❌ "No hay tablas en la BD"
**Solución:** Ejecuta `python railway_setup.py` UNA VEZ después del despliegue

#### ❌ Error de conexión a BD
- Verifica que el servicio PostgreSQL esté activo
- `DATABASE_URL` se genera automáticamente

#### ❌ Error 500 en la aplicación
- Revisa los logs: `railway logs`
- Verifica que todas las variables de entorno estén configuradas

#### ❌ No puedo hacer login
- Usuario: `admin`, Contraseña: `admin123`
- Si no funciona, ejecuta `railway_setup.py` de nuevo

### 8. Monitoreo

Railway proporciona:
- 📊 Logs en tiempo real
- 📈 Métricas CPU/RAM
- 🔄 Reinicio automático
- 🏥 Health checks
- 🌐 Dominio: `tu-app.up.railway.app`

### 9. Seguridad

- 🔒 HTTPS automático
- 🛡️ Headers de seguridad configurados
- 🔐 Protección CSRF
- 👤 Sistema de usuarios y roles
- 🚫 Variables sensibles en entorno

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs: `railway logs`
2. Verifica variables de entorno
3. Asegúrate de haber ejecutado `railway_setup.py`