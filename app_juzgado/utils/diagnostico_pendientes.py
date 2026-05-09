#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico_pendientes.py
--------------------------
Escanea todos los expedientes con estado = 'Pendiente' y los clasifica en:

  GRUPO A — Tienen ingresos o estados pero el campo `estado` dice 'Pendiente'
             → Deberían ser Activo Pendiente / Activo Resuelto / Inactivo Resuelto
             → Son candidatos a corregir con sincronizar_estados_y_turnos

  GRUPO B — No tienen ningún movimiento (ni ingresos ni estados)
             → Estado 'Pendiente' es correcto según las reglas de negocio
             → Pueden ser expedientes vacíos / cargados sin datos relacionados

Genera un reporte en consola y opcionalmente exporta a Excel.

USO
  python diagnostico_pendientes.py                    # solo consola
  python diagnostico_pendientes.py --excel            # exporta a Excel
  python diagnostico_pendientes.py --corregir         # aplica sincronización al final
  python diagnostico_pendientes.py --excel --corregir # todo junto
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNÓSTICO
# ─────────────────────────────────────────────────────────────────────────────

def escanear_pendientes(conn) -> dict:
    """
    Consulta todos los expedientes con estado = 'Pendiente' y los clasifica.

    Retorna dict con:
        total_pendientes : int
        con_movimiento   : list[dict]   — Grupo A
        sin_movimiento   : list[dict]   — Grupo B
    """
    cursor = conn.cursor()
    try:
        # ── Totales rápidos ───────────────────────────────────────────────────
        cursor.execute("SELECT COUNT(*) FROM expediente WHERE estado = 'Sin Movimiento'")
        total_pendientes = cursor.fetchone()[0]

        if total_pendientes == 0:
            return {'total_pendientes': 0, 'con_movimiento': [], 'sin_movimiento': []}

        # ── Consulta principal ────────────────────────────────────────────────
        # Para cada expediente Pendiente, cuenta ingresos y estados
        cursor.execute("""
            SELECT
                e.id,
                e.radicado_completo,
                e.radicado_corto,
                e.demandante,
                e.demandado,
                e.fecha_ingreso,
                COALESCE(ing.cnt, 0)          AS total_ingresos,
                COALESCE(est.cnt, 0)          AS total_estados,
                ing.primera_fecha_ingreso,
                ing.ultima_fecha_ingreso,
                est.primera_fecha_estado,
                est.ultima_fecha_estado,
                -- Estado que DEBERÍA tener según reglas de negocio
                CASE
                    WHEN COALESCE(ing.cnt,0) > 0 AND COALESCE(est.cnt,0) = 0
                        THEN 'Activo Pendiente'
                    WHEN COALESCE(est.cnt,0) > 0 AND COALESCE(ing.cnt,0) = 0
                        THEN CASE
                            WHEN (CURRENT_DATE - est.ultima_fecha_estado) <= 730
                                THEN 'Activo Resuelto'
                            ELSE 'Inactivo Resuelto'
                        END
                    WHEN COALESCE(ing.cnt,0) > 0 AND COALESCE(est.cnt,0) > 0
                        THEN CASE
                            WHEN ing.ultima_fecha_ingreso > est.ultima_fecha_estado
                                THEN 'Activo Pendiente'
                            WHEN (CURRENT_DATE - est.ultima_fecha_estado) <= 730
                                THEN 'Activo Resuelto'
                            ELSE 'Inactivo Resuelto'
                        END
                    ELSE 'Sin Movimiento'
                END AS estado_correcto
            FROM expediente e
            LEFT JOIN (
                SELECT
                    expediente_id,
                    COUNT(*)           AS cnt,
                    MIN(fecha_ingreso) AS primera_fecha_ingreso,
                    MAX(fecha_ingreso) AS ultima_fecha_ingreso
                FROM ingresos
                WHERE fecha_ingreso IS NOT NULL
                GROUP BY expediente_id
            ) ing ON ing.expediente_id = e.id
            LEFT JOIN (
                SELECT
                    expediente_id,
                    COUNT(*)          AS cnt,
                    MIN(fecha_estado) AS primera_fecha_estado,
                    MAX(fecha_estado) AS ultima_fecha_estado
                FROM estados
                WHERE fecha_estado IS NOT NULL
                GROUP BY expediente_id
            ) est ON est.expediente_id = e.id
            WHERE e.estado = 'Sin Movimiento'
            ORDER BY
                -- Primero los que tienen movimiento
                (COALESCE(ing.cnt,0) + COALESCE(est.cnt,0)) DESC,
                e.fecha_ingreso ASC NULLS LAST,
                e.id ASC
        """)

        filas = cursor.fetchall()

        con_movimiento = []
        sin_movimiento = []

        for row in filas:
            (exp_id, radicado_completo, radicado_corto, demandante, demandado,
             fecha_ingreso, total_ingresos, total_estados,
             primera_fi, ultima_fi, primera_fe, ultima_fe,
             estado_correcto) = row

            registro = {
                'id':                  exp_id,
                'radicado_completo':   radicado_completo or '—',
                'radicado_corto':      radicado_corto or '—',
                'demandante':          demandante or '—',
                'demandado':           demandado or '—',
                'fecha_ingreso_exp':   fecha_ingreso,
                'total_ingresos':      total_ingresos,
                'total_estados':       total_estados,
                'primera_fecha_ingreso': primera_fi,
                'ultima_fecha_ingreso':  ultima_fi,
                'primera_fecha_estado':  primera_fe,
                'ultima_fecha_estado':   ultima_fe,
                'estado_correcto':     estado_correcto,
            }

            if total_ingresos > 0 or total_estados > 0:
                con_movimiento.append(registro)
            else:
                sin_movimiento.append(registro)

        return {
            'total_pendientes': total_pendientes,
            'con_movimiento':   con_movimiento,
            'sin_movimiento':   sin_movimiento,
        }

    finally:
        cursor.close()


