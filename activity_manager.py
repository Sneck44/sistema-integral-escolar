from html import escape
from datetime import datetime

from flask import request, redirect, flash, session

import app as core


def install(app):
    def activities_manager():
        r = core.require()
        if r:
            return r

        subjects = core.Subject.query.order_by(core.Subject.name).all()
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            subject_id = request.form.get('subject_id', type=int)
            trimester = request.form.get('trimester', '').strip()
            day_raw = request.form.get('day', '').strip()
            max_score = request.form.get('max_score', type=float) or 10
            if not name or not subject_id or not trimester or not day_raw:
                flash('Completa los datos de la actividad.')
            else:
                try:
                    day = datetime.strptime(day_raw, '%Y-%m-%d').date()
                except ValueError:
                    day = None
                if not day:
                    flash('La fecha no es válida.')
                else:
                    core.db.session.add(core.Activity(
                        name=name,
                        subject_id=subject_id,
                        trimester=trimester,
                        activity_date=day,
                        max_score=max_score,
                    ))
                    core.db.session.commit()
                    flash('Actividad creada.')
                    return redirect('/activities')

        subject_options = ''.join(
            f'<option value="{s.id}">{escape(s.name)}</option>' for s in subjects
        )
        trimester_options = ''.join(f'<option>{escape(t)}</option>' for t in core.TRIMS)

        rows = ''
        for a in core.Activity.query.order_by(core.Activity.activity_date.desc(), core.Activity.id.desc()).all():
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
            rows += f'''
            <tr>
              <td>{a.activity_date.strftime('%d/%m/%Y') if a.activity_date else ''}</td>
              <td><b>{escape(a.name)}</b>{warning}</td>
              <td>{escape(a.subject.name if a.subject else '')}</td>
              <td>{escape(a.trimester)}</td>
              <td>{a.max_score:g}</td>
              <td style="white-space:nowrap">
                <a href="/grades/{a.id}" style="font-weight:700">Calificar</a> ·
                <a href="/activities/{a.id}/edit" style="font-weight:700">Editar</a> ·
                <a href="/activities/{a.id}/delete" style="font-weight:700;color:#a00">Borrar</a>
              </td>
            </tr>'''

        body = f'''
        <h1>Actividades</h1>
        <div class="card">
          <h2>Crear actividad</h2>
          <form method="post" class="grid">
            <label>Fecha<input type="date" name="day" required></label>
            <label>Nombre<input name="name" required></label>
            <label>Asignatura<select name="subject_id" required>{subject_options}</select></label>
            <label>Trimestre<select name="trimester" required>{trimester_options}</select></label>
            <label>Puntaje máximo<input name="max_score" type="number" step="0.01" min="0.01" value="10"></label>
            <div><button>Crear actividad</button></div>
          </form>
        </div>
        <div class="card scroll">
          <h2>Actividades registradas</h2>
          <table><tr><th>Fecha</th><th>Actividad</th><th>Asignatura</th><th>Trimestre</th><th>Máximo</th><th>Acciones</th></tr>{rows}</table>
        </div>'''
        return core.page('Actividades', body)

    app.view_functions['activities'] = activities_manager

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
            activity.name = request.form.get('name', '').strip()
            activity.subject_id = request.form.get('subject_id', type=int)
            activity.trimester = request.form.get('trimester', '').strip()
            activity.max_score = request.form.get('max_score', type=float) or 10
            day_raw = request.form.get('day', '').strip()
            try:
                activity.activity_date = datetime.strptime(day_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('La fecha no es válida.')
                return redirect(f'/activities/{activity_id}/edit')
            core.db.session.commit()
            flash('Actividad actualizada.')
            return redirect('/activities')

        so = ''.join(
            f'<option value="{s.id}" {"selected" if s.id == activity.subject_id else ""}>{escape(s.name)}</option>'
            for s in subjects
        )
        to = ''.join(
            f'<option {"selected" if t == activity.trimester else ""}>{escape(t)}</option>' for t in core.TRIMS
        )
        body = f'''
        <h1>Editar actividad</h1>
        <div class="card" style="max-width:780px">
          <form method="post" class="grid">
            <label>Fecha<input type="date" name="day" value="{activity.activity_date.isoformat() if activity.activity_date else ''}" required></label>
            <label>Nombre<input name="name" value="{escape(activity.name)}" required></label>
            <label>Asignatura<select name="subject_id" required>{so}</select></label>
            <label>Trimestre<select name="trimester" required>{to}</select></label>
            <label>Puntaje máximo<input name="max_score" type="number" step="0.01" min="0.01" value="{activity.max_score:g}"></label>
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
        rubric = None
        rubric_assessments = []
        try:
            from rubric_ai import Rubric, RubricAssessment
            rubric = Rubric.query.filter_by(activity_id=activity.id).first()
            if rubric:
                rubric_assessments = RubricAssessment.query.filter_by(rubric_id=rubric.id).all()
        except Exception:
            pass

        related = len(grades) + len(rubric_assessments)
        if request.method == 'POST':
            confirm = request.form.get('confirm') == 'DELETE'
            if related and not confirm:
                flash('Debes marcar la confirmación porque esta actividad tiene registros asociados.')
                return redirect(f'/activities/{activity.id}/delete')

            for g in grades:
                core.db.session.delete(g)
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
              <b>Atención:</b> esta actividad tiene {len(grades)} calificación(es) y {len(rubric_assessments)} evaluación(es) de rúbrica asociadas.
              Si la eliminas, esos registros también se borrarán.
            </div>
            <label style="display:flex;gap:8px;align-items:center"><input style="width:auto" type="checkbox" name="confirm" value="DELETE" required> Confirmo que deseo borrar la actividad y sus registros asociados.</label><br><br>
            '''
        body = f'''
        <h1>Borrar actividad</h1>
        <div class="card" style="max-width:680px">
          <h2>{escape(activity.name)}</h2>
          <p>{escape(activity.subject.name if activity.subject else '')} · {escape(activity.trimester)}</p>
          {warning}
          <form method="post">
            {'<input type="hidden" name="confirm" value="DELETE">' if not related else ''}
            <button style="background:#a61b1b">Borrar definitivamente</button>
          </form>
          <p style="margin-top:16px"><a href="/activities">Cancelar y volver</a></p>
        </div>'''
        return core.page('Borrar actividad', body)
