# Fíjate bien en esta primera línea, agregamos 'request' y 'abort'
from io import BytesIO
from flask import render_template, flash, redirect, url_for, request, abort, make_response
from xhtml2pdf import pisa
from flask_login import login_required, current_user
from sqlalchemy import func,or_ 
from app import db
from app.main import bp
from app.main.forms import BitacoraForm, EditUserAdminForm
from app.models import Bitacora, User  
from datetime import datetime, timedelta
import calendar

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = BitacoraForm()
    if current_user.rol == 'cliente':
        return redirect(url_for('main.cliente_dashboard'))

    # Este era el punto del error: ahora 'request' ya está importado
    if request.method == 'GET':
        form.nombre_completo.data = current_user.nombre
        form.empresa.data = current_user.empresa
        form.nombre_jefe_inmediato.data = current_user.jefe_directo
        form.puesto.data = current_user.puesto
        form.cargo_jefe_inmediato.data = current_user.cargo_jefe
        form.proyecto_actual.data = current_user.proyecto_actual

    if form.validate_on_submit():
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
        flash('¡Tu reporte de bitácora ha sido guardado exitosamente!')
        return redirect(url_for('main.index'))

    return render_template('main/index.html', title='Nueva Bitácora', form=form)


def obtener_nombre_mes(yyyy_mm):
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    año, mes = yyyy_mm.split('-')
    return f"{meses[int(mes)-1]} {año}"


# Ruta para el Administrador
@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.rol != 'admin':
        return redirect(url_for('main.index'))
    
    # 1. Capturar parámetros de la URL (AÑADIMOS EL MES)
    search_query = request.args.get('q', '')
    empresa_filter = request.args.get('empresa', '')
    status_filter = request.args.get('status', '')
    mes_filter = request.args.get('mes', '')

    query = Bitacora.query

    # Filtros existentes...
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

    # 2. NUEVO FILTRO DE MES
    if mes_filter:
        año, mes = map(int, mes_filter.split('-'))
        # Obtenemos el último día del mes seleccionado (ej. 28, 29, 30 o 31)
        ultimo_dia = calendar.monthrange(año, mes)[1]
        
        # Filtramos desde el día 1 a las 00:00:00 hasta el último día a las 23:59:59
        fecha_inicio = datetime(año, mes, 1)
        fecha_fin = datetime(año, mes, ultimo_dia, 23, 59, 59)
        
        query = query.filter(Bitacora.timestamp >= fecha_inicio, Bitacora.timestamp <= fecha_fin)

    # Ejecutar consulta final
    reportes = query.order_by(Bitacora.timestamp.desc()).all()

    # 3. GENERAR OPCIONES PARA LOS SELECTS
    empresas = [e[0] for e in db.session.query(User.empresa).distinct().all() if e[0]]
    
    # Extraer los meses únicos que existen en la base de datos (Formato: YYYY-MM)
    fechas_db = db.session.query(Bitacora.timestamp).all()
    meses_set = {f[0].strftime('%Y-%m') for f in fechas_db if f[0]}
    
    # Ordenar de más reciente a más antiguo y darles un nombre legible
    meses_lista = sorted(list(meses_set), reverse=True)
    meses_opciones = [(m, obtener_nombre_mes(m)) for m in meses_lista]

    return render_template('main/admin_dashboard.html', 
                           title='Panel Admin', 
                           reportes=reportes,
                           search_query=search_query,
                           empresa_filter=empresa_filter,
                           status_filter=status_filter,
                           mes_filter=mes_filter,
                           empresas=empresas,
                           meses_opciones=meses_opciones)

