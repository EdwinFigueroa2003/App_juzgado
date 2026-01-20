import psycopg2
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (solo en desarrollo local)
load_dotenv()

def obtener_conexion():
    """Conexión que funciona tanto en desarrollo como en producción (Railway)"""
    try:
        # Intentar usar DATABASE_URL primero (Railway/producción)
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # Parsear la URL de la base de datos
            url = urlparse(database_url)
            return psycopg2.connect(
                host=url.hostname,
                database=url.path[1:],  # Remover el '/' inicial
                user=url.username,
                password=url.password,
                port=url.port or 5432,
                client_encoding='utf8'
            )
        else:
            # Usar variables de entorno individuales (desarrollo local)
            return psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                port=os.getenv('DB_PORT', '5432'),
                client_encoding='utf8'
            )
    except Exception as e:
        print(f"Error conectando a BD: {e}")
        raise