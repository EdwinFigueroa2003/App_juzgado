#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Limpiador de archivos Excel para normalización de radicados
"""

import pandas as pd
import re
import os
from datetime import datetime

class ExcelCleaner:
    """Limpiador de archivos Excel para radicados"""
    
    def __init__(self, archivos_path="Archivos/Otros"):
        self.archivos_path = archivos_path
        self.estados_file = os.path.join(archivos_path, "estados.xlsx")
        self.ingresos_file = os.path.join(archivos_path, "ingresos_al_despacho_act.xlsx")
        
    def limpiar_radicado_estados(self, radicado):
        """
        Limpia radicado del archivo estados.xlsx
        Ejemplo: '08001-40-03-012-2015-00629-00' -> '080014003012201500629000'
        """
        if pd.isna(radicado) or radicado == "":
            return ""
        
        # Convertir a string y quitar guiones
        radicado_str = str(radicado).strip()
        radicado_limpio = radicado_str.replace("-", "")
        
        return radicado_limpio
    
    def limpiar_radicado_ingresos(self, radicado):
        """
        Limpia radicado del archivo ingresos_al_despacho_act.xlsx
        Ejemplos: 
        - '11 CM-2011-00407' -> '11201100407'
        - '04-2015-01125' -> '04201501125'
        """
        if pd.isna(radicado) or radicado == "":
            return ""
        
        # Convertir a string
        radicado_str = str(radicado).strip()
        
        # Quitar espacios, guiones y letras (mantener solo números)
        radicado_limpio = re.sub(r'[^0-9]', '', radicado_str)
        
        return radicado_limpio
    
    def procesar_estados(self):
        """Procesa el archivo estados.xlsx"""
        print("📁 Procesando estados.xlsx...")
        
        try:
            # Leer archivo Excel - probar diferentes configuraciones
            df = pd.read_excel(self.estados_file)
            
            print(f"   ✅ Archivo leído: {len(df)} filas")
            print(f"   📋 Columnas: {list(df.columns)}")
            
            # Si las columnas son 'Unnamed', intentar leer desde fila 1 o 2
            if any('Unnamed' in str(col) for col in df.columns):
                print("   🔄 Detectado formato con encabezados no estándar, intentando alternativas...")
                
                # Intentar leer desde fila 1
                try:
                    df_alt1 = pd.read_excel(self.estados_file, header=1)
                    print(f"   📋 Columnas (header=1): {list(df_alt1.columns)}")
                    
                    # Buscar columna que contenga radicados
                    for col in df_alt1.columns:
                        if any(keyword in str(col).lower() for keyword in ['radicac', 'radicado', 'expediente']):
                            print(f"   ✅ Encontrada columna de radicados: '{col}'")
                            df = df_alt1
                            columna_radicado = col
                            break
                    else:
                        # Si no encuentra por nombre, buscar por contenido
                        print("   🔍 Buscando columna por contenido...")
                        for col in df_alt1.columns:
                            # Verificar si la columna contiene patrones de radicado
                            sample_values = df_alt1[col].dropna().head(5).astype(str)
                            if any('-' in str(val) and len(str(val)) > 10 for val in sample_values):
                                print(f"   ✅ Encontrada columna de radicados por patrón: '{col}'")
                                df = df_alt1
                                columna_radicado = col
                                break
                        else:
                            # Intentar con header=2
                            df_alt2 = pd.read_excel(self.estados_file, header=2)
                            print(f"   📋 Columnas (header=2): {list(df_alt2.columns)}")
                            
                            for col in df_alt2.columns:
                                if any(keyword in str(col).lower() for keyword in ['radicac', 'radicado', 'expediente']):
                                    print(f"   ✅ Encontrada columna de radicados: '{col}'")
                                    df = df_alt2
                                    columna_radicado = col
                                    break
                            else:
                                # Mostrar primeras filas para análisis manual
                                print("   📊 Primeras 5 filas para análisis:")
                                print(df.head().to_string())
                                
                                print("   ❓ No se pudo identificar automáticamente la columna de radicados.")
                                print("   📋 Columnas disponibles:")
                                for i, col in enumerate(df.columns):
                                    sample = df[col].dropna().head(3).tolist()
                                    print(f"      {i}: '{col}' - Ejemplos: {sample}")
                                
                                return None
                                
                except Exception as e:
                    print(f"   ⚠️ Error probando headers alternativos: {e}")
                    return None
            else:
                # Buscar columna de radicación en columnas normales
                columna_radicado = None
                for col in df.columns:
                    if any(keyword in str(col).lower() for keyword in ['radicac', 'radicado', 'expediente']):
                        columna_radicado = col
                        break
                
                if not columna_radicado:
                    print("   ❌ ERROR: No se encontró columna de radicados")
                    return None
            
            # Crear copia del DataFrame
            df_limpio = df.copy()
            
            # Limpiar radicados
            df_limpio['Radicado_Limpio'] = df_limpio[columna_radicado].apply(self.limpiar_radicado_estados)
            
            # Estadísticas de limpieza
            total_filas = len(df_limpio)
            filas_vacias = df_limpio['Radicado_Limpio'].eq('').sum()
            filas_limpias = total_filas - filas_vacias
            
            print(f"   📊 Estadísticas:")
            print(f"      - Columna usada: '{columna_radicado}'")
            print(f"      - Total filas: {total_filas}")
            print(f"      - Radicados limpios: {filas_limpias}")
            print(f"      - Radicados vacíos: {filas_vacias}")
            
            # Mostrar ejemplos
            print(f"   🔍 Ejemplos de limpieza:")
            ejemplos_mostrados = 0
            for i in range(len(df_limpio)):
                original = df_limpio.iloc[i][columna_radicado]
                limpio = df_limpio.iloc[i]['Radicado_Limpio']
                if pd.notna(original) and original != "" and limpio != "":
                    print(f"      '{original}' -> '{limpio}'")
                    ejemplos_mostrados += 1
                    if ejemplos_mostrados >= 5:
                        break
            
            return df_limpio
            
        except Exception as e:
            print(f"   ❌ ERROR procesando estados.xlsx: {e}")
            return None
    
    def procesar_ingresos(self):
        """Procesa el archivo ingresos_al_despacho_act.xlsx"""
        print("📁 Procesando ingresos_al_despacho_act.xlsx...")
        
        try:
            # Leer archivo Excel
            df = pd.read_excel(self.ingresos_file)
            
            print(f"   ✅ Archivo leído: {len(df)} filas")
            print(f"   📋 Columnas: {list(df.columns)}")
            
            # Verificar que existe la columna RADICADO MODIFICADO
            if 'RADICADO MODIFICADO' not in df.columns:
                print("   ❌ ERROR: No se encontró la columna 'RADICADO MODIFICADO'")
                print(f"   📋 Columnas disponibles: {list(df.columns)}")
                return None
            
            # Crear copia del DataFrame
            df_limpio = df.copy()
            
            # Limpiar radicados
            df_limpio['Radicado_Limpio'] = df_limpio['RADICADO MODIFICADO'].apply(self.limpiar_radicado_ingresos)
            
            # Estadísticas de limpieza
            total_filas = len(df_limpio)
            filas_vacias = df_limpio['Radicado_Limpio'].eq('').sum()
            filas_limpias = total_filas - filas_vacias
            
            print(f"   📊 Estadísticas:")
            print(f"      - Total filas: {total_filas}")
            print(f"      - Radicados limpios: {filas_limpias}")
            print(f"      - Radicados vacíos: {filas_vacias}")
            
            # Mostrar ejemplos
            print(f"   🔍 Ejemplos de limpieza:")
            for i in range(min(5, len(df_limpio))):
                original = df_limpio.iloc[i]['RADICADO MODIFICADO']
                limpio = df_limpio.iloc[i]['Radicado_Limpio']
                if pd.notna(original) and original != "":
                    print(f"      '{original}' -> '{limpio}'")
            
            return df_limpio
            
        except Exception as e:
            print(f"   ❌ ERROR procesando ingresos_al_despacho_act.xlsx: {e}")
            return None
    
    def guardar_archivos_limpios(self, df_estados, df_ingresos):
        """Guarda los archivos limpios"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Guardar estados limpio
            if df_estados is not None:
                estados_limpio_path = os.path.join(self.archivos_path, f"estados_limpio_{timestamp}.xlsx")
                df_estados.to_excel(estados_limpio_path, index=False)
                print(f"   ✅ Estados limpio guardado: {estados_limpio_path}")
            
            # Guardar ingresos limpio
            if df_ingresos is not None:
                ingresos_limpio_path = os.path.join(self.archivos_path, f"ingresos_limpio_{timestamp}.xlsx")
                df_ingresos.to_excel(ingresos_limpio_path, index=False)
                print(f"   ✅ Ingresos limpio guardado: {ingresos_limpio_path}")
                
        except Exception as e:
            print(f"   ❌ ERROR guardando archivos: {e}")
    
    def analizar_cruces(self, df_estados, df_ingresos):
        """Analiza los cruces posibles entre archivos"""
        print("🔍 Analizando cruces de información...")
        
        if df_estados is None or df_ingresos is None:
            print("   ❌ No se pueden analizar cruces: archivos faltantes")
            return
        
        # Obtener radicados únicos
        radicados_estados = set(df_estados['Radicado_Limpio'].dropna())
        radicados_ingresos = set(df_ingresos['Radicado_Limpio'].dropna())
        
        # Análisis de cruces
        cruces_comunes = radicados_estados.intersection(radicados_ingresos)
        solo_estados = radicados_estados - radicados_ingresos
        solo_ingresos = radicados_ingresos - radicados_estados
        
        print(f"   📊 Análisis de cruces:")
        print(f"      - Radicados en estados: {len(radicados_estados)}")
        print(f"      - Radicados en ingresos: {len(radicados_ingresos)}")
        print(f"      - Cruces comunes: {len(cruces_comunes)}")
        print(f"      - Solo en estados: {len(solo_estados)}")
        print(f"      - Solo en ingresos: {len(solo_ingresos)}")
        
        # Mostrar algunos ejemplos de cruces
        if cruces_comunes:
            print(f"   🔍 Ejemplos de cruces exitosos:")
            for i, radicado in enumerate(list(cruces_comunes)[:5]):
                print(f"      - {radicado}")
        
        return {
            'cruces_comunes': len(cruces_comunes),
            'solo_estados': len(solo_estados),
            'solo_ingresos': len(solo_ingresos),
            'total_estados': len(radicados_estados),
            'total_ingresos': len(radicados_ingresos)
        }
    
    def ejecutar_limpieza_completa(self):
        """Ejecuta el proceso completo de limpieza"""
        print("🧹 INICIANDO LIMPIEZA COMPLETA DE ARCHIVOS EXCEL")
        print("=" * 60)
        
        # Verificar que existen los archivos
        if not os.path.exists(self.estados_file):
            print(f"❌ ERROR: No se encontró {self.estados_file}")
            return False
            
        if not os.path.exists(self.ingresos_file):
            print(f"❌ ERROR: No se encontró {self.ingresos_file}")
            return False
        
        # Procesar archivos
        df_estados = self.procesar_estados()
        print()
        df_ingresos = self.procesar_ingresos()
        print()
        
        # Analizar cruces
        estadisticas = self.analizar_cruces(df_estados, df_ingresos)
        print()
        
        # Guardar archivos limpios
        print("💾 Guardando archivos limpios...")
        self.guardar_archivos_limpios(df_estados, df_ingresos)
        print()
        
        print("✅ LIMPIEZA COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        
        return True, df_estados, df_ingresos, estadisticas

def main():
    """Función principal para ejecutar la limpieza"""
    cleaner = ExcelCleaner()
    resultado = cleaner.ejecutar_limpieza_completa()
    
    if resultado:
        print("🎉 Proceso completado. Archivos limpios generados.")
    else:
        print("❌ Error en el proceso de limpieza.")

if __name__ == "__main__":
    main()