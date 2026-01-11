#!/usr/bin/env python3
"""
Script para probar los estados con todos los campos
"""

import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vista.vistaexpediente import buscar_expedientes

def test_estados_completos(radicado):
    """Probar que se cargan todos los campos de estados"""
    
    print(f"🧪 PROBANDO ESTADOS COMPLETOS PARA: {radicado}")
    print("=" * 70)
    
    try:
        expedientes = buscar_expedientes(radicado)
        
        if not expedientes:
            print("❌ No se encontraron expedientes")
            return
        
        expediente = expedientes[0]
        estados = expediente['estados']
        
        print(f"✅ Expediente encontrado: {expediente['id']}")
        print(f"📤 Total de estados: {len(estados)}")
        
        if estados:
            print(f"\n📋 DETALLE COMPLETO DE ESTADOS:")
            for i, estado in enumerate(estados, 1):
                print(f"\n   🔸 ESTADO {i}:")
                print(f"      Fecha estado: {estado.get('fecha_estado', 'N/A')}")
                print(f"      Fecha auto: {estado.get('fecha_auto', 'N/A')}")
                print(f"      Clase: {estado.get('clase', 'N/A')}")
                print(f"      Auto/Anotación: {estado.get('auto_anotacion', 'N/A')}")
                print(f"      Observaciones: {estado.get('observaciones', 'N/A')}")
                print(f"      Actuación ID: {estado.get('actuacion_id', 'N/A')}")
                print(f"      Ingresos ID: {estado.get('ingresos_id', 'N/A')}")
                print(f"      Demandante: {estado.get('demandante', 'N/A')}")
                print(f"      Demandado: {estado.get('demandado', 'N/A')}")
        else:
            print("   ⚠️  No hay estados registrados")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    radicado = "08001418900820220036500"
    if len(sys.argv) > 1:
        radicado = sys.argv[1]
    
    test_estados_completos(radicado)