import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from html import escape

from flask import request, redirect, session, flash
from sqlalchemy import UniqueConstraint

import app as core


LEVELS = [
    ('4', 'Sobresaliente'),
    ('3', 'Logro esperado'),
    ('2', 'En desarrollo'),
    ('1', 'Requiere apoyo'),
]


class Rubric(core.db.Model):
    __tablename__ = 'rubric'
    id = core.db.Column(core.db.Integer, primary_key=True)
    activity_id = core.db.Column(core.db.Integer, core.db.ForeignKey('activity.id'), unique=True, nullable=False)
    title = core.db.Column(core.db.String(180), nullable=False)
    purpose = core.db.Column(core.db.Text, default='')
    criteria_json = core.db.Column(core.db.Text, nullable=False, default='[]')
    created_by = core.db.Column(core.db.Integer, core.db.ForeignKey('user.id'), nullable=True)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


class RubricAssessment(core.db.Model):
    __tablename__ = 'rubric_assessment'
    id = core.db.Column(core.db.Integer, primary_key=True)
    rubric_id = core.db.Column(core.db.Integer, core.db.ForeignKey('rubric.id'), nullable=False)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), nullable=False)
    levels_json = core.db.Column(core.db.Text, default='{}', nullable=False)
    total = core.db.Column(core.db.Float, default=0, nullable=False)
    feedback = core.db.Column(core.db.Text, default='')
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint('rubric_id', 'student_id'),)


def _rubric_for(activity_id):
    return Rubric.query.filter_by(activity_id=activity_id).first()


def _criteria(rubric):
    if not rubric:
        return []
    try:
        data = json.loads(rubric.criteria_json or '[]')
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _normalize_criteria(items):
    cleaned = []
    for raw in (items or [])[:6]:
        name = str(raw.get('name', '')).strip()
        if not name:
            continue
        try:
            weight = float(raw.get('weight', 0))
        except Exception:
            weight = 0
        descriptions = raw.get('descriptions') or {}
        cleaned.append({
            'name': name[:160],
            'weight': max(weight, 0),
            'descriptions': {
                '4': str(descriptions.get('4', '')).strip()[:900],
                '3': str(descriptions.get('3', '')).strip()[:900],
                '2': str(descriptions.get('2', '')).strip()[:900],
                '1': str(descriptions.get('1', '')).strip()[:900],
            },
        })
    if not cleaned:
        return []
    total = sum(x['weight'] for x in cleaned)
    if total <= 0:
        each = 100 / len(cleaned)
        for item in cleaned:
            item['weight'] = round(each, 2)
    else:
        for item in cleaned:
            item['weight'] = round(item['weight'] * 100 / total, 2)
    diff = round(100 - sum(x['weight'] for x in cleaned), 2)
    cleaned[-1]['weight'] = round(cleaned[-1]['weight'] + diff, 2)
    return cleaned


def _default_rubric(activity):
    names = [
        ('Comprensión y dominio del aprendizaje', 30),
        ('Aplicación y calidad del producto o desempeño', 30),
        ('Argumentación, comunicación y uso de evidencias', 25),
        ('Proceso de trabajo, autonomía y mejora', 15),
    ]
    criteria = []
    for name, weight in names:
        criteria.append({
            'name': name,
            'weight': weight,
            'descriptions': {
                '4': 'Demuestra el criterio de manera completa, precisa y autónoma; integra evidencias pertinentes y mejora el producto cuando es necesario.',
                '3': 'Demuestra el criterio de forma adecuada y consistente; presenta evidencias suficientes, con errores menores que no afectan el logro principal.',
                '2': 'Demuestra el criterio parcialmente; requiere apoyo para completar, justificar o mejorar aspectos importantes del producto o desempeño.',
                '1': 'Presenta evidencia insuficiente o poco relacionada con el criterio; necesita acompañamiento para comprender y realizar la tarea esperada.',
            },
        })
    return {
        'title': f'Rúbrica analítica · {activity.name}',
        'purpose': 'Valorar de manera analítica, transparente y formativa el desempeño mostrado en la actividad, con criterios observables y retroalimentación para la mejora.',
        'criteria': criteria,
    }


def _extract_response_text(payload):
    if isinstance(payload.get('output_text'), str) and payload.get('output_text').strip():
        return payload['output_text']
    for item in payload.get('output', []) or []:
        for content in item.get('content', []) or []:
            text = content.get('text')
            if isinstance(text, str) and text.strip():
                return text
    return ''