# ─────────────────────────────────────────────────────────────────────────────
# REPORTE EN CONSOLA
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(fecha):
    if fecha is None:
        return '—'
    if hasattr(fecha, 'strftime'):
        return fecha.strftime('%d/%m/%Y')
    return str(fecha)


def imprimir_reporte(resultado: dict):
    total     = resultado['total_pendientes']
    grupo_a   = resultado['con_movimiento']
    grupo_b   = resultado['sin_movimiento']

    print("\n" + "=" * 80)
    print("  DIAGNÓSTICO DE EXPEDIENTES EN ESTADO 'Sin Movimiento'")
    print("=" * 80)
    print(f"  Total expedientes Sin Movimiento : {total:,}")
    print(f"  Grupo A — con movimiento    : {len(grupo_a):,}  (estado incorrecto → se puede corregir)")
    print(f"  Grupo B — Sin Movimiento    : {len(grupo_b):,}  (estado correcto → sin datos relacionados)")
    print("=" * 80)

    # ── Grupo A ───────────────────────────────────────────────────────────────
    if grupo_a:
        print(f"\n{'─'*80}")
        print(f"  GRUPO A — {len(grupo_a)} expedientes con movimiento pero estado = 'Sin Movimiento'")
        print(f"  Estos deberían tener otro estado. Ejecuta --corregir para arreglarlos.")
        print(f"{'─'*80}")

        # Resumen por estado correcto
        from collections import Counter
        conteo = Counter(r['estado_correcto'] for r in grupo_a)
        print("\n  Distribución de estado correcto:")
        for estado, cnt in sorted(conteo.items(), key=lambda x: -x[1]):
            print(f"    {estado:<25} : {cnt:,}")

        print(f"\n  Primeros 20 registros:")
        print(f"  {'Radicado':<25} {'Ingresos':>8} {'Estados':>7} {'Últ.Ingreso':>12} {'Últ.Estado':>12} {'Estado correcto'}")
        print(f"  {'─'*25} {'─'*8} {'─'*7} {'─'*12} {'─'*12} {'─'*20}")
        for r in grupo_a[:20]:
            rad = (r['radicado_completo'][:23] + '..') if len(r['radicado_completo']) > 25 else r['radicado_completo']
            print(f"  {rad:<25} {r['total_ingresos']:>8} {r['total_estados']:>7} "
                  f"{_fmt(r['ultima_fecha_ingreso']):>12} {_fmt(r['ultima_fecha_estado']):>12} "
                  f"  {r['estado_correcto']}")
        if len(grupo_a) > 20:
            print(f"  ... y {len(grupo_a) - 20} más (ver Excel con --excel)")

    # ── Grupo B ───────────────────────────────────────────────────────────────
    if grupo_b:
        print(f"\n{'─'*80}")
        print(f"  GRUPO B — {len(grupo_b)} expedientes sin ningún movimiento")
        print(f"  Estado 'Sin Movimiento' es correcto. Revisar si tienen datos o se pueden archivar.")
        print(f"{'─'*80}")
        print(f"\n  Primeros 20 registros:")
        print(f"  {'Radicado':<25} {'Demandante':<30} {'Fecha ingreso exp.'}")
        print(f"  {'─'*25} {'─'*30} {'─'*18}")
        for r in grupo_b[:20]:
            rad = (r['radicado_completo'][:23] + '..') if len(r['radicado_completo']) > 25 else r['radicado_completo']
            dem = (r['demandante'][:28] + '..') if len(r['demandante']) > 30 else r['demandante']
            print(f"  {rad:<25} {dem:<30} {_fmt(r['fecha_ingreso_exp'])}")
        if len(grupo_b) > 20:
            print(f"  ... y {len(grupo_b) - 20} más (ver Excel con --excel)")

    print()


