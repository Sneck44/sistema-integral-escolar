from html import escape
from flask import request, redirect, session, flash

import app as core


RITMOS = ['RÁPIDO', 'MODERADO', 'PAUSADO', 'VARIABLE', 'POR DETERMINAR']
ESTILOS = ['ACTIVO', 'REFLEXIVO', 'TEÓRICO', 'PRAGMÁTICO', 'MULTIMODAL', 'POR DETERMINAR']
CANALES = ['VISUAL', 'AUDITIVO', 'CINESTÉSICO', 'VISUAL-AUDITIVO', 'VISUAL-CINESTÉSICO', 'AUDITIVO-CINESTÉSICO', 'MULTIMODAL', 'POR DETERMINAR']
NIVELES = ['REQUIERE APOYO', 'EN DESARROLLO', 'ESPERADO', 'DESTACADO', 'POR DETERMINAR']


class StudentDiagnostic(core.db.Model):
    __tablename__ = 'student_diagnostic'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), unique=True, nullable=False)
    diagnostic_score = core.db.Column(core.db.Float, nullable=True)
    learning_pace = core.db.Column(core.db.String(40), default='POR DETERMINAR')
    learning_style = core.db.Column(core.db.String(50), default='POR DETERMINAR')
    perception_channel = core.db.Column(core.db.String(60), default='POR DETERMINAR')
    performance_level = core.db.Column(core.db.String(40), default='POR DETERMINAR')
    strengths = core.db.Column(core.db.Text, default='')
    support_needs = core.db.Column(core.db.Text, default='')
    observations = core.db.Column(core.db.Text, default='')


def get_diagnostic(student_id):
    return StudentDiagnostic.query.filter_by(student_id=student_id).first()


def _select(name, values, selected, student_id):
    opts = ''.join(
        f'<option value="{escape(v)}" {"selected" if v == selected else ""}>{escape(v.title())}</option>'
        for v in values
    )
    return f'<select name="{name}_{student_id}">{opts}</select>'


def _score(value):
    if value in (None, ''):
        return None
    try:
        x = float(str(value).replace(',', '.'))
        return max(0, min(10, x))
    except Exception:
        return None


def install(app):
    @app.route('/diagnostic', methods=['GET', 'POST'])
    def diagnostic():
        if not session.get('uid'):
            return redirect('/login')

        students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()

        if request.method == 'POST':
            for s in students:
                d = get_diagnostic(s.id)
                if not d:
                    d = StudentDiagnostic(student_id=s.id)
                    core.db.session.add(d)
                d.diagnostic_score = _score(request.form.get(f'score_{s.id}'))
                d.learning_pace = request.form.get(f'pace_{s.id}', 'POR DETERMINAR')
                d.learning_style = request.form.get(f'style_{s.id}', 'POR DETERMINAR')
                d.perception_channel = request.form.get(f'channel_{s.id}', 'POR DETERMINAR')
                d.performance_level = request.form.get(f'level_{s.id}', 'POR DETERMINAR')
                d.strengths = request.form.get(f'strengths_{s.id}', '').strip()
                d.support_needs = request.form.get(f'support_{s.id}', '').strip()
                d.observations = request.form.get(f'obs_{s.id}', '').strip()
            core.db.session.commit()
            flash('Diagnóstico del grupo guardado correctamente.')
            return redirect('/diagnostic')

        rows = ''
        scores = []
        completed = 0
        for s in students:
            d = get_diagnostic(s.id)
            if d and d.diagnostic_score is not None:
                scores.append(d.diagnostic_score)
                completed += 1
            rows += f'''<tr>
              <td>{escape(str(s.list_no or ''))}</td>
              <td style="min-width:180px"><b>{escape(s.full_name)}</b></td>
              <td><input name="score_{s.id}" type="number" min="0" max="10" step="0.1" value="{'' if not d or d.diagnostic_score is None else d.diagnostic_score}" style="min-width:75px"></td>
              <td>{_select('pace', RITMOS, d.learning_pace if d else 'POR DETERMINAR', s.id)}</td>
              <td>{_select('style', ESTILOS, d.learning_style if d else 'POR DETERMINAR', s.id)}</td>
              <td>{_select('channel', CANALES, d.perception_channel if d else 'POR DETERMINAR', s.id)}</td>
              <td>{_select('level', NIVELES, d.performance_level if d else 'POR DETERMINAR', s.id)}</td>
              <td><textarea name="strengths_{s.id}" rows="2" style="min-width:190px">{escape(d.strengths if d else '')}</textarea></td>
              <td><textarea name="support_{s.id}" rows="2" style="min-width:190px">{escape(d.support_needs if d else '')}</textarea></td>
              <td><textarea name="obs_{s.id}" rows="2" style="min-width:190px">{escape(d.observations if d else '')}</textarea></td>
            </tr>'''

        average = round(sum(scores) / len(scores), 2) if scores else '—'
        body = f'''
        <h1>Diagnóstico del grupo</h1>
        <div class="grid">
          <div class="card"><div class="muted">Alumnos activos</div><div class="kpi">{len(students)}</div></div>
          <div class="card"><div class="muted">Con calificación diagnóstica</div><div class="kpi">{completed}</div></div>
          <div class="card"><div class="muted">Promedio diagnóstico</div><div class="kpi">{average}</div></div>
        </div>
        <div class="card">
          <h2>Registro rápido</h2>
          <p class="muted">Captura la calificación diagnóstica de 0 a 10 y selecciona ritmo, estilo y canal de percepción. Las categorías son orientativas y pueden actualizarse cuando cuentes con nueva evidencia del alumno.</p>
          <form method="post">
            <div class="scroll"><table>
              <tr><th>No.</th><th>Alumno</th><th>Calificación</th><th>Ritmo</th><th>Estilo</th><th>Canal de percepción</th><th>Nivel</th><th>Fortalezas</th><th>Necesidades de apoyo</th><th>Observaciones</th></tr>
              {rows}
            </table></div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px">
              <button style="width:auto">Guardar diagnóstico</button>
              <a href="/exports/diagnostic.xlsx" style="display:inline-block;padding:10px 14px;border-radius:8px;background:#217346;color:white;text-decoration:none;font-weight:700">Exportar diagnóstico a Excel</a>
            </div>
          </form>
        </div>'''
        return core.page('Diagnóstico', body)

    @app.after_request
    def diagnostic_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if 'href="/diagnostic"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/diagnostic"><span class="nav-icon">🧭</span><span>Diagnóstico</span></a>'
            if marker in html:
                html = html.replace(marker, link + marker, 1)
            else:
                marker2 = '<a href="/logout">Salir</a>'
                if marker2 in html:
                    html = html.replace(marker2, '<a href="/diagnostic">Diagnóstico</a>' + marker2, 1)
        if '<h1>Panel de control</h1>' in html and 'Diagnóstico del grupo' not in html:
            card = '''<div class="card"><h2>🧭 Diagnóstico del grupo</h2><p>Registra calificación diagnóstica, ritmos, estilos de aprendizaje, canales de percepción, fortalezas y necesidades de apoyo.</p><a href="/diagnostic" style="display:inline-block;background:#7b1024;color:#fff;text-decoration:none;padding:11px 16px;border-radius:9px;font-weight:800">Abrir Diagnóstico</a></div>'''
            html = html.replace('</main>', card + '</main>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
