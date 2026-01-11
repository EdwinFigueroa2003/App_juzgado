#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que el filtro por estado funciona correctamente
"""
import sys
import os

# Añadir el directorio de la app al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_juzgado'))

from app_juzgado.modelo.configBd import obtener_conexion

def verificar_filtro_por_estado():
    """Verifica que el filtro por estado funciona correctamente"""
    
    print("="*70)
    print("VERIFICANDO FILTRO POR ESTADO")
    print("="*70)
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # TEST 1: Verificar expedientes con ACTIVO PENDIENTE (tienen ingresos)
        print("\n[TEST 1] ACTIVO PENDIENTE - Expedientes con ingresos")
        print("-" * 70)
        
        cursor.execute("""
            SELECT COUNT(DISTINCT e.id) as total
            FROM expediente e
            WHERE EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
              AND (NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                   OR 
                   (SELECT MAX(i2.fecha_ingreso) FROM ingresos i2 WHERE i2.expediente_id = e.id) > 
                   (SELECT MAX(s2.fecha_estado) FROM estados s2 WHERE s2.expediente_id = e.id))
        """)
        
        result = cursor.fetchone()
        count_activo_pendiente = result[0] if result else 0
        print(f"✓ Expedientes con ACTIVO PENDIENTE: {count_activo_pendiente}")
        
        if count_activo_pendiente > 0:
            cursor.execute("""
                SELECT e.id, e.radicado_completo, 
                       (SELECT COUNT(*) FROM ingresos i WHERE i.expediente_id = e.id) as ingresos,
                       (SELECT COUNT(*) FROM estados s WHERE s.expediente_id = e.id) as estados
                FROM expediente e
                WHERE EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
                  AND (NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                       OR 
                       (SELECT MAX(i2.fecha_ingreso) FROM ingresos i2 WHERE i2.expediente_id = e.id) > 
                       (SELECT MAX(s2.fecha_estado) FROM estados s2 WHERE s2.expediente_id = e.id))
                LIMIT 3
            """)
            
            ejemplos = cursor.fetchall()
            print(f"\nEjemplos (primeros 3):")
            for exp in ejemplos:
                print(f"  - {exp[1]}: {exp[2]} ingresos, {exp[3]} estados")
        
        # TEST 2: Verificar expedientes con ACTIVO RESUELTO (tienen estados < 1 año)
        print("\n[TEST 2] ACTIVO RESUELTO - Expedientes resueltos hace < 1 año")
        print("-" * 70)
        
        cursor.execute("""
            SELECT COUNT(DISTINCT e.id) as total
            FROM expediente e
            WHERE EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
              AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) > 
                  (CURRENT_DATE - INTERVAL '1 year')
        """)
        
        result = cursor.fetchone()
        count_activo_resuelto = result[0] if result else 0
        print(f"✓ Expedientes con ACTIVO RESUELTO: {count_activo_resuelto}")
        
        if count_activo_resuelto > 0:
            cursor.execute("""
                SELECT e.id, e.radicado_completo, 
                       (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) as ultima_fecha,
                       (SELECT COUNT(*) FROM estados s WHERE s.expediente_id = e.id) as estados
                FROM expediente e
                WHERE EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                  AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) > 
                      (CURRENT_DATE - INTERVAL '1 year')
                LIMIT 3
            """)
            
            ejemplos = cursor.fetchall()
            print(f"\nEjemplos (primeros 3):")
            for exp in ejemplos:
                print(f"  - {exp[1]}: {exp[2].strftime('%Y-%m-%d') if exp[2] else 'N/A'}, {exp[3]} estados")
        
        # TEST 3: Verificar expedientes con INACTIVO RESUELTO (tienen estados > 1 año)
        print("\n[TEST 3] INACTIVO RESUELTO - Expedientes resueltos hace > 1 año")
        print("-" * 70)
        
        cursor.execute("""
            SELECT COUNT(DISTINCT e.id) as total
            FROM expediente e
            WHERE EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
              AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) <= 
                  (CURRENT_DATE - INTERVAL '1 year')
        """)
        
        result = cursor.fetchone()
        count_inactivo_resuelto = result[0] if result else 0
        print(f"✓ Expedientes con INACTIVO RESUELTO: {count_inactivo_resuelto}")
        
        if count_inactivo_resuelto > 0:
            cursor.execute("""
                SELECT e.id, e.radicado_completo, 
                       (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) as ultima_fecha,
                       (SELECT COUNT(*) FROM estados s WHERE s.expediente_id = e.id) as estados
                FROM expediente e
                WHERE EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                  AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) <= 
                      (CURRENT_DATE - INTERVAL '1 year')
                LIMIT 3
            """)
            
            ejemplos = cursor.fetchall()
            print(f"\nEjemplos (primeros 3):")
            for exp in ejemplos:
                print(f"  - {exp[1]}: {exp[2].strftime('%Y-%m-%d') if exp[2] else 'N/A'}, {exp[3]} estados")
        
        # TEST 4: Verificar expedientes PENDIENTE (sin ingresos ni estados)
        print("\n[TEST 4] PENDIENTE - Expedientes sin ingresos ni estados")
        print("-" * 70)
        
        cursor.execute("""
            SELECT COUNT(DISTINCT e.id) as total
            FROM expediente e
            WHERE NOT EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
              AND NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
        """)
        
        result = cursor.fetchone()
        count_pendiente = result[0] if result else 0
        print(f"✓ Expedientes PENDIENTE: {count_pendiente}")
        
        if count_pendiente > 0:
            cursor.execute("""
                SELECT e.id, e.radicado_completo
                FROM expediente e
                WHERE NOT EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
                  AND NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                LIMIT 3
            """)
            
            ejemplos = cursor.fetchall()
            print(f"\nEjemplos (primeros 3):")
            for exp in ejemplos:
                print(f"  - {exp[1]}")
        
        # RESUMEN
        print("\n" + "="*70)
        print("RESUMEN DE RESULTADOS")
        print("="*70)
        print(f"Total ACTIVO PENDIENTE:  {count_activo_pendiente:>6}")
        print(f"Total ACTIVO RESUELTO:   {count_activo_resuelto:>6}")
        print(f"Total INACTIVO RESUELTO: {count_inactivo_resuelto:>6}")
        print(f"Total PENDIENTE:         {count_pendiente:>6}")
        print(f"{'─'*35}")
        total_expedientes = count_activo_pendiente + count_activo_resuelto + count_inactivo_resuelto + count_pendiente
        print(f"TOTAL EXPEDIENTES:       {total_expedientes:>6}")
        print("="*70)
        
        # Verificación final
        cursor.execute("SELECT COUNT(*) FROM expediente")
        total_en_bd = cursor.fetchone()[0]
        
        if total_expedientes == total_en_bd:
            print(f"\n✓✓✓ ÉXITO: Todos los {total_en_bd} expedientes están categorizados correctamente")
        else:
            print(f"\n⚠️  ADVERTENCIA: Se categorizaron {total_expedientes} de {total_en_bd} expedientes")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n✗✗✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verificar_filtro_por_estado()
    sys.exit(0 if success else 1)
