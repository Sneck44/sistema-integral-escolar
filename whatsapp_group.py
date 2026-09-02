from html import escape
from urllib.parse import quote
from flask import session, redirect

import app as core


def _digits(phone):
    return ''.join(ch for ch in (phone or '') if ch.isdigit())


def _mx_phone(phone):
    digits = _digits(phone)
    if len(digits) == 10:
        return '52' + digits
    if len(digits) == 12 and digits.startswith('52'):
        return digits
    return digits


def install(app):
    @app.route('/whatsapp-group')
    def whatsapp_group():
        if not session.get('uid'):
            return redirect('/login')

        students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()
        valid = []
        missing = []
        for s in students:
            number = _mx_phone(s.phone)
            if len(number) >= 11:
                valid.append((s, number))
            else:
                missing.append(s)

        rows = ''
        for s, number in valid:
            text = quote(f'Hola. Soy docente del grupo. Este número está registrado como contacto de {s.full_name}.')
            rows += f'''<tr>
              <td>{escape(str(s.list_no or ''))}</td>
              <td><b>{escape(s.full_name)}</b><br><small>{escape(s.tutor or 'Tutor no especificado')}</small></td>
              <td>{escape(s.phone or '')}</td>
              <td><a class="wa-btn" target="_blank" rel="noopener" href="https://wa.me/{number}?text={text}">Abrir WhatsApp</a></td>
            </tr>'''

        missing_html = ''.join(f'<li>{escape(s.full_name)}</li>' for s in missing)
        numbers_text = ', '.join('+' + number for _, number in valid)
        body = f'''
        <h1>Grupo de WhatsApp</h1>
        <div class="card">
          <h2>Preparar grupo con los contactos registrados</h2>
          <p>Se encontraron <b>{len(valid)}</b> teléfonos utilizables de <b>{len(students)}</b> alumnos activos.</p>
          <p class="muted">Por seguridad y por las limitaciones de WhatsApp, una página web no puede crear silenciosamente un grupo ni agregar personas sin intervención en WhatsApp. Esta herramienta reúne y valida los teléfonos para facilitar el proceso.</p>
          <label>Nombre sugerido del grupo<input id="groupName" value="Padres y tutores - {escape(core.cfg().grade)} {escape(core.cfg().group)} - {escape(core.cfg().cycle)}"></label><br><br>
          <label>Teléfonos listos para copiar<textarea id="phones" rows="5" readonly>{escape(numbers_text)}</textarea></label><br>
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <button type="button" style="width:auto" onclick="navigator.clipboard.writeText(document.getElementById('phones').value);this.textContent='✓ Teléfonos copiados'">Copiar teléfonos</button>
            <a class="wa-main" target="_blank" rel="noopener" href="https://web.whatsapp.com/">Abrir WhatsApp Web</a>
          </div>
        </div>
        <div class="card scroll"><h2>Contactos</h2><table><tr><th>No.</th><th>Alumno / tutor</th><th>Teléfono</th><th>Acción</th></tr>{rows}</table></div>
        {f'<div class="card"><h2>Sin teléfono válido ({len(missing)})</h2><p class="muted">Edita estos alumnos para completar el teléfono del tutor.</p><ul>{missing_html}</ul></div>' if missing else ''}
        <style>
        .wa-btn,.wa-main{{display:inline-block;text-decoration:none;border-radius:9px;padding:10px 14px;font-weight:800}}
        .wa-btn{{background:#eaf8ef;color:#16723a}}.wa-main{{background:#1f7a45;color:#fff}}
        </style>
        '''
        return core.page('Grupo de WhatsApp', body)

    @app.after_request
    def whatsapp_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if 'href="/whatsapp-group"' not in html:
            # Añadir al menú lateral antes de salir cuando existe la navegación moderna.
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/whatsapp-group"><span class="nav-icon">💬</span><span>WhatsApp</span></a>'
            if marker in html:
                html = html.replace(marker, link + marker, 1)
            else:
                marker2 = '<a href="/logout">Salir</a>'
                if marker2 in html:
                    html = html.replace(marker2, '<a href="/whatsapp-group">WhatsApp</a>' + marker2, 1)

        # Botón visible en dashboard.
        if '<h1>Panel de control</h1>' in html and '/whatsapp-group' not in html.split('<h1>Panel de control</h1>',1)[1][:1800]:
            button = '''<div class="card"><h2>Comunicación con familias</h2><p>Prepara los teléfonos registrados de madres, padres y tutores para crear tu grupo de WhatsApp.</p><a href="/whatsapp-group" style="display:inline-block;background:#1f7a45;color:white;text-decoration:none;padding:11px 16px;border-radius:9px;font-weight:800">💬 Preparar grupo de WhatsApp</a></div>'''
            html = html.replace('</main>', button + '</main>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
