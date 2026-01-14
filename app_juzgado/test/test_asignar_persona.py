#!/usr/bin/env python3
"""
Script para probar la asignación de persona específica
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

def test_asignacion_persona():
    """Prueba asignar una persona a un expediente"""
    logger.info("=== PRUEBA: Asignación de Persona ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # 1. Obtener un expediente de prueba
        cursor.execute("""
            SELECT id, radicado_completo, radicado_corto, responsable
            FROM expediente
            LIMIT 1
        """)
        
        expediente = cursor.fetchone()
        
        if not expediente:
            logger.error("No hay expedientes en la base de datos")
            return False
        
        exp_id, radicado_completo, radicado_corto, responsable_actual = expediente
        
        logger.info(f"Expediente de prueba:")
        logger.info(f"  ID: {exp_id}")
        logger.info(f"  Radicado: {radicado_completo or radicado_corto}")
        logger.info(f"  Responsable actual: {responsable_actual or 'Sin asignar'}")
        
        # 2. Asignar una persona de prueba
        nombre_prueba = "Juan Pérez Test"
        
        logger.info(f"\nAsignando a: {nombre_prueba}")
        
        cursor.execute("""
            UPDATE expediente 
            SET responsable = %s
            WHERE id = %s
        """, (nombre_prueba, exp_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"✓ UPDATE ejecutado correctamente ({cursor.rowcount} fila afectada)")
        else:
            logger.error("✗ No se actualizó ninguna fila")
            return False
        
        # 3. Verificar que se guardó
        cursor.execute("""
            SELECT responsable
            FROM expediente
            WHERE id = %s
        """, (exp_id,))
        
        resultado = cursor.fetchone()
        
        if resultado:
            responsable_nuevo = resultado[0]
            logger.info(f"\nResponsable después de UPDATE: {responsable_nuevo}")
            
            if responsable_nuevo == nombre_prueba:
                logger.info("✅ ÉXITO: La asignación se guardó correctamente")
                
                # 4. Restaurar el valor original
                cursor.execute("""
                    UPDATE expediente 
                    SET responsable = %s
                    WHERE id = %s
                """, (responsable_actual, exp_id))
                conn.commit()
                logger.info(f"Responsable restaurado a: {responsable_actual or 'Sin asignar'}")
                
                cursor.close()
                conn.close()
                return True
            else:
                logger.error(f"❌ ERROR: Se esperaba '{nombre_prueba}' pero se obtuvo '{responsable_nuevo}'")
                cursor.close()
                conn.close()
                return False
        else:
            logger.error("❌ ERROR: No se pudo leer el expediente después del UPDATE")
            cursor.close()
            conn.close()
            return False
        
    except Exception as e:
        logger.error(f"✗ Error en prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_buscar_expediente_por_id():
    """Prueba la función buscar_expediente_por_id"""
    logger.info("\n=== PRUEBA: buscar_expediente_por_id ===")
    
    try:
        sys.path.append('app_juzgado')
        from vista.vistaactualizarexpediente import buscar_expediente_por_id
        from modelo.configBd import obtener_conexion
        
        # Obtener un ID de expediente
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM expediente LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            logger.error("No hay expedientes")
            return False
        
        exp_id = result[0]
        cursor.close()
        conn.close()
        
        logger.info(f"Buscando expediente ID: {exp_id}")
        
        # Buscar usando la función
        expediente = buscar_expediente_por_id(exp_id)
        
        if expediente:
            logger.info(f"✓ Expediente encontrado:")
            logger.info(f"  ID: {expediente['id']}")
            logger.info(f"  Radicado: {expediente.get('radicado_completo') or expediente.get('radicado_corto')}")
            logger.info(f"  Responsable: {expediente.get('responsable', 'Sin asignar')}")
            logger.info("✅ ÉXITO: La función buscar_expediente_por_id funciona")
            return True
        else:
            logger.error("❌ ERROR: No se encontró el expediente")
            return False
        
    except Exception as e:
        logger.error(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    logger.info("🚀 === PRUEBA ASIGNACIÓN DE PERSONA ===\n")
    
    pruebas = [
        ("Asignación de Persona", test_asignacion_persona),
        ("Buscar Expediente por ID", test_buscar_expediente_por_id)
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
        logger.info("\n🎉 TODAS LAS PRUEBAS PASARON")
        return True
    else:
        logger.warning(f"\n⚠️ {total - pasadas} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
