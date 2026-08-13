from io import BytesIO
from flask import render_template, flash, redirect, url_for, request, abort, make_response
from xhtml2pdf import pisa
from flask_login import login_required, current_user
from sqlalchemy import func, or_, cast, Date 
from app import db
from app.main import bp
from app.main.forms import BitacoraForm, EditUserAdminForm, EditReportAdminForm
from app.models import Bitacora, User  
from datetime import datetime, timedelta
import calendar

# --- RUTA PRINCIPAL (DASHBOARD) ---
@bp.route('/', methods=['GET'])
@bp.route('/index', methods=['GET'])
@login_required
def index():
    # Redirecciones según el rol
    if current_user.rol == 'cliente':
        return redirect(url_for('main.cliente_dashboard'))
    
    if current_user.rol == 'admin':
        return redirect(url_for('main.admin_home'))

    # Si es un usuario normal, ahora verá su pantalla de inicio
    return render_template('main/user_home.html', title='Inicio')


# --- NUEVA BITÁCORA FORMULARIO ---
@bp.route('/bitacora/nueva', methods=['GET', 'POST'])
@login_required
def nueva_bitacora():
    if current_user.rol == 'cliente':
        return redirect(url_for('main.cliente_dashboard'))

    form = BitacoraForm()

    if request.method == 'GET':
        form.nombre_completo.data = current_user.nombre
        form.empresa.data = current_user.empresa
        form.nombre_jefe_inmediato.data = current_user.jefe_directo
        form.puesto.data = current_user.puesto
        form.cargo_jefe_inmediato.data = current_user.cargo_jefe
        form.proyecto_actual.data = current_user.proyecto_actual

    if form.validate_on_submit():
        # VALIDACIÓN: EVITAR DÍAS REPETIDOS (DIARIO)
        dia_nuevo = form.periodo_semanal.data.strip()
        bitacoras_usuario = Bitacora.query.filter_by(user_id=current_user.id).all()
        
        dias_duplicados = False
        for reporte_previo in bitacoras_usuario:
            if reporte_previo.periodo_semanal:
                dias_viejos = [d.strip() for d in reporte_previo.periodo_semanal.split('|') if d.strip()]
                if dia_nuevo in dias_viejos:
                    dias_duplicados = True
                    break
        
        if dias_duplicados:
            flash(f'Ya tienes una actividad registrada con fecha: {dia_nuevo}. Selecciona otro día.', 'error')
            return render_template('main/index.html', title='Nueva Bitácora', form=form)
        
        reporte = Bitacora(
            nombre_completo=form.nombre_completo.data,
            empresa=current_user.empresa, 
            puesto=form.puesto.data,
            periodo_semanal=form.periodo_semanal.data,
            nombre_jefe_inmediato=form.nombre_jefe_inmediato.data,
            cargo_jefe_inmediato=form.cargo_jefe_inmediato.data,
            proyecto_actual=form.proyecto_actual.data,
            actividades=form.actividades.data,
            herramientas_utilizadas=form.herramientas_utilizadas.data,
            status=form.status.data,
            entregable_generado=form.entregable_generado.data,
            medio_entregable=form.medio_entregable.data,
            incidencias=form.incidencias.data,
            autor=current_user 
        )
        db.session.add(reporte)
        db.session.commit()
        flash('¡Tu reporte de bitácora ha sido guardado exitosamente!', 'guardado')
        # Redirigimos a la misma página para que SweetAlert2 dispare la alerta y luego redirija con JS
        return redirect(url_for('main.nueva_bitacora')) 

    return render_template('main/index.html', title='Nueva Bitácora', form=form)


# --- NUEVA RUTA: VER MIS BITÁCORAS ---
@bp.route('/mis_bitacoras')
@login_required
def mis_bitacoras():
    if current_user.rol == 'cliente':
        return redirect(url_for('main.cliente_dashboard'))

    # Traemos solo las bitácoras pertenecientes al usuario actual
    reportes = Bitacora.query.filter_by(user_id=current_user.id).order_by(Bitacora.timestamp.desc()).all()

    for r in reportes:
        r.periodo_visual = obtener_rango_semanal(r.periodo_semanal)

    return render_template('main/mis_bitacoras.html', title='Mis Bitácoras', reportes=reportes)


