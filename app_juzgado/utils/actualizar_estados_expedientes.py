"""
Script para actualizar el campo 'estado' en la tabla expediente
basándose en la lógica de negocio:

COMPORTAMIENTO ACTUAL:
- Por defecto, SOLO procesa expedientes con estado = 'Pendiente' QUE TENGAN MOVIMIENTO (Grupo A)
- Expedientes Pendiente SIN movimiento (Grupo B) se mantienen como Pendiente
- Utiliza la misma lógica de estados que actualizar_estados_expedientes

LÓGICA DE ESTADOS (para Grupo A):
1. Si tiene ingresos o actuaciones SIN estados → Activo Pendiente
2. Si tiene SOLO estados (sin ingresos/actuaciones) → Verificar antigüedad:
   - Menos de 2 años → Activo Resuelto
   - Más de 2 años → Inactivo Resuelto
3. Si tiene ingresos/actuaciones Y estados → Comparar fechas:
   - Si actividad más reciente que último estado → Activo Pendiente
   - Si estado más reciente → Aplicar lógica de antigüedad (Activo/Inactivo Resuelto)

USO:
    python app_juzgado/utils/actualizar_estados_expedientes.py
    
    Opciones:
    --dry-run            : Solo muestra los cambios sin aplicarlos
    --expediente-id      : Actualizar solo un expediente específico
    --verbose            : Mostrar información detallada
    --todos              : Procesar TODOS los expedientes (no solo Pendiente)
    --asignar-turnos     : Asignar automáticamente turnos después de actualizar estados

EJEMPLOS:
    # Ver cambios que se harían en Pendiente con movimiento
    python actualizar_estados_expedientes.py --dry-run
    
    # Aplicar actualización a Pendiente con movimiento
    python actualizar_estados_expedientes.py
    
    # Actualizar y asignar turnos automáticamente
    python actualizar_estados_expedientes.py --asignar-turnos
    
    # Procesar todos los expedientes (no solo Pendiente)
    python actualizar_estados_expedientes.py --todos
"""

import sys
import os
from datetime import datetime, date
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app_juzgado.modelo.configBd import obtener_conexion

def normalize_date(fecha_valor):
    """Convierte cualquier tipo de fecha a datetime.date"""
    if fecha_valor is None:
        return None
    
    if isinstance(fecha_valor, date):
        return fecha_valor
    elif isinstance(fecha_valor, datetime):
        return fecha_valor.date()
    else:
        try:
            if isinstance(fecha_valor, str):
                return datetime.strptime(fecha_valor, '%Y-%m-%d').date()
            return fecha_valor
        except:
            return None

