from datetime import timedelta
from flask import Flask, session  # Agregamos "session" para manejar la cookie de sesión
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

# Inicializar extensiones (pero aún no ligarlas a la app)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # A dónde redirigir si no está logueado
login_manager.login_message = 'Por favor inicia sesión para acceder.'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Configurar la duración de la sesión a 10 minutos
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Registrar blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # 2. Hook para que la sesión se auto-extienda con cada clic (por inactividad)
    @app.before_request
    def refrescar_sesion():
        session.permanent = True
        session.modified = True # Obliga a Flask a enviar una nueva cookie extendida al navegador

    # IMPORTANTE: Importar los modelos aquí para que Flask-Migrate los vea
    from app import models 

    return app