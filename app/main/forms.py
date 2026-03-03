from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Optional, URL, Length

class BitacoraForm(FlaskForm):
    nombre_completo = StringField('Nombre Completo', validators=[DataRequired(), Length(max=100)])
    empresa = SelectField('Empresa cliente', choices=[ 
        ('Empresa A', 'Empresa A'),
        ('Empresa B', 'Empresa B'),
        ('Empresa C', 'Empresa C'),
        ('Empresa D', 'Empresa D'),
        ('Independiente', 'Trabajador Independiente')
    ], validators=[DataRequired()])
    puesto = StringField('Puesto / Cargo', validators=[DataRequired()])
    periodo_semanal = StringField('Periodo Semanal (ej. Lun 02 - Vie 06 Oct)', validators=[DataRequired()])
    
    nombre_jefe_inmediato = StringField('Nombre del Jefe Inmediato', validators=[DataRequired()])
    cargo_jefe_inmediato = StringField('Cargo del Jefe Inmediato', validators=[DataRequired()])
    
    proyecto_actual = StringField('Proyecto Actual', validators=[DataRequired()])
    actividades = TextAreaField('Actividades Realizadas', validators=[DataRequired()])
    
    herramientas_utilizadas = StringField('Herramientas Utilizadas')
    status = SelectField('Status de la Actividad', choices=[
        ('En proceso', 'En proceso'),
        ('Finalizado', 'Finalizado')
    ], validators=[DataRequired()], id="status-select") # Agregamos ID para JS

    entregable_generado = StringField('Entregable Generado')
    medio_entregable = StringField('Medio Entregable (Link, Carpeta, Correo, etc.)')
    incidencias = TextAreaField('Incidencias / Observaciones (Opcional)')
    
    submit = SubmitField('Guardar Reporte de Bitácora')

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
    puesto = StringField('Puesto / Cargo', validators=[DataRequired()])
    
    status = SelectField('Estado del Usuario', choices=[
        ('1', 'Vigente'),
        ('0', 'No Vigente')
    ], validators=[DataRequired()])
    
    submit = SubmitField('Actualizar Usuario')