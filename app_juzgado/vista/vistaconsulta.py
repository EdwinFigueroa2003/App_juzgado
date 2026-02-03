from flask import Blueprint, render_template, request, flash, jsonify, send_file, redirect, url_for
import sys
import os
import logging
from datetime import datetime, timedelta, date
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import re

# Configurar logging específico para expedientes
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion

vistaconsulta = Blueprint('vistaconsulta', __name__, template_folder='templates')

@vistaconsulta.route('/consulta')
def consulta_publica():
    """Portal público de consulta de expedientes"""
    return render_template('consulta.html')

@vistaconsulta.route('/api/buscar_expediente', methods=['POST'])
def buscar_expediente():
    """API para búsqueda de expedientes por radicado"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        radicado = data.get('radicado', '').strip()
        
        if not radicado:
            return jsonify({'error': 'Debe ingresar un número de radicado'}), 400
        
        # Limpiar y normalizar el radicado
        radicado_limpio = re.sub(r'[^\d-]', '', radicado)
        
        if not radicado_limpio:
            return jsonify({'error': 'Formato de radicado inválido'}), 400
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Búsqueda flexible por radicado (completo o parcial)
        query = """
        SELECT 
            id,
            radicado_completo,
            demandante,
            demandado,
            estado,
            fecha_ingreso,
            turno            
        FROM expediente 
        WHERE radicado_completo ILIKE %s 
           OR radicado_corto ILIKE %s
           OR radicado_completo ILIKE %s
        ORDER BY fecha_ingreso DESC
        LIMIT 10
        """
        
        # Patrones de búsqueda
        patron_completo = f"%{radicado_limpio}%"
        patron_corto = f"%{radicado_limpio.split('-')[-1]}%" if '-' in radicado_limpio else patron_completo
        
        cursor.execute(query, (patron_completo, patron_corto, patron_completo))
        resultados = cursor.fetchall()
        
        # Helper para convertir a date
        def _to_date(v):
            if v is None:
                return None
            if isinstance(v, date):
                return v
            if isinstance(v, datetime):
                return v.date()
            try:
                return datetime.fromisoformat(str(v)).date()
            except Exception:
                return None

        expedientes = []
        for row in resultados:
            exp_id = row[0]
            radicado_val = row[1]
            fecha_ingreso_val = row[5]

            # Calcular fecha_ingreso_mas_antigua_sin_salida consultando tablas relacionadas
            try:
                cursor.execute("SELECT fecha_ingreso FROM ingresos WHERE expediente_id = %s ORDER BY fecha_ingreso ASC", (exp_id,))
                ingresos_rows = cursor.fetchall()
                cursor.execute("SELECT fecha_estado FROM estados WHERE expediente_id = %s ORDER BY fecha_estado ASC", (exp_id,))
                estados_rows = cursor.fetchall()

                fecha_mas_antigua = None
                ingresos_dates = [_to_date(r[0]) for r in ingresos_rows]
                estados_dates = [_to_date(r[0]) for r in estados_rows]

                for fi in ingresos_dates:
                    if not fi:
                        continue
                    tiene_salida = any(fe and fe > fi for fe in estados_dates)
                    if not tiene_salida:
                        if fecha_mas_antigua is None or fi < fecha_mas_antigua:
                            fecha_mas_antigua = fi
            except Exception:
                logger.exception('Error calculando ingresos/estados para consulta pública')
                fecha_mas_antigua = None

            expedientes.append({
                'id': exp_id,
                'numero_radicado': radicado_val or 'No disponible',
                'demandante': row[2] or 'No disponible',
                'demandado': row[3] or 'No disponible',
                'estado': row[4] or 'pendiente',
                'fecha_ingreso': fecha_ingreso_val.strftime('%d/%m/%Y') if fecha_ingreso_val else 'No disponible',
                'turno': row[6] or '',
                'fecha_actuacion': 'No disponible',
                'actuacion': 'Sin actuaciones',
                'fecha_ingreso_mas_antigua_sin_salida': fecha_mas_antigua.strftime('%d/%m/%Y') if fecha_mas_antigua else (fecha_ingreso_val.strftime('%d/%m/%Y') if fecha_ingreso_val else 'No disponible')
            })
        
        cursor.close()
        conexion.close()
        
        return jsonify({
            'success': True,
            'expedientes': expedientes,
            'total': len(expedientes)
        })
        
    except Exception as e:
        logger.error(f"Error en búsqueda de expediente: {str(e)}")
        return jsonify({'error': 'Error interno del servidor. Intente nuevamente.'}), 500

@vistaconsulta.route('/api/buscar_por_nombres', methods=['POST'])
def buscar_por_nombres():
    """API para búsqueda de expedientes por nombres de demandante/demandado con paginación"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        nombre = data.get('nombre', '').strip()
        pagina = data.get('pagina', 1)
        items_por_pagina = 10
        
        if not nombre or len(nombre) < 3:
            return jsonify({'error': 'Debe ingresar al menos 3 caracteres'}), 400
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Búsqueda por nombres (demandante o demandado) - traer todos los resultados
        query = """
        SELECT 
            id,
            radicado_completo,
            demandante,
            demandado,
            estado,
            fecha_ingreso,
            turno
        FROM expediente 
        WHERE demandante ILIKE %s 
           OR demandado ILIKE %s
        ORDER BY fecha_ingreso DESC
        """
        
        patron_busqueda = f"%{nombre}%"
        cursor.execute(query, (patron_busqueda, patron_busqueda))
        resultados = cursor.fetchall()
        
        total_items = len(resultados)
        total_paginas = (total_items + items_por_pagina - 1) // items_por_pagina if total_items > 0 else 1
        
        # Validar página
        if pagina < 1:
            pagina = 1
        elif pagina > total_paginas:
            pagina = total_paginas
        
        # Calcular índices para el slice
        indice_inicio = (pagina - 1) * items_por_pagina
        indice_fin = indice_inicio + items_por_pagina
        resultados_pagina = resultados[indice_inicio:indice_fin]
        
        # Helper para convertir a date
        def _to_date(v):
            if v is None:
                return None
            if isinstance(v, date):
                return v
            if isinstance(v, datetime):
                return v.date()
            try:
                return datetime.fromisoformat(str(v)).date()
            except Exception:
                return None

        expedientes = []
        for row in resultados_pagina:
            exp_id = row[0]
            radicado_val = row[1]
            fecha_ingreso_val = row[5]

            try:
                cursor.execute("SELECT fecha_ingreso FROM ingresos WHERE expediente_id = %s ORDER BY fecha_ingreso ASC", (exp_id,))
                ingresos_rows = cursor.fetchall()
                cursor.execute("SELECT fecha_estado FROM estados WHERE expediente_id = %s ORDER BY fecha_estado ASC", (exp_id,))
                estados_rows = cursor.fetchall()

                fecha_mas_antigua = None
                ingresos_dates = [_to_date(r[0]) for r in ingresos_rows]
                estados_dates = [_to_date(r[0]) for r in estados_rows]

                for fi in ingresos_dates:
                    if not fi:
                        continue
                    tiene_salida = any(fe and fe > fi for fe in estados_dates)
                    if not tiene_salida:
                        if fecha_mas_antigua is None or fi < fecha_mas_antigua:
                            fecha_mas_antigua = fi
            except Exception:
                logger.exception('Error calculando ingresos/estados para búsqueda por nombres')
                fecha_mas_antigua = None

            expedientes.append({
                'id': exp_id,
                'numero_radicado': radicado_val or 'No disponible',
                'demandante': row[2] or 'No disponible',
                'demandado': row[3] or 'No disponible',
                'estado': row[4] or 'pendiente',
                'fecha_ingreso': fecha_ingreso_val.strftime('%d/%m/%Y') if fecha_ingreso_val else 'No disponible',
                'turno': row[6] or '',
                'fecha_actuacion': 'No disponible',
                'actuacion': 'Sin actuaciones',
                'fecha_ingreso_mas_antigua_sin_salida': fecha_mas_antigua.strftime('%d/%m/%Y') if fecha_mas_antigua else (fecha_ingreso_val.strftime('%d/%m/%Y') if fecha_ingreso_val else 'No disponible')
            })
        
        cursor.close()
        conexion.close()
        
        # Calcular información de paginación
        inicio_item = indice_inicio + 1 if total_items > 0 else 0
        fin_item = min(indice_fin, total_items)
        
        # Generar lista de páginas a mostrar (máximo 5 páginas)
        paginas_inicio = max(1, pagina - 2)
        paginas_fin = min(total_paginas, pagina + 2)
        paginas_mostrar = list(range(paginas_inicio, paginas_fin + 1))
        
        paginacion = {
            'pagina_actual': pagina,
            'total_paginas': total_paginas,
            'total_items': total_items,
            'items_por_pagina': items_por_pagina,
            'inicio_item': inicio_item,
            'fin_item': fin_item,
            'tiene_anterior': pagina > 1,
            'tiene_siguiente': pagina < total_paginas,
            'pagina_anterior': pagina - 1,
            'pagina_siguiente': pagina + 1,
            'paginas_mostrar': paginas_mostrar,
            'nombre': nombre
        }
        
        return jsonify({
            'success': True,
            'expedientes': expedientes,
            'total': total_items,
            'paginacion': paginacion
        })
        
    except Exception as e:
        logger.error(f"Error en búsqueda por nombres: {str(e)}")
        return jsonify({'error': 'Error interno del servidor. Intente nuevamente.'}), 500