# --- FUNCIÓN AUXILIAR PARA FILTRAR FECHAS REALES DE ACTIVIDAD ---
def filtrar_reportes_por_fecha(reportes_base, tipo_filtro, fecha_inicio, fecha_fin, fechas_especificas):
    reportes_finales = []
    
    if tipo_filtro == 'rango' and (fecha_inicio or fecha_fin):
        inicio_dt = datetime.strptime(fecha_inicio.strip(), '%Y-%m-%d').date() if fecha_inicio else datetime.min.date()
        fin_dt = datetime.strptime(fecha_fin.strip(), '%Y-%m-%d').date() if fecha_fin else datetime.max.date()
        
        for r in reportes_base:
            if not r.periodo_semanal: continue
            try:
                fechas_str = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
                fechas_obj = [datetime.strptime(d, '%d/%m/%Y').date() for d in fechas_str]
                
                if any(inicio_dt <= f <= fin_dt for f in fechas_obj):
                    reportes_finales.append(r)
            except ValueError:
                pass
                
    elif tipo_filtro == 'especificas' and fechas_especificas:
        try:
            dias_buscar = [datetime.strptime(d.strip(), '%d/%m/%Y').date() for d in fechas_especificas.split(',') if d.strip()]
            for r in reportes_base:
                if not r.periodo_semanal: continue
                fechas_str = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
                fechas_obj = [datetime.strptime(d, '%d/%m/%Y').date() for d in fechas_str]
                
                if any(f in dias_buscar for f in fechas_obj):
                    reportes_finales.append(r)
        except ValueError:
            pass
    else:
        reportes_finales = reportes_base
        
    return reportes_finales


def obtener_nombre_mes(yyyy_mm):
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    año, mes = yyyy_mm.split('-')
    return f"{meses[int(mes)-1]} {año}"


@bp.route('/admin/inicio')
@login_required
def admin_home():
    if current_user.rol != 'admin':
        return redirect(url_for('main.index'))
    return render_template('main/admin_home.html', title='Inicio Admin')


@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.rol != 'admin':
        return redirect(url_for('main.index'))
    
    search_query = request.args.get('q', '')
    empresa_filter = request.args.get('empresa', '')
    status_filter = request.args.get('status', '')
    
    tipo_filtro = request.args.get('tipo_filtro', 'rango')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    fechas_especificas = request.args.get('fechas_especificas', '')

    query = Bitacora.query

    if search_query:
        query = query.filter(
            or_(
                Bitacora.nombre_completo.ilike(f'%{search_query}%'),
                Bitacora.proyecto_actual.ilike(f'%{search_query}%'),
                Bitacora.actividades.ilike(f'%{search_query}%'),
                Bitacora.nombre_jefe_inmediato.ilike(f'%{search_query}%'),
                Bitacora.cargo_jefe_inmediato.ilike(f'%{search_query}%'),
                Bitacora.empresa.ilike(f'%{search_query}%')
            )
        )
    if empresa_filter:
        query = query.filter(Bitacora.empresa == empresa_filter)
    if status_filter:
        query = query.filter(Bitacora.status == status_filter)

    reportes_base = query.order_by(Bitacora.timestamp.desc()).all()
    reportes = filtrar_reportes_por_fecha(reportes_base, tipo_filtro, fecha_inicio, fecha_fin, fechas_especificas)
    
    empresas = [e[0] for e in db.session.query(User.empresa).distinct().all() if e[0]]

    for r in reportes:
        if r.periodo_semanal:
            dias_lista = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
            r.dias_contados = len(dias_lista)
            r.fechas_especificas = ", ".join(dias_lista)
            
            if len(dias_lista) > 1:
                r.rango_periodo = f"Semana del {dias_lista[0][:5]} al {dias_lista[-1][:5]}"
            elif len(dias_lista) == 1:
                r.rango_periodo = f"Día {dias_lista[0]}"
            else:
                r.rango_periodo = "-"
        else:
            r.dias_contados = 0
            r.fechas_especificas = "-"
            r.rango_periodo = "-"

    return render_template('main/admin_dashboard.html', 
                           title='Panel Admin', 
                           reportes=reportes,
                           search_query=search_query,
                           empresa_filter=empresa_filter,
                           status_filter=status_filter,
                           tipo_filtro=tipo_filtro,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin,
                           fechas_especificas=fechas_especificas,
                           empresas=empresas)


