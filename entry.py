import base64
from flask import Response

import ui_app
from logo_jpeg_data import LOGO_JPEG_B64


def embedded_school_logo():
    try:
        payload = base64.b64decode(LOGO_JPEG_B64, validate=False)
    except Exception:
        payload = b''
    return Response(
        payload,
        status=200 if payload else 500,
        mimetype='image/jpeg',
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Content-Disposition': 'inline; filename="logo-benito-juarez.jpeg"',
            'X-Content-Type-Options': 'nosniff',
        },
    )


# Sustituye la vista existente por una respuesta binaria embebida.
ui_app.app.view_functions['school_logo_final'] = embedded_school_logo

# La función page() de ui_app consulta esta variable en cada petición.
ui_app.STATIC_LOGO = '/school-logo-final?v=20260902-embedded'

app = ui_app.app