# ─────────────────────────────────────────────────────────────────────────────
# EXPORTAR A EXCEL
# ─────────────────────────────────────────────────────────────────────────────

def exportar_excel(resultado: dict) -> str:
    try:
        import pandas as pd
    except ImportError:
        print("❌ pandas no disponible — no se puede exportar a Excel")
        return ''

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre = os.path.join(
        os.path.dirname(__file__), '..', 'Archivos',
        f'diagnostico_pendientes_{timestamp}.xlsx'
    )

    def _lista_a_df(lista):
        if not lista:
            return pd.DataFrame()
        rows = []
        for r in lista:
            rows.append({
                'ID':                    r['id'],
                'Radicado Completo':     r['radicado_completo'],
                'Radicado Corto':        r['radicado_corto'],
                'Demandante':            r['demandante'],
                'Demandado':             r['demandado'],
                'Fecha Ingreso Exp.':    _fmt(r['fecha_ingreso_exp']),
                'Total Ingresos':        r['total_ingresos'],
                'Total Estados':         r['total_estados'],
                'Primera Fecha Ingreso': _fmt(r['primera_fecha_ingreso']),
                'Última Fecha Ingreso':  _fmt(r['ultima_fecha_ingreso']),
                'Primera Fecha Estado':  _fmt(r['primera_fecha_estado']),
                'Última Fecha Estado':   _fmt(r['ultima_fecha_estado']),
                'Estado Correcto':       r['estado_correcto'],
            })
        return pd.DataFrame(rows)

    df_a = _lista_a_df(resultado['con_movimiento'])
    df_b = _lista_a_df(resultado['sin_movimiento'])

    with pd.ExcelWriter(nombre, engine='openpyxl') as writer:
        if not df_a.empty:
            df_a.to_excel(writer, sheet_name='A - Con movimiento', index=False)
        if not df_b.empty:
            df_b.to_excel(writer, sheet_name='B - Sin Movimiento', index=False)

        # Hoja resumen
        resumen = pd.DataFrame([
            {'Grupo': 'A — Con movimiento (estado incorrecto)', 'Cantidad': len(resultado['con_movimiento'])},
            {'Grupo': 'B — Sin Movimiento (estado correcto)',   'Cantidad': len(resultado['sin_movimiento'])},
            {'Grupo': 'TOTAL Sin Movimiento',                        'Cantidad': resultado['total_pendientes']},
        ])
        resumen.to_excel(writer, sheet_name='Resumen', index=False)

    print(f"\n📊 Excel exportado: {os.path.abspath(nombre)}")
    return nombre


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICACIÓN CONTRA ARCHIVOS EXCEL DE REFERENCIA
# ─────────────────────────────────────────────────────────────────────────────