def obtener_rango_semanal(cadena_fechas):
    if ' | ' in cadena_fechas:
        try:
            primera_fecha_str = cadena_fechas.split(' | ')[0]
            fecha_dt = datetime.strptime(primera_fecha_str, '%d/%m/%Y')
            lunes = fecha_dt - timedelta(days=fecha_dt.weekday())
            viernes = lunes + timedelta(days=4)
            return f"Lun {lunes.strftime('%d/%m')} - Vie {viernes.strftime('%d/%m')}"
        except:
            return cadena_fechas
    else:
        return cadena_fechas
    

@bp.route('/cliente/dashboard')
@login_required
def cliente_dashboard():
    if current_user.rol != 'cliente':
        flash('No tienes permiso para estar aquí.')
        return redirect(url_for('main.index'))

    target = current_user.empresa.strip().lower()

    reportes = Bitacora.query.join(User).filter(
        or_(
            func.lower(func.trim(Bitacora.empresa)) == target,
            func.lower(func.trim(User.empresa)) == target
        )
    ).order_by(Bitacora.timestamp.desc()).all()

    for reporte in reportes:
        reporte.periodo_visual = obtener_rango_semanal(reporte.periodo_semanal)

    return render_template('main/cliente_dashboard.html', 
                           title='Panel Cliente', 
                           reportes=reportes)


@bp.route('/admin/usuarios')
@login_required
def users_list():
    if current_user.rol != 'admin':
        abort(403)
        
    search_query = request.args.get('q', '')
    query = User.query

    if search_query:
        # 1. Filtros estándar de texto
        filtros = [
            User.nombre.ilike(f'%{search_query}%'),
            User.email.ilike(f'%{search_query}%'),
            User.empresa.ilike(f'%{search_query}%'),
            User.empresa_origen.ilike(f'%{search_query}%'),
            User.rol.ilike(f'%{search_query}%')
        ]
        
        # 2. Filtro inteligente para el Estatus (Booleano)
        q_lower = search_query.lower().strip()
        
        # Si escribe "no vigente" o "inactivo", filtramos por activo = False
        if 'no vigente' in q_lower or 'inactivo' in q_lower:
            filtros.append(User.activo == False)
            
        # Si escribe "vigente" o "activo", filtramos por activo = True
        elif 'vigente' in q_lower or 'activo' in q_lower:
            filtros.append(User.activo == True)

        # 3. Aplicamos todos los filtros usando desempaquetado de listas (*filtros)
        query = query.filter(or_(*filtros))

    # Ordenar y obtener resultados
    usuarios = query.order_by(User.nombre).all()
    
    return render_template('main/users_list.html', 
                           title='Gestión de Usuarios', 
                           usuarios=usuarios, 
                           search_query=search_query)


