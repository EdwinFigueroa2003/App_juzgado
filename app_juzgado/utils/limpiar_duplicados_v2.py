#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
limpiar_duplicados_v2.py
------------------------
Elimina duplicados en las tablas ingresos, estados y actuaciones,
y al finalizar ejecuta sincronizar_estados_y_turnos para dejar la BD
en un estado completamente coherente.

CRITERIOS DE DUPLICADO
  ingresos   : expediente_id + fecha_ingreso + solicitud
               (se ignora 'observaciones' — puede ser metadata)
  estados    : expediente_id + fecha_estado + clase + auto_anotacion
               (se ignora 'observaciones' — puede ser metadata)
  actuaciones: todos los campos excepto id

PRIORIDAD AL CONSERVAR
  Se conserva el registro con observaciones más informativas:
    1. Observaciones reales (no NULL y no contiene 'desde excel')  ← prioridad alta
    2. Observaciones con 'desde excel'
    3. Observaciones NULL
  En caso de empate, se conserva el de menor id.

USO
  python limpiar_duplicados_v2.py              # interactivo
  python limpiar_duplicados_v2.py --dry-run    # simula sin borrar ni sincronizar
  python limpiar_duplicados_v2.py --auto       # sin confirmación (para scripts)
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.turnos import sincronizar_estados_y_turnos


# ─────────────────────────────────────────────────────────────────────────────
# LIMPIEZA DE TABLAS
# ─────────────────────────────────────────────────────────────────────────────

def limpiar_duplicados_ingresos_v2(conn, dry_run: bool = False) -> int:
    """
    Elimina duplicados en ingresos.
    Campos clave: expediente_id, fecha_ingreso, solicitud
    Se conserva el registro con observaciones más informativas (menor id en empate).
    """
    print("\n📥 LIMPIANDO DUPLICADOS EN INGRESOS...")
    cursor = conn.cursor()
    try:
        # Detectar duplicados
        cursor.execute("""
            WITH ranked AS (
                SELECT
                    id,
                    expediente_id,
                    observaciones,
                    ROW_NUMBER() OVER (
                        PARTITION BY expediente_id, fecha_ingreso, solicitud
                        ORDER BY
                            CASE
                                WHEN observaciones IS NOT NULL
                                 AND LOWER(observaciones) NOT LIKE '%desde excel%'
                                    THEN 1
                                WHEN observaciones IS NOT NULL
                                    THEN 2
                                ELSE 3
                            END,
                            id ASC
                    ) AS rn
                FROM ingresos
            )
            SELECT id, expediente_id, observaciones
            FROM ranked
            WHERE rn > 1
        """)
        resultados = cursor.fetchall()
        ids_a_eliminar = [r[0] for r in resultados]

        print(f"   Duplicados encontrados: {len(ids_a_eliminar)}")

        if ids_a_eliminar:
            print("   📋 Ejemplos (primeros 5):")
            for id_dup, exp_id, obs in resultados[:5]:
                obs_preview = (obs[:60] + '...') if obs and len(obs) > 60 else (obs or 'NULL')
                print(f"      ID {id_dup} — expediente {exp_id} — obs: {obs_preview}")
            if len(resultados) > 5:
                print(f"      ... y {len(resultados) - 5} más")

            if not dry_run:
                lotes = [ids_a_eliminar[i:i+1000] for i in range(0, len(ids_a_eliminar), 1000)]
                total = 0
                for idx, lote in enumerate(lotes, 1):
                    ph = ','.join(['%s'] * len(lote))
                    cursor.execute(f"DELETE FROM ingresos WHERE id IN ({ph})", lote)
                    total += cursor.rowcount
                    print(f"   Lote {idx}/{len(lotes)}: {cursor.rowcount} eliminados")
                conn.commit()
                print(f"   ✅ Total eliminados: {total}")
                return total
            else:
                print("   🔍 DRY-RUN — no se eliminó nada")
                return len(ids_a_eliminar)
        else:
            print("   ✅ Sin duplicados")
            return 0

    except Exception as e:
        conn.rollback()
        print(f"   ❌ Error: {e}")
        return 0
    finally:
        cursor.close()


