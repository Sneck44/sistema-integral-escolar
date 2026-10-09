from html import escape
from datetime import datetime

from flask import request, redirect, flash, session

import app as core


class ActivitySubject(core.db.Model):
    __tablename__ = 'activity_subject'
    id = core.db.Column(core.db.Integer, primary_key=True)
    activity_id = core.db.Column(core.db.Integer, core.db.ForeignKey('activity.id'), nullable=False, index=True)
    subject_id = core.db.Column(core.db.Integer, core.db.ForeignKey('subject.id'), nullable=False, index=True)
    subject = core.db.relationship('Subject')
    __table_args__ = (
        core.db.UniqueConstraint('activity_id', 'subject_id', name='uq_activity_subject'),
    )


DELIVERY_STATES = [
    ('ENTREGADO', 'Entregado'),
    ('PENDIENTE', 'Pendiente'),
    ('TARDIO', 'Entrega tardía'),
    ('JUSTIFICADO', 'Justificado'),
    ('NO_ENTREGADO', 'No entregado'),
]
DELIVERY_LABELS = dict(DELIVERY_STATES)


def activity_subject_ids(activity):
    """Asignaturas vinculadas; las actividades antiguas conservan la principal."""
    ids = [
        row.subject_id for row in ActivitySubject.query.filter_by(activity_id=activity.id)
        .order_by(ActivitySubject.id).all()
    ]
    if activity.subject_id and activity.subject_id not in ids:
        ids.insert(0, activity.subject_id)
    return ids


def activity_subjects(activity):
    ids = activity_subject_ids(activity)
    if not ids:
        return []
    subjects = {subject.id: subject for subject in core.Subject.query.filter(core.Subject.id.in_(ids)).all()}
    return [subjects[sid] for sid in ids if sid in subjects]


def activity_subject_label(activity):
    return ' · '.join(subject.name for subject in activity_subjects(activity)) or 'Sin asignatura'


def _selected_subject_ids(subjects):
    valid_ids = {subject.id for subject in subjects}
    selected = []
    for raw in request.form.getlist('subject_ids'):
        try:
            subject_id = int(raw)
        except (TypeError, ValueError):
            continue
        if subject_id in valid_ids and subject_id not in selected:
            selected.append(subject_id)
    return selected


def _set_activity_subjects(activity, subject_ids):
    current = {row.subject_id: row for row in ActivitySubject.query.filter_by(activity_id=activity.id).all()}
    primary = activity.subject_id if activity.subject_id in subject_ids else subject_ids[0]
    activity.subject_id = primary
    for subject_id in subject_ids:
        if subject_id not in current:
            core.db.session.add(ActivitySubject(activity_id=activity.id, subject_id=subject_id))
    for subject_id, row in current.items():
        if subject_id not in subject_ids:
            core.db.session.delete(row)


def _delivery_record(student_id, activity_id):
    try:
        from integral_suite import StudentActivityStatus
        return StudentActivityStatus.query.filter_by(student_id=student_id, activity_id=activity_id).first()
    except Exception:
        return None


def _delivery_status(student_id, activity_id, grade=None):
    record = _delivery_record(student_id, activity_id)
    if record and record.status in DELIVERY_LABELS:
        return record.status
    if grade and (grade.score is not None or (grade.code or '').upper() in ('J', 'P')):
        return 'ENTREGADO'
    if grade and (grade.code or '').upper() in ('NP', 'NE'):
        return 'NO_ENTREGADO'
    return 'PENDIENTE'


def _grade_text(grade, activity):
    if not grade:
        return '<span class="grade-empty">Sin calificar</span>'
    if grade.code:
        return f'<b>{escape(grade.code.upper())}</b>'
    if grade.score is None:
        return '<span class="grade-empty">Sin calificar</span>'
    raw = f'{grade.score:g}'
    if activity.max_score and activity.max_score != 10:
        normalized = max(0, min(10, grade.score / activity.max_score * 10))
        return f'<b>{raw} / {activity.max_score:g}</b><br><small>{normalized:.2f} en escala de 10</small>'
    return f'<b>{raw}</b>'


def _subject_checkboxes(subjects, selected_ids=None):
    selected_ids = set(selected_ids or [])
    return ''.join(
        f'<label class="subject-check"><input type="checkbox" name="subject_ids" value="{subject.id}" {"checked" if subject.id in selected_ids else ""}><span><b>{escape(subject.name)}</b><small>{escape(subject.field or "")}</small></span></label>'
        for subject in subjects
    ) or '<p class="muted">Primero registra las asignaturas que utilizará el grupo.</p>'


