#!/usr/bin/env python3
"""
migrar_clases_estado.py
-----------------------
Crea la tabla clases_estado y la pobla con las clases que estaban
hardcodeadas en actualizarexpediente.html.

Ejecutar UNA sola vez:
    python app_juzgado/utils/migrar_clases_estado.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.configBd import obtener_conexion

CLASES_INICIALES = [
    'Ejecutivos De Mínima Cuantía',
    'Ejecutivos De Mayor Cuantía',
    'Procesos Ejecutivos',
    'Declarativos',
    'Especiales',
    'Terminado',
    'Archivado',
]

conn = obtener_conexion()
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute("""
    CREATE TABLE IF NOT EXISTS clases_estado (
        id      SERIAL PRIMARY KEY,
        nombre  VARCHAR(200) NOT NULL UNIQUE,
        activo  BOOLEAN NOT NULL DEFAULT TRUE,
        creado  TIMESTAMP NOT NULL DEFAULT NOW()
    )
""")

# Insertar clases iniciales (ignorar duplicados)
for nombre in CLASES_INICIALES:
    cursor.execute("""
        INSERT INTO clases_estado (nombre)
        VALUES (%s)
        ON CONFLICT (nombre) DO NOTHING
    """, (nombre,))

conn.commit()

cursor.execute("SELECT id, nombre, activo FROM clases_estado ORDER BY nombre")
rows = cursor.fetchall()
print(f"✅ Tabla clases_estado lista — {len(rows)} clases:")
for r in rows:
    estado = '✓' if r[2] else '✗'
    print(f"  [{estado}] {r[0]:3d}. {r[1]}")

cursor.close()
conn.close()
