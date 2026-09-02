import os, json, urllib.request, urllib.error
from datetime import datetime
from html import escape
from flask import request, redirect, session, flash
from sqlalchemy import UniqueConstraint

import app as core


class Rubric(core.db.Model):
    __tablename__ = 'rubric'
    id = core.db.Column(core.db.Integer, primary_key=True)
    activity_id = core.db.Column(core.db.Integer, core.db.ForeignKey('activity.id'), nullable=False, unique=True)
    title = core.db.Column(core.db.String(180), nullable=False)
    purpose = core.db.Column(core.db.Text, default='')
    product = core.db.Column(core.db.String(220), default='')
    criteria_json = core.db.Column(core.db.Text, nullable=False)
    ai_model = core.db.Column(core.db.String(80), default='')
    created_by = core.db.Column(core.db.Integer, nullable=True)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    activity = core.db.relationship('Activity')


class RubricAssessment(core.db.Model):
    __tablename__ = 'rubric_assessment'
    id = core.db.Column(core.db.Integer, primary_key=True)
    rubric_id = core.db.Column(core.db.Integer, core.db.ForeignKey('rubric.id'), nullable=False)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), nullable=False)
    details_json = core.db.Column(core.db.Text, nullable=False)
    percentage = core.db.Column(core.db.Float, default=0)
    final_score = core.db.Column(core.db.Float, default=0)
    feedback = core.db.Column(core.db.Text, default='')
    ai_assisted = core.db.Column(core.db.Boolean, default=False)
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint('rubric_id', 'student_id', name='uq_rubric_student'),)


def _rubric_data(rubric):
    try:
        return json.loads(rubric.criteria_json)
    except Exception:
        return {'criteria': []}


def _api_text(payload):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('OPENAI_API_KEY no está configurada en Vercel.')
    req = urllib.request.Request(
        'https://api.openai.com/v1/responses',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=55) as res:
            data = json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='ignore')[:800]
        raise RuntimeError(f'La IA respondió con error {e.code}: {detail}')
    except Exception as e:
        raise RuntimeError(f'No fue posible conectar con la IA: {e}')
    if data.get('output_text'):
        return data['output_text']
    for item in data.get('output', []):
        for content in item.get('content', []):
            if content.get('type') == 'output_text' and content.get('text'):
                return content['text']
    raise RuntimeError('La IA no devolvió contenido utilizable.')


def _ai_json(system_text, user_text, schema, schema_name):
    model = os.getenv('OPENAI_MODEL', 'gpt-5.6-terra')
    payload = {
        'model': model,
        'input': [
            {'role': 'system', 'content': [{'type': 'input_text', 'text': system_text}]},
            {'role': 'user', 'content': [{'type': 'input_text', 'text': user_text}]},
        ],
        'text': {
            'format': {
                'type': 'json_schema',
                'name': schema_name,
                'strict': True,
                'schema': schema,
            }
        },
    }
    raw = _api_text(payload)
    return json.loads(raw), model


def _rubric_schema():
    level = {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'level': {'type': 'integer', 'enum': [1, 2, 3, 4]},
            'label': {'type': 'string'},
            'descriptor': {'type': 'string'},
        },
        'required': ['level', 'label', 'descriptor'],
    }
    criterion = {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'name': {'type': 'string'},
            'weight': {'type': 'number'},
            'levels': {'type': 'array', 'minItems': 4, 'maxItems': 4, 'items': level},
        },
        'required': ['name', 'weight', 'levels'],
    }
    return {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'title': {'type': 'string'},
            'criteria': {'type': 'array', 'minItems': 4, 'maxItems': 6, 'items': criterion},
            'feedback_focus': {'type': 'string'},
        },
        'required': ['title', 'criteria', 'feedback_focus'],
    }


def _grade_schema(criteria_count):
    item = {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'criterion_index': {'type': 'integer', 'minimum': 0, 'maximum': max(criteria_count - 1, 0)},
            'level': {'type': 'integer', 'enum': [1, 2, 3, 4]},
            'reason': {'type': 'string'},
        },
        'required': ['criterion_index', 'level', 'reason'],
    }
    return {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'scores': {'type': 'array', 'minItems': criteria_count, 'maxItems': criteria_count, 'items': item},
            'feedback': {'type': 'string'},
        },
        'required': ['scores', 'feedback'],
    }


