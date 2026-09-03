from datetime import datetime
from html import escape
from urllib.parse import quote
from flask import session, redirect, request, flash

import app as core


class WhatsAppGroupMember(core.db.Model):
    __tablename__ = 'whatsapp_group_member'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), unique=True, nullable=False)
    state = core.db.Column(core.db.String(20), default='NO_AGREGADO', nullable=False)
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


def _digits(phone):
    return ''.join(ch for ch in (phone or '') if ch.isdigit())


def _local_phone(phone):
    """Devuelve el teléfono para mostrar/copiar sin el prefijo internacional 52."""
    digits = _digits(phone)
    if len(digits) == 12 and digits.startswith('52'):
        return digits[2:]
    return digits


def _wa_phone(phone):
    """WhatsApp necesita el código de país internamente, aunque no se muestre al usuario."""
    local = _local_phone(phone)
    if len(local) == 10:
        return '52' + local
    return _digits(phone)


def _state_for(student_id):
    row = WhatsAppGroupMember.query.filter_by(student_id=student_id).first()
    return row.state if row else 'NO_AGREGADO'


def _state_label(state):
    return {
        'NO_AGREGADO': 'No agregado',
        'PENDIENTE': 'Pendiente',
        'AGREGADO': 'Agregado',
    }.get(state, 'No agregado')


