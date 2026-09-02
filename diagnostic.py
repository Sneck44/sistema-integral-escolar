from html import escape
from flask import request, redirect, session, flash

import app as core


ESTILOS = ['ACOMODADOR', 'DIVERGENTE', 'CONVERGENTE', 'ASIMILADOR', 'POR DETERMINAR']
CANALES = ['VISUAL', 'AUDITIVO', 'CINESTÉSICO', 'VISUAL-AUDITIVO', 'VISUAL-CINESTÉSICO', 'AUDITIVO-CINESTÉSICO', 'MULTIMODAL', 'POR DETERMINAR']
NIVELES = ['REQUIERE APOYO', 'EN DESARROLLO', 'ESPERADO', 'DESTACADO', 'POR DETERMINAR']

ESTILO_INFO = {
    'ACOMODADOR': (
        'Aprende especialmente mediante la experiencia concreta y la experimentación activa; suele involucrarse, probar, adaptarse y resolver situaciones prácticas.',
        'Priorizar proyectos, retos prácticos, experimentos, dramatizaciones, trabajo de campo, construcción de productos y actividades donde pueda aprender haciendo.'
    ),
    'DIVERGENTE': (
        'Tiende a observar las situaciones desde distintas perspectivas, relacionar experiencias, generar alternativas y reflexionar antes de llegar a conclusiones.',
        'Usar lluvia de ideas, análisis de casos, preguntas abiertas, diarios de reflexión, debates, interpretación de imágenes y actividades creativas con varias respuestas posibles.'
    ),
    'CONVERGENTE': (
        'Se orienta a aplicar ideas y conceptos para encontrar soluciones concretas; suele desenvolverse bien ante problemas con una meta o respuesta práctica.',
        'Plantear resolución de problemas, desafíos, estudios de caso, ejercicios de aplicación, prototipos, simulaciones y tareas que permitan comprobar una solución.'
    ),
    'ASIMILADOR': (
        'Prefiere organizar y comprender información de manera lógica, integrar datos en explicaciones coherentes y construir modelos o conceptos.',
        'Ofrecer esquemas, mapas conceptuales, lecturas guiadas, organizadores gráficos, explicaciones estructuradas, comparación de conceptos y oportunidades para sintetizar información.'
    ),
    'POR DETERMINAR': (
        'Aún no se cuenta con evidencia suficiente para identificar una preferencia de aprendizaje.',
        'Observar al alumno en actividades variadas y ofrecer experiencias prácticas, visuales, orales, reflexivas y de resolución de problemas antes de establecer una preferencia.'
    ),
}

CANAL_SUGERENCIAS = {
    'VISUAL': 'Apoyar con mapas, diagramas, líneas del tiempo, imágenes, demostraciones, códigos visuales, palabras clave y organizadores gráficos.',
    'AUDITIVO': 'Incluir explicaciones orales, diálogo, lectura en voz alta, debates, exposiciones, instrucciones verbalizadas y oportunidades para explicar lo aprendido.',
    'CINESTÉSICO': 'Incorporar manipulación de materiales, movimiento, experimentos, modelos, dramatizaciones, estaciones de trabajo y actividades prácticas.',
    'VISUAL-AUDITIVO': 'Combinar apoyos gráficos y demostraciones con explicación oral, diálogo, lectura comentada y exposición de ideas.',
    'VISUAL-CINESTÉSICO': 'Combinar imágenes, esquemas y demostraciones con manipulación, construcción, movimiento y experiencias prácticas.',
    'AUDITIVO-CINESTÉSICO': 'Combinar explicación y discusión oral con experimentación, movimiento, dramatización, manipulación y aprendizaje práctico.',
    'MULTIMODAL': 'Variar deliberadamente recursos visuales, auditivos y prácticos, permitiendo al alumno elegir y combinar formas de acceso y expresión.',
    'POR DETERMINAR': 'Presentar la información mediante varios canales y observar con cuáles recursos el alumno comprende, participa y comunica mejor lo aprendido.',
}


class StudentDiagnostic(core.db.Model):
    __tablename__ = 'student_diagnostic'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), unique=True, nullable=False)
    diagnostic_score = core.db.Column(core.db.Float, nullable=True)
    # Se conserva la columna anterior solo por compatibilidad con la base de datos.
    # Ya no se captura ni se muestra como parte del diagnóstico.
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


def _style_info(style):
    return ESTILO_INFO.get(style or 'POR DETERMINAR', ESTILO_INFO['POR DETERMINAR'])


