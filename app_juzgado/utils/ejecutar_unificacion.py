"""
EJECUTOR DE UNIFICACIÓN DE EXPEDIENTES
=====================================================
Lee la estrategia JSON y ejecuta la consolidación:
- Transfiere ingresos, estados y actuaciones
- Elimina expedientes secundarios
- Genera auditoría detallada
"""

import os
import sys
import argparse
import psycopg2
from datetime import datetime
from pathlib import Path
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=True)

# Importar conexión
#sys.path.insert(0, os.path.dirname(__file__))
BASE_DIR = Path(__file__).resolve().parent.parent


# Agregamos la raíz del proyecto al sys.path
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

    
from modelo.configBd import obtener_conexion


class EjecutorUnificacion:
    def __init__(self, ruta_estrategia=None):
        self.conn = obtener_conexion()
        self.cursor = self.conn.cursor()
        self.estrategia = self.cargar_estrategia(ruta_estrategia)
        self.auditoría = []
        self.errores = []
    
    def cargar_estrategia(self, ruta=None):
        """Carga la estrategia JSON generada por analizar_duplicados.py o un archivo de unificación masiva"""
        if not ruta:
            # Buscar el más reciente
            archivos_dir = Path(__file__).parent.parent / 'Archivos'
            archivos_est = list(archivos_dir.glob('estrategia_unificacion_*.json'))
            
            if not archivos_est:
                print("❌ No se encontró archivo de estrategia")
                print("   Ejecutar primero: python utils/analizar_duplicados.py")
                sys.exit(1)
            
            ruta = max(archivos_est, key=lambda x: x.stat().st_mtime)
        else:
            ruta = Path(ruta)
            if not ruta.exists():
                print(f"❌ El archivo de estrategia no existe: {ruta}")
                sys.exit(1)
        
        print(f"\n📂 Cargando estrategia: {ruta.name}")
        
        with open(ruta, 'r', encoding='utf-8') as f:
            estrategia = json.load(f)

        if estrategia.get('tipo') == 'unificacion_masiva':
            if 'parejas' not in estrategia or not isinstance(estrategia['parejas'], list):
                print("❌ El archivo de unificación masiva debe contener la clave 'parejas'")
                sys.exit(1)
            estrategia['total_a_consolidar'] = len(estrategia['parejas'])
        return estrategia
    
    def transferir_datos(self, exp_maestro, exp_secundario):
        """Transfiere ingresos, estados y actuaciones del secundario al maestro"""
        try:
            # 1. Transferir INGRESOS
            self.cursor.execute("""
                UPDATE ingresos 
                SET expediente_id = %s 
                WHERE expediente_id = %s
            """, (exp_maestro, exp_secundario))
            ing = self.cursor.rowcount
            
            # 2. Transferir ESTADOS
            self.cursor.execute("""
                UPDATE estados 
                SET expediente_id = %s 
                WHERE expediente_id = %s
            """, (exp_maestro, exp_secundario))
            est = self.cursor.rowcount
            
            # 3. Transferir ACTUACIONES
            self.cursor.execute("""
                UPDATE actuaciones 
                SET expediente_id = %s 
                WHERE expediente_id = %s
            """, (exp_maestro, exp_secundario))
            act = self.cursor.rowcount
            
            self.conn.commit()
            
            return {
                'ingresos': ing,
                'estados': est,
                'actuaciones': act,
                'total': ing + est + act
            }
        
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Error al transferir datos: {e}")
    
    def obtener_info_expediente_para_auditoria(self, exp_id):
        """Obtiene radicados del expediente ANTES de eliminar"""
        try:
            self.cursor.execute("""
                SELECT radicado_completo, radicado_corto
                FROM expediente WHERE id = %s
            """, (exp_id,))
            result = self.cursor.fetchone()
            return {
                'radicado_completo': result[0] if result else None,
                'radicado_corto': result[1] if result else None
            }
        except:
            return {'radicado_completo': None, 'radicado_corto': None}
    def eliminar_expediente(self, exp_id):
        """Elimina un expediente y sus datos relacionados"""
        try:
            # PRIMERO: Guardar información de auditoría (radicados)
            info_auditoria = self.obtener_info_expediente_para_auditoria(exp_id)
            
            # Primero eliminar ingresos/estados/actuaciones por si queda algo
            self.cursor.execute("DELETE FROM ingresos WHERE expediente_id = %s", (exp_id,))
            self.cursor.execute("DELETE FROM estados WHERE expediente_id = %s", (exp_id,))
            self.cursor.execute("DELETE FROM actuaciones WHERE expediente_id = %s", (exp_id,))
            
            # Eliminar el expediente
            self.cursor.execute("DELETE FROM expediente WHERE id = %s", (exp_id,))
            
            self.conn.commit()
            
            # Guardar info para auditoría
            return True, info_auditoria
        
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Error al eliminar expediente {exp_id}: {e}")
    
    def procesar_caso_3_4(self):
        """Procesa casos 3 y 4: 999 vs REAL"""
        print("\n" + "="*70)
        print("⚙️  EJECUTANDO: CASO 3/4 (999 vs REAL)")
        print("="*70)
        
        pares = self.estrategia.get('caso_3_4', [])
        exitosos = 0
        
        for i, par in enumerate(pares, 1):
            try:
                maestro_id = par['maestro_id']
                secundario_id = par['secundario_id']
                
                print(f"\n[{i}/{len(pares)}] Procesando par...")
                print(f"    ✅ Maestro: ID {maestro_id} ({par['maestro_datos']} registros)")
                print(f"       Radicado: {par.get('maestro_radicado_completo', par.get('maestro_radicado', 'N/A'))}")
                print(f"    ❌ Eliminar: ID {secundario_id} ({par['secundario_datos']} registros)")
                print(f"       Radicado: {par.get('secundario_radicado_completo', par.get('secundario_radicado', 'N/A'))}")
                
                # 1. Transferir datos
                datos = self.transferir_datos(maestro_id, secundario_id)
                print(f"    📦 Transferidos: {datos['total']} registros")
                print(f"       • Ingresos: {datos['ingresos']}")
                print(f"       • Estados: {datos['estados']}")
                print(f"       • Actuaciones: {datos['actuaciones']}")
                
                # 2. Eliminar expediente secundario
                eliminado, info_rad = self.eliminar_expediente(secundario_id)
                if eliminado:
                    print(f"    🗑️  Expediente {secundario_id} eliminado")
                    exitosos += 1
                    
                    # Registrar en auditoría
                    self.auditoría.append({
                        'tipo': 'CASO_3_4',
                        'maestro_id': maestro_id,
                        'maestro_radicado_completo': par.get('maestro_radicado_completo'),
                        'maestro_radicado_corto': par.get('maestro_radicado_corto'),
                        'secundario_id': secundario_id,
                        'secundario_radicado_completo': par.get('secundario_radicado_completo'),
                        'secundario_radicado_corto': par.get('secundario_radicado_corto'),
                        'demandante': par['demandante'],
                        'demandado': par['demandado'],
                        'registros_transferidos': datos['total'],
                        'estado': 'EXITOSO',
                        'fecha': datetime.now().isoformat()
                    })
                else:
                    raise Exception("No se eliminó correctamente")
            
            except Exception as e:
                error_msg = f"[Par {i}] {e}"
                self.errores.append(error_msg)
                print(f"    ❌ ERROR: {e}")
                
                # Guardar info para auditoría incluso si hay error
                info_rad = self.obtener_info_expediente_para_auditoria(secundario_id)
                self.auditoría.append({
                    'tipo': 'CASO_3_4',
                    'maestro_id': par['maestro_id'],
                    'secundario_id': secundario_id,
                    'secundario_radicado_completo': par.get('secundario_radicado_completo'),
                    'secundario_radicado_corto': par.get('secundario_radicado_corto'),
                    'demandante': par['demandante'],
                    'demandado': par['demandado'],
                    'estado': 'ERROR',
                    'error': str(e),
                    'fecha': datetime.now().isoformat()
                })
        
        print(f"\n✅ Casos 3/4 completados: {exitosos}/{len(pares)} exitosos")
        return exitosos
    
    def procesar_caso_5_6(self):
        """Procesa casos 5 y 6: Múltiples REALES"""
        print("\n" + "="*70)
        print("⚙️  EJECUTANDO: CASO 5/6 (MÚLTIPLES REALES)")
        print("="*70)
        
        grupos = self.estrategia.get('caso_5_6', [])
        exitosos = 0
        
        for i, grupo in enumerate(grupos, 1):
            try:
                maestro_id = grupo['maestro_id']
                secundarios = grupo['secundarios']
                
                print(f"\n[{i}/{len(grupos)}] Grupo: {grupo['demandante'][:40]}")
                print(f"    ✅ Maestro: ID {maestro_id} ({grupo['maestro_datos']} registros)")
                print(f"       Radicado: {grupo.get('maestro_radicado_completo')}")
                print(f"    📋 Consolidando {len(secundarios)} expedientes...")
                
                total_transferido = 0
                
                # Procesar cada secundario del grupo
                for j, secundario in enumerate(secundarios, 1):
                    sec_id = secundario['id']
                    
                    try:
                        # Transferir datos
                        datos = self.transferir_datos(maestro_id, sec_id)
                        
                        # Eliminar expediente
                        eliminado, info_rad = self.eliminar_expediente(sec_id)
                        if eliminado:
                            total_transferido += datos['total']
                            print(f"       [{j}] ✅ ID {sec_id} consolidado ({datos['total']} registros)")
                            print(f"            Radicado: {secundario.get('radicado_completo')}")
                            
                            self.auditoría.append({
                                'tipo': 'CASO_5_6',
                                'maestro_id': maestro_id,
                                'maestro_radicado_completo': grupo.get('maestro_radicado_completo'),
                                'maestro_radicado_corto': grupo.get('maestro_radicado_corto'),
                                'secundario_id': sec_id,
                                'secundario_radicado_completo': secundario.get('radicado_completo'),
                                'secundario_radicado_corto': secundario.get('radicado_corto'),
                                'demandante': grupo['demandante'],
                                'demandado': grupo['demandado'],
                                'registros_transferidos': datos['total'],
                                'estado': 'EXITOSO',
                                'fecha': datetime.now().isoformat()
                            })
                            exitosos += 1
                    
                    except Exception as e:
                        error_msg = f"[Grupo {i}, sec {j}] {e}"
                        self.errores.append(error_msg)
                        print(f"       [{j}] ❌ ID {sec_id} ERROR: {e}")
                        
                        self.auditoría.append({
                            'tipo': 'CASO_5_6',
                            'maestro_id': maestro_id,
                            'secundario_id': sec_id,
                            'secundario_radicado_completo': secundario.get('radicado_completo'),
                            'secundario_radicado_corto': secundario.get('radicado_corto'),
                            'demandante': grupo['demandante'],
                            'demandado': grupo['demandado'],
                            'estado': 'ERROR',
                            'error': str(e),
                            'fecha': datetime.now().isoformat()
                        })
                
                print(f"    ✅ Grupo completado: {total_transferido} registros consolidados")
            
            except Exception as e:
                self.errores.append(f"[Grupo {i}] {e}")
                print(f"    ❌ ERROR en grupo: {e}")
        
        print(f"\n✅ Casos 5/6 completados: {exitosos} expedientes consolidados")
        return exitosos

    def obtener_maestro_por_radicado(self, radicado_completo):
        """Busca el maestro por su radicado completo"""
        self.cursor.execute(
            "SELECT id, radicado_completo, radicado_corto FROM expediente WHERE radicado_completo = %s",
            (radicado_completo,)
        )
        fila = self.cursor.fetchone()
        if not fila:
            return None
        return {
            'id': fila[0],
            'radicado_completo': fila[1],
            'radicado_corto': fila[2]
        }

    def procesar_unificacion_masiva(self):
        """Procesa un archivo de unificación masiva con parejas de secundario -> maestro"""
        print("\n" + "="*70)
        print("⚙️  EJECUTANDO: UNIFICACIÓN MASIVA")
        print("="*70)
        
        parejas = self.estrategia.get('parejas', [])
        exitosos = 0
        
        for i, pareja in enumerate(parejas, 1):
            secundario_id = pareja.get('secundario_id')
            maestro_radicado = pareja.get('maestro_radicado_completo')
            secundario_radicado_corto = pareja.get('secundario_radicado_corto')
            
            try:
                print(f"\n[{i}/{len(parejas)}] Procesando unificación masiva...")
                print(f"    ✅ Secundario: ID {secundario_id} ({secundario_radicado_corto})")
                print(f"    🎯 Maestro radicado completo: {maestro_radicado}")

                maestro = self.obtener_maestro_por_radicado(maestro_radicado)
                if not maestro:
                    raise Exception(f"No se encontró expediente maestro con radicado completo {maestro_radicado}")

                maestro_id = maestro['id']
                datos = self.transferir_datos(maestro_id, secundario_id)
                print(f"    📦 Transferidos: {datos['total']} registros")
                print(f"       • Ingresos: {datos['ingresos']}")
                print(f"       • Estados: {datos['estados']}")
                print(f"       • Actuaciones: {datos['actuaciones']}")

                eliminado, info_rad = self.eliminar_expediente(secundario_id)
                if eliminado:
                    exitosos += 1
                    print(f"    🗑️  Expediente secundario {secundario_id} eliminado")
                    self.auditoría.append({
                        'tipo': 'UNIFICACION_MASIVA',
                        'maestro_id': maestro_id,
                        'maestro_radicado_completo': maestro['radicado_completo'],
                        'maestro_radicado_corto': maestro['radicado_corto'],
                        'secundario_id': secundario_id,
                        'secundario_radicado_completo': info_rad.get('radicado_completo'),
                        'secundario_radicado_corto': info_rad.get('radicado_corto'),
                        'demandante': pareja.get('demandante', ''),
                        'demandado': pareja.get('demandado', ''),
                        'registros_transferidos': datos['total'],
                        'estado': 'EXITOSO',
                        'fecha': datetime.now().isoformat()
                    })
                else:
                    raise Exception("No se eliminó correctamente el expediente secundario")
            except Exception as e:
                error_msg = f"[Pareja {i}] {e}"
                self.errores.append(error_msg)
                print(f"    ❌ ERROR: {e}")
                self.auditoría.append({
                    'tipo': 'UNIFICACION_MASIVA',
                    'maestro_radicado_completo': maestro_radicado,
                    'secundario_id': secundario_id,
                    'secundario_radicado_corto': secundario_radicado_corto,
                    'demandante': pareja.get('demandante', ''),
                    'demandado': pareja.get('demandado', ''),
                    'estado': 'ERROR',
                    'error': str(e),
                    'fecha': datetime.now().isoformat()
                })
        
        print(f"\n✅ Unificación masiva completada: {exitosos}/{len(parejas)} expedientes consolidados")
        return exitosos
    
    def generar_reporte_final(self):
        """Genera reporte final"""
        print("\n" + "="*70)
        print("📊 REPORTE FINAL")
        print("="*70)
        
        exitosos = len([a for a in self.auditoría if a.get('estado') == 'EXITOSO'])
        errores = len(self.errores)
        
        print(f"\n✅ Consolidaciones exitosas: {exitosos}")
        print(f"❌ Errores: {errores}")
        
        if exitosos > 0:
            total_registros = sum(a.get('registros_transferidos', 0) for a in self.auditoría if a.get('estado') == 'EXITOSO')
            print(f"📦 Total de registros transferidos: {total_registros}")
        
        if self.errores:
            print(f"\n⚠️  ERRORES ENCONTRADOS:")
            for error in self.errores[:10]:
                print(f"  • {error}")
            if len(self.errores) > 10:
                print(f"  ... y {len(self.errores) - 10} errores más")
        
        # Guardar reporte JSON
        reporte = {
            'fecha_ejecucion': datetime.now().isoformat(),
            'consolidaciones_exitosas': exitosos,
            'total_errores': errores,
            'auditoría': self.auditoría,
            'errores': self.errores
        }
        
        nombre = f"reporte_consolidacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        ruta = Path(__file__).parent.parent / 'Archivos' / nombre
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Reporte guardado: {ruta}")
        
        # Generar CSV de auditoría para visualizar fácilmente
        import csv
        nombre_csv = f"auditoria_consolidacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        ruta_csv = Path(__file__).parent.parent / 'Archivos' / nombre_csv
        
        if self.auditoría:
            with open(ruta_csv, 'w', newline='', encoding='utf-8') as f:
                campos = ['tipo', 'maestro_id', 'maestro_radicado', 'secundario_id', 
                         'secundario_radicado_completo', 'secundario_radicado_corto',
                         'demandante', 'demandado', 'registros_transferidos', 'estado', 'error', 'fecha']
                writer = csv.DictWriter(f, fieldnames=campos)
                writer.writeheader()
                for audit in self.auditoría:
                    writer.writerow({k: audit.get(k, '') for k in campos})
            
            print(f"📄 Auditoría CSV: {ruta_csv}")
    
    def cerrar(self):
        self.cursor.close()
        self.conn.close()