def _generate_with_openai(activity, extra_context=''):
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY no está configurada en Vercel.')

    model = os.getenv('OPENAI_MODEL', 'gpt-5-mini').strip() or 'gpt-5-mini'
    school = core.cfg()
    subject = activity.subject.name if activity.subject else 'Actividad escolar'
    field = activity.subject.field if activity.subject else 'No especificado'

    schema = {
        'type': 'object',
        'additionalProperties': False,
        'required': ['title', 'purpose', 'criteria'],
        'properties': {
            'title': {'type': 'string'},
            'purpose': {'type': 'string'},
            'criteria': {
                'type': 'array',
                'minItems': 3,
                'maxItems': 6,
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['name', 'weight', 'descriptions'],
                    'properties': {
                        'name': {'type': 'string'},
                        'weight': {'type': 'number', 'minimum': 1, 'maximum': 100},
                        'descriptions': {
                            'type': 'object',
                            'additionalProperties': False,
                            'required': ['4', '3', '2', '1'],
                            'properties': {
                                '4': {'type': 'string'},
                                '3': {'type': 'string'},
                                '2': {'type': 'string'},
                                '1': {'type': 'string'},
                            },
                        },
                    },
                },
            },
        },
    }

    system_text = '''Actúa como especialista en evaluación formativa, diseño curricular y elaboración de rúbricas analíticas para educación secundaria y Telesecundaria en México. Diseña rúbricas técnicamente sólidas: criterios observables y alineados con la evidencia de la actividad; niveles de desempeño progresivos, mutuamente distinguibles y descritos con conductas o evidencias verificables; ponderaciones justificadas que sumen 100; lenguaje claro para docentes y estudiantes; evita adjetivos vagos sin evidencia. Usa exactamente cuatro niveles: 4 Sobresaliente, 3 Logro esperado, 2 En desarrollo y 1 Requiere apoyo. La rúbrica debe permitir retroalimentación formativa y una calificación transparente. Devuelve solamente JSON conforme al esquema solicitado.'''
    user_text = f'''Genera una rúbrica analítica profesional para esta actividad escolar.
Escuela: {school.school}
Grado/grupo configurado: {school.grade} {school.group}
Asignatura o disciplina: {subject}
Campo formativo: {field}
Actividad: {activity.name}
Trimestre: {activity.trimester}
Puntaje máximo de la actividad: {activity.max_score}
Contexto adicional del docente: {extra_context or 'Sin contexto adicional.'}

Prioriza entre 4 y 5 criterios. Los descriptores deben explicar qué evidencia concreta observar en el producto o desempeño, no limitarse a decir excelente/bueno/regular. Las ponderaciones deben sumar 100.'''

    body = {
        'model': model,
        'input': [
            {'role': 'system', 'content': [{'type': 'input_text', 'text': system_text}]},
            {'role': 'user', 'content': [{'type': 'input_text', 'text': user_text}]},
        ],
        'text': {
            'format': {
                'type': 'json_schema',
                'name': 'rubric_generation',
                'strict': True,
                'schema': schema,
            }
        },
        'store': False,
    }
    req = urllib.request.Request(
        'https://api.openai.com/v1/responses',
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')[:500]
        raise RuntimeError(f'La IA devolvió un error HTTP {exc.code}: {detail}')
    except Exception as exc:
        raise RuntimeError(f'No fue posible conectar con la IA: {exc}')

    text = _extract_response_text(payload)
    if not text:
        raise RuntimeError('La IA no devolvió una rúbrica utilizable.')
    try:
        result = json.loads(text)
    except Exception:
        raise RuntimeError('La respuesta de la IA no pudo interpretarse como rúbrica estructurada.')
    result['criteria'] = _normalize_criteria(result.get('criteria', []))
    if not result['criteria']:
        raise RuntimeError('La IA no generó criterios válidos.')
    return result


def _save_generated(activity, data):
    rubric = _rubric_for(activity.id)
    if not rubric:
        rubric = Rubric(activity_id=activity.id, created_by=session.get('uid'))
        core.db.session.add(rubric)
    rubric.title = str(data.get('title') or f'Rúbrica · {activity.name}')[:180]
    rubric.purpose = str(data.get('purpose') or '')
    rubric.criteria_json = json.dumps(_normalize_criteria(data.get('criteria', [])), ensure_ascii=False)
    rubric.updated_at = datetime.utcnow()
    core.db.session.commit()
    return rubric


def _score_total(criteria, selected):
    total = 0.0
    for idx, criterion in enumerate(criteria):
        try:
            level = int(selected.get(str(idx), 0))
        except Exception:
            level = 0
        level = min(max(level, 0), 4)
        total += float(criterion.get('weight', 0)) * (level / 4.0)
    return round(total, 2)


def install(app):
    @app.before_request
    def rubric_tables_bootstrap():
        # Son tablas nuevas; db.create_all conserva las existentes y crea estas al importar el módulo.
        core.db.create_all()

    @app.route('/rubrics')
    def rubrics_home():
        r = core.require()
        if r:
            return r
        activities = core.Activity.query.order_by(core.Activity.activity_date.desc()).all()
        rows = ''
        for activity in activities:
            rubric = _rubric_for(activity.id)
            subject = activity.subject.name if activity.subject else '—'
            status = 'Lista para calificar' if rubric else 'Sin rúbrica'
            action = f'<a href="/rubrics/{activity.id}">{"Abrir rúbrica" if rubric else "Crear rúbrica"}</a>'
            rows += f'<tr><td>{escape(str(activity.activity_date))}</td><td><b>{escape(activity.name)}</b><br><small>{escape(subject)} · {escape(activity.trimester)}</small></td><td>{escape(status)}</td><td>{action}</td></tr>'
        if not rows:
            rows = '<tr><td colspan="4">Primero crea una actividad desde Actividades y calificaciones.</td></tr>'
        ai_state = 'IA conectada' if os.getenv('OPENAI_API_KEY') else 'IA pendiente de configurar'
        body = f'''
        <h1>Rúbricas con IA</h1>
        <div class="card"><h2>Evaluación analítica y formativa</h2>
        <p>Selecciona una actividad para generar una rúbrica profesional, editar sus criterios y posteriormente calificar a cada alumno.</p>
        <p class="muted">Estado: <b>{escape(ai_state)}</b>. La generación automática utiliza OpenAI; siempre puedes revisar y editar la rúbrica antes de aplicarla.</p></div>
        <div class="card scroll"><table><tr><th>Fecha</th><th>Actividad</th><th>Rúbrica</th><th>Acción</th></tr>{rows}</table></div>'''
        return core.page('Rúbricas con IA', body)

    @app.route('/rubrics/<int:activity_id>', methods=['GET', 'POST'])
    def rubric_builder(activity_id):
        r = core.require()
        if r:
            return r
        activity = core.db.session.get(core.Activity, activity_id)
        if not activity:
            flash('Actividad no encontrada.')
            return redirect('/rubrics')
        rubric = _rubric_for(activity.id)

        if request.method == 'POST':
            action = request.form.get('action', '')
            if action == 'generate_ai':
                try:
                    data = _generate_with_openai(activity, request.form.get('context', '').strip())
                    _save_generated(activity, data)
                    flash('Rúbrica generada con IA. Revísala y ajústala antes de calificar.')
                except Exception as exc:
                    flash(str(exc))
                return redirect(f'/rubrics/{activity.id}')
            if action == 'create_template':
                _save_generated(activity, _default_rubric(activity))
                flash('Rúbrica base creada. Puedes editar todos sus criterios y descriptores.')
                return redirect(f'/rubrics/{activity.id}')
            if action == 'save_rubric':
                criteria = []
                for idx in range(6):
                    name = request.form.get(f'criterion_{idx}', '').strip()
                    if not name:
                        continue
                    criteria.append({
                        'name': name,
                        'weight': request.form.get(f'weight_{idx}', '0'),
                        'descriptions': {
                            '4': request.form.get(f'desc_{idx}_4', '').strip(),
                            '3': request.form.get(f'desc_{idx}_3', '').strip(),
                            '2': request.form.get(f'desc_{idx}_2', '').strip(),
                            '1': request.form.get(f'desc_{idx}_1', '').strip(),
                        },
                    })
                criteria = _normalize_criteria(criteria)
                if len(criteria) < 2:
                    flash('La rúbrica debe conservar al menos dos criterios.')
                    return redirect(f'/rubrics/{activity.id}')
                if not rubric:
                    rubric = Rubric(activity_id=activity.id, created_by=session.get('uid'))
                    core.db.session.add(rubric)
                rubric.title = request.form.get('title', '').strip()[:180] or f'Rúbrica · {activity.name}'
                rubric.purpose = request.form.get('purpose', '').strip()
                rubric.criteria_json = json.dumps(criteria, ensure_ascii=False)
                rubric.updated_at = datetime.utcnow()
                core.db.session.commit()
                flash('Rúbrica actualizada.')
                return redirect(f'/rubrics/{activity.id}')

        rubric = _rubric_for(activity.id)
        if not rubric:
            ai_button = '<button name="action" value="generate_ai">✨ Generar rúbrica con IA</button>' if os.getenv('OPENAI_API_KEY') else '<button name="action" value="generate_ai">✨ Generar con IA</button>'
            body = f'''
            <h1>Crear rúbrica</h1><div class="card"><h2>{escape(activity.name)}</h2>
            <p>{escape(activity.subject.name if activity.subject else 'Actividad')} · {escape(activity.trimester)} · Puntaje máximo {activity.max_score}</p></div>
            <div class="card"><h2>Generación inteligente</h2><p>La IA construirá criterios observables, cuatro niveles de desempeño progresivos y ponderaciones que suman 100%.</p>
            <form method="post"><label>Contexto adicional para la IA<textarea name="context" rows="5" placeholder="Ejemplo: el producto es una exposición con cartel; deseo valorar investigación, explicación oral, uso de fuentes y trabajo colaborativo."></textarea></label><br><br>{ai_button}</form>
            <hr style="margin:24px 0;border:0;border-top:1px solid #e5e7eb"><form method="post"><button name="action" value="create_template">Crear una rúbrica experta sin IA</button></form>
            <p class="muted" style="margin-top:15px">Si la IA aún no está configurada, la plantilla experta te permite comenzar y editar todo manualmente.</p></div>
            <p><a href="/rubrics">← Volver a Rúbricas</a></p>'''
            return core.page('Crear rúbrica', body)

        criteria = _criteria(rubric)
        editor_rows = ''
        for idx in range(6):
            item = criteria[idx] if idx < len(criteria) else {'name': '', 'weight': '', 'descriptions': {'4':'','3':'','2':'','1':''}}
            desc = item.get('descriptions') or {}
            editor_rows += f'''
            <div class="card" style="border:1px solid #eceff3">
              <div class="grid">
                <label>Criterio {idx + 1}<input name="criterion_{idx}" value="{escape(str(item.get('name','')))}" placeholder="Dejar vacío para no usar"></label>
                <label>Ponderación %<input name="weight_{idx}" type="number" min="0" max="100" step="0.01" value="{escape(str(item.get('weight','')))}"></label>
              </div><br>
              <div class="grid">
                <label>Sobresaliente (4)<textarea name="desc_{idx}_4" rows="4">{escape(str(desc.get('4','')))}</textarea></label>
                <label>Logro esperado (3)<textarea name="desc_{idx}_3" rows="4">{escape(str(desc.get('3','')))}</textarea></label>
                <label>En desarrollo (2)<textarea name="desc_{idx}_2" rows="4">{escape(str(desc.get('2','')))}</textarea></label>
                <label>Requiere apoyo (1)<textarea name="desc_{idx}_1" rows="4">{escape(str(desc.get('1','')))}</textarea></label>
              </div>
            </div>'''
        body = f'''
        <h1>{escape(rubric.title)}</h1>
        <div class="card"><p><b>Actividad:</b> {escape(activity.name)} · <b>Asignatura:</b> {escape(activity.subject.name if activity.subject else '—')}</p>
        <p class="muted">Las ponderaciones se normalizan automáticamente para sumar 100%. Revisa que cada descriptor sea observable y diferente entre niveles.</p>
        <a href="/rubrics/{activity.id}/grade">Calificar grupo con esta rúbrica →</a></div>
        <form method="post">
          <div class="card"><label>Título<input name="title" value="{escape(rubric.title)}" required></label><br><br>
          <label>Propósito de evaluación<textarea name="purpose" rows="4">{escape(rubric.purpose or '')}</textarea></label></div>
          {editor_rows}
          <div class="card"><button name="action" value="save_rubric">Guardar cambios de la rúbrica</button></div>
        </form>
        <div class="card"><h2>Regenerar con IA</h2><form method="post"><label>Indica qué deseas mejorar<textarea name="context" rows="3" placeholder="Ejemplo: haz más específicos los criterios para una exposición oral."></textarea></label><br><br><button name="action" value="generate_ai">Regenerar rúbrica con IA</button></form></div>
        <p><a href="/rubrics">← Volver a Rúbricas</a></p>'''
        return core.page('Editar rúbrica', body)

    @app.route('/rubrics/<int:activity_id>/grade', methods=['GET', 'POST'])
    def rubric_grade(activity_id):
        r = core.require()
        if r:
            return r
        activity = core.db.session.get(core.Activity, activity_id)
        rubric = _rubric_for(activity_id)
        if not activity or not rubric:
            flash('Primero crea una rúbrica para esta actividad.')
            return redirect('/rubrics')
        criteria = _criteria(rubric)
        students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()

        if request.method == 'POST':
            student_id = request.form.get('student_id', type=int)
            student = core.db.session.get(core.Student, student_id)
            if not student:
                flash('Alumno no encontrado.')
                return redirect(f'/rubrics/{activity_id}/grade')
            selected = {}
            for idx in range(len(criteria)):
                selected[str(idx)] = request.form.get(f'level_{idx}', '0')
            total = _score_total(criteria, selected)
            feedback = request.form.get('feedback', '').strip()
            assessment = RubricAssessment.query.filter_by(rubric_id=rubric.id, student_id=student.id).first()
            if not assessment:
                assessment = RubricAssessment(rubric_id=rubric.id, student_id=student.id)
                core.db.session.add(assessment)
            assessment.levels_json = json.dumps(selected, ensure_ascii=False)
            assessment.total = total
            assessment.feedback = feedback
            assessment.updated_at = datetime.utcnow()

            grade = core.Grade.query.filter_by(student_id=student.id, activity_id=activity.id).first()
            if not grade:
                grade = core.Grade(student_id=student.id, activity_id=activity.id)
                core.db.session.add(grade)
            grade.score = round((total / 100.0) * float(activity.max_score or 10), 2)
            grade.code = ''
            core.db.session.commit()
            flash(f'Rúbrica guardada para {student.full_name}. Calificación: {grade.score}/{activity.max_score}.')
            return redirect(f'/rubrics/{activity_id}/grade?student={student.id}')

        selected_student_id = request.args.get('student', type=int)
        if not selected_student_id and students:
            selected_student_id = students[0].id
        student = core.db.session.get(core.Student, selected_student_id) if selected_student_id else None
        student_options = ''.join(f'<option value="{s.id}" {"selected" if student and s.id == student.id else ""}>{s.list_no or ""} · {escape(s.full_name)}</option>' for s in students)
        existing = RubricAssessment.query.filter_by(rubric_id=rubric.id, student_id=student.id).first() if student else None
        previous = {}
        if existing:
            try:
                previous = json.loads(existing.levels_json or '{}')
            except Exception:
                previous = {}

        criterion_blocks = ''
        for idx, criterion in enumerate(criteria):
            options = '<option value="0">Selecciona nivel</option>'
            for value, label in LEVELS:
                selected_attr = 'selected' if str(previous.get(str(idx), '')) == value else ''
                description = (criterion.get('descriptions') or {}).get(value, '')
                options += f'<option value="{value}" {selected_attr}>{value} · {escape(label)}</option>'
            descriptors = ''.join(f'<div style="margin:6px 0"><b>{escape(label)}:</b> {escape(str((criterion.get("descriptions") or {}).get(value, "")))}</div>' for value, label in LEVELS)
            criterion_blocks += f'''
            <div class="card" style="border:1px solid #eceff3"><h3>{escape(str(criterion.get('name','')))} <small>({criterion.get('weight',0)}%)</small></h3>
            <div class="muted" style="margin-bottom:12px">{descriptors}</div>
            <label>Nivel observado<select name="level_{idx}" required>{options}</select></label></div>'''
        feedback = escape(existing.feedback if existing else '')
        current_total = f'{existing.total:.2f}%' if existing else 'Sin evaluar'
        body = f'''
        <h1>Calificar con rúbrica</h1>
        <div class="card"><h2>{escape(activity.name)}</h2><p>{escape(rubric.title)} · Resultado actual: <b>{current_total}</b></p>
        <form method="get"><label>Alumno<select name="student" onchange="this.form.submit()">{student_options}</select></label></form></div>
        {('<form method="post"><input type="hidden" name="student_id" value="'+str(student.id)+'">'+criterion_blocks+'<div class="card"><label>Retroalimentación formativa<textarea name="feedback" rows="5" placeholder="Fortalezas, aspectos por mejorar y siguiente paso concreto.">'+feedback+'</textarea></label><br><br><button>Guardar evaluación y pasar calificación a la actividad</button></div></form>') if student else '<div class="card">No hay alumnos activos.</div>'}
        <p><a href="/rubrics/{activity.id}">← Editar rúbrica</a> · <a href="/rubrics">Ver todas las rúbricas</a></p>'''
        return core.page('Calificar con rúbrica', body)

    @app.after_request
    def rubric_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        if not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if request.path == '/' and 'href="/rubrics"' not in html:
            marker = '<div class="quick">'
            card = '<a href="/rubrics"><span class="quick-icon">▦</span><span>Rúbricas con IA</span></a>'
            if marker in html:
                html = html.replace(marker, marker + card, 1)
        if request.path.startswith('/activities') and 'Rúbricas con IA' not in html:
            html = html.replace('<h1>Actividades', '<div style="float:right"><a href="/rubrics">▦ Rúbricas con IA</a></div><h1>Actividades', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