# Rutas por defecto de los archivos de referencia (relativas a este script)
_BASE = os.path.join(os.path.dirname(__file__), '..', 'Archivos')
ARCHIVO_INGRESOS  = os.path.join(_BASE, 'Otros', 'ingresos_al_despacho_act.xlsx')
ARCHIVO_LISTADO   = os.path.join(_BASE, 'Listado_Final_Cruzado_20251105_161151.xlsx')


def _normalizar_radicado(valor) -> str:
    """Deja solo dígitos, retorna '' si no hay nada."""
    if valor is None:
        return ''
    return ''.join(c for c in str(valor) if c.isdigit())


def _cargar_radicados_excel(ruta: str) -> tuple[set, set, list]:
    """
    Lee un archivo Excel y devuelve:
      - radicados_completos : set de radicados de 23 dígitos encontrados
      - radicados_cortos    : set de radicados cortos (< 23 dígitos)
      - filas               : lista de dicts con los datos crudos
    """
    import pandas as pd

    radicados_completos = set()
    radicados_cortos    = set()
    filas               = []

    # Columnas candidatas para radicado completo
    cols_completo = ['RADICADO COMPLETO', 'radicado_completo', 'RadicadoUnicoLimpio',
                     'RADICADO_MODIFICADO_OFI']
    # Columnas candidatas para radicado corto
    cols_corto    = ['RADICADO', 'radicado_corto', 'RadicadoCorto', 'RADICADO MODIFICADO']

    xl = pd.ExcelFile(ruta)
    for hoja in xl.sheet_names:
        df = pd.read_excel(ruta, sheet_name=hoja)
        df.columns = [str(c).strip() for c in df.columns]

        col_c = next((c for c in cols_completo if c in df.columns), None)
        col_k = next((c for c in cols_corto    if c in df.columns), None)

        for _, row in df.iterrows():
            rad_c = _normalizar_radicado(row[col_c] if col_c else None)
            rad_k = _normalizar_radicado(row[col_k] if col_k else None)

            if rad_c and len(rad_c) >= 20:
                radicados_completos.add(rad_c)
            if rad_k and len(rad_k) < 20 and rad_k:
                radicados_cortos.add(rad_k)

            filas.append({
                'hoja':              hoja,
                'radicado_completo': rad_c or None,
                'radicado_corto':    rad_k or None,
            })

    return radicados_completos, radicados_cortos, filas


