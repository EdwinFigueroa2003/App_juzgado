#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explorador profundo de archivos Excel - analiza todas las hojas y archivos
"""

import pandas as pd
import os
from datetime import datetime

class ExcelDeepExplorer:
    """Explorador profundo de archivos Excel"""
    
    def __init__(self, archivos_path="Archivos/Otros"):
        self.archivos_path = archivos_path
    
    def listar_todos_archivos_excel(self):
        """Lista todos los archivos Excel en la carpeta"""
        print("📁 ARCHIVOS EXCEL ENCONTRADOS:")
        print("=" * 50)
        
        archivos_excel = []
        
        if os.path.exists(self.archivos_path):
            for archivo in os.listdir(self.archivos_path):
                if archivo.endswith(('.xlsx', '.xls')):
                    ruta_completa = os.path.join(self.archivos_path, archivo)
                    tamaño = os.path.getsize(ruta_completa)
                    archivos_excel.append({
                        'nombre': archivo,
                        'ruta': ruta_completa,
                        'tamaño': tamaño
                    })
                    print(f"   📄 {archivo} ({tamaño:,} bytes)")
        
        return archivos_excel
    
    def explorar_hojas_excel(self, archivo_path):
        """Explora todas las hojas de un archivo Excel"""
        print(f"\n📊 EXPLORANDO HOJAS DE: {os.path.basename(archivo_path)}")
        print("=" * 60)
        
        try:
            # Obtener nombres de todas las hojas
            excel_file = pd.ExcelFile(archivo_path)
            hojas = excel_file.sheet_names
            
            print(f"   📋 Hojas encontradas: {len(hojas)}")
            for i, hoja in enumerate(hojas):
                print(f"      {i+1}. '{hoja}'")
            
            # Explorar cada hoja
            for hoja in hojas:
                print(f"\n   🔍 HOJA: '{hoja}'")
                print("   " + "-" * 40)
                
                try:
                    df = pd.read_excel(archivo_path, sheet_name=hoja)
                    print(f"      Filas: {len(df)}")
                    print(f"      Columnas: {len(df.columns)}")
                    print(f"      Nombres: {list(df.columns)}")
                    
                    # Buscar patrones de radicados
                    self.buscar_radicados_en_hoja(df, hoja)
                    
                    # Buscar fechas
                    self.buscar_fechas_en_hoja(df, hoja)
                    
                except Exception as e:
                    print(f"      ❌ Error leyendo hoja '{hoja}': {e}")
        
        except Exception as e:
            print(f"   ❌ Error explorando archivo: {e}")
    
    def buscar_radicados_en_hoja(self, df, nombre_hoja):
        """Busca radicados en una hoja específica"""
        radicados_encontrados = []
        
        for col in df.columns:
            # Buscar por nombre de columna
            if any(keyword in str(col).lower() for keyword in ['radicad', 'expediente', 'numero']):
                sample_values = df[col].dropna().head(3).astype(str).tolist()
                if any(len(str(val)) > 8 for val in sample_values):
                    radicados_encontrados.append({
                        'columna': col,
                        'ejemplos': sample_values,
                        'total': df[col].notna().sum()
                    })
        
        if radicados_encontrados:
            print(f"      ✅ Posibles columnas de radicados:")
            for item in radicados_encontrados:
                print(f"         - '{item['columna']}': {item['total']} valores")
                print(f"           Ejemplos: {item['ejemplos']}")
    
    def buscar_fechas_en_hoja(self, df, nombre_hoja):
        """Busca columnas de fechas en una hoja"""
        fechas_encontradas = []
        
        for col in df.columns:
            # Buscar por nombre de columna
            if any(keyword in str(col).lower() for keyword in ['fecha', 'date', 'estado']):
                # Verificar si contiene fechas
                sample_values = df[col].dropna().head(3)
                if len(sample_values) > 0:
                    fechas_encontradas.append({
                        'columna': col,
                        'ejemplos': sample_values.tolist(),
                        'total_no_nulos': df[col].notna().sum(),
                        'total_nulos': df[col].isna().sum()
                    })
        
        if fechas_encontradas:
            print(f"      📅 Posibles columnas de fechas:")
            for item in fechas_encontradas:
                print(f"         - '{item['columna']}':")
                print(f"           Con fecha: {item['total_no_nulos']}")
                print(f"           Sin fecha: {item['total_nulos']}")
                print(f"           Ejemplos: {item['ejemplos']}")
    
    def analizar_fecha_estado_ingresos(self):
        """Analiza específicamente la columna FECHA ESTADO del archivo de ingresos"""
        print("\n🔍 ANÁLISIS ESPECÍFICO: FECHA ESTADO en ingresos_al_despacho_act.xlsx")
        print("=" * 70)
        
        archivo_ingresos = os.path.join(self.archivos_path, "ingresos_al_despacho_act.xlsx")
        
        if not os.path.exists(archivo_ingresos):
            print("❌ Archivo de ingresos no encontrado")
            return
        
        try:
            df = pd.read_excel(archivo_ingresos)
            
            if 'FECHA ESTADO' in df.columns:
                fecha_estado = df['FECHA ESTADO']
                
                print(f"   📊 Análisis de FECHA ESTADO:")
                print(f"      - Total registros: {len(fecha_estado)}")
                print(f"      - Con fecha: {fecha_estado.notna().sum()}")
                print(f"      - Sin fecha (vacíos): {fecha_estado.isna().sum()}")
                print(f"      - Porcentaje con fecha: {(fecha_estado.notna().sum() / len(fecha_estado) * 100):.1f}%")
                
                # Mostrar ejemplos de fechas
                fechas_no_nulas = fecha_estado.dropna()
                if len(fechas_no_nulas) > 0:
                    print(f"   📅 Ejemplos de fechas encontradas:")
                    for i, fecha in enumerate(fechas_no_nulas.head(5)):
                        radicado = df.iloc[fechas_no_nulas.index[i]]['RADICADO MODIFICADO']
                        print(f"      - {radicado}: {fecha}")
                
                # Mostrar ejemplos sin fecha
                fechas_nulas = fecha_estado.isna()
                if fechas_nulas.sum() > 0:
                    print(f"   ❌ Ejemplos SIN fecha (posibles pendientes):")
                    indices_nulos = df[fechas_nulas].head(5)
                    for _, row in indices_nulos.iterrows():
                        print(f"      - {row['RADICADO MODIFICADO']}: SIN FECHA")
                
            else:
                print("   ❌ No se encontró columna 'FECHA ESTADO'")
                
        except Exception as e:
            print(f"   ❌ Error analizando FECHA ESTADO: {e}")
    
    def ejecutar_exploracion_completa(self):
        """Ejecuta exploración completa de todos los archivos"""
        print("🔍 EXPLORACIÓN PROFUNDA DE ARCHIVOS EXCEL")
        print("=" * 80)
        
        # Listar todos los archivos Excel
        archivos = self.listar_todos_archivos_excel()
        
        # Explorar cada archivo
        for archivo in archivos:
            self.explorar_hojas_excel(archivo['ruta'])
        
        # Análisis específico de FECHA ESTADO
        self.analizar_fecha_estado_ingresos()
        
        print("\n" + "=" * 80)
        print("✅ EXPLORACIÓN COMPLETA FINALIZADA")
        print("\nConclusiones:")
        print("1. Revisa si FECHA ESTADO es la fecha de salida/cierre")
        print("2. Verifica si hay otras hojas con datos individuales")
        print("3. Confirma la lógica: Sin FECHA ESTADO = Pendiente")

def main():
    """Función principal"""
    explorer = ExcelDeepExplorer()
    explorer.ejecutar_exploracion_completa()

if __name__ == "__main__":
    main()