from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.models import User

# --- CLASE QUE FALTABA ---
class LoginForm(FlaskForm):
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

# --- CLASE DE REGISTRO ACTUALIZADA ---
class RegistrationForm(FlaskForm):
    nombre = StringField('Nombre completo', validators=[DataRequired()])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Número telefónico', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    password_confirm = PasswordField('Confirmar Contraseña', 
                                    validators=[DataRequired(), EqualTo('password')])
    
    # Campo Empresa como SELECT
    empresa = SelectField('Empresa - cliente', choices=[
        ('', '--- Seleccione una empresa ---'),
        ('Hyphametrics', 'Hyphametrics'),
        ('Qualis', 'Qualis'),
        ('Empresa C', 'Empresa C'),
        ('Empresa D', 'Empresa D'),
        ('Independiente', 'Trabajador independiente')
    ], validators=[DataRequired()])

    jefe_directo = StringField('A quién reporta (jefe directo)', validators=[DataRequired()])
    puesto = StringField('Puesto / cargo', validators=[DataRequired()])
    cargo_jefe = StringField('Cargo de jefe directo', validators=[DataRequired()])
    proyecto_actual = StringField('Proyecto', validators=[DataRequired()])
    empresa_origen = SelectField('Empresa - origen', choices=[
        ('', '--- Seleccione una empresa ---'),
        ('Krolls', 'Krolls'),
        ('PROGREDI', 'PROGREDI'),
    ], validators=[DataRequired()])

    status = SelectField('Estado del usuario', choices=[
        ('1', 'Vigente'),
        ('0', 'No Vigente')
    ], default='1', validators=[DataRequired()])
    
    submit = SubmitField('Registrar')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este correo ya está registrado.')