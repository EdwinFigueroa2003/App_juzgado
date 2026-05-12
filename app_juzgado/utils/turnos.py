#!/usr/bin/env python3
"""
turnos.py — Lógica central y única de asignación de turnos y estados.

REGLAS DE NEGOCIO
-----------------
Estado:
  - Activo Pendiente  : MAX(fecha_ingreso) > MAX(fecha_estado), o solo ingresos sin estados
  - Activo Resuelto   : MAX(fecha_estado) >= MAX(fecha_ingreso) y <= 730 días desde hoy
  - Inactivo Resuelto : MAX(fecha_estado) >= MAX(fecha_ingreso) y > 730 días desde hoy
  - Pendiente         : sin ingresos ni estados

Turno:
  - Solo expedientes con estado = 'Activo Pendiente' reciben turno.
  - La fecha de referencia es el ingreso ACTIVO más antiguo sin estado posterior
    (MIN de fecha_ingreso de la tabla `ingresos` donde no existe estado con
     fecha_estado > fecha_ingreso para ese expediente).
  - Si todos los ingresos tienen estado posterior, se usa MIN(fecha_ingreso) como
    fallback, y si no hay ingresos, se usa expediente.fecha_ingreso.
  - Los turnos son enteros consecutivos desde 1, ordenados ASC por esa fecha.
  - Idempotente: ejecutar N veces produce el mismo resultado.
  - Expedientes en cualquier otro estado quedan con turno = NULL.

USO COMO MÓDULO
---------------
    from utils.turnos import sincronizar_estados_y_turnos
    conn = obtener_conexion()
    resultado = sincronizar_estados_y_turnos(conn)
    conn.close()

USO COMO SCRIPT
---------------
    python app_juzgado/utils/turnos.py              # producción
    python app_juzgado/utils/turnos.py --dry-run    # simular sin guardar
    python app_juzgado/utils/turnos.py --verbose    # ver cada turno asignado

"""

import sys
import os
import logging
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN CENTRAL — única fuente
# ─────────────────────────────────────────────────────────────────────────────