def calcular_estado_correcto(expediente_id, cursor):
    """
    Calcula el estado correcto del expediente basado en la lógica SIMPLIFICADA:
    
    - Activo Pendiente: fecha_ingreso (más reciente) > fecha_estado (última)
    - Activo Resuelto: fecha_estado (última) > fecha_ingreso (más reciente) Y < 2 años
    - Inactivo Resuelto: fecha_estado (última) > fecha_ingreso (más reciente) Y > 2 años
    
    NOTA: Se ignora la tabla 'actuaciones' para el cálculo del estado
    
    Returns: (estado_nuevo, razon)
    """
    
    # Obtener contadores y fechas de ingresos
    cursor.execute("""
        SELECT COUNT(*), MAX(fecha_ingreso) 
        FROM ingresos 
        WHERE expediente_id = %s
    """, (expediente_id,))
    
    ingresos_count, ultima_fecha_ingreso = cursor.fetchone()
    ultima_fecha_ingreso = normalize_date(ultima_fecha_ingreso)
    
    # Obtener contadores y fechas de estados
    cursor.execute("""
        SELECT COUNT(*), MAX(fecha_estado) 
        FROM estados 
        WHERE expediente_id = %s
    """, (expediente_id,))
    
    estados_count, ultima_fecha_estado = cursor.fetchone()
    ultima_fecha_estado = normalize_date(ultima_fecha_estado)
    
    # LÓGICA SIMPLIFICADA DE ESTADOS (solo ingresos vs estados)
    
    # Caso 1: Tiene ingresos pero NO tiene estados → Activo Pendiente
    if ingresos_count > 0 and estados_count == 0:
        return "Activo Pendiente", f"Tiene {ingresos_count} ingreso(s) sin estados"
    
    # Caso 2: Tiene estados pero NO tiene ingresos → Verificar antigüedad
    elif estados_count > 0 and ingresos_count == 0:
        if ultima_fecha_estado:
            dias_desde_ultimo_estado = (datetime.now().date() - ultima_fecha_estado).days
            
            if dias_desde_ultimo_estado <= 730:
                return "Activo Resuelto", f"Solo estados, resuelto hace {dias_desde_ultimo_estado} días (< 2 años)"
            else:
                return "Inactivo Resuelto", f"Solo estados, resuelto hace {dias_desde_ultimo_estado} días (> 2 años)"
        else:
            return "Activo Resuelto", "Tiene estados pero sin fecha válida"
    
    # Caso 3: Tiene AMBOS (ingresos Y estados) → Comparar fechas
    elif ingresos_count > 0 and estados_count > 0:
        if ultima_fecha_ingreso and ultima_fecha_estado:
            if ultima_fecha_ingreso > ultima_fecha_estado:
                # Ingreso más reciente → Activo Pendiente
                return "Activo Pendiente", f"Ingreso más reciente ({ultima_fecha_ingreso}) que último estado ({ultima_fecha_estado})"
            else:
                # Estado más reciente → Aplicar lógica de antigüedad
                dias_desde_ultimo_estado = (datetime.now().date() - ultima_fecha_estado).days
                
                if dias_desde_ultimo_estado <= 730:
                    return "Activo Resuelto", f"Estado más reciente ({ultima_fecha_estado}), hace {dias_desde_ultimo_estado} días (< 2 años)"
                else:
                    return "Inactivo Resuelto", f"Estado más reciente ({ultima_fecha_estado}), hace {dias_desde_ultimo_estado} días (> 2 años)"
        elif ultima_fecha_ingreso:
            # Solo hay fecha de ingreso válida → Activo Pendiente
            return "Activo Pendiente", f"Solo fecha de ingreso válida ({ultima_fecha_ingreso})"
        elif ultima_fecha_estado:
            # Solo hay fecha de estado válida → Verificar antigüedad
            dias_desde_ultimo_estado = (datetime.now().date() - ultima_fecha_estado).days
            if dias_desde_ultimo_estado <= 730:
                return "Activo Resuelto", f"Solo fecha de estado válida ({ultima_fecha_estado}), hace {dias_desde_ultimo_estado} días (< 2 años)"
            else:
                return "Inactivo Resuelto", f"Solo fecha de estado válida ({ultima_fecha_estado}), hace {dias_desde_ultimo_estado} días (> 2 años)"
        else:
            # Sin fechas válidas → Activo Pendiente por defecto
            return "Activo Pendiente", "Sin fechas válidas para comparar"
    
    # Caso 4: Sin ingresos ni estados
    else:
        return "Sin Movimiento", "Sin movimiento registrado (sin ingresos ni estados)"