def _channel_tip(channel):
    return CANAL_SUGERENCIAS.get(channel or 'POR DETERMINAR', CANAL_SUGERENCIAS['POR DETERMINAR'])


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
        result_rows = ''
        scores = []
        completed = 0
        for s in students:
            d = get_diagnostic(s.id)
            if d and d.diagnostic_score is not None:
                scores.append(d.diagnostic_score)
                completed += 1
            style = d.learning_style if d and d.learning_style in ESTILOS else 'POR DETERMINAR'
            channel = d.perception_channel if d and d.perception_channel in CANALES else 'POR DETERMINAR'
            description, style_tip = _style_info(style)
            channel_tip = _channel_tip(channel)
            rows += f'''<tr>
              <td>{escape(str(s.list_no or ''))}</td>
              <td style="min-width:180px"><b>{escape(s.full_name)}</b></td>
              <td><input name="score_{s.id}" type="number" min="0" max="10" step="0.1" value="{'' if not d or d.diagnostic_score is None else d.diagnostic_score}" style="min-width:75px"></td>
              <td>{_select('style', ESTILOS, style, s.id)}</td>
              <td>{_select('channel', CANALES, channel, s.id)}</td>
              <td>{_select('level', NIVELES, d.performance_level if d else 'POR DETERMINAR', s.id)}</td>
              <td><textarea name="strengths_{s.id}" rows="2" style="min-width:190px">{escape(d.strengths if d else '')}</textarea></td>
              <td><textarea name="support_{s.id}" rows="2" style="min-width:190px">{escape(d.support_needs if d else '')}</textarea></td>
              <td><textarea name="obs_{s.id}" rows="2" style="min-width:190px">{escape(d.observations if d else '')}</textarea></td>
            </tr>'''
            result_rows += f'''<tr>
              <td>{escape(str(s.list_no or ''))}</td>
              <td><b>{escape(s.full_name)}</b></td>
              <td><span class="diag-chip">{escape(style.title())}</span></td>
              <td class="diag-text">{escape(description)}</td>
              <td><span class="diag-chip gold">{escape(channel.title())}</span></td>
              <td class="diag-text"><b>Por estilo:</b> {escape(style_tip)}<br><br><b>Por canal:</b> {escape(channel_tip)}</td>
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
          <p class="muted">Captura la calificación diagnóstica y selecciona el estilo de aprendizaje y canal de percepción observado. Estas categorías funcionan como referentes pedagógicos y pueden actualizarse conforme se reúna nueva evidencia del alumno.</p>
          <form method="post">
            <div class="scroll"><table>
              <tr><th>No.</th><th>Alumno</th><th>Calificación</th><th>Estilo</th><th>Canal de percepción</th><th>Nivel</th><th>Fortalezas</th><th>Necesidades de apoyo</th><th>Observaciones</th></tr>
              {rows}
            </table></div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px">
              <button style="width:auto">Guardar diagnóstico</button>
              <a href="/exports/diagnostic.xlsx" style="display:inline-block;padding:10px 14px;border-radius:8px;background:#217346;color:white;text-decoration:none;font-weight:700">Exportar diagnóstico a Excel</a>
            </div>
          </form>
        </div>
        <div class="card diag-results">
          <h2>Resultados y orientaciones para la intervención docente</h2>
          <p class="muted">La tabla relaciona el estilo registrado y el canal de percepción con orientaciones prácticas para diversificar las actividades. Se recomienda utilizarlas como apoyo para la planeación, no como etiquetas fijas del alumnado.</p>
          <div class="scroll"><table>
            <tr><th>No.</th><th>Alumno</th><th>Estilo</th><th>Descripción del estilo</th><th>Canal</th><th>Sugerencias para trabajar con el alumno</th></tr>
            {result_rows}
          </table></div>
        </div>
        <style>
          .diag-results{{margin-top:18px}}.diag-results table{{min-width:1180px}}.diag-results th{{vertical-align:middle}}.diag-text{{min-width:280px;line-height:1.48;font-size:12px}}.diag-chip{{display:inline-flex;padding:6px 10px;border-radius:999px;background:#f3e7ea;color:#7b1024;font-size:11px;font-weight:800;white-space:nowrap}}.diag-chip.gold{{background:#fff4dc;color:#7b5a19}}
        </style>'''
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
            card = '''<div class="card"><h2>Diagnóstico del grupo</h2><p>Registra calificación diagnóstica, estilos de aprendizaje, canales de percepción, fortalezas y necesidades de apoyo.</p><a href="/diagnostic" style="display:inline-block;background:#7b1024;color:#fff;text-decoration:none;padding:11px 16px;border-radius:9px;font-weight:800">Abrir Diagnóstico</a></div>'''
            html = html.replace('</main>', card + '</main>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