def preguntar_confirmacion(estrategia):
    """Pide confirmación antes de ejecutar"""
    print("\n" + "="*70)
    print("⚠️  CONFIRMACIÓN REQUERIDA")
    print("="*70)
    
    tipo = estrategia.get('tipo', 'caso_3_4_5_6')
    if tipo == 'unificacion_masiva':
        total = len(estrategia.get('parejas', []))
        print(f"\n📋 Se ejecutarán:")
        print(f"   • Unificación masiva: {total} expedientes")
        print(f"   • TOTAL: {total} expedientes a ELIMINAR")
    else:
        caso_3_4 = len(estrategia.get('caso_3_4', []))
        caso_5_6 = len(estrategia.get('caso_5_6', []))
        total_secundarios_5_6 = sum(len(g.get('secundarios', [])) for g in estrategia.get('caso_5_6', []))
        print(f"\n📋 Se ejecutarán:")
        print(f"   • Caso 3/4 (999 vs REAL): {caso_3_4} consolidaciones")
        print(f"   • Caso 5/6 (Múltiples REALES): {total_secundarios_5_6} consolidaciones")
        print(f"   • TOTAL: {caso_3_4 + total_secundarios_5_6} expedientes a ELIMINAR")
    
    print(f"\n⚠️  Esta operación es IRREVERSIBLE (datos transferidos, expedientes eliminados)")
    
    respuesta = input("\n¿Deseas continuar? (escribe 'SI' para confirmar): ").strip().upper()
    
    return respuesta == 'SI'


