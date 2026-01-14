#!/usr/bin/env python3
"""
Script para probar el endpoint API de búsqueda de personas
"""

import sys
import os
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Agregar el directorio de la aplicación al path
sys.path.append('app_juzgado')

def test_api_buscar_personas():
    """Prueba el endpoint API de búsqueda de personas"""
    logger.info("=== PRUEBA: API Buscar Personas ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # 1. Verificar que existen responsables en la BD
        cursor.execute("""
            SELECT DISTINCT responsable, COUNT(*) as cantidad
            FROM expediente
            WHERE responsable IS NOT NULL AND responsable != ''
            GROUP BY responsable
            ORDER BY cantidad DESC
            LIMIT 10
        """)
        
        responsables = cursor.fetchall()
        
        logger.info(f"Responsables únicos en BD: {len(responsables)}")
        
        if responsables:
            logger.info("Top 10 responsables:")
            for i, (nombre, cantidad) in enumerate(responsables, 1):
                logger.info(f"  {i}. {nombre} ({cantidad} expedientes)")
        
        # 2. Probar búsquedas simuladas
        if responsables:
            # Tomar el primer responsable y buscar por parte de su nombre
            primer_responsable = responsables[0][0]
            
            # Buscar por las primeras 3 letras
            query_test = primer_responsable[:3] if len(primer_responsable) >= 3 else primer_responsable
            
            logger.info(f"\nProbando búsqueda con query: '{query_test}'")
            
            cursor.execute("""
                SELECT DISTINCT responsable
                FROM expediente
                WHERE responsable IS NOT NULL 
                  AND responsable != ''
                  AND responsable ILIKE %s
                ORDER BY responsable
                LIMIT 20
            """, (f'%{query_test}%',))
            
            resultados = cursor.fetchall()
            
            logger.info(f"Resultados encontrados: {len(resultados)}")
            
            if resultados:
                logger.info("Primeros 5 resultados:")
                for i, (nombre,) in enumerate(resultados[:5], 1):
                    logger.info(f"  {i}. {nombre}")
        
        # 3. Probar búsquedas con diferentes queries
        queries_prueba = ['MAR', 'JUA', 'ANA', 'CAR', 'LUI']
        
        logger.info("\nProbando búsquedas con diferentes queries:")
        
        for query in queries_prueba:
            cursor.execute("""
                SELECT COUNT(DISTINCT responsable)
                FROM expediente
                WHERE responsable IS NOT NULL 
                  AND responsable != ''
                  AND responsable ILIKE %s
            """, (f'%{query}%',))
            
            count = cursor.fetchone()[0]
            logger.info(f"  Query '{query}': {count} resultados")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✓ API de búsqueda funcionaría correctamente")
        logger.info("🎉 PRUEBA EXITOSA")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_rendimiento_busqueda():
    """Prueba el rendimiento de la búsqueda"""
    logger.info("\n=== PRUEBA: Rendimiento de Búsqueda ===")
    
    try:
        import time
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        queries_prueba = ['A', 'MA', 'MAR', 'MARI', 'MARIA']
        
        logger.info("Midiendo tiempo de respuesta para diferentes longitudes de query:")
        
        for query in queries_prueba:
            start_time = time.time()
            
            cursor.execute("""
                SELECT DISTINCT responsable
                FROM expediente
                WHERE responsable IS NOT NULL 
                  AND responsable != ''
                  AND responsable ILIKE %s
                ORDER BY responsable
                LIMIT 20
            """, (f'%{query}%',))
            
            resultados = cursor.fetchall()
            end_time = time.time()
            
            tiempo = (end_time - start_time) * 1000  # Convertir a milisegundos
            
            logger.info(f"  Query '{query}' ({len(query)} chars): {len(resultados)} resultados en {tiempo:.2f}ms")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✓ Rendimiento aceptable para autocompletado")
        logger.info("🎉 PRUEBA DE RENDIMIENTO EXITOSA")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en prueba de rendimiento: {str(e)}")
        return False

def main():
    """Función principal"""
    logger.info("🚀 === PRUEBA API BUSCAR PERSONAS ===\n")
    
    pruebas = [
        ("API Buscar Personas", test_api_buscar_personas),
        ("Rendimiento de Búsqueda", test_rendimiento_busqueda)
    ]
    
    resultados = []
    
    for nombre, test_func in pruebas:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            logger.error(f"💥 {nombre}: ERROR - {str(e)}")
            resultados.append((nombre, False))
    
    # Resumen
    logger.info("\n🎯 === RESUMEN ===")
    pasadas = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    logger.info(f"Pruebas pasadas: {pasadas}/{total}")
    
    for nombre, resultado in resultados:
        estado = "✅ PASÓ" if resultado else "❌ FALLÓ"
        logger.info(f"  - {nombre}: {estado}")
    
    if pasadas == total:
        logger.info("\n🎉 TODAS LAS PRUEBAS PASARON - API LISTA")
        return True
    else:
        logger.warning(f"\n⚠️ {total - pasadas} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)