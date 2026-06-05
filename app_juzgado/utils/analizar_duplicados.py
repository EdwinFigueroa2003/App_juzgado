"""
ANALIZADOR DE PARES DUPLICADOS DESDE EXCEL
=====================================================
Lee el Excel de duplicados y crea pares maestro-secundario automáticamente.
Identifica radicados con 999, agrupa por demandante/demandado y genera
la estrategia de unificación.
"""

import os
import sys
import psycopg2
from datetime import datetime
from pathlib import Path
import pandas as pd
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=True)

# Importar conexión
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.configBd import obtener_conexion


class AnalizadorDuplicados:
    def __init__(self):
        self.conn = obtener_conexion()
        self.cursor = self.conn.cursor()
        self.pares = []  # Pares a consolidar
        self.resumen = {
            'caso_3_4': [],  # 999 vs REAL
            'caso_5_6': []   # Múltiples REALES
        }
    
    def cargar_excel(self, ruta_excel):
        """Lee el Excel de duplicados"""
        print(f"\n📂 Cargando Excel: {ruta_excel}")
        try:
            df = pd.read_excel(ruta_excel)
            print(f"✅ Excel cargado: {len(df)} filas")
            print(f"   Columnas: {list(df.columns)}")
            return df
        except Exception as e:
            print(f"❌ Error al cargar Excel: {e}")
            return None
    
    def obtener_info_expediente(self, exp_id):
        """Obtiene información del expediente"""
        self.cursor.execute("""
            SELECT id, radicado_completo, radicado_corto, demandante, demandado, 
                   fecha_ingreso, estado, juzgado_origen
            FROM expediente WHERE id = %s
        """, (exp_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'radicado_completo': result[1],
                'radicado_corto': result[2],
                'demandante': result[3],
                'demandado': result[4],
                'fecha_ingreso': result[5],
                'estado': result[6],
                'juzgado': result[7],
                'tiene_999': '999' in str(result[1]) if result[1] else False
            }
        return None
    
    def contar_registros(self, exp_id):
        """Cuenta ingresos + estados + actuaciones"""
        self.cursor.execute("""
            SELECT 
                COALESCE((SELECT COUNT(*) FROM ingresos WHERE expediente_id = %s), 0) as ing,
                COALESCE((SELECT COUNT(*) FROM estados WHERE expediente_id = %s), 0) as est,
                COALESCE((SELECT COUNT(*) FROM actuaciones WHERE expediente_id = %s), 0) as act
        """, (exp_id, exp_id, exp_id))
        ing, est, act = self.cursor.fetchone()
        return {'ingresos': ing, 'estados': est, 'actuaciones': act, 'total': ing + est + act}
    
    def elegir_maestro_simple(self, id1, id2):
        """
        Elige maestro entre dos expedientes.
        Criterio:
        1. Sin 999 > Con 999
        2. Más antiguo (menor fecha_ingreso)
        3. Más datos
        """
        info1 = self.obtener_info_expediente(id1)
        info2 = self.obtener_info_expediente(id2)
        
        if not info1 or not info2:
            return None
        
        # Criterio 1: Sin 999 vs Con 999
        if info1['tiene_999'] != info2['tiene_999']:
            return id1 if not info1['tiene_999'] else id2
        
        # Criterio 2: Más antiguo
        fecha1 = info1['fecha_ingreso'] or datetime.max.date()
        fecha2 = info2['fecha_ingreso'] or datetime.max.date()
        
        if fecha1 != fecha2:
            return id1 if fecha1 < fecha2 else id2
        
        # Criterio 3: Más datos
        datos1 = self.contar_registros(id1)['total']
        datos2 = self.contar_registros(id2)['total']
        
        return id1 if datos1 >= datos2 else id2
    
    def elegir_maestro_grupo(self, ids):
        """Elige maestro de un grupo de 3+ expedientes.
        Prioridad: sin 999 → radicado de 23 dígitos → más datos → menor ID.
        """
        if len(ids) == 1:
            return ids[0]

        infos = {i: self.obtener_info_expediente(i) for i in ids}
        # Filtrar los sin 999
        sin_999 = [i for i in ids if infos[i] and not infos[i]['tiene_999']]
        candidatos = sin_999 if sin_999 else ids

        # Entre candidatos: preferir radicado de exactamente 23 dígitos
        de_23 = [i for i in candidatos
                 if infos[i] and infos[i]['radicado_completo']
                 and len(str(infos[i]['radicado_completo']).strip()) == 23]
        if de_23:
            candidatos = de_23

        # Desempate por más datos
        return max(candidatos, key=lambda i: self.contar_registros(i)['total'])
    
    def agrupar_por_expediente(self, df):
        """Agrupa expedientes por Clave Demandante + Clave Demandado"""
        print("\n📊 Agrupando expedientes...")
        
        # Asegurar que ID es int
        df['ID'] = df['ID'].astype(int)
        
        # Detectar nombres de columnas (mayúsculas o minúsculas)
        cols = df.columns.tolist()
        col_demandante = next((c for c in cols if 'demandante' in c.lower() and 'clave' in c.lower()), 'Clave Demandante')
        col_demandado = next((c for c in cols if 'demandado' in c.lower() and 'clave' in c.lower()), 'Clave Demandado')
        
        print(f"   Usando columnas: '{col_demandante}' y '{col_demandado}'")
        
        grupos = {}
        for idx, row in df.iterrows():
            dem = str(row.get(col_demandante, '')).strip().lower()
            dem_do = str(row.get(col_demandado, '')).strip().lower()
            exp_id = int(row['ID'])
            
            # Saltar si las claves están vacías
            if not dem or not dem_do or dem == 'none' or dem_do == 'none':
                continue
            
            clave = (dem, dem_do)
            
            if clave not in grupos:
                grupos[clave] = []
            grupos[clave].append(exp_id)
        
        # Filtrar solo grupos con 2+ expedientes
        grupos_dup = {k: v for k, v in grupos.items() if len(v) > 1}
        
        print(f"✅ Encontrados {len(grupos_dup)} grupos con duplicados")
        return grupos_dup
    
    def crear_pares_caso_3_4(self, df):
        """Identifica pares 999 vs REAL (Caso 3 y 4)"""
        print("\n" + "="*70)
        print("🔍 IDENTIFICANDO CASO 3/4: Mezcla 999 vs REAL")
        print("="*70)
        
        # Detectar nombre de columna de radicado
        cols = df.columns.tolist()
        col_radicado = next((c for c in cols if 'radicado' in c.lower() and 'completo' in c.lower()), 'Radicado Completo')
        
        # Marcar cuáles tienen 999
        df['tiene_999'] = df[col_radicado].astype(str).str.contains('999', na=False)
        
        grupos = self.agrupar_por_expediente(df)
        pares_identificados = []
        
        for (demandante, demandado), ids in grupos.items():
            # Separar con 999 y sin 999
            con_999 = []
            sin_999 = []
            
            for exp_id in ids:
                info = self.obtener_info_expediente(exp_id)
                if info:
                    if info['tiene_999']:
                        con_999.append(info)
                    else:
                        sin_999.append(info)
            
            # Si hay mezcla 999 vs real
            if con_999 and sin_999 and len(ids) == 2:
                maestro_info = sin_999[0]
                secundario_info = con_999[0]
                
                datos_maestro = self.contar_registros(maestro_info['id'])
                datos_secundario = self.contar_registros(secundario_info['id'])
                
                par = {
                    'tipo': 'CASO_3_4',
                    'maestro_id': maestro_info['id'],
                    'maestro_radicado_completo': maestro_info['radicado_completo'],
                    'maestro_radicado_corto': maestro_info['radicado_corto'],
                    'maestro_datos': datos_maestro['total'],
                    'secundario_id': secundario_info['id'],
                    'secundario_radicado_completo': secundario_info['radicado_completo'],
                    'secundario_radicado_corto': secundario_info['radicado_corto'],
                    'secundario_datos': datos_secundario['total'],
                    'demandante': demandante,
                    'demandado': demandado,
                    'motivo': 'Expediente 999 (placeholder) consolidar a REAL'
                }
                pares_identificados.append(par)
        
        print(f"✅ Pares encontrados (Caso 3/4): {len(pares_identificados)}")
        return pares_identificados
    
    def crear_grupos_caso_5_6(self, df):
        """
        Identifica:
        - Caso 5: grupos de 3+ expedientes todos reales
        - Caso 6: grupos de 2 expedientes ambos reales (sin ningún 999)
        """
        print("\n" + "="*70)
        print("🔍 IDENTIFICANDO CASO 5/6: REALES sin 999")
        print("="*70)

        grupos = self.agrupar_por_expediente(df)
        grupos_identificados = []

        for (demandante, demandado), ids in grupos.items():
            infos = {i: self.obtener_info_expediente(i) for i in ids}
            hay_999  = any(infos[i] and infos[i]['tiene_999'] for i in ids)
            hay_real = any(infos[i] and not infos[i]['tiene_999'] for i in ids)

            # Caso 3/4 (mezcla 999+real con exactamente 2): ya procesado, saltar
            if hay_999 and hay_real and len(ids) == 2:
                continue

            # Caso 5/6: todos reales (o grupos 3+ con mezcla)
            # Incluir si no hay ningún 999, o si hay 3+ aunque sea mezcla
            if hay_999 and len(ids) == 2:
                continue  # solo 999, sin real — no unificable automáticamente

            if len(ids) < 2:
                continue

            maestro_id   = self.elegir_maestro_grupo(ids)
            secundarios  = [i for i in ids if i != maestro_id]
            maestro_info = infos[maestro_id]
            datos_maestro = self.contar_registros(maestro_id)

            tipo = 'CASO_5' if len(ids) >= 3 else 'CASO_6'

            grupo = {
                'tipo': tipo,
                'maestro_id': maestro_id,
                'maestro_radicado_completo': maestro_info['radicado_completo'] if maestro_info else '',
                'maestro_radicado_corto':    maestro_info['radicado_corto']    if maestro_info else '',
                'maestro_datos': datos_maestro['total'],
                'maestro_fecha': str(maestro_info['fecha_ingreso'] if maestro_info else ''),
                'maestro_juzgado': maestro_info['juzgado'] if maestro_info else '',
                'secundarios': [],
                'demandante': demandante,
                'demandado': demandado,
                'total_expedientes': len(ids),
                'motivo': f'{len(ids)} expedientes del mismo caso (distintos juzgados/instancias)'
            }

            for sec_id in secundarios:
                sec_info  = infos[sec_id]
                datos_sec = self.contar_registros(sec_id)
                grupo['secundarios'].append({
                    'id': sec_id,
                    'radicado_completo': sec_info['radicado_completo'] if sec_info else '',
                    'radicado_corto':    sec_info['radicado_corto']    if sec_info else '',
                    'datos': datos_sec['total'],
                    'fecha': str(sec_info['fecha_ingreso'] if sec_info else ''),
                    'juzgado': sec_info['juzgado'] if sec_info else '',
                    'tiene_999': sec_info['tiene_999'] if sec_info else False,
                })

            grupos_identificados.append(grupo)

        caso5 = sum(1 for g in grupos_identificados if g['tipo'] == 'CASO_5')
        caso6 = sum(1 for g in grupos_identificados if g['tipo'] == 'CASO_6')
        print(f"✅ Grupos Caso 5 (3+ reales): {caso5}")
        print(f"✅ Grupos Caso 6 (2 reales)  : {caso6}")
        return grupos_identificados
    
    def mostrar_resumen(self, pares_3_4, grupos_5_6):
        """Muestra resumen visual"""
        print("\n" + "="*70)
        print("📋 RESUMEN DE PARES A CONSOLIDAR")
        print("="*70)
        
        print(f"\n🔵 CASO 3/4 (999 vs REAL): {len(pares_3_4)} pares")
        for i, par in enumerate(pares_3_4[:5], 1):
            print(f"\n  [{i}] {par['demandante'][:30]}")
            print(f"      ✅ Maestro: ID {par['maestro_id']} | {par['maestro_datos']} registros")
            print(f"         Radicado: {par['maestro_radicado_completo']}")
            print(f"      ❌ Eliminar: ID {par['secundario_id']} ({par['secundario_datos']} registros)")
            print(f"         Radicado: {par['secundario_radicado_completo']}")
        if len(pares_3_4) > 5:
            print(f"\n  ... y {len(pares_3_4) - 5} pares más")
        
        print(f"\n🟡 CASO 5/6 (MÚLTIPLES REALES): {len(grupos_5_6)} grupos")
        for i, grupo in enumerate(grupos_5_6[:3], 1):
            print(f"\n  [{i}] {grupo['demandante'][:30]}")
            print(f"      ✅ Maestro: ID {grupo['maestro_id']} ({grupo['maestro_datos']} registros)")
            print(f"         Radicado: {grupo['maestro_radicado_completo']}")
            print(f"      Consolidar {len(grupo['secundarios'])} expedientes:")
            for sec in grupo['secundarios'][:3]:
                print(f"         ❌ ID {sec['id']} ({sec['datos']} registros)")
                print(f"            Radicado: {sec['radicado_completo']}")
            if len(grupo['secundarios']) > 3:
                print(f"         ... y {len(grupo['secundarios']) - 3} más")
        if len(grupos_5_6) > 3:
            print(f"\n  ... y {len(grupos_5_6) - 3} grupos más")
        
        total_consolidar = len(pares_3_4) + sum(len(g['secundarios']) for g in grupos_5_6)
        print(f"\n📦 TOTAL EXPEDIENTES A CONSOLIDAR: {total_consolidar}")
    
    def guardar_estrategia_json(self, pares_3_4, grupos_5_6):
        """Guarda la estrategia en JSON para ejecutar después"""
        estrategia = {
            'fecha_generacion': datetime.now().isoformat(),
            'caso_3_4': pares_3_4,
            'caso_5_6': grupos_5_6,
            'total_a_consolidar': len(pares_3_4) + sum(len(g['secundarios']) for g in grupos_5_6)
        }
        
        nombre_archivo = f"estrategia_unificacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        ruta = Path(__file__).parent.parent / 'Archivos' / nombre_archivo
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(estrategia, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Estrategia guardada: {ruta}")
        return ruta
    
    def cerrar(self):
        self.cursor.close()
        self.conn.close()


def main():
    print("\n" + "="*70)
    print("🔍 ANALIZADOR DE DUPLICADOS - FASE 1")
    print("="*70)

    # Usar el archivo específico indicado, o el más reciente como fallback
    ARCHIVO_FIJO = 'duplicados_fuzzy_3palabras_20260605_122257.xlsx'
    archivos_dir = Path(__file__).parent.parent / 'Archivos'
    archivo_fijo = archivos_dir / ARCHIVO_FIJO

    if archivo_fijo.exists():
        archivo = archivo_fijo
        print(f"\n📂 Usando archivo fijo: {archivo.name}")
    else:
        archivos_excel = list(archivos_dir.glob('duplicados_fuzzy_*_*.xlsx'))
        if not archivos_excel:
            print("❌ No se encontró archivo de duplicados")
            sys.exit(1)
        archivo = max(archivos_excel, key=lambda x: x.stat().st_mtime)
        print(f"\n📂 Usando archivo más reciente: {archivo.name}")

    print(f"   Ruta completa: {archivo}")

    analizador = AnalizadorDuplicados()

    try:
        # Cargar Excel
        df = analizador.cargar_excel(str(archivo))
        if df is None:
            sys.exit(1)

        # Verificar que el Excel tiene las columnas esperadas
        cols_requeridas = {'Clave Demandante', 'Clave Demandado', 'ID',
                           'Radicado Completo', 'Estado'}
        cols_faltantes = cols_requeridas - set(df.columns)
        if cols_faltantes:
            print(f"❌ Columnas faltantes en el Excel: {cols_faltantes}")
            print(f"   Columnas disponibles: {list(df.columns)}")
            sys.exit(1)

        print(f"\n📊 Resumen del Excel cargado:")
        print(f"   Total filas     : {len(df)}")
        print(f"   IDs únicos      : {df['ID'].nunique()}")
        print(f"   Con radicado 999: {df['Radicado Completo'].astype(str).str.contains('999').sum()}")
        print(f"   Sin radicado 999: {(~df['Radicado Completo'].astype(str).str.contains('999')).sum()}")

        # Analizar casos
        pares_3_4  = analizador.crear_pares_caso_3_4(df)
        grupos_5_6 = analizador.crear_grupos_caso_5_6(df)

        # Mostrar resumen
        analizador.mostrar_resumen(pares_3_4, grupos_5_6)

        # Guardar estrategia
        ruta_estrategia = analizador.guardar_estrategia_json(pares_3_4, grupos_5_6)

        print("\n✅ Análisis completado")
        print(f"\n📌 Siguiente paso:")
        print(f"   python utils/ejecutar_unificacion.py")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analizador.cerrar()


if __name__ == '__main__':
    main()