def sincronizar_estados_y_turnos(conn, dry_run: bool = False, verbose: bool = False) -> dict:
    """
    Recalcula estados y turnos de TODOS los expedientes en una sola transacción.

    Parámetros
    ----------
    conn     : conexión psycopg2 activa (sin autocommit)
    dry_run  : si True, ejecuta todo pero hace ROLLBACK al final
    verbose  : si True, loguea detalles de cada expediente procesado

    Retorna
    -------
    dict con claves:
        estados_actualizados  : int
        turnos_asignados      : int
    """
    cursor = conn.cursor()
    try:
        logger.info("🔄 [SYNC] Iniciando sincronización global de estados y turnos...")

        # ── PASO 1: ACTUALIZAR ESTADOS ────────────────────────────────────────
        # Un solo UPDATE que recalcula el campo `estado` comparando
        # Solo recalcula expedientes que tienen filas en ingresos o en estados.
        # Si no tienen ninguna de las dos, el estado se preserva tal como está.
        # expediente.fecha_ingreso NO se usa — puede generar confusiones.
        cursor.execute("""
            UPDATE expediente e
            SET estado = calc.estado_nuevo
            FROM (
                SELECT
                    exp.id,
                    CASE
                        -- Solo ingresos, sin estados → Activo Pendiente
                        WHEN COALESCE(ing.cnt, 0) > 0 AND COALESCE(est.cnt, 0) = 0
                            THEN 'Activo Pendiente'

                        -- Solo estados, sin ingresos → por antigüedad
                        WHEN COALESCE(est.cnt, 0) > 0 AND COALESCE(ing.cnt, 0) = 0
                            THEN CASE
                                WHEN (CURRENT_DATE - est.ultima_fecha) <= 730
                                    THEN 'Activo Resuelto'
                                ELSE 'Inactivo Resuelto'
                            END

                        -- Tiene ambos → comparar fechas
                        WHEN COALESCE(ing.cnt, 0) > 0 AND COALESCE(est.cnt, 0) > 0
                            THEN CASE
                                WHEN ing.ultima_fecha > est.ultima_fecha
                                    THEN 'Activo Pendiente'
                                WHEN (CURRENT_DATE - est.ultima_fecha) <= 730
                                    THEN 'Activo Resuelto'
                                ELSE 'Inactivo Resuelto'
                            END

                        -- Sin filas en ninguna tabla → no debería llegar aquí
                        -- por el WHERE de abajo, pero por seguridad
                        ELSE e.estado
                    END AS estado_nuevo
                FROM expediente exp
                LEFT JOIN (
                    SELECT expediente_id,
                           COUNT(*)           AS cnt,
                           MAX(fecha_ingreso) AS ultima_fecha
                    FROM ingresos
                    WHERE fecha_ingreso IS NOT NULL
                    GROUP BY expediente_id
                ) ing ON ing.expediente_id = exp.id
                LEFT JOIN (
                    SELECT expediente_id,
                           COUNT(*)          AS cnt,
                           MAX(fecha_estado) AS ultima_fecha
                    FROM estados
                    WHERE fecha_estado IS NOT NULL
                    GROUP BY expediente_id
                ) est ON est.expediente_id = exp.id
                -- Solo procesar expedientes con datos reales en las tablas relacionadas
                WHERE COALESCE(ing.cnt, 0) > 0
                   OR COALESCE(est.cnt, 0) > 0
            ) calc
            WHERE e.id = calc.id
              AND (e.estado IS DISTINCT FROM calc.estado_nuevo)
        """)
        estados_actualizados = cursor.rowcount
        logger.info(f"✅ [SYNC] Paso 1 — Estados actualizados: {estados_actualizados}")

        # ── PASO 2: LIMPIAR TURNOS ────────────────────────────────────────────
        # Quitar turno a cualquier expediente que ya no sea Activo Pendiente.
        cursor.execute("""
            UPDATE expediente
            SET turno = NULL
            WHERE estado != 'Activo Pendiente'
              AND turno IS NOT NULL
        """)
        logger.info(f"🧹 [SYNC] Paso 2 — Turnos limpiados en no-pendientes: {cursor.rowcount}")

        # Resetear todos los turnos de Activo Pendiente para reasignar desde cero.
        cursor.execute("""
            UPDATE expediente
            SET turno = NULL
            WHERE estado = 'Activo Pendiente'
        """)
        logger.info("🧹 [SYNC] Paso 2 — Turnos de Activo Pendiente reseteados")

        # ── PASO 3: CALCULAR ORDEN Y ASIGNAR TURNOS ──────────────────────────
        # Fecha de referencia por expediente:
        #   1. MIN(fecha_ingreso) de ingresos SIN estado posterior  ← prioritario
        #   2. MIN(fecha_ingreso) de todos los ingresos             ← fallback
        #   3. expediente.fecha_ingreso                             ← último recurso
        # Orden final: fecha_ref ASC, expediente.fecha_ingreso ASC, id ASC
        cursor.execute("""
            WITH ingresos_exp AS (
                SELECT expediente_id, fecha_ingreso
                FROM ingresos
                WHERE fecha_ingreso IS NOT NULL
            ),
            ingresos_sin_salida AS (
                -- Ingresos que NO tienen ningún estado con fecha_estado > fecha_ingreso
                SELECT ie.expediente_id, ie.fecha_ingreso
                FROM ingresos_exp ie
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM estados est
                    WHERE est.expediente_id = ie.expediente_id
                      AND est.fecha_estado > ie.fecha_ingreso
                )
            ),
            fecha_activa AS (
                -- Ingreso activo más antiguo sin salida
                SELECT expediente_id, MIN(fecha_ingreso) AS fecha_ref
                FROM ingresos_sin_salida
                GROUP BY expediente_id
            ),
            fecha_fallback AS (
                -- Fallback: ingreso más antiguo de todos
                SELECT expediente_id, MIN(fecha_ingreso) AS fecha_ref
                FROM ingresos_exp
                GROUP BY expediente_id
            )
            SELECT e.id
            FROM expediente e
            LEFT JOIN fecha_activa  fa  ON fa.expediente_id  = e.id
            LEFT JOIN fecha_fallback fb ON fb.expediente_id  = e.id
            WHERE e.estado = 'Activo Pendiente'
            ORDER BY
                COALESCE(fa.fecha_ref, fb.fecha_ref, e.fecha_ingreso) ASC NULLS LAST,
                e.fecha_ingreso ASC NULLS LAST,
                e.id ASC
        """)

        expedientes_ordenados = cursor.fetchall()
        turnos_asignados = len(expedientes_ordenados)

        for turno_num, (exp_id,) in enumerate(expedientes_ordenados, 1):
            cursor.execute(
                "UPDATE expediente SET turno = %s WHERE id = %s",
                (turno_num, exp_id)
            )
            if verbose:
                logger.info(f"   Turno {turno_num} → expediente id={exp_id}")

        logger.info(f"✅ [SYNC] Paso 3 — Turnos asignados: {turnos_asignados}")

        # ── VERIFICACIÓN: no deben quedar Activo Pendiente sin turno ─────────
        cursor.execute("""
            SELECT COUNT(*) FROM expediente
            WHERE estado = 'Activo Pendiente' AND turno IS NULL
        """)
        sin_turno = cursor.fetchone()[0]
        if sin_turno:
            logger.warning(f"⚠️  [SYNC] {sin_turno} expedientes 'Activo Pendiente' quedaron sin turno")
        else:
            logger.info("✅ [SYNC] Verificación OK — ningún 'Activo Pendiente' sin turno")

        if dry_run:
            conn.rollback()
            logger.info("🔍 [SYNC] DRY-RUN — cambios revertidos, ninguna modificación guardada")
        else:
            conn.commit()
            logger.info("💾 [SYNC] Cambios guardados en la base de datos")

        return {
            'estados_actualizados': estados_actualizados,
            'turnos_asignados': turnos_asignados,
            'sin_turno_pendientes': sin_turno,
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ [SYNC] Error — se hizo ROLLBACK: {e}")
        raise
    finally:
        cursor.close()


# ─────────────────────────────────────────────────────────────────────────────
# EJECUCIÓN COMO SCRIPT
# ─────────────────────────────────────────────────────────────────────────────

def _configurar_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(os.path.dirname(__file__), '..', 'logs', 'turnos.log'),
                encoding='utf-8'
            ),
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description='Sincroniza estados y turnos de todos los expedientes.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python turnos.py                  # Ejecutar en producción
  python turnos.py --dry-run        # Simular sin guardar cambios
  python turnos.py --verbose        # Ver detalle de cada turno asignado
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula la ejecución sin guardar cambios')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Muestra detalle de cada expediente procesado')
    args = parser.parse_args()

    _configurar_logging(args.verbose)

    modo = 'DRY-RUN' if args.dry_run else 'PRODUCCIÓN'
    logger.info(f"{'='*60}")
    logger.info(f"  SINCRONIZACIÓN DE ESTADOS Y TURNOS — {modo}")
    logger.info(f"{'='*60}")

    conn = obtener_conexion()
    try:
        resultado = sincronizar_estados_y_turnos(conn, dry_run=args.dry_run, verbose=args.verbose)
    finally:
        conn.close()

    logger.info(f"{'='*60}")
    logger.info(f"  RESUMEN")
    logger.info(f"  Estados actualizados : {resultado['estados_actualizados']}")
    logger.info(f"  Turnos asignados     : {resultado['turnos_asignados']}")
    logger.info(f"  Pendientes sin turno : {resultado['sin_turno_pendientes']}")
    logger.info(f"{'='*60}")

    if resultado['sin_turno_pendientes'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
