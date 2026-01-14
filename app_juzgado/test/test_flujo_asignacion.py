#!/usr/bin/env python3
"""
Script para probar el flujo completo de asignación
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

def test_flujo_completo():
    """Prueba el flujo completo: buscar -> asignar -> recargar"""
    logger.info("=== PRUEBA: Flujo Completo de Asignación ===")
    
    try:
        from modelo.configBd import obtener_conexion
        from vista.vistaactualizarexpediente import buscar_expediente_por_id
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # 1. Obtener un expediente de prueba
        cursor.execute("""
            SELECT id, radicado_completo, radicado_corto, responsable
            FROM expediente
            LIMIT 1
        """)
        
        expediente_db = cursor.fetchone()
        
        if not expediente_db:
            logger.error("No hay expedientes en la base de datos")
            return False
        
        exp_id, radicado_completo, radicado_corto, responsable_original = expediente_db
        
        logger.info(f"\n1️⃣ EXPEDIENTE INICIAL:")
        logger.info(f"   ID: {exp_id}")
        logger.info(f"   Radicado: {radicado_completo or radicado_corto}")
        logger.info(f"   Responsable: {responsable_original or 'Sin asignar'}")
        
        # 2. Buscar usando la función (simula GET con buscar_id)
        logger.info(f"\n2️⃣ BUSCANDO EXPEDIENTE CON buscar_expediente_por_id({exp_id})...")
        expediente = buscar_expediente_por_id(exp_id)
        
        if not expediente:
            logger.error("No se pudo buscar el expediente")
            return False
        
        logger.info(f"   Responsable en dict: {expediente.get('responsable', 'KEY NO EXISTE')}")
        
        # 3. Asignar una persona (simula POST de asignación)
        nombre_prueba = "María González Test"
        logger.info(f"\n3️⃣ ASIGNANDO A: {nombre_prueba}")
        
        cursor.execute("""
            UPDATE expediente 
            SET responsable = %s
            WHERE id = %s
        """, (nombre_prueba, exp_id))
        
        conn.commit()
        logger.info(f"   ✓ UPDATE ejecutado ({cursor.rowcount} fila afectada)")
        
        # 4. Verificar en BD directamente
        cursor.execute("SELECT responsable FROM expediente WHERE id = %s", (exp_id,))
        responsable_bd = cursor.fetchone()[0]
        logger.info(f"\n4️⃣ VERIFICACIÓN EN BD:")
        logger.info(f"   Responsable en BD: {responsable_bd}")
        
        # 5. Recargar expediente (simula redirect con buscar_id)
        logger.info(f"\n5️⃣ RECARGANDO EXPEDIENTE CON buscar_expediente_por_id({exp_id})...")
        expediente_recargado = buscar_expediente_por_id(exp_id)
        
        if not expediente_recargado:
            logger.error("No se pudo recargar el expediente")
            return False
        
        responsable_recargado = expediente_recargado.get('responsable')
        logger.info(f"   Responsable en dict recargado: {responsable_recargado}")
        
        # 6. Verificar que coincide
        logger.info(f"\n6️⃣ VERIFICACIÓN FINAL:")
        if responsable_recargado == nombre_prueba:
            logger.info(f"   ✅ ÉXITO: El responsable se muestra correctamente")
            logger.info(f"   ✅ BD: {responsable_bd}")
            logger.info(f"   ✅ Dict: {responsable_recargado}")
            exito = True
        else:
            logger.error(f"   ❌ ERROR: El responsable NO coincide")
            logger.error(f"   BD: {responsable_bd}")
            logger.error(f"   Dict: {responsable_recargado}")
            exito = False
        
        # 7. Restaurar valor original
        cursor.execute("""
            UPDATE expediente 
            SET responsable = %s
            WHERE id = %s
        """, (responsable_original, exp_id))
        conn.commit()
        logger.info(f"\n7️⃣ Responsable restaurado a: {responsable_original or 'Sin asignar'}")
        
        cursor.close()
        conn.close()
        
        return exito
        
    except Exception as e:
        logger.error(f"✗ Error en prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    logger.info("🚀 === PRUEBA FLUJO COMPLETO DE ASIGNACIÓN ===\n")
    
    resultado = test_flujo_completo()
    
    if resultado:
        logger.info("\n🎉 FLUJO COMPLETO FUNCIONA CORRECTAMENTE")
        logger.info("✅ La asignación se guarda y se muestra correctamente")
    else:
        logger.warning("\n⚠️ HAY UN PROBLEMA EN EL FLUJO")
    
    return resultado

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
