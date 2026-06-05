#!/usr/bin/env python3
"""
diagnostico_duplicados_fuzzy.py
--------------------------------
Identifica expedientes que probablemente son el mismo proceso judicial
registrado dos veces, usando similitud de demandante + demandado.

Criterio: primeras N palabras del demandante Y del demandado coinciden
(normalizado: sin tildes, minúsculas). La revisión final la hace el usuario
en el Excel — el script solo agrupa candidatos.

USO
  python diagnostico_duplicados_fuzzy.py
  python diagnostico_duplicados_fuzzy.py --excel
  python diagnostico_duplicados_fuzzy.py --min-palabras 2   # más permisivo
  python diagnostico_duplicados_fuzzy.py --min-palabras 4   # más estricto
"""

import sys, os, re, argparse
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.configBd import obtener_conexion


# ─────────────────────────────────────────────────────────────────────────────

def normalizar(texto: str, n_palabras: int) -> str:
    """Minúsculas, sin tildes, solo letras, primeras n_palabras."""
    if not texto:
        return ''
    t = texto.lower().strip()
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
        t = t.replace(a, b)
    t = re.sub(r'[^a-z\s]', ' ', t)
    palabras = [p for p in t.split() if len(p) > 1]
    return ' '.join(palabras[:n_palabras])


def obtener_expedientes(conn) -> list:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, radicado_completo, radicado_corto,
               demandante, demandado, estado, fecha_ingreso
        FROM expediente
        WHERE demandante IS NOT NULL AND demandante <> ''
          AND demandado  IS NOT NULL AND demandado  <> ''
        ORDER BY id
    """)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def encontrar_grupos(rows: list, n_palabras: int) -> list:
    """
    Agrupa expedientes por (clave_demandante, clave_demandado).
    Devuelve solo grupos con 2+ expedientes, ordenados por tamaño desc.
    """
    por_clave: dict = defaultdict(list)
    for row in rows:
        id_, rad_c, rad_k, dem, dem_do, estado, fi = row
        clave = (normalizar(dem, n_palabras), normalizar(dem_do, n_palabras))
        if clave[0] and clave[1]:
            por_clave[clave].append({
                'id':                id_,
                'radicado_completo': rad_c or '',
                'radicado_corto':    rad_k or '',
                'demandante':        dem,
                'demandado':         dem_do,
                'estado':            estado or '',
                'fecha_ingreso':     fi,
            })

    grupos = [
        {'clave': k, 'expedientes': v}
        for k, v in por_clave.items()
        if len(v) > 1
    ]
    grupos.sort(key=lambda g: len(g['expedientes']), reverse=True)
    return grupos


# ─────────────────────────────────────────────────────────────────────────────

def imprimir_reporte(grupos: list, n_palabras: int):
    total_grupos  = len(grupos)
    total_exp_dup = sum(len(g['expedientes']) for g in grupos)

    print(f"\n{'='*80}")
    print(f"  POSIBLES DUPLICADOS — similitud demandante + demandado")
    print(f"  Palabras clave usadas: {n_palabras}")
    print(f"{'='*80}")
    print(f"  Grupos encontrados   : {total_grupos:,}")
    print(f"  Expedientes afectados: {total_exp_dup:,}")
    print(f"{'='*80}")

    for i, grupo in enumerate(grupos[:30], 1):
        clave_dem, clave_dem_do = grupo['clave']
        print(f"\n  [{i}] dem~'{clave_dem}'  |  dem_do~'{clave_dem_do}'")
        print(f"  {'ID':<8} {'Radicado completo':<26} {'Corto':<16} {'Estado':<20} {'F.Ingreso'}")
        print(f"  {'─'*8} {'─'*26} {'─'*16} {'─'*20} {'─'*12}")
        for exp in grupo['expedientes']:
            fi  = exp['fecha_ingreso'].strftime('%d/%m/%Y') if exp['fecha_ingreso'] else '—'
            rad = (exp['radicado_completo'] or '—')[:24]
            print(f"  {exp['id']:<8} {rad:<26} {exp['radicado_corto']:<16} "
                  f"{exp['estado']:<20} {fi}")
        dems   = set(exp['demandante'] for exp in grupo['expedientes'])
        demdos = set(exp['demandado']  for exp in grupo['expedientes'])
        if len(dems) > 1:
            print(f"  i  Demandantes: {' | '.join(sorted(dems))}")
        if len(demdos) > 1:
            print(f"  i  Demandados : {' | '.join(sorted(demdos))}")

    if total_grupos > 30:
        print(f"\n  ... y {total_grupos - 30} grupos mas (usa --excel para ver todos)")


def exportar_excel(grupos: list, n_palabras: int) -> str:
    try:
        import pandas as pd
    except ImportError:
        print("pandas no disponible")
        return ''

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta = os.path.join(
        os.path.dirname(__file__), '..', 'Archivos',
        f'duplicados_fuzzy_{n_palabras}palabras_{timestamp}.xlsx'
    )

    filas = []
    for grupo in grupos:
        clave_dem, clave_dem_do = grupo['clave']
        for exp in grupo['expedientes']:
            filas.append({
                'Clave Demandante':  clave_dem,
                'Clave Demandado':   clave_dem_do,
                'ID':                exp['id'],
                'Radicado Completo': exp['radicado_completo'],
                'Radicado Corto':    exp['radicado_corto'],
                'Demandante':        exp['demandante'],
                'Demandado':         exp['demandado'],
                'Estado':            exp['estado'],
                'Fecha Ingreso':     (exp['fecha_ingreso'].strftime('%d/%m/%Y')
                                      if exp['fecha_ingreso'] else ''),
            })

    df = pd.DataFrame(filas)
    df.to_excel(ruta, index=False, sheet_name='Posibles Duplicados')
    print(f"\nExcel exportado: {os.path.abspath(ruta)}")
    return ruta


# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Identifica expedientes duplicados por similitud demandante+demandado.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python diagnostico_duplicados_fuzzy.py              # 3 palabras (default)
  python diagnostico_duplicados_fuzzy.py --excel      # exportar a Excel
  python diagnostico_duplicados_fuzzy.py --min-palabras 2   # mas permisivo
  python diagnostico_duplicados_fuzzy.py --min-palabras 4   # mas estricto
        """
    )
    parser.add_argument('--excel', action='store_true',
                        help='Exporta resultados a Excel')
    parser.add_argument('--min-palabras', type=int, default=3,
                        help='Palabras clave a comparar (default: 3)')
    args = parser.parse_args()

    conn = obtener_conexion()
    try:
        print(f"Cargando expedientes...")
        rows = obtener_expedientes(conn)
        print(f"  {len(rows):,} expedientes con demandante y demandado")

        print(f"Buscando grupos similares ({args.min_palabras} palabras)...")
        grupos = encontrar_grupos(rows, args.min_palabras)

        imprimir_reporte(grupos, args.min_palabras)

        if args.excel and grupos:
            exportar_excel(grupos, args.min_palabras)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
