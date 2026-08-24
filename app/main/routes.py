from io import BytesIO
from datetime import datetime, timedelta
import calendar
from flask import render_template, flash, redirect, url_for, request, abort, make_response
from xhtml2pdf import pisa
from flask_login import login_required, current_user
from sqlalchemy import func, or_, cast, Date 
from app import db
from app.main import bp
from app.main.forms import BitacoraForm, EditUserAdminForm, EditReportAdminForm
from app.models import Bitacora, User  


# --- RUTA PRINCIPAL (DASHBOARD) ---
@bp.route('/', methods=['GET'])
@bp.route('/index', methods=['GET'])
@login_required
def index():
    if current_user.rol == 'cliente':
        return redirect(url_for('main.cliente_dashboard'))
    
    if current_user.rol == 'admin':
        return redirect(url_for('main.admin_home'))

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
        return redirect(url_for('main.nueva_bitacora')) 

    return render_template('main/index.html', title='Nueva Bitácora', form=form)


# --- RUTA: VER MIS BITÁCORAS ---
@bp.route('/mis_bitacoras')
@login_required
def mis_bitacoras():
    if current_user.rol == 'cliente':
        return redirect(url_for('main.cliente_dashboard'))

    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')

    query = Bitacora.query.filter_by(user_id=current_user.id)
    reportes_base = query.all()

    if fecha_inicio or fecha_fin:
        reportes = filtrar_reportes_por_fecha(reportes_base, 'rango', fecha_inicio, fecha_fin, '')
    else:
        reportes = reportes_base

    def obtener_fecha_ordenamiento(reporte):
        if not reporte.periodo_semanal:
            return datetime.min.date()
        try:
            fecha_str = [d.strip() for d in reporte.periodo_semanal.split('|') if d.strip()][0]
            return datetime.strptime(fecha_str, '%d/%m/%Y').date()
        except (ValueError, IndexError):
            return datetime.min.date()

    reportes = sorted(reportes, key=obtener_fecha_ordenamiento, reverse=True)

    for r in reportes:
        r.periodo_visual = obtener_rango_semanal(r.periodo_semanal)

    return render_template('main/mis_bitacoras.html', 
                           title='Mis Bitácoras', 
                           reportes=reportes,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin)


# --- FUNCIÓN AUXILIAR PARA FILTRAR FECHAS ---
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


# --- RUTAS DE ADMINISTRACIÓN ---
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
            try:
                fechas_obj = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in dias_lista])
                dias_lista = [f.strftime('%d/%m/%Y') for f in fechas_obj]
                r.fecha_iso = fechas_obj[0].strftime('%Y-%m-%d')
            except ValueError:
                r.fecha_iso = "0000-00-00"

            r.dias_contados = len(dias_lista)
            r.fechas_especificas = ", ".join(dias_lista)
            
            if len(dias_lista) > 1:
                r.rango_periodo = f"{dias_lista[0]} - {dias_lista[-1]}"
            elif len(dias_lista) == 1:
                r.rango_periodo = dias_lista[0]
            else:
                r.rango_periodo = "-"
        else:
            r.dias_contados = 0
            r.fechas_especificas = "-"
            r.rango_periodo = "-"
            r.fecha_iso = "0000-00-00"

    def obtener_fecha_sort(rep):
        if not rep.periodo_semanal:
            return datetime.min.date()
        try:
            f_str = [d.strip() for d in rep.periodo_semanal.split('|') if d.strip()][0]
            return datetime.strptime(f_str, '%d/%m/%Y').date()
        except (ValueError, IndexError):
            return datetime.min.date()

    reportes = sorted(reportes, key=obtener_fecha_sort, reverse=False)

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


