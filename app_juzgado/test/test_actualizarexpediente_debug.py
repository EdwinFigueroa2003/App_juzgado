#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de actualizarexpediente
con depuración completa
"""

import sys
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Agregar el directorio de la aplicación al path
sys.path.append('app_juzgado')

def test_database_structure():
    """Verifica la estructura actual de la base de datos"""
    logger.info("=== PRUEBA: Estructura de Base de Datos ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
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
        
        # Verificar tablas relacionadas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('ingresos_expediente', 'estados_expediente', 'roles', 'actuaciones')
        """)
        
        tables = cursor.fetchall()
        logger.info(f"Tablas relacionadas encontradas: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error verificando estructura: {str(e)}")
        return False

def test_column_detection():
    """Prueba las funciones de detección de columnas"""
    logger.info("=== PRUEBA: Detección de Columnas ===")
    
    try:
        from vista.vistaactualizarexpediente import (
            _detectar_columnas_disponibles,
            _detectar_columna_tipo,
            _detectar_columna_ubicacion,
            _construir_select_expediente
        )
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Probar detección de columnas disponibles
        available_columns = _detectar_columnas_disponibles(cursor)
        logger.info(f"Columnas disponibles: {available_columns}")
        
        # Probar detección de columna tipo
        tipo_col = _detectar_columna_tipo(cursor)
        logger.info(f"Columna tipo detectada: {tipo_col}")
        
        # Probar detección de columna ubicación
        ubicacion_col = _detectar_columna_ubicacion(cursor)
        logger.info(f"Columna ubicación detectada: {ubicacion_col}")
        
        # Probar construcción de SELECT
        select_clause = _construir_select_expediente(cursor)
        logger.info(f"SELECT construido: {select_clause}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error en detección de columnas: {str(e)}")
        return False

def test_search_functions():
    """Prueba las funciones de búsqueda"""
    logger.info("=== PRUEBA: Funciones de Búsqueda ===")
    
    try:
        from vista.vistaactualizarexpediente import buscar_expediente_por_radicado
        
        # Buscar un expediente que probablemente exista
        # (usando un radicado genérico para prueba)
        test_radicados = [
            "2022-00001",  # Formato corto
            "08001418902020220001",  # Formato largo (ejemplo)
        ]
        
        for radicado in test_radicados:
            logger.info(f"Probando búsqueda con radicado: {radicado}")
            resultado = buscar_expediente_por_radicado(radicado)
            
            if resultado:
                logger.info(f"✓ Expediente encontrado: ID {resultado['id']}")
                logger.info(f"  - Radicado completo: {resultado.get('radicado_completo')}")
                logger.info(f"  - Radicado corto: {resultado.get('radicado_corto')}")
                logger.info(f"  - Estado: {resultado.get('estado_actual')}")
                logger.info(f"  - Responsable: {resultado.get('responsable')}")
                break
            else:
                logger.info(f"  No encontrado: {radicado}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en funciones de búsqueda: {str(e)}")
        return False

def test_roles_integration():
    """Prueba la integración con roles"""
    logger.info("=== PRUEBA: Integración con Roles ===")
    
    try:
        from vista.vistaactualizarexpediente import obtener_roles_activos
        
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
        logger.error(f"Error obteniendo roles: {str(e)}")
        return False

def test_statistics():
    """Prueba la función de estadísticas"""
    logger.info("=== PRUEBA: Estadísticas ===")
    
    try:
        from vista.vistaactualizarexpediente import obtener_estadisticas_expedientes
        
        stats = obtener_estadisticas_expedientes()
        
        logger.info("Estadísticas obtenidas:")
        logger.info(f"  - Total expedientes: {stats.get('total_expedientes', 0)}")
        logger.info(f"  - Sin responsable: {stats.get('sin_responsable', 0)}")
        logger.info(f"  - Escribientes: {stats.get('escribientes', 0)}")
        logger.info(f"  - Sustanciadores: {stats.get('sustanciadores', 0)}")
        
        estados_comunes = stats.get('estados_comunes', [])
        if estados_comunes:
            logger.info("Estados más comunes:")
            for estado, cantidad in estados_comunes[:5]:  # Top 5
                logger.info(f"    - {estado}: {cantidad}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return False

def main():
    """Función principal de pruebas"""
    logger.info("=== PRUEBAS ACTUALIZAREXPEDIENTE ===")
    
    tests = [
        ("Estructura de Base de Datos", test_database_structure),
        ("Detección de Columnas", test_column_detection),
        ("Integración con Roles", test_roles_integration),
        ("Estadísticas", test_statistics),
        ("Funciones de Búsqueda", test_search_functions)
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
    
    logger.info(f"\n=== RESUMEN ===")
    logger.info(f"Pruebas pasadas: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 TODAS LAS PRUEBAS PASARON")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)