from app import create_app, db
from app.models import User, Bitacora

app = create_app()

with app.app_context():
    print("=" * 65)
    print("🚀 INICIANDO MIGRACIÓN DE NOMBRES DE EMPRESAS")
    print("=" * 65)

    # 1. Actualizar registros en la tabla de Usuarios (User)
    usuarios_a = User.query.filter_by(empresa='Empresa A').all()
    for u in usuarios_a:
        u.empresa = 'Hyphametrics'
    
    usuarios_b = User.query.filter_by(empresa='Empresa B').all()
    for u in usuarios_b:
        u.empresa = 'Qualis'

    print(f"👥 Usuarios actualizados en la base de datos:")
    print(f"   - Empresa A -> Hyphametrics: {len(usuarios_a)}")
    print(f"   - Empresa B -> Qualis: {len(usuarios_b)}")
    print("-" * 65)

    # 2. Actualizar registros en la tabla de Bitácoras (Bitacora)
    bitacoras_a = Bitacora.query.filter_by(empresa='Empresa A').all()
    for b in bitacoras_a:
        b.empresa = 'Hyphametrics'

    bitacoras_b = Bitacora.query.filter_by(empresa='Empresa B').all()
    for b in bitacoras_b:
        b.empresa = 'Qualis'

    print(f"📝 Reportes de bitácora actualizados:")
    print(f"   - Empresa A -> Hyphametrics: {len(bitacoras_a)}")
    print(f"   - Empresa B -> Qualis: {len(bitacoras_b)}")

    # Guardar cambios definitivos en la base de datos
    db.session.commit()
    print("=" * 65)
    print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE EN LA BASE DE DATOS")
    print("=" * 65)