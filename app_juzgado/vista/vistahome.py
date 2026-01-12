from flask import Blueprint, render_template, request, flash, session, redirect, url_for
import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auth import login_required, get_current_user
from modelo.configBd import obtener_conexion

# Crear un Blueprint
vistahome = Blueprint('idvistahome', __name__, template_folder='templates')

def _detectar_columna_tipo(cursor):
    """Retorna el nombre de la columna existente entre 'tipo_solicitud' y 'tipo_tramite', o None"""
    try:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'expediente' AND column_name IN ('tipo_solicitud', 'tipo_tramite')
        """)
        cols = [r[0] for r in cursor.fetchall()]
        if 'tipo_solicitud' in cols:
            return 'tipo_solicitud'
        if 'tipo_tramite' in cols:
            return 'tipo_tramite'
        return None
    except:
        return None

def obtener_metricas_dashboard():
    """Obtiene las métricas para el dashboard"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        metricas = {}
        
        # 1. Total de expedientes
        cursor.execute("SELECT COUNT(*) FROM expediente")
        metricas['total_expediente'] = cursor.fetchone()[0]
        
        # 2. Expedientes por estado (basado en la nueva lógica)
        # ACTIVO PENDIENTE: tienen ingresos/actuaciones sin estados más recientes
        cursor.execute("""
            SELECT COUNT(*) FROM expediente e
            WHERE (EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
                   OR EXISTS (SELECT 1 FROM actuaciones a WHERE a.expediente_id = e.id))
            AND (NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
                 OR GREATEST(
                     COALESCE((SELECT MAX(i2.fecha_ingreso) FROM ingresos i2 WHERE i2.expediente_id = e.id), DATE '1900-01-01'),
                     COALESCE((SELECT MAX(a2.fecha_actuacion) FROM actuaciones a2 WHERE a2.expediente_id = e.id), DATE '1900-01-01'),
                     COALESCE(e.fecha_ingreso, DATE '1900-01-01')
                 ) > (SELECT MAX(s2.fecha_estado) FROM estados s2 WHERE s2.expediente_id = e.id))
        """)
        activo_pendiente = cursor.fetchone()[0]
        
        # ACTIVO RESUELTO: tienen estados recientes (< 1 año)
        cursor.execute("""
            SELECT COUNT(*) FROM expediente e
            WHERE EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
            AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) > 
                (CURRENT_DATE - INTERVAL '1 year')
        """)
        activo_resuelto = cursor.fetchone()[0]
        
        # INACTIVO RESUELTO: tienen estados antiguos (> 1 año)
        cursor.execute("""
            SELECT COUNT(*) FROM expediente e
            WHERE EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
            AND (SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id) <= 
                (CURRENT_DATE - INTERVAL '1 year')
        """)
        inactivo_resuelto = cursor.fetchone()[0]
        
        # PENDIENTE: sin ingresos, estados ni actuaciones
        cursor.execute("""
            SELECT COUNT(*) FROM expediente e
            WHERE NOT EXISTS (SELECT 1 FROM ingresos i WHERE i.expediente_id = e.id)
            AND NOT EXISTS (SELECT 1 FROM estados s WHERE s.expediente_id = e.id)
            AND NOT EXISTS (SELECT 1 FROM actuaciones a WHERE a.expediente_id = e.id)
        """)
        pendiente = cursor.fetchone()[0]
        
        metricas['expediente_por_estado'] = [
            ('Activo Pendiente', activo_pendiente),
            ('Activo Resuelto', activo_resuelto),
            ('Inactivo Resuelto', inactivo_resuelto),
            ('Pendiente', pendiente)
        ]
        
        # 2b. Estadísticas por responsable
        cursor.execute("""
            SELECT responsable, COUNT(*) 
            FROM expediente 
            WHERE responsable IS NOT NULL AND responsable != ''
            GROUP BY responsable
            ORDER BY COUNT(*) DESC
        """)
        metricas['expediente_por_responsable'] = cursor.fetchall()
        
        # 3. Top 5 expedientes más recientes (ordenados por la fecha máxima de actividad)
        cursor.execute("""
            SELECT 
                e.id, e.radicado_completo, e.radicado_corto, e.demandante, e.demandado, 
                e.responsable,
                GREATEST(
                    COALESCE((SELECT MAX(s.fecha_estado) FROM estados s WHERE s.expediente_id = e.id), DATE '1900-01-01'),
                    COALESCE((SELECT MAX(i.fecha_ingreso) FROM ingresos i WHERE i.expediente_id = e.id), DATE '1900-01-01'),
                    COALESCE((SELECT MAX(a.fecha_actuacion) FROM actuaciones a WHERE a.expediente_id = e.id), DATE '1900-01-01'),
                    COALESCE(e.fecha_ingreso, CURRENT_DATE)
                ) as fecha_actividad
            FROM expediente e
            ORDER BY fecha_actividad DESC
            LIMIT 5
        """)
        metricas['expediente_recientes'] = cursor.fetchall()
        
        # 4. Distribución por tipo de proceso
        tipo_col = _detectar_columna_tipo(cursor)
        if tipo_col:
            cursor.execute(f"""
                SELECT {tipo_col}, COUNT(*) 
                FROM expediente
                WHERE {tipo_col} IS NOT NULL AND {tipo_col} != ''
                GROUP BY {tipo_col}
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """)
            metricas['tipos_proceso'] = cursor.fetchall()
        else:
            # Si no existe la columna, devolver lista vacía
            metricas['tipos_proceso'] = []
        
        cursor.close()
        conn.close()
        
        return metricas
        
    except Exception as e:
        print(f"Error obteniendo métricas: {e}")
        return {}

@vistahome.route('/home', methods=['GET', 'POST'])
@login_required
def vista_home():
    user = get_current_user()
    metricas = obtener_metricas_dashboard()
    return render_template('home.html', user=user, metricas=metricas)


@vistahome.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('idvistalogin.vista_login'))