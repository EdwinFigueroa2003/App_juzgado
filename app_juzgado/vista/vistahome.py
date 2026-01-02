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

def obtener_metricas_dashboard():
    """Obtiene las métricas para el dashboard"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        metricas = {}
        
        # 1. Total de expedientes
        cursor.execute("SELECT COUNT(*) FROM expedientes")
        metricas['total_expedientes'] = cursor.fetchone()[0]
        
        # 2. Expedientes por estado (NUEVOS ESTADOS)
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN estado_principal IS NOT NULL AND estado_adicional IS NOT NULL THEN 
                        CONCAT(estado_principal, ' + ', estado_adicional)
                    WHEN estado_principal IS NOT NULL THEN estado_principal
                    WHEN estado_adicional IS NOT NULL THEN estado_adicional
                    ELSE COALESCE(estado_actual, 'SIN_INFORMACION')
                END as estado_combinado,
                COUNT(*) 
            FROM expedientes 
            GROUP BY estado_combinado
            ORDER BY COUNT(*) DESC
        """)
        metricas['expedientes_por_estado'] = cursor.fetchall()
        
        # 2b. Estadísticas de estados principales
        cursor.execute("""
            SELECT estado_principal, COUNT(*) 
            FROM expedientes 
            WHERE estado_principal IS NOT NULL
            GROUP BY estado_principal
            ORDER BY COUNT(*) DESC
        """)
        metricas['estados_principales'] = cursor.fetchall()
        
        # 2c. Estadísticas de estados adicionales
        cursor.execute("""
            SELECT estado_adicional, COUNT(*) 
            FROM expedientes 
            WHERE estado_adicional IS NOT NULL
            GROUP BY estado_adicional
            ORDER BY COUNT(*) DESC
        """)
        metricas['estados_adicionales'] = cursor.fetchall()
        
        # 3. Expedientes por responsable
        cursor.execute("""
            SELECT responsable, COUNT(*) 
            FROM expedientes 
            WHERE responsable IS NOT NULL AND responsable != ''
            GROUP BY responsable
            ORDER BY COUNT(*) DESC
        """)
        metricas['expedientes_por_responsable'] = cursor.fetchall()
        
        # 4. Ingresos recientes (últimos 30 días)
        #fecha_limite = datetime.now() - timedelta(days=30)
        #cursor.execute("""
        #    SELECT COUNT(*) 
        #    FROM ingresos_expediente 
        #    WHERE fecha_ingreso >= %s
        #""", (fecha_limite.date(),))
        #metricas['ingresos_recientes'] = cursor.fetchone()[0]
        
        # 5. Expedientes actualizados recientemente (últimos 7 días)
        #fecha_limite_semana = datetime.now() - timedelta(days=7)
        #cursor.execute("""
        #    SELECT COUNT(*) 
        #    FROM expedientes 
        #    WHERE fecha_ultima_actualizacion >= %s
        #""", (fecha_limite_semana,))
        #metricas['actualizados_recientes'] = cursor.fetchone()[0]
        
        # 6. Top 5 expedientes más recientes
        cursor.execute("""
            SELECT radicado_completo, radicado_corto, demandante, demandado, 
                   estado_actual, estado_principal, estado_adicional, responsable, fecha_ultima_actualizacion
            FROM expedientes 
            ORDER BY fecha_ultima_actualizacion DESC NULLS LAST
            LIMIT 5
        """)
        metricas['expedientes_recientes'] = cursor.fetchall()
        
        # 7. Distribución por tipo de proceso
        cursor.execute("""
            SELECT tipo_tramite, COUNT(*) 
            FROM expedientes 
            WHERE tipo_tramite IS NOT NULL AND tipo_tramite != ''
            GROUP BY tipo_tramite
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """)
        metricas['tipos_proceso'] = cursor.fetchall()
        
        # 8. Actividad por mes (últimos 6 meses)
        #cursor.execute("""
        #    SELECT 
        #        DATE_TRUNC('month', fecha_ingreso) as mes,
        #        COUNT(*) as ingresos
        #    FROM ingresos_expediente 
        #    WHERE fecha_ingreso >= %s
        #    GROUP BY DATE_TRUNC('month', fecha_ingreso)
        #    ORDER BY mes DESC
        #    LIMIT 6
        #""", ((datetime.now() - timedelta(days=180)).date(),))
        #metricas['actividad_mensual'] = cursor.fetchall()
        
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