import os
from flask import send_file
import ui_app

app = ui_app.app

BASE_DIR = os.path.dirname(__file__)
LOGO_FILE = os.path.join(BASE_DIR, 'static', 'logo-benito-juarez-final.PNG')
APP_ICON_FILE = os.path.join(BASE_DIR, 'static', 'apple-touch-icon.PNG')


def school_logo_exact():
    return send_file(
        LOGO_FILE,
        mimetype='image/png',
        conditional=True,
        max_age=0,
        download_name='logo-benito-juarez-final.PNG',
    )


def apple_touch_icon_exact():
    return send_file(
        APP_ICON_FILE,
        mimetype='image/png',
        conditional=True,
        max_age=0,
        download_name='apple-touch-icon.PNG',
    )


# Rutas exactas para el logo institucional y el icono de iPhone.
app.view_functions['school_logo'] = school_logo_exact
app.add_url_rule('/apple-touch-icon.png', 'apple_touch_icon_png_exact', apple_touch_icon_exact)
app.add_url_rule('/apple-touch-icon-precomposed.png', 'apple_touch_icon_precomposed_exact', apple_touch_icon_exact)
app.add_url_rule('/favicon.png', 'favicon_png_exact', apple_touch_icon_exact)

# Fuerza a Safari/iOS a reconocer el icono subido por el usuario en todas las páginas.
@app.after_request
def add_ios_app_icon(response):
    content_type = response.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        html = response.get_data(as_text=True)
        if '</head>' in html:
            tags = (
                '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png?v=f45126bd">'
                '<link rel="apple-touch-icon-precomposed" href="/apple-touch-icon-precomposed.png?v=f45126bd">'
                '<link rel="icon" type="image/png" href="/favicon.png?v=f45126bd">'
                '<meta name="apple-mobile-web-app-capable" content="yes">'
                '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
                '<meta name="apple-mobile-web-app-title" content="Sistema Escolar">'
            )
            html = html.replace('</head>', tags + '</head>', 1)
            response.set_data(html)
            response.headers['Content-Length'] = str(len(response.get_data()))
    return response

# El logo horizontal del sistema sigue usando el archivo institucional definitivo.
ui_app.STATIC_LOGO = '/school-logo?v=20260902-finalpng'
