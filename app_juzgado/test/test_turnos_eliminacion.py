#!/usr/bin/env python3
"""
Prueba de sincronización de turnos tras eliminar ingresos o estados.

Verifica que cuando un expediente queda sin filas en `ingresos` ni `estados`,
la lógica de `utils.turnos.sincronizar_estados_y_turnos` actualiza su estado a
`Sin Movimiento` y elimina el turno asignado.
"""

import sys
import os
import logging
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.append('app_juzgado')


def obtener_columnas(cursor, tabla):
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """,
        (tabla,)
    )
    return [row[0] for row in cursor.fetchall()]


def insertar_expediente(cursor, datos):
    columnas = []
    valores = []
    placeholders = []

    for columna, valor in datos.items():
        columnas.append(columna)
        valores.append(valor)
        placeholders.append('%s')

    cursor.execute(
        f"INSERT INTO expediente ({', '.join(columnas)}) VALUES ({', '.join(placeholders)}) RETURNING id",
        tuple(valores)
    )
    return cursor.fetchone()[0]


def insertar_ingreso(cursor, expediente_id, columnas):
    datos = {
        'expediente_id': expediente_id,
        'fecha_ingreso': date.today() - timedelta(days=20),
        'observaciones': 'Ingreso de prueba'
    }

    cols = [c for c in datos if c in columnas]
    vals = [datos[c] for c in cols]
    placeholders = ['%s'] * len(cols)

    cursor.execute(
        f"INSERT INTO ingresos ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING id",
        tuple(vals)
    )
    return cursor.fetchone()[0]


def insertar_estado(cursor, expediente_id, columnas):
    datos = {
        'expediente_id': expediente_id,
        'clase': 'Activo Resuelto',
        'fecha_estado': date.today() - timedelta(days=10),
        'auto_anotacion': 'Prueba de estado',
        'observaciones': 'Estado de prueba'
    }

    cols = [c for c in datos if c in columnas]
    vals = [datos[c] for c in cols]
    placeholders = ['%s'] * len(cols)

    cursor.execute(
        f"INSERT INTO estados ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING id",
        tuple(vals)
    )
    return cursor.fetchone()[0]


def verificar_expediente(cursor, expediente_id):
    cursor.execute(
        "SELECT estado, turno FROM expediente WHERE id = %s",
        (expediente_id,)
    )
    return cursor.fetchone()


def limpiar_expediente(cursor, expediente_id):
    cursor.execute("DELETE FROM estados WHERE expediente_id = %s", (expediente_id,))
    cursor.execute("DELETE FROM ingresos WHERE expediente_id = %s", (expediente_id,))
    cursor.execute("DELETE FROM expediente WHERE id = %s", (expediente_id,))


def prueba_eliminar_ingreso_recalcula_turno():
    from modelo.configBd import obtener_conexion
    from utils.turnos import sincronizar_estados_y_turnos

    logger.info("=== INICIO prueba_eliminar_ingreso_recalcula_turno ===")
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        expediente_cols = obtener_columnas(cursor, 'expediente')
        ingresos_cols = obtener_columnas(cursor, 'ingresos')
        estados_cols = obtener_columnas(cursor, 'estados')

        expediente_data = {
            'radicado_completo': f'TEST-ELIM-ING-{date.today().strftime("%Y%m%d")}',
            'radicado_corto': f'TEST{date.today().strftime("%Y%m%d")}',
            'estado': 'Activo Pendiente',
            'turno': 1,
            'fecha_ingreso': date.today() - timedelta(days=20)
        }
        expediente_data = {k: v for k, v in expediente_data.items() if k in expediente_cols}

        expediente_id = insertar_expediente(cursor, expediente_data)
        conn.commit()
        logger.info(f"Expediente creado: {expediente_id}")

        if not ingresos_cols:
            raise RuntimeError('La tabla ingresos no existe o no tiene columnas esperadas')

        ingreso_id = insertar_ingreso(cursor, expediente_id, ingresos_cols)
        conn.commit()
        logger.info(f"Ingreso creado: {ingreso_id}")

        resultado = sincronizar_estados_y_turnos(conn)
        cursor.execute("SELECT estado, turno FROM expediente WHERE id = %s", (expediente_id,))
        estado_inicial, turno_inicial = cursor.fetchone()

        logger.info(f"Estado tras sincronización inicial: {estado_inicial}")
        logger.info(f"Turno tras sincronización inicial: {turno_inicial}")

        if estado_inicial != 'Activo Pendiente':
            raise AssertionError(f"Se esperaba estado 'Activo Pendiente' después del insert, se obtuvo '{estado_inicial}'")
        if turno_inicial is None:
            raise AssertionError('Se esperaba turno asignado antes de eliminar el ingreso')

        cursor.execute("DELETE FROM ingresos WHERE id = %s", (ingreso_id,))
        conn.commit()
        logger.info(f"Ingreso eliminado: {ingreso_id}")

        resultado = sincronizar_estados_y_turnos(conn)
        estado_final, turno_final = verificar_expediente(cursor, expediente_id)

        logger.info(f"Estado final tras eliminar ingreso: {estado_final}")
        logger.info(f"Turno final tras eliminar ingreso: {turno_final}")

        if estado_final != 'Sin Movimiento':
            raise AssertionError(f"Se esperaba estado 'Sin Movimiento' tras eliminar ingreso, se obtuvo '{estado_final}'")
        if turno_final is not None:
            raise AssertionError('Se esperaba turno NULL tras eliminar ingreso y sincronizar')

        logger.info('✓ prueba_eliminar_ingreso_recalcula_turno pasó')
        return True

    finally:
        limpiar_expediente(cursor, expediente_id)
        conn.commit()
        cursor.close()
        conn.close()


def prueba_eliminar_estado_recalcula_turno():
    from modelo.configBd import obtener_conexion
    from utils.turnos import sincronizar_estados_y_turnos

    logger.info("=== INICIO prueba_eliminar_estado_recalcula_turno ===")
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        expediente_cols = obtener_columnas(cursor, 'expediente')
        ingresos_cols = obtener_columnas(cursor, 'ingresos')
        estados_cols = obtener_columnas(cursor, 'estados')

        expediente_data = {
            'radicado_completo': f'TEST-ELIM-EST-{date.today().strftime("%Y%m%d")}',
            'radicado_corto': f'TEST{date.today().strftime("%Y%m%d")}',
            'estado': 'Activo Resuelto',
            'turno': 1,
            'fecha_ingreso': date.today() - timedelta(days=40)
        }
        expediente_data = {k: v for k, v in expediente_data.items() if k in expediente_cols}

        expediente_id = insertar_expediente(cursor, expediente_data)
        conn.commit()
        logger.info(f"Expediente creado: {expediente_id}")

        if not estados_cols:
            raise RuntimeError('La tabla estados no existe o no tiene columnas esperadas')

        estado_id = insertar_estado(cursor, expediente_id, estados_cols)
        conn.commit()
        logger.info(f"Estado creado: {estado_id}")

        resultado = sincronizar_estados_y_turnos(conn)
        cursor.execute("SELECT estado, turno FROM expediente WHERE id = %s", (expediente_id,))
        estado_inicial, turno_inicial = cursor.fetchone()

        logger.info(f"Estado tras sincronización inicial: {estado_inicial}")
        logger.info(f"Turno tras sincronización inicial: {turno_inicial}")

        if turno_inicial is not None:
            raise AssertionError('Se esperaba turno NULL en expediente con solo estado al inicio')

        cursor.execute("DELETE FROM estados WHERE id = %s", (estado_id,))
        conn.commit()
        logger.info(f"Estado eliminado: {estado_id}")

        resultado = sincronizar_estados_y_turnos(conn)
        estado_final, turno_final = verificar_expediente(cursor, expediente_id)

        logger.info(f"Estado final tras eliminar estado: {estado_final}")
        logger.info(f"Turno final tras eliminar estado: {turno_final}")

        if estado_final != 'Sin Movimiento':
            raise AssertionError(f"Se esperaba estado 'Sin Movimiento' tras eliminar estado, se obtuvo '{estado_final}'")
        if turno_final is not None:
            raise AssertionError('Se esperaba turno NULL tras eliminar estado y sincronizar')

        logger.info('✓ prueba_eliminar_estado_recalcula_turno pasó')
        return True

    finally:
        limpiar_expediente(cursor, expediente_id)
        conn.commit()
        cursor.close()
        conn.close()


def main():
    tests = [
        prueba_eliminar_ingreso_recalcula_turno,
        prueba_eliminar_estado_recalcula_turno,
    ]

    all_passed = True
    for test_func in tests:
        logger.info(f"\nEjecutando {test_func.__name__}...")
        try:
            if not test_func():
                all_passed = False
        except Exception as exc:
            all_passed = False
            logger.error(f"ERROR en {test_func.__name__}: {exc}")

    if all_passed:
        logger.info('🎉 TODAS LAS pruebas de eliminación de turnos pasaron')
        return 0
    logger.error('❌ ALGUNAS pruebas fallaron')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
