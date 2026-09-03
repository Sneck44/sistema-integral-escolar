from flask import request, session


def install(app):
    @app.after_request
    def ensure_attendance_list_button(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        if request.path.rstrip('/') != '/attendance':
            return response
        html = response.get_data(as_text=True)
        if '/attendance/list.xlsx' in html:
            return response
        card = '''<div class="card attendance-list-card" style="margin-bottom:18px">
<h2 style="margin-top:0">Lista de asistencia para imprimir</h2>
<p class="muted">Genera el formato institucional con ciclo escolar, grado y grupo, docente titular y los alumnos del grupo activo.</p>
<a href="/attendance/list.xlsx" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none;background:#7b1024;color:#fff;padding:11px 16px;border-radius:10px;font-weight:800">Generar lista de asistencia en Excel</a>
</div>'''
        if '<h1>Asistencia</h1>' in html:
            html = html.replace('<h1>Asistencia</h1>', '<h1>Asistencia</h1>' + card, 1)
        elif '<main' in html and '</main>' in html:
            html = html.replace('</main>', card + '</main>', 1)
        elif '</body>' in html:
            html = html.replace('</body>', card + '</body>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
