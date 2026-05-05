"""
Cargador de datos consolidado para sistema de juzgado
Implementa carga completa de todos los radicados de los tres archivos fuente
"""

import pandas as pd
import os
import re
import sys
from datetime import datetime

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

class CargadorDatosMejorado:
    """Cargador de datos consolidado que procesa todos los radicados de los tres archivos"""
    
    def __init__(self):
        # Rutas de los archivos
        self.listado_final_path = "app_juzgado/Archivos/Listado_Final_Cruzado_20251105_161151.xlsx"
        self.ingresos_path = "app_juzgado/Archivos/Otros/ingresos_al_despacho_act.xlsx"
        self.estados_path = "app_juzgado/Archivos/Otros/estados.xlsx"
        
        # Contadores
        self.stats = {
            'expedientes_cargados': 0,
            'ingresos_cargados': 0,
            'estados_cargados': 0,
            'errores': 0,
            'inconsistencias_ingresos': 0,
            'inconsistencias_estados': 0
        }
        
        # Mapa de radicados a expediente_id (se carga después de insertar expedientes)
        self.mapa_radicados = {}
        
        # Lista de inconsistencias para auditoría
        self.inconsistencias = []
    
    def limpiar_radicado(self, radicado):
        """Limpia un radicado para extraer solo números"""
        if pd.isna(radicado) or radicado == "":
            return None
        
        # Convertir a string y limpiar
        radicado_str = str(radicado).strip()
        # Extraer solo números
        numeros = re.sub(r'[^0-9]', '', radicado_str)
        
        # Verificar que no esté vacío
        if numeros:
            # Para radicados muy largos, usar solo los últimos 23 dígitos (radicado completo)
            if len(numeros) > 23:
                numeros = numeros[-23:]
            # IMPORTANTE: Devolver como STRING para preservar ceros a la izquierda
            return numeros
        return None
    
    def safe_str(self, value, max_length=None):
        """Convierte un valor a string de forma segura"""
        if pd.isna(value):
            return None
        
        result = str(value).strip()
        if max_length and len(result) > max_length:
            result = result[:max_length]
        
        return result if result else None
    
    def safe_date(self, value):
        """Convierte un valor a fecha de forma segura"""
        if pd.isna(value):
            return None
        
        if isinstance(value, datetime):
            return value.date()
        
        try:
            # Intentar parsear como fecha
            if isinstance(value, str):
                return pd.to_datetime(value).date()
            return value
        except:
            return None
    
    def registrar_inconsistencia(self, tipo, archivo, hoja, fila, radicado, motivo, datos_adicionales=None):
        """Registra una inconsistencia para auditoría posterior"""
        inconsistencia = {
            'tipo': tipo,  # 'INGRESO' o 'ESTADO'
            'archivo': archivo,
            'hoja': hoja,
            'fila': fila,
            'radicado': radicado,
            'motivo': motivo,
            'datos_adicionales': datos_adicionales or {},
            'timestamp': datetime.now()
        }
        self.inconsistencias.append(inconsistencia)
        
        if tipo == 'INGRESO':
            self.stats['inconsistencias_ingresos'] += 1
        else:
            self.stats['inconsistencias_estados'] += 1
    
    def registrar_error(self, tipo, archivo, hoja, fila, error, datos_fila=None):
        """Registra un error técnico detallado"""
        error_detalle = {
            'tipo': tipo,
            'archivo': archivo,
            'hoja': hoja,
            'fila': fila,
            'error': str(error),
            'datos_fila': datos_fila or {},
            'timestamp': datetime.now()
        }
        
        # Agregar a la lista de inconsistencias para el reporte
        self.inconsistencias.append({
            'tipo': f'ERROR_{tipo}',
            'archivo': archivo,
            'hoja': hoja,
            'fila': fila,
            'radicado': datos_fila.get('radicado', 'N/A') if datos_fila else 'N/A',
            'motivo': f'Error técnico: {str(error)}',
            'datos_adicionales': datos_fila or {},
            'timestamp': datetime.now()
        })
        
        self.stats['errores'] += 1
    
    def limpiar_base_datos(self):
        """Limpia todas las tablas de la base de datos en el orden correcto"""
        print("🧹 LIMPIANDO BASE DE DATOS...")
        
        conn = None
        cursor = None
        
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            # Limpiar en orden inverso de dependencias (de hijos a padres)
            print("   🗑️ Limpiando tabla actuaciones...")
            cursor.execute("DELETE FROM actuaciones")
            
            print("   🗑️ Limpiando tabla estados...")
            cursor.execute("DELETE FROM estados")
            
            print("   🗑️ Limpiando tabla ingresos...")
            cursor.execute("DELETE FROM ingresos")
            
            print("   🗑️ Limpiando tabla expediente...")
            cursor.execute("DELETE FROM expediente")
            
            conn.commit()
            print("   ✅ Base de datos limpiada correctamente")
            return True
            
        except Exception as e:
            print(f"   ❌ Error limpiando base de datos: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def cargar_mapa_radicados(self):
        """Carga el mapa de radicados → expediente_id desde la base de datos"""
        print("🗺️ Cargando mapa de radicados...")
        
        conn = None
        cursor = None
        
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            # Obtener todos los radicados y sus IDs
            cursor.execute("SELECT id, radicado_completo FROM expediente WHERE radicado_completo IS NOT NULL")
            resultados = cursor.fetchall()
            
            # Crear el mapa
            self.mapa_radicados = {radicado: expediente_id for expediente_id, radicado in resultados}
            
            print(f"   ✅ Mapa cargado con {len(self.mapa_radicados)} radicados")
            return True
            
        except Exception as e:
            print(f"   ❌ Error cargando mapa: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def buscar_expediente_por_radicado(self, radicado_completo, demandante_nuevo=None, demandado_nuevo=None):
        """
        Busca un expediente por radicado con validación de últimos 13 dígitos Y similitud de nombres.
        
        VALIDACIONES:
        1. Búsqueda exacta en el mapa de radicados
        2. Búsqueda por últimos 13 dígitos en la BD con validación de demandante/demandado similares
        
        Si se proporcionan demandante_nuevo y demandado_nuevo, se valida también que sean similares
        a los datos del expediente encontrado para mayor confiabilidad.
        
        Returns:
            expediente_id si se encuentra, None si no existe
        """
        if not radicado_completo:
            return None
        
        # VALIDACIÓN 1: Búsqueda exacta en el mapa
        expediente_id = self.mapa_radicados.get(radicado_completo)
        if expediente_id:
            return expediente_id
        
        # VALIDACIÓN 2: Búsqueda por últimos 13 dígitos en la BD
        if len(str(radicado_completo)) >= 13:
            try:
                conn = obtener_conexion()
                cursor = conn.cursor()
                
                # Buscar TODOS los expedientes con los últimos 13 dígitos coincidentes
                # para poder validar por similitud de nombres
                # Buscar candidatos usando RIGHT y LIKE para capturar subcadenas
                ultimos_13_param = str(radicado_completo)[-13:]
                like_full = f"%{str(radicado_completo)}%"
                like_ult13 = f"%{ultimos_13_param}%"
                cursor.execute("""
                    SELECT id, radicado_completo, demandante, demandado FROM expediente 
                    WHERE radicado_completo IS NOT NULL 
                    AND (
                        (LENGTH(radicado_completo) >= 13 AND RIGHT(radicado_completo, 13) = RIGHT(%s, 13))
                        OR radicado_completo LIKE %s
                        OR radicado_completo LIKE %s
                    )
                    ORDER BY LENGTH(radicado_completo) DESC
                """, (str(radicado_completo), like_full, like_ult13))
                
                resultados = cursor.fetchall()
                
                if resultados:
                    # Si hay resultados, priorizar por similitud de nombres
                    mejor_match = None
                    mejor_score = 0
                    
                    for expediente_id, radicado_encontrado, demandante_bd, demandado_bd in resultados:
                        score = 100  # Score base por coincidencia de radicado
                        
                        # Si tenemos nombres nuevos para validar, mejorar score si son similares
                        if demandante_nuevo and demandante_bd:
                            if self.nombres_similares(demandante_nuevo, demandante_bd, umbral=0.6):
                                score += 50
                                print(f"      ✅ Demandante similar: '{demandante_nuevo}' ≈ '{demandante_bd}'")
                        
                        if demandado_nuevo and demandado_bd:
                            if self.nombres_similares(demandado_nuevo, demandado_bd, umbral=0.6):
                                score += 50
                                print(f"      ✅ Demandado similar: '{demandado_nuevo}' ≈ '{demandado_bd}'")
                        
                        # Bonus por radicado más largo (23 dígitos es prioritario)
                        if len(radicado_encontrado) == 23:
                            score += 30
                        elif len(radicado_encontrado) >= 13:
                            score += 10
                        
                        if score > mejor_score:
                            mejor_score = score
                            mejor_match = (expediente_id, radicado_encontrado)
                    
                    if mejor_match:
                        expediente_id, radicado_encontrado = mejor_match
                        # Actualizar el mapa para futuras búsquedas
                        self.mapa_radicados[radicado_completo] = expediente_id
                        print(f"   🔍 Encontrado por últimos 13 dígitos: {radicado_completo} → {radicado_encontrado} (score: {mejor_score})")
                        return expediente_id
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                print(f"   ⚠️ Error buscando por últimos 13 dígitos: {e}")
        
        return None
    
    def cargar_ingresos(self):
        """Carga datos de ingresos con manejo de inconsistencias"""
        print("📋 Cargando Ingresos a tabla 'ingresos'...")
        
        if not os.path.exists(self.ingresos_path):
            print(f"❌ Archivo no encontrado: {self.ingresos_path}")
            return False
        
        # Asegurar que el mapa de radicados esté cargado
        if not self.mapa_radicados:
            if not self.cargar_mapa_radicados():
                return False
        
        conn = None
        cursor = None
        
        try:
            # NO limpiar tabla aquí - ya se limpió en cargar_expedientes_consolidados
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            # Leer todas las hojas del archivo (solo las que contienen "Ingresos")
            excel_file = pd.ExcelFile(self.ingresos_path)
            hojas_ingresos = [h for h in excel_file.sheet_names if 'Ingresos' in h]
            hojas_procesadas = 0
            
            for sheet_name in hojas_ingresos:
                print(f"   🔄 Procesando hoja: {sheet_name}")
                
                try:
                    df = pd.read_excel(self.ingresos_path, sheet_name=sheet_name)
                    batch_count = 0
                    batch_size = 50
                    
                    # Procesar cada fila
                    for index, row in df.iterrows():
                        try:
                            # Usar RADICADO MODIFICADO como fuente principal
                            radicado_original = row.get('RADICADO MODIFICADO', '')
                            radicado_limpio = self.limpiar_radicado(radicado_original)
                            
                            if radicado_limpio:
                                # Extraer demandante y demandado para validación de similitud
                                demandante_ingreso = row.get('DEMANDANTE', '')
                                demandado_ingreso = row.get('DEMANDADO', '')
                                
                                # Buscar expediente_id con validación de últimos 13 dígitos Y similitud de nombres
                                expediente_id = self.buscar_expediente_por_radicado(
                                    radicado_limpio,
                                    demandante_nuevo=demandante_ingreso,
                                    demandado_nuevo=demandado_ingreso
                                )
                                
                                if expediente_id:
                                    # Radicado existe en expedientes, proceder con la inserción
                                    datos = (
                                        expediente_id,  # expediente_id
                                        self.safe_date(row.get('FECHA DE INGRESO')),  # fecha_ingreso
                                        self.safe_str(row.get('SOLICITUD'), 255),  # motivo_ingreso
                                        self.safe_str(row.get('OBSERVACIONES')),  # observaciones_ingreso
                                        self.safe_str(row.get('J. ORIGEN'), 255),  # juzgado_origen
                                        radicado_limpio,  # radicado_completo
                                        radicado_limpio  # radicado_corto
                                    )
                                    
                                    cursor.execute("""
                                        INSERT INTO ingresos (expediente_id, fecha_ingreso, 
                                                                       motivo_ingreso, observaciones_ingreso,
                                                                       juzgado_origen, radicado_completo, radicado_corto)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    """, datos)
                                    
                                    self.stats['ingresos_cargados'] += 1
                                    batch_count += 1
                                    
                                    # Commit cada lote
                                    if batch_count >= batch_size:
                                        conn.commit()
                                        batch_count = 0
                                else:
                                    # Radicado no existe en expedientes, registrar inconsistencia
                                    self.registrar_inconsistencia(
                                        tipo='INGRESO',
                                        archivo='ingresos_al_despacho_act.xlsx',
                                        hoja=sheet_name,
                                        fila=index + 2,  # +2 porque Excel empieza en 1 y hay header
                                        radicado=str(radicado_original),
                                        motivo=f'Radicado {radicado_limpio} no existe en tabla expediente',
                                        datos_adicionales={
                                            'demandante': row.get('DEMANDANTE', ''),
                                            'demandado': row.get('DEMANDADO', ''),
                                            'fecha_ingreso': str(row.get('FECHA DE INGRESO', '')),
                                            'solicitud': row.get('SOLICITUD', ''),
                                            'juzgado_origen': row.get('J. ORIGEN', ''),
                                            'observaciones': row.get('OBSERVACIONES', '')
                                        }
                                    )
                        
                        except Exception as e:
                            # Registrar error detallado
                            self.registrar_error(
                                tipo='INGRESO',
                                archivo='ingresos_al_despacho_act.xlsx',
                                hoja=sheet_name,
                                fila=index + 2,
                                error=e,
                                datos_fila={
                                    'radicado_original': row.get('RADICADO MODIFICADO', ''),
                                    'demandante': row.get('DEMANDANTE', ''),
                                    'demandado': row.get('DEMANDADO', ''),
                                    'fecha_ingreso': str(row.get('FECHA DE INGRESO', '')),
                                    'solicitud': row.get('SOLICITUD', ''),
                                    'juzgado_origen': row.get('J. ORIGEN', '')
                                }
                            )
                            conn.rollback()
                            batch_count = 0
                            continue
                    
                    # Commit final del sheet
                    conn.commit()
                    hojas_procesadas += 1
                    
                except Exception as e:
                    print(f"      ❌ Error procesando hoja {sheet_name}: {e}")
                    conn.rollback()
                    continue
            
            print(f"   ✅ Hojas procesadas: {hojas_procesadas}")
            print(f"   ✅ Ingresos cargados: {self.stats['ingresos_cargados']}")
            print(f"   ⚠️ Inconsistencias encontradas: {self.stats['inconsistencias_ingresos']}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error cargando ingresos: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def cargar_estados(self):
        """Carga datos de estados con manejo de inconsistencias"""
        print("📋 Cargando Estados a tabla 'estados'...")
        
        if not os.path.exists(self.estados_path):
            print(f"❌ Archivo no encontrado: {self.estados_path}")
            return False
        
        # Asegurar que el mapa de radicados esté cargado
        if not self.mapa_radicados:
            if not self.cargar_mapa_radicados():
                return False
        
        conn = None
        cursor = None
        
        try:
            # NO limpiar tabla aquí - ya se limpió en cargar_expedientes_consolidados
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            # Leer todas las hojas del archivo (solo las que contienen trimestres)
            excel_file = pd.ExcelFile(self.estados_path)
            hojas_estados = [h for h in excel_file.sheet_names if 'Q' in h and ('2023' in h or '2024' in h or '2025' in h)]
            hojas_procesadas = 0
            
            for sheet_name in hojas_estados:
                print(f"   🔄 Procesando hoja: {sheet_name}")
                
                try:
                    df = pd.read_excel(self.estados_path, sheet_name=sheet_name)
                    batch_count = 0
                    batch_size = 50
                    
                    # Procesar cada fila
                    for index, row in df.iterrows():
                        try:
                            # Usar RADICADO COMPLETO como fuente principal
                            radicado_original = row.get('RADICADO COMPLETO', '')
                            radicado_limpio = self.limpiar_radicado(radicado_original)
                            
                            if radicado_limpio:
                                # Extraer demandante para validación de similitud
                                demandante_estado = row.get('Demandante', '')
                                
                                # Buscar expediente_id con validación de últimos 13 dígitos Y similitud de demandante
                                expediente_id = self.buscar_expediente_por_radicado(
                                    radicado_limpio,
                                    demandante_nuevo=demandante_estado
                                )
                                
                                if expediente_id:
                                    # Radicado existe en expedientes, proceder con la inserción
                                    datos = (
                                        expediente_id,  # expediente_id
                                        self.safe_date(row.get('Fecha Estado')),  # fecha_estado
                                        self.safe_str(row.get('Clase'), 255),  # clase
                                        self.safe_str(row.get('Demandante'), 255),  # demandante
                                        self.safe_str(row.get('Auto / Anotación'), 255),  # auto_anotacion
                                        radicado_limpio  # radicado_corto
                                    )
                                    
                                    cursor.execute("""
                                        INSERT INTO estados (expediente_id, fecha_estado, 
                                                                       clase, demandante, auto_anotacion, radicado_corto)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """, datos)
                                    
                                    self.stats['estados_cargados'] += 1
                                    batch_count += 1
                                    
                                    # Commit cada lote
                                    if batch_count >= batch_size:
                                        conn.commit()
                                        batch_count = 0
                                else:
                                    # Radicado no existe en expedientes, registrar inconsistencia
                                    self.registrar_inconsistencia(
                                        tipo='ESTADO',
                                        archivo='estados.xlsx',
                                        hoja=sheet_name,
                                        fila=index + 2,  # +2 porque Excel empieza en 1 y hay header
                                        radicado=str(radicado_original),
                                        motivo=f'Radicado {radicado_limpio} no existe en tabla expediente',
                                        datos_adicionales={
                                            'clase': row.get('Clase', ''),
                                            'demandante': row.get('Demandante', ''),
                                            'fecha_estado': str(row.get('Fecha Estado', '')),
                                            'auto_anotacion': row.get('Auto / Anotación', ''),
                                            'radicacion': row.get('RADICADO COMPLETO', '')
                                        }
                                    )
                        
                        except Exception as e:
                            # Registrar error detallado
                            self.registrar_error(
                                tipo='ESTADO',
                                archivo='estados.xlsx',
                                hoja=sheet_name,
                                fila=index + 2,
                                error=e,
                                datos_fila={
                                    'radicado_original': row.get('RADICADO COMPLETO', ''),
                                    'clase': row.get('Clase', ''),
                                    'demandante': row.get('Demandante', ''),
                                    'fecha_estado': str(row.get('Fecha Estado', '')),
                                    'auto_anotacion': row.get('Auto / Anotación', ''),
                                    'radicacion': row.get('Radicación', '')
                                }
                            )
                            conn.rollback()
                            batch_count = 0
                            continue
                    
                    # Commit final del sheet
                    conn.commit()
                    hojas_procesadas += 1
                    
                except Exception as e:
                    print(f"      ❌ Error procesando hoja {sheet_name}: {e}")
                    conn.rollback()
                    continue
            
            print(f"   ✅ Hojas procesadas: {hojas_procesadas}")
            print(f"   ✅ Estados cargados: {self.stats['estados_cargados']}")
            print(f"   ⚠️ Inconsistencias encontradas: {self.stats['inconsistencias_estados']}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error cargando estados: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def generar_reporte_inconsistencias(self):
        """Genera un reporte detallado de errores técnicos en formato TXT"""
        if not self.inconsistencias:
            print("   ✅ No se encontraron errores técnicos")
            return
        
        print(f"📄 Generando reporte de errores técnicos...")
        
        try:
            # Generar archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo_reporte = f"app_juzgado/logs/errores_tecnicos_{timestamp}.txt"
            
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(archivo_reporte), exist_ok=True)
            
            with open(archivo_reporte, 'w', encoding='utf-8') as f:
                # Encabezado del reporte
                f.write("=" * 100 + "\n")
                f.write("REPORTE DE ERRORES TÉCNICOS - CARGA CONSOLIDADA\n")
                f.write("=" * 100 + "\n")
                f.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total de errores encontrados: {len(self.inconsistencias)}\n")
                f.write("\n")
                f.write("NOTA: En esta carga consolidada, todos los radicados de los tres archivos\n")
                f.write("se procesan como expedientes válidos. Solo se reportan errores técnicos.\n")
                f.write("\n")
                
                # Resumen por tipo
                tipos = {}
                for item in self.inconsistencias:
                    tipo = item['tipo']
                    if tipo not in tipos:
                        tipos[tipo] = 0
                    tipos[tipo] += 1
                
                f.write("RESUMEN POR TIPO:\n")
                f.write("-" * 50 + "\n")
                for tipo, cantidad in sorted(tipos.items()):
                    f.write(f"{tipo}: {cantidad} casos\n")
                f.write("\n")
                
                # Resumen por archivo
                archivos = {}
                for item in self.inconsistencias:
                    archivo = item['archivo']
                    if archivo not in archivos:
                        archivos[archivo] = 0
                    archivos[archivo] += 1
                
                f.write("RESUMEN POR ARCHIVO:\n")
                f.write("-" * 50 + "\n")
                for archivo, cantidad in sorted(archivos.items()):
                    f.write(f"{archivo}: {cantidad} casos\n")
                f.write("\n")
                
                # Detalle completo de cada problema
                f.write("DETALLE COMPLETO DE ERRORES:\n")
                f.write("=" * 100 + "\n")
                
                for i, item in enumerate(self.inconsistencias, 1):
                    f.write(f"\nERROR #{i:04d}\n")
                    f.write("-" * 30 + "\n")
                    f.write(f"Tipo: {item['tipo']}\n")
                    f.write(f"Archivo: {item['archivo']}\n")
                    f.write(f"Hoja: {item['hoja']}\n")
                    f.write(f"Fila: {item['fila']}\n")
                    f.write(f"Radicado: {item['radicado']}\n")
                    f.write(f"Motivo: {item['motivo']}\n")
                    f.write(f"Timestamp: {item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    # Datos adicionales si existen
                    if 'datos_adicionales' in item and item['datos_adicionales']:
                        f.write("\nDatos adicionales de la fila:\n")
                        for clave, valor in item['datos_adicionales'].items():
                            f.write(f"  {clave}: {valor}\n")
                    
                    f.write("\n" + "." * 80 + "\n")
                
                # Sección de recomendaciones
                f.write("\n" + "=" * 100 + "\n")
                f.write("RECOMENDACIONES:\n")
                f.write("=" * 100 + "\n")
                
                errores_tecnicos = [t for t in tipos.keys() if t.startswith('ERROR_')]
                if errores_tecnicos:
                    f.write(f"\n• ERRORES TÉCNICOS ({sum(tipos[t] for t in errores_tecnicos)} casos):\n")
                    f.write("  - Revisar la estructura de los archivos Excel\n")
                    f.write("  - Verificar que las columnas esperadas existan\n")
                    f.write("  - Comprobar el formato de los datos (fechas, números, etc.)\n")
                    f.write("  - Revisar la configuración de la base de datos\n")
                
                f.write(f"\n• ACCIONES SUGERIDAS:\n")
                f.write("  1. Revisar manualmente los casos de errores técnicos\n")
                f.write("  2. Validar la integridad de los archivos fuente\n")
                f.write("  3. Verificar la configuración de la base de datos\n")
                f.write("  4. Comprobar que todas las columnas esperadas existan en los archivos\n")
                
                f.write("\n" + "=" * 100 + "\n")
                f.write("FIN DEL REPORTE\n")
                f.write("=" * 100 + "\n")
            
            print(f"   ✅ Reporte de errores generado: {archivo_reporte}")
            
            # También generar un resumen corto
            archivo_resumen = f"app_juzgado/logs/resumen_consolidado_{timestamp}.txt"
            with open(archivo_resumen, 'w', encoding='utf-8') as f:
                f.write("RESUMEN EJECUTIVO - CARGA CONSOLIDADA\n")
                f.write("=" * 50 + "\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("ESTRATEGIA: Carga consolidada de todos los radicados\n")
                f.write("- Todos los radicados de los 3 archivos se cargan como expedientes\n")
                f.write("- Información adicional se guarda en tablas ingresos y estados\n")
                f.write("- Solo se reportan errores técnicos, no inconsistencias de negocio\n\n")
                
                f.write("ESTADÍSTICAS DE CARGA:\n")
                f.write(f"• Expedientes cargados: {self.stats['expedientes_cargados']}\n")
                f.write(f"• Ingresos cargados: {self.stats['ingresos_cargados']}\n")
                f.write(f"• Estados cargados: {self.stats['estados_cargados']}\n")
                f.write(f"• Errores técnicos: {self.stats['errores']}\n\n")
                
                if tipos:
                    f.write("TIPOS DE ERRORES:\n")
                    for tipo, cantidad in sorted(tipos.items()):
                        f.write(f"• {tipo}: {cantidad}\n")
                    f.write(f"\nVer detalles completos en: {archivo_reporte}\n")
                else:
                    f.write("✅ No se encontraron errores técnicos\n")
            
            print(f"   ✅ Resumen ejecutivo generado: {archivo_resumen}")
            
        except Exception as e:
            print(f"   ❌ Error generando reporte: {e}")
    
    def normalizar_nombre(self, nombre):
        """
        Normaliza un nombre para comparación flexible.
        Elimina puntos, comas, espacios extras, y convierte a mayúsculas.
        """
        if not nombre or pd.isna(nombre):
            return ""
        
        nombre_str = str(nombre).upper().strip()
        # Eliminar puntos, comas, guiones
        nombre_str = nombre_str.replace('.', '').replace(',', '').replace('-', '')
        # Eliminar espacios múltiples
        nombre_str = ' '.join(nombre_str.split())
        return nombre_str
    
    def nombres_similares(self, nombre1, nombre2, umbral=0.7):
        """
        Compara dos nombres y determina si son similares.
        
        Criterios:
        1. Si uno contiene al otro (ej: "HELM BANK" está en "HELM BANK S.A.")
        2. Si comparten palabras significativas (más del 70% de palabras en común)
        """
        if not nombre1 or not nombre2:
            return False
        
        norm1 = self.normalizar_nombre(nombre1)
        norm2 = self.normalizar_nombre(nombre2)
        
        if not norm1 or not norm2:
            return False
        
        # Criterio 1: Uno contiene al otro
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        # Criterio 2: Palabras en común
        palabras1 = set(norm1.split())
        palabras2 = set(norm2.split())
        
        # Filtrar palabras muy cortas (conectores, artículos)
        palabras1 = {p for p in palabras1 if len(p) > 2}
        palabras2 = {p for p in palabras2 if len(p) > 2}
        
        if not palabras1 or not palabras2:
            return False
        
        # Calcular intersección
        comunes = palabras1 & palabras2
        total = min(len(palabras1), len(palabras2))
        
        similitud = len(comunes) / total if total > 0 else 0
        
        return similitud >= umbral
    
    def obtener_nombres_de_datos(self, info_radicado):
        """
        Extrae demandante y demandado de los datos del radicado.
        Prioriza: Listado Final > Ingresos > Estados
        """
        demandante = None
        demandado = None
        
        # Prioridad 1: Listado Final
        if 'listado_final' in info_radicado.get('datos', {}) and info_radicado['datos']['listado_final']:
            primer_listado = info_radicado['datos']['listado_final'][0]
            demandante = primer_listado.get('demandante')
            demandado = primer_listado.get('demandado')
        
        # Prioridad 2: Ingresos (si no hay en listado final)
        if (not demandante or not demandado) and 'ingresos' in info_radicado.get('datos', {}) and info_radicado['datos']['ingresos']:
            primer_ingreso = info_radicado['datos']['ingresos'][0]
            if not demandante:
                demandante = primer_ingreso.get('demandante')
            if not demandado:
                demandado = primer_ingreso.get('demandado')
        
        # Prioridad 3: Estados (si aún no hay)
        if not demandante and 'estados' in info_radicado.get('datos', {}) and info_radicado['datos']['estados']:
            primer_estado = info_radicado['datos']['estados'][0]
            demandante = primer_estado.get('demandante')
        
        return demandante, demandado
    
    def buscar_radicado_existente_flexible(self, todos_los_radicados, radicado_limpio, demandante_nuevo=None, demandado_nuevo=None):
        """
        Busca un radicado existente usando validación flexible.
        
        Compara contra:
        1. radicado_completo exacto
        2. Últimos 13 dígitos de radicado_completo
        3. radicado_corto
        4. Versiones sin ceros a la izquierda
        5. Similitud de demandante y demandado (si los radicados son similares)
        
        Returns:
            radicado_existente si encuentra coincidencia, None si no existe
        """
        longitud = len(radicado_limpio)
        
        # Generar variantes del radicado para búsqueda
        variantes = set()
        
        # Variante 1: El radicado tal cual
        variantes.add(radicado_limpio)
        
        # Variante 2: Sin ceros a la izquierda
        sin_ceros = radicado_limpio.lstrip('0')
        if sin_ceros:  # Evitar string vacío si es todo ceros
            variantes.add(sin_ceros)
        
        # Variante 3: Con ceros completados a 13 dígitos (si tiene menos de 13)
        if longitud < 13:
            variantes.add(radicado_limpio.zfill(13))
        
        # Variante 4: Últimos 13 dígitos (si tiene más de 13)
        if longitud >= 13:
            ultimos_13 = radicado_limpio[-13:]
            variantes.add(ultimos_13)
            # También sin ceros a la izquierda
            ultimos_13_sin_ceros = ultimos_13.lstrip('0')
            if ultimos_13_sin_ceros:
                variantes.add(ultimos_13_sin_ceros)
        
        # Buscar en todos los radicados existentes
        candidatos = []  # Lista de (radicado, score) para priorizar
        
        for rad_existente, info_existente in todos_los_radicados.items():
            len_existente = len(rad_existente)
            
            # Generar variantes del radicado existente
            variantes_existente = set()
            variantes_existente.add(rad_existente)
            
            sin_ceros_existente = rad_existente.lstrip('0')
            if sin_ceros_existente:
                variantes_existente.add(sin_ceros_existente)
            
            if len_existente >= 13:
                ultimos_13_existente = rad_existente[-13:]
                variantes_existente.add(ultimos_13_existente)
                ultimos_13_sin_ceros_existente = ultimos_13_existente.lstrip('0')
                if ultimos_13_sin_ceros_existente:
                    variantes_existente.add(ultimos_13_sin_ceros_existente)
            
            if len_existente < 13:
                variantes_existente.add(rad_existente.zfill(13))
            
            # Verificar si hay intersección entre variantes
            # Verificar si hay intersección entre variantes o si alguna variante
            # es subcadena de otra (casos como radicados cortos dentro del radicado largo)
            matched = False
            # intersección directa
            if variantes & variantes_existente:
                matched = True
            else:
                # comprobar subcadenas
                for v in variantes:
                    for w in variantes_existente:
                        if v and w and (v in w or w in v):
                            matched = True
                            break
                    if matched:
                        break

            if matched:
                # Hay coincidencia de radicado (directa o por subcadena), calcular score
                score = 100  # Score base por coincidencia de radicado
                
                # Si tenemos nombres, verificar similitud para aumentar confianza
                if demandante_nuevo or demandado_nuevo:
                    demandante_existente, demandado_existente = self.obtener_nombres_de_datos(info_existente)
                    
                    # Bonus por similitud de nombres
                    if demandante_nuevo and demandante_existente:
                        if self.nombres_similares(demandante_nuevo, demandante_existente):
                            score += 50
                    
                    if demandado_nuevo and demandado_existente:
                        if self.nombres_similares(demandado_nuevo, demandado_existente):
                            score += 50
                
                # Bonus por longitud (priorizar radicados de 23 dígitos)
                if len_existente == 23:
                    score += 30
                elif len_existente >= 13:
                    score += 10
                
                candidatos.append((rad_existente, score))
        
        # Si hay candidatos, devolver el de mayor score
        if candidatos:
            candidatos.sort(key=lambda x: x[1], reverse=True)
            mejor_candidato = candidatos[0][0]
            
            # Si el score es muy alto (>= 150), hay alta confianza de que es el mismo expediente
            if candidatos[0][1] >= 150:
                print(f"      🎯 Alta confianza: {radicado_limpio} coincide con {mejor_candidato} (score: {candidatos[0][1]})")
            
            return mejor_candidato
        
        return None
    
    def agregar_radicado_inteligente(self, todos_los_radicados, radicado_limpio, fuente, datos):
        """
        Agrega un radicado de forma inteligente, consolidando automáticamente.
        
        REGLAS:
        1. Validación flexible: compara contra múltiples variantes antes de crear nuevo
        2. Validación por nombres: si radicados similares tienen demandante/demandado similares, se consolidan
        3. Si el radicado tiene 23 dígitos: Es radicado_completo, prioridad máxima
        4. Si el radicado tiene 13 o menos dígitos: Buscar radicado_completo equivalente
        5. Siempre priorizar el radicado de 23 dígitos como principal
        """
        longitud = len(radicado_limpio)
        
        # Extraer nombres del nuevo radicado para comparación
        demandante_nuevo = datos.get('demandante')
        demandado_nuevo = datos.get('demandado')
        
        # PASO 1: Buscar si ya existe un radicado equivalente (validación flexible + nombres)
        radicado_existente = self.buscar_radicado_existente_flexible(
            todos_los_radicados, 
            radicado_limpio,
            demandante_nuevo,
            demandado_nuevo
        )
        
        if radicado_existente:
            # Ya existe un radicado equivalente
            len_existente = len(radicado_existente)
            
            # Decidir cuál debe ser el principal según longitud
            if longitud == 23:
                # El nuevo es de 23 dígitos (completo)
                if len_existente < 23:
                    # Reemplazar el existente con el de 23 dígitos
                    print(f"      🔄 Reemplazando radicado {radicado_existente} ({len_existente} dígitos) con completo {radicado_limpio} (23 dígitos)")
                    todos_los_radicados[radicado_limpio] = todos_los_radicados.pop(radicado_existente)
                    radicado_principal = radicado_limpio
                else:
                    # El existente también es de 23 dígitos, usar el existente
                    radicado_principal = radicado_existente
                    if radicado_existente != radicado_limpio:
                        print(f"      🔗 Vinculando radicado {radicado_limpio} (23 dígitos) con existente {radicado_existente} (23 dígitos)")
            elif len_existente == 23:
                # El existente es de 23 dígitos, mantenerlo como principal
                radicado_principal = radicado_existente
                print(f"      🔗 Vinculando radicado {radicado_limpio} ({longitud} dígitos) con completo existente {radicado_existente} (23 dígitos)")
            elif longitud > len_existente:
                # El nuevo es más largo, reemplazar
                print(f"      🔄 Reemplazando radicado {radicado_existente} ({len_existente} dígitos) con {radicado_limpio} ({longitud} dígitos)")
                todos_los_radicados[radicado_limpio] = todos_los_radicados.pop(radicado_existente)
                radicado_principal = radicado_limpio
            else:
                # El existente es más largo o igual, mantenerlo
                radicado_principal = radicado_existente
                if radicado_existente != radicado_limpio:
                    print(f"      🔗 Vinculando radicado {radicado_limpio} ({longitud} dígitos) con existente {radicado_existente} ({len_existente} dígitos)")
        else:
            # No existe ningún radicado equivalente, crear nuevo
            todos_los_radicados[radicado_limpio] = {'fuentes': [], 'datos': {}}
            radicado_principal = radicado_limpio
        
        # Agregar fuente si no existe
        if fuente not in todos_los_radicados[radicado_principal]['fuentes']:
            todos_los_radicados[radicado_principal]['fuentes'].append(fuente)
        
        # Agregar datos según el tipo de fuente
        tipo_datos = fuente.lower().replace('_', '')
        if tipo_datos == 'listadofinal':
            tipo_datos = 'listado_final'
        
        if tipo_datos not in todos_los_radicados[radicado_principal]['datos']:
            todos_los_radicados[radicado_principal]['datos'][tipo_datos] = []
        
        todos_los_radicados[radicado_principal]['datos'][tipo_datos].append(datos)
        
        return radicado_principal
    
    def recopilar_todos_los_radicados(self):
        """Recopila todos los radicados únicos de los tres archivos"""
        print("🔍 RECOPILANDO TODOS LOS RADICADOS DE LOS ARCHIVOS...")
        
        todos_los_radicados = {}  # radicado -> {fuentes: [], datos: {}}
        
        # 1. Procesar Listado Final Cruzado (hoja "Resumen por Expediente")
        print("   📋 Procesando Listado Final Cruzado (Resumen por Expediente)...")
        try:
            if os.path.exists(self.listado_final_path):
                df_listado = pd.read_excel(self.listado_final_path, sheet_name='Resumen por Expediente')
                
                for index, row in df_listado.iterrows():
                    # USAR RADICADO COMPLETO (23 dígitos) como principal
                    radicado_original = row.get('RADICADO COMPLETO', '')
                    
                    # Si no hay RADICADO COMPLETO, usar RADICADO_MODIFICADO_OFI como fallback
                    if not radicado_original or pd.isna(radicado_original):
                        radicado_original = row.get('RADICADO_MODIFICADO_OFI', '')
                    
                    radicado_limpio = self.limpiar_radicado(radicado_original)
                    
                    if radicado_limpio:
                        datos = {
                            'radicado_corto': row.get('RadicadoCorto'),
                            'juzgado_origen': row.get('J. ORIGEN'),
                            'demandante': row.get('DEMANDANTE'),
                            'demandado': row.get('DEMANDADO'),
                            'fecha_ingreso': row.get('FECHA INGRESO'),
                            'fecha_actuacion': row.get('FECHA ACTUACION'),
                            'fecha_estado': row.get('FECHA ESTADO'),
                            'auto_anotacion': row.get('Auto / Anotación')
                        }
                        
                        self.agregar_radicado_inteligente(todos_los_radicados, radicado_limpio, 'LISTADO_FINAL', datos)
                
                listado_count = len([r for r in todos_los_radicados.values() if 'LISTADO_FINAL' in r['fuentes']])
                print(f"      ✅ Radicados en Listado Final: {listado_count}")
            else:
                print(f"      ⚠️ Archivo no encontrado: {self.listado_final_path}")
        except Exception as e:
            print(f"      ❌ Error procesando Listado Final: {e}")
        
        # 2. Procesar Ingresos
        print("   📋 Procesando Ingresos...")
        try:
            excel_file = pd.ExcelFile(self.ingresos_path)
            hojas_ingresos = [h for h in excel_file.sheet_names if 'Ingresos' in h]
            
            for sheet_name in hojas_ingresos:
                df_ingresos = pd.read_excel(self.ingresos_path, sheet_name=sheet_name)
                for index, row in df_ingresos.iterrows():
                    # USAR RADICADO COMPLETO (23 dígitos) como principal
                    radicado_original = row.get('RADICADO COMPLETO', '')
                    
                    # Si no hay RADICADO COMPLETO, usar RADICADO MODIFICADO como fallback
                    if not radicado_original or pd.isna(radicado_original):
                        radicado_original = row.get('RADICADO MODIFICADO', '')
                    
                    radicado_limpio = self.limpiar_radicado(radicado_original)
                    
                    if radicado_limpio:
                        datos = {
                            'fecha_ingreso': row.get('FECHA DE INGRESO'),
                            'motivo_ingreso': row.get('SOLICITUD'),
                            'observaciones_ingreso': row.get('OBSERVACIONES'),
                            'juzgado_origen': row.get('J. ORIGEN'),
                            'demandante': row.get('DEMANDANTE'),
                            'demandado': row.get('DEMANDADO'),
                            'hoja': sheet_name
                        }
                        
                        self.agregar_radicado_inteligente(todos_los_radicados, radicado_limpio, 'INGRESOS', datos)
            
            ingresos_count = len([r for r in todos_los_radicados.values() if 'INGRESOS' in r['fuentes']])
            print(f"      ✅ Radicados con Ingresos: {ingresos_count}")
        except Exception as e:
            print(f"      ❌ Error procesando Ingresos: {e}")
        
        # 3. Procesar Estados
        print("   📋 Procesando Estados...")
        try:
            excel_file = pd.ExcelFile(self.estados_path)
            hojas_estados = [h for h in excel_file.sheet_names if 'Q' in h and ('2023' in h or '2024' in h or '2025' in h)]
            
            for sheet_name in hojas_estados:
                df_estados = pd.read_excel(self.estados_path, sheet_name=sheet_name)
                for index, row in df_estados.iterrows():
                    # USAR RADICADO COMPLETO (23 dígitos) como principal
                    radicado_original = row.get('RADICADO COMPLETO', '')
                    
                    # Si no hay RADICADO COMPLETO, usar RADICADO_MODIFICADO_OFI como fallback
                    if not radicado_original or pd.isna(radicado_original):
                        radicado_original = row.get('RADICADO_MODIFICADO_OFI', '')
                    
                    radicado_limpio = self.limpiar_radicado(radicado_original)
                    
                    if radicado_limpio:
                        datos = {
                            'fecha_estado': row.get('FECHA ESTADO'),
                            'clase': row.get('CLASE'),
                            'demandante': row.get('DEMANDANTE'),
                            'auto_anotacion': row.get('AUTO / ANOTACION'),
                            'observaciones': row.get('OBSERVACIONES'),
                            'fecha_auto': row.get('FECHA AUTO'),
                            'hoja': sheet_name
                        }
                        
                        self.agregar_radicado_inteligente(todos_los_radicados, radicado_limpio, 'ESTADOS', datos)
            
            estados_count = len([r for r in todos_los_radicados.values() if 'ESTADOS' in r['fuentes']])
            print(f"      ✅ Radicados con Estados: {estados_count}")
        except Exception as e:
            print(f"      ❌ Error procesando Estados: {e}")
        
        print(f"   🎯 TOTAL DE RADICADOS ÚNICOS ENCONTRADOS: {len(todos_los_radicados)}")
        
        # Mostrar estadísticas de fuentes
        solo_listado = len([r for r in todos_los_radicados.values() if r['fuentes'] == ['LISTADO_FINAL']])
        solo_ingresos = len([r for r in todos_los_radicados.values() if r['fuentes'] == ['INGRESOS']])
        solo_estados = len([r for r in todos_los_radicados.values() if r['fuentes'] == ['ESTADOS']])
        multiples = len(todos_los_radicados) - solo_listado - solo_ingresos - solo_estados
        
        print(f"      📊 Solo en Listado Final: {solo_listado}")
        print(f"      📊 Solo en Ingresos: {solo_ingresos}")
        print(f"      📊 Solo en Estados: {solo_estados}")
        print(f"      📊 En múltiples fuentes: {multiples}")
        
        return todos_los_radicados
    
    def consolidar_radicados_duplicados(self, todos_los_radicados):
        """Consolida radicados que tienen los mismos últimos 13 dígitos, priorizando el más largo Y validando similitud de nombres"""
        print("🔄 CONSOLIDANDO RADICADOS DUPLICADOS POR ÚLTIMOS 13 DÍGITOS CON VALIDACIÓN DE NOMBRES...")
        
        radicados_consolidados = {}
        mapa_ultimos_13 = {}  # últimos_13 -> radicado_principal
        duplicados_encontrados = 0
        consolidaciones_rechazadas = 0
        
        for radicado, info in todos_los_radicados.items():
            # Obtener últimos 13 dígitos
            if len(radicado) >= 13:
                ultimos_13 = radicado[-13:]
                
                # Verificar si ya existe un radicado con estos últimos 13 dígitos
                if ultimos_13 in mapa_ultimos_13:
                    # Ya existe, decidir si consolidar basándose en similitud de nombres
                    radicado_existente = mapa_ultimos_13[ultimos_13]
                    
                    # Extraer demandantes y demandados para validación
                    demandante_nuevo, demandado_nuevo = self.obtener_nombres_de_datos(info)
                    info_existente = radicados_consolidados[radicado_existente]
                    demandante_existente, demandado_existente = self.obtener_nombres_de_datos(info_existente)
                    
                    # Validar similitud de nombres
                    nombres_similares = False
                    
                    # Criterio 1: Si no hay nombres en uno de ellos, consolidar
                    if not (demandante_nuevo or demandado_nuevo) or not (demandante_existente or demandado_existente):
                        nombres_similares = True
                        print(f"      ℹ️ Consolidando por falta de datos de nombres en uno de los radicados")
                    else:
                        # Criterio 2: Validar similitud de demandante
                        demandante_match = False
                        if demandante_nuevo and demandante_existente:
                            demandante_match = self.nombres_similares(demandante_nuevo, demandante_existente, umbral=0.6)
                            if demandante_match:
                                print(f"      ✅ Demandantes similares: '{demandante_nuevo}' ≈ '{demandante_existente}'")
                        elif not demandante_nuevo or not demandante_existente:
                            # Si uno no tiene demandante, no penalizar
                            demandante_match = True
                        
                        # Criterio 3: Validar similitud de demandado
                        demandado_match = False
                        if demandado_nuevo and demandado_existente:
                            demandado_match = self.nombres_similares(demandado_nuevo, demandado_existente, umbral=0.6)
                            if demandado_match:
                                print(f"      ✅ Demandados similares: '{demandado_nuevo}' ≈ '{demandado_existente}'")
                        elif not demandado_nuevo or not demandado_existente:
                            # Si uno no tiene demandado, no penalizar
                            demandado_match = True
                        
                        # Consolidar solo si demandante Y demandado coinciden o no tenemos datos completos
                        nombres_similares = demandante_match and demandado_match
                    
                    if not nombres_similares:
                        # Nombres no coinciden, no consolidar, mantener como radicados separados
                        print(f"      ⚠️ NO se consolidó: radicados con últimos 13 dígitos iguales pero nombres distintos")
                        print(f"         Radicado 1: {radicado_existente}")
                        print(f"         Demandante: {demandante_existente}, Demandado: {demandado_existente}")
                        print(f"         Radicado 2: {radicado}")
                        print(f"         Demandante: {demandante_nuevo}, Demandado: {demandado_nuevo}")
                        radicados_consolidados[radicado] = info
                        consolidaciones_rechazadas += 1
                        continue
                    
                    # PRIORIZAR EL RADICADO MÁS LARGO (23 dígitos completos)
                    if len(radicado) > len(radicado_existente):
                        # El nuevo radicado es más largo, usarlo como principal
                        radicado_principal = radicado
                        radicado_secundario = radicado_existente
                        
                        # Actualizar el mapa
                        mapa_ultimos_13[ultimos_13] = radicado_principal
                        
                        # Mover datos del existente al nuevo principal
                        radicados_consolidados[radicado_principal] = info
                        
                        # Consolidar datos del secundario (el que era principal antes)
                        info_secundario = radicados_consolidados.pop(radicado_secundario)
                        
                        print(f"   🔍 Duplicado encontrado (priorizando más largo):")
                        print(f"      Principal: {radicado_principal} ({len(radicado_principal)} dígitos)")
                        print(f"      Secundario: {radicado_secundario} ({len(radicado_secundario)} dígitos)")
                        print(f"      Últimos 13: {ultimos_13}")
                        
                        # Consolidar fuentes del secundario al principal
                        for fuente in info_secundario['fuentes']:
                            if fuente not in radicados_consolidados[radicado_principal]['fuentes']:
                                radicados_consolidados[radicado_principal]['fuentes'].append(fuente)
                        
                        # Consolidar datos de listado_final
                        if 'listado_final' in info_secundario['datos']:
                            if 'listado_final' not in radicados_consolidados[radicado_principal]['datos']:
                                radicados_consolidados[radicado_principal]['datos']['listado_final'] = []
                            radicados_consolidados[radicado_principal]['datos']['listado_final'].extend(info_secundario['datos']['listado_final'])
                        
                        # Consolidar datos de ingresos
                        if 'ingresos' in info_secundario['datos']:
                            if 'ingresos' not in radicados_consolidados[radicado_principal]['datos']:
                                radicados_consolidados[radicado_principal]['datos']['ingresos'] = []
                            radicados_consolidados[radicado_principal]['datos']['ingresos'].extend(info_secundario['datos']['ingresos'])
                        
                        # Consolidar datos de estados
                        if 'estados' in info_secundario['datos']:
                            if 'estados' not in radicados_consolidados[radicado_principal]['datos']:
                                radicados_consolidados[radicado_principal]['datos']['estados'] = []
                            radicados_consolidados[radicado_principal]['datos']['estados'].extend(info_secundario['datos']['estados'])
                    else:
                        # El existente es más largo o igual, mantenerlo como principal
                        radicado_principal = radicado_existente
                        radicado_secundario = radicado
                        
                        print(f"   🔍 Duplicado encontrado (manteniendo más largo):")
                        print(f"      Principal: {radicado_principal} ({len(radicado_principal)} dígitos)")
                        print(f"      Secundario: {radicado_secundario} ({len(radicado_secundario)} dígitos)")
                        print(f"      Últimos 13: {ultimos_13}")
                        
                        # Consolidar fuentes del secundario al principal
                        for fuente in info['fuentes']:
                            if fuente not in radicados_consolidados[radicado_principal]['fuentes']:
                                radicados_consolidados[radicado_principal]['fuentes'].append(fuente)
                        
                        # Consolidar datos de listado_final
                        if 'listado_final' in info['datos']:
                            if 'listado_final' not in radicados_consolidados[radicado_principal]['datos']:
                                radicados_consolidados[radicado_principal]['datos']['listado_final'] = []
                            radicados_consolidados[radicado_principal]['datos']['listado_final'].extend(info['datos']['listado_final'])
                        
                        # Consolidar datos de ingresos
                        if 'ingresos' in info['datos']:
                            if 'ingresos' not in radicados_consolidados[radicado_principal]['datos']:
                                radicados_consolidados[radicado_principal]['datos']['ingresos'] = []
                            radicados_consolidados[radicado_principal]['datos']['ingresos'].extend(info['datos']['ingresos'])
                        
                        # Consolidar datos de estados
                        if 'estados' in info['datos']:
                            if 'estados' not in radicados_consolidados[radicado_principal]['datos']:
                                radicados_consolidados[radicado_principal]['datos']['estados'] = []
                            radicados_consolidados[radicado_principal]['datos']['estados'].extend(info['datos']['estados'])
                    
                    duplicados_encontrados += 1
                else:
                    # Primer radicado con estos últimos 13 dígitos
                    mapa_ultimos_13[ultimos_13] = radicado
                    radicados_consolidados[radicado] = info
            else:
                # Radicado muy corto, no consolidar
                radicados_consolidados[radicado] = info
        
        print(f"   ✅ Duplicados consolidados: {duplicados_encontrados}")
        print(f"   ⚠️ Consolidaciones rechazadas (nombres distintos): {consolidaciones_rechazadas}")
        print(f"   📊 Radicados únicos después de consolidar: {len(radicados_consolidados)}")
        
        return radicados_consolidados
    
    def cargar_expedientes_consolidados(self, todos_los_radicados):
        """Carga todos los expedientes consolidando información de todas las fuentes"""
        print("📋 CARGANDO EXPEDIENTES CONSOLIDADOS...")
        
        conn = None
        cursor = None
        
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            batch_size = 100
            batch_count = 0
            
            for radicado_limpio, info in todos_los_radicados.items():
                try:
                    # Consolidar datos priorizando Listado Final, luego Ingresos, luego Estados
                    datos_consolidados = self.consolidar_datos_expediente(radicado_limpio, info)
                    
                    # Insertar en la base de datos
                    cursor.execute("""
                        INSERT INTO expediente (fecha_ingreso, juzgado_origen, radicado_completo, 
                                               demandante, demandado, radicado_corto)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, datos_consolidados)
                    
                    self.stats['expedientes_cargados'] += 1
                    batch_count += 1
                    
                    # Commit cada lote
                    if batch_count >= batch_size:
                        conn.commit()
                        batch_count = 0
                        if self.stats['expedientes_cargados'] % 1000 == 0:
                            print(f"      📊 Procesados {self.stats['expedientes_cargados']} expedientes...")
                
                except Exception as e:
                    print(f"      ⚠️ Error procesando radicado {radicado_limpio}: {e}")
                    self.registrar_error(
                        tipo='EXPEDIENTE_CONSOLIDADO',
                        archivo='CONSOLIDACION',
                        hoja='N/A',
                        fila=0,
                        error=e,
                        datos_fila={'radicado': radicado_limpio, 'fuentes': info['fuentes']}
                    )
                    conn.rollback()
                    batch_count = 0
                    continue
            
            # Commit final
            conn.commit()
            print(f"   ✅ Expedientes consolidados cargados: {self.stats['expedientes_cargados']}")
            
            # Cargar el mapa de radicados después de insertar expedientes
            self.cargar_mapa_radicados()
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error cargando expedientes consolidados: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def consolidar_datos_expediente(self, radicado_limpio, info):
        """Consolida datos de expediente priorizando fuentes"""
        # Prioridad: Listado Final > Ingresos > Estados
        
        # Valores por defecto
        fecha_ingreso = None
        juzgado_origen = 1
        demandante = None
        demandado = None
        radicado_corto = None
        
        # 1. Priorizar datos del Listado Final
        if 'listado_final' in info['datos'] and info['datos']['listado_final']:
            # Usar el primer registro del listado final
            primer_listado = info['datos']['listado_final'][0]
            
            fecha_ingreso = self.safe_date(primer_listado.get('fecha_ingreso'))
            demandante = self.safe_str(primer_listado.get('demandante'), 255)
            demandado = self.safe_str(primer_listado.get('demandado'), 255)
            
            # Juzgado origen del listado final
            juzgado_listado = primer_listado.get('juzgado_origen')
            if juzgado_listado and str(juzgado_listado).strip():
                try:
                    juzgado_origen = int(str(juzgado_listado).strip())
                except:
                    pass
        
        # 2. Completar con datos de Ingresos si faltan
        if 'ingresos' in info['datos'] and info['datos']['ingresos']:
            # Usar el primer ingreso para datos básicos
            primer_ingreso = info['datos']['ingresos'][0]
            
            if not fecha_ingreso:
                fecha_ingreso = self.safe_date(primer_ingreso.get('fecha_ingreso'))
            if not demandante:
                demandante = self.safe_str(primer_ingreso.get('demandante'), 255)
            if not demandado:
                demandado = self.safe_str(primer_ingreso.get('demandado'), 255)
            
            # Juzgado origen de ingresos si no está definido
            juzgado_ingreso = primer_ingreso.get('juzgado_origen')
            if juzgado_ingreso and str(juzgado_ingreso).strip():
                try:
                    juzgado_origen = int(str(juzgado_ingreso).strip())
                except:
                    pass
        
        # 3. Completar con datos de Estados si aún faltan
        if 'estados' in info['datos'] and info['datos']['estados']:
            # Usar el primer estado para datos básicos
            primer_estado = info['datos']['estados'][0]
            
            if not demandante:
                demandante = self.safe_str(primer_estado.get('demandante'), 255)
        
        # 4. Calcular radicado_corto (últimos 13 dígitos del radicado_completo)
        if len(radicado_limpio) >= 13:
            # Si tiene 13 o más dígitos, tomar los últimos 13
            radicado_corto = radicado_limpio[-13:]
        else:
            # Si tiene menos de 13 dígitos, completar con ceros a la izquierda
            radicado_corto = radicado_limpio.zfill(13)
        
        return (
            fecha_ingreso,
            juzgado_origen,
            radicado_limpio,  # radicado_completo
            demandante,
            demandado,
            radicado_corto  # últimos 13 dígitos o completado con ceros
        )
    
    def cargar_ingresos_detallados(self, todos_los_radicados):
        """Carga todos los ingresos detallados usando el mapa de expedientes"""
        print("📋 CARGANDO INGRESOS DETALLADOS...")
        
        if not self.mapa_radicados:
            print("   ❌ Mapa de radicados no disponible")
            return False
        
        conn = None
        cursor = None
        
        try:
            # NO limpiar tabla aquí - ya se limpió en cargar_expedientes_consolidados
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            batch_size = 50
            batch_count = 0
            
            # Debug: contar cuántos radicados tienen ingresos
            radicados_con_ingresos = 0
            total_ingresos = 0
            
            for radicado_limpio, info in todos_los_radicados.items():
                if 'ingresos' in info['datos']:
                    radicados_con_ingresos += 1
                    total_ingresos += len(info['datos']['ingresos'])
                    
                    expediente_id = self.mapa_radicados.get(radicado_limpio)
                    
                    if expediente_id:
                        # Insertar cada ingreso
                        for ingreso in info['datos']['ingresos']:
                            try:
                                # Columnas reales de la tabla ingresos:
                                # expediente_id, fecha_ingreso, observaciones, solicitud, fechas, fecha_estado_auto
                                datos = (
                                    expediente_id,
                                    self.safe_date(ingreso.get('fecha_ingreso')),
                                    self.safe_str(ingreso.get('observaciones_ingreso'), 2000),
                                    self.safe_str(ingreso.get('motivo_ingreso'), 2000),
                                    None,  # fechas
                                    None   # fecha_estado_auto
                                )
                                
                                cursor.execute("""
                                    INSERT INTO ingresos (expediente_id, fecha_ingreso, 
                                                         observaciones, solicitud, fechas, fecha_estado_auto)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, datos)
                                
                                self.stats['ingresos_cargados'] += 1
                                batch_count += 1
                                
                                if batch_count >= batch_size:
                                    conn.commit()
                                    batch_count = 0
                            
                            except Exception as e:
                                print(f"      ⚠️ Error insertando ingreso para radicado {radicado_limpio}: {e}")
                                conn.rollback()
                                batch_count = 0
                                continue
                    else:
                        print(f"      ⚠️ No se encontró expediente_id para radicado {radicado_limpio}")
            
            conn.commit()
            print(f"   📊 Radicados con ingresos: {radicados_con_ingresos}")
            print(f"   📊 Total de ingresos a insertar: {total_ingresos}")
            print(f"   ✅ Ingresos detallados cargados: {self.stats['ingresos_cargados']}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error cargando ingresos detallados: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def cargar_estados_detallados(self, todos_los_radicados):
        """Carga todos los estados detallados usando el mapa de expedientes"""
        print("📋 CARGANDO ESTADOS DETALLADOS...")
        
        if not self.mapa_radicados:
            print("   ❌ Mapa de radicados no disponible")
            return False
        
        conn = None
        cursor = None
        
        try:
            # NO limpiar tabla aquí - ya se limpió en cargar_expedientes_consolidados
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            batch_size = 50
            batch_count = 0
            
            # Debug: contar cuántos radicados tienen estados
            radicados_con_estados = 0
            total_estados = 0
            
            for radicado_limpio, info in todos_los_radicados.items():
                if 'estados' in info['datos']:
                    radicados_con_estados += 1
                    total_estados += len(info['datos']['estados'])
                    
                    expediente_id = self.mapa_radicados.get(radicado_limpio)
                    
                    if expediente_id:
                        # Insertar cada estado
                        for estado in info['datos']['estados']:
                            try:
                                # Columnas reales de la tabla estados:
                                # clase, auto_anotacion, observaciones, fecha_estado, fecha_auto, expediente_id
                                datos = (
                                    self.safe_str(estado.get('clase'), 1000),
                                    self.safe_str(estado.get('auto_anotacion'), 2000),
                                    self.safe_str(estado.get('observaciones'), 2000),
                                    self.safe_date(estado.get('fecha_estado')),
                                    self.safe_date(estado.get('fecha_auto')),
                                    expediente_id
                                )
                                
                                cursor.execute("""
                                    INSERT INTO estados (clase, auto_anotacion, observaciones, 
                                                        fecha_estado, fecha_auto, expediente_id)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, datos)
                                
                                self.stats['estados_cargados'] += 1
                                batch_count += 1
                                
                                if batch_count >= batch_size:
                                    conn.commit()
                                    batch_count = 0
                            
                            except Exception as e:
                                print(f"      ⚠️ Error insertando estado para radicado {radicado_limpio}: {e}")
                                conn.rollback()
                                batch_count = 0
                                continue
                    else:
                        print(f"      ⚠️ No se encontró expediente_id para radicado {radicado_limpio}")
            
            conn.commit()
            print(f"   📊 Radicados con estados: {radicados_con_estados}")
            print(f"   📊 Total de estados a insertar: {total_estados}")
            print(f"   ✅ Estados detallados cargados: {self.stats['estados_cargados']}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error cargando estados detallados: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def ejecutar_carga_completa(self):
        """Ejecuta la carga completa consolidando todos los radicados"""
        print("🚀 INICIANDO CARGA COMPLETA CONSOLIDADA")
        print("=" * 80)
        
        inicio = datetime.now()
        
        # Paso 0: Limpiar base de datos
        if not self.limpiar_base_datos():
            print("❌ Error limpiando base de datos. Abortando proceso.")
            return False
        
        print()
        
        # Paso 1: Recopilar todos los radicados de los tres archivos
        todos_los_radicados = self.recopilar_todos_los_radicados()
        if not todos_los_radicados:
            print("❌ No se encontraron radicados. Abortando proceso.")
            return False
        
        print()
        
        # Paso 1.5: Consolidar radicados duplicados por últimos 13 dígitos
        todos_los_radicados = self.consolidar_radicados_duplicados(todos_los_radicados)
        
        print()
        
        # Paso 2: Cargar expedientes consolidados
        if not self.cargar_expedientes_consolidados(todos_los_radicados):
            print("❌ Error cargando expedientes consolidados. Abortando proceso.")
            return False
        
        print()
        
        # Paso 3: Cargar ingresos detallados
        if not self.cargar_ingresos_detallados(todos_los_radicados):
            print("⚠️ Error cargando ingresos detallados, pero continuando...")
        
        print()
        
        # Paso 4: Cargar estados detallados
        if not self.cargar_estados_detallados(todos_los_radicados):
            print("⚠️ Error cargando estados detallados, pero continuando...")
        
        print()
        
        # Paso 5: Generar reporte de inconsistencias (ahora solo errores técnicos)
        self.generar_reporte_inconsistencias()
        
        print()
        
        # Mostrar estadísticas finales
        fin = datetime.now()
        duracion = fin - inicio
        
        print("✅ CARGA CONSOLIDADA COMPLETADA")
        print("=" * 80)
        print(f"📊 ESTADÍSTICAS FINALES:")
        print(f"   - Expedientes cargados: {self.stats['expedientes_cargados']}")
        print(f"   - Ingresos cargados: {self.stats['ingresos_cargados']}")
        print(f"   - Estados cargados: {self.stats['estados_cargados']}")
        print(f"   - Errores encontrados: {self.stats['errores']}")
        print(f"   - Tiempo total: {duracion}")
        
        return True

def main():
    """Función principal"""
    cargador = CargadorDatosMejorado()
    cargador.ejecutar_carga_completa()

if __name__ == "__main__":
    main()