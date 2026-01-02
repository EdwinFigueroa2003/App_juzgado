from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo.configBd import obtener_conexion
from utils.auth import login_required, admin_required

# Crear un Blueprint
vistaroles = Blueprint('idvistaroles', __name__, template_folder='templates')

@vistaroles.route('/roles', methods=['GET', 'POST'])
@login_required
@admin_required
def vista_roles():
    usuarios = []
    mensaje = ""
    usuario_buscado = None
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        if accion == 'asignar_rol':
            usuario_id = request.form.get('usuario_id')
            nuevo_rol = request.form.get('rol')
            
            if usuario_id and nuevo_rol:
                try:
                    resultado = asignar_rol_usuario(usuario_id, nuevo_rol)
                    if resultado:
                        mensaje = f"Rol '{nuevo_rol}' asignado exitosamente"
                        flash(mensaje, 'success')
                    else:
                        mensaje = "Error al asignar el rol"
                        flash(mensaje, 'error')
                except Exception as e:
                    mensaje = f"Error: {str(e)}"
                    flash(mensaje, 'error')
        
        elif accion == 'remover_rol':
            usuario_id = request.form.get('usuario_id')
            
            if usuario_id:
                try:
                    resultado = remover_rol_usuario(usuario_id)
                    if resultado:
                        mensaje = "Rol removido exitosamente"
                        flash(mensaje, 'success')
                    else:
                        mensaje = "Error al remover el rol"
                        flash(mensaje, 'error')
                except Exception as e:
                    mensaje = f"Error: {str(e)}"
                    flash(mensaje, 'error')
        
        elif accion == 'asignar_masivo':
            usuarios_ids = request.form.getlist('usuarios_ids[]')
            rol_masivo = request.form.get('rol_masivo')
            
            if usuarios_ids and rol_masivo:
                try:
                    resultado = asignar_rol_masivo(usuarios_ids, rol_masivo)
                    mensaje = f"Se asignó el rol '{rol_masivo}' a {resultado['exitosos']} usuario(s)"
                    if resultado['fallidos'] > 0:
                        mensaje += f". {resultado['fallidos']} fallaron"
                    flash(mensaje, 'success' if resultado['fallidos'] == 0 else 'warning')
                except Exception as e:
                    mensaje = f"Error en asignación masiva: {str(e)}"
                    flash(mensaje, 'error')
        
        elif accion == 'buscar_usuario':
            termino_busqueda = request.form.get('termino_busqueda', '').strip()
            
            if termino_busqueda:
                try:
                    usuario_buscado = buscar_usuario_por_nombre_correo(termino_busqueda)
                    if not usuario_buscado:
                        mensaje = f"No se encontró ningún usuario con: {termino_busqueda}"
                        flash(mensaje, 'warning')
                except Exception as e:
                    mensaje = f"Error en búsqueda: {str(e)}"
                    flash(mensaje, 'error')
        
        elif accion == 'asignar_roles_aleatorios':
            try:
                resultado = asignar_roles_aleatorios()
                mensaje = f"Se asignaron roles aleatorios a {resultado['total']} usuarios. "
                mensaje += f"Escribientes: {resultado['escribientes']}, Sustanciadores: {resultado['sustanciadores']}"
                flash(mensaje, 'success')
            except Exception as e:
                mensaje = f"Error al asignar roles aleatorios: {str(e)}"
                flash(mensaje, 'error')
        
        elif accion == 'remover_todos_roles':
            try:
                resultado = remover_todos_roles()
                mensaje = f"Se removieron los roles de {resultado} usuario(s)"
                flash(mensaje, 'success')
            except Exception as e:
                mensaje = f"Error al remover todos los roles: {str(e)}"
                flash(mensaje, 'error')
    
    # Obtener todos los usuarios
    try:
        usuarios = obtener_usuarios_con_roles()
    except Exception as e:
        mensaje = f"Error al cargar usuarios: {str(e)}"
        flash(mensaje, 'error')
    
    return render_template('roles.html', 
                         usuarios=usuarios, 
                         mensaje=mensaje,
                         usuario_buscado=usuario_buscado)

def obtener_usuarios_con_roles():
    """Obtiene todos los usuarios con sus roles actuales"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Consulta corregida con la estructura real de la BD
        query = """
            SELECT u.id, u.nombre, u.correo, r.nombre_rol as rol_nombre, u.fecha_registro, u.activo
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            ORDER BY 
                CASE 
                    WHEN r.nombre_rol = 'ESCRIBIENTE' THEN 1
                    WHEN r.nombre_rol = 'SUSTANCIADOR' THEN 2
                    WHEN r.nombre_rol IS NULL THEN 3
                    ELSE 4
                END,
                u.nombre
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        usuarios = []
        for row in resultados:
            usuarios.append({
                'id': row[0],
                'nombre': row[1],
                'correo': row[2],  # Mapear correo a correo para consistencia con template
                'rol': row[3],    # nombre_rol desde la tabla roles
                'fecha_creacion': row[4],  # fecha_registro
                'activo': row[5] if row[5] is not None else True
            })
        
        cursor.close()
        conn.close()
        
        return usuarios
        
    except Exception as e:
        print(f"Error en obtener_usuarios_con_roles: {e}")
        raise e

