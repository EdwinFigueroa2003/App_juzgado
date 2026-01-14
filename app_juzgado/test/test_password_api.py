#!/usr/bin/env python3
"""
Script para probar la API de validación de contraseñas
"""

import requests
import json

def test_password_api():
    """Prueba la API de validación de contraseñas"""
    
    url = "http://127.0.0.1:5000/api/validate-password"
    
    # Casos de prueba
    test_cases = [
        {
            "name": "Contraseña vacía",
            "password": "",
            "expected_valid": False
        },
        {
            "name": "Contraseña débil",
            "password": "123",
            "expected_valid": False
        },
        {
            "name": "Contraseña moderada",
            "password": "Password123",
            "expected_valid": True
        },
        {
            "name": "Contraseña fuerte",
            "password": "MiContraseña123!",
            "expected_valid": True
        }
    ]
    
    print("=== PRUEBA DE API DE VALIDACIÓN DE CONTRASEÑAS ===\n")
    
    for test_case in test_cases:
        print(f"Probando: {test_case['name']}")
        print(f"Contraseña: '{test_case['password']}'")
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json={'password': test_case['password']},
                timeout=5
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Respuesta exitosa:")
                print(f"   - Válida: {result.get('is_valid', 'N/A')}")
                print(f"   - Fortaleza: {result.get('strength', 'N/A')}")
                print(f"   - Puntaje: {result.get('score', 'N/A')}")
                print(f"   - Errores: {len(result.get('errors', []))}")
                print(f"   - Sugerencias: {len(result.get('suggestions', []))}")
            else:
                print(f"❌ Error HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error text: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print("❌ Error: No se pudo conectar al servidor. ¿Está ejecutándose la aplicación?")
        except requests.exceptions.Timeout:
            print("❌ Error: Timeout en la petición")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_password_api()