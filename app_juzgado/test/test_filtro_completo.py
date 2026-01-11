#!/usr/bin/env python3
"""
Test completo del filtro por estado para verificar que funciona correctamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vista.vistaexpediente import filtrar_por_estado

def test_filtro_estado():
    """Test del filtro por estado"""
    
    print("=== TEST FILTRO POR ESTADO ===")
    
    # Test 1: Filtrar por ACTIVO PENDIENTE
    print("\n1. Filtrando por ACTIVO PENDIENTE...")
    try:
        expedientes = filtrar_por_estado("ACTIVO PENDIENTE", limite=5)
        print(f"   Encontrados: {len(expedientes)} expedientes")
        
        if expedientes:
            exp = expedientes[0]
            print(f"   Ejemplo: {exp['radicado_completo']} - Estado: {exp['estado_actual']}")
            print(f"   Ingresos: {len(exp['ingresos'])}, Estados: {len(exp['estados'])}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 2: Filtrar por ACTIVO RESUELTO
    print("\n2. Filtrando por ACTIVO RESUELTO...")
    try:
        expedientes = filtrar_por_estado("ACTIVO RESUELTO", limite=5)
        print(f"   Encontrados: {len(expedientes)} expedientes")
        
        if expedientes:
            exp = expedientes[0]
            print(f"   Ejemplo: {exp['radicado_completo']} - Estado: {exp['estado_actual']}")
            print(f"   Ingresos: {len(exp['ingresos'])}, Estados: {len(exp['estados'])}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 3: Filtrar por INACTIVO RESUELTO
    print("\n3. Filtrando por INACTIVO RESUELTO...")
    try:
        expedientes = filtrar_por_estado("INACTIVO RESUELTO", limite=5)
        print(f"   Encontrados: {len(expedientes)} expedientes")
        
        if expedientes:
            exp = expedientes[0]
            print(f"   Ejemplo: {exp['radicado_completo']} - Estado: {exp['estado_actual']}")
            print(f"   Ingresos: {len(exp['ingresos'])}, Estados: {len(exp['estados'])}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 4: Filtrar por PENDIENTE
    print("\n4. Filtrando por PENDIENTE...")
    try:
        expedientes = filtrar_por_estado("PENDIENTE", limite=5)
        print(f"   Encontrados: {len(expedientes)} expedientes")
        
        if expedientes:
            exp = expedientes[0]
            print(f"   Ejemplo: {exp['radicado_completo']} - Estado: {exp['estado_actual']}")
            print(f"   Ingresos: {len(exp['ingresos'])}, Estados: {len(exp['estados'])}")
        
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == "__main__":
    test_filtro_estado()