def verificar_contra_excels(conn,
                             ruta_ingresos: str = ARCHIVO_INGRESOS,
                             ruta_listado:  str = ARCHIVO_LISTADO) -> dict:
    """
    Cruza los radicados de los archivos Excel de referencia contra la BD y
    reporta para cada radicado del Excel:
      - Si existe en la BD
      - Su estado actual
      - Si tiene ingresos y/o estados registrados

    Retorna dict con:
        fuente_ingresos  : resultados del archivo ingresos_al_despacho_act.xlsx
        fuente_listado   : resultados del archivo Listado_Final_Cruzado
        resumen          : totales por fuente
    """
    import pandas as pd

    cursor = conn.cursor()

    # Cargar todos los radicados de la BD en memoria (rápido)
    cursor.execute("""
        SELECT
            e.id,
            e.radicado_completo,
            e.radicado_corto,
            e.estado,
            COALESCE(ing.cnt, 0) AS total_ingresos,
            COALESCE(est.cnt, 0) AS total_estados
        FROM expediente e
        LEFT JOIN (
            SELECT expediente_id, COUNT(*) AS cnt
            FROM ingresos GROUP BY expediente_id
        ) ing ON ing.expediente_id = e.id
        LEFT JOIN (
            SELECT expediente_id, COUNT(*) AS cnt
            FROM estados GROUP BY expediente_id
        ) est ON est.expediente_id = e.id
    """)
    rows_bd = cursor.fetchall()
    cursor.close()

    # Índices en memoria: radicado_completo → fila, radicado_corto → fila
    idx_completo = {}
    idx_corto    = {}
    for row in rows_bd:
        exp_id, rad_c, rad_k, estado, n_ing, n_est = row
        if rad_c:
            idx_completo[_normalizar_radicado(rad_c)] = row
        if rad_k:
            idx_corto[_normalizar_radicado(rad_k)] = row

    def _cruzar(ruta: str, nombre_fuente: str) -> dict:
        if not os.path.exists(ruta):
            print(f"   ⚠️  Archivo no encontrado: {ruta}")
            return {'nombre': nombre_fuente, 'total_excel': 0,
                    'encontrados': [], 'no_encontrados': []}

        print(f"   Leyendo {nombre_fuente}...")
        rads_c, rads_k, filas = _cargar_radicados_excel(ruta)
        todos_rads = rads_c | {r for r in rads_k if r}

        encontrados    = []
        no_encontrados = []

        for rad in sorted(todos_rads):
            fila_bd = idx_completo.get(rad) or idx_corto.get(rad)

            if fila_bd:
                exp_id, rad_c, rad_k, estado, n_ing, n_est = fila_bd
                encontrados.append({
                    'radicado_excel':    rad,
                    'radicado_bd':       rad_c or rad_k or '—',
                    'estado_actual':     estado or '—',
                    'total_ingresos':    n_ing,
                    'total_estados':     n_est,
                    'tiene_movimiento':  (n_ing + n_est) > 0,
                })
            else:
                no_encontrados.append({
                    'radicado_excel': rad,
                })

        return {
            'nombre':          nombre_fuente,
            'total_excel':     len(todos_rads),
            'encontrados':     encontrados,
            'no_encontrados':  no_encontrados,
        }

    resultado_ingresos = _cruzar(ruta_ingresos, 'ingresos_al_despacho_act.xlsx')
    resultado_listado  = _cruzar(ruta_listado,  'Listado_Final_Cruzado_20251105_161151.xlsx')

    return {
        'fuente_ingresos': resultado_ingresos,
        'fuente_listado':  resultado_listado,
    }


def imprimir_reporte_excels(resultado_excels: dict):
    """Imprime en consola el resultado del cruce contra los archivos Excel."""

    from collections import Counter

    for fuente in (resultado_excels['fuente_ingresos'],
                   resultado_excels['fuente_listado']):

        nombre      = fuente['nombre']
        total       = fuente['total_excel']
        encontrados = fuente['encontrados']
        no_enc      = fuente['no_encontrados']

        if total == 0:
            continue

        print(f"\n{'='*80}")
        print(f"  VERIFICACIÓN: {nombre}")
        print(f"{'='*80}")
        print(f"  Radicados únicos en Excel : {total:,}")
        print(f"  Encontrados en BD         : {len(encontrados):,}")
        print(f"  NO encontrados en BD      : {len(no_enc):,}")

        if encontrados:
            # Distribución por estado actual
            conteo_estado = Counter(r['estado_actual'] for r in encontrados)
            print(f"\n  Distribución por estado actual en BD:")
            for estado, cnt in sorted(conteo_estado.items(), key=lambda x: -x[1]):
                print(f"    {estado:<25} : {cnt:,}")

            # Encontrados Pendiente
            sin_mov = [r for r in encontrados if not r['tiene_movimiento']]
            if sin_mov:
                print(f"\n  ⚠️  Encontrados en BD pero SIN ingresos ni estados: {len(sin_mov):,}")
                print(f"  {'Radicado BD':<25} {'Estado actual':<20}")
                print(f"  {'─'*25} {'─'*20}")
                for r in sin_mov[:15]:
                    print(f"  {r['radicado_bd']:<25} {r['estado_actual']:<20}")
                if len(sin_mov) > 15:
                    print(f"  ... y {len(sin_mov)-15} más")

        if no_enc:
            print(f"\n  ❌ Radicados del Excel NO encontrados en BD: {len(no_enc):,}")
            print(f"  (primeros 15)")
            for r in no_enc[:15]:
                print(f"    {r['radicado_excel']}")
            if len(no_enc) > 15:
                print(f"    ... y {len(no_enc)-15} más")