def _activity_summary(activity, students):
    grades = {grade.student_id: grade for grade in core.Grade.query.filter_by(activity_id=activity.id).all()}
    rows = ''
    counts = {key: 0 for key in DELIVERY_LABELS}
    graded = 0
    for student in students:
        grade = grades.get(student.id)
        status = _delivery_status(student.id, activity.id, grade)
        counts[status] = counts.get(status, 0) + 1
        if grade and (grade.score is not None or grade.code):
            graded += 1
        rows += f'''<tr>
          <td>{student.list_no or ''}</td>
          <td><b>{escape(student.full_name)}</b></td>
          <td><span class="delivery-pill delivery-{status}">{escape(DELIVERY_LABELS.get(status, status))}</span></td>
          <td>{_grade_text(grade, activity)}</td>
        </tr>'''
    if not rows:
        rows = '<tr><td colspan="4">Aún no hay alumnos activos en este grupo.</td></tr>'
    delivered = counts.get('ENTREGADO', 0) + counts.get('TARDIO', 0) + counts.get('JUSTIFICADO', 0)
    pending = counts.get('PENDIENTE', 0) + counts.get('NO_ENTREGADO', 0)
    subjects = activity_subject_label(activity)
    return f'''<section class="activity-summary" id="activity-summary">
      <div class="activity-summary-head"><div><span class="activity-kicker">RESUMEN POR ALUMNO</span><h2>{escape(activity.name)}</h2><p>{escape(subjects)} · {escape(activity.trimester)}</p></div><a href="/grades/{activity.id}">Capturar entregas y calificaciones</a></div>
      <div class="activity-summary-stats"><div><small>Alumnos</small><b>{len(students)}</b></div><div><small>Con entrega</small><b>{delivered}</b></div><div><small>Pendientes</small><b>{pending}</b></div><div><small>Calificados</small><b>{graded}</b></div></div>
      <div class="scroll"><table><tr><th>No.</th><th>Alumno</th><th>Entrega</th><th>Calificación registrada</th></tr>{rows}</table></div>
    </section>'''


ACTIVITY_CSS = '''<style id="activity-multisubject-css">
.subject-selector{grid-column:1/-1;border:1px solid #eadfe1;border-radius:16px;padding:14px;margin:0}.subject-selector legend{padding:0 7px;color:#6d1022;font-weight:850}.subject-selector>p{margin:2px 0 12px}.subject-check-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:9px}.subject-check{display:flex!important;align-items:flex-start;gap:9px;padding:10px;border:1px solid #eee5e7;border-radius:12px;background:#fcfaf9;cursor:pointer}.subject-check input{width:auto!important;margin-top:3px}.subject-check span{min-width:0}.subject-check b,.subject-check small{display:block}.subject-check small{color:#7d7175;margin-top:2px;font-size:10px}.subject-tags{display:flex;gap:5px;flex-wrap:wrap}.subject-tag{display:inline-flex;padding:4px 7px;border-radius:999px;background:#f4e9ec;color:#6d1022;font-size:10px;font-weight:800}.activity-summary{background:#fff;border:1px solid #eee5e7;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(74,18,32,.07)}.activity-summary-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.activity-summary-head h2{margin:4px 0}.activity-summary-head p{margin:0;color:#766a6e}.activity-summary-head>a{padding:10px 14px;border-radius:11px;background:#7b1024;color:#fff;text-decoration:none;font-size:11px;font-weight:850}.activity-kicker{font-size:9px;letter-spacing:1px;color:#9b7a35;font-weight:900}.activity-summary-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:16px 0}.activity-summary-stats div{padding:11px;border-radius:14px;background:#faf6f5;border:1px solid #eee5e3}.activity-summary-stats small,.activity-summary-stats b{display:block}.activity-summary-stats small{color:#7b7074}.activity-summary-stats b{font-size:23px;color:#6d1022}.delivery-pill{display:inline-flex;padding:5px 8px;border-radius:999px;font-size:9px;font-weight:900}.delivery-ENTREGADO{background:#e5f4e9;color:#24643a}.delivery-TARDIO{background:#fff0c9;color:#745710}.delivery-JUSTIFICADO{background:#e6eff8;color:#2e5f88}.delivery-PENDIENTE{background:#f3ecee;color:#735b62}.delivery-NO_ENTREGADO{background:#fde1e5;color:#a41f34}.grade-empty{color:#887b7f;font-size:11px}.activity-select-form{display:flex;align-items:end;gap:10px;flex-wrap:wrap;margin-top:18px}.activity-select-form label{min-width:min(100%,440px)}.grade-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:13px 0}.grade-summary div{padding:11px;border-radius:13px;background:#faf6f5;border:1px solid #eee5e3}.grade-summary small,.grade-summary b{display:block}.grade-summary b{font-size:21px;color:#6d1022}.grade-capture-table select{min-width:135px}.grade-capture-table input{min-width:130px}.grade-capture-table .grade-input{min-width:100px}@media(max-width:720px){.activity-summary-head{display:grid}.activity-summary-head>a{width:100%;text-align:center}.activity-summary-stats{grid-template-columns:repeat(2,1fr)}.subject-check-grid{grid-template-columns:1fr}.grade-summary{grid-template-columns:repeat(2,1fr)}.activity-select-form{display:grid}.activity-select-form label{min-width:0}}
</style>'''


