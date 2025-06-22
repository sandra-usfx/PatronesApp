from app import create_app

# app va a ser igual a create_app()
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)  # debug=True durante desarrollo, False para producción