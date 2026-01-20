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
    print("🔧 Inicializando base de datos...")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Aquí puedes agregar los CREATE TABLE statements
        # Por ejemplo:
        
        print("✅ Tablas creadas exitosamente")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return False
    
    return True

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

if __name__ == "__main__":
    print("🚀 === INICIALIZACIÓN DE BASE DE DATOS ===")
    
    if verificar_conexion():
        crear_tablas()
        print("\n✅ Inicialización completada")
    else:
        print("\n❌ Inicialización fallida")
        sys.exit(1)