def limpiar_duplicados_estados_v2(conn, dry_run: bool = False) -> int:
    """
    Elimina duplicados en estados.
    Campos clave: expediente_id, fecha_estado, clase, auto_anotacion
    Se conserva el registro con observaciones más informativas (menor id en empate).
    """
    print("\n📤 LIMPIANDO DUPLICADOS EN ESTADOS...")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            WITH ranked AS (
                SELECT
                    id,
                    expediente_id,
                    observaciones,
                    ROW_NUMBER() OVER (
                        PARTITION BY expediente_id, fecha_estado, clase, auto_anotacion
                        ORDER BY
                            CASE
                                WHEN observaciones IS NOT NULL
                                 AND LOWER(observaciones) NOT LIKE '%desde excel%'
                                    THEN 1
                                WHEN observaciones IS NOT NULL
                                    THEN 2
                                ELSE 3
                            END,
                            id ASC
                    ) AS rn
                FROM estados
            )
            SELECT id, expediente_id, observaciones
            FROM ranked
            WHERE rn > 1
        """)
        resultados = cursor.fetchall()
        ids_a_eliminar = [r[0] for r in resultados]

        print(f"   Duplicados encontrados: {len(ids_a_eliminar)}")

        if ids_a_eliminar:
            print("   📋 Ejemplos (primeros 5):")
            for id_dup, exp_id, obs in resultados[:5]:
                obs_preview = (obs[:60] + '...') if obs and len(obs) > 60 else (obs or 'NULL')
                print(f"      ID {id_dup} — expediente {exp_id} — obs: {obs_preview}")
            if len(resultados) > 5:
                print(f"      ... y {len(resultados) - 5} más")

            if not dry_run:
                lotes = [ids_a_eliminar[i:i+1000] for i in range(0, len(ids_a_eliminar), 1000)]
                total = 0
                for idx, lote in enumerate(lotes, 1):
                    ph = ','.join(['%s'] * len(lote))
                    cursor.execute(f"DELETE FROM estados WHERE id IN ({ph})", lote)
                    total += cursor.rowcount
                    print(f"   Lote {idx}/{len(lotes)}: {cursor.rowcount} eliminados")
                conn.commit()
                print(f"   ✅ Total eliminados: {total}")
                return total
            else:
                print("   🔍 DRY-RUN — no se eliminó nada")
                return len(ids_a_eliminar)
        else:
            print("   ✅ Sin duplicados")
            return 0

    except Exception as e:
        conn.rollback()
        print(f"   ❌ Error: {e}")
        return 0
    finally:
        cursor.close()


def limpiar_duplicados_actuaciones_v2(conn, dry_run: bool = False) -> int:
    """
    Elimina duplicados exactos en actuaciones (todos los campos excepto id).
    """
    print("\n📋 LIMPIANDO DUPLICADOS EN ACTUACIONES...")
    cursor = conn.cursor()
    try:
        # Obtener columnas dinámicamente
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'actuaciones'
            ORDER BY ordinal_position
        """)
        columnas = [r[0] for r in cursor.fetchall() if r[0] != 'id']
        partition_cols = ', '.join(columnas)
        print(f"   Campos clave: {partition_cols}")

        cursor.execute(f"""
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY {partition_cols}
                        ORDER BY id ASC
                    ) AS rn
                FROM actuaciones
            )
            SELECT id FROM ranked WHERE rn > 1
        """)
        ids_a_eliminar = [r[0] for r in cursor.fetchall()]

        print(f"   Duplicados encontrados: {len(ids_a_eliminar)}")

        if ids_a_eliminar:
            if not dry_run:
                lotes = [ids_a_eliminar[i:i+1000] for i in range(0, len(ids_a_eliminar), 1000)]
                total = 0
                for idx, lote in enumerate(lotes, 1):
                    ph = ','.join(['%s'] * len(lote))
                    cursor.execute(f"DELETE FROM actuaciones WHERE id IN ({ph})", lote)
                    total += cursor.rowcount
                    print(f"   Lote {idx}/{len(lotes)}: {cursor.rowcount} eliminados")
                conn.commit()
                print(f"   ✅ Total eliminados: {total}")
                return total
            else:
                print("   🔍 DRY-RUN — no se eliminó nada")
                return len(ids_a_eliminar)
        else:
            print("   ✅ Sin duplicados")
            return 0

    except Exception as e:
        conn.rollback()
        print(f"   ❌ Error: {e}")
        return 0
    finally:
        cursor.close()


