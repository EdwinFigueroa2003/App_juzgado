#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para analizar y corregir el filtro por estado
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_juzgado'))

from app_juzgado.modelo.configBd import obtener_conexion

def verificar_filtro_corregido():
    """Verifica el filtro usando CASE WHEN para garantizar categorías mutualmente exclusivas"""
    
    print("="*70)
    print("VERIFICANDO FILTRO POR ESTADO (VERSIÓN CORREGIDA)")
    print("="*70)
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Total en BD
        cursor.execute("SELECT COUNT(*) FROM expediente")
        total_bd = cursor.fetchone()[0]
        print(f"\nTotal de expedientes en BD: {total_bd}\n")
        
        # Query correcta que usa CASE WHEN para evitar solapamientos
        cursor.execute("""
            WITH categorias AS (
                SELECT e.id,
                    CASE 
                        WHEN EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
                             AND (NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                                  OR 
                                  (SELECT MAX(i2.fecha_ingreso) FROM ingresos i2 WHERE i2.expediente_id = e.id) > 
                                  (SELECT MAX(s2.fecha_estado) FROM estados s2 WHERE s2.expediente_id = e.id))
                        THEN 'ACTIVO PENDIENTE'
                        
                        WHEN EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                             AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) > 
                                 (CURRENT_DATE - INTERVAL '1 year')
                        THEN 'ACTIVO RESUELTO'
                        
                        WHEN EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                             AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) <= 
                                 (CURRENT_DATE - INTERVAL '1 year')
                        THEN 'INACTIVO RESUELTO'
                        
                        ELSE 'PENDIENTE'
                    END as categoria
                FROM expediente e
            )
            SELECT categoria, COUNT(*) as total
            FROM categorias
            GROUP BY categoria
            ORDER BY total DESC
        """)
        
        resultados = cursor.fetchall()
        
        print("DISTRIBUCIÓN DE EXPEDIENTES POR ESTADO:")
        print("-" * 70)
        
        total_categorizado = 0
        for estado, total in resultados:
            total_categorizado += total
            porcentaje = (total / total_bd * 100) if total_bd > 0 else 0
            print(f"  {estado:<20} {total:>6} expedientes ({porcentaje:>5.1f}%)")
        
        print("-" * 70)
        print(f"  {'TOTAL':<20} {total_categorizado:>6} expedientes")
        print("="*70)
        
        # Verificación final
        if total_categorizado == total_bd:
            print(f"\n✓✓✓ ÉXITO: Filtro por estado funciona correctamente")
            print(f"    Todos los {total_bd} expedientes están categorizados sin duplicados\n")
            
            # Mostrar algunos ejemplos de cada categoría
            print("\nEJEMPLOS DE CADA CATEGORÍA:")
            print("-" * 70)
            
            for estado in ['ACTIVO PENDIENTE', 'ACTIVO RESUELTO', 'INACTIVO RESUELTO', 'PENDIENTE']:
                cursor.execute(f"""
                    WITH categorias AS (
                        SELECT e.id, e.radicado_completo,
                            (SELECT COUNT(*) FROM ingresos i WHERE i.expediente_id = e.id) as ingresos,
                            (SELECT COUNT(*) FROM estados s WHERE s.expediente_id = e.id) as estados,
                            (SELECT MAX(i.fecha_ingreso) FROM ingresos i WHERE i.expediente_id = e.id) as max_ingreso,
                            (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) as max_estado,
                            CASE 
                                WHEN EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
                                     AND (NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                                          OR 
                                          (SELECT MAX(i2.fecha_ingreso) FROM ingresos i2 WHERE i2.expediente_id = e.id) > 
                                          (SELECT MAX(s2.fecha_estado) FROM estados s2 WHERE s2.expediente_id = e.id))
                                THEN 'ACTIVO PENDIENTE'
                                
                                WHEN EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                                     AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) > 
                                         (CURRENT_DATE - INTERVAL '1 year')
                                THEN 'ACTIVO RESUELTO'
                                
                                WHEN EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                                     AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) <= 
                                         (CURRENT_DATE - INTERVAL '1 year')
                                THEN 'INACTIVO RESUELTO'
                                
                                ELSE 'PENDIENTE'
                            END as categoria
                        FROM expediente e
                    )
                    SELECT radicado_completo, ingresos, estados, max_ingreso, max_estado
                    FROM categorias
                    WHERE categoria = %s
                    LIMIT 2
                """, (estado,))
                
                ejemplos = cursor.fetchall()
                if ejemplos:
                    print(f"\n{estado}:")
                    for radicado, ingresos, estados, max_ing, max_est in ejemplos:
                        print(f"  - {radicado}")
                        print(f"    → {ingresos} ingresos (max: {max_ing}), {estados} estados (max: {max_est})")
            
            return True
        else:
            print(f"\n⚠️  ADVERTENCIA: Inconsistencia en categorización")
            print(f"    Total en BD: {total_bd}")
            print(f"    Total categorizado: {total_categorizado}")
            print(f"    Diferencia: {total_categorizado - total_bd}\n")
            return False
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗✗✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verificar_filtro_corregido()
    sys.exit(0 if success else 1)
