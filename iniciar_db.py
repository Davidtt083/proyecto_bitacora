# iniciar_db.py

# 1. En lugar de importar 'app', importamos 'create_app'
from app import create_app, db
from app.models import User

# 2. Construimos la aplicación llamando a la función
app = create_app()

# 3. Ahora sí, le decimos a Flask que trabaje dentro del contexto de esta app
with app.app_context():
    # Crear el archivo SQLite y las tablas
    db.create_all()
    print("✅ Base de datos SQLite y tablas creadas.")

    # Crear el Súper Usuario (Administrador)
    admin = User.query.filter_by(email='admin@midominio.com').first()
    
    if not admin:
        admin = User(
            nombre='Jorge Luis Medellín Santillan',    # <-- CAMBIA POR TU NOMBRE
            email='jorge.medellin@progredi.com.mx',    # <-- CAMBIA POR TU CORREO
            telefono='0000000000',
            empresa='Administración',
            puesto='Administrador',
            rol='admin',
            activo=True
        )
        admin.set_password('J0rG3*2026!')    # <-- CAMBIA POR TU CONTRASEÑA
        db.session.add(admin)
        db.session.commit()
        print("✅ Administrador creado con éxito.")
    else:
        print("⚠️ El admin ya existe.")