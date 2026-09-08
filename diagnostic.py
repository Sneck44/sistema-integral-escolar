from html import escape
from flask import request, redirect, session, flash

import app as core


ESTILOS = ['ACOMODADOR', 'DIVERGENTE', 'CONVERGENTE', 'ASIMILADOR', 'POR DETERMINAR']
CANALES = ['VISUAL', 'AUDITIVO', 'CINESTÉSICO', 'VISUAL-AUDITIVO', 'VISUAL-CINESTÉSICO', 'AUDITIVO-CINESTÉSICO', 'MULTIMODAL', 'POR DETERMINAR']
NIVELES = ['REQUIERE APOYO', 'EN DESARROLLO', 'ESPERADO', 'DESTACADO', 'POR DETERMINAR']

SUBJECTS_BY_GRADE = {
    '1': ['Español', 'Inglés', 'Artes', 'Matemáticas', 'Biología', 'Geografía', 'Historia', 'Formación Cívica y Ética', 'Tecnología', 'Educación Física'],
    '2': ['Español', 'Inglés', 'Artes', 'Matemáticas', 'Física', 'Historia', 'Formación Cívica y Ética', 'Tecnología', 'Educación Física'],
    '3': ['Español', 'Inglés', 'Artes', 'Matemáticas', 'Química', 'Historia', 'Formación Cívica y Ética', 'Tecnología', 'Educación Física'],
}

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
    learning_pace = core.db.Column(core.db.String(40), default='POR DETERMINAR')
    learning_style = core.db.Column(core.db.String(50), default='POR DETERMINAR')
    perception_channel = core.db.Column(core.db.String(60), default='POR DETERMINAR')
    performance_level = core.db.Column(core.db.String(40), default='POR DETERMINAR')
    strengths = core.db.Column(core.db.Text, default='')
    support_needs = core.db.Column(core.db.Text, default='')
    observations = core.db.Column(core.db.Text, default='')


class DiagnosticSubjectGrade(core.db.Model):
    __tablename__ = 'diagnostic_subject_grade'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), nullable=False, index=True)
    grade_level = core.db.Column(core.db.String(4), nullable=False, index=True)
    subject_name = core.db.Column(core.db.String(120), nullable=False)
    score = core.db.Column(core.db.Float, nullable=True)
    __table_args__ = (
        core.db.UniqueConstraint('student_id', 'grade_level', 'subject_name', name='uq_diag_subject_student_grade'),
    )


def get_diagnostic(student_id):
    return StudentDiagnostic.query.filter_by(student_id=student_id).first()


def _active_grade_key():
    try:
        import group_workspaces
        grade, _ = group_workspaces.active_group_tuple()
        digits = ''.join(ch for ch in str(grade) if ch.isdigit())
        if digits in SUBJECTS_BY_GRADE:
            return digits
    except Exception:
        pass
    try:
        digits = ''.join(ch for ch in str(core.cfg().grade) if ch.isdigit())
        if digits in SUBJECTS_BY_GRADE:
            return digits
    except Exception:
        pass
    return '1'


def _subjects_for_active_grade():
    return SUBJECTS_BY_GRADE.get(_active_grade_key(), SUBJECTS_BY_GRADE['1'])


def _subject_grade(student_id, grade_key, subject_name):
    return DiagnosticSubjectGrade.query.filter_by(
        student_id=student_id,
        grade_level=grade_key,
        subject_name=subject_name,
    ).first()


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


def _student_subject_average(student_id, grade_key, subjects):
    values = []
    for subject_name in subjects:
        row = _subject_grade(student_id, grade_key, subject_name)
        if row and row.score is not None:
            values.append(row.score)
    return round(sum(values) / len(values), 2) if values else None


def _style_info(style):
    return ESTILO_INFO.get(style or 'POR DETERMINAR', ESTILO_INFO['POR DETERMINAR'])


def _channel_tip(channel):
    return CANAL_SUGERENCIAS.get(channel or 'POR DETERMINAR', CANAL_SUGERENCIAS['POR DETERMINAR'])


