#!/usr/bin/env python3
"""
Script para migrar datos desde base de datos local a Railway
IMPORTANTE: Ejecutar después de railway_setup.py
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def get_local_connection():
    """Conexión a base de datos local usando variables de entorno"""
    # Cargar variables de entorno
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(dotenv_path='app_juzgado/.env')
    
    # Obtener credenciales de variables de entorno
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_port = os.getenv('DB_PORT', '5432')
    
    # Verificar que las credenciales estén configuradas
    if not db_name:
        raise Exception("❌ DB_NAME no configurada en variables de entorno")
    if not db_user:
        raise Exception("❌ DB_USER no configurada en variables de entorno")
    if not db_password:
        raise Exception("❌ DB_PASSWORD no configurada en variables de entorno")
    
    return psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port,
        client_encoding='utf8'
    )

def get_railway_connection():
    """Conexión a base de datos Railway"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL no encontrada. Configúrala con la URL de Railway")
    
    url = urlparse(database_url)
    return psycopg2.connect(
        host=url.hostname,
        database=url.path[1:],
        user=url.username,
        password=url.password,
        port=url.port or 5432,
        client_encoding='utf8'
    )

def migrate_table(table_name, local_conn, railway_conn, batch_size=1000):
    """Migra una tabla específica"""
    print(f"📋 Migrando tabla '{table_name}'...")
    
    try:
        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()
        
        # Obtener estructura de la tabla LOCAL
        local_cursor.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position
        """)
        local_columns_info = local_cursor.fetchall()
        
        if not local_columns_info:
            print(f"   ⚠️  Tabla '{table_name}' no encontrada en BD local")
            return 0
        
        # Obtener estructura de la tabla RAILWAY
        railway_cursor.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position
        """)
        railway_columns_info = railway_cursor.fetchall()
        
        if not railway_columns_info:
            print(f"   ⚠️  Tabla '{table_name}' no encontrada en BD Railway")
            return 0
        
        # Obtener solo las columnas que existen en AMBAS tablas
        local_columns = [col[0] for col in local_columns_info]
        railway_columns = [col[0] for col in railway_columns_info]
        
        # Columnas comunes (intersección)
        common_columns = [col for col in local_columns if col in railway_columns]
        
        if not common_columns:
            print(f"   ⚠️  No hay columnas comunes entre BD local y Railway para '{table_name}'")
            return 0
        
        print(f"   📊 Columnas a migrar: {len(common_columns)} de {len(local_columns)} disponibles")
        if len(common_columns) < len(local_columns):
            excluded = [col for col in local_columns if col not in railway_columns]
            print(f"   ⚠️  Columnas excluidas: {', '.join(excluded)}")
        
        columns_str = ', '.join(common_columns)
        placeholders = ', '.join(['%s'] * len(common_columns))
        
        # Contar registros totales
        local_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = local_cursor.fetchone()[0]
        
        if total_records == 0:
            print(f"   📭 Tabla '{table_name}' está vacía")
            return 0
        
        print(f"   📊 Total de registros: {total_records:,}")
        
        # Migrar en lotes
        migrated = 0
        offset = 0
        
        while offset < total_records:
            try:
                # Leer lote de la BD local (solo columnas comunes)
                local_cursor.execute(f"""
                    SELECT {columns_str} 
                    FROM {table_name} 
                    ORDER BY id 
                    LIMIT {batch_size} OFFSET {offset}
                """)
                
                batch = local_cursor.fetchall()
                
                if not batch:
                    break
                
                # Insertar lote en Railway
                insert_query = f"""
                    INSERT INTO {table_name} ({columns_str}) 
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                """
                
                railway_cursor.executemany(insert_query, batch)
                railway_conn.commit()
                
                migrated += len(batch)
                offset += batch_size
                
                # Mostrar progreso
                progress = (migrated / total_records) * 100
                print(f"   📈 Progreso: {migrated:,}/{total_records:,} ({progress:.1f}%)")
                
            except Exception as batch_error:
                print(f"   ⚠️  Error en lote {offset}-{offset+batch_size}: {batch_error}")
                # Continuar con el siguiente lote
                offset += batch_size
                railway_conn.rollback()  # Rollback solo este lote
                continue
        
        print(f"   ✅ Migración completada: {migrated:,} registros")
        return migrated
        
    except Exception as e:
        print(f"   ❌ Error migrando '{table_name}': {e}")
        # Rollback de la transacción completa
        try:
            railway_conn.rollback()
        except:
            pass
        return 0