@bp.route('/admin/usuario/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.rol != 'admin':
        abort(403)
        
    user = User.query.get_or_404(user_id)
    form = EditUserAdminForm()

    if form.validate_on_submit():
        user.nombre = form.nombre.data
        user.email = form.email.data
        user.telefono = form.telefono.data 
        user.empresa = form.empresa.data
        user.empresa_origen = form.empresa_origen.data
        user.puesto = form.puesto.data
        user.jefe_directo = form.jefe_directo.data
        user.rol = form.rol.data
        user.activo = (form.status.data == '1')
        
        if form.password.data:
            user.set_password(form.password.data)
            
        for reporte in user.bitacoras:
            reporte.nombre_completo = form.nombre.data
            reporte.empresa = form.empresa.data
            reporte.puesto = form.puesto.data
            reporte.nombre_jefe_inmediato = form.jefe_directo.data
            
        db.session.commit()
        flash(f'Usuario {user.nombre} actualizado correctamente.', 'success')
        return redirect(url_for('main.users_list'))

    elif request.method == 'GET':
        form.nombre.data = user.nombre
        form.email.data = user.email
        form.telefono.data = user.telefono
        form.empresa.data = user.empresa
        form.empresa_origen.data = user.empresa_origen
        form.puesto.data = user.puesto
        form.jefe_directo.data = user.jefe_directo
        form.rol.data = user.rol
        form.status.data = '1' if user.activo else '0'

    return render_template('main/edit_user.html', title='Editar Usuario', form=form, user=user)


@bp.route('/admin/usuario/<int:user_id>/eliminar', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.rol != 'admin':
        abort(403)
        
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('main.admin_dashboard'))

    db.session.delete(user)
    db.session.commit()
    flash(f'El usuario {user.nombre} y TODOS sus reportes han sido eliminados.', 'success')
    return redirect(url_for('main.admin_dashboard'))


@bp.route('/admin/bitacora/<int:report_id>/eliminar', methods=['POST'])
@login_required
def delete_report(report_id):
    if current_user.rol != 'admin':
        abort(403)
        
    reporte = Bitacora.query.get_or_404(report_id)
    db.session.delete(reporte)
    db.session.commit()
    flash('El reporte de bitácora ha sido eliminado.', 'success')
    return redirect(url_for('main.admin_dashboard'))


@bp.route('/admin/exportar_pdf')
@login_required
def export_pdf():
    if current_user.rol != 'admin':
        abort(403)
    
    search_query = request.args.get('q', '')
    empresa_filter = request.args.get('empresa', '')
    status_filter = request.args.get('status', '')
    tipo_filtro = request.args.get('tipo_filtro', 'rango')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    fechas_especificas = request.args.get('fechas_especificas', '')
    
    # El responsable ahora es automáticamente el administrador logueado
    responsable = current_user.nombre

    if not empresa_filter:
        flash('Debe seleccionar una empresa cliente específica para generar el informe.', 'warning')
        return redirect(url_for('main.admin_dashboard'))

    query = Bitacora.query

    if search_query:
        query = query.filter(
            or_(
                Bitacora.nombre_completo.ilike(f'%{search_query}%'),
                Bitacora.proyecto_actual.ilike(f'%{search_query}%'),
                Bitacora.actividades.ilike(f'%{search_query}%'),
                Bitacora.nombre_jefe_inmediato.ilike(f'%{search_query}%'),
                Bitacora.cargo_jefe_inmediato.ilike(f'%{search_query}%'),
                Bitacora.empresa.ilike(f'%{search_query}%')
            )
        )
        
    query = query.filter(Bitacora.empresa == empresa_filter)

    if status_filter:
        query = query.filter(Bitacora.status == status_filter)

    # Filtrar fechas reales
    reportes_base = query.order_by(Bitacora.timestamp.desc()).all()
    reportes = filtrar_reportes_por_fecha(reportes_base, tipo_filtro, fecha_inicio, fecha_fin, fechas_especificas)

    # 1. Determinar Título del PDF para el encabezado
    headline_title = "Informe General"
    if tipo_filtro == 'rango' and (fecha_inicio or fecha_fin):
        if fecha_inicio and fecha_fin:
            f_ini = datetime.strptime(fecha_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
            f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
            headline_title = f"Informe del {f_ini} al {f_fin}"
        elif fecha_inicio:
            f_ini = datetime.strptime(fecha_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
            headline_title = f"Informe a partir del {f_ini}"
        elif fecha_fin:
            f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
            headline_title = f"Informe hasta el {f_fin}"
    elif tipo_filtro == 'especificas' and fechas_especificas:
        headline_title = f"Informe de días específicos: {fechas_especificas}"

    # 2. Agrupar consultores y recopilar sus fechas específicas
    consultores_agrupados = {}
    empresa_origen_general = "" 
    
    for r in reportes:
        usuario_id = r.autor.id
        if not empresa_origen_general and r.autor.empresa_origen:
            empresa_origen_general = r.autor.empresa_origen

        if usuario_id not in consultores_agrupados:
            consultores_agrupados[usuario_id] = {
                'nombre': r.nombre_completo,
                'puesto': r.puesto,
                'jefe': r.nombre_jefe_inmediato,
                'num_bitacoras': 0,
                'dias_asignados': 0,
                'fechas_especificas_list': []
            }
        
        if r.periodo_semanal:
            dias_str = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
            num_dias = len(dias_str)
            
            # Ajuste clave: Sumamos el número de días reales a las bitácoras registradas
            consultores_agrupados[usuario_id]['num_bitacoras'] += num_dias
            consultores_agrupados[usuario_id]['dias_asignados'] += num_dias
            consultores_agrupados[usuario_id]['fechas_especificas_list'].extend(dias_str)
        else:
            # Fallback de respaldo por si no tiene fechas ingresadas
            consultores_agrupados[usuario_id]['num_bitacoras'] += 1

    # Dar formato ordenado a las fechas específicas de cada consultor
    for cid, data in consultores_agrupados.items():
        if data['fechas_especificas_list']:
            try:
                # Ordenar fechas reales de forma cronológica
                fechas_unicas = sorted(list(set(data['fechas_especificas_list'])), key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
                data['fechas_especificas'] = ", ".join(fechas_unicas)
            except ValueError:
                data['fechas_especificas'] = ", ".join(sorted(list(set(data['fechas_especificas_list']))))
        else:
            data['fechas_especificas'] = "-"

    # Dar formato ordenado a las fechas específicas de cada consultor
    for cid, data in consultores_agrupados.items():
        if data['fechas_especificas_list']:
            try:
                # Ordenar fechas reales de forma cronológica
                fechas_unicas = sorted(list(set(data['fechas_especificas_list'])), key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
                data['fechas_especificas'] = ", ".join(fechas_unicas)
            except ValueError:
                data['fechas_especificas'] = ", ".join(sorted(list(set(data['fechas_especificas_list']))))
        else:
            data['fechas_especificas'] = "-"

    if not empresa_origen_general:
        empresa_origen_general = "Krolls"

    lista_consultores = list(consultores_agrupados.values())
    total_consultores = len(lista_consultores)

    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    hoy = datetime.now()
    fecha_hoy = f"{hoy.day} de {meses_es[hoy.month-1]} de {hoy.year}"

    # 3. Determinar nombre dinámico para la descarga del archivo PDF
    hoy_str = hoy.strftime('%d-%m-%Y')
    if tipo_filtro == 'rango':
        ini_str = datetime.strptime(fecha_inicio.strip(), '%Y-%m-%d').strftime('%d-%m-%Y') if fecha_inicio else "inicio"
        fin_str = datetime.strptime(fecha_fin.strip(), '%Y-%m-%d').strftime('%d-%m-%Y') if fecha_fin else "fin"
        filename = f"Informe_mensual[{ini_str}][{fin_str}].pdf"
    else:
        filename = f"informemensualpordiasespecificos_{hoy_str}.pdf"

    html = render_template('main/pdf_report.html', 
                           lista_consultores=lista_consultores,
                           total_consultores=total_consultores,
                           fecha_hoy=fecha_hoy,
                           headline_title=headline_title,
                           empresa_cliente=empresa_filter, 
                           empresa_origen=empresa_origen_general, 
                           responsable=responsable)

    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=result, encoding='utf-8')

    if pdf.err:
        flash('Hubo un error al generar el PDF.', 'danger')
        return redirect(url_for('main.admin_dashboard'))

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


@bp.route('/admin/exportar_tabla_pdf')
@login_required
def export_table_pdf():
    if current_user.rol != 'admin':
        abort(403)
    
    search_query = request.args.get('q', '')
    empresa_filter = request.args.get('empresa', '')
    status_filter = request.args.get('status', '')
    tipo_filtro = request.args.get('tipo_filtro', 'rango')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    fechas_especificas = request.args.get('fechas_especificas', '')

    query = Bitacora.query

    if search_query:
        query = query.filter(
            or_(
                Bitacora.nombre_completo.ilike(f'%{search_query}%'),
                Bitacora.proyecto_actual.ilike(f'%{search_query}%'),
                Bitacora.actividades.ilike(f'%{search_query}%'),
                Bitacora.nombre_jefe_inmediato.ilike(f'%{search_query}%'),
                Bitacora.cargo_jefe_inmediato.ilike(f'%{search_query}%'),
                Bitacora.empresa.ilike(f'%{search_query}%')
            )
        )
    if empresa_filter:
        query = query.filter(Bitacora.empresa == empresa_filter)
    if status_filter:
        query = query.filter(Bitacora.status == status_filter)

    # Filtrar fechas reales
    reportes_base = query.order_by(Bitacora.timestamp.desc()).all()
    reportes = filtrar_reportes_por_fecha(reportes_base, tipo_filtro, fecha_inicio, fecha_fin, fechas_especificas)

    for r in reportes:
        if r.periodo_semanal:
            dias_lista = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
            r.dias_contados = len(dias_lista)
            r.fechas_especificas = ", ".join(dias_lista)
            
            if len(dias_lista) > 1:
                r.rango_periodo = f"Semana del {dias_lista[0][:5]} al {dias_lista[-1][:5]}"
            elif len(dias_lista) == 1:
                r.rango_periodo = f"Día {dias_lista[0]}"
            else:
                r.rango_periodo = "-"
        else:
            r.dias_contados = 0
            r.fechas_especificas = "-"
            r.rango_periodo = "-"

    html = render_template('main/pdf_table.html', reportes=reportes)
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=result, encoding='utf-8')

    if pdf.err:
        flash('Hubo un error al generar el PDF de la tabla.', 'danger')
        return redirect(url_for('main.admin_dashboard'))

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=vista_tabla_bitacoras.pdf'
    return response


@bp.route('/admin/bitacora/<int:report_id>/editar', methods=['GET', 'POST'])
@login_required
def edit_report(report_id):
    if current_user.rol != 'admin':
        abort(403)
        
    reporte = Bitacora.query.get_or_404(report_id)
    form = EditReportAdminForm()

    if form.validate_on_submit():
        reporte.nombre_completo = form.nombre_completo.data
        reporte.empresa = form.empresa.data
        reporte.puesto = form.puesto.data
        reporte.nombre_jefe_inmediato = form.nombre_jefe_inmediato.data
        reporte.cargo_jefe_inmediato = form.cargo_jefe_inmediato.data
        reporte.periodo_semanal = form.periodo_semanal.data
        reporte.proyecto_actual = form.proyecto_actual.data
        reporte.actividades = form.actividades.data
        reporte.herramientas_utilizadas = form.herramientas_utilizadas.data
        reporte.status = form.status.data
        reporte.entregable_generado = form.entregable_generado.data
        reporte.medio_entregable = form.medio_entregable.data
        reporte.incidencias = form.incidencias.data
        
        db.session.commit()
        flash('La fila de la bitácora ha sido corregida y actualizada exitosamente.', 'success')
        return redirect(url_for('main.admin_dashboard'))

    elif request.method == 'GET':
        form.nombre_completo.data = reporte.nombre_completo
        form.empresa.data = reporte.empresa
        form.puesto.data = reporte.puesto
        form.nombre_jefe_inmediato.data = reporte.nombre_jefe_inmediato
        form.cargo_jefe_inmediato.data = reporte.cargo_jefe_inmediato
        form.periodo_semanal.data = reporte.periodo_semanal
        form.proyecto_actual.data = reporte.proyecto_actual
        form.actividades.data = reporte.actividades
        form.herramientas_utilizadas.data = reporte.herramientas_utilizadas
        form.status.data = reporte.status
        form.entregable_generado.data = reporte.entregable_generado
        form.medio_entregable.data = reporte.medio_entregable
        form.incidencias.data = reporte.incidencias

    return render_template('main/edit_report.html', title='Editar Fila', form=form, reporte=reporte)

@bp.route('/mis_bitacoras/<int:report_id>/editar', methods=['GET', 'POST'])
@login_required
def edit_my_report(report_id):
    reporte = Bitacora.query.get_or_404(report_id)
    
    # Seguridad: Asegurar que el reporte le pertenece de verdad al usuario logueado
    if reporte.user_id != current_user.id:
        abort(403)
        
    form = BitacoraForm()
    
    if form.validate_on_submit():
        # --- NUEVA VALIDACIÓN: EVITAR DÍAS REPETIDOS (DIARIO) EN EDICIÓN ---
        dia_nuevo = form.periodo_semanal.data.strip()
        
        # Consultamos las bitácoras del usuario EXCLUYENDO el reporte actual que se está editando
        bitacoras_usuario = Bitacora.query.filter(
            Bitacora.user_id == current_user.id,
            Bitacora.id != report_id
        ).all()
        
        dias_duplicados = False
        for reporte_previo in bitacoras_usuario:
            if reporte_previo.periodo_semanal:
                dias_viejos = [d.strip() for d in reporte_previo.periodo_semanal.split('|') if d.strip()]
                if dia_nuevo in dias_viejos:
                    dias_duplicados = True
                    break
        
        if dias_duplicados:
            flash(f'Ya tienes una actividad registrada con fecha: {dia_nuevo}. Selecciona otro día.', 'error')
            # Si hay error, volvemos a renderizar el formulario con los datos para que no los pierda
            return render_template('main/edit_my_report.html', title='Corregir Bitácora', form=form, reporte=reporte)
        # --- FIN DE LA VALIDACIÓN ---
        
        # Actualizamos únicamente los campos permitidos según requerimientos del PDF
        reporte.periodo_semanal = form.periodo_semanal.data
        reporte.proyecto_actual = form.proyecto_actual.data
        reporte.actividades = form.actividades.data
        reporte.herramientas_utilizadas = form.herramientas_utilizadas.data
        reporte.status = form.status.data
        reporte.entregable_generado = form.entregable_generado.data
        reporte.medio_entregable = form.medio_entregable.data
        reporte.incidencias = form.incidencias.data
        
        db.session.commit()
        flash('La bitácora ha sido corregida y actualizada exitosamente.', 'editado')
        return redirect(url_for('main.edit_my_report', report_id=reporte.id))
        
    elif request.method == 'GET':
        # Llenamos el formulario con los datos existentes
        form.nombre_completo.data = reporte.nombre_completo
        form.empresa.data = reporte.empresa
        form.puesto.data = reporte.puesto
        form.periodo_semanal.data = reporte.periodo_semanal
        form.nombre_jefe_inmediato.data = reporte.nombre_jefe_inmediato
        form.cargo_jefe_inmediato.data = reporte.cargo_jefe_inmediato
        form.proyecto_actual.data = reporte.proyecto_actual
        form.actividades.data = reporte.actividades
        form.herramientas_utilizadas.data = reporte.herramientas_utilizadas
        form.status.data = reporte.status
        form.entregable_generado.data = reporte.entregable_generado
        form.medio_entregable.data = reporte.medio_entregable
        form.incidencias.data = reporte.incidencias
        
    if request.method == 'POST' and not form.validate_on_submit():
        print("❌ Errores de validación al editar:", form.errors)
        
    return render_template('main/edit_my_report.html', title='Corregir Bitácora', form=form, reporte=reporte)

@bp.route('/admin/usuario/<int:user_id>/bitacoras')
@login_required
def user_reports_admin(user_id):
    if current_user.rol != 'admin':
        abort(403)
        
    usuario = User.query.get_or_404(user_id)
    
    # Traemos únicamente las bitácoras de este usuario específico
    reportes = Bitacora.query.filter_by(user_id=user_id).order_by(Bitacora.timestamp.desc()).all()

    # Procesamiento idéntico de periodos que en admin_dashboard
    for r in reportes:
        if r.periodo_semanal:
            dias_lista = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
            r.dias_contados = len(dias_lista)
            r.fechas_especificas = ", ".join(dias_lista)
            
            if len(dias_lista) > 1:
                r.rango_periodo = f"Semana del {dias_lista[0][:5]} al {dias_lista[-1][:5]}"
            elif len(dias_lista) == 1:
                r.rango_periodo = f"Día {dias_lista[0]}"
            else:
                r.rango_periodo = "-"
        else:
            r.dias_contados = 0
            r.fechas_especificas = "-"
            r.rango_periodo = "-"

    return render_template('main/user_reports_admin.html', 
                           title=f'Bitácoras de {usuario.nombre}', 
                           usuario=usuario, 
                           reportes=reportes)

@bp.route('/admin/usuario/<int:user_id>/exportar_pdf')
@login_required
def user_reports_pdf(user_id):
    if current_user.rol != 'admin':
        abort(403)
        
    usuario = User.query.get_or_404(user_id)
    reportes = Bitacora.query.filter_by(user_id=user_id).order_by(Bitacora.timestamp.desc()).all()

    # Procesar periodos y fechas tal como se muestra en pantalla
    for r in reportes:
        if r.periodo_semanal:
            dias_lista = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
            r.dias_contados = len(dias_lista)
            r.fechas_especificas = ", ".join(dias_lista)
            
            if len(dias_lista) > 1:
                r.rango_periodo = f"Semana del {dias_lista[0][:5]} al {dias_lista[-1][:5]}"
            elif len(dias_lista) == 1:
                r.rango_periodo = f"Día {dias_lista[0]}"
            else:
                r.rango_periodo = "-"
        else:
            r.dias_contados = 0
            r.fechas_especificas = "-"
            r.rango_periodo = "-"

    # Renderizar plantilla diseñada para PDF
    html = render_template('main/pdf_user_reports.html', 
                           usuario=usuario, 
                           reportes=reportes)
    
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=result, encoding='utf-8')

    if pdf.err:
        flash('Hubo un error al generar el PDF.', 'danger')
        return redirect(url_for('main.user_reports_admin', user_id=user_id))

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    # Genera un nombre de archivo dinámico basado en el nombre del usuario
    nombre_archivo = f"bitacoras_{usuario.nombre.replace(' ', '_').lower()}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
    
    return response