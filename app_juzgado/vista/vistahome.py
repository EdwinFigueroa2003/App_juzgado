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
    """Obtiene las métricas para el dashboard - ULTRA OPTIMIZADO usando campo estado"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        metricas = {}
        
        # 1. Total de expedientes - DIRECTO
        cursor.execute("SELECT COUNT(*) FROM expediente")
        metricas['total_expediente'] = cursor.fetchone()[0]
        
        # 2. Expedientes por estado - DIRECTO desde campo estado (ULTRA RÁPIDO)
        # Orden específico para coincidir con los colores del gráfico:
        # 1. Pendiente (#4e73df - azul)
        # 2. Activo Pendiente (#1cc88a - verde)
        # 3. Inactivo Resuelto (#36b9cc - cyan)
        # 4. Activo Resuelto (#f6c23e - amarillo)
        cursor.execute("""
            SELECT 
                COALESCE(estado, 'Sin Estado') as estado_exp,
                COUNT(*) as cantidad
            FROM expediente 
            GROUP BY estado
            ORDER BY 
                CASE estado
                    WHEN 'Pendiente' THEN 1
                    WHEN 'Activo Pendiente' THEN 2
                    WHEN 'Inactivo Resuelto' THEN 3
                    WHEN 'Activo Resuelto' THEN 4
                    ELSE 5
                END
        """)
        metricas['expediente_por_estado'] = cursor.fetchall()
        
        # 3. Expedientes por responsable - DIRECTO
        cursor.execute("""
            SELECT 
                COALESCE(responsable, 'Sin Asignar') as responsable, 
                COUNT(*) 
            FROM expediente 
            GROUP BY responsable
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        metricas['expediente_por_responsable'] = cursor.fetchall()
        
        # 4. Top 10 expedientes más recientes - OPTIMIZADO
        cursor.execute("""
            SELECT 
                e.id, e.radicado_completo, e.radicado_corto, 
                e.demandante, e.demandado, e.responsable,
                COALESCE(e.fecha_ingreso, CURRENT_DATE) as fecha_actividad,
                COALESCE(e.estado, 'Sin Estado') as estado_actual
            FROM expediente e
            ORDER BY e.fecha_ingreso DESC NULLS LAST
            LIMIT 10
        """)
        metricas['expediente_recientes'] = cursor.fetchall()
        
        # 5. Estadísticas rápidas de tablas relacionadas
        cursor.execute("SELECT COUNT(*) FROM actuaciones")
        metricas['total_actuaciones'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ingresos")
        metricas['total_ingresos'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM estados")
        metricas['total_estados'] = cursor.fetchone()[0]
        
        # 6. Distribución por tipo de proceso - SIMPLIFICADO
        tipo_col = _detectar_columna_tipo(cursor)
        if tipo_col:
            cursor.execute(f"""
                SELECT 
                    COALESCE({tipo_col}, 'Sin Especificar') as tipo, 
                    COUNT(*) 
                FROM expediente
                GROUP BY {tipo_col}
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """)
            metricas['tipos_proceso'] = cursor.fetchall()
        else:
            metricas['tipos_proceso'] = []
        
        cursor.close()
        conn.close()
        
        return metricas
        
    except Exception as e:
        print(f"Error obteniendo métricas: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_expediente': 0,
            'expediente_por_estado': [],
            'expediente_por_responsable': [],
            'expediente_recientes': [],
            'total_actuaciones': 0,
            'total_ingresos': 0,
            'total_estados': 0,
            'tipos_proceso': []
        }

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