#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Procesador completo de expedientes - Cruza ingresos y estados para determinar estado actual
"""

import pandas as pd
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
import sys

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

class ExpedientesProcessor:
    """Procesador completo de expedientes"""
    
    def __init__(self, archivos_path="Archivos/Otros"):
        self.archivos_path = archivos_path
        self.estados_file = os.path.join(archivos_path, "estados.xlsx")
        self.ingresos_file = os.path.join(archivos_path, "ingresos_al_despacho_act.xlsx")
        
        # Datos procesados
        self.ingresos_data = {}  # {radicado_limpio: info_ingreso}
        self.estados_data = {}   # {radicado_limpio: info_estado}
        self.expedientes_procesados = {}  # {radicado_limpio: estado_final}
    
    def limpiar_radicado(self, radicado):
        """Limpia un radicado removiendo guiones, espacios y letras"""
        if pd.isna(radicado) or radicado == "":
            return ""
        
        # Convertir a string y limpiar
        radicado_str = str(radicado).strip()
        # Quitar todo excepto números
        radicado_limpio = re.sub(r'[^0-9]', '', radicado_str)
        
        return radicado_limpio
    
    def procesar_ingresos(self):
        """Procesa todas las hojas del archivo de ingresos"""
        print("📁 Procesando archivo de ingresos...")
        
        if not os.path.exists(self.ingresos_file):
            print(f"❌ Archivo no encontrado: {self.ingresos_file}")
            return False
        
        try:
            excel_file = pd.ExcelFile(self.ingresos_file)
            hojas_ingresos = [h for h in excel_file.sheet_names if 'Ingresos' in h]
            
            print(f"   📋 Hojas de ingresos encontradas: {len(hojas_ingresos)}")
            
            total_procesados = 0
            
            for hoja in hojas_ingresos:
                print(f"   🔄 Procesando hoja: {hoja}")
                
                df = pd.read_excel(self.ingresos_file, sheet_name=hoja)
                
                # Buscar columnas relevantes
                col_radicado = None
                col_fecha_ingreso = None
                
                for col in df.columns:
                    if 'RADICADO MODIFICADO' in str(col):
                        col_radicado = col
                    elif 'FECHA DE INGRESO' in str(col):
                        col_fecha_ingreso = col
                
                if not col_radicado or not col_fecha_ingreso:
                    print(f"      ⚠️ Columnas no encontradas en {hoja}")
                    continue
                
                # Procesar cada fila
                for _, row in df.iterrows():
                    radicado_original = row[col_radicado]
                    fecha_ingreso = row[col_fecha_ingreso]
                    
                    if pd.notna(radicado_original) and pd.notna(fecha_ingreso):
                        radicado_limpio = self.limpiar_radicado(radicado_original)
                        
                        if radicado_limpio:
                            self.ingresos_data[radicado_limpio] = {
                                'radicado_original': radicado_original,
                                'fecha_ingreso': fecha_ingreso,
                                'hoja_origen': hoja,
                                'demandante': row.get('DEMANDANTE', ''),
                                'demandado': row.get('DEMANDADO', ''),
                                'solicitud': row.get('SOLICITUD', ''),
                                'responsable': row.get('RESPONSABLE', ''),
                                'ubicacion': row.get('UBICACIÓN', '')
                            }
                            total_procesados += 1
                
                print(f"      ✅ {len(df)} filas procesadas")
            
            print(f"   📊 Total ingresos únicos: {len(self.ingresos_data)}")
            print(f"   📊 Total registros procesados: {total_procesados}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error procesando ingresos: {e}")
            return False
    
    def procesar_estados(self):
        """Procesa todas las hojas del archivo de estados"""
        print("📁 Procesando archivo de estados...")
        
        if not os.path.exists(self.estados_file):
            print(f"❌ Archivo no encontrado: {self.estados_file}")
            return False
        
        try:
            excel_file = pd.ExcelFile(self.estados_file)
            hojas_estados = [h for h in excel_file.sheet_names if 'Q' in h and '20' in h]
            
            print(f"   📋 Hojas de estados encontradas: {len(hojas_estados)}")
            
            total_procesados = 0
            
            for hoja in hojas_estados:
                print(f"   🔄 Procesando hoja: {hoja}")
                
                df = pd.read_excel(self.estados_file, sheet_name=hoja)
                
                # Buscar columnas relevantes
                col_radicacion = None
                col_fecha_estado = None
                
                for col in df.columns:
                    if 'Radicación' in str(col):
                        col_radicacion = col
                    elif 'Fecha Estado' in str(col):
                        col_fecha_estado = col
                
                if not col_radicacion or not col_fecha_estado:
                    print(f"      ⚠️ Columnas no encontradas en {hoja}")
                    continue
                
                # Procesar cada fila
                for _, row in df.iterrows():
                    radicacion_original = row[col_radicacion]
                    fecha_estado = row[col_fecha_estado]
                    
                    if pd.notna(radicacion_original):
                        radicado_limpio = self.limpiar_radicado(radicacion_original)
                        
                        if radicado_limpio:
                            self.estados_data[radicado_limpio] = {
                                'radicacion_original': radicacion_original,
                                'fecha_estado': fecha_estado if pd.notna(fecha_estado) else None,
                                'hoja_origen': hoja,
                                'clase': row.get('Clase', ''),
                                'demandante': row.get('Demandante', ''),
                                'demandado': row.get('Demandado', ''),
                                'auto_anotacion': row.get('Auto / Anotación', '')
                            }
                            total_procesados += 1
                
                print(f"      ✅ {len(df)} filas procesadas")
            
            print(f"   📊 Total estados únicos: {len(self.estados_data)}")
            print(f"   📊 Total registros procesados: {total_procesados}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error procesando estados: {e}")
            return False
    
    def determinar_estado_expediente(self, radicado_limpio):
        """Determina el estado de un expediente según la lógica del negocio"""
        ingreso = self.ingresos_data.get(radicado_limpio)
        estado = self.estados_data.get(radicado_limpio)
        
        # Lógica de determinación de estado
        if estado and estado['fecha_estado']:
            # Tiene fecha de salida registrada
            return {
                'estado': 'SALIÓ',
                'descripcion': 'Expediente cerrado/resuelto',
                'fecha_salida': estado['fecha_estado'],
                'activo': True  # Activo resuelto
            }
        
        elif ingreso and not (estado and estado['fecha_estado']):
            # Tiene ingreso pero no salida
            ubicacion = str(ingreso.get('ubicacion', '')).upper() if pd.notna(ingreso.get('ubicacion', '')) else ''
            
            if 'DESPACHO' in ubicacion:
                return {
                    'estado': 'ACTIVO',
                    'descripcion': 'Activo pendiente en despacho',
                    'fecha_salida': None,
                    'activo': True
                }
            else:
                return {
                    'estado': 'PENDIENTE',
                    'descripcion': 'Pendiente de resolución',
                    'fecha_salida': None,
                    'activo': False
                }
        
        elif not ingreso and not estado:
            # Sin movimiento registrado
            return {
                'estado': 'INACTIVO',
                'descripcion': 'Sin movimiento registrado',
                'fecha_salida': None,
                'activo': False
            }
        
        else:
            # Caso por defecto
            return {
                'estado': 'PENDIENTE',
                'descripcion': 'Estado indeterminado',
                'fecha_salida': None,
                'activo': False
            }
    
    def procesar_todos_expedientes(self):
        """Procesa todos los expedientes y determina sus estados"""
        print("🔄 Determinando estados de expedientes...")
        
        # Obtener todos los radicados únicos
        todos_radicados = set(self.ingresos_data.keys()) | set(self.estados_data.keys())
        
        print(f"   📊 Total expedientes únicos a procesar: {len(todos_radicados)}")
        
        # Contadores por estado
        contadores = defaultdict(int)
        
        for radicado_limpio in todos_radicados:
            estado_info = self.determinar_estado_expediente(radicado_limpio)
            
            # Combinar información de ingreso y estado
            ingreso = self.ingresos_data.get(radicado_limpio, {})
            estado = self.estados_data.get(radicado_limpio, {})
            
            # Función auxiliar para manejar valores nulos
            def safe_str(value):
                return str(value) if pd.notna(value) else ''
            
            expediente_completo = {
                'radicado_limpio': radicado_limpio,
                'radicado_original_ingreso': safe_str(ingreso.get('radicado_original', '')),
                'radicado_original_estado': safe_str(estado.get('radicacion_original', '')),
                'fecha_ingreso': ingreso.get('fecha_ingreso'),
                'fecha_estado': estado_info['fecha_salida'],
                'estado_final': estado_info['estado'],
                'descripcion_estado': estado_info['descripcion'],
                'activo': estado_info['activo'],
                'demandante': safe_str(ingreso.get('demandante', '')) or safe_str(estado.get('demandante', '')),
                'demandado': safe_str(ingreso.get('demandado', '')) or safe_str(estado.get('demandado', '')),
                'responsable': safe_str(ingreso.get('responsable', '')),
                'ubicacion': safe_str(ingreso.get('ubicacion', '')),
                'solicitud': safe_str(ingreso.get('solicitud', '')),
                'clase': safe_str(estado.get('clase', '')),
                'auto_anotacion': safe_str(estado.get('auto_anotacion', ''))
            }
            
            self.expedientes_procesados[radicado_limpio] = expediente_completo
            contadores[estado_info['estado']] += 1
        
        # Mostrar estadísticas
        print(f"   📊 Estadísticas de estados:")
        for estado, cantidad in contadores.items():
            porcentaje = (cantidad / len(todos_radicados)) * 100
            print(f"      - {estado}: {cantidad} ({porcentaje:.1f}%)")
        
        return True
    
    def generar_reporte_excel(self):
        """Genera un reporte Excel con todos los expedientes procesados"""
        print("📄 Generando reporte Excel...")
        
        if not self.expedientes_procesados:
            print("   ❌ No hay expedientes procesados")
            return False
        
        try:
            # Convertir a DataFrame
            df_reporte = pd.DataFrame(list(self.expedientes_procesados.values()))
            
            # Ordenar por estado y fecha
            df_reporte = df_reporte.sort_values(['estado_final', 'fecha_ingreso'])
            
            # Generar archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo_reporte = os.path.join(self.archivos_path, f"expedientes_procesados_{timestamp}.xlsx")
            
            with pd.ExcelWriter(archivo_reporte, engine='openpyxl') as writer:
                # Hoja principal con todos los datos
                df_reporte.to_excel(writer, sheet_name='Todos_Expedientes', index=False)
                
                # Hojas por estado
                for estado in df_reporte['estado_final'].unique():
                    df_estado = df_reporte[df_reporte['estado_final'] == estado]
                    df_estado.to_excel(writer, sheet_name=f'Estado_{estado}', index=False)
                
                # Hoja de estadísticas
                estadisticas = df_reporte['estado_final'].value_counts().reset_index()
                estadisticas.columns = ['Estado', 'Cantidad']
                estadisticas['Porcentaje'] = (estadisticas['Cantidad'] / len(df_reporte) * 100).round(1)
                estadisticas.to_excel(writer, sheet_name='Estadisticas', index=False)
            
            print(f"   ✅ Reporte generado: {archivo_reporte}")
            return archivo_reporte
            
        except Exception as e:
            print(f"   ❌ Error generando reporte: {e}")
            return False
    
    def ejecutar_procesamiento_completo(self):
        """Ejecuta el procesamiento completo de expedientes"""
        print("🚀 PROCESAMIENTO COMPLETO DE EXPEDIENTES")
        print("=" * 80)
        
        # Paso 1: Procesar ingresos
        if not self.procesar_ingresos():
            print("❌ Error procesando ingresos")
            return False
        
        print()
        
        # Paso 2: Procesar estados
        if not self.procesar_estados():
            print("❌ Error procesando estados")
            return False
        
        print()
        
        # Paso 3: Determinar estados finales
        if not self.procesar_todos_expedientes():
            print("❌ Error determinando estados")
            return False
        
        print()
        
        # Paso 4: Generar reporte
        archivo_reporte = self.generar_reporte_excel()
        
        print()
        print("✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
        print("=" * 80)
        
        if archivo_reporte:
            print(f"📄 Reporte generado: {archivo_reporte}")
            print("📊 El reporte incluye:")
            print("   - Todos los expedientes procesados")
            print("   - Hojas separadas por estado")
            print("   - Estadísticas generales")
        
        return True

def main():
    """Función principal"""
    processor = ExpedientesProcessor()
    processor.ejecutar_procesamiento_completo()

if __name__ == "__main__":
    main()