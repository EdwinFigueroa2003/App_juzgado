#!/usr/bin/env python3
"""
Prueba final completa de la funcionalidad subirexpediente
con la estructura actual de la base de datos
"""

import sys
import os
import logging
from datetime import datetime, date

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Agregar el directorio de la aplicación al path
sys.path.append('app_juzgado')

def test_insert_expediente_manual():
    """Prueba inserción manual de expediente con estructura actual"""
    logger.info("=== PRUEBA: Inserción Manual de Expediente ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Verificar estructura actual
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'expediente'
        """)
        
        available_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Columnas disponibles: {available_columns}")
        
        # Datos de prueba
        test_data = {
            'radicado_completo': f'TEST{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'radicado_corto': f'TEST-{datetime.now().strftime("%Y-%m%d")}',
            'demandante': 'JUAN PEREZ PRUEBA',
            'demandado': 'MARIA GARCIA PRUEBA',
            'estado': 'PENDIENTE',
            'responsable': 'ESCRIBIENTE'
        }
        
        # Construir query dinámicamente
        columns_to_insert = []
        values_to_insert = []
        placeholders = []
        
        for col, value in test_data.items():
            if col in available_columns:
                columns_to_insert.append(col)
                placeholders.append('%s')
                values_to_insert.append(value)
        
        # Agregar fecha_ingreso si existe
        if 'fecha_ingreso' in available_columns:
            columns_to_insert.append('fecha_ingreso')
            placeholders.append('%s')
            values_to_insert.append(date.today())
        
        query = f"""
            INSERT INTO expediente 
            ({', '.join(columns_to_insert)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """
        
        logger.info(f"Query: {query}")
        logger.info(f"Valores: {values_to_insert}")
        
        cursor.execute(query, values_to_insert)
        expediente_id = cursor.fetchone()[0]
        
        logger.info(f"✓ Expediente insertado con ID: {expediente_id}")
        
        # Verificar inserción
        cursor.execute("SELECT * FROM expediente WHERE id = %s", (expediente_id,))
        result = cursor.fetchone()
        logger.info(f"✓ Expediente verificado: {result}")
        
        # Limpiar datos de prueba
        cursor.execute("DELETE FROM expediente WHERE id = %s", (expediente_id,))
        conn.commit()
        logger.info("✓ Datos de prueba limpiados")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en prueba de inserción: {str(e)}")
        return False

def test_dynamic_column_detection():
    """Prueba la detección dinámica de columnas"""
    logger.info("=== PRUEBA: Detección Dinámica de Columnas ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Obtener columnas disponibles
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'expediente'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        # Simular datos de formulario
        form_data = {
            'radicado_completo': 'TEST123',
            'radicado_corto': 'TEST-123',
            'demandante': 'JUAN PEREZ',
            'demandado': 'MARIA GARCIA',
            'estado': 'PENDIENTE',
            'ubicacion': 'ARCHIVO CENTRAL',  # Puede no existir
            'tipo_solicitud': 'TUTELA',      # Puede no existir
            'responsable': 'ESCRIBIENTE',
            'observaciones': 'Prueba'        # Puede no existir
        }
        
        available_columns = [col[0] for col in columns]
        
        # Filtrar datos según columnas disponibles
        filtered_data = {}
        for key, value in form_data.items():
            if key in available_columns:
                filtered_data[key] = value
                logger.info(f"✓ {key}: disponible")
            else:
                logger.warning(f"⚠ {key}: no disponible en BD")
        
        logger.info(f"Datos filtrados: {filtered_data}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en detección de columnas: {str(e)}")
        return False

def test_roles_integration():
    """Prueba la integración con la tabla roles"""
    logger.info("=== PRUEBA: Integración con Roles ===")
    
    try:
        from vista.vistasubirexpediente import obtener_roles_activos
        
        roles = obtener_roles_activos()
        
        if roles:
            logger.info(f"✓ Roles obtenidos: {len(roles)}")
            for rol in roles:
                logger.info(f"  - {rol['nombre_rol']} (ID: {rol['id']})")
            return True
        else:
            logger.warning("⚠ No se encontraron roles")
            return False
        
    except Exception as e:
        logger.error(f"✗ Error obteniendo roles: {str(e)}")
        return False

def test_file_validation():
    """Prueba la validación de archivos"""
    logger.info("=== PRUEBA: Validación de Archivos ===")
    
    try:
        from vista.vistasubirexpediente import allowed_file
        
        test_files = [
            ('test.xlsx', True),
            ('test.xls', True),
            ('test.csv', False),
            ('test.txt', False),
            ('archivo.XLSX', True),
            ('archivo.XLS', True),
            ('sin_extension', False)
        ]
        
        all_passed = True
        for filename, expected in test_files:
            result = allowed_file(filename)
            status = "✓" if result == expected else "✗"
            logger.info(f"  {status} {filename}: {result} (esperado: {expected})")
            if result != expected:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        logger.error(f"✗ Error en validación de archivos: {str(e)}")
        return False

def main():
    """Función principal de pruebas"""
    logger.info("=== PRUEBAS FINALES SUBIREXPEDIENTE ===")
    
    tests = [
        ("Detección Dinámica de Columnas", test_dynamic_column_detection),
        ("Integración con Roles", test_roles_integration),
        ("Validación de Archivos", test_file_validation),
        ("Inserción Manual de Expediente", test_insert_expediente_manual)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✓ {test_name}: PASÓ")
            else:
                logger.error(f"✗ {test_name}: FALLÓ")
        except Exception as e:
            logger.error(f"✗ {test_name}: ERROR - {str(e)}")
    
    logger.info(f"\n=== RESUMEN FINAL ===")
    logger.info(f"Pruebas pasadas: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 TODAS LAS PRUEBAS PASARON - SISTEMA LISTO")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)