def asignar_rol_usuario(usuario_id, rol_nombre):
    """Asigna un rol a un usuario"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Validar que el rol sea válido y obtener su ID
        roles_validos = ['ESCRIBIENTE', 'SUSTANCIADOR']
        if rol_nombre not in roles_validos:
            raise ValueError(f"Rol inválido. Debe ser uno de: {', '.join(roles_validos)}")
        
        # Obtener el ID del rol usando nombre_rol
        cursor.execute("SELECT id FROM roles WHERE nombre_rol = %s", (rol_nombre,))
        rol_result = cursor.fetchone()
        
        if not rol_result:
            raise ValueError(f"Rol '{rol_nombre}' no encontrado en la base de datos")
        
        rol_id = rol_result[0]
        
        # Actualizar el rol del usuario
        query = """
            UPDATE usuarios 
            SET rol_id = %s, activo = TRUE
            WHERE id = %s
        """
        
        cursor.execute(query, (rol_id, usuario_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            cursor.close()
            conn.close()
            return True
        else:
            cursor.close()
            conn.close()
            return False
        
    except Exception as e:
        print(f"Error en asignar_rol_usuario: {e}")
        raise e

def remover_rol_usuario(usuario_id):
    """Remueve el rol de un usuario"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Remover el rol del usuario (establecer rol_id a NULL)
        query = """
            UPDATE usuarios 
            SET rol_id = NULL
            WHERE id = %s
        """
        
        cursor.execute(query, (usuario_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            cursor.close()
            conn.close()
            return True
        else:
            cursor.close()
            conn.close()
            return False
        
    except Exception as e:
        print(f"Error en remover_rol_usuario: {e}")
        raise e

@vistaroles.route('/api/usuarios/<int:usuario_id>/rol', methods=['POST'])
@login_required
@admin_required
def api_cambiar_rol(usuario_id):
    """API para cambiar rol de usuario via AJAX"""
    try:
        data = request.get_json()
        nuevo_rol = data.get('rol')
        
        if nuevo_rol:
            resultado = asignar_rol_usuario(usuario_id, nuevo_rol)
            if resultado:
                return jsonify({'success': True, 'message': f'Rol {nuevo_rol} asignado exitosamente'})
            else:
                return jsonify({'success': False, 'message': 'Error al asignar rol'})
        else:
            resultado = remover_rol_usuario(usuario_id)
            if resultado:
                return jsonify({'success': True, 'message': 'Rol removido exitosamente'})
            else:
                return jsonify({'success': False, 'message': 'Error al remover rol'})
                
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@vistaroles.route('/api/estadisticas-roles')
@login_required
@admin_required
def api_estadisticas_roles():
    """API para obtener estadísticas de roles"""
    try:
        usuarios = obtener_usuarios_con_roles()
        
        estadisticas = {
            'total_usuarios': len(usuarios),
            'escribientes': len([u for u in usuarios if u['rol'] == 'ESCRIBIENTE']),
            'sustanciadores': len([u for u in usuarios if u['rol'] == 'SUSTANCIADOR']),
            'sin_rol': len([u for u in usuarios if not u['rol']]),
            'activos': len([u for u in usuarios if u['activo']]),
            'inactivos': len([u for u in usuarios if not u['activo']])
        }
        
        return jsonify(estadisticas)
        
    except Exception as e:
        return jsonify({'error': str(e)})

def obtener_responsables_activos():
    """Obtiene solo los usuarios con roles asignados y activos"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        query = """
            SELECT u.id, u.nombre, u.correo, r.nombre_rol as rol_nombre
            FROM usuarios u
            INNER JOIN roles r ON u.rol_id = r.id
            WHERE u.activo = TRUE
            ORDER BY r.nombre_rol, u.nombre
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        responsables = []
        for row in resultados:
            responsables.append({
                'id': row[0],
                'nombre': row[1],
                'correo': row[2],  # Mapear correo a correo para consistencia
                'rol': row[3]
            })
        
        cursor.close()
        conn.close()
        
        return responsables
        
    except Exception as e:
        print(f"Error en obtener_responsables_activos: {e}")
        raise e

def asignar_rol_masivo(usuarios_ids, rol_nombre):
    """Asigna un rol a múltiples usuarios"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Validar que el rol sea válido y obtener su ID
        roles_validos = ['ESCRIBIENTE', 'SUSTANCIADOR']
        if rol_nombre not in roles_validos:
            raise ValueError(f"Rol inválido. Debe ser uno de: {', '.join(roles_validos)}")
        
        # Obtener el ID del rol usando nombre_rol
        cursor.execute("SELECT id FROM roles WHERE nombre_rol = %s", (rol_nombre,))
        rol_result = cursor.fetchone()
        
        if not rol_result:
            raise ValueError(f"Rol '{rol_nombre}' no encontrado en la base de datos")
        
        rol_id = rol_result[0]
        
        exitosos = 0
        fallidos = 0
        
        for usuario_id in usuarios_ids:
            try:
                # Actualizar el rol del usuario
                query = """
                    UPDATE usuarios 
                    SET rol_id = %s, activo = TRUE
                    WHERE id = %s
                """
                
                cursor.execute(query, (rol_id, usuario_id))
                
                if cursor.rowcount > 0:
                    exitosos += 1
                else:
                    fallidos += 1
                    
            except Exception as e:
                print(f"Error asignando rol a usuario {usuario_id}: {e}")
                fallidos += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {'exitosos': exitosos, 'fallidos': fallidos}
        
    except Exception as e:
        print(f"Error en asignar_rol_masivo: {e}")
        raise e

def buscar_usuario_por_nombre_correo(termino):
    """Busca un usuario por nombre o correo"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Buscar por nombre o correo (case insensitive)
        query = """
            SELECT u.id, u.nombre, u.correo, r.nombre_rol as rol_nombre, u.fecha_registro, u.activo
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE LOWER(u.nombre) LIKE LOWER(%s) OR LOWER(u.correo) LIKE LOWER(%s)
            ORDER BY u.nombre
            LIMIT 10
        """
        
        termino_busqueda = f"%{termino}%"
        cursor.execute(query, (termino_busqueda, termino_busqueda))
        resultados = cursor.fetchall()
        
        usuarios_encontrados = []
        for row in resultados:
            usuarios_encontrados.append({
                'id': row[0],
                'nombre': row[1],
                'email': row[2],  # Mapear correo a email
                'rol': row[3],
                'fecha_creacion': row[4],
                'activo': row[5] if row[5] is not None else True
            })
        
        cursor.close()
        conn.close()
        
        return usuarios_encontrados
        
    except Exception as e:
        print(f"Error en buscar_usuario_por_nombre_correo: {e}")
        raise e

@vistaroles.route('/api/asignar-masivo', methods=['POST'])
@login_required
@admin_required
def api_asignar_masivo():
    """API para asignación masiva de roles"""
    try:
        data = request.get_json()
        usuarios_ids = data.get('usuarios_ids', [])
        rol = data.get('rol')
        
        if not usuarios_ids or not rol:
            return jsonify({'success': False, 'message': 'Faltan parámetros'})
        
        resultado = asignar_rol_masivo(usuarios_ids, rol)
        
        mensaje = f"Se asignó el rol '{rol}' a {resultado['exitosos']} usuario(s)"
        if resultado['fallidos'] > 0:
            mensaje += f". {resultado['fallidos']} fallaron"
        
        return jsonify({
            'success': True, 
            'message': mensaje,
            'exitosos': resultado['exitosos'],
            'fallidos': resultado['fallidos']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def asignar_roles_aleatorios():
    """Asigna roles aleatorios (ESCRIBIENTE o SUSTANCIADOR) a todos los usuarios"""
    import random
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Obtener todos los usuarios activos
        cursor.execute("SELECT id FROM usuarios WHERE activo = TRUE")
        usuarios = cursor.fetchall()
        
        if not usuarios:
            return {'total': 0, 'escribientes': 0, 'sustanciadores': 0}
        
        # Obtener IDs de roles
        cursor.execute("SELECT id FROM roles WHERE nombre_rol = 'ESCRIBIENTE'")
        escribiente_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM roles WHERE nombre_rol = 'SUSTANCIADOR'")
        sustanciador_id = cursor.fetchone()[0]
        
        roles = [escribiente_id, sustanciador_id]
        contador_escribientes = 0
        contador_sustanciadores = 0
        
        # Asignar rol aleatorio a cada usuario
        for usuario in usuarios:
            usuario_id = usuario[0]
            rol_aleatorio = random.choice(roles)
            
            cursor.execute("""
                UPDATE usuarios 
                SET rol_id = %s 
                WHERE id = %s
            """, (rol_aleatorio, usuario_id))
            
            if rol_aleatorio == escribiente_id:
                contador_escribientes += 1
            else:
                contador_sustanciadores += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'total': len(usuarios),
            'escribientes': contador_escribientes,
            'sustanciadores': contador_sustanciadores
        }
        
    except Exception as e:
        print(f"Error en asignar_roles_aleatorios: {e}")
        raise e

def remover_todos_roles():
    """Remueve todos los roles asignados a los usuarios"""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Remover todos los roles (establecer rol_id a NULL)
        cursor.execute("""
            UPDATE usuarios 
            SET rol_id = NULL 
            WHERE rol_id IS NOT NULL
        """)
        
        usuarios_actualizados = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return usuarios_actualizados
        
    except Exception as e:
        print(f"Error en remover_todos_roles: {e}")
        raise e