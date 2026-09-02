import base64
from flask import Response
import ui_app
from logo_jpeg_data import LOGO_JPEG_B64


def school_logo_embedded():
    payload = base64.b64decode(LOGO_JPEG_B64.strip(), validate=False)
    return Response(
        payload,
        mimetype='image/jpeg',
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Content-Disposition': 'inline; filename="logo-benito-juarez.jpg"',
        },
    )


# Sustituir exactamente la vista que usa la interfaz: /school-logo
ui_app.app.view_functions['school_logo'] = school_logo_embedded

# Punto de entrada de producción estable.
app = ui_app.app
