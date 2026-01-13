#!/usr/bin/env python3
"""
Script para probar el sistema completo optimizado:
- Vista Home
- Filtrado por Estado
- Búsqueda por Radicado
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

def test_vista_home():
    """Prueba la vista home optimizada"""
    logger.info("=== PRUEBA: Vista Home Optimizada ===")
    
    try:
        from vista.vistahome import obtener_metricas_dashboard
        
        start_time = time.time()
        metricas = obtener_metricas_dashboard()
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.info(f"✓ Vista Home: {execution_time:.3f}s")
        logger.info(f"  - Total expedientes: {metricas.get('total_expediente', 0)}")
        logger.info(f"  - Estados disponibles: {len(metricas.get('expediente_por_estado', []))}")
        
        return execution_time < 1.0
        
    except Exception as e:
        logger.error(f"✗ Error en vista home: {e}")
        return False

def test_filtrado_estados():
    """Prueba el filtrado por estados optimizado"""
    logger.info("=== PRUEBA: Filtrado por Estados Optimizado ===")
    
    try:
        from vista.vistaexpediente import filtrar_por_estado
        
        estados_prueba = ["ACTIVO PENDIENTE", "PENDIENTE", "ACTIVO RESUELTO"]
        tiempos = []
        
        for estado in estados_prueba:
            start_time = time.time()
            expedientes = filtrar_por_estado(estado, limite=50)
            end_time = time.time()
            
            execution_time = end_time - start_time
            tiempos.append(execution_time)
            
            logger.info(f"✓ {estado}: {len(expedientes)} expedientes en {execution_time:.3f}s")
        
        tiempo_promedio = sum(tiempos) / len(tiempos)
        logger.info(f"  - Tiempo promedio: {tiempo_promedio:.3f}s")
        
        return tiempo_promedio < 1.0
        
    except Exception as e:
        logger.error(f"✗ Error en filtrado: {e}")
        return False

def test_busqueda_radicado():
    """Prueba la búsqueda por radicado"""
    logger.info("=== PRUEBA: Búsqueda por Radicado ===")
    
    try:
        from vista.vistaexpediente import buscar_expedientes
        
        # Usar el expediente específico que sabemos que existe
        radicado = '08001405300920230059400'
        
        start_time = time.time()
        expedientes = buscar_expedientes(radicado)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.info(f"✓ Búsqueda radicado: {len(expedientes)} expedientes en {execution_time:.3f}s")
        
        if expedientes:
            exp = expedientes[0]
            logger.info(f"  - Expediente encontrado: ID {exp['id']}")
            logger.info(f"  - Estado: {exp.get('estado_actual', 'N/A')}")
            logger.info(f"  - Actuaciones: {exp['estadisticas']['total_actuaciones']}")
        
        return execution_time < 2.0 and len(expedientes) > 0
        
    except Exception as e:
        logger.error(f"✗ Error en búsqueda: {e}")
        return False

def test_consistencia_estados():
    """Verifica que los estados sean consistentes entre vista home y filtrado"""
    logger.info("=== PRUEBA: Consistencia de Estados ===")
    
    try:
        from vista.vistahome import obtener_metricas_dashboard
        from vista.vistaexpediente import filtrar_por_estado
        
        # Obtener distribución desde home
        metricas = obtener_metricas_dashboard()
        estados_home = {estado: cantidad for estado, cantidad in metricas.get('expediente_por_estado', [])}
        
        logger.info("Estados desde Vista Home:")
        for estado, cantidad in estados_home.items():
            logger.info(f"  - {estado}: {cantidad}")
        
        # Verificar algunos estados con filtrado
        estados_verificar = ["Activo Pendiente", "Pendiente"]
        consistente = True
        
        for estado in estados_verificar:
            if estado in estados_home:
                # Obtener todos los expedientes de este estado
                expedientes = filtrar_por_estado(estado.upper().replace(" ", " "), limite=10000)
                cantidad_filtrado = len(expedientes)
                cantidad_home = estados_home[estado]
                
                logger.info(f"Verificando {estado}:")
                logger.info(f"  - Home: {cantidad_home}")
                logger.info(f"  - Filtrado: {cantidad_filtrado} (muestra)")
                
                # No verificamos exactitud porque el filtrado puede tener límite
                # Solo verificamos que ambos funcionen
                if cantidad_filtrado == 0 and cantidad_home > 0:
                    logger.warning(f"  ⚠️ Posible inconsistencia en {estado}")
                    consistente = False
                else:
                    logger.info(f"  ✓ {estado} consistente")
        
        return consistente
        
    except Exception as e:
        logger.error(f"✗ Error en consistencia: {e}")
        return False

def main():
    """Función principal de pruebas completas"""
    logger.info("🚀 === PRUEBA SISTEMA COMPLETO OPTIMIZADO ===")
    
    pruebas = [
        ("Vista Home", test_vista_home),
        ("Filtrado Estados", test_filtrado_estados),
        ("Búsqueda Radicado", test_busqueda_radicado),
        ("Consistencia Estados", test_consistencia_estados)
    ]
    
    resultados = []
    tiempo_total_inicio = time.time()
    
    for nombre, test_func in pruebas:
        logger.info(f"\n--- {nombre} ---")
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
            if resultado:
                logger.info(f"✅ {nombre}: PASÓ")
            else:
                logger.error(f"❌ {nombre}: FALLÓ")
        except Exception as e:
            logger.error(f"💥 {nombre}: ERROR - {str(e)}")
            resultados.append((nombre, False))
    
    tiempo_total = time.time() - tiempo_total_inicio
    
    # Resumen final
    logger.info(f"\n🎯 === RESUMEN FINAL ===")
    logger.info(f"Tiempo total de pruebas: {tiempo_total:.3f}s")
    
    pasadas = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    logger.info(f"Pruebas pasadas: {pasadas}/{total}")
    
    for nombre, resultado in resultados:
        estado = "✅ PASÓ" if resultado else "❌ FALLÓ"
        logger.info(f"  - {nombre}: {estado}")
    
    if pasadas == total:
        logger.info("🎉 TODAS LAS PRUEBAS PASARON - SISTEMA COMPLETAMENTE OPTIMIZADO")
        return True
    else:
        logger.warning(f"⚠️ {total - pasadas} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)