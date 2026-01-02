import psycopg2
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (solo en desarrollo local)
load_dotenv()

# Intentar obtener DATABASE_URL de las variables de entorno
#database_url = os.environ.get('DATABASE_URL')

def obtener_conexion():
    #Conexión usando variables de entorno
    try:
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