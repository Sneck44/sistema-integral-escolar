from flask import request, session

import multi_user


def _profile():
    uid = session.get('uid')
    return multi_user._profile(uid) if uid else None


def _allowed():
    p = _profile()
    return bool(p and p.active and p.role != 'PENDIENTE')


def _sidebar_link(active=False):
    return '<a class="nav-link%s" href="/suite"><span class="nav-icon">◎</span><span>Seguimiento integral</span></a>' % (' active' if active else '')


def _mobile_link(active=False):
    return '<a class="%s" href="/suite"><i>◎</i><span>Seguimiento</span></a>' % ('active' if active else '')


def install(app):
    @app.after_request
    def suite_navigation(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not _allowed():
            return response
        html = response.get_data(as_text=True)
        active = request.path.startswith('/suite')

        # Menú lateral: visible para todos los perfiles autorizados.
        if '<nav class="side-nav">' in html and 'href="/suite"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            html = html.replace(marker, _sidebar_link(active) + marker, 1)
        elif active and 'href="/suite"' in html:
            html = html.replace('class="nav-link" href="/suite"', 'class="nav-link active" href="/suite"', 1)

        # Navegación inferior móvil: no sustituye opciones; agrega acceso directo.
        if '<nav class="bottom-nav">' in html:
            start = html.find('<nav class="bottom-nav">')
            end = html.find('</nav>', start)
            fragment = html[start:end] if end != -1 else ''
            if 'href="/suite"' not in fragment and end != -1:
                html = html[:end] + _mobile_link(active) + html[end:]

        # Acceso visible en la lista de alumnos para llegar al expediente digital.
        if request.path == '/students' and 'Abrir expedientes integrales' not in html:
            marker = '<h1>Alumnos'
            pos = html.find(marker)
            if pos != -1:
                close = html.find('</h1>', pos)
                if close != -1:
                    close += 5
                    action = '<div style="margin:10px 0 16px"><a class="btn" href="/suite/students" style="display:inline-flex;text-decoration:none;background:#7b1024;color:#fff;padding:10px 14px;border-radius:10px;font-weight:800">Abrir expedientes integrales</a></div>'
                    html = html[:close] + action + html[close:]

        # Acceso adicional desde el inicio para que la suite no dependa solo del menú.
        if request.path == '/' and 'Centro de Seguimiento Integral' not in html and '<main class="wrap">' in html:
            card = '''<div class="card" id="suite-home-access" style="margin-bottom:16px"><div style="display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap"><div><h2 style="margin:0 0 5px">Centro de Seguimiento Integral</h2><p class="muted" style="margin:0">Expedientes, alertas, pendientes, reportes, tutoría, convivencia, documentos, agenda, estadísticas, planeación y evidencias.</p></div><a href="/suite" style="display:inline-flex;text-decoration:none;background:#7b1024;color:white;padding:11px 16px;border-radius:10px;font-weight:800">Abrir 11 módulos</a></div></div>'''
            html = html.replace('<main class="wrap">', '<main class="wrap">' + card, 1)

        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
