#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para CONSULTAR duplicados sin eliminarlos
Útil para revisar qué registros se consideran duplicados antes de ejecutar la limpieza
"""

import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

def consultar_duplicados_estados(radicado=None):
    """Consulta duplicados en estados (sin eliminar)"""
    print("\n📤 CONSULTANDO DUPLICADOS EN ESTADOS...")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Query para encontrar duplicados
        if radicado:
            # Buscar duplicados de un expediente específico
            query = """
                SELECT 
                    e.id,
                    exp.radicado_completo,
                    e.fecha_estado,
                    e.clase,
                    e.auto_anotacion,
                    e.observaciones,
                    COUNT(*) OVER (
                        PARTITION BY e.expediente_id, e.fecha_estado, e.clase, e.auto_anotacion
                    ) as total_duplicados
                FROM estados e
                JOIN expediente exp ON e.expediente_id = exp.id
                WHERE exp.radicado_completo LIKE %s
                ORDER BY e.expediente_id, e.fecha_estado, e.clase, e.auto_anotacion, e.id
            """
            cursor.execute(query, (f'%{radicado}%',))
        else:
            # Buscar todos los duplicados
            query = """
                SELECT 
                    e.id,
                    exp.radicado_completo,
                    e.fecha_estado,
                    e.clase,
                    e.auto_anotacion,
                    e.observaciones,
                    COUNT(*) OVER (
                        PARTITION BY e.expediente_id, e.fecha_estado, e.clase, e.auto_anotacion
                    ) as total_duplicados
                FROM estados e
                JOIN expediente exp ON e.expediente_id = exp.id
                ORDER BY total_duplicados DESC, exp.radicado_completo, e.fecha_estado
                LIMIT 100
            """
            cursor.execute(query)
        
        resultados = cursor.fetchall()
        
        # Filtrar solo los que tienen duplicados
        duplicados = [r for r in resultados if r[6] > 1]
        
        if duplicados:
            print(f"\n   ✅ Encontrados {len(duplicados)} registros con duplicados")
            print("\n   📋 DETALLE DE DUPLICADOS:")
            print("   " + "="*100)
            
            radicado_anterior = None
            grupo_num = 0
            
            for id_estado, radicado, fecha, clase, auto, obs, total in duplicados:
                # Detectar cambio de grupo
                if radicado != radicado_anterior:
                    grupo_num += 1
                    print(f"\n   🔸 GRUPO {grupo_num} - Radicado: {radicado} ({total} registros duplicados)")
                    radicado_anterior = radicado
                
                obs_preview = (obs[:60] + '...') if obs and len(obs) > 60 else (obs or 'NULL')
                print(f"      ID: {id_estado:6d} | Fecha: {fecha} | Clase: {clase[:30]:30s} | Auto: {auto[:30]:30s}")
                print(f"                  | Observaciones: {obs_preview}")
            
            print("\n   " + "="*100)
        else:
            print(f"   ✅ No se encontraron duplicados")
        
        cursor.close()
        conn.close()
        
        return len(duplicados)
        
    except Exception as e:
        print(f"   ❌ Error consultando estados: {str(e)}")
        return 0

def consultar_duplicados_ingresos(radicado=None):
    """Consulta duplicados en ingresos (sin eliminar)"""
    print("\n📥 CONSULTANDO DUPLICADOS EN INGRESOS...")
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Query para encontrar duplicados
        if radicado:
            query = """
                SELECT 
                    i.id,
                    exp.radicado_completo,
                    i.fecha_ingreso,
                    i.solicitud,
                    i.observaciones,
                    COUNT(*) OVER (
                        PARTITION BY i.expediente_id, i.fecha_ingreso, i.solicitud
                    ) as total_duplicados
                FROM ingresos i
                JOIN expediente exp ON i.expediente_id = exp.id
                WHERE exp.radicado_completo LIKE %s
                ORDER BY i.expediente_id, i.fecha_ingreso, i.solicitud, i.id
            """
            cursor.execute(query, (f'%{radicado}%',))
        else:
            query = """
                SELECT 
                    i.id,
                    exp.radicado_completo,
                    i.fecha_ingreso,
                    i.solicitud,
                    i.observaciones,
                    COUNT(*) OVER (
                        PARTITION BY i.expediente_id, i.fecha_ingreso, i.solicitud
                    ) as total_duplicados
                FROM ingresos i
                JOIN expediente exp ON i.expediente_id = exp.id
                ORDER BY total_duplicados DESC, exp.radicado_completo, i.fecha_ingreso
                LIMIT 100
            """
            cursor.execute(query)
        
        resultados = cursor.fetchall()
        duplicados = [r for r in resultados if r[5] > 1]
        
        if duplicados:
            print(f"\n   ✅ Encontrados {len(duplicados)} registros con duplicados")
            print("\n   📋 DETALLE DE DUPLICADOS:")
            print("   " + "="*100)
            
            radicado_anterior = None
            grupo_num = 0
            
            for id_ingreso, radicado, fecha, solicitud, obs, total in duplicados:
                if radicado != radicado_anterior:
                    grupo_num += 1
                    print(f"\n   🔸 GRUPO {grupo_num} - Radicado: {radicado} ({total} registros duplicados)")
                    radicado_anterior = radicado
                
                obs_preview = (obs[:60] + '...') if obs and len(obs) > 60 else (obs or 'NULL')
                print(f"      ID: {id_ingreso:6d} | Fecha: {fecha} | Solicitud: {solicitud[:40]:40s}")
                print(f"                  | Observaciones: {obs_preview}")
            
            print("\n   " + "="*100)
        else:
            print(f"   ✅ No se encontraron duplicados")
        
        cursor.close()
        conn.close()
        
        return len(duplicados)
        
    except Exception as e:
        print(f"   ❌ Error consultando ingresos: {str(e)}")
        return 0

def main():
    print("\n" + "="*70)
    print("🔍 CONSULTA DE DUPLICADOS (SIN ELIMINAR)")
    print("="*70)
    print("\nEste script muestra los registros duplicados sin eliminarlos.")
    print("Campos clave:")
    print("  - INGRESOS: expediente_id, fecha_ingreso, solicitud")
    print("  - ESTADOS: expediente_id, fecha_estado, clase, auto_anotacion")
    
    print("\nOpciones:")
    print("  1. Consultar duplicados de un expediente específico")
    print("  2. Consultar todos los duplicados (primeros 100)")
    
    opcion = input("\nSeleccione una opción (1 o 2): ")
    
    radicado = None
    if opcion == '1':
        radicado = input("Ingrese el radicado (o parte de él): ").strip()
        if not radicado:
            print("❌ Debe ingresar un radicado")
            return
    
    print("\n🚀 Consultando duplicados...\n")
    
    # Consultar duplicados
    total_ingresos = consultar_duplicados_ingresos(radicado)
    total_estados = consultar_duplicados_estados(radicado)
    
    print("\n" + "="*70)
    print("✅ CONSULTA COMPLETADA")
    print("="*70)
    print(f"\n📊 RESUMEN:")
    print(f"   Registros de ingresos con duplicados: {total_ingresos}")
    print(f"   Registros de estados con duplicados: {total_estados}")
    print(f"   TOTAL: {total_ingresos + total_estados}")
    print("\n💡 Para eliminar estos duplicados, ejecute: limpiar_duplicados_v2.py")
    print("="*70)

if __name__ == "__main__":
    main()