def obtener_rango_semanal(cadena_fechas):
    """
    Toma una cadena de fechas "DD/MM/YYYY | ..." y devuelve "Lun DD/MM - Vie DD/MM"
    """
    try:
        # Tomamos la primera fecha de la lista
        primera_fecha_str = cadena_fechas.split(' | ')[0]
        fecha_dt = datetime.strptime(primera_fecha_str, '%d/%m/%Y')
        
        # Encontramos el lunes (weekday 0)
        lunes = fecha_dt - timedelta(days=fecha_dt.weekday())
        # Encontramos el viernes (lunes + 4 días)
        viernes = lunes + timedelta(days=4)
        
        return f"Lun {lunes.strftime('%d/%m')} - Vie {viernes.strftime('%d/%m')}"
    except:
        return cadena_fechas # Si falla, devuelve el original
    
@bp.route('/cliente/dashboard')
@login_required
def cliente_dashboard():
    if current_user.rol != 'cliente':
        flash('No tienes permiso para estar aquí.')
        return redirect(url_for('main.index'))

    # 1. Normalizamos el nombre de la empresa del cliente
    # Quitamos espacios y pasamos a minúsculas: "Empresa C" -> "empresa c"
    target = current_user.empresa.strip().lower()

    # 2. Hacemos la consulta ultra-flexible
    # Buscamos reportes donde:
    # (La empresa del reporte sea igual a la del cliente) O (La empresa del autor sea igual a la del cliente)
    reportes = Bitacora.query.join(User).filter(
        or_(
            func.lower(func.trim(Bitacora.empresa)) == target,
            func.lower(func.trim(User.empresa)) == target
        )
    ).order_by(Bitacora.timestamp.desc()).all()

    # DEBUG PARA CONSOLA: Para que veas exactamente qué encontró Flask
    print(f"--- DEBUG CLIENTE ---")
    print(f"Buscando empresa: '{target}'")
    print(f"Resultados encontrados: {len(reportes)}")
    for r in reportes:
        print(f"ID: {r.id} | En reporte: '{r.empresa}' | En autor: '{r.autor.empresa}'")

    # 3. Procesar las fechas para el cliente
    for reporte in reportes:
        reporte.periodo_visual = obtener_rango_semanal(reporte.periodo_semanal)

    return render_template('main/cliente_dashboard.html', 
                           title='Panel Cliente', 
                           reportes=reportes)