def main():
    parser = argparse.ArgumentParser(description='Ejecutor de unificación de expedientes')
    parser.add_argument('--ruta', '-r', help='Ruta al archivo JSON de estrategia', default=None)
    args = parser.parse_args()

    print("\n" + "="*70)
    print("🔄 EJECUTOR DE UNIFICACIÓN - FASE 2")
    print("="*70)
    
    ejecutor = EjecutorUnificacion(ruta_estrategia=args.ruta)
    
    try:
        tipo = ejecutor.estrategia.get('tipo', 'caso_3_4_5_6')

        print(f"\n📊 Resumen de estrategia:")
        if tipo == 'unificacion_masiva':
            print(f"   • Unificación masiva: {len(ejecutor.estrategia.get('parejas', []))} parejas")
            print(f"   • Total a consolidar: {ejecutor.estrategia.get('total_a_consolidar', len(ejecutor.estrategia.get('parejas', [])))}")
        else:
            caso_3_4 = ejecutor.estrategia.get('caso_3_4', [])
            caso_5_6 = ejecutor.estrategia.get('caso_5_6', [])
            print(f"   • Caso 3/4: {len(caso_3_4)} pares")
            print(f"   • Caso 5/6: {len(caso_5_6)} grupos")
            print(f"   • Total a consolidar: {ejecutor.estrategia.get('total_a_consolidar', 0)}")
        
        # Preguntar confirmación
        if not preguntar_confirmacion(ejecutor.estrategia):
            print("\n❌ Operación cancelada por el usuario")
            return
        
        # Ejecutar consolidación según tipo de estrategia
        if tipo == 'unificacion_masiva':
            ejecutor.procesar_unificacion_masiva()
        else:
            ejecutor.procesar_caso_3_4()
            ejecutor.procesar_caso_5_6()
        
        # Generar reporte
        ejecutor.generar_reporte_final()
        
        print("\n✅ Proceso completado")
        
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ejecutor.cerrar()


if __name__ == '__main__':
    main()
