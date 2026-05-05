#!/usr/bin/env python3
"""
Script para monitorear el estado de los turnos
Sistema de Gestión Judicial

Uso:
    python monitorear_turnos.py
"""

import sys
import os
from datetime import datetime, date, time
from collections import defaultdict

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

def obtener_estadisticas_turnos():
    """Obtiene estadísticas completas de turnos"""
    
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        estadisticas = {}
        
        # Total de expedientes
        cursor.execute("SELECT COUNT(*) FROM expediente")
        estadisticas['total_expedientes'] = cursor.fetchone()[0]
        
        # Expedientes con turno
        cursor.execute("""
            SELECT COUNT(*) FROM expediente 
            WHERE turno IS NOT NULL AND turno != ''
        """)
        estadisticas['con_turno'] = cursor.fetchone()[0]
        
        # Expedientes sin turno (activos)
        cursor.execute("""
            SELECT COUNT(*) FROM expediente 
            WHERE (turno IS NULL OR turno = '') 
              AND estado = 'Activo Pendiente'
        """)
        estadisticas['sin_turno_activos'] = cursor.fetchone()[0]
        
        # Turnos por estado
        cursor.execute("""
            SELECT estado, COUNT(*) 
            FROM expediente 
            WHERE turno IS NOT NULL AND turno != ''
            GROUP BY estado
            ORDER BY COUNT(*) DESC
        """)
        estadisticas['por_estado'] = dict(cursor.fetchall())
        
        # Distribución por horas
        cursor.execute("""
            SELECT turno, COUNT(*) 
            FROM expediente 
            WHERE turno IS NOT NULL AND turno != ''
            GROUP BY turno
            ORDER BY turno
        """)
        estadisticas['por_hora'] = dict(cursor.fetchall())
        
        return estadisticas
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return {}
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conexion' in locals():
            conexion.close()

def mostrar_dashboard():
    """Muestra un dashboard con el estado actual de turnos"""
    
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "DASHBOARD DE TURNOS" + " " * 24 + "║")
    print("╠" + "═" * 58 + "╣")
    
    stats = obtener_estadisticas_turnos()
    
    if not stats:
        print("║" + " " * 20 + "Error cargando datos" + " " * 17 + "║")
        print("╚" + "═" * 58 + "╝")
        return
    
    # Estadísticas generales
    print(f"║ Total de expedientes: {stats.get('total_expedientes', 0):<35} ║")
    print(f"║ Con turno asignado: {stats.get('con_turno', 0):<37} ║")
    print(f"║ Sin turno (activos): {stats.get('sin_turno_activos', 0):<36} ║")
    
    # Porcentaje de cobertura
    total = stats.get('total_expedientes', 0)
    con_turno = stats.get('con_turno', 0)
    porcentaje = (con_turno / total * 100) if total > 0 else 0
    print(f"║ Cobertura de turnos: {porcentaje:.1f}%{' ' * (34 - len(f'{porcentaje:.1f}%'))} ║")
    
    print("╠" + "═" * 58 + "╣")
    
    # Turnos por estado
    print("║ DISTRIBUCIÓN POR ESTADO:" + " " * 33 + "║")
    for estado, cantidad in stats.get('por_estado', {}).items():
        estado_truncado = estado[:25] if len(estado) > 25 else estado
        print(f"║   {estado_truncado:<25} : {cantidad:<25} ║")
    
    print("╚" + "═" * 58 + "╝")

