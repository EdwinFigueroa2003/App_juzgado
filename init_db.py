#!/usr/bin/env python3
"""
Script para inicializar la base de datos en Railway
Ejecutar después del primer despliegue
"""

import sys
import os

# Agregar el directorio de la aplicación al path
sys.path.append('app_juzgado')

from modelo.configBd import obtener_conexion

def crear_tablas():
    """Crea las tablas necesarias en la base de datos"""
    print("🔧 Creando tablas en la base de datos...")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # 1. Tabla roles
        print("📋 Creando tabla 'roles'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                nombre_rol VARCHAR(50) NOT NULL UNIQUE,
                descripcion TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Tabla usuarios
        print("👥 Creando tabla 'usuarios'...")
        cursor.execute("""
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
        """)
        
        # 3. Tabla expediente
        print("📁 Creando tabla 'expediente'...")
        cursor.execute("""
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
        """)
        
        # 4. Tabla ingresos
        print("📥 Creando tabla 'ingresos'...")
        cursor.execute("""
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
        """)
        
        # 5. Tabla estados
        print("📊 Creando tabla 'estados'...")
        cursor.execute("""
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
        """)
        
        # 6. Tabla actuaciones
        print("⚡ Creando tabla 'actuaciones'...")
        cursor.execute("""
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
        """)
        
        # 7. Tabla ingresos_expediente (opcional - para compatibilidad)
        print("📝 Creando tabla 'ingresos_expediente'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingresos_expediente (
                id SERIAL PRIMARY KEY,
                expediente_id INTEGER REFERENCES expediente(id) ON DELETE CASCADE,
                fecha_ingreso DATE,
                motivo_ingreso TEXT,
                observaciones_ingreso TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 8. Tabla estados_expediente (opcional - para compatibilidad)
        print("📈 Creando tabla 'estados_expediente'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estados_expediente (
                id SERIAL PRIMARY KEY,
                expediente_id INTEGER REFERENCES expediente(id) ON DELETE CASCADE,
                estado VARCHAR(100),
                fecha_estado DATE,
                observaciones TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 9. Tabla expedientes_error (para logging de errores)
        print("❌ Creando tabla 'expedientes_error'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expedientes_error (
                id SERIAL PRIMARY KEY,
                tipo_error VARCHAR(100),
                hoja_origen VARCHAR(100),
                fila_origen INTEGER,
                radicado_completo VARCHAR(255),
                radicado_corto VARCHAR(255),
                demandante TEXT,
                demandado TEXT,
                mensaje_error TEXT,
                datos_completos TEXT,
                fecha_error TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Crear índices para mejorar rendimiento
        print("🔍 Creando índices...")
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_expediente_radicado_completo ON expediente(radicado_completo);",
            "CREATE INDEX IF NOT EXISTS idx_expediente_radicado_corto ON expediente(radicado_corto);",
            "CREATE INDEX IF NOT EXISTS idx_expediente_estado ON expediente(estado);",
            "CREATE INDEX IF NOT EXISTS idx_expediente_responsable ON expediente(responsable);",
            "CREATE INDEX IF NOT EXISTS idx_expediente_fecha_ingreso ON expediente(fecha_ingreso);",
            "CREATE INDEX IF NOT EXISTS idx_ingresos_expediente_id ON ingresos(expediente_id);",
            "CREATE INDEX IF NOT EXISTS idx_ingresos_fecha_ingreso ON ingresos(fecha_ingreso);",
            "CREATE INDEX IF NOT EXISTS idx_estados_expediente_id ON estados(expediente_id);",
            "CREATE INDEX IF NOT EXISTS idx_estados_fecha_estado ON estados(fecha_estado);",
            "CREATE INDEX IF NOT EXISTS idx_actuaciones_expediente_id ON actuaciones(expediente_id);",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario);",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_correo ON usuarios(correo);"
        ]
        
        for indice in indices:
            cursor.execute(indice)
        
        conn.commit()
        print("✅ Todas las tablas e índices creados exitosamente")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        import traceback
        traceback.print_exc()
        return False

def insertar_datos_iniciales():
    """Inserta datos iniciales necesarios"""
    print("🌱 Insertando datos iniciales...")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Insertar roles básicos
        print("👤 Insertando roles básicos...")
        roles_iniciales = [
            ('ESCRIBIENTE', 'Encargado de redacción y documentación'),
            ('SUSTANCIADOR', 'Encargado de revisión y sustanciación'),
            ('ADMINISTRADOR', 'Administrador del sistema')
        ]
        
        for nombre_rol, descripcion in roles_iniciales:
            cursor.execute("""
                INSERT INTO roles (nombre_rol, descripcion) 
                VALUES (%s, %s) 
                ON CONFLICT (nombre_rol) DO NOTHING
            """, (nombre_rol, descripcion))
        
        # Crear usuario administrador por defecto
        print("🔐 Creando usuario administrador...")
        cursor.execute("SELECT id FROM roles WHERE nombre_rol = 'ADMINISTRADOR'")
        admin_role_id = cursor.fetchone()[0]
        
        # Hash de la contraseña "admin123" (deberías cambiarla después)
        import hashlib
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO usuarios (nombre, usuario, correo, contrasena, rol_id, administrador, activo) 
            VALUES (%s, %s, %s, %s, %s, %s, %s) 
            ON CONFLICT (usuario) DO NOTHING
        """, ("Administrador", "admin", "admin@juzgado.com", password_hash, admin_role_id, True, True))
        
        conn.commit()
        print("✅ Datos iniciales insertados exitosamente")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error insertando datos iniciales: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_conexion():
    """Verifica que la conexión a la BD funcione"""
    print("🔍 Verificando conexión a la base de datos...")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Conexión exitosa. PostgreSQL version: {version[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def verificar_tablas():
    """Verifica que las tablas se crearon correctamente"""
    print("📋 Verificando tablas creadas...")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tablas = cursor.fetchall()
        print(f"✅ Tablas encontradas ({len(tablas)}):")
        for tabla in tablas:
            print(f"   - {tabla[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return False

if __name__ == "__main__":
    print("🚀 === INICIALIZACIÓN DE BASE DE DATOS PARA RAILWAY ===")
    print("Este script creará todas las tablas necesarias para la aplicación")
    print("=" * 60)
    
    if verificar_conexion():
        if crear_tablas():
            if insertar_datos_iniciales():
                if verificar_tablas():
                    print("\n" + "=" * 60)
                    print("✅ INICIALIZACIÓN COMPLETADA EXITOSAMENTE")
                    print("=" * 60)
                    print("📝 Usuario administrador creado:")
                    print("   Usuario: admin")
                    print("   Contraseña: admin123")
                    print("   ⚠️  CAMBIA LA CONTRASEÑA DESPUÉS DEL PRIMER LOGIN")
                    print("=" * 60)
                else:
                    print("\n❌ Error verificando tablas")
            else:
                print("\n❌ Error insertando datos iniciales")
        else:
            print("\n❌ Error creando tablas")
    else:
        print("\n❌ Error de conexión")
        sys.exit(1)