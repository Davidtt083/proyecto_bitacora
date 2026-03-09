from app import create_app

# Gunicorn buscará esta variable 'app'
app = create_app()

if __name__ == '__main__':
    app.run()