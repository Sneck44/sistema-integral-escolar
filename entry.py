import os
import base64
from flask import send_file, Response
import ui_app
from app_icon_data import APP_ICON_JPEG_B64

app = ui_app.app

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


def apple_touch_icon():
    return Response(
        base64.b64decode(APP_ICON_JPEG_B64),
        mimetype='image/jpeg',
        headers={'Cache-Control': 'public, max-age=86400'},
    )


app.view_functions['school_logo'] = school_logo_exact
app.add_url_rule('/apple-touch-icon.jpg', 'apple_touch_icon', apple_touch_icon)
ui_app.STATIC_LOGO = '/school-logo?v=20260902-finalpng'