def install(app):
    @app.route('/whatsapp-group', methods=['GET', 'POST'])
    def whatsapp_group():
        if not session.get('uid'):
            return redirect('/login')

        if request.method == 'POST':
            student_id = request.form.get('student_id', type=int)
            new_state = request.form.get('state', '').strip().upper()
            if new_state not in ('NO_AGREGADO', 'PENDIENTE', 'AGREGADO'):
                flash('Estado de WhatsApp no válido.')
                return redirect('/whatsapp-group')
            student = core.db.session.get(core.Student, student_id) if student_id else None
            if not student:
                flash('No se encontró el alumno seleccionado.')
                return redirect('/whatsapp-group')
            row = WhatsAppGroupMember.query.filter_by(student_id=student.id).first()
            if not row:
                row = WhatsAppGroupMember(student_id=student.id)
            row.state = new_state
            row.updated_at = datetime.utcnow()
            core.db.session.add(row)
            core.db.session.commit()
            flash(f'{student.full_name}: {_state_label(new_state)}.')
            return redirect('/whatsapp-group')

        students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()
        valid = []
        missing = []
        counts = {'NO_AGREGADO': 0, 'PENDIENTE': 0, 'AGREGADO': 0}
        for s in students:
            state = _state_for(s.id)
            counts[state] = counts.get(state, 0) + 1
            local_number = _local_phone(s.phone)
            wa_number = _wa_phone(s.phone)
            if len(local_number) == 10 and len(wa_number) == 12:
                valid.append((s, local_number, wa_number, state))
            else:
                missing.append((s, state))

        rows = ''
        for s, local_number, wa_number, state in valid:
            text = quote(f'Hola. Soy docente del grupo. Este número está registrado como contacto de {s.full_name}.')
            status_class = {'NO_AGREGADO': 'status-no', 'PENDIENTE': 'status-pending', 'AGREGADO': 'status-ok'}.get(state, 'status-no')
            rows += f'''<tr data-state="{escape(state)}">
              <td>{escape(str(s.list_no or ''))}</td>
              <td><b>{escape(s.full_name)}</b><br><small>{escape(s.tutor or 'Tutor no especificado')}</small></td>
              <td><a class="phone-link" href="tel:{escape(local_number)}">{escape(local_number)}</a></td>
              <td><span class="status-pill {status_class}">{escape(_state_label(state))}</span></td>
              <td>
                <div class="wa-actions">
                  <a class="wa-btn" target="_blank" rel="noopener" href="https://wa.me/{wa_number}?text={text}">Abrir contacto</a>
                  <button type="button" class="copy-btn" data-phone="{escape(local_number)}" onclick="copyPhone(this)">Copiar</button>
                </div>
              </td>
              <td>
                <form method="post" class="state-form">
                  <input type="hidden" name="student_id" value="{s.id}">
                  <select name="state" onchange="this.form.submit()" aria-label="Estado de {escape(s.full_name)}">
                    <option value="NO_AGREGADO" {'selected' if state == 'NO_AGREGADO' else ''}>No agregado</option>
                    <option value="PENDIENTE" {'selected' if state == 'PENDIENTE' else ''}>Pendiente</option>
                    <option value="AGREGADO" {'selected' if state == 'AGREGADO' else ''}>Agregado</option>
                  </select>
                </form>
              </td>
            </tr>'''

        missing_html = ''.join(
            f'<li><b>{escape(s.full_name)}</b> — {_state_label(state)}</li>' for s, state in missing
        )
        numbers_text = ', '.join(local_number for _, local_number, _, state in valid if state != 'AGREGADO')
        body = f'''
        <h1>Grupo de WhatsApp</h1>
        <div class="wa-summary">
          <button type="button" class="summary-card" data-filter="TODOS" onclick="filterState('TODOS', this)"><span>{len(students)}</span><small>Total</small></button>
          <button type="button" class="summary-card" data-filter="NO_AGREGADO" onclick="filterState('NO_AGREGADO', this)"><span>{counts['NO_AGREGADO']}</span><small>No agregados</small></button>
          <button type="button" class="summary-card" data-filter="PENDIENTE" onclick="filterState('PENDIENTE', this)"><span>{counts['PENDIENTE']}</span><small>Pendientes</small></button>
          <button type="button" class="summary-card summary-ok" data-filter="AGREGADO" onclick="filterState('AGREGADO', this)"><span>{counts['AGREGADO']}</span><small>Agregados</small></button>
        </div>
        <div class="card">
          <h2>Gestión rápida del grupo</h2>
          <p>Usa esta pantalla como lista de control mientras agregas manualmente a madres, padres y tutores desde WhatsApp. No necesitas enviar una invitación desde el sistema.</p>
          <p class="muted"><b>Cómo usarlo:</b> abre el contacto o copia el número, agrégalo desde WhatsApp y cambia su estado a <b>Agregado</b>. Los estados quedan guardados para la próxima vez.</p>
          <label>Nombre sugerido del grupo<input id="groupName" value="Padres y tutores - {escape(core.cfg().grade)} {escape(core.cfg().group)} - {escape(core.cfg().cycle)}"></label><br><br>
          <label>Teléfonos que aún faltan por agregar<textarea id="phones" rows="5" readonly>{escape(numbers_text)}</textarea></label><br>
          <div class="toolbar">
            <button type="button" class="tool-btn" onclick="copyPending(this)">Copiar pendientes</button>
            <a class="wa-main" target="_blank" rel="noopener" href="https://web.whatsapp.com/">Abrir WhatsApp Web</a>
          </div>
        </div>
        <div class="card scroll"><h2>Contactos</h2><table id="waTable"><tr><th>No.</th><th>Alumno / tutor</th><th>Teléfono</th><th>Estado</th><th>Acción rápida</th><th>Actualizar</th></tr>{rows}</table></div>
        {f'<div class="card"><h2>Sin teléfono válido ({len(missing)})</h2><p class="muted">Edita estos alumnos para completar el teléfono del tutor. También aparecen en el conteo del estado correspondiente.</p><ul>{missing_html}</ul></div>' if missing else ''}
        <style>
        .wa-summary{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:18px}}
        .summary-card{{background:white;color:#172033;border:1px solid #e0e7ef;border-radius:14px;padding:14px;box-shadow:0 4px 18px #0000000b;text-align:left}}
        .summary-card span{{display:block;font-size:28px;font-weight:900}}.summary-card small{{font-weight:800;color:#657085}}
        .summary-card.active{{outline:3px solid #1463d633}}.summary-ok span{{color:#16723a}}
        .wa-btn,.wa-main{{display:inline-block;text-decoration:none;border-radius:9px;padding:10px 14px;font-weight:800;white-space:nowrap}}
        .wa-btn{{background:#eaf8ef;color:#16723a}}.wa-main{{background:#1f7a45;color:#fff}}
        .wa-actions,.toolbar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}.copy-btn,.tool-btn{{width:auto;padding:10px 12px}}
        .copy-btn{{background:#eef3f9;color:#27364a}}.phone-link{{font-weight:800;text-decoration:none;color:#1463d6}}
        .status-pill{{display:inline-block;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:900;white-space:nowrap}}
        .status-no{{background:#f1f3f5;color:#495057}}.status-pending{{background:#fff3bf;color:#8a5a00}}.status-ok{{background:#dff6e7;color:#126b35}}
        .state-form{{margin:0;min-width:135px}}.state-form select{{padding:8px}}
        @media(max-width:760px){{.wa-summary{{grid-template-columns:repeat(2,minmax(0,1fr))}}.wa-actions{{min-width:145px}}}}
        </style>
        <script>
        function copyPhone(button){{
          navigator.clipboard.writeText(button.dataset.phone).then(function(){{
            const original=button.textContent; button.textContent='✓ Copiado'; setTimeout(()=>button.textContent=original,1200);
          }});
        }}
        function copyPending(button){{
          navigator.clipboard.writeText(document.getElementById('phones').value).then(function(){{
            const original=button.textContent; button.textContent='✓ Pendientes copiados'; setTimeout(()=>button.textContent=original,1500);
          }});
        }}
        function filterState(state, button){{
          document.querySelectorAll('.summary-card').forEach(x=>x.classList.remove('active')); button.classList.add('active');
          document.querySelectorAll('#waTable tr[data-state]').forEach(function(row){{
            row.style.display=(state==='TODOS'||row.dataset.state===state)?'':'none';
          }});
        }}
        document.addEventListener('DOMContentLoaded',function(){{const first=document.querySelector('.summary-card[data-filter="TODOS"]');if(first)first.classList.add('active');}});
        </script>
        '''
        return core.page('Grupo de WhatsApp', body)

    @app.after_request
    def whatsapp_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if 'href="/whatsapp-group"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/whatsapp-group"><span class="nav-icon">💬</span><span>WhatsApp</span></a>'
            if marker in html:
                html = html.replace(marker, link + marker, 1)
            else:
                marker2 = '<a href="/logout">Salir</a>'
                if marker2 in html:
                    html = html.replace(marker2, '<a href="/whatsapp-group">WhatsApp</a>' + marker2, 1)

        if '<h1>Panel de control</h1>' in html and '/whatsapp-group' not in html.split('<h1>Panel de control</h1>',1)[1][:1800]:
            button = '''<div class="card"><h2>Comunicación con familias</h2><p>Controla qué madres, padres y tutores ya agregaste manualmente a tu grupo de WhatsApp.</p><a href="/whatsapp-group" style="display:inline-block;background:#1f7a45;color:white;text-decoration:none;padding:11px 16px;border-radius:9px;font-weight:800">💬 Gestionar grupo de WhatsApp</a></div>'''
            html = html.replace('</main>', button + '</main>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
