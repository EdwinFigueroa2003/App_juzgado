#!/usr/bin/env python3
"""
Script para probar la funcionalidad de asignación a persona específica
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

def test_asignacion_persona_especifica():
    """Prueba la asignación de expediente a persona específica"""
    logger.info("=== PRUEBA: Asignación a Persona Específica ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # 1. Buscar un expediente de prueba
        cursor.execute("""
            SELECT id, radicado_completo, radicado_corto, responsable
            FROM expediente
            LIMIT 1
        """)
        
        expediente = cursor.fetchone()
        
        if not expediente:
            logger.error("No se encontró ningún expediente para probar")
            return False
        
        exp_id, radicado_completo, radicado_corto, responsable_actual = expediente
        
        logger.info(f"Expediente de prueba:")
        logger.info(f"  - ID: {exp_id}")
        logger.info(f"  - Radicado: {radicado_completo or radicado_corto}")
        logger.info(f"  - Responsable actual: {responsable_actual or 'Sin asignar'}")
        
        # 2. Asignar a una persona específica
        nombre_persona = "Juan Pérez García"
        logger.info(f"\nAsignando expediente a: {nombre_persona}")
        
        cursor.execute("""
            UPDATE expediente
            SET responsable = %s
            WHERE id = %s
        """, (nombre_persona, exp_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"✓ Expediente asignado exitosamente")
            
            # 3. Verificar la asignación
            cursor.execute("""
                SELECT responsable
                FROM expediente
                WHERE id = %s
            """, (exp_id,))
            
            nuevo_responsable = cursor.fetchone()[0]
            
            if nuevo_responsable == nombre_persona:
                logger.info(f"✓ Verificación exitosa: Responsable = '{nuevo_responsable}'")
                
                # 4. Probar con otro nombre
                nombre_persona_2 = "María García López"
                logger.info(f"\nCambiando asignación a: {nombre_persona_2}")
                
                cursor.execute("""
                    UPDATE expediente
                    SET responsable = %s
                    WHERE id = %s
                """, (nombre_persona_2, exp_id))
                
                conn.commit()
                
                cursor.execute("""
                    SELECT responsable
                    FROM expediente
                    WHERE id = %s
                """, (exp_id,))
                
                nuevo_responsable_2 = cursor.fetchone()[0]
                
                if nuevo_responsable_2 == nombre_persona_2:
                    logger.info(f"✓ Segunda asignación exitosa: Responsable = '{nuevo_responsable_2}'")
                    
                    # 5. Restaurar responsable original (si existía)
                    if responsable_actual:
                        logger.info(f"\nRestaurando responsable original: {responsable_actual}")
                        cursor.execute("""
                            UPDATE expediente
                            SET responsable = %s
                            WHERE id = %s
                        """, (responsable_actual, exp_id))
                        conn.commit()
                        logger.info("✓ Responsable original restaurado")
                    else:
                        logger.info("\nDejando el nuevo responsable asignado (no había responsable anterior)")
                    
                    cursor.close()
                    conn.close()
                    
                    logger.info("\n🎉 TODAS LAS PRUEBAS PASARON")
                    return True
                else:
                    logger.error(f"✗ Error: Responsable esperado '{nombre_persona_2}', obtenido '{nuevo_responsable_2}'")
                    return False
            else:
                logger.error(f"✗ Error: Responsable esperado '{nombre_persona}', obtenido '{nuevo_responsable}'")
                return False
        else:
            logger.error("✗ No se pudo actualizar el expediente")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error en prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_casos_especiales():
    """Prueba casos especiales de asignación"""
    logger.info("\n=== PRUEBA: Casos Especiales ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Buscar expediente de prueba
        cursor.execute("SELECT id FROM expediente LIMIT 1")
        exp_id = cursor.fetchone()[0]
        
        casos_prueba = [
            ("Carlos Rodríguez", "Nombre simple"),
            ("Ana María Fernández García", "Nombre compuesto"),
            ("Dr. Pedro Sánchez", "Con título"),
            ("Ing. Laura Martínez PhD", "Con título y grado"),
            ("José Luis O'Connor", "Con apóstrofe"),
            ("María José Pérez-González", "Con guión")
        ]
        
        logger.info(f"Probando {len(casos_prueba)} casos especiales...")
        
        for nombre, descripcion in casos_prueba:
            cursor.execute("""
                UPDATE expediente
                SET responsable = %s
                WHERE id = %s
            """, (nombre, exp_id))
            
            conn.commit()
            
            cursor.execute("""
                SELECT responsable
                FROM expediente
                WHERE id = %s
            """, (exp_id,))
            
            responsable_guardado = cursor.fetchone()[0]
            
            if responsable_guardado == nombre:
                logger.info(f"✓ {descripcion}: '{nombre}' - OK")
            else:
                logger.error(f"✗ {descripcion}: Esperado '{nombre}', obtenido '{responsable_guardado}'")
                return False
        
        cursor.close()
        conn.close()
        
        logger.info("🎉 TODOS LOS CASOS ESPECIALES PASARON")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en casos especiales: {str(e)}")
        return False

def main():
    """Función principal"""
    logger.info("🚀 === PRUEBA ASIGNACIÓN A PERSONA ESPECÍFICA ===\n")
    
    pruebas = [
        ("Asignación Básica", test_asignacion_persona_especifica),
        ("Casos Especiales", test_casos_especiales)
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
        logger.info("\n🎉 TODAS LAS PRUEBAS PASARON - FUNCIONALIDAD LISTA")
        return True
    else:
        logger.warning(f"\n⚠️ {total - pasadas} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)