# --- GESTIÓN DE USUARIOS (CON BÚSQUEDA Y ESTATUS) ---
@bp.route('/admin/usuarios')
@login_required
def users_list():
    if current_user.rol != 'admin':
        abort(403)
        
    search_query = request.args.get('q', '')
    query = User.query

    if search_query:
        filtros = [
            User.nombre.ilike(f'%{search_query}%'),
            User.email.ilike(f'%{search_query}%'),
            User.empresa.ilike(f'%{search_query}%'),
            User.empresa_origen.ilike(f'%{search_query}%'),
            User.rol.ilike(f'%{search_query}%')
        ]
        
        q_lower = search_query.lower().strip()
        if 'no vigente' in q_lower or 'inactivo' in q_lower:
            filtros.append(User.activo == False)
        elif 'vigente' in q_lower or 'activo' in q_lower:
            filtros.append(User.activo == True)

        query = query.filter(or_(*filtros))

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
    return redirect(url_for('main.users_list'))


# --- HISTORIAL Y EXPORTACIÓN DE BITÁCORAS DE USUARIO INDIVIDUAL ---
@bp.route('/admin/usuario/<int:user_id>/bitacoras')
@login_required
def user_reports_admin(user_id):
    if current_user.rol != 'admin':
        abort(403)
        
    usuario = User.query.get_or_404(user_id)
    reportes = Bitacora.query.filter_by(user_id=user_id).order_by(Bitacora.timestamp.desc()).all()

    for r in reportes:
        if r.periodo_semanal:
            dias_lista = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
            try:
                fechas_obj = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in dias_lista])
                dias_lista = [f.strftime('%d/%m/%Y') for f in fechas_obj]
                r.fecha_iso = fechas_obj[0].strftime('%Y-%m-%d')
            except ValueError:
                r.fecha_iso = "0000-00-00"
            
            r.dias_contados = len(dias_lista)
            r.fechas_especificas = ", ".join(dias_lista)
            
            if len(dias_lista) > 1:
                r.rango_periodo = f"{dias_lista[0]} - {dias_lista[-1]}"
            elif len(dias_lista) == 1:
                r.rango_periodo = dias_lista[0]
            else:
                r.rango_periodo = "-"
        else:
            r.dias_contados = 0
            r.fechas_especificas = "-"
            r.rango_periodo = "-"
            r.fecha_iso = "0000-00-00"

    def obtener_fecha_sort(rep):
        if not rep.periodo_semanal:
            return datetime.min.date()
        try:
            f_str = [d.strip() for d in rep.periodo_semanal.split('|') if d.strip()][0]
            return datetime.strptime(f_str, '%d/%m/%Y').date()
        except (ValueError, IndexError):
            return datetime.min.date()

    reportes = sorted(reportes, key=obtener_fecha_sort, reverse=True)

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

    for r in reportes:
        if r.periodo_semanal:
            dias_lista = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
            r.dias_contados = len(dias_lista)
            r.fechas_especificas = ", ".join(dias_lista)
            
            if len(dias_lista) > 1:
                r.rango_periodo = f"{dias_lista[0]} - {dias_lista[-1]}"
            elif len(dias_lista) == 1:
                r.rango_periodo = dias_lista[0]
            else:
                r.rango_periodo = "-"
        else:
            r.dias_contados = 0
            r.fechas_especificas = "-"
            r.rango_periodo = "-"

    # Construir fecha y hora exacta de emisión en el encabezado
    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    hoy = datetime.now()
    fecha_hoy = f"{hoy.day} de {meses_es[hoy.month-1]} de {hoy.year} a las {hoy.strftime('%H:%M')} hrs"

    html = render_template('main/pdf_user_reports.html', 
                           usuario=usuario, 
                           reportes=reportes,
                           fecha_hoy=fecha_hoy)
    
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=result, encoding='utf-8')

    if pdf.err:
        flash('Hubo un error al generar el PDF.', 'danger')
        return redirect(url_for('main.user_reports_admin', user_id=user_id))

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    nombre_archivo = f"bitacoras_{usuario.nombre.replace(' ', '_').lower()}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
    
    return response


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


