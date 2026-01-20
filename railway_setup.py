#!/usr/bin/env python3
"""
Script simplificado para Railway - Ejecutar una sola vez después del despliegue
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    """Obtiene conexión usando DATABASE_URL de Railway"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL no encontrada en variables de entorno")
    
    url = urlparse(database_url)
    return psycopg2.connect(
        host=url.hostname,
        database=url.path[1:],
        user=url.username,
        password=url.password,
        port=url.port or 5432,
        client_encoding='utf8'
    )

def setup_database():
    """Configura la base de datos completa"""
    print("🚀 Configurando base de datos en Railway...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Crear todas las tablas de una vez
        sql_script = """
        -- Tabla roles
        CREATE TABLE IF NOT EXISTS roles (
            id SERIAL PRIMARY KEY,
            nombre_rol VARCHAR(50) NOT NULL UNIQUE,
            descripcion TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Tabla usuarios
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255),
            usuario VARCHAR(100) NOT NULL UNIQUE,
            correo VARCHAR(255) NOT NULL UNIQUE,
            contrasena VARCHAR(255) NOT NULL,
            rol_id INTEGER REFERENCES roles(id),
            administrador BOOLEAN DEFAULT FALSE,
            activo BOOLEAN DEFAULT TRUE,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Tabla expediente
        CREATE TABLE IF NOT EXISTS expediente (
            id SERIAL PRIMARY KEY,
            fecha_ingreso DATE,
            juzgado_origen INTEGER,
            radicado_completo VARCHAR(255),
            demandante TEXT,
            demandado TEXT,
            radicado_corto VARCHAR(255),
            responsable VARCHAR(255),
            estado VARCHAR(100),
            tipo_solicitud VARCHAR(255),
            tipo_tramite VARCHAR(255),
            ubicacion VARCHAR(255),
            ubicacion_actual VARCHAR(255),
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Tabla ingresos
        CREATE TABLE IF NOT EXISTS ingresos (
            id SERIAL PRIMARY KEY,
            expediente_id INTEGER REFERENCES expediente(id) ON DELETE CASCADE,
            fecha_ingreso DATE,
            observaciones TEXT,
            solicitud TEXT,
            fechas TEXT,
            actuacion_id INTEGER,
            ubicacion VARCHAR(255),
            fecha_estado_auto DATE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Tabla estados
        CREATE TABLE IF NOT EXISTS estados (
            id SERIAL PRIMARY KEY,
            expediente_id INTEGER REFERENCES expediente(id) ON DELETE CASCADE,
            fecha_estado DATE,
            clase VARCHAR(255),
            auto_anotacion TEXT,
            observaciones TEXT,
            actuacion_id INTEGER,
            ingresos_id INTEGER,
            fecha_auto DATE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Tabla actuaciones
        CREATE TABLE IF NOT EXISTS actuaciones (
            id SERIAL PRIMARY KEY,
            expediente_id INTEGER REFERENCES expediente(id) ON DELETE CASCADE,
            numero_actuacion INTEGER,
            descripcion_actuacion TEXT,
            tipo_origen VARCHAR(100),
            archivo_origen VARCHAR(255),
            fecha_actuacion DATE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Índices principales
        CREATE INDEX IF NOT EXISTS idx_expediente_radicado_completo ON expediente(radicado_completo);
        CREATE INDEX IF NOT EXISTS idx_expediente_radicado_corto ON expediente(radicado_corto);
        CREATE INDEX IF NOT EXISTS idx_expediente_estado ON expediente(estado);
        CREATE INDEX IF NOT EXISTS idx_ingresos_expediente_id ON ingresos(expediente_id);
        CREATE INDEX IF NOT EXISTS idx_estados_expediente_id ON estados(expediente_id);

        -- Insertar roles básicos
        INSERT INTO roles (nombre_rol, descripcion) VALUES 
        ('ESCRIBIENTE', 'Encargado de redacción y documentación'),
        ('SUSTANCIADOR', 'Encargado de revisión y sustanciación'),
        ('ADMINISTRADOR', 'Administrador del sistema')
        ON CONFLICT (nombre_rol) DO NOTHING;

        -- Crear usuario admin (contraseña: admin123)
        INSERT INTO usuarios (nombre, usuario, correo, contrasena, rol_id, administrador, activo) 
        SELECT 'Administrador', 'admin', 'admin@juzgado.com', 
               'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 
               r.id, true, true
        FROM roles r WHERE r.nombre_rol = 'ADMINISTRADOR'
        ON CONFLICT (usuario) DO NOTHING;
        """
        
        cursor.execute(sql_script)
        conn.commit()
        
        # Verificar que todo se creó correctamente
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' ORDER BY table_name;
        """)
        tablas = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM roles;")
        roles_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM usuarios;")
        usuarios_count = cursor.fetchone()[0]
        
        print(f"✅ Base de datos configurada exitosamente:")
        print(f"   📋 Tablas creadas: {len(tablas)}")
        print(f"   👤 Roles: {roles_count}")
        print(f"   👥 Usuarios: {usuarios_count}")
        print(f"\n🔐 Usuario administrador:")
        print(f"   Usuario: admin")
        print(f"   Contraseña: admin123")
        print(f"   ⚠️  CAMBIA LA CONTRASEÑA DESPUÉS DEL PRIMER LOGIN")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error configurando base de datos: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 === CONFIGURACIÓN RAILWAY ===")
    
    if setup_database():
        print("\n✅ ¡Configuración completada! Tu aplicación está lista.")
    else:
        print("\n❌ Error en la configuración")
        sys.exit(1)