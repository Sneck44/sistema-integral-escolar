import re
from flask import request, session


def _is_admin():
    uid = session.get('uid')
    if not uid:
        return False
    try:
        import multi_user
        p = multi_user._profile(uid)
        return bool(p and p.active and p.role == 'ADMIN')
    except Exception:
        return False


def _reorder_admin_sidebar(html):
    if not _is_admin() or '<nav class="side-nav">' not in html:
        return html

    # Solo toca los enlaces del menú lateral. El orden solicitado es:
    # Mi perfil -> Usuarios -> Configuración -> Cerrar sesión.
    wanted = [
        ('/account/profile', 'Mi perfil'),
        ('/users', 'Usuarios'),
        ('/config', 'Configuración'),
    ]

    extracted = {}
    for href, _label in wanted:
        pattern = rf'<a class="nav-link(?: active)?" href="{re.escape(href)}">.*?</a>'
        match = re.search(pattern, html, flags=re.S)
        if match:
            extracted[href] = match.group(0)
            html = html[:match.start()] + html[match.end():]

    logout_pattern = r'<a class="nav-link logout" href="/logout">.*?</a>'
    logout = re.search(logout_pattern, html, flags=re.S)
    if not logout:
        return html

    block = ''
    for href, _label in wanted:
        if href in extracted:
            block += extracted[href]

    html = html[:logout.start()] + block + html[logout.start():]
    return html


def _ensure_logo_manager(html):
    if request.path != '/config' or not _is_admin() or 'id="document-logos"' in html:
        return html
    try:
        import document_logos
        panel = document_logos._panel()
    except Exception:
        return html

    marker = '<h1>Configuración</h1>'
    start = html.find(marker)
    if start != -1:
        form_end = html.find('</form>', start)
        if form_end != -1:
            pos = form_end + len('</form>')
            return html[:pos] + panel + html[pos:]

    footer = html.find('<footer class="footer">')
    if footer != -1:
        return html[:footer] + panel + html[footer:]
    if '</main>' in html:
        return html.replace('</main>', panel + '</main>', 1)
    return html


def install(app):
    @app.after_request
    def admin_ui_finalizer(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        html = _ensure_logo_manager(html)
        html = _reorder_admin_sidebar(html)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
