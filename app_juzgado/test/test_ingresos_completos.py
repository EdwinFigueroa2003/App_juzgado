#!/usr/bin/env python3
"""
Script para probar los ingresos con todos los campos
"""

import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vista.vistaexpediente import buscar_expedientes

def test_ingresos_completos(radicado):
    """Probar que se cargan todos los campos de ingresos"""
    
    print(f"🧪 PROBANDO INGRESOS COMPLETOS PARA: {radicado}")
    print("=" * 70)
    
    try:
        expedientes = buscar_expedientes(radicado)
        
        if not expedientes:
            print("❌ No se encontraron expedientes")
            return
        
        expediente = expedientes[0]
        ingresos = expediente['ingresos']
        
        print(f"✅ Expediente encontrado: {expediente['id']}")
        print(f"📥 Total de ingresos: {len(ingresos)}")
        
        if ingresos:
            print(f"\n📋 DETALLE COMPLETO DE INGRESOS:")
            for i, ingreso in enumerate(ingresos, 1):
                print(f"\n   🔸 INGRESO {i}:")
                print(f"      Fecha ingreso: {ingreso.get('fecha_ingreso', 'N/A')}")
                print(f"      Observaciones: {ingreso.get('observaciones', 'N/A')}")
                print(f"      Solicitud: {ingreso.get('solicitud', 'N/A')}")
                print(f"      Fechas: {ingreso.get('fechas', 'N/A')}")
                print(f"      Actuación ID: {ingreso.get('actuacion_id', 'N/A')}")
                print(f"      Ubicación: {ingreso.get('ubicacion', 'N/A')}")
                print(f"      Fecha estado/auto: {ingreso.get('fecha_estado_auto', 'N/A')}")
                print(f"      Juzgado origen: {ingreso.get('juzgado_origen', 'N/A')}")
        else:
            print("   ⚠️  No hay ingresos registrados")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    radicado = "08001418900820220036500"
    if len(sys.argv) > 1:
        radicado = sys.argv[1]
    
    test_ingresos_completos(radicado)