def exportar_excel_cruce(resultado_excels: dict) -> str:
    """Exporta el resultado del cruce a Excel."""
    try:
        import pandas as pd
    except ImportError:
        print("❌ pandas no disponible")
        return ''

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre = os.path.join(
        os.path.dirname(__file__), '..', 'Archivos',
        f'verificacion_excels_{timestamp}.xlsx'
    )

    with pd.ExcelWriter(nombre, engine='openpyxl') as writer:
        for fuente in (resultado_excels['fuente_ingresos'],
                       resultado_excels['fuente_listado']):
            src = fuente['nombre'][:28]  # límite nombre hoja Excel

            if fuente['encontrados']:
                pd.DataFrame(fuente['encontrados']).to_excel(
                    writer, sheet_name=f'{src[:20]}_encontrados', index=False)

            if fuente['no_encontrados']:
                pd.DataFrame(fuente['no_encontrados']).to_excel(
                    writer, sheet_name=f'{src[:20]}_no_encontrados', index=False)

    print(f"\n📊 Excel de verificación exportado: {os.path.abspath(nombre)}")
    return nombre


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Diagnóstico de expedientes en estado Sin Movimiento.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python diagnostico_pendientes.py
  python diagnostico_pendientes.py --excel
  python diagnostico_pendientes.py --corregir
  python diagnostico_pendientes.py --verificar
  python diagnostico_pendientes.py --verificar --excel
  python diagnostico_pendientes.py --excel --corregir --verificar
        """
    )
    parser.add_argument('--excel',    action='store_true',
                        help='Exporta resultados a Excel')
    parser.add_argument('--corregir', action='store_true',
                        help='Aplica sincronizar_estados_y_turnos al final para corregir el Grupo A')
    parser.add_argument('--verificar', action='store_true',
                        help='Cruza los archivos Excel de referencia contra la BD')
    parser.add_argument('--ingresos-excel', default=ARCHIVO_INGRESOS,
                        help=f'Ruta al archivo ingresos_al_despacho_act.xlsx (default: {ARCHIVO_INGRESOS})')
    parser.add_argument('--listado-excel', default=ARCHIVO_LISTADO,
                        help=f'Ruta al archivo Listado_Final_Cruzado (default: {ARCHIVO_LISTADO})')
    args = parser.parse_args()

    conn = obtener_conexion()
    try:
        # ── Diagnóstico de Pendientes ─────────────────────────────────────────
        print("\n🔍 Escaneando expedientes en estado 'Pendiente'...")
        resultado = escanear_pendientes(conn)

        if resultado['total_pendientes'] == 0:
            print("✅ No hay expedientes en estado 'Pendiente'.")
        else:
            imprimir_reporte(resultado)
            if args.excel:
                exportar_excel(resultado)

        # ── Verificación contra archivos Excel ────────────────────────────────
        if args.verificar:
            print("\n🔍 Verificando radicados de archivos Excel contra la BD...")
            resultado_excels = verificar_contra_excels(
                conn,
                ruta_ingresos=args.ingresos_excel,
                ruta_listado=args.listado_excel,
            )
            imprimir_reporte_excels(resultado_excels)
            if args.excel:
                exportar_excel_cruce(resultado_excels)

        # ── Corrección ────────────────────────────────────────────────────────
        if args.corregir:
            if resultado['total_pendientes'] == 0 or not resultado['con_movimiento']:
                print("\nℹ️  No hay expedientes del Grupo A que corregir.")
            else:
                print(f"\n🔄 Aplicando sincronización para corregir "
                      f"{len(resultado['con_movimiento'])} expedientes del Grupo A...")
                from utils.turnos import sincronizar_estados_y_turnos
                sync = sincronizar_estados_y_turnos(conn)
                print(f"   ✅ Estados actualizados : {sync['estados_actualizados']}")
                print(f"   ✅ Turnos asignados     : {sync['turnos_asignados']}")
                if sync['sin_turno_pendientes']:
                    print(f"   ⚠️  Pendientes sin turno: {sync['sin_turno_pendientes']}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
