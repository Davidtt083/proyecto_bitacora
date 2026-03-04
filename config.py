import os
from dotenv import load_dotenv

# Ubicación absoluta de la carpeta de tu proyecto
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-por-defecto'
    
    # --- CONFIGURACIÓN PARA SQLITE (Súper simple) ---
    # Esto creará un archivo llamado 'app.db' mágicamente en tu carpeta
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False