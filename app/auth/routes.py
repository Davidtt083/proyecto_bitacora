from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User

@bp.route('/register', methods=['GET', 'POST'])
def register():
   # if current_user.is_authenticated:
     #   return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            nombre=form.nombre.data, 
            email=form.email.data,
            telefono=form.telefono.data,
            empresa=form.empresa.data,
            jefe_directo=form.jefe_directo.data,
            # GUARDAMOS LOS NUEVOS CAMPOS
            puesto=form.puesto.data,
            cargo_jefe=form.cargo_jefe.data,
            proyecto_actual=form.proyecto_actual.data,
            activo=(form.status.data == '1') 
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('¡Registro exitoso! Ahora puedes iniciar sesión.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Registro', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # 1. Intentamos buscar al usuario por el correo ingresado
        user = User.query.filter_by(email=form.email.data).first()
        
        # VALIDACIÓN 1: ¿Existe el correo?
        if user is None:
            flash('El correo electrónico no está registrado.', 'danger')
            return redirect(url_for('auth.login'))
        
        # VALIDACIÓN 2: ¿La contraseña es correcta?
        if not user.check_password(form.password.data):
            flash('La contraseña es incorrecta. Por favor, verifica tus datos.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Si ambas pasan, iniciamos sesión
        login_user(user)
        flash(f'¡Bienvenido de nuevo, {user.nombre}!', 'success')
        
        # Redirigir a la página que intentaba entrar o al index
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.index'))
    
        login_user(user)
        flash(f'¡Bienvenido, representante de {user.empresa}!', 'success')
        
        if user.rol == 'cliente':
            return redirect(url_for('main.cliente_dashboard'))
        
        next_page = request.args.get('next')
        
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))