def _normalize_weights(data):
    criteria = data.get('criteria', [])
    total = sum(max(float(c.get('weight') or 0), 0) for c in criteria)
    if not criteria:
        return data
    if total <= 0:
        each = 100.0 / len(criteria)
        for c in criteria: c['weight'] = round(each, 2)
    elif abs(total - 100) > 0.01:
        running = 0
        for i, c in enumerate(criteria):
            if i == len(criteria) - 1:
                c['weight'] = round(100 - running, 2)
            else:
                c['weight'] = round(float(c.get('weight') or 0) * 100 / total, 2)
                running += c['weight']
    for c in criteria:
        c['levels'] = sorted(c.get('levels', []), key=lambda x: x.get('level', 0), reverse=True)
    return data


def _compute(data, selections):
    pct = 0.0
    for i, c in enumerate(data.get('criteria', [])):
        level = int(selections.get(str(i), 1))
        level = min(4, max(1, level))
        pct += float(c.get('weight') or 0) * level / 4.0
    return round(pct, 2)


def _save_assessment(rubric, student, selections, feedback, ai_assisted=False):
    data = _rubric_data(rubric)
    pct = _compute(data, selections)
    max_score = float(rubric.activity.max_score or 10)
    final = round(pct / 100 * max_score, 2)
    assessment = RubricAssessment.query.filter_by(rubric_id=rubric.id, student_id=student.id).first()
    if not assessment:
        assessment = RubricAssessment(rubric_id=rubric.id, student_id=student.id, details_json='{}')
    assessment.details_json = json.dumps(selections, ensure_ascii=False)
    assessment.percentage = pct
    assessment.final_score = final
    assessment.feedback = feedback
    assessment.ai_assisted = ai_assisted
    assessment.updated_at = datetime.utcnow()
    core.db.session.add(assessment)
    grade = core.Grade.query.filter_by(student_id=student.id, activity_id=rubric.activity_id).first()
    if not grade:
        grade = core.Grade(student_id=student.id, activity_id=rubric.activity_id)
    grade.score = final
    grade.code = ''
    core.db.session.add(grade)
    core.db.session.commit()
    return assessment


def _render_rubric_table(data, editable=False, prefix=''):
    rows = ''
    for i, c in enumerate(data.get('criteria', [])):
        levels = {int(x['level']): x for x in c.get('levels', [])}
        if editable:
            cells = ''.join(f'<td><b>{escape(levels.get(n, {}).get("label", ""))}</b><textarea name="c{i}_d{n}" rows="5" required>{escape(levels.get(n, {}).get("descriptor", ""))}</textarea></td>' for n in (4,3,2,1))
            rows += f'<tr><td><input name="c{i}_name" value="{escape(c.get("name", ""))}" required><input name="c{i}_weight" type="number" step=".01" min="0" max="100" value="{c.get("weight",0)}" required></td>{cells}</tr>'
        else:
            cells = ''.join(f'<td><b>{escape(levels.get(n, {}).get("label", ""))}</b><br><small>{escape(levels.get(n, {}).get("descriptor", ""))}</small></td>' for n in (4,3,2,1))
            rows += f'<tr><td><b>{escape(c.get("name", ""))}</b><br><small>{c.get("weight",0)}%</small></td>{cells}</tr>'
    return f'<div class="scroll"><table><tr><th>Criterio</th><th>4 · Sobresaliente</th><th>3 · Logrado</th><th>2 · En proceso</th><th>1 · Inicial</th></tr>{rows}</table></div>'


