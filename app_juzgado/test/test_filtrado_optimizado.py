#!/usr/bin/env python3
"""
Script para probar el rendimiento del filtrado por estado OPTIMIZADO
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

def test_filtrado_por_estado():
    """Prueba el rendimiento del filtrado por estado OPTIMIZADO"""
    logger.info("=== PRUEBA: Filtrado por Estado ULTRA OPTIMIZADO ===")
    
    try:
        from vista.vistaexpediente import filtrar_por_estado
        
        # Estados a probar
        estados_prueba = [
            "ACTIVO PENDIENTE",
            "ACTIVO RESUELTO", 
            "INACTIVO RESUELTO",
            "PENDIENTE",
            "ACTIVO"
        ]
        
        resultados = {}
        
        for estado in estados_prueba:
            logger.info(f"\n--- Probando filtro: {estado} ---")
            
            # Medir tiempo de ejecución
            start_time = time.time()
            
            expedientes = filtrar_por_estado(estado, limite=100)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            resultados[estado] = {
                'tiempo': execution_time,
                'cantidad': len(expedientes),
                'expedientes': expedientes[:3]  # Primeros 3 para verificar
            }
            
            logger.info(f"✓ {estado}: {len(expedientes)} expedientes en {execution_time:.3f}s")
            
            # Mostrar algunos expedientes de muestra
            if expedientes:
                logger.info("  Primeros 3 expedientes:")
                for i, exp in enumerate(expedientes[:3], 1):
                    logger.info(f"    {i}. ID: {exp['id']}, Radicado: {exp['radicado_completo'] or exp['radicado_corto']}")
                    logger.info(f"       Estado: {exp['estado_actual']}, Actuaciones: {exp['estadisticas']['total_actuaciones']}")
        
        # Resumen de rendimiento
        logger.info(f"\n=== RESUMEN DE RENDIMIENTO ===")
        tiempo_total = sum(r['tiempo'] for r in resultados.values())
        expedientes_total = sum(r['cantidad'] for r in resultados.values())
        
        logger.info(f"Tiempo total: {tiempo_total:.3f}s")
        logger.info(f"Expedientes procesados: {expedientes_total}")
        logger.info(f"Promedio por filtro: {tiempo_total/len(estados_prueba):.3f}s")
        
        for estado, datos in resultados.items():
            logger.info(f"  {estado}: {datos['cantidad']} expedientes en {datos['tiempo']:.3f}s")
        
        # Evaluar rendimiento general
        tiempo_promedio = tiempo_total / len(estados_prueba)
        if tiempo_promedio < 0.5:
            logger.info(f"🚀 ULTRA RÁPIDO: Promedio {tiempo_promedio:.3f}s por filtro")
            return True
        elif tiempo_promedio < 1.0:
            logger.info(f"⚡ EXCELENTE: Promedio {tiempo_promedio:.3f}s por filtro")
            return True
        elif tiempo_promedio < 2.0:
            logger.info(f"✅ BUENO: Promedio {tiempo_promedio:.3f}s por filtro")
            return True
        else:
            logger.warning(f"⚠️ LENTO: Promedio {tiempo_promedio:.3f}s por filtro")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error en prueba de filtrado: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    logger.info("=== PRUEBA FILTRADO ULTRA OPTIMIZADO ===")
    
    success = test_filtrado_por_estado()
    
    if success:
        logger.info("🎉 PRUEBA DE FILTRADO EXITOSA")
        return True
    else:
        logger.warning("⚠️ PRUEBA DE FILTRADO FALLÓ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)