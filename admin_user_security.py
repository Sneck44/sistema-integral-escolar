import re
from flask import request, session, redirect, flash

import multi_user


PROTECTED_PREFIXES = (
    '/users',
)


def _is_admin():
    try:
        return bool(multi_user._is_admin())
    except Exception:
        return False


def install(app):
    @app.before_request
    def admin_only_user_management():
        path = request.path or ''
        if not path.startswith(PROTECTED_PREFIXES):
            return None
        if _is_admin():
            return None
        flash('Solo el administrador puede ver usuarios, revisar solicitudes y autorizar grupos.')
        return redirect('/')

    @app.after_request
    def hide_admin_user_controls(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        if not session.get('uid') or _is_admin():
            return response

        html = response.get_data(as_text=True)

        # Oculta cualquier acceso al módulo de usuarios que pudiera ser agregado
        # por otro módulo o quedar en una plantilla antigua.
        html = re.sub(
            r'<a\b[^>]*href=["\']/users(?:[^"\']*)["\'][^>]*>.*?</a>',
            '', html, flags=re.I | re.S,
        )

        # Oculta formularios administrativos sensibles si por alguna razón
        # aparecieran en una respuesta HTML fuera del módulo /users.
        html = re.sub(
            r'<form\b[^>]*action=["\']/users/\d+/(?:update|password|group-access|reject|restore-request|delete-request)["\'][^>]*>.*?</form>',
            '', html, flags=re.I | re.S,
        )

        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
