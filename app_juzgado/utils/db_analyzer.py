#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizador de base de datos para verificar compatibilidad con radicados limpios
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

class DatabaseAnalyzer:
    """Analizador de estructura de base de datos"""
    
    def __init__(self):
        self.conn = None
        
    def conectar(self):
        """Conectar a la base de datos"""
        try:
            self.conn = obtener_conexion()
            print("✅ Conexión a base de datos exitosa")
            return True
        except Exception as e:
            print(f"❌ Error conectando a BD: {e}")
            return False
    
    def analizar_tabla_expedientes(self):
        """Analiza la estructura de la tabla expedientes"""
        print("🔍 Analizando tabla expedientes...")
        
        try:
            cursor = self.conn.cursor()
            
            # Obtener estructura de la tabla
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'expedientes'
                ORDER BY ordinal_position
            """)
            
            columnas = cursor.fetchall()
            
            print("   📋 Estructura actual:")
            for col in columnas:
                nombre, tipo, longitud, nullable = col
                longitud_str = f"({longitud})" if longitud else ""
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"      - {nombre}: {tipo}{longitud_str} {nullable_str}")
            
            # Verificar campos relacionados con radicados
            campos_radicado = [col for col in columnas if 'radicado' in col[0].lower()]
            
            print("   🔍 Campos relacionados con radicados:")
            for campo in campos_radicado:
                nombre, tipo, longitud, nullable = campo
                print(f"      - {nombre}: {tipo}({longitud}) - Longitud máxima: {longitud}")
            
            # Analizar datos existentes
            cursor.execute("SELECT COUNT(*) FROM expedientes")
            total_expedientes = cursor.fetchone()[0]
            
            print(f"   📊 Total expedientes en BD: {total_expedientes}")
            
            # Analizar longitudes de radicados existentes
            if total_expedientes > 0:
                cursor.execute("""
                    SELECT 
                        MIN(LENGTH(radicado_completo)) as min_length,
                        MAX(LENGTH(radicado_completo)) as max_length,
                        AVG(LENGTH(radicado_completo)) as avg_length
                    FROM expedientes 
                    WHERE radicado_completo IS NOT NULL
                """)
                
                stats = cursor.fetchone()
                if stats and stats[0]:
                    print(f"   📏 Longitudes de radicados actuales:")
                    print(f"      - Mínima: {stats[0]} caracteres")
                    print(f"      - Máxima: {stats[1]} caracteres") 
                    print(f"      - Promedio: {stats[2]:.1f} caracteres")
            
            cursor.close()
            return campos_radicado
            
        except Exception as e:
            print(f"   ❌ Error analizando tabla: {e}")
            return []
    
    def verificar_necesidad_cambios(self, campos_radicado):
        """Verifica si necesitamos cambios en la BD"""
        print("🔧 Verificando necesidad de cambios...")
        
        cambios_necesarios = []
        
        # Verificar si existe campo para radicado limpio
        tiene_radicado_limpio = any('limpio' in campo[0].lower() for campo in campos_radicado)
        
        if not tiene_radicado_limpio:
            cambios_necesarios.append({
                'tipo': 'agregar_columna',
                'descripcion': 'Agregar columna radicado_limpio para búsquedas optimizadas',
                'sql': 'ALTER TABLE expedientes ADD COLUMN radicado_limpio VARCHAR(50);'
            })
        
        # Verificar longitudes de campos existentes
        for campo in campos_radicado:
            nombre, tipo, longitud, nullable = campo
            if longitud and longitud < 50:  # Los radicados limpios pueden ser largos
                cambios_necesarios.append({
                    'tipo': 'modificar_longitud',
                    'descripcion': f'Aumentar longitud de {nombre} para radicados largos',
                    'sql': f'ALTER TABLE expedientes ALTER COLUMN {nombre} TYPE VARCHAR(100);'
                })
        
        # Verificar índices para optimización
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'expedientes' 
                AND indexdef LIKE '%radicado%'
            """)
            
            indices = cursor.fetchall()
            
            if not indices:
                cambios_necesarios.append({
                    'tipo': 'agregar_indice',
                    'descripcion': 'Agregar índice en radicado_limpio para búsquedas rápidas',
                    'sql': 'CREATE INDEX idx_expedientes_radicado_limpio ON expedientes(radicado_limpio);'
                })
            
            cursor.close()
            
        except Exception as e:
            print(f"   ⚠️ No se pudieron verificar índices: {e}")
        
        return cambios_necesarios
    
    def generar_script_migracion(self, cambios):
        """Genera script SQL para aplicar cambios"""
        if not cambios:
            print("   ✅ No se necesitan cambios en la base de datos")
            return None
        
        print(f"   📝 Se necesitan {len(cambios)} cambios:")
        
        script_sql = "-- Script de migración para soporte de radicados limpios\n"
        script_sql += f"-- Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for i, cambio in enumerate(cambios, 1):
            print(f"      {i}. {cambio['descripcion']}")
            script_sql += f"-- {cambio['descripcion']}\n"
            script_sql += f"{cambio['sql']}\n\n"
        
        # Guardar script
        script_path = "migracion_radicados.sql"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_sql)
        
        print(f"   💾 Script guardado en: {script_path}")
        return script_path
    
    def ejecutar_analisis_completo(self):
        """Ejecuta análisis completo de la base de datos"""
        print("🔍 ANÁLISIS DE BASE DE DATOS PARA RADICADOS")
        print("=" * 50)
        
        if not self.conectar():
            return False
        
        try:
            # Analizar tabla expedientes
            campos_radicado = self.analizar_tabla_expedientes()
            print()
            
            # Verificar cambios necesarios
            cambios = self.verificar_necesidad_cambios(campos_radicado)
            print()
            
            # Generar script si es necesario
            if cambios:
                script_path = self.generar_script_migracion(cambios)
                print()
                print("⚠️  ACCIÓN REQUERIDA:")
                print(f"   1. Revisar script: {script_path}")
                print("   2. Hacer backup de la base de datos")
                print("   3. Ejecutar script en entorno de prueba")
                print("   4. Ejecutar script en producción")
            else:
                print("✅ Base de datos lista para radicados limpios")
            
            print("=" * 50)
            return True
            
        except Exception as e:
            print(f"❌ Error en análisis: {e}")
            return False
        
        finally:
            if self.conn:
                self.conn.close()

def main():
    """Función principal"""
    analyzer = DatabaseAnalyzer()
    analyzer.ejecutar_analisis_completo()

if __name__ == "__main__":
    from datetime import datetime
    main()