def reset_sequences(railway_conn, tables):
    """Reinicia las secuencias de ID después de la migración"""
    print("🔄 Reiniciando secuencias de ID...")
    
    try:
        railway_cursor = railway_conn.cursor()
        
        for table in tables:
            try:
                # Obtener el máximo ID actual
                railway_cursor.execute(f"SELECT MAX(id) FROM {table}")
                max_id = railway_cursor.fetchone()[0]
                
                if max_id:
                    # Reiniciar la secuencia
                    railway_cursor.execute(f"SELECT setval('{table}_id_seq', {max_id})")
                    print(f"   ✅ Secuencia '{table}_id_seq' reiniciada a {max_id}")
                
            except Exception as e:
                print(f"   ⚠️  No se pudo reiniciar secuencia para '{table}': {e}")
        
        railway_conn.commit()
        
    except Exception as e:
        print(f"❌ Error reiniciando secuencias: {e}")

def verify_migration(local_conn, railway_conn, tables):
    """Verifica que la migración fue exitosa"""
    print("🔍 Verificando migración...")
    
    try:
        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()
        
        for table in tables:
            try:
                # Contar registros en ambas BDs
                local_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                local_count = local_cursor.fetchone()[0]
                
                railway_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                railway_count = railway_cursor.fetchone()[0]
                
                status = "✅" if local_count == railway_count else "⚠️"
                print(f"   {status} {table}: Local={local_count:,}, Railway={railway_count:,}")
                
            except Exception as e:
                print(f"   ❌ Error verificando '{table}': {e}")
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")

def main():
    """Función principal de migración"""
    print("🚀 === MIGRACIÓN DE DATOS A RAILWAY ===")
    print("Este script copiará todos los datos de tu BD local a Railway")
    print("⚠️  IMPORTANTE: Ejecuta 'python railway_setup.py' PRIMERO")
    print("=" * 60)
    
    # Verificar que DATABASE_URL esté configurada
    if not os.environ.get('DATABASE_URL'):
        print("❌ ERROR: Variable DATABASE_URL no encontrada")
        print("Configúrala con la URL de tu base de datos Railway:")
        print("set DATABASE_URL='postgresql://usuario:password@host:puerto/database'")
        sys.exit(1)
    
    # Confirmar migración
    respuesta = input("\n¿Continuar con la migración? (s/n): ").strip().lower()
    if respuesta != 's':
        print("❌ Migración cancelada")
        sys.exit(0)
    
    try:
        # Conectar a ambas bases de datos
        print("\n🔌 Conectando a bases de datos...")
        local_conn = get_local_connection()
        railway_conn = get_railway_connection()
        print("✅ Conexiones establecidas")
        
        # Orden de migración (respetando foreign keys)
        tables_order = [
            'roles',
            'usuarios', 
            'expediente',
            'ingresos',
            'estados',
            'actuaciones',
            'ingresos_expediente',
            'estados_expediente',
            'expedientes_error'
        ]
        
        print(f"\n📋 Migrando {len(tables_order)} tablas...")
        
        total_migrated = 0
        successful_tables = []
        
        for table in tables_order:
            migrated = migrate_table(table, local_conn, railway_conn)
            total_migrated += migrated
            if migrated > 0:
                successful_tables.append(table)
        
        # Reiniciar secuencias
        if successful_tables:
            reset_sequences(railway_conn, successful_tables)
        
        # Verificar migración
        verify_migration(local_conn, railway_conn, successful_tables)
        
        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN COMPLETADA")
        print("=" * 60)
        print(f"📊 Total de registros migrados: {total_migrated:,}")
        print(f"📋 Tablas migradas: {len(successful_tables)}")
        print("🎉 Tus datos están ahora en Railway!")
        print("=" * 60)
        
        local_conn.close()
        railway_conn.close()
        
    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()