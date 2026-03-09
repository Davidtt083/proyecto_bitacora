from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # 1. Crea las tablas si no existen
    db.create_all()
    
    # 2. Revisa si la base de datos está vacía
    if not User.query.first():
        # 3. Si está vacía, crea el Administrador Maestro
        admin = User(
            nombre="Administrador Maestro",
            email="admin@admin.com",
            empresa="Krolls",
            rol="admin",
            activo=True
        )
        admin.set_password("admin123") # Contraseña por defecto
        
        db.session.add(admin)
        db.session.commit()
        print("¡Usuario administrador creado exitosamente!")

if __name__ == '__main__':
    app.run()