# ─────────────────────────────────────────────────────────────────────────────
# ESTADÍSTICAS
# ─────────────────────────────────────────────────────────────────────────────

def obtener_estadisticas(conn):
    print("\n📊 ESTADÍSTICAS FINALES...")
    cursor = conn.cursor()
    try:
        for tabla in ('expediente', 'ingresos', 'estados', 'actuaciones'):
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            total = cursor.fetchone()[0]
            print(f"   {tabla}: {total:,} registros")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    finally:
        cursor.close()
 

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Limpia duplicados en ingresos, estados y actuaciones, '
                    'luego sincroniza estados y turnos.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python limpiar_duplicados_v2.py              # interactivo
  python limpiar_duplicados_v2.py --dry-run    # simula sin modificar nada
  python limpiar_duplicados_v2.py --auto       # sin confirmación
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula la ejecución sin eliminar ni sincronizar')
    parser.add_argument('--auto', action='store_true',
                        help='Ejecuta sin pedir confirmación')
    args = parser.parse_args()

    modo = 'DRY-RUN' if args.dry_run else 'PRODUCCIÓN'

    print("\n" + "=" * 70)
    print(f"🧹 LIMPIEZA DE DUPLICADOS V2 — {modo}")
    print("=" * 70)
    print()
    print("  Tabla ingresos   → clave: expediente_id + fecha_ingreso + solicitud")
    print("  Tabla estados    → clave: expediente_id + fecha_estado + clase + auto_anotacion")
    print("  Tabla actuaciones→ clave: todos los campos excepto id")
    print()
    print("  Se conserva el registro con observaciones más informativas.")
    print("  Al finalizar se ejecuta sincronizar_estados_y_turnos.")

    if not args.auto and not args.dry_run:
        respuesta = input("\n¿Continuar? (s/n): ").strip().lower()
        if respuesta not in ('s', 'si', 'y', 'yes'):
            print("❌ Cancelado")
            return

    inicio = datetime.now()
    conn = obtener_conexion()

    try:
        # ── Limpieza ──────────────────────────────────────────────────────────
        eli_ingresos    = limpiar_duplicados_ingresos_v2(conn, dry_run=args.dry_run)
        eli_estados     = limpiar_duplicados_estados_v2(conn, dry_run=args.dry_run)
        eli_actuaciones = limpiar_duplicados_actuaciones_v2(conn, dry_run=args.dry_run)

        # ── Sincronización final ──────────────────────────────────────────────
        if not args.dry_run:
            print("\n🔄 SINCRONIZANDO ESTADOS Y TURNOS...")
            try:
                resultado_sync = sincronizar_estados_y_turnos(conn)
                print(f"   ✅ Estados actualizados : {resultado_sync['estados_actualizados']}")
                print(f"   ✅ Turnos asignados     : {resultado_sync['turnos_asignados']}")
                if resultado_sync['sin_turno_pendientes']:
                    print(f"   ⚠️  Pendientes sin turno: {resultado_sync['sin_turno_pendientes']}")
            except Exception as e:
                print(f"   ❌ Error en sincronización: {e}")
        else:
            print("\n🔍 DRY-RUN — sincronización omitida")

        # ── Estadísticas ──────────────────────────────────────────────────────
        obtener_estadisticas(conn)

    finally:
        conn.close()

    duracion = (datetime.now() - inicio).total_seconds()
    total = eli_ingresos + eli_estados + eli_actuaciones

    print("\n" + "=" * 70)
    print(f"✅ LIMPIEZA {'SIMULADA' if args.dry_run else 'COMPLETADA'}")
    print("=" * 70)
    print(f"   Ingresos eliminados    : {eli_ingresos:,}")
    print(f"   Estados eliminados     : {eli_estados:,}")
    print(f"   Actuaciones eliminadas : {eli_actuaciones:,}")
    print(f"   TOTAL                  : {total:,}")
    print(f"   Tiempo                 : {duracion:.2f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