# --- EXPORTAR INFORME MENSUAL / GENERAL PDF ---
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

    reportes_base = query.order_by(Bitacora.timestamp.desc()).all()
    reportes = filtrar_reportes_por_fecha(reportes_base, tipo_filtro, fecha_inicio, fecha_fin, fechas_especificas)

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
        try:
            fechas_list = [d.strip() for d in fechas_especificas.split(',') if d.strip()]
            fechas_ordenadas = sorted(fechas_list, key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
            fechas_especificas_clean = ", ".join(fechas_ordenadas)
        except ValueError:
            fechas_especificas_clean = fechas_especificas

        headline_title = f"Informe de días específicos: {fechas_especificas_clean}"

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
            consultores_agrupados[usuario_id]['num_bitacoras'] += num_dias
            consultores_agrupados[usuario_id]['dias_asignados'] += num_dias
            consultores_agrupados[usuario_id]['fechas_especificas_list'].extend(dias_str)
        else:
            consultores_agrupados[usuario_id]['num_bitacoras'] += 1

    for cid, data in consultores_agrupados.items():
        if data['fechas_especificas_list']:
            try:
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
    fecha_hoy = f"{hoy.day} de {meses_es[hoy.month-1]} de {hoy.year} a las {hoy.strftime('%H:%M')} hrs"

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


# --- EXPORTAR TABLA DE BITÁCORAS PDF (HORIZONTAL) ---
# --- EXPORTAR TABLA DE BITÁCORAS PDF (HORIZONTAL) ---
@bp.route('/admin/exportar_tabla_pdf')
@login_required
def export_table_pdf():
    if current_user.rol != 'admin':
        abort(403)
    
    # 1. Obtener parámetros de búsqueda y filtros
    search_query = request.args.get('q', '')
    empresa_filter = request.args.get('empresa', '')
    status_filter = request.args.get('status', '')
    tipo_filtro = request.args.get('tipo_filtro', 'rango')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    fechas_especificas = request.args.get('fechas_especificas', '')

    # Leer parámetros de ordenamiento enviados desde la vista interactiva del Dashboard
    sort_col = request.args.get('sort_col', type=int)
    sort_dir = request.args.get('sort_dir', 'asc')

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

    # 2. Filtrar fechas reales
    reportes_base = query.order_by(Bitacora.timestamp.desc()).all()
    reportes = filtrar_reportes_por_fecha(reportes_base, tipo_filtro, fecha_inicio, fecha_fin, fechas_especificas)

    # 3. Formatear datos individuales para cada fila de la bitácora
    for r in reportes:
        if r.periodo_semanal:
            dias_lista = [d.strip() for d in r.periodo_semanal.split('|') if d.strip()]
            
            # Ordenar fechas internas del reporte cronológicamente
            try:
                fechas_obj = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in dias_lista])
                dias_lista = [f.strftime('%d/%m/%Y') for f in fechas_obj]
            except ValueError:
                pass
            
            r.dias_contados = len(dias_lista)
            r.fechas_especificas = ", ".join(dias_lista)
            
            # Formato de periodo limpio (sin 'Día' ni 'Semana del')
            if len(dias_lista) > 1:
                r.rango_periodo = f"{dias_lista[0]} - {dias_lista[-1]}"
            elif len(dias_lista) == 1:
                r.rango_periodo = dias_lista[0]
            else:
                r.rango_periodo = "-"
        else:
            r.dias_contados = 0
            r.fechas_especificas = "-"
            r.rango_periodo = "-"

    # 4. Sistema de ordenamiento idéntico al que está en pantalla
    if sort_col is not None:
        is_reverse = (sort_dir == 'desc')
        
        def obtener_llave_ordenamiento(rep):
            if sort_col in [0, 1]:  # Periodo o Fechas específicas
                if not rep.periodo_semanal:
                    return datetime.min.date()
                try:
                    f_str = [d.strip() for d in rep.periodo_semanal.split('|') if d.strip()][0]
                    return datetime.strptime(f_str, '%d/%m/%Y').date()
                except (ValueError, IndexError):
                    return datetime.min.date()
            elif sort_col == 2:
                return rep.nombre_completo.lower()
            elif sort_col == 3:
                return 1 if rep.autor.activo else 0
            elif sort_col == 4:
                return rep.empresa.lower()
            elif sort_col == 5:
                return rep.puesto.lower()
            elif sort_col == 6:
                return rep.dias_contados
            elif sort_col == 7:
                return rep.nombre_jefe_inmediato.lower()
            elif sort_col == 8:
                return rep.cargo_jefe_inmediato.lower()
            elif sort_col == 9:
                return rep.proyecto_actual.lower()
            elif sort_col == 10:
                return rep.status
            elif sort_col == 11:
                return rep.actividades
            elif sort_col == 12:
                return rep.herramientas_utilizadas or ''
            elif sort_col == 13:
                return rep.entregable_generado or ''
            elif sort_col == 14:
                return rep.medio_entregable or ''
            elif sort_col == 15:
                return rep.incidencias or ''
            return rep.timestamp

        reportes = sorted(reportes, key=obtener_llave_ordenamiento, reverse=is_reverse)
    else:
        # Ordenamiento ascendente cronológico por defecto
        def obtener_fecha_sort(rep):
            if not rep.periodo_semanal:
                return datetime.min.date()
            try:
                f_str = [d.strip() for d in rep.periodo_semanal.split('|') if d.strip()][0]
                return datetime.strptime(f_str, '%d/%m/%Y').date()
            except (ValueError, IndexError):
                return datetime.min.date()
        reportes = sorted(reportes, key=obtener_fecha_sort, reverse=False)

    # 5. Construir fecha, hora exacta y desglose de criterios para el encabezado ejecutivo
    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    hoy = datetime.now()
    fecha_hoy = f"{hoy.day} de {meses_es[hoy.month-1]} de {hoy.year} a las {hoy.strftime('%H:%M')} hrs"

    # Determinar si fue por rango, por días específicos o general
    if tipo_filtro == 'rango' and (fecha_inicio or fecha_fin):
        criterio_busqueda = "Por Rango de Fechas"
        if fecha_inicio and fecha_fin:
            f_ini = datetime.strptime(fecha_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
            f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
            detalle_periodo = f"Del {f_ini} al {f_fin}"
        elif fecha_inicio:
            f_ini = datetime.strptime(fecha_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
            detalle_periodo = f"A partir del {f_ini}"
        elif fecha_fin:
            f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
            detalle_periodo = f"Hasta el {f_fin}"
    elif tipo_filtro == 'especificas' and fechas_especificas:
        criterio_busqueda = "Por Días Específicos"
        try:
            fechas_list = [d.strip() for d in fechas_especificas.split(',') if d.strip()]
            fechas_ordenadas = sorted(fechas_list, key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
            detalle_periodo = ", ".join(fechas_ordenadas)
        except ValueError:
            detalle_periodo = fechas_especificas
    else:
        criterio_busqueda = "Periodo General"
        detalle_periodo = "Historial completo de actividades"

    empresa_filtro_texto = empresa_filter if empresa_filter else "Todas las empresas"

    # 6. Renderizar plantilla PDF pasando los nuevos datos del encabezado
    html = render_template('main/pdf_table.html', 
                           reportes=reportes,
                           fecha_hoy=fecha_hoy,
                           criterio_busqueda=criterio_busqueda,
                           detalle_periodo=detalle_periodo,
                           empresa_filtro_texto=empresa_filtro_texto,
                           total_registros=len(reportes))

    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=result, encoding='utf-8')

    if pdf.err:
        flash('Hubo un error al generar el PDF de la tabla.', 'danger')
        return redirect(url_for('main.admin_dashboard'))

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=vista_tabla_bitacoras.pdf'
    return response


# --- EDITAR FILA DE BITÁCORA COMO ADMIN ---
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


# --- EDITAR MI BITÁCORA (USUARIO) ---
@bp.route('/mis_bitacoras/<int:report_id>/editar', methods=['GET', 'POST'])
@login_required
def edit_my_report(report_id):
    reporte = Bitacora.query.get_or_404(report_id)
    
    if reporte.user_id != current_user.id:
        abort(403)
        
    form = BitacoraForm()
    
    if form.validate_on_submit():
        dia_nuevo = form.periodo_semanal.data.strip()
        
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
            return render_template('main/edit_my_report.html', title='Corregir Bitácora', form=form, reporte=reporte)
        
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
        
    return render_template('main/edit_my_report.html', title='Corregir Bitácora', form=form, reporte=reporte)