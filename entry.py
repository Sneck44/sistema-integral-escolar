import os
from flask import send_file
import ui_app

app = ui_app.app

# Archivo PNG final subido a GitHub. Se sirve directamente, sin conversión.
LOGO_FILE = os.path.join(
    os.path.dirname(__file__),
    'static',
    'logo-benito-juarez-final.PNG',
)


def school_logo_exact():
    return send_file(
        LOGO_FILE,
        mimetype='image/png',
        conditional=True,
        max_age=0,
        download_name='logo-benito-juarez-final.PNG',
    )


# Reemplaza únicamente la vista /school-logo usada por toda la interfaz.
app.view_functions['school_logo'] = school_logo_exact
ui_app.STATIC_LOGO = '/school-logo?v=20260902-finalpng'