def install(app):
    @app.route('/diagnostic', methods=['GET', 'POST'])
    def diagnostic():
        if not session.get('uid'):
            return redirect('/login')

        grade_key = _active_grade_key()
        subjects = _subjects_for_active_grade()
        students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()

        if request.method == 'POST':
            for s in students:
                d = get_diagnostic(s.id)
                if not d:
                    d = StudentDiagnostic(student_id=s.id)
                    core.db.session.add(d)

                captured = []
                for subject_name in subjects:
                    field_name = f'subject_{s.id}_{subjects.index(subject_name)}'
                    value = _score(request.form.get(field_name))
                    row = _subject_grade(s.id, grade_key, subject_name)
                    if not row:
                        row = DiagnosticSubjectGrade(
                            student_id=s.id,
                            grade_level=grade_key,
                            subject_name=subject_name,
                        )
                        core.db.session.add(row)
                    row.score = value
                    if value is not None:
                        captured.append(value)

                d.diagnostic_score = round(sum(captured) / len(captured), 2) if captured else _score(request.form.get(f'score_{s.id}'))
                d.learning_style = request.form.get(f'style_{s.id}', 'POR DETERMINAR')
                d.perception_channel = request.form.get(f'channel_{s.id}', 'POR DETERMINAR')
                d.performance_level = request.form.get(f'level_{s.id}', 'POR DETERMINAR')
                d.strengths = request.form.get(f'strengths_{s.id}', '').strip()
                d.support_needs = request.form.get(f'support_{s.id}', '').strip()
                d.observations = request.form.get(f'obs_{s.id}', '').strip()

            core.db.session.commit()
            flash(f'Diagnóstico de {grade_key}.º guardado correctamente. El promedio general se calculó con las asignaturas capturadas.')
            return redirect('/diagnostic')

        rows = ''
        result_rows = ''
        scores = []
        completed = 0
        subject_totals = {name: [] for name in subjects}

        subject_headers = ''.join(f'<th class="subject-head">{escape(name)}</th>' for name in subjects)

        for s in students:
            d = get_diagnostic(s.id)
            subject_cells = ''
            student_values = []
            for idx, subject_name in enumerate(subjects):
                sg = _subject_grade(s.id, grade_key, subject_name)
                value = sg.score if sg and sg.score is not None else None
                if value is not None:
                    student_values.append(value)
                    subject_totals[subject_name].append(value)
                shown = '' if value is None else f'{value:g}'
                subject_cells += (
                    f'<td class="subject-score"><input name="subject_{s.id}_{idx}" type="number" '
                    f'min="0" max="10" step="0.1" value="{shown}" aria-label="{escape(subject_name)} de {escape(s.full_name)}"></td>'
                )

            calculated = round(sum(student_values) / len(student_values), 2) if student_values else (d.diagnostic_score if d else None)
            if calculated is not None:
                scores.append(calculated)
                completed += 1

            style = d.learning_style if d and d.learning_style in ESTILOS else 'POR DETERMINAR'
            channel = d.perception_channel if d and d.perception_channel in CANALES else 'POR DETERMINAR'
            description, style_tip = _style_info(style)
            channel_tip = _channel_tip(channel)

            rows += f'''<tr>
              <td class="sticky-no">{escape(str(s.list_no or ''))}</td>
              <td class="sticky-name"><b>{escape(s.full_name)}</b></td>
              {subject_cells}
              <td class="diag-average"><b>{'—' if calculated is None else calculated}</b><input type="hidden" name="score_{s.id}" value="{'' if calculated is None else calculated}"></td>
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
              <td><b>{'—' if calculated is None else calculated}</b></td>
              <td><span class="diag-chip">{escape(style.title())}</span></td>
              <td class="diag-text">{escape(description)}</td>
              <td><span class="diag-chip gold">{escape(channel.title())}</span></td>
              <td class="diag-text"><b>Por estilo:</b> {escape(style_tip)}<br><br><b>Por canal:</b> {escape(channel_tip)}</td>
            </tr>'''

        average = round(sum(scores) / len(scores), 2) if scores else '—'
        subject_cards = ''.join(
            f'<div class="subject-kpi"><span>{escape(name)}</span><b>{round(sum(vals)/len(vals),2) if vals else "—"}</b></div>'
            for name, vals in subject_totals.items()
        )

        body = f'''
        <h1>Diagnóstico del grupo · {grade_key}.º</h1>
        <div class="grid">
          <div class="card"><div class="muted">Alumnos activos</div><div class="kpi">{len(students)}</div></div>
          <div class="card"><div class="muted">Con diagnóstico académico</div><div class="kpi">{completed}</div></div>
          <div class="card"><div class="muted">Promedio diagnóstico del grupo</div><div class="kpi">{average}</div></div>
        </div>

        <div class="card">
          <h2>Promedio diagnóstico por asignatura</h2>
          <p class="muted">Los promedios se actualizan con las calificaciones capturadas para el grado activo.</p>
          <div class="subject-summary">{subject_cards}</div>
        </div>

        <div class="card">
          <h2>Registro diagnóstico por asignatura</h2>
          <p class="muted">Captura de 0 a 10 únicamente las asignaturas evaluadas. El promedio diagnóstico de cada alumno se calcula automáticamente con las calificaciones disponibles. Las asignaturas cambian al seleccionar otro grado o grupo.</p>
          <form method="post">
            <div class="scroll diag-table-wrap"><table class="diag-entry-table">
              <tr><th class="sticky-no">No.</th><th class="sticky-name">Alumno</th>{subject_headers}<th>Promedio</th><th>Estilo</th><th>Canal de percepción</th><th>Nivel</th><th>Fortalezas</th><th>Necesidades de apoyo</th><th>Observaciones</th></tr>
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
          <p class="muted">El promedio académico se complementa con estilo, canal de percepción, fortalezas y necesidades de apoyo para orientar la planeación docente sin convertir estas categorías en etiquetas fijas.</p>
          <div class="scroll"><table>
            <tr><th>No.</th><th>Alumno</th><th>Promedio</th><th>Estilo</th><th>Descripción del estilo</th><th>Canal</th><th>Sugerencias para trabajar con el alumno</th></tr>
            {result_rows}
          </table></div>
        </div>
        <style>
          .diag-results{{margin-top:18px}}.diag-results table{{min-width:1240px}}.diag-results th{{vertical-align:middle}}.diag-text{{min-width:280px;line-height:1.48;font-size:12px}}.diag-chip{{display:inline-flex;padding:6px 10px;border-radius:999px;background:#f3e7ea;color:#7b1024;font-size:11px;font-weight:800;white-space:nowrap}}.diag-chip.gold{{background:#fff4dc;color:#7b5a19}}
          .subject-summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}.subject-kpi{{border:1px solid #eee3e6;border-radius:12px;padding:11px;background:#fffaf8}}.subject-kpi span{{display:block;font-size:11px;color:#746a6d;min-height:30px}}.subject-kpi b{{display:block;font-size:23px;color:#7b1024;margin-top:4px}}
          .diag-entry-table{{min-width:2050px}}.subject-head{{min-width:112px;text-align:center}}.subject-score{{min-width:112px}}.subject-score input{{min-width:82px;text-align:center;font-weight:750}}.diag-average{{min-width:90px;text-align:center;background:#fff8e8}}.sticky-no{{position:sticky;left:0;z-index:3;background:#fff;min-width:58px}}.sticky-name{{position:sticky;left:58px;z-index:3;background:#fff;min-width:210px;box-shadow:3px 0 5px rgba(0,0,0,.04)}}
          @media(max-width:720px){{.diag-entry-table{{font-size:12px}}.sticky-name{{min-width:170px}}}}
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
            card = '''<div class="card"><h2>Diagnóstico del grupo</h2><p>Registra calificaciones diagnósticas por asignatura, estilos de aprendizaje, canales de percepción, fortalezas y necesidades de apoyo.</p><a href="/diagnostic" style="display:inline-block;background:#7b1024;color:#fff;text-decoration:none;padding:11px 16px;border-radius:9px;font-weight:800">Abrir Diagnóstico</a></div>'''
            html = html.replace('</main>', card + '</main>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