def install(app):
    try:
        with app.app_context():
            core.db.create_all()
    except Exception:
        pass

    def activities_manager():
        r = core.require()
        if r:
            return r

        subjects = core.Subject.query.order_by(core.Subject.name).all()
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            subject_ids = _selected_subject_ids(subjects)
            trimester = request.form.get('trimester', '').strip()
            day_raw = request.form.get('day', '').strip()
            max_score = request.form.get('max_score', type=float) or 10
            if not name or not subject_ids or trimester not in core.TRIMS or not day_raw:
                flash('Completa los datos de la actividad y selecciona al menos una asignatura.')
            else:
                try:
                    day = datetime.strptime(day_raw, '%Y-%m-%d').date()
                except ValueError:
                    day = None
                if not day:
                    flash('La fecha no es válida.')
                else:
                    activity = core.Activity(
                        name=name,
                        subject_id=subject_ids[0],
                        trimester=trimester,
                        activity_date=day,
                        max_score=max_score,
                    )
                    core.db.session.add(activity)
                    core.db.session.flush()
                    _set_activity_subjects(activity, subject_ids)
                    core.db.session.commit()
                    label = 'asignatura' if len(subject_ids) == 1 else 'asignaturas'
                    flash(f'Actividad creada y vinculada con {len(subject_ids)} {label}.')
                    return redirect(f'/activities?summary={activity.id}#activity-summary')

        trimester_options = ''.join(f'<option>{escape(t)}</option>' for t in core.TRIMS)

        activities = core.Activity.query.order_by(core.Activity.activity_date.desc(), core.Activity.id.desc()).all()
        rows = ''
        for a in activities:
            grade_count = core.Grade.query.filter_by(activity_id=a.id).count()
            rubric_count = 0
            try:
                from rubric_ai import Rubric, RubricAssessment
                rubric = Rubric.query.filter_by(activity_id=a.id).first()
                if rubric:
                    rubric_count = RubricAssessment.query.filter_by(rubric_id=rubric.id).count()
            except Exception:
                rubric = None
            warning = ''
            if grade_count or rubric_count:
                warning = f'<br><small style="color:#8A4B08">Tiene {grade_count} calificación(es)' + (f' y {rubric_count} evaluación(es) con rúbrica' if rubric_count else '') + '.</small>'
            subject_tags = ''.join(
                f'<span class="subject-tag">{escape(subject.name)}</span>' for subject in activity_subjects(a)
            )
            rows += f'''
            <tr>
              <td>{a.activity_date.strftime('%d/%m/%Y') if a.activity_date else ''}</td>
              <td><b>{escape(a.name)}</b>{warning}</td>
              <td><div class="subject-tags">{subject_tags}</div></td>
              <td>{escape(a.trimester)}</td>
              <td>{a.max_score:g}</td>
              <td style="white-space:nowrap">
                <a href="/activities?summary={a.id}#activity-summary" style="font-weight:800">Resumen</a> ·
                <a href="/grades/{a.id}" style="font-weight:700">Capturar</a> ·
                <a href="/activities/{a.id}/edit" style="font-weight:700">Editar</a> ·
                <a href="/activities/{a.id}/delete" style="font-weight:700;color:#a00">Borrar</a>
              </td>
            </tr>'''

        requested_summary = request.args.get('summary', type=int)
        summary_activity = next((activity for activity in activities if activity.id == requested_summary), None)
        if not summary_activity and activities:
            summary_activity = activities[0]
        summary_options = ''.join(
            f'<option value="{activity.id}" {"selected" if summary_activity and activity.id == summary_activity.id else ""}>{activity.activity_date.strftime("%d/%m/%Y") if activity.activity_date else ""} · {escape(activity.name)}</option>'
            for activity in activities
        )
        students = core.Student.query.filter_by(status='ACTIVO').order_by(
            core.Student.list_no, core.Student.paternal, core.Student.maternal, core.Student.names
        ).all()
        summary = ''
        if summary_activity:
            summary = f'''<form class="card activity-select-form" method="get" action="/activities"><label>Resumen por actividad<select name="summary" onchange="this.form.submit()">{summary_options}</select></label><div><button>Consultar resumen</button></div></form>{_activity_summary(summary_activity, students)}'''

        body = f'''
        {ACTIVITY_CSS}
        <h1>Actividades</h1>
        <div class="card">
          <h2>Crear actividad</h2>
          <form method="post" class="grid">
            <label>Fecha<input type="date" name="day" required></label>
            <label>Nombre<input name="name" required></label>
            <label>Trimestre<select name="trimester" required>{trimester_options}</select></label>
            <label>Puntaje máximo<input name="max_score" type="number" step="0.01" min="0.01" value="10"></label>
            <fieldset class="subject-selector"><legend>Asignaturas que evaluará</legend><p class="muted">Selecciona una o varias. La misma calificación registrada contará en cada asignatura elegida.</p><div class="subject-check-grid">{_subject_checkboxes(subjects)}</div></fieldset>
            <div><button>Crear actividad</button></div>
          </form>
        </div>
        <div class="card scroll">
          <h2>Actividades registradas</h2>
          <table><tr><th>Fecha</th><th>Actividad</th><th>Asignatura(s)</th><th>Trimestre</th><th>Máximo</th><th>Acciones</th></tr>{rows or '<tr><td colspan="6">Aún no hay actividades registradas.</td></tr>'}</table>
        </div>{summary}'''
        return core.page('Actividades', body)

    app.view_functions['activities'] = activities_manager

    def grades_manager(aid):
        r = core.require()
        if r:
            return r
        activity = core.db.session.get(core.Activity, aid)
        if not activity:
            flash('Actividad no encontrada.')
            return redirect('/activities')
        students = core.Student.query.filter_by(status='ACTIVO').order_by(
            core.Student.list_no, core.Student.paternal, core.Student.maternal, core.Student.names
        ).all()

        if request.method == 'POST':
            parsed = {}
            errors = []
            for student in students:
                raw = request.form.get(f'g{student.id}', '').strip()
                if not raw:
                    parsed[student.id] = (None, '')
                elif raw.upper() in ('NP', 'NE', 'J', 'P'):
                    parsed[student.id] = (None, raw.upper())
                else:
                    try:
                        score = float(raw.replace(',', '.'))
                    except ValueError:
                        errors.append(student.full_name)
                        continue
                    if score < 0 or score > activity.max_score:
                        errors.append(student.full_name)
                        continue
                    parsed[student.id] = (score, '')
            if errors:
                flash(f'Revisa la calificación de: {", ".join(errors)}. Debe estar entre 0 y {activity.max_score:g}, o usar NP, NE, J o P.')
                return redirect(f'/grades/{activity.id}')

            try:
                from integral_suite import StudentActivityStatus
                import group_workspaces
                group_code = group_workspaces.active_group_code() or '1A'
            except Exception:
                StudentActivityStatus = None
                group_code = '1A'

            for student in students:
                score, code = parsed[student.id]
                grade = core.Grade.query.filter_by(student_id=student.id, activity_id=activity.id).first()
                if grade or score is not None or code:
                    grade = grade or core.Grade(student_id=student.id, activity_id=activity.id)
                    grade.score = score
                    grade.code = code
                    core.db.session.add(grade)
                if StudentActivityStatus:
                    status = request.form.get(f'status_{student.id}', 'PENDIENTE')
                    if status not in DELIVERY_LABELS:
                        status = 'PENDIENTE'
                    if status == 'PENDIENTE' and (score is not None or code in ('J', 'P')):
                        status = 'ENTREGADO'
                    elif status == 'PENDIENTE' and code in ('NP', 'NE'):
                        status = 'NO_ENTREGADO'
                    record = StudentActivityStatus.query.filter_by(student_id=student.id, activity_id=activity.id).first()
                    if not record:
                        record = StudentActivityStatus(student_id=student.id, activity_id=activity.id, group_code=group_code)
                        core.db.session.add(record)
                    record.status = status
                    record.notes = request.form.get(f'note_{student.id}', '').strip()[:250]
            core.db.session.commit()
            flash('Entregas y calificaciones guardadas correctamente.')
            return redirect(f'/activities?summary={activity.id}#activity-summary')

        grades = {grade.student_id: grade for grade in core.Grade.query.filter_by(activity_id=activity.id).all()}
        rows = ''
        delivered = pending = graded = 0
        for student in students:
            grade = grades.get(student.id)
            value = grade.code if grade and grade.code else (f'{grade.score:g}' if grade and grade.score is not None else '')
            status = _delivery_status(student.id, activity.id, grade)
            if status in ('ENTREGADO', 'TARDIO', 'JUSTIFICADO'):
                delivered += 1
            else:
                pending += 1
            if grade and (grade.score is not None or grade.code):
                graded += 1
            status_options = ''.join(
                f'<option value="{key}" {"selected" if key == status else ""}>{escape(label)}</option>'
                for key, label in DELIVERY_STATES
            )
            record = _delivery_record(student.id, activity.id)
            note = escape(record.notes if record else '')
            rows += f'''<tr><td>{student.list_no or ''}</td><td><b>{escape(student.full_name)}</b></td><td><select name="status_{student.id}">{status_options}</select></td><td><input class="grade-input" name="g{student.id}" value="{escape(value)}" placeholder="0–{activity.max_score:g} o código"></td><td><input name="note_{student.id}" value="{note}" placeholder="Observación opcional"></td></tr>'''

        body = f'''{ACTIVITY_CSS}<div class="page-head"><h1>{escape(activity.name)}</h1><p>{escape(activity_subject_label(activity))} · {escape(activity.trimester)} · máximo {activity.max_score:g}</p></div>
        <div class="card"><h2>Captura por alumno</h2><p class="muted">Registra qué entregó cada estudiante y su calificación. En una actividad interdisciplinaria, esta calificación contará en todas las asignaturas vinculadas. Códigos permitidos: NP, NE, J y P.</p><div class="grade-summary"><div><small>Alumnos</small><b>{len(students)}</b></div><div><small>Con entrega</small><b>{delivered}</b></div><div><small>Pendientes</small><b>{pending}</b></div><div><small>Calificados</small><b>{graded}</b></div></div></div>
        <form method="post" class="card scroll"><table class="grade-capture-table"><tr><th>No.</th><th>Alumno</th><th>Entrega</th><th>Calificación</th><th>Observación</th></tr>{rows or '<tr><td colspan="5">Aún no hay alumnos activos.</td></tr>'}</table><br><button>Guardar entregas y calificaciones</button></form>
        <p><a href="/activities?summary={activity.id}#activity-summary">← Volver al resumen de la actividad</a></p>'''
        return core.page('Calificaciones', body)

    app.view_functions['grades'] = grades_manager

    @app.route('/activities/<int:activity_id>/edit', methods=['GET', 'POST'])
    def activity_edit(activity_id):
        r = core.require()
        if r:
            return r
        activity = core.db.session.get(core.Activity, activity_id)
        if not activity:
            flash('Actividad no encontrada.')
            return redirect('/activities')

        subjects = core.Subject.query.order_by(core.Subject.name).all()
        if request.method == 'POST':
            subject_ids = _selected_subject_ids(subjects)
            name = request.form.get('name', '').strip()
            trimester = request.form.get('trimester', '').strip()
            day_raw = request.form.get('day', '').strip()
            if not name or not subject_ids or trimester not in core.TRIMS:
                flash('Escribe el nombre, selecciona el trimestre y al menos una asignatura.')
                return redirect(f'/activities/{activity_id}/edit')
            try:
                day = datetime.strptime(day_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('La fecha no es válida.')
                return redirect(f'/activities/{activity_id}/edit')
            activity.name = name
            activity.trimester = trimester
            activity.max_score = request.form.get('max_score', type=float) or 10
            activity.activity_date = day
            _set_activity_subjects(activity, subject_ids)
            core.db.session.commit()
            flash('Actividad actualizada.')
            return redirect(f'/activities?summary={activity.id}#activity-summary')

        to = ''.join(
            f'<option {"selected" if t == activity.trimester else ""}>{escape(t)}</option>' for t in core.TRIMS
        )
        selected_ids = activity_subject_ids(activity)
        body = f'''
        {ACTIVITY_CSS}
        <h1>Editar actividad</h1>
        <div class="card" style="max-width:780px">
          <form method="post" class="grid">
            <label>Fecha<input type="date" name="day" value="{activity.activity_date.isoformat() if activity.activity_date else ''}" required></label>
            <label>Nombre<input name="name" value="{escape(activity.name)}" required></label>
            <label>Trimestre<select name="trimester" required>{to}</select></label>
            <label>Puntaje máximo<input name="max_score" type="number" step="0.01" min="0.01" value="{activity.max_score:g}"></label>
            <fieldset class="subject-selector"><legend>Asignaturas que evaluará</legend><p class="muted">Puedes agregar o retirar asignaturas. La calificación de la actividad se aplicará en todas las seleccionadas.</p><div class="subject-check-grid">{_subject_checkboxes(subjects, selected_ids)}</div></fieldset>
            <div><button>Guardar cambios</button></div>
            <div><a href="/activities" style="display:block;padding:10px;text-align:center">Cancelar</a></div>
          </form>
        </div>'''
        return core.page('Editar actividad', body)

    @app.route('/activities/<int:activity_id>/delete', methods=['GET', 'POST'])
    def activity_delete(activity_id):
        r = core.require()
        if r:
            return r
        activity = core.db.session.get(core.Activity, activity_id)
        if not activity:
            flash('Actividad no encontrada.')
            return redirect('/activities')

        grades = core.Grade.query.filter_by(activity_id=activity.id).all()
        subject_links = ActivitySubject.query.filter_by(activity_id=activity.id).all()
        delivery_records = []
        try:
            from integral_suite import StudentActivityStatus
            delivery_records = StudentActivityStatus.query.filter_by(activity_id=activity.id).all()
        except Exception:
            pass
        rubric = None
        rubric_assessments = []
        try:
            from rubric_ai import Rubric, RubricAssessment
            rubric = Rubric.query.filter_by(activity_id=activity.id).first()
            if rubric:
                rubric_assessments = RubricAssessment.query.filter_by(rubric_id=rubric.id).all()
        except Exception:
            pass

        related = len(grades) + len(rubric_assessments) + len(delivery_records)
        if request.method == 'POST':
            confirm = request.form.get('confirm') == 'DELETE'
            if related and not confirm:
                flash('Debes marcar la confirmación porque esta actividad tiene registros asociados.')
                return redirect(f'/activities/{activity.id}/delete')

            for g in grades:
                core.db.session.delete(g)
            for record in delivery_records:
                core.db.session.delete(record)
            for link in subject_links:
                core.db.session.delete(link)
            for ra in rubric_assessments:
                core.db.session.delete(ra)
            if rubric:
                core.db.session.delete(rubric)
            core.db.session.delete(activity)
            core.db.session.commit()
            flash('Actividad eliminada correctamente.')
            return redirect('/activities')

        warning = ''
        if related:
            warning = f'''
            <div class="alert danger">
              <b>Atención:</b> esta actividad tiene {len(grades)} calificación(es), {len(delivery_records)} registro(s) de entrega y {len(rubric_assessments)} evaluación(es) de rúbrica asociadas.
              Si la eliminas, esos registros también se borrarán.
            </div>
            <label style="display:flex;gap:8px;align-items:center"><input style="width:auto" type="checkbox" name="confirm" value="DELETE" required> Confirmo que deseo borrar la actividad y sus registros asociados.</label><br><br>
            '''
        body = f'''
        <h1>Borrar actividad</h1>
        <div class="card" style="max-width:680px">
          <h2>{escape(activity.name)}</h2>
          <p>{escape(activity_subject_label(activity))} · {escape(activity.trimester)}</p>
          {warning}
          <form method="post">
            {'<input type="hidden" name="confirm" value="DELETE">' if not related else ''}
            <button style="background:#a61b1b">Borrar definitivamente</button>
          </form>
          <p style="margin-top:16px"><a href="/activities">Cancelar y volver</a></p>
        </div>'''
        return core.page('Borrar actividad', body)
