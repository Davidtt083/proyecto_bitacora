from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    
    # Roles: 'admin' o 'usuario'. Por defecto será usuario.
    rol = db.Column(db.String(20), default='usuario', nullable=False)

    # Campos que servirán de "Default" para la bitácora
    empresa = db.Column(db.String(100), nullable=True)
    empresa_origen = db.Column(db.String(100), nullable=True)
    puesto = db.Column(db.String(100), nullable=True)
    proyecto_actual = db.Column(db.String(200), nullable=True)
    jefe_directo = db.Column(db.String(100), nullable=True)
    cargo_jefe = db.Column(db.String(100), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Fecha de registro
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # RELACIÓN: Un usuario puede tener muchas bitácoras
    # 'backref' crea una propiedad .autor en cada bitácora para saber de quién es
    bitacoras = db.relationship('Bitacora', backref='autor', lazy='dynamic', cascade='all, delete-orphan')

    # Métodos para seguridad de contraseña
    def set_password(self, password):
        """Crea un hash seguro de la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña introducida coincide con el hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

# --- NUEVO MODELO DE BITÁCORA ---

class Bitacora(db.Model):
    __tablename__ = 'bitacoras'

    id = db.Column(db.Integer, primary_key=True)
    
    # Datos que pediste en la lista
    nombre_completo = db.Column(db.String(100), nullable=False) # Se llena con current_user.nombre
    empresa = db.Column(db.String(100), nullable=False)         # Se llena con current_user.empresa
    puesto = db.Column(db.String(100), nullable=False)
    periodo_semanal = db.Column(db.String(100), nullable=False)
    nombre_jefe_inmediato = db.Column(db.String(100), nullable=False)
    cargo_jefe_inmediato = db.Column(db.String(100), nullable=False)
    proyecto_actual = db.Column(db.String(200), nullable=False)
    actividades = db.Column(db.Text, nullable=False)
    herramientas_utilizadas = db.Column(db.String(200))
    entregable_generado = db.Column(db.String(200))
    status = db.Column(db.String(20), nullable=False, default='En proceso')
    medio_entregable = db.Column(db.Text)
    incidencias = db.Column(db.Text)
    
    
    # Metadatos
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    # Relación con la tabla users
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Bitacora {self.id} de {self.nombre_completo}>'

# Este decorador es necesario para que Flask-Login cargue al usuario por su ID
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))