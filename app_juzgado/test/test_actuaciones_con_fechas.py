#!/usr/bin/env python3
"""
Script para probar que las actuaciones ahora tienen fechas
"""

import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vista.vistaexpediente import buscar_expedientes

def test_actuaciones_con_fechas(radicado):
    """Probar que las actuaciones tienen fechas cargadas"""
    
    print(f"🧪 PROBANDO ACTUACIONES CON FECHAS PARA: {radicado}")
    print("=" * 70)
    
    try:
        expedientes = buscar_expedientes(radicado)
        
        if not expedientes:
            print("❌ No se encontraron expedientes")
            return
        
        expediente = expedientes[0]
        actuaciones = expediente['actuaciones']
        
        print(f"✅ Expediente encontrado: {expediente['id']}")
        print(f"📋 Total de actuaciones: {len(actuaciones)}")
        
        if actuaciones:
            con_fecha = 0
            sin_fecha = 0
            
            print(f"\n📝 DETALLE DE ACTUACIONES CON FECHAS:")
            for i, actuacion in enumerate(actuaciones, 1):
                fecha_act = actuacion.get('fecha_actuacion')
                if fecha_act:
                    con_fecha += 1
                    print(f"\n   ✅ ACTUACIÓN {i} (CON FECHA):")
                else:
                    sin_fecha += 1
                    print(f"\n   ⚠️  ACTUACIÓN {i} (SIN FECHA):")
                
                print(f"      Número: {actuacion.get('numero_actuacion', 'N/A')}")
                print(f"      Tipo: {actuacion.get('tipo_origen', 'N/A')}")
                print(f"      Descripción: {actuacion.get('descripcion_actuacion', 'N/A')[:50]}...")
                print(f"      Archivo: {actuacion.get('archivo_origen', 'N/A')}")
                print(f"      Fecha: {fecha_act}")
                
                if fecha_act and hasattr(fecha_act, 'strftime'):
                    print(f"      Fecha formateada: {fecha_act.strftime('%d/%m/%Y')}")
            
            print(f"\n📊 RESUMEN:")
            print(f"   • Actuaciones con fecha: {con_fecha}")
            print(f"   • Actuaciones sin fecha: {sin_fecha}")
            print(f"   • Total: {len(actuaciones)}")
            
            if con_fecha > 0:
                print(f"   ✅ ¡Éxito! Las actuaciones ahora tienen fechas")
            else:
                print(f"   ❌ Ninguna actuación tiene fecha")
                
        else:
            print("   ⚠️  No hay actuaciones registradas")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    radicado = "08001418900820220036500"
    if len(sys.argv) > 1:
        radicado = sys.argv[1]
    
    test_actuaciones_con_fechas(radicado)