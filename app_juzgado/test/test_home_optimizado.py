#!/usr/bin/env python3
"""
Script para probar el rendimiento de la vista home OPTIMIZADA con campo estado
"""

import sys
import os
import time
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Agregar el directorio de la aplicación al path
sys.path.append('app_juzgado')

def test_home_optimizado():
    """Prueba el rendimiento de la vista home OPTIMIZADA"""
    logger.info("=== PRUEBA: Vista Home ULTRA OPTIMIZADA ===")
    
    try:
        from vista.vistahome import obtener_metricas_dashboard
        
        # Medir tiempo de ejecución
        start_time = time.time()
        
        logger.info("Obteniendo métricas del dashboard OPTIMIZADO...")
        metricas = obtener_metricas_dashboard()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(f"✓ Métricas obtenidas en {execution_time:.3f} segundos")
        
        # Mostrar métricas obtenidas
        logger.info("Métricas obtenidas:")
        logger.info(f"  - Total expedientes: {metricas.get('total_expediente', 0)}")
        logger.info(f"  - Total actuaciones: {metricas.get('total_actuaciones', 0)}")
        logger.info(f"  - Total ingresos: {metricas.get('total_ingresos', 0)}")
        logger.info(f"  - Total estados: {metricas.get('total_estados', 0)}")
        
        # Mostrar distribución por estado OPTIMIZADA
        estados_dist = metricas.get('expediente_por_estado', [])
        if estados_dist:
            logger.info("  - Distribución por estado (DIRECTO desde campo estado):")
            for estado, cantidad in estados_dist:
                logger.info(f"    * {estado}: {cantidad}")
        
        # Mostrar expedientes recientes
        recientes = metricas.get('expediente_recientes', [])
        logger.info(f"  - Expedientes recientes: {len(recientes)}")
        if recientes:
            logger.info("  - Primeros 3 expedientes recientes:")
            for i, exp in enumerate(recientes[:3], 1):
                logger.info(f"    {i}. ID: {exp[0]}, Radicado: {exp[1] or exp[2]}, Estado: {exp[7] if len(exp) > 7 else 'N/A'}")
        
        # Evaluar rendimiento
        if execution_time < 0.1:
            logger.info(f"🚀 ULTRA RÁPIDO: Tiempo de carga {execution_time:.3f}s (< 0.1s)")
            return True
        elif execution_time < 0.5:
            logger.info(f"⚡ EXCELENTE: Tiempo de carga {execution_time:.3f}s (< 0.5s)")
            return True
        elif execution_time < 1.0:
            logger.info(f"✅ BUENO: Tiempo de carga {execution_time:.3f}s (< 1s)")
            return True
        else:
            logger.warning(f"⚠️ LENTO: Tiempo de carga {execution_time:.3f}s (> 1s)")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error en prueba de rendimiento: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    logger.info("=== PRUEBA VISTA HOME ULTRA OPTIMIZADA ===")
    
    success = test_home_optimizado()
    
    if success:
        logger.info("🎉 PRUEBA DE RENDIMIENTO EXITOSA")
        return True
    else:
        logger.warning("⚠️ PRUEBA DE RENDIMIENTO FALLÓ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)