def actualizar_estados(dry_run=False, expediente_id=None, verbose=False, solo_pendientes=True):
    """
    Actualiza el campo estado de expedientes (por defecto solo los que están en 'Pendiente')
    
    Lógica:
    - Grupo A: Expedientes Pendiente CON movimiento → Se actualizan a estado correcto
    - Grupo B: Expedientes Pendiente SIN movimiento → Se mantienen como Pendiente
    
    Args:
        dry_run: Si es True, solo muestra los cambios sin aplicarlos
        expediente_id: Si se proporciona, solo actualiza ese expediente
        verbose: Si es True, muestra información detallada
        solo_pendientes: Si es True, solo procesa expedientes con estado = 'Pendiente'
    """
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # Obtener expedientes Pendiente y clasificarlos en Grupo A (con movimiento) y B (sin movimiento)
        if expediente_id:
            query = """
                SELECT id, radicado_completo, estado 
                FROM expediente 
                WHERE id = %s
            """
            params = (expediente_id,)
        elif solo_pendientes:
            # Solo expedientes con estado = 'Pendiente' que tengan movimiento (Grupo A)
            query = """
                SELECT e.id, e.radicado_completo, e.estado
                FROM expediente e
                WHERE e.estado = 'Pendiente'
                  AND (
                    EXISTS (SELECT 1 FROM ingresos WHERE expediente_id = e.id LIMIT 1)
                    OR EXISTS (SELECT 1 FROM estados WHERE expediente_id = e.id LIMIT 1)
                  )
                ORDER BY e.id
            """
            params = ()
        else:
            query = """
                SELECT id, radicado_completo, estado 
                FROM expediente 
                ORDER BY id
            """
            params = ()
        
        cursor.execute(query, params)
        expedientes = cursor.fetchall()
        total_expedientes = len(expedientes)
        
        print(f"\n{'='*80}")
        print(f"ACTUALIZACIÓN DE ESTADOS DE EXPEDIENTES")
        print(f"{'='*80}")
        print(f"Modo: {'DRY RUN (sin cambios)' if dry_run else 'ACTUALIZACIÓN REAL'}")
        if solo_pendientes:
            print(f"Filtro: Solo expedientes con estado = 'Pendiente' Y con movimiento")
        print(f"Total de expedientes a procesar: {total_expedientes}")
        print(f"{'='*80}\n")
        
        # Contadores
        actualizados = 0
        sin_cambios = 0
        errores = 0
        cambios_por_estado = {}
        
        for idx, (exp_id, radicado, estado_actual) in enumerate(expedientes, 1):
            try:
                # Calcular estado correcto
                estado_nuevo, razon = calcular_estado_correcto(exp_id, cursor)
                
                # Verificar si hay cambio
                if estado_actual != estado_nuevo:
                    actualizados += 1
                    
                    # Registrar cambio por tipo
                    clave_cambio = f"{estado_actual or 'NULL'} → {estado_nuevo}"
                    cambios_por_estado[clave_cambio] = cambios_por_estado.get(clave_cambio, 0) + 1
                    
                    if verbose or dry_run:
                        print(f"[{idx}/{total_expedientes}] ID: {exp_id} | Radicado: {radicado}")
                        print(f"  Estado actual: {estado_actual or 'NULL'}")
                        print(f"  Estado nuevo:  {estado_nuevo}")
                        print(f"  Razón: {razon}")
                        print()
                    
                    # Actualizar en BD si no es dry-run
                    if not dry_run:
                        cursor.execute("""
                            UPDATE expediente 
                            SET estado = %s 
                            WHERE id = %s
                        """, (estado_nuevo, exp_id))
                else:
                    sin_cambios += 1
                    if verbose:
                        print(f"[{idx}/{total_expedientes}] ID: {exp_id} | Sin cambios ({estado_actual})")
                
            except Exception as e:
                errores += 1
                print(f"ERROR en expediente {exp_id}: {str(e)}")
        
        # Commit si no es dry-run
        if not dry_run:
            conexion.commit()
            print(f"\n✓ Cambios guardados en la base de datos")
        
        # Resumen
        print(f"\n{'='*80}")
        print(f"RESUMEN DE ACTUALIZACIÓN")
        print(f"{'='*80}")
        print(f"Total procesados:     {total_expedientes}")
        print(f"Actualizados:         {actualizados}")
        print(f"Sin cambios:          {sin_cambios}")
        print(f"Errores:              {errores}")
        print(f"{'='*80}")
        
        if cambios_por_estado:
            print(f"\nDISTRIBUCIÓN DE CAMBIOS POR ESTADO:")
            print(f"{'-'*80}")
            for cambio, cantidad in sorted(cambios_por_estado.items(), key=lambda x: x[1], reverse=True):
                print(f"  {cambio}: {cantidad:,} expediente(s)")
            print(f"{'-'*80}")
        
        if dry_run and actualizados > 0:
            print(f"\n⚠ MODO DRY-RUN: Los cambios NO se aplicaron.")
            print(f"  Ejecuta sin --dry-run para aplicar los cambios.")
        
    except Exception as e:
        print(f"\nERROR GENERAL: {str(e)}")
        conexion.rollback()
        raise
    
    finally:
        cursor.close()
        conexion.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Actualizar estados de expedientes')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Solo mostrar cambios sin aplicarlos')
    parser.add_argument('--expediente-id', type=int, 
                       help='ID del expediente a actualizar (opcional)')
    parser.add_argument('--verbose', action='store_true', 
                       help='Mostrar información detallada')
    parser.add_argument('--todos', action='store_true',
                       help='Procesar TODOS los expedientes (por defecto solo Pendiente con movimiento)')
    parser.add_argument('--asignar-turnos', action='store_true',
                       help='Asignar turnos automáticamente a los expedientes actualizados')
    
    args = parser.parse_args()
    
    # Ejecutar actualización
    actualizar_estados(
        dry_run=args.dry_run,
        expediente_id=args.expediente_id,
        verbose=args.verbose,
        solo_pendientes=not args.todos
    )
    
    # Asignar turnos si se solicitó y no fue dry-run
    if args.asignar_turnos and not args.dry_run:
        print("\n🔄 Asignando turnos automáticamente...")
        try:
            from utils.turnos import sincronizar_estados_y_turnos
            conexion = obtener_conexion()
            resultado = sincronizar_estados_y_turnos(conexion)
            print(f"✅ Estados sincronizados: {resultado.get('estados_actualizados', 0)}")
            print(f"✅ Turnos asignados: {resultado.get('turnos_asignados', 0)}")
            if resultado.get('sin_turno_pendientes'):
                print(f"⚠️  Pendientes sin turno: {resultado.get('sin_turno_pendientes', 0)}")
            conexion.close()
        except ImportError:
            print("⚠️  No se pudo importar sincronizar_estados_y_turnos")
        except Exception as e:
            print(f"❌ Error al asignar turnos: {str(e)}")
