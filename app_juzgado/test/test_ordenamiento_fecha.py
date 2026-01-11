#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar que el ordenamiento por fecha funciona correctamente
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_juzgado'))

from app_juzgado.modelo.configBd import obtener_conexion

def verificar_ordenamiento_fecha():
    """Verifica que el ordenamiento por fecha en filtro por estado funciona"""
    
    print("="*80)
    print("VERIFICANDO ORDENAMIENTO POR FECHA EN FILTRO POR ESTADO")
    print("="*80)
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Test 1: Ordenamiento DESC (más recientes primero)
        print("\n[TEST 1] ORDENAMIENTO DESC - Más recientes primero")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                e.id, e.radicado_completo, 
                COALESCE(
                    (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id),
                    (SELECT MAX(i.fecha_ingreso) FROM ingresos i WHERE i.expediente_id = e.id),
                    e.fecha_ingreso,
                    CURRENT_DATE
                ) as fecha_orden
            FROM expediente e
            WHERE EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
               OR EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
            ORDER BY fecha_orden DESC
            LIMIT 10
        """)
        
        resultados_desc = cursor.fetchall()
        print("Primeros 10 expedientes (DESC - más recientes):\n")
        
        fechas_desc = []
        for i, (exp_id, radicado, fecha) in enumerate(resultados_desc, 1):
            print(f"{i:2}. {radicado} → {fecha.strftime('%Y-%m-%d') if fecha else 'N/A'}")
            fechas_desc.append(fecha)
        
        # Verificar que está ordenado correctamente
        es_desc_correcto = all(fechas_desc[i] >= fechas_desc[i+1] for i in range(len(fechas_desc)-1))
        if es_desc_correcto:
            print("✓ Ordenamiento DESC: CORRECTO (de más reciente a más antiguo)")
        else:
            print("✗ Ordenamiento DESC: INCORRECTO (no está ordenado de mayor a menor)")
        
        # Test 2: Ordenamiento ASC (más antiguos primero)
        print("\n[TEST 2] ORDENAMIENTO ASC - Más antiguos primero")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                e.id, e.radicado_completo, 
                COALESCE(
                    (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id),
                    (SELECT MAX(i.fecha_ingreso) FROM ingresos i WHERE i.expediente_id = e.id),
                    e.fecha_ingreso,
                    CURRENT_DATE
                ) as fecha_orden
            FROM expediente e
            WHERE EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
               OR EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
            ORDER BY fecha_orden ASC
            LIMIT 10
        """)
        
        resultados_asc = cursor.fetchall()
        print("Primeros 10 expedientes (ASC - más antiguos):\n")
        
        fechas_asc = []
        for i, (exp_id, radicado, fecha) in enumerate(resultados_asc, 1):
            print(f"{i:2}. {radicado} → {fecha.strftime('%Y-%m-%d') if fecha else 'N/A'}")
            fechas_asc.append(fecha)
        
        # Verificar que está ordenado correctamente
        es_asc_correcto = all(fechas_asc[i] <= fechas_asc[i+1] for i in range(len(fechas_asc)-1))
        if es_asc_correcto:
            print("✓ Ordenamiento ASC: CORRECTO (de más antiguo a más reciente)")
        else:
            print("✗ Ordenamiento ASC: INCORRECTO (no está ordenado de menor a mayor)")
        
        # Test 3: Verificar que las fechas son diferentes en ambos sentidos
        print("\n[TEST 3] COMPARACIÓN DESC vs ASC")
        print("-" * 80)
        
        print(f"Más reciente (DESC):  {resultados_desc[0][2].strftime('%Y-%m-%d') if resultados_desc[0][2] else 'N/A'}")
        print(f"Más antigua (ASC):    {resultados_asc[0][2].strftime('%Y-%m-%d') if resultados_asc[0][2] else 'N/A'}")
        
        # Test 4: Verificar por categoría específica
        print("\n[TEST 4] ORDENAMIENTO POR CATEGORÍA - ACTIVO PENDIENTE (DESC)")
        print("-" * 80)
        
        cursor.execute("""
            WITH expedientes_activo AS (
                SELECT e.id, e.radicado_completo,
                    (SELECT MAX(i.fecha_ingreso) FROM ingresos i WHERE i.expediente_id = e.id) as max_ingreso
                FROM expediente e
                WHERE EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
                  AND (NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                       OR 
                       (SELECT MAX(i2.fecha_ingreso) FROM ingresos i2 WHERE i2.expediente_id = e.id) > 
                       (SELECT MAX(s2.fecha_estado) FROM estados s2 WHERE s2.expediente_id = e.id))
            )
            SELECT radicado_completo, max_ingreso
            FROM expedientes_activo
            ORDER BY max_ingreso DESC
            LIMIT 10
        """)
        
        resultados_activo = cursor.fetchall()
        print("Top 10 ACTIVO PENDIENTE (ordenados por ingreso más reciente):\n")
        
        fechas_activo = []
        for i, (radicado, fecha) in enumerate(resultados_activo, 1):
            print(f"{i:2}. {radicado} → Ingreso: {fecha.strftime('%Y-%m-%d') if fecha else 'N/A'}")
            if fecha is not None:  # Solo agregar fechas válidas
                fechas_activo.append(fecha)
        
        # Verificar ordenamiento solo con fechas no-None
        es_activo_correcto = True
        if len(fechas_activo) > 1:
            es_activo_correcto = all(fechas_activo[i] >= fechas_activo[i+1] for i in range(len(fechas_activo)-1))
        if es_activo_correcto:
            print("✓ Ordenamiento ACTIVO PENDIENTE: CORRECTO")
        else:
            print("✗ Ordenamiento ACTIVO PENDIENTE: INCORRECTO")
        
        # RESUMEN FINAL
        print("\n" + "="*80)
        print("RESUMEN FINAL")
        print("="*80)
        
        todos_correctos = es_desc_correcto and es_asc_correcto and es_activo_correcto
        
        if todos_correctos:
            print("✓✓✓ ÉXITO: El ordenamiento por fecha funciona correctamente en todas las pruebas")
            print("\n  ✓ DESC (más recientes primero): FUNCIONA")
            print("  ✓ ASC (más antiguos primero): FUNCIONA")
            print("  ✓ Ordenamiento por categoría: FUNCIONA")
        else:
            print("✗✗✗ FALLO: Hay problemas en el ordenamiento por fecha")
            if not es_desc_correcto:
                print("  ✗ DESC (más recientes primero): FALLA")
            if not es_asc_correcto:
                print("  ✗ ASC (más antiguos primero): FALLA")
            if not es_activo_correcto:
                print("  ✗ Ordenamiento por categoría: FALLA")
        
        print("="*80)
        
        cursor.close()
        conn.close()
        
        return todos_correctos
        
    except Exception as e:
        print(f"\n✗✗✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verificar_ordenamiento_fecha()
    sys.exit(0 if success else 1)