@vistaconsulta.route('/api/turnos_del_dia')
def turnos_del_dia():
    """API para obtener los turnos programados para hoy"""
    try:
        fecha_hoy = date.today()
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Obtener turnos del día actual (expedientes con turno asignado)
        query = """
        SELECT 
            radicado_completo,
            demandante,
            demandado,
            turno,
            estado
        FROM expediente 
        WHERE turno IS NOT NULL
           AND turno != ''
           AND estado = 'Activo Pendiente'
        ORDER BY turno ASC
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        turnos = []
        for row in resultados:
            turnos.append({
                'numero_radicado': row[0] or 'No disponible',  # radicado_completo
                'demandante': row[1] or 'No disponible',
                'demandado': row[2] or 'No disponible',
                'turno': row[3] or '',
                'estado': row[4] or 'pendiente',
                'fecha_actuacion': fecha_hoy.strftime('%d/%m/%Y')
            })
        
        cursor.close()
        conexion.close()
        
        return jsonify({
            'success': True,
            'turnos': turnos,
            'fecha': fecha_hoy.strftime('%d/%m/%Y'),
            'total': len(turnos)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo turnos del día: {str(e)}")
        return jsonify({'error': 'Error interno del servidor. Intente nuevamente.'}), 500

@vistaconsulta.route('/turnos')
def vista_turnos():
    """Vista pública de turnos del día"""
    return render_template('turnos_publicos.html')

@vistaconsulta.route('/api/turnos_publicos')
def turnos_publicos():
    """API para obtener turnos públicos con información básica"""
    try:
        fecha_hoy = date.today()
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Obtener turnos del día con información básica para mostrar públicamente
        query = """
        SELECT 
            ROW_NUMBER() OVER (ORDER BY turno ASC) as numero,
            CONCAT(SUBSTRING(demandante FROM 1 FOR 1), '***') as nombre_anonimo,
            SUBSTRING(radicado_completo FROM LENGTH(radicado_completo) - 3) as cedula_parcial,
            'Consulta General' as tipo,
            turno as hora,
            CASE 
                WHEN estado = 'Inactivo Resuelto' THEN 'completado'
                WHEN estado = 'Activo Pendiente' AND turno <= TO_CHAR(CURRENT_TIME, 'HH24:MI') THEN 'atendiendo'
                ELSE 'esperando'
            END as estado
        FROM expediente 
        WHERE turno IS NOT NULL
           AND turno != ''
           AND estado IN ('Activo Pendiente', 'Inactivo Resuelto')
        ORDER BY turno ASC
        LIMIT 50
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        turnos = []
        for row in resultados:
            turnos.append({
                'numero': int(row[0]),
                'nombre': row[1] or f"Usuario {row[0]}",
                'cedula': f"***{row[2]}" if row[2] else "***",
                'tipo': row[3],
                'hora': row[4] or '09:00',
                'estado': row[5]
            })
        
        cursor.close()
        conexion.close()
        
        return jsonify({
            'success': True,
            'turnos': turnos,
            'fecha': fecha_hoy.strftime('%d/%m/%Y'),
            'total': len(turnos)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo turnos públicos: {str(e)}")
        return jsonify({'error': 'Error interno del servidor. Intente nuevamente.'}), 500

