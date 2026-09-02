import os
from flask import send_file
import ui_app

app = ui_app.app

# Archivo PNG original subido por el usuario. Se sirve sin modificar ni convertir.
LOGO_FILE = os.path.join(
    os.path.dirname(__file__),
    'static',
    '    logo-benito-juarez.png.PNG',
)


def school_logo_exact():
    return send_file(
        LOGO_FILE,
        mimetype='image/png',
        conditional=True,
        max_age=0,
        download_name='logo-benito-juarez.png',
    )


# La interfaz completa usa esta misma ruta para el logo.
app.view_functions['school_logo'] = school_logo_exact
ui_app.STATIC_LOGO = '/school-logo?v=20260902-originalpng'
