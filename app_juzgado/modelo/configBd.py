import psycopg2
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Cargar variables de entorno desde múltiples ubicaciones posibles
# override=True garantiza que el .env de la raíz siempre tiene la última palabra
load_dotenv()  # Busca .env en directorio actual
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)       # app_juzgado/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=True) # raíz/.env

"""def obtener_conexion():
    #Conexión que funciona tanto en desarrollo como en producción (Railway)
    try:
        # Verificar si estamos en modo desarrollo
        flask_env = os.getenv('FLASK_ENV', '').lower()
        is_development = flask_env == 'development'
        
        # En desarrollo, forzar uso de configuración local
        if is_development:
            print("🏠 Modo desarrollo: Usando configuración local (.env)")
            
            # Obtener credenciales de variables de entorno (SIN valores por defecto)
            db_host = os.getenv('DB_HOST', 'localhost')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_password = os.getenv('DB_PASSWORD')
            db_port = os.getenv('DB_PORT', '5433')
            
            # Verificar que las credenciales críticas estén configuradas
            if not db_password:
                raise Exception("❌ DB_PASSWORD no configurada en variables de entorno (.env)")
            if not db_name:
                raise Exception("❌ DB_NAME no configurada en variables de entorno (.env)")
            if not db_user:
                raise Exception("❌ DB_USER no configurada en variables de entorno (.env)")
            
            db_config = {
                'host': db_host,
                'database': db_name,
                'user': db_user,
                'password': db_password,
                'port': db_port,
                'client_encoding': 'utf8'
            }
            
            #print(f"   Host: {db_config['host']}")
            #print(f"   Database: {db_config['database']}")
            #print(f"   User: {db_config['user']}")
            #print(f"   Port: {db_config['port']}")
            
            return psycopg2.connect(**db_config)
        
        # En producción, usar DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            print("� Usando DATABASE_URL (Railway/Producción)")
            # Parsear la URL de la base de datos
            url = urlparse(database_url)
            return psycopg2.connect(
                host=url.hostname,
                database=url.path[1:],  # Remover el '/' inicial
                user=url.username,
                password=url.password,
                port=url.port or 5433,
                client_encoding='utf8'
            )
        else:
            # Fallback a configuración local (pero sin credenciales hardcodeadas)
            print("🏠 Fallback: Usando configuración local (.env)")
            
            # Obtener credenciales de variables de entorno (SIN valores por defecto)
            db_host = os.getenv('DB_HOST', 'localhost')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_password = os.getenv('DB_PASSWORD')
            db_port = os.getenv('DB_PORT', '5433')
            
            # Verificar que las credenciales críticas estén configuradas
            if not db_password:
                raise Exception("❌ DB_PASSWORD no configurada en variables de entorno")
            if not db_name:
                raise Exception("❌ DB_NAME no configurada en variables de entorno")
            if not db_user:
                raise Exception("❌ DB_USER no configurada en variables de entorno")
            
            db_config = {
                'host': db_host,
                'database': db_name,
                'user': db_user,
                'password': db_password,
                'port': db_port,
                'client_encoding': 'utf8'
            }
            
            return psycopg2.connect(**db_config)
            
    except Exception as e:
        raise """

def obtener_conexion():
   #Conexión que funciona tanto en desarrollo como en producción (Railway)
    try:
        # 👉 PRIORIDAD 1: Producción (Railway)
        database_url = os.environ.get('DATABASE_URL')

        if database_url:
            print("🚀 Producción: Usando DATABASE_URL (Railway)")
            url = urlparse(database_url)
            return psycopg2.connect(
                host=url.hostname,
                database=url.path[1:],
                user=url.username,
                password=url.password,
                port=url.port or 5432,
                client_encoding='utf8'
            )

        # 👉 PRIORIDAD 2: Desarrollo local (.env)
        print("🏠 Desarrollo: Usando configuración local (.env)")

        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'port': os.getenv('DB_PORT', '5432'),
            'client_encoding': 'utf8'
        }

        # Validaciones
        for key in ['database', 'user', 'password']:
            if not db_config[key]:
                raise Exception(f"❌ Variable {key.upper()} no configurada")

        return psycopg2.connect(**db_config)

    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        raise
