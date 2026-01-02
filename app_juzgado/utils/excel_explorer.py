#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explorador de archivos Excel para identificar estructura y contenido
"""

import pandas as pd
import os

class ExcelExplorer:
    """Explorador de archivos Excel"""
    
    def __init__(self, archivos_path="Archivos/Otros"):
        self.archivos_path = archivos_path
        self.estados_file = os.path.join(archivos_path, "estados.xlsx")
        self.ingresos_file = os.path.join(archivos_path, "ingresos_al_despacho_act.xlsx")
    
    def explorar_archivo(self, archivo_path, nombre_archivo):
        """Explora un archivo Excel específico"""
        print(f"🔍 EXPLORANDO: {nombre_archivo}")
        print("=" * 60)
        
        if not os.path.exists(archivo_path):
            print(f"❌ Archivo no encontrado: {archivo_path}")
            return
        
        try:
            # Leer con diferentes configuraciones de header
            for header_row in [0, 1, 2, None]:
                print(f"\n📋 HEADER = {header_row}:")
                try:
                    df = pd.read_excel(archivo_path, header=header_row)
                    print(f"   Filas: {len(df)}")
                    print(f"   Columnas: {len(df.columns)}")
                    print(f"   Nombres de columnas: {list(df.columns)}")
                    
                    # Mostrar primeras 3 filas
                    print("   📊 Primeras 3 filas:")
                    for i in range(min(3, len(df))):
                        print(f"      Fila {i}: {df.iloc[i].tolist()}")
                    
                except Exception as e:
                    print(f"   ❌ Error con header={header_row}: {e}")
            
            # Análisis especial para encontrar radicados
            print(f"\n🔍 BÚSQUEDA DE RADICADOS:")
            self.buscar_radicados_en_archivo(archivo_path)
            
        except Exception as e:
            print(f"❌ Error general explorando {nombre_archivo}: {e}")
    
    def buscar_radicados_en_archivo(self, archivo_path):
        """Busca patrones de radicados en el archivo"""
        try:
            # Leer sin header para ver datos raw
            df_raw = pd.read_excel(archivo_path, header=None)
            
            print("   🔍 Buscando patrones de radicado...")
            
            # Buscar celdas que contengan patrones de radicado
            radicados_encontrados = []
            
            for row_idx in range(min(10, len(df_raw))):  # Revisar primeras 10 filas
                for col_idx in range(len(df_raw.columns)):
                    cell_value = str(df_raw.iloc[row_idx, col_idx])
                    
                    # Patrones de radicado
                    if (('-' in cell_value and len(cell_value) > 10) or 
                        ('CM' in cell_value) or 
                        (len(cell_value) > 15 and any(c.isdigit() for c in cell_value))):
                        
                        radicados_encontrados.append({
                            'fila': row_idx,
                            'columna': col_idx,
                            'valor': cell_value
                        })
            
            if radicados_encontrados:
                print("   ✅ Posibles radicados encontrados:")
                for item in radicados_encontrados[:10]:  # Mostrar máximo 10
                    print(f"      Fila {item['fila']}, Col {item['columna']}: '{item['valor']}'")
            else:
                print("   ❌ No se encontraron patrones de radicado evidentes")
                
        except Exception as e:
            print(f"   ❌ Error buscando radicados: {e}")
    
    def explorar_ambos_archivos(self):
        """Explora ambos archivos Excel"""
        print("🔍 EXPLORADOR DE ARCHIVOS EXCEL")
        print("=" * 80)
        
        # Explorar estados.xlsx
        self.explorar_archivo(self.estados_file, "estados.xlsx")
        print("\n" + "=" * 80)
        
        # Explorar ingresos_al_despacho_act.xlsx
        self.explorar_archivo(self.ingresos_file, "ingresos_al_despacho_act.xlsx")
        print("\n" + "=" * 80)
        
        print("✅ EXPLORACIÓN COMPLETADA")
        print("\nUsa esta información para:")
        print("1. Identificar la fila correcta de encabezados")
        print("2. Encontrar las columnas que contienen radicados")
        print("3. Ajustar el limpiador con los nombres correctos")

def main():
    """Función principal"""
    explorer = ExcelExplorer()
    explorer.explorar_ambos_archivos()

if __name__ == "__main__":
    main()