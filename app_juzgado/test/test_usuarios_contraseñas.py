#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de usuarios
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app_juzgado'))

def test_imports():
    """Verificar que todas las importaciones funcionen"""
    try:
        from vista.vistausuarios import obtener_todos_usuarios, obtener_roles
        from utils.auth import hash_password, validate_password
        print("✅ Todas las importaciones funcionan correctamente")
        return True
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False

def test_password_validation():
    """Verificar que la validación de contraseñas funcione"""
    try:
        from utils.auth import validate_password
        
        # Probar contraseña débil
        weak_result = validate_password("123")
        print(f"Contraseña débil '123': válida={weak_result['is_valid']}")
        
        # Probar contraseña fuerte
        strong_result = validate_password("MiContraseña123!")
        print(f"Contraseña fuerte 'MiContraseña123!': válida={strong_result['is_valid']}, fortaleza={strong_result.get('strength', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Error en validación de contraseñas: {e}")
        return False

def test_database_connection():
    """Verificar conexión a la base de datos"""
    try:
        from modelo.configBd import obtener_conexion
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"✅ Conexión a BD exitosa. Total usuarios: {count}")
        return True
    except Exception as e:
        print(f"❌ Error de conexión a BD: {e}")
        return False

def main():
    print("=== PRUEBA DE FUNCIONALIDAD DE USUARIOS ===\n")
    
    tests = [
        ("Importaciones", test_imports),
        ("Validación de contraseñas", test_password_validation),
        ("Conexión a base de datos", test_database_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Ejecutando: {test_name}")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Error inesperado en {test_name}: {e}")
            results.append(False)
        print()
    
    # Resumen
    passed = sum(results)
    total = len(results)
    print(f"=== RESUMEN ===")
    print(f"Pruebas pasadas: {passed}/{total}")
    
    if passed == total:
        print("🎉 Todas las pruebas pasaron. La funcionalidad de usuarios debería funcionar correctamente.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revise los errores anteriores.")

if __name__ == "__main__":
    main()