import ui_app

# En producción, cargar el logo directamente desde GitHub RAW para evitar
# problemas de publicación de archivos estáticos en Vercel.
ui_app.STATIC_LOGO = (
    'https://raw.githubusercontent.com/'
    'Sneck44/sistema-integral-escolar/main/static/logo-school.jpeg'
    '?v=20260901-raw'
)

app = ui_app.app
