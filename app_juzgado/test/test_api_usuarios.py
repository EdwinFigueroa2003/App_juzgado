#!/usr/bin/env python3
"""
Script para probar que el API busca correctamente en la tabla usuarios
"""

import sys
import os
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Agregar el directorio de la aplicación al path
sys.path.append('app_juzgado')

def test_usuarios_disponibles():
    """Verifica que existen usuarios en la tabla"""
    logger.info("=== PRUEBA: Usuarios Disponibles ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Verificar usuarios en la tabla
        cursor.execute("""
            SELECT id, usuario, nombre, correo
            FROM usuarios
            WHERE nombre IS NOT NULL AND nombre != ''
            ORDER BY nombre
        """)
        
        usuarios = cursor.fetchall()
        
        logger.info(f"Total usuarios con nombre: {len(usuarios)}")
        
        if usuarios:
            logger.info("Primeros 10 usuarios:")
            for i, (id, usuario, nombre, correo) in enumerate(usuarios[:10], 1):
                logger.info(f"  {i}. {nombre} (usuario: {usuario}, correo: {correo})")
        else:
            logger.warning("⚠️ No hay usuarios con nombre en la tabla")
        
        cursor.close()
        conn.close()
        
        return len(usuarios) > 0
        
    except Exception as e:
        logger.error(f"✗ Error verificando usuarios: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_busqueda_usuarios():
    """Prueba la búsqueda de usuarios simulando el API"""
    logger.info("\n=== PRUEBA: Búsqueda de Usuarios ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Primero obtener algunos nombres para probar
        cursor.execute("""
            SELECT DISTINCT nombre
            FROM usuarios
            WHERE nombre IS NOT NULL AND nombre != ''
            LIMIT 5
        """)
        
        nombres_prueba = [row[0] for row in cursor.fetchall()]
        
        if not nombres_prueba:
            logger.warning("No hay nombres para probar")
            return False
        
        logger.info(f"Probando búsquedas con {len(nombres_prueba)} nombres:")
        
        for nombre in nombres_prueba:
            # Tomar las primeras 3 letras para buscar
            query = nombre[:3] if len(nombre) >= 3 else nombre
            
            logger.info(f"\nBuscando con query: '{query}'")
            
            # Simular la búsqueda del API
            cursor.execute("""
                SELECT DISTINCT nombre
                FROM usuarios
                WHERE (nombre IS NOT NULL AND nombre != '' AND nombre ILIKE %s)
                   OR (usuario IS NOT NULL AND usuario != '' AND usuario ILIKE %s)
                ORDER BY nombre
                LIMIT 20
            """, (f'%{query}%', f'%{query}%'))
            
            resultados = cursor.fetchall()
            
            logger.info(f"  Resultados encontrados: {len(resultados)}")
            
            if resultados:
                logger.info("  Primeros 3 resultados:")
                for i, (nombre_resultado,) in enumerate(resultados[:3], 1):
                    logger.info(f"    {i}. {nombre_resultado}")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✓ Búsqueda de usuarios funciona correctamente")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en búsqueda: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_busqueda_combinada():
    """Prueba la búsqueda combinada (usuarios + responsables)"""
    logger.info("\n=== PRUEBA: Búsqueda Combinada ===")
    
    try:
        from modelo.configBd import obtener_conexion
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        query_test = "a"  # Buscar con 'a'
        
        logger.info(f"Buscando con query: '{query_test}'")
        
        # Buscar en usuarios
        cursor.execute("""
            SELECT DISTINCT nombre
            FROM usuarios
            WHERE (nombre IS NOT NULL AND nombre != '' AND nombre ILIKE %s)
               OR (usuario IS NOT NULL AND usuario != '' AND usuario ILIKE %s)
            ORDER BY nombre
            LIMIT 20
        """, (f'%{query_test}%', f'%{query_test}%'))
        
        usuarios_encontrados = [row[0] for row in cursor.fetchall() if row[0]]
        
        logger.info(f"  Usuarios encontrados: {len(usuarios_encontrados)}")
        
        # Buscar en responsables de expedientes
        cursor.execute("""
            SELECT DISTINCT responsable
            FROM expediente
            WHERE responsable IS NOT NULL 
              AND responsable != ''
              AND responsable ILIKE %s
              AND responsable NOT IN (SELECT nombre FROM usuarios WHERE nombre IS NOT NULL)
            ORDER BY responsable
            LIMIT 10
        """, (f'%{query_test}%',))
        
        responsables_encontrados = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"  Responsables adicionales: {len(responsables_encontrados)}")
        
        # Combinar
        todas_personas = list(dict.fromkeys(usuarios_encontrados + responsables_encontrados))
        
        logger.info(f"  Total combinado: {len(todas_personas)}")
        
        if todas_personas:
            logger.info("  Primeros 5 resultados combinados:")
            for i, persona in enumerate(todas_personas[:5], 1):
                logger.info(f"    {i}. {persona}")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✓ Búsqueda combinada funciona correctamente")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error en búsqueda combinada: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    logger.info("🚀 === PRUEBA API BÚSQUEDA DE USUARIOS ===\n")
    
    pruebas = [
        ("Usuarios Disponibles", test_usuarios_disponibles),
        ("Búsqueda de Usuarios", test_busqueda_usuarios),
        ("Búsqueda Combinada", test_busqueda_combinada)
    ]
    
    resultados = []
    
    for nombre, test_func in pruebas:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            logger.error(f"💥 {nombre}: ERROR - {str(e)}")
            resultados.append((nombre, False))
    
    # Resumen
    logger.info("\n🎯 === RESUMEN ===")
    pasadas = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    logger.info(f"Pruebas pasadas: {pasadas}/{total}")
    
    for nombre, resultado in resultados:
        estado = "✅ PASÓ" if resultado else "❌ FALLÓ"
        logger.info(f"  - {nombre}: {estado}")
    
    if pasadas == total:
        logger.info("\n🎉 TODAS LAS PRUEBAS PASARON - API LISTA")
        return True
    else:
        logger.warning(f"\n⚠️ {total - pasadas} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)