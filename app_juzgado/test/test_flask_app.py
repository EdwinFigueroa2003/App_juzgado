#!/usr/bin/env python3
"""
Script para probar la aplicación Flask directamente
"""

import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from vista.vistaexpediente import vistaexpediente

def test_flask_app():
    """Crear una aplicación Flask de prueba y simular una búsqueda"""
    
    app = Flask(__name__)
    app.register_blueprint(vistaexpediente)
    
    with app.test_client() as client:
        # Simular una búsqueda POST
        response = client.post('/expediente', data={
            'tipo_busqueda': 'radicado',
            'radicado': '08001418900820220036500'
        })
        
        print(f"🌐 RESPUESTA DE LA APLICACIÓN FLASK:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Buscar la fecha en el HTML
            html_content = response.get_data(as_text=True)
            
            # Buscar líneas que contengan "Última Actuación"
            lines = html_content.split('\n')
            for i, line in enumerate(lines):
                if 'Última Actuación' in line or 'fecha_actuacion' in line:
                    print(f"   Línea {i}: {line.strip()}")
                    # Mostrar también las líneas siguientes
                    for j in range(1, 4):
                        if i + j < len(lines):
                            print(f"   Línea {i+j}: {lines[i+j].strip()}")
                    print()
            
            # Buscar fechas específicas
            if '16/12/2024' in html_content:
                print("   ⚠️  ENCONTRADA FECHA INCORRECTA: 16/12/2024")
            
            if '19/11/2025' in html_content:
                print("   ✅ ENCONTRADA FECHA CORRECTA: 19/11/2025")
            
        else:
            print(f"   ❌ Error en la respuesta: {response.status_code}")

if __name__ == "__main__":
    test_flask_app()