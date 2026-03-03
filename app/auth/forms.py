from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.models import User

# --- CLASE QUE FALTABA ---
class LoginForm(FlaskForm):
    email = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

# --- CLASE DE REGISTRO ACTUALIZADA ---
class RegistrationForm(FlaskForm):
    nombre = StringField('Nombre Completo', validators=[DataRequired()])
    email = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Número Telefónico', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    password_confirm = PasswordField('Confirmar Contraseña', 
                                    validators=[DataRequired(), EqualTo('password')])
    
    # Campo Empresa como SELECT
    empresa = SelectField('Empresa - Cliente', choices=[
        ('', '--- Seleccione una Empresa ---'),
        ('Empresa A', 'Empresa A'),
        ('Empresa B', 'Empresa B'),
        ('Empresa C', 'Empresa C'),
        ('Empresa D', 'Empresa D'),
        ('Independiente', 'Trabajador Independiente')
    ], validators=[DataRequired()])

    jefe_directo = StringField('A quién reportas (Jefe Directo)', validators=[DataRequired()])
    puesto = StringField('Tu Puesto / Cargo', validators=[DataRequired()])
    cargo_jefe = StringField('Cargo de tu Jefe Inmediato', validators=[DataRequired()])
    proyecto_actual = StringField('Proyecto Actual', validators=[DataRequired()])
    empresa_origen = SelectField('Empresa - Origen', choices=[
        ('', '--- Seleccione una Empresa ---'),
        ('Krolls', 'Krolls'),
        ('PROGREDI', 'PROGREDI'),
    ], validators=[DataRequired()])

    status = SelectField('Estado del Usuario', choices=[
        ('1', 'Vigente'),
        ('0', 'No Vigente')
    ], default='1', validators=[DataRequired()])
    
    submit = SubmitField('Registrarse')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este correo ya está registrado.')