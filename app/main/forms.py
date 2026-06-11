from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, URL, Length, EqualTo

class BitacoraForm(FlaskForm):
    nombre_completo = StringField('Nombre completo', validators=[DataRequired(), Length(max=100)])
    empresa = SelectField('Empresa cliente', choices=[ 
        ('Empresa A', 'Empresa A'),
        ('Empresa B', 'Empresa B'),
        ('Empresa C', 'Empresa C'),
        ('Empresa D', 'Empresa D'),
        ('Independiente', 'Trabajador independiente')
    ], validators=[DataRequired()])
    puesto = StringField('Puesto / cargo', validators=[DataRequired()])
    periodo_semanal = StringField('Periodo semanal (ej. Lun 02 - Vie 06 Oct)', validators=[DataRequired()])
    
    nombre_jefe_inmediato = StringField('Nombre del jefe directo', validators=[DataRequired()])
    cargo_jefe_inmediato = StringField('Cargo del jefe directo', validators=[DataRequired()])
    
    proyecto_actual = StringField('Proyecto actual', validators=[DataRequired()])
    actividades = TextAreaField('Actividades realizadas', validators=[DataRequired()])
    
    herramientas_utilizadas = StringField('Herramientas utilizadas')
    status = SelectField('Estatus de la actividad', choices=[
        ('En proceso', 'En proceso'),
        ('Finalizado', 'Finalizado')
    ], validators=[DataRequired()], id="status-select") # Agregamos ID para JS

    entregable_generado = StringField('Entregable generado')
    medio_entregable = StringField('Medio entregable (Link, Carpeta, Correo, etc.)')
    incidencias = TextAreaField('Incidencias / observaciones (opcional)')
    
    submit = SubmitField('Guardar reporte de bitácora')

class EditUserAdminForm(FlaskForm):
    nombre = StringField('Nombre completo', validators=[DataRequired()])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Número telefónico', validators=[DataRequired()])
    empresa = SelectField('Empresa', choices=[ 
        ('Empresa A', 'Empresa A'),
        ('Empresa B', 'Empresa B'),
        ('Empresa C', 'Empresa C'),
        ('Empresa D', 'Empresa D'),
        ('Independiente', 'Trabajador Independiente')
    ], validators=[DataRequired()])
    empresa_origen = SelectField('Empresa origen', choices=[
        ('Krolls', 'Krolls'),
        ('PROGREDI', 'PROGREDI'),
    ], validators=[DataRequired()])
    puesto = StringField('Puesto / cargo', validators=[DataRequired()])
    jefe_directo = StringField('A quién reporta (Jefe directo)', validators=[DataRequired()])
    
    rol = SelectField('Rol en el sistema', choices=[
        ('usuario', 'Consultor / empleado (normal)'),
        ('cliente', 'Cliente (solo ve su empresa)'),
        ('admin', 'Administrador maestro')
    ], validators=[DataRequired()])
    
    status = SelectField('Estado del usuario', choices=[
        ('1', 'Vigente'),
        ('0', 'No vigente')
    ], validators=[DataRequired()])
    
    # --- NUEVOS CAMPOS DE CONTRASEÑA ---
    password = PasswordField('Nueva contraseña (Dejar en blanco para NO cambiarla)', validators=[Optional()])
    password_confirm = PasswordField('Confirmar nueva contraseña', validators=[EqualTo('password', message='Las contraseñas no coinciden')])
    
    submit = SubmitField('Actualizar usuario')

class EditReportAdminForm(FlaskForm):
    nombre_completo = StringField('Nombre completo', validators=[DataRequired()])
    empresa = SelectField('Empresa cliente', choices=[ 
        ('Empresa A', 'Empresa A'),
        ('Empresa B', 'Empresa B'),
        ('Empresa C', 'Empresa C'),
        ('Empresa D', 'Empresa D'),
        ('Independiente', 'Trabajador independiente')
    ], validators=[DataRequired()])
    puesto = StringField('Puesto / cargo', validators=[DataRequired()])
    nombre_jefe_inmediato = StringField('Jefe directo', validators=[DataRequired()])
    cargo_jefe_inmediato = StringField('Cargo del jefe', validators=[DataRequired()])
    
    # Lo dejamos como texto libre para que el admin pueda corregir la cadena de fechas fácilmente
    periodo_semanal = StringField('Días laborados (separados por |)', validators=[DataRequired()]) 
    
    proyecto_actual = StringField('Proyecto actual', validators=[DataRequired()])
    actividades = TextAreaField('Actividades realizadas', validators=[DataRequired()])
    herramientas_utilizadas = StringField('Herramientas utilizadas')
    
    status = SelectField('Estatus', choices=[
        ('En proceso', 'En proceso'),
        ('Finalizado', 'Finalizado')
    ], validators=[DataRequired()])
    
    entregable_generado = StringField('Entregable generado')
    medio_entregable = StringField('Medio entregable')
    incidencias = TextAreaField('Incidencias / observaciones')
    
    submit = SubmitField('Actualizar fila')