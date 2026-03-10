from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Optional, URL, Length

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
    
    nombre_jefe_inmediato = StringField('Nombre del jefe inmediato', validators=[DataRequired()])
    cargo_jefe_inmediato = StringField('Cargo del jefe inmediato', validators=[DataRequired()])
    
    proyecto_actual = StringField('Proyecto actual', validators=[DataRequired()])
    actividades = TextAreaField('Actividades realizadas', validators=[DataRequired()])
    
    herramientas_utilizadas = StringField('Herramientas utilizadas')
    status = SelectField('Estatus de la actividad', choices=[
        ('En proceso', 'En proceso'),
        ('Finalizado', 'Finalizado')
    ], validators=[DataRequired()], id="status-select") # Agregamos ID para JS

    entregable_generado = StringField('Entregable generado')
    medio_entregable = StringField('Medio entregable (Link, Carpeta, Correo, etc.)')
    incidencias = TextAreaField('Incidencias / observaciones (Opcional)')
    
    submit = SubmitField('Guardar reporte de bitácora')

class EditUserAdminForm(FlaskForm):
    nombre = StringField('Nombre Completo', validators=[DataRequired()])
    email = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Número Telefónico', validators=[DataRequired()])
    empresa = SelectField('Empresa', choices=[ 
        ('Empresa A', 'Empresa A'),
        ('Empresa B', 'Empresa B'),
        ('Empresa C', 'Empresa C'),
        ('Empresa D', 'Empresa D'),
        ('Independiente', 'Trabajador Independiente')
    ], validators=[DataRequired()])
    empresa_origen = SelectField('Empresa Origen', choices=[
        ('Krolls', 'Krolls'),
        ('PROGREDI', 'PROGREDI'),
    ], validators=[DataRequired()])
    puesto = StringField('Puesto / Cargo', validators=[DataRequired()])
    jefe_directo = StringField('A quién reporta (Jefe Directo)', validators=[DataRequired()])    
    status = SelectField('Estado del Usuario', choices=[
        ('1', 'Vigente'),
        ('0', 'No Vigente')
    ], validators=[DataRequired()])
    
    submit = SubmitField('Actualizar Usuario')

class EditReportAdminForm(FlaskForm):
    nombre_completo = StringField('Nombre completo', validators=[DataRequired()])
    empresa = SelectField('Empresa Cliente', choices=[ 
        ('Empresa A', 'Empresa A'),
        ('Empresa B', 'Empresa B'),
        ('Empresa C', 'Empresa C'),
        ('Empresa D', 'Empresa D'),
        ('Independiente', 'Trabajador Independiente')
    ], validators=[DataRequired()])
    puesto = StringField('Puesto / Cargo', validators=[DataRequired()])
    nombre_jefe_inmediato = StringField('Jefe Inmediato', validators=[DataRequired()])
    cargo_jefe_inmediato = StringField('Cargo del Jefe', validators=[DataRequired()])
    
    # Lo dejamos como texto libre para que el admin pueda corregir la cadena de fechas fácilmente
    periodo_semanal = StringField('Días Laborados (Separados por |)', validators=[DataRequired()]) 
    
    proyecto_actual = StringField('Proyecto Actual', validators=[DataRequired()])
    actividades = TextAreaField('Actividades Realizadas', validators=[DataRequired()])
    herramientas_utilizadas = StringField('Herramientas Utilizadas')
    
    status = SelectField('Estatus', choices=[
        ('En proceso', 'En proceso'),
        ('Finalizado', 'Finalizado')
    ], validators=[DataRequired()])
    
    entregable_generado = StringField('Entregable Generado')
    medio_entregable = StringField('Medio Entregable')
    incidencias = TextAreaField('Incidencias / Observaciones')
    
    submit = SubmitField('Actualizar Fila')