def install(app):
    @app.before_request
    def rubric_bootstrap():
        core.db.create_all()

    @app.route('/rubrics')
    def rubrics_home():
        r = core.require()
        if r: return r
        rows = ''
        for rubric in Rubric.query.order_by(Rubric.updated_at.desc()).all():
            count = RubricAssessment.query.filter_by(rubric_id=rubric.id).count()
            a = rubric.activity
            rows += f'''<tr><td><b>{escape(rubric.title)}</b><br><small>{escape(a.name)} · {escape(a.subject.name if a.subject else '')}</small></td><td>{count}</td><td><a href="/rubrics/{rubric.id}">Ver</a> · <a href="/rubrics/{rubric.id}/edit">Editar</a> · <a href="/rubrics/{rubric.id}/grade">Calificar</a></td></tr>'''
        if not rows:
            rows = '<tr><td colspan="3">Aún no has creado rúbricas.</td></tr>'
        ai_status = 'IA conectada' if os.getenv('OPENAI_API_KEY') else 'Falta configurar OPENAI_API_KEY en Vercel'
        body = f'''<h1>Rúbricas con IA</h1><div class="card"><h2>Evaluación analítica asistida</h2><p>Genera rúbricas profesionales alineadas a una actividad, edítalas y úsalas para calificar a tus alumnos. La decisión final siempre queda en manos del docente.</p><p class="muted"><b>Estado:</b> {escape(ai_status)}</p><a href="/rubrics/new"><button style="max-width:280px">＋ Generar nueva rúbrica</button></a></div><div class="card scroll"><table><tr><th>Rúbrica / actividad</th><th>Evaluados</th><th>Acciones</th></tr>{rows}</table></div>'''
        return core.page('Rúbricas IA', body)

    @app.route('/rubrics/new', methods=['GET', 'POST'])
    def rubric_new():
        r = core.require()
        if r: return r
        activities = core.Activity.query.order_by(core.Activity.activity_date.desc()).all()
        if request.method == 'POST':
            aid = request.form.get('activity_id', type=int)
            activity = core.db.session.get(core.Activity, aid)
            if not activity:
                flash('Selecciona una actividad válida.'); return redirect('/rubrics/new')
            if Rubric.query.filter_by(activity_id=aid).first():
                flash('Esta actividad ya tiene una rúbrica. Puedes editarla.'); return redirect(f'/rubrics/{Rubric.query.filter_by(activity_id=aid).first().id}/edit')
            purpose = request.form.get('purpose', '').strip()
            product = request.form.get('product', '').strip()
            context = request.form.get('context', '').strip()
            system = '''Eres especialista en evaluación formativa, diseño curricular y construcción de rúbricas analíticas para secundaria. Diseña una rúbrica técnicamente sólida: 4 a 6 criterios no redundantes, alineados al producto y propósito; ponderaciones que sumen 100%; cuatro niveles (4 Sobresaliente, 3 Logrado, 2 En proceso, 1 Inicial). Cada descriptor debe ser observable, específico, verificable y distinguir con claridad la calidad del desempeño. Evita palabras vagas como excelente, bien, regular o mal si no están acompañadas por evidencias observables. No evalúes conducta salvo que sea parte explícita del aprendizaje. Redacta en español mexicano y con lenguaje adecuado para Telesecundaria.'''
            user = f'''Actividad: {activity.name}\nAsignatura/Disciplina: {activity.subject.name if activity.subject else ''}\nCampo formativo: {activity.subject.field if activity.subject else ''}\nTrimestre: {activity.trimester}\nPuntaje máximo: {activity.max_score}\nPropósito de evaluación: {purpose}\nProducto o evidencia: {product}\nContexto adicional: {context}\nGenera una rúbrica aplicable directamente a esta actividad.'''
            try:
                data, model = _ai_json(system, user, _rubric_schema(), 'rubrica_analitica')
                data = _normalize_weights(data)
                rubric = Rubric(activity_id=aid, title=data.get('title') or f'Rúbrica · {activity.name}', purpose=purpose, product=product, criteria_json=json.dumps(data, ensure_ascii=False), ai_model=model, created_by=session.get('uid'))
                core.db.session.add(rubric); core.db.session.commit()
                flash('Rúbrica generada. Revísala y edítala antes de aplicarla.')
                return redirect(f'/rubrics/{rubric.id}/edit')
            except Exception as e:
                flash(str(e))
        opts = ''.join(f'<option value="{a.id}">{escape(a.name)} · {escape(a.subject.name if a.subject else "")} · {escape(a.trimester)}</option>' for a in activities)
        body = f'''<h1>Generar rúbrica con IA</h1><div class="card"><form method="post"><label>Actividad<select name="activity_id" required><option value="">Selecciona…</option>{opts}</select></label><br><br><label>Propósito de evaluación<textarea name="purpose" rows="3" required placeholder="¿Qué aprendizaje quieres valorar?"></textarea></label><br><br><label>Producto o evidencia<textarea name="product" rows="3" required placeholder="Ej. exposición, infografía, reporte, resolución de problemas, proyecto…"></textarea></label><br><br><label>Contexto adicional (opcional)<textarea name="context" rows="3" placeholder="PDA, contenido, condiciones de trabajo, aspectos indispensables…"></textarea></label><br><br><button>✨ Generar rúbrica profesional con IA</button></form></div>'''
        return core.page('Nueva rúbrica', body)

    @app.route('/rubrics/<int:rid>')
    def rubric_view(rid):
        r = core.require()
        if r: return r
        rubric = core.db.session.get(Rubric, rid)
        if not rubric: return redirect('/rubrics')
        data = _rubric_data(rubric)
        body = f'''<h1>{escape(rubric.title)}</h1><div class="card"><p><b>Actividad:</b> {escape(rubric.activity.name)}</p><p><b>Propósito:</b> {escape(rubric.purpose)}</p><p><b>Producto:</b> {escape(rubric.product)}</p><p><a href="/rubrics/{rid}/edit">Editar rúbrica</a> · <a href="/rubrics/{rid}/grade">Calificar alumnos</a></p></div><div class="card">{_render_rubric_table(data)}</div>'''
        return core.page('Rúbrica', body)

    @app.route('/rubrics/<int:rid>/edit', methods=['GET', 'POST'])
    def rubric_edit(rid):
        r = core.require()
        if r: return r
        rubric = core.db.session.get(Rubric, rid)
        if not rubric: return redirect('/rubrics')
        data = _rubric_data(rubric)
        if request.method == 'POST':
            rubric.title = request.form.get('title', rubric.title).strip()
            rubric.purpose = request.form.get('purpose', '').strip()
            rubric.product = request.form.get('product', '').strip()
            newcriteria = []
            for i, old in enumerate(data.get('criteria', [])):
                levels = []
                labels = {4:'Sobresaliente',3:'Logrado',2:'En proceso',1:'Inicial'}
                for n in (4,3,2,1):
                    levels.append({'level':n,'label':labels[n],'descriptor':request.form.get(f'c{i}_d{n}','').strip()})
                newcriteria.append({'name':request.form.get(f'c{i}_name','').strip(), 'weight':request.form.get(f'c{i}_weight', type=float) or 0, 'levels':levels})
            data['criteria'] = newcriteria
            data = _normalize_weights(data)
            rubric.criteria_json = json.dumps(data, ensure_ascii=False)
            rubric.updated_at = datetime.utcnow()
            core.db.session.commit(); flash('Rúbrica actualizada.'); return redirect(f'/rubrics/{rid}')
        body = f'''<h1>Revisar y editar rúbrica</h1><div class="card"><form method="post"><label>Título<input name="title" value="{escape(rubric.title)}" required></label><br><br><label>Propósito<textarea name="purpose" rows="2">{escape(rubric.purpose)}</textarea></label><br><br><label>Producto/evidencia<textarea name="product" rows="2">{escape(rubric.product)}</textarea></label><br><br>{_render_rubric_table(data, editable=True)}<p class="muted">Si modificas ponderaciones, el sistema las normalizará automáticamente para sumar 100%.</p><button>Guardar rúbrica</button></form></div>'''
        return core.page('Editar rúbrica', body)

    @app.route('/rubrics/<int:rid>/grade', methods=['GET'])
    def rubric_grade_list(rid):
        r = core.require()
        if r: return r
        rubric = core.db.session.get(Rubric, rid)
        if not rubric: return redirect('/rubrics')
        rows = ''
        for s in core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all():
            a = RubricAssessment.query.filter_by(rubric_id=rid, student_id=s.id).first()
            score = f'{a.final_score:g} / {rubric.activity.max_score:g}' if a else 'Pendiente'
            rows += f'<tr><td>{s.list_no or ""}</td><td>{escape(s.full_name)}</td><td>{score}</td><td><a href="/rubrics/{rid}/grade/{s.id}">Calificar</a></td></tr>'
        body = f'''<h1>Calificar con rúbrica</h1><div class="card"><b>{escape(rubric.title)}</b><br><span class="muted">{escape(rubric.activity.name)}</span></div><div class="card scroll"><table><tr><th>No.</th><th>Alumno</th><th>Resultado</th><th></th></tr>{rows}</table></div>'''
        return core.page('Calificar con rúbrica', body)

    @app.route('/rubrics/<int:rid>/grade/<int:sid>', methods=['GET', 'POST'])
    def rubric_grade_student(rid, sid):
        r = core.require()
        if r: return r
        rubric = core.db.session.get(Rubric, rid); student = core.db.session.get(core.Student, sid)
        if not rubric or not student: return redirect('/rubrics')
        data = _rubric_data(rubric); criteria = data.get('criteria', [])
        assessment = RubricAssessment.query.filter_by(rubric_id=rid, student_id=sid).first()
        selected = json.loads(assessment.details_json) if assessment else {}
        feedback = assessment.feedback if assessment else ''
        ai_reasons = {}
        if request.method == 'POST' and request.form.get('action') == 'ai':
            evidence = request.form.get('evidence', '').strip()
            if not evidence:
                flash('Pega primero la evidencia o respuesta del alumno.')
            else:
                rubric_text = '\n'.join(f'''Criterio {i}: {c.get('name')} ({c.get('weight')}%). ''' + ' | '.join(f'''Nivel {l.get('level')}: {l.get('descriptor')}''' for l in c.get('levels', [])) for i,c in enumerate(criteria))
                system = '''Actúa como evaluador experto. Compara únicamente la evidencia proporcionada contra la rúbrica. No inventes datos ni premies elementos no observables en la evidencia. Para cada criterio selecciona el nivel 1-4 mejor sustentado y explica brevemente qué evidencia justifica la decisión. Si falta evidencia para un criterio, asigna el nivel que corresponda según los descriptores, sin asumir que el alumno hizo algo que no aparece. La sugerencia es para revisión docente, no una decisión automática.'''
                user = f'''Alumno: {student.full_name}\nActividad: {rubric.activity.name}\nRúbrica:\n{rubric_text}\n\nEVIDENCIA DEL ALUMNO:\n{evidence}'''
                try:
                    result, _ = _ai_json(system, user, _grade_schema(len(criteria)), 'evaluacion_rubrica')
                    for x in result.get('scores', []):
                        selected[str(x['criterion_index'])] = int(x['level'])
                        ai_reasons[str(x['criterion_index'])] = x.get('reason','')
                    feedback = result.get('feedback','')
                    flash('La IA generó una propuesta. Revísala y pulsa Guardar calificación para hacerla definitiva.')
                except Exception as e:
                    flash(str(e))
        elif request.method == 'POST':
            selected = {str(i): request.form.get(f'level_{i}', type=int) or 1 for i in range(len(criteria))}
            feedback = request.form.get('feedback','').strip()
            _save_assessment(rubric, student, selected, feedback, request.form.get('ai_used') == '1')
            flash('Calificación guardada y sincronizada con la actividad.')
            return redirect(f'/rubrics/{rid}/grade')
        rows = ''
        for i,c in enumerate(criteria):
            opts=''
            levels = sorted(c.get('levels',[]), key=lambda x:x.get('level',0), reverse=True)
            for l in levels:
                n=int(l['level']); sel='selected' if int(selected.get(str(i),0) or 0)==n else ''
                opts += f'<option value="{n}" {sel}>{n} · {escape(l.get("label",""))} — {escape(l.get("descriptor",""))}</option>'
            reason = ai_reasons.get(str(i),'')
            rows += f'<tr><td><b>{escape(c.get("name",""))}</b><br><small>{c.get("weight",0)}%</small></td><td><select name="level_{i}" required><option value="">Selecciona…</option>{opts}</select>{f"<small><b>Sugerencia IA:</b> {escape(reason)}</small>" if reason else ""}</td></tr>'
        ai_used = '1' if ai_reasons else ('1' if assessment and assessment.ai_assisted else '0')
        body = f'''<h1>{escape(student.full_name)}</h1><div class="card"><h2>Asistencia de IA sobre evidencia</h2><form method="post"><input type="hidden" name="action" value="ai"><label>Pega aquí la evidencia, respuesta, texto o descripción verificable del producto del alumno<textarea name="evidence" rows="9" placeholder="La IA solo evaluará lo que esté explícitamente presente aquí."></textarea></label><br><br><button>✨ Analizar evidencia con la rúbrica</button></form></div><div class="card"><form method="post"><input type="hidden" name="action" value="save"><input type="hidden" name="ai_used" value="{ai_used}"><h2>Decisión docente final</h2><div class="scroll"><table><tr><th>Criterio</th><th>Nivel de desempeño</th></tr>{rows}</table></div><br><label>Retroalimentación<textarea name="feedback" rows="5">{escape(feedback)}</textarea></label><br><br><button>Guardar calificación definitiva</button></form></div>'''
        return core.page('Evaluar con rúbrica', body)

    @app.after_request
    def rubric_ui(response):
        if 'text/html' not in response.headers.get('Content-Type','') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if 'href="/rubrics"' not in html:
            # Sidebar principal.
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/rubrics"><span class="nav-icon">★</span><span>Rúbricas IA</span></a>'
            if marker in html:
                html = html.replace(marker, link + marker, 1)
            # Menú básico de respaldo.
            html = html.replace('<a href="/config">Configuración</a>', '<a href="/rubrics">Rúbricas IA</a><a href="/config">Configuración</a>', 1)
        # Acceso visible en dashboard si existe la sección de acciones rápidas.
        if request.path == '/' and 'Generar rúbrica IA' not in html:
            marker = '</div></section><section class="analytics-row">'
            card = '<a href="/rubrics/new"><span class="quick-icon">★</span><span>Generar rúbrica IA</span></a>'
            if marker in html and '<div class="quick">' in html:
                pos = html.find(marker)
                before = html[:pos]
                qend = before.rfind('</div>')
                if qend != -1:
                    html = html[:qend] + card + html[qend:]
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
