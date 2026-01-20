# App Juzgado - Despliegue en Railway

## 🚀 Configuración para Railway

### 1. Variables de Entorno Requeridas

En Railway, configura las siguientes variables de entorno:

```bash
# Flask
SECRET_KEY=tu_secret_key_aqui
CSRF_SECRET_KEY=tu_csrf_secret_key_aqui
FLASK_ENV=production

# Base de Datos (Railway PostgreSQL)
DATABASE_URL=postgresql://usuario:password@host:puerto/database
```

### 2. Servicios Necesarios

1. **PostgreSQL Database**: Agrega un servicio de PostgreSQL en Railway
2. **Web Service**: Tu aplicación Flask

### 3. Pasos de Despliegue

1. **Conectar Repositorio**:
   - Conecta tu repositorio de GitHub a Railway
   - Railway detectará automáticamente el `Procfile`

2. **Configurar Base de Datos**:
   - Agrega un servicio PostgreSQL
   - Railway generará automáticamente `DATABASE_URL`

3. **Variables de Entorno**:
   ```bash
   SECRET_KEY=80dd31050215cc24bff484e16c187285cde3c343a2fa19209907fa1d7633f376
   CSRF_SECRET_KEY=d0fe14792ad9b5bc127c544422862fb1133da22f75fc035c6338567f90b24b93
   FLASK_ENV=production
   ```

4. **Deploy**:
   - Railway desplegará automáticamente usando el `Procfile`
   - Usará Gunicorn como servidor WSGI

### 4. Estructura del Proyecto

```
app_juzgado/
├── app_juzgado/           # Código principal de la aplicación
│   ├── main.py           # Punto de entrada
│   ├── modelo/           # Modelos y configuración BD
│   ├── vista/            # Controladores/Vistas
│   ├── templates/        # Templates HTML
│   └── static/           # Archivos estáticos
├── requirements.txt      # Dependencias Python
├── Procfile             # Configuración Railway
├── gunicorn.conf.py     # Configuración Gunicorn
├── railway.toml         # Configuración Railway
└── .gitignore           # Archivos a ignorar
```

### 5. Comandos Útiles

```bash
# Desarrollo local
python app_juzgado/main.py

# Producción con Gunicorn
cd app_juzgado && gunicorn --config ../gunicorn.conf.py main:app
```

### 6. Características

- ✅ Flask con Gunicorn
- ✅ PostgreSQL
- ✅ Protección CSRF
- ✅ Headers de seguridad
- ✅ Variables de entorno
- ✅ Logging configurado
- ✅ Auto-scaling en Railway

### 7. Monitoreo

Railway proporciona:
- Logs en tiempo real
- Métricas de CPU/RAM
- Reinicio automático en caso de fallo
- Health checks

### 8. Dominios

Railway asigna automáticamente:
- Subdominio: `tu-app.up.railway.app`
- Puedes configurar un dominio personalizado

## 🔧 Troubleshooting

### Error de Conexión a BD
- Verifica que `DATABASE_URL` esté configurada
- Asegúrate de que el servicio PostgreSQL esté activo

### Error de Variables de Entorno
- Verifica que todas las variables estén configuradas en Railway
- No incluyas comillas en los valores

### Error de Puerto
- Railway asigna automáticamente el puerto via `PORT` env var
- No hardcodees el puerto en el código