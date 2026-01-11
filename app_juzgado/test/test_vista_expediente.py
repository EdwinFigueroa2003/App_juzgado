#!/usr/bin/env python3
"""
Script para probar directamente la función buscar_expedientes de la vista
"""

import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vista.vistaexpediente import buscar_expedientes

def test_buscar_expedientes(radicado):
    """Probar la función buscar_expedientes directamente"""
    
    print(f"🧪 PROBANDO buscar_expedientes('{radicado}')")
    print("=" * 60)
    
    try:
        expedientes = buscar_expedientes(radicado)
        
        if not expedientes:
            print("❌ No se encontraron expedientes")
            return
        
        print(f"✅ Se encontraron {len(expedientes)} expediente(s)")
        
        for i, exp in enumerate(expedientes, 1):
            print(f"\n📁 EXPEDIENTE {i}:")
            print(f"   ID: {exp['id']}")
            print(f"   Radicado completo: {exp['radicado_completo']}")
            print(f"   Radicado corto: {exp['radicado_corto']}")
            print(f"   Fecha ingreso: {exp['fecha_ingreso']}")
            print(f"   Fecha actuación: {exp['fecha_actuacion']} (tipo: {type(exp['fecha_actuacion'])})")
            
            if exp['fecha_actuacion']:
                if hasattr(exp['fecha_actuacion'], 'strftime'):
                    fecha_formateada = exp['fecha_actuacion'].strftime('%d/%m/%Y')
                    print(f"   Fecha formateada: {fecha_formateada}")
            
            print(f"   Estado actual: {exp['estado_actual']}")
            print(f"   Descripción estado: {exp['descripcion_estado']}")
            
            print(f"   Ingresos: {len(exp['ingresos'])}")
            for j, ingreso in enumerate(exp['ingresos'], 1):
                print(f"      {j}. {ingreso['fecha_ingreso']}")
            
            print(f"   Estados: {len(exp['estados'])}")
            for j, estado in enumerate(exp['estados'], 1):
                print(f"      {j}. {estado['fecha_estado']}")
            
            print(f"   Actuaciones: {len(exp['actuaciones'])}")
            for j, actuacion in enumerate(exp['actuaciones'], 1):
                print(f"      {j}. {actuacion['fecha_actuacion']}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    radicado = "08001418900820220036500"
    if len(sys.argv) > 1:
        radicado = sys.argv[1]
    
    test_buscar_expedientes(radicado)