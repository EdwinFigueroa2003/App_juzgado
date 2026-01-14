#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de subirexpediente
con depuración completa
"""

import sys
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/test_subirexpediente_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Agregar el directorio de la aplicación al path
sys.path.append('app_juzgado')

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    logger.info("=== PRUEBA: Conexión a Base de Datos ===")
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        logger.info("✓ Conexión establecida correctamente")
        
        cursor = conn.cursor()
        
        # Verificar que existe la tabla expediente
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('expediente', 'roles', 'ingresos_expediente', 'estados_expediente')
        """)
        
        tables = cursor.fetchall()
        logger.info(f"Tablas encontradas: {[t[0] for t in tables]}")
        
        # Verificar estructura de tabla expediente
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'expediente'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        logger.info("Estructura de tabla 'expediente':")
        for col in columns:
            logger.info(f"  - {col[0]} ({col[1]}) - Nullable: {col[2]}")
        
        cursor.close()
        conn.close()
        logger.info("✓ Conexión cerrada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en conexión BD: {str(e)}")
        return False

def test_roles_function():
    """Prueba la función obtener_roles_activos"""
    logger.info("=== PRUEBA: Función obtener_roles_activos ===")
    try:
        from vista.vistasubirexpediente import obtener_roles_activos
        
        roles = obtener_roles_activos()
        logger.info(f"✓ Roles obtenidos: {len(roles)}")
        
        for rol in roles:
            logger.info(f"  - ID: {rol['id']}, Nombre: {rol['nombre_rol']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error obteniendo roles: {str(e)}")
        return False

def test_allowed_file_function():
    """Prueba la función allowed_file"""
    logger.info("=== PRUEBA: Función allowed_file ===")
    try:
        from vista.vistasubirexpediente import allowed_file
        
        test_files = [
            'test.xlsx',
            'test.xls', 
            'test.csv',
            'test.txt',
            'archivo.XLSX',
            'archivo.XLS'
        ]
        
        for filename in test_files:
            result = allowed_file(filename)
            status = "✓" if result else "✗"
            logger.info(f"  {status} {filename}: {result}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en allowed_file: {str(e)}")
        return False

def test_form_data_simulation():
    """Simula datos de formulario para pruebas"""
    logger.info("=== PRUEBA: Simulación de datos de formulario ===")
    
    test_data = {
        'radicado_completo': '08001418902020220003100',
        'radicado_corto': '2022-00031',
        'demandante': 'JUAN PEREZ',
        'demandado': 'MARIA GARCIA',
        'estado_actual': 'PENDIENTE',
        'ubicacion': 'ARCHIVO CENTRAL',
        'tipo_solicitud': 'TUTELA',
        'juzgado_origen': 'JUZGADO 1 CIVIL',
        'responsable': 'ESCRIBIENTE',
        'observaciones': 'Expediente de prueba',
        'fecha_ingreso': '2024-01-15',
        'motivo_ingreso': 'Ingreso por prueba',
        'observaciones_ingreso': 'Observaciones de prueba'
    }
    
    logger.info("Datos de prueba preparados:")
    for key, value in test_data.items():
        logger.info(f"  - {key}: '{value}'")
    
    return test_data

def main():
    """Función principal de pruebas"""
    logger.info("=== INICIO DE PRUEBAS SUBIREXPEDIENTE ===")
    
    # Crear directorio de logs si no existe
    os.makedirs('logs', exist_ok=True)
    
    tests_passed = 0
    total_tests = 4
    
    # Prueba 1: Conexión BD
    if test_database_connection():
        tests_passed += 1
    
    # Prueba 2: Función de roles
    if test_roles_function():
        tests_passed += 1
    
    # Prueba 3: Función allowed_file
    if test_allowed_file_function():
        tests_passed += 1
    
    # Prueba 4: Simulación de datos
    if test_form_data_simulation():
        tests_passed += 1
    
    logger.info("=== RESUMEN DE PRUEBAS ===")
    logger.info(f"Pruebas pasadas: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        logger.info("✓ TODAS LAS PRUEBAS PASARON")
        return True
    else:
        logger.warning(f"✗ {total_tests - tests_passed} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)