@bp.route('/admin/usuario/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.rol != 'admin':
        abort(403)
        
    user = User.query.get_or_404(user_id)
    form = EditUserAdminForm()

    if form.validate_on_submit():
        # 1. Actualizamos los datos del Perfil del Usuario
        user.nombre = form.nombre.data
        user.email = form.email.data
        user.telefono = form.telefono.data 
        user.empresa = form.empresa.data
        user.empresa_origen = form.empresa_origen.data
        user.puesto = form.puesto.data
        user.activo = (form.status.data == '1')
        
        # 2. NUEVO: Actualizamos TODOS los reportes anteriores de este usuario
        # para que el dashboard muestre la información corregida inmediatamente.
        for reporte in user.bitacoras:
            reporte.nombre_completo = form.nombre.data
            reporte.empresa = form.empresa.data
            reporte.puesto = form.puesto.data
            
        # Guardamos todo en la base de datos
        db.session.commit()
        
        flash(f'Datos de {user.nombre} y todos sus reportes fueron actualizados correctamente.', 'success')
        return redirect(url_for('main.admin_dashboard'))

    elif request.method == 'GET':
        # Pre-llenar el formulario con los datos actuales
        form.nombre.data = user.nombre
        form.email.data = user.email
        form.telefono.data = user.telefono
        form.empresa.data = user.empresa
        form.empresa_origen.data = user.empresa_origen
        form.puesto.data = user.puesto
        form.status.data = '1' if user.activo else '0'

    return render_template('main/edit_user.html', title='Editar Usuario', form=form, user=user)


@bp.route('/admin/usuario/<int:user_id>/eliminar', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.rol != 'admin':
        abort(403)
        
    user = User.query.get_or_404(user_id)
    
    # Evitar que el admin se borre a sí mismo
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

    # --- RUTA PARA EXPORTAR PDF ---
@bp.route('/admin/exportar_pdf')
@login_required
def export_pdf():
    if current_user.rol != 'admin':
        abort(403)
    
    search_query = request.args.get('q', '')
    empresa_filter = request.args.get('empresa', '')
    status_filter = request.args.get('status', '')
    mes_filter = request.args.get('mes', '')
    responsable = request.args.get('responsable', '___________________________')

    # --- NUEVA VALIDACIÓN DE SEGURIDAD ---
    # Si alguien intenta forzar la URL sin empresa, lo regresamos
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
    # Como ya validamos que empresa_filter existe, este filtro siempre se aplicará
    query = query.filter(Bitacora.empresa == empresa_filter)
    
    if status_filter:
        query = query.filter(Bitacora.status == status_filter)
        
    if mes_filter:
        año, mes = map(int, mes_filter.split('-'))
        ultimo_dia = calendar.monthrange(año, mes)[1]
        fecha_inicio = datetime(año, mes, 1)
        fecha_fin = datetime(año, mes, ultimo_dia, 23, 59, 59)
        query = query.filter(Bitacora.timestamp >= fecha_inicio, Bitacora.timestamp <= fecha_fin)

    reportes = query.order_by(Bitacora.timestamp.desc()).all()

    # --- LÓGICA DE AGRUPACIÓN ---
    consultores_agrupados = {}
    empresa_origen_general = "" # Iniciamos totalmente en blanco
    
    for r in reportes:
        usuario_id = r.autor.id
        
        # 1. Extraemos EXACTAMENTE la empresa origen (Krolls o PROGREDI) del usuario
        if not empresa_origen_general and r.autor.empresa_origen:
            empresa_origen_general = r.autor.empresa_origen

        # 2. Agrupamos los datos del consultor
        if usuario_id not in consultores_agrupados:
            consultores_agrupados[usuario_id] = {
                'nombre': r.nombre_completo,
                'puesto': r.puesto,
                'jefe': r.nombre_jefe_inmediato,
                'num_bitacoras': 0,
                'dias_asignados': 0
            }
                
        # Sumamos 1 bitácora
        consultores_agrupados[usuario_id]['num_bitacoras'] += 1
        
        # Sumamos los días laborados
        if r.periodo_semanal:
            dias = len([d for d in r.periodo_semanal.split('|') if d.strip()])
            consultores_agrupados[usuario_id]['dias_asignados'] += dias

    # Si el reporte lo hizo un usuario muy antiguo o el admin que no tenía este dato,
    # forzamos a que diga "Krolls International" para no romper el formato formal.
    if not empresa_origen_general:
        empresa_origen_general = "Krolls"

    lista_consultores = list(consultores_agrupados.values())
    total_consultores = len(lista_consultores)

    # --- GENERACIÓN DE TEXTOS DINÁMICOS ---
    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    hoy = datetime.now()
    fecha_hoy = f"{hoy.day} de {meses_es[hoy.month-1]} de {hoy.year}"
    
    if mes_filter:
        año, mes = mes_filter.split('-')
        informe_mes = f"{meses_es[int(mes)-1].upper()} {año}"
    else:
        informe_mes = f"PERIODO GENERAL"

    # 2. Renderizar el HTML
    html = render_template('main/pdf_report.html', 
                           lista_consultores=lista_consultores,
                           total_consultores=total_consultores,
                           fecha_hoy=fecha_hoy,
                           informe_mes=informe_mes,
                           empresa_cliente=empresa_filter, # Usamos directamente el filtro obligatorio
                           empresa_origen=empresa_origen_general, # Extraído del perfil del usuario
                           responsable=responsable)

    # 3. Convertir a PDF
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=result, encoding='utf-8')

    if pdf.err:
        flash('Hubo un error al generar el PDF.', 'danger')
        return redirect(url_for('main.admin_dashboard'))

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=informe_mensual.pdf'
    
    return response