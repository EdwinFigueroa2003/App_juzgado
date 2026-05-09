#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.configBd import obtener_conexion

conn = obtener_conexion()
cursor = conn.cursor()
cursor.execute("UPDATE expediente SET estado = 'Sin Movimiento' WHERE estado = 'Pendiente'")
actualizados = cursor.rowcount
conn.commit()
cursor.close()
conn.close()
print(f"✅ {actualizados} expedientes actualizados de 'Pendiente' a 'Sin Movimiento'")