def mostrar_turnos_detallados():
    """Muestra los turnos del día con detalles"""
    
    print("\n📅 TURNOS DETALLADOS DEL DÍA")
    print("=" * 80)
    
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("""
            SELECT 
                turno,
                radicado_completo,
                demandante,
                demandado,
                estado,
                responsable,
                fecha_ingreso
            FROM expediente 
            WHERE turno IS NOT NULL AND turno != ''
            ORDER BY turno ASC
        """)
        
        turnos = cursor.fetchall()
        
        if not turnos:
            print("ℹ️ No hay turnos asignados")
            return
        
        print(f"{'Hora':<6} | {'Radicado':<15} | {'Demandante':<20} | {'Estado':<15} | {'Responsable':<12}")
        print("-" * 80)
        
        for turno in turnos:
            hora, radicado, demandante, demandado, estado, responsable, fecha_ingreso = turno
            
            # Truncar nombres largos
            demandante = demandante[:20] if demandante else "N/A"
            estado = estado[:15] if estado else "N/A"
            responsable = responsable[:12] if responsable else "Sin asignar"
            radicado = radicado[:15] if radicado else "N/A"
            
            print(f"{hora:<6} | {radicado:<15} | {demandante:<20} | {estado:<15} | {responsable:<12}")
        
        print(f"\nTotal: {len(turnos)} turnos programados")
        
    except Exception as e:
        print(f"❌ Error mostrando turnos detallados: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conexion' in locals():
            conexion.close()

def verificar_conflictos():
    """Verifica si hay conflictos en los turnos"""
    
    print("\n🔍 VERIFICACIÓN DE CONFLICTOS")
    print("=" * 40)
    
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Buscar turnos duplicados
        cursor.execute("""
            SELECT turno, COUNT(*) as cantidad
            FROM expediente 
            WHERE turno IS NOT NULL AND turno != ''
            GROUP BY turno
            HAVING COUNT(*) > 1
            ORDER BY turno
        """)
        
        duplicados = cursor.fetchall()
        
        if duplicados:
            print("⚠️ TURNOS DUPLICADOS ENCONTRADOS:")
            for turno, cantidad in duplicados:
                print(f"   {turno}: {cantidad} expedientes")
                
                # Mostrar detalles de los duplicados
                cursor.execute("""
                    SELECT radicado_completo, demandante 
                    FROM expediente 
                    WHERE turno = %s
                """, (turno,))
                
                expedientes = cursor.fetchall()
                for radicado, demandante in expedientes:
                    print(f"     - {radicado}: {demandante}")
        else:
            print("✅ No se encontraron turnos duplicados")
        
        # Verificar turnos fuera de horario laboral
        cursor.execute("""
            SELECT turno, COUNT(*) 
            FROM expediente 
            WHERE turno IS NOT NULL 
              AND turno != ''
              AND (turno < '08:00' OR turno > '17:00')
            GROUP BY turno
            ORDER BY turno
        """)
        
        fuera_horario = cursor.fetchall()
        
        if fuera_horario:
            print("\n⚠️ TURNOS FUERA DE HORARIO LABORAL:")
            for turno, cantidad in fuera_horario:
                print(f"   {turno}: {cantidad} expedientes")
        else:
            print("✅ Todos los turnos están en horario laboral")
        
    except Exception as e:
        print(f"❌ Error verificando conflictos: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conexion' in locals():
            conexion.close()

def generar_reporte_completo():
    """Genera un reporte completo del estado de turnos"""
    
    fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    print("\n" + "=" * 80)
    print(f"REPORTE COMPLETO DE TURNOS - {fecha_actual}")
    print("=" * 80)
    
    # Dashboard principal
    mostrar_dashboard()
    
    # Turnos detallados
    mostrar_turnos_detallados()
    
    # Verificación de conflictos
    verificar_conflictos()
    
    print("\n" + "=" * 80)
    print("Reporte generado exitosamente")
    print("=" * 80)

def main():
    """Función principal"""
    
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando == 'dashboard':
            mostrar_dashboard()
        elif comando == 'detallado':
            mostrar_turnos_detallados()
        elif comando == 'conflictos':
            verificar_conflictos()
        elif comando == 'reporte':
            generar_reporte_completo()
        else:
            print("Comandos disponibles: dashboard, detallado, conflictos, reporte")
    else:
        # Por defecto, mostrar reporte completo
        generar_reporte_completo()

if __name__ == '__main__':
    main()