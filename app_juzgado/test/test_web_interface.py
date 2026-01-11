#!/usr/bin/env python3
"""
Test de la interfaz web para verificar que el filtro funciona correctamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from vista.vistaexpediente import vistaexpediente

def test_web_interface():
    """Test de la interfaz web"""
    
    print("=== TEST INTERFAZ WEB ===")
    
    # Crear app Flask de prueba
    app = Flask(__name__)
    app.secret_key = 'test_key'
    app.register_blueprint(vistaexpediente, url_prefix='/')
    
    with app.test_client() as client:
        # Test 1: GET request (página inicial)
        print("\n1. Probando GET request...")
        response = client.get('/expediente')
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.content_type}")
        
        # Test 2: POST request con filtro por estado
        print("\n2. Probando POST request con filtro por estado...")
        data = {
            'tipo_busqueda': 'estado',
            'estado_filtro': 'ACTIVO PENDIENTE',
            'orden_fecha': 'DESC',
            'limite': '10'
        }
        
        response = client.post('/expediente', data=data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            
            # Verificar que contiene elementos esperados
            checks = [
                ('resumen_filtro', 'Expedientes con Estado:' in content),
                ('ver_mas_button', 'Ver más' in content),
                ('expediente_details', 'expediente-details-hidden' in content),
                ('estado_filtro', 'ACTIVO PENDIENTE' in content)
            ]
            
            print("   Verificaciones:")
            for check_name, result in checks:
                status = "✓" if result else "✗"
                print(f"     {status} {check_name}: {result}")
        
        # Test 3: POST request con búsqueda por radicado
        print("\n3. Probando POST request con búsqueda por radicado...")
        data = {
            'tipo_busqueda': 'radicado',
            'radicado': '08001418902220200004000'
        }
        
        response = client.post('/expediente', data=data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            
            # Verificar que NO contiene resumen_filtro (solo para filtros)
            has_resumen_filtro = 'Expedientes con Estado:' in content
            has_ver_mas = 'Ver más' in content
            
            print("   Verificaciones:")
            print(f"     ✓ No resumen_filtro: {not has_resumen_filtro}")
            print(f"     ✓ No botón Ver más: {not has_ver_mas}")

if __name__ == "__main__":
    test_web_interface()