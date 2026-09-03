import io
import os
from datetime import date, datetime, timedelta
from html import escape

from flask import request, session, redirect, flash, Response, send_file
from sqlalchemy import func

import app as core
import multi_user


# ---------------------------
# Modelos aditivos (no alteran tablas existentes)
# ---------------------------
class StudentActivityStatus(core.db.Model):
    __tablename__ = 'student_activity_status'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), nullable=False, index=True)
    activity_id = core.db.Column(core.db.Integer, core.db.ForeignKey('activity.id'), nullable=False, index=True)
    group_code = core.db.Column(core.db.String(8), nullable=False, index=True)
    status = core.db.Column(core.db.String(30), default='PENDIENTE', nullable=False)
    notes = core.db.Column(core.db.String(250), default='')
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (core.db.UniqueConstraint('student_id','activity_id', name='uq_student_activity_status'),)


class GuardianContact(core.db.Model):
    __tablename__ = 'guardian_contact'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), nullable=False, index=True)
    group_code = core.db.Column(core.db.String(8), nullable=False, index=True)
    contact_date = core.db.Column(core.db.Date, default=date.today, nullable=False)
    contact_type = core.db.Column(core.db.String(40), default='ENTREVISTA')
    reason = core.db.Column(core.db.Text, nullable=False)
    agreements = core.db.Column(core.db.Text, default='')
    followup_date = core.db.Column(core.db.Date, nullable=True)
    status = core.db.Column(core.db.String(30), default='PENDIENTE')
    created_by = core.db.Column(core.db.Integer, nullable=True)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


class IncidentFollowup(core.db.Model):
    __tablename__ = 'incident_followup'
    id = core.db.Column(core.db.Integer, primary_key=True)
    incident_id = core.db.Column(core.db.Integer, core.db.ForeignKey('incident.id'), nullable=False, index=True)
    group_code = core.db.Column(core.db.String(8), nullable=False, index=True)
    severity = core.db.Column(core.db.String(20), default='MEDIA')
    recurrence = core.db.Column(core.db.Boolean, default=False)
    measure = core.db.Column(core.db.Text, default='')
    agreement = core.db.Column(core.db.Text, default='')
    followup_date = core.db.Column(core.db.Date, nullable=True)
    followup_notes = core.db.Column(core.db.Text, default='')
    resolved = core.db.Column(core.db.Boolean, default=False)
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (core.db.UniqueConstraint('incident_id', name='uq_incident_followup'),)


class SchoolAgenda(core.db.Model):
    __tablename__ = 'school_agenda'
    id = core.db.Column(core.db.Integer, primary_key=True)
    group_code = core.db.Column(core.db.String(8), nullable=False, index=True)
    event_date = core.db.Column(core.db.Date, nullable=False, index=True)
    title = core.db.Column(core.db.String(180), nullable=False)
    category = core.db.Column(core.db.String(50), default='ESCOLAR')
    details = core.db.Column(core.db.Text, default='')
    all_groups = core.db.Column(core.db.Boolean, default=False)
    created_by = core.db.Column(core.db.Integer, nullable=True)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


class PlanningRecord(core.db.Model):
    __tablename__ = 'planning_record'
    id = core.db.Column(core.db.Integer, primary_key=True)
    group_code = core.db.Column(core.db.String(8), nullable=False, index=True)
    field = core.db.Column(core.db.String(120), default='Lenguajes')
    project = core.db.Column(core.db.String(180), nullable=False)
    partial_projects = core.db.Column(core.db.String(250), default='')
    start_date = core.db.Column(core.db.Date, nullable=False)
    end_date = core.db.Column(core.db.Date, nullable=False)
    session_minutes = core.db.Column(core.db.Integer, default=90)
    non_working_days = core.db.Column(core.db.String(250), default='')
    group_observations = core.db.Column(core.db.Text, default='')
    purpose = core.db.Column(core.db.Text, default='')
    stages = core.db.Column(core.db.Text, default='')
    resources = core.db.Column(core.db.Text, default='')
    assessment = core.db.Column(core.db.Text, default='')
    created_by = core.db.Column(core.db.Integer, nullable=True)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


class StudentEvidence(core.db.Model):
    __tablename__ = 'student_evidence'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), nullable=False, index=True)
    group_code = core.db.Column(core.db.String(8), nullable=False, index=True)
    evidence_date = core.db.Column(core.db.Date, default=date.today, nullable=False)
    category = core.db.Column(core.db.String(60), default='PRODUCTO')
    title = core.db.Column(core.db.String(180), nullable=False)
    notes = core.db.Column(core.db.Text, default='')
    filename = core.db.Column(core.db.String(220), nullable=False)
    mime = core.db.Column(core.db.String(100), nullable=False)
    data = core.db.Column(core.db.LargeBinary, nullable=False)
    created_by = core.db.Column(core.db.Integer, nullable=True)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------
# Utilidades
# ---------------------------
def _uid():
    return session.get('uid')


def _profile():
    return multi_user._profile(_uid()) if _uid() else None


def _can_edit():
    p = _profile()
    return bool(p and p.active and p.role in ('ADMIN','DOCENTE'))


def _group_code():
    try:
        import group_workspaces
        return group_workspaces.active_group_code() or '1A'
    except Exception:
        c = core.cfg(); digits = ''.join(ch for ch in (c.grade or '') if ch.isdigit()) or '1'
        return f'{digits}{(c.group or "A").upper()}'


def _group_label():
    try:
        import group_workspaces
        return group_workspaces.active_group_label()
    except Exception:
        c = core.cfg(); return f'{c.grade} {c.group}'


def _students():
    return core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal, core.Student.names).all()


def _student(sid):
    s = core.db.session.get(core.Student, sid)
    return s


def _e(v):
    return escape(str(v or ''))


def _student_option(selected=None):
    return ''.join(f'<option value="{s.id}" {"selected" if s.id==selected else ""}>{_e(s.list_no or "")} · {_e(s.full_name)}</option>' for s in _students())


def _attendance_stats(sid):
    rows = core.Attendance.query.filter_by(student_id=sid).all()
    total = len(rows)
    present = sum(1 for r in rows if r.state in ('PRESENTE','RETARDO'))
    absences = sum(1 for r in rows if r.state not in ('PRESENTE','RETARDO'))
    pct = round(present * 100 / total, 1) if total else None
    return total, present, absences, pct


def _grade_stats(sid, trim=None):
    vals = []
    missing = 0
    activities = core.Activity.query
    if trim:
        activities = activities.filter_by(trimester=trim)
    acts = activities.all()
    grade_map = {g.activity_id:g for g in core.Grade.query.filter_by(student_id=sid).all()}
    for a in acts:
        g = grade_map.get(a.id)
        if g and g.score is not None and a.max_score:
            vals.append(g.score / a.max_score * 10)
        elif not g or (g.score is None and (g.code or '').upper() in ('NP','NE','')):
            missing += 1
    return (round(sum(vals)/len(vals),2) if vals else None), missing, len(acts)


def _risk(sid):
    avg, missing, total_acts = _grade_stats(sid)
    _, _, absences, att_pct = _attendance_stats(sid)
    incidents = core.Incident.query.filter_by(student_id=sid, status='ABIERTA').count()
    score = 0; reasons = []
    if avg is not None and avg < 6: score += 4; reasons.append(f'promedio {avg}')
    elif avg is not None and avg < 7: score += 2; reasons.append(f'promedio {avg}')
    if att_pct is not None and att_pct < 80: score += 4; reasons.append(f'asistencia {att_pct}%')
    elif att_pct is not None and att_pct < 90: score += 2; reasons.append(f'asistencia {att_pct}%')
    if missing >= 3: score += 3; reasons.append(f'{missing} actividades sin evidencia')
    elif missing >= 1: score += 1; reasons.append(f'{missing} actividad(es) sin evidencia')
    if incidents >= 3: score += 3; reasons.append(f'{incidents} incidencias abiertas')
    elif incidents >= 1: score += 1; reasons.append(f'{incidents} incidencia(s) abierta(s)')
    if score >= 7: level, label = 'RED', 'Intervención prioritaria'
    elif score >= 4: level, label = 'ORANGE', 'Riesgo'
    elif score >= 2: level, label = 'YELLOW', 'Atención'
    else: level, label = 'GREEN', 'Sin riesgo'
    return {'score':score,'level':level,'label':label,'reasons':reasons,'avg':avg,'att':att_pct,'missing':missing,'incidents':incidents,'absences':absences}


def _status_for(sid, aid):
    rec = StudentActivityStatus.query.filter_by(student_id=sid, activity_id=aid).first()
    if rec:
        return rec.status
    g = core.Grade.query.filter_by(student_id=sid, activity_id=aid).first()
    if g and (g.score is not None or (g.code or '').upper() in ('J','P')):
        return 'ENTREGADO'
    if g and (g.code or '').upper() in ('NP','NE'):
        return 'NO_ENTREGADO'
    return 'PENDIENTE'


def _suite_css():
    return '''<style id="integral-suite-css">.suite-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.suite-card{display:block;text-decoration:none;padding:17px;border:1px solid #eee8e6;border-radius:16px;background:#fff;min-height:122px}.suite-card b{display:block;color:#7b1024;margin-bottom:7px}.suite-card p{margin:0;color:#746a6d;font-size:12px;line-height:1.45}.risk-pill{display:inline-flex;padding:5px 9px;border-radius:999px;font-size:11px;font-weight:850}.risk-GREEN{background:#e8f5ea;color:#246438}.risk-YELLOW{background:#fff2c7;color:#765812}.risk-ORANGE{background:#ffe8cc;color:#8a4c12}.risk-RED{background:#fde2e5;color:#9d1b2e}.student-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.student-tabs a{padding:8px 11px;border-radius:999px;text-decoration:none;background:#f5edef;color:#6d1022;font-weight:750;font-size:12px}.metric-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.metric-box{border:1px solid #eee8e6;border-radius:14px;padding:12px}.metric-box b{font-size:23px;color:#7b1024}.doc-actions{display:flex;gap:9px;flex-wrap:wrap}.doc-actions a{display:inline-block;text-decoration:none;padding:10px 14px;border-radius:999px;background:#7b1024;color:#fff;font-weight:800;font-size:12px}.portfolio-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.evidence-card{border:1px solid #eee8e6;border-radius:14px;padding:12px;min-width:0}.evidence-card b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.suite-form-actions{display:flex;gap:8px;align-items:end}.suite-form-actions>*{flex:1}@media(max-width:720px){.metric-row{grid-template-columns:repeat(2,minmax(0,1fr))}.suite-grid{grid-template-columns:1fr}.suite-form-actions{display:grid}.doc-actions a{width:100%;text-align:center}}</style>'''


def _page(title, body):
    return core.page(title, _suite_css() + body)


# ---------------------------
# Instalación y rutas
# ---------------------------
def install(app):
    try:
        with app.app_context():
            core.db.create_all()
    except Exception:
        pass

    @app.route('/suite')
    def suite_home():
        if not _uid(): return redirect('/login')
        cards = [
            ('/suite/students','1. Expediente integral','Ficha única por alumno con desempeño, asistencia, incidencias, tutoría y evidencias.'),
            ('/suite/risk','2. Alertas tempranas','Detección automática de riesgo académico, asistencia, pendientes e incidencias.'),
            ('/suite/pending','3. Trabajos pendientes','Control de entregado, pendiente, tardío, justificado y no entregado.'),
            ('/suite/reports','4. Reportes trimestrales','Resumen imprimible por alumno y trimestre.'),
            ('/suite/guardians','5. Atención a tutores','Bitácora de entrevistas, llamadas, acuerdos y seguimiento.'),
            ('/suite/behavior','6. Convivencia avanzada','Gravedad, reincidencia, medidas, acuerdos y seguimiento de incidencias.'),
            ('/suite/documents','7. Documentos escolares','Centro de formatos imprimibles y exportaciones existentes.'),
            ('/suite/agenda','8. Agenda docente','Eventos, evaluaciones, reuniones y recordatorios por grupo.'),
            ('/suite/analytics','9. Reportes y estadísticas','Indicadores consolidados para decisiones docentes.'),
            ('/suite/planning','10. Planeación didáctica','Registro estructurado de proyectos, fechas, etapas, recursos y evaluación.'),
            ('/suite/evidence','11. Portafolio de evidencias','Archivos vinculados al alumno para productos, proyectos e incidencias.'),
        ]
        html = ''.join(f'<a class="suite-card" href="{href}"><b>{_e(title)}</b><p>{_e(desc)}</p></a>' for href,title,desc in cards)
        return _page('Seguimiento integral', f'<div class="page-head"><h1>Centro de Seguimiento Integral</h1><p>Grupo activo: {_e(_group_label())}. Los módulos nuevos complementan los registros existentes sin sustituirlos.</p></div><div class="suite-grid">{html}</div>')

    # 1. Expediente integral
    @app.route('/suite/students')
    def suite_students():
        if not _uid(): return redirect('/login')
        rows = ''
        for s in _students():
            r = _risk(s.id); rows += f'<tr><td>{_e(s.list_no)}</td><td><a href="/suite/student/{s.id}"><b>{_e(s.full_name)}</b></a></td><td>{r["avg"] if r["avg"] is not None else "—"}</td><td>{str(r["att"])+"%" if r["att"] is not None else "—"}</td><td><span class="risk-pill risk-{r["level"]}">{_e(r["label"])}</span></td></tr>'
        return _page('Expedientes', f'<div class="page-head"><h1>Expediente integral del alumno</h1><p>Concentra la información disponible del grupo {_e(_group_label())}.</p></div><div class="card scroll"><table><tr><th>No.</th><th>Alumno</th><th>Promedio</th><th>Asistencia</th><th>Alerta</th></tr>{rows}</table></div>')

    @app.route('/suite/student/<int:sid>')
    def suite_student(sid):
        if not _uid(): return redirect('/login')
        s = _student(sid)
        if not s: return Response('Alumno no encontrado', status=404)
        r = _risk(sid); total,present,absences,pct = _attendance_stats(sid)
        contacts = GuardianContact.query.filter_by(student_id=sid, group_code=_group_code()).order_by(GuardianContact.contact_date.desc()).limit(5).all()
        evidences = StudentEvidence.query.filter_by(student_id=sid, group_code=_group_code()).order_by(StudentEvidence.evidence_date.desc()).limit(6).all()
        incs = core.Incident.query.filter_by(student_id=sid).order_by(core.Incident.day.desc()).limit(5).all()
        contact_html = ''.join(f'<tr><td>{c.contact_date}</td><td>{_e(c.contact_type)}</td><td>{_e(c.reason)}</td><td>{_e(c.status)}</td></tr>' for c in contacts) or '<tr><td colspan="4">Sin registros</td></tr>'
        inc_html = ''.join(f'<tr><td>{i.day}</td><td>{_e(i.category)}</td><td>{_e(i.description)}</td><td>{_e(i.status)}</td></tr>' for i in incs) or '<tr><td colspan="4">Sin registros</td></tr>'
        ev_html = ''.join(f'<div class="evidence-card"><b>{_e(e.title)}</b><small>{e.evidence_date} · {_e(e.category)}</small><p class="muted">{_e(e.notes)}</p><a href="/suite/evidence/{e.id}/download">Abrir archivo</a></div>' for e in evidences) or '<p class="muted">Sin evidencias.</p>'
        return _page('Expediente', f'''<div class="page-head"><h1>{_e(s.full_name)}</h1><p>No. {_e(s.list_no)} · Tutor: {_e(s.tutor)} · Teléfono: {_e(s.phone)}</p></div>
        <div class="metric-row"><div class="metric-box"><span>Promedio</span><br><b>{r['avg'] if r['avg'] is not None else '—'}</b></div><div class="metric-box"><span>Asistencia</span><br><b>{str(pct)+'%' if pct is not None else '—'}</b></div><div class="metric-box"><span>Pendientes</span><br><b>{r['missing']}</b></div><div class="metric-box"><span>Incidencias abiertas</span><br><b>{r['incidents']}</b></div></div>
        <div class="card"><span class="risk-pill risk-{r['level']}">{_e(r['label'])}</span><p>{_e(', '.join(r['reasons']) if r['reasons'] else 'Sin factores de riesgo detectados con los datos actuales.')}</p><div class="student-tabs"><a href="/suite/reports?student={s.id}">Reporte trimestral</a><a href="/suite/guardians?student={s.id}">Atención a tutor</a><a href="/suite/evidence?student={s.id}">Agregar evidencia</a><a href="/suite/documents?student={s.id}">Documentos</a></div></div>
        <div class="card scroll"><h2>Atención a tutor reciente</h2><table><tr><th>Fecha</th><th>Tipo</th><th>Motivo</th><th>Estado</th></tr>{contact_html}</table></div>
        <div class="card scroll"><h2>Incidencias recientes</h2><table><tr><th>Fecha</th><th>Categoría</th><th>Descripción</th><th>Estado</th></tr>{inc_html}</table></div>
        <div class="card"><h2>Evidencias recientes</h2><div class="portfolio-grid">{ev_html}</div></div>''')

    # 2. Alertas
    @app.route('/suite/risk')
    def suite_risk():
        if not _uid(): return redirect('/login')
        items = sorted([(s,_risk(s.id)) for s in _students()], key=lambda x:x[1]['score'], reverse=True)
        rows = ''.join(f'<tr><td>{_e(s.list_no)}</td><td><a href="/suite/student/{s.id}">{_e(s.full_name)}</a></td><td><span class="risk-pill risk-{r["level"]}">{_e(r["label"])}</span></td><td>{_e(", ".join(r["reasons"]) or "Sin factores")}</td></tr>' for s,r in items)
        return _page('Alertas tempranas', f'<div class="page-head"><h1>Alertas tempranas</h1><p>Clasificación automática basada únicamente en los registros disponibles del sistema.</p></div><div class="card scroll"><table><tr><th>No.</th><th>Alumno</th><th>Nivel</th><th>Factores detectados</th></tr>{rows}</table></div>')

    # 3. Trabajos pendientes
    @app.route('/suite/pending', methods=['GET','POST'])
    def suite_pending():
        if not _uid(): return redirect('/login')
        acts = core.Activity.query.order_by(core.Activity.activity_date.desc()).all()
        aid = request.values.get('activity_id', type=int) or (acts[0].id if acts else None)
        if request.method == 'POST' and _can_edit() and aid:
            for s in _students():
                val = request.form.get(f'status_{s.id}', 'PENDIENTE')
                if val not in ('ENTREGADO','PENDIENTE','TARDIO','JUSTIFICADO','NO_ENTREGADO'): val='PENDIENTE'
                rec = StudentActivityStatus.query.filter_by(student_id=s.id, activity_id=aid).first()
                if not rec:
                    rec = StudentActivityStatus(student_id=s.id, activity_id=aid, group_code=_group_code())
                    core.db.session.add(rec)
                rec.status = val; rec.notes = request.form.get(f'note_{s.id}','')[:250]; rec.updated_at = datetime.utcnow()
            core.db.session.commit(); flash('Estado de entregas actualizado.'); return redirect(f'/suite/pending?activity_id={aid}')
        options = ''.join(f'<option value="{a.id}" {"selected" if a.id==aid else ""}>{a.activity_date} · {_e(a.name)}</option>' for a in acts)
        rows=''
        if aid:
            for s in _students():
                current = _status_for(s.id, aid)
                opts=''.join(f'<option value="{v}" {"selected" if v==current else ""}>{l}</option>' for v,l in [('ENTREGADO','Entregado'),('PENDIENTE','Pendiente'),('TARDIO','Entrega tardía'),('JUSTIFICADO','Justificado'),('NO_ENTREGADO','No entregado')])
                rec=StudentActivityStatus.query.filter_by(student_id=s.id, activity_id=aid).first(); note=_e(rec.notes if rec else '')
                rows+=f'<tr><td>{_e(s.list_no)}</td><td>{_e(s.full_name)}</td><td><select name="status_{s.id}">{opts}</select></td><td><input name="note_{s.id}" value="{note}" placeholder="Observación"></td></tr>'
        action = '<button>Guardar seguimiento</button>' if _can_edit() and aid else ''
        return _page('Trabajos pendientes', f'<div class="page-head"><h1>Seguimiento de trabajos</h1><p>Complementa las calificaciones sin modificarlas.</p></div><form method="get" class="card"><label>Actividad<select name="activity_id" onchange="this.form.submit()">{options}</select></label></form><form method="post" class="card scroll"><input type="hidden" name="activity_id" value="{aid or ""}"><table><tr><th>No.</th><th>Alumno</th><th>Estado</th><th>Observación</th></tr>{rows}</table><div style="margin-top:14px">{action}</div></form>')

    # 4. Reporte trimestral
    @app.route('/suite/reports')
    def suite_reports():
        if not _uid(): return redirect('/login')
        sid = request.args.get('student', type=int); trim = request.args.get('trim') or core.TRIMS[0]
        s = _student(sid) if sid else None
        student_options = '<option value="">Selecciona...</option>' + _student_option(sid)
        trim_opts = ''.join(f'<option {"selected" if t==trim else ""}>{t}</option>' for t in core.TRIMS)
        preview=''
        if s:
            avg,missing,total_acts=_grade_stats(s.id,trim); _,_,absences,pct=_attendance_stats(s.id); inc=core.Incident.query.filter_by(student_id=s.id).count(); r=_risk(s.id)
            preview=f'''<div class="card"><h2>Vista previa</h2><div class="metric-row"><div class="metric-box">Promedio<br><b>{avg if avg is not None else '—'}</b></div><div class="metric-box">Asistencia<br><b>{str(pct)+'%' if pct is not None else '—'}</b></div><div class="metric-box">Sin evidencia<br><b>{missing}</b></div><div class="metric-box">Incidencias<br><b>{inc}</b></div></div><p><b>Alerta:</b> {_e(r['label'])}</p><div class="doc-actions"><a href="/suite/report/{s.id}/print?trim={_e(trim)}" target="_blank">Abrir reporte imprimible</a></div></div>'''
        return _page('Reportes trimestrales', f'<div class="page-head"><h1>Reporte trimestral automático</h1><p>Integra calificaciones, asistencia, pendientes e incidencias.</p></div><form method="get" class="card grid"><label>Alumno<select name="student">{student_options}</select></label><label>Trimestre<select name="trim">{trim_opts}</select></label><div><button>Generar vista previa</button></div></form>{preview}')

    @app.route('/suite/report/<int:sid>/print')
    def suite_report_print(sid):
        if not _uid(): return redirect('/login')
        s=_student(sid)
        if not s:return Response('Alumno no encontrado',404)
        trim=request.args.get('trim') or core.TRIMS[0]; avg,missing,total_acts=_grade_stats(sid,trim); total,present,absences,pct=_attendance_stats(sid); inc=core.Incident.query.filter_by(student_id=sid).count(); r=_risk(sid)
        html=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Reporte {_e(s.full_name)}</title><style>body{{font-family:Arial,sans-serif;margin:35px;color:#222}}h1,h2{{color:#7b1024}}table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:9px}}.sig{{margin-top:70px;display:grid;grid-template-columns:1fr 1fr;gap:70px;text-align:center}}@media print{{button{{display:none}}}}</style></head><body><button onclick="print()">Imprimir</button><h1>REPORTE TRIMESTRAL DEL ALUMNO</h1><p><b>Escuela:</b> {_e(core.cfg().school)} &nbsp; <b>CCT:</b> {_e(core.cfg().cct)} &nbsp; <b>Ciclo:</b> {_e(core.cfg().cycle)}</p><p><b>Grupo:</b> {_e(_group_label())} &nbsp; <b>Trimestre:</b> {_e(trim)}</p><h2>{_e(s.full_name)}</h2><table><tr><th>Promedio</th><th>Asistencia</th><th>Actividades sin evidencia</th><th>Incidencias</th></tr><tr><td>{avg if avg is not None else '—'}</td><td>{str(pct)+'%' if pct is not None else '—'}</td><td>{missing}</td><td>{inc}</td></tr></table><p><b>Seguimiento:</b> {_e(r['label'])}. {_e(', '.join(r['reasons']) if r['reasons'] else 'Sin factores de riesgo detectados.')}</p><div class="sig"><div>____________________________<br>DOCENTE TITULAR</div><div>____________________________<br>Vo. Bo. DIRECCIÓN</div></div></body></html>'''
        return Response(html,mimetype='text/html')

    # 5. Tutoría
    @app.route('/suite/guardians', methods=['GET','POST'])
    def suite_guardians():
        if not _uid(): return redirect('/login')
        selected=request.values.get('student',type=int)
        if request.method=='POST' and _can_edit():
            sid=request.form.get('student',type=int)
            if sid:
                fd=request.form.get('followup_date')
                rec=GuardianContact(student_id=sid,group_code=_group_code(),contact_date=datetime.strptime(request.form.get('contact_date') or str(date.today()),'%Y-%m-%d').date(),contact_type=request.form.get('contact_type','ENTREVISTA'),reason=request.form.get('reason','').strip(),agreements=request.form.get('agreements','').strip(),followup_date=datetime.strptime(fd,'%Y-%m-%d').date() if fd else None,status=request.form.get('status','PENDIENTE'),created_by=_uid())
                core.db.session.add(rec);core.db.session.commit();flash('Atención a tutor registrada.');return redirect(f'/suite/guardians?student={sid}')
        q=GuardianContact.query.filter_by(group_code=_group_code())
        if selected:q=q.filter_by(student_id=selected)
        rows=''.join(f'<tr><td>{c.contact_date}</td><td>{_e((_student(c.student_id).full_name if _student(c.student_id) else ""))}</td><td>{_e(c.contact_type)}</td><td>{_e(c.reason)}</td><td>{_e(c.status)}</td></tr>' for c in q.order_by(GuardianContact.contact_date.desc()).limit(100).all())
        form=''
        if _can_edit(): form=f'''<div class="card"><h2>Nuevo registro</h2><form method="post" class="grid"><label>Alumno<select name="student">{_student_option(selected)}</select></label><label>Fecha<input type="date" name="contact_date" value="{date.today()}"></label><label>Tipo<select name="contact_type"><option>ENTREVISTA</option><option>LLAMADA</option><option>WHATSAPP</option><option>CITATORIO</option><option>OTRO</option></select></label><label>Seguimiento<input type="date" name="followup_date"></label><label class="wide">Motivo<textarea name="reason" required></textarea></label><label class="wide">Acuerdos<textarea name="agreements"></textarea></label><label>Estado<select name="status"><option>PENDIENTE</option><option>EN SEGUIMIENTO</option><option>CUMPLIDO</option><option>CERRADO</option></select></label><div><button>Guardar atención</button></div></form></div>'''
        return _page('Atención a tutores', f'<div class="page-head"><h1>Bitácora de atención a madres, padres y tutores</h1></div>{form}<div class="card scroll"><table><tr><th>Fecha</th><th>Alumno</th><th>Tipo</th><th>Motivo</th><th>Estado</th></tr>{rows}</table></div>')

    # 6. Convivencia avanzada
    @app.route('/suite/behavior', methods=['GET','POST'])
    def suite_behavior():
        if not _uid(): return redirect('/login')
        if request.method=='POST' and _can_edit():
            iid=request.form.get('incident_id',type=int); inc=core.db.session.get(core.Incident,iid)
            if inc:
                rec=IncidentFollowup.query.filter_by(incident_id=iid).first() or IncidentFollowup(incident_id=iid,group_code=_group_code())
                rec.severity=request.form.get('severity','MEDIA');rec.recurrence=request.form.get('recurrence')=='on';rec.measure=request.form.get('measure','');rec.agreement=request.form.get('agreement','');fd=request.form.get('followup_date');rec.followup_date=datetime.strptime(fd,'%Y-%m-%d').date() if fd else None;rec.followup_notes=request.form.get('followup_notes','');rec.resolved=request.form.get('resolved')=='on';rec.updated_at=datetime.utcnow();core.db.session.add(rec);core.db.session.commit();flash('Seguimiento de convivencia actualizado.');return redirect('/suite/behavior')
        rows=''
        for inc in core.Incident.query.order_by(core.Incident.day.desc()).all():
            f=IncidentFollowup.query.filter_by(incident_id=inc.id).first(); sev=f.severity if f else 'SIN CLASIFICAR'; recur='Sí' if f and f.recurrence else 'No'; resolved='Sí' if f and f.resolved else 'No'
            rows+=f'<tr><td>{inc.day}</td><td>{_e(inc.student.full_name if inc.student else "")}</td><td>{_e(inc.category)}</td><td>{_e(sev)}</td><td>{recur}</td><td>{resolved}</td><td><a href="/suite/behavior/{inc.id}">Seguimiento</a></td></tr>'
        return _page('Convivencia avanzada', f'<div class="page-head"><h1>Seguimiento integral de convivencia</h1><p>Amplía las incidencias existentes sin modificar su registro original.</p></div><div class="card scroll"><table><tr><th>Fecha</th><th>Alumno</th><th>Categoría</th><th>Gravedad</th><th>Reincidencia</th><th>Resuelta</th><th></th></tr>{rows}</table></div>')

    @app.route('/suite/behavior/<int:iid>', methods=['GET'])
    def suite_behavior_detail(iid):
        if not _uid(): return redirect('/login')
        inc=core.db.session.get(core.Incident,iid)
        if not inc:return Response('Incidencia no encontrada',404)
        f=IncidentFollowup.query.filter_by(incident_id=iid).first()
        if not _can_edit(): return _page('Seguimiento de convivencia',f'<div class="card"><h1>{_e(inc.category)}</h1><p>{_e(inc.description)}</p><p>Consulta sin permisos de edición.</p></div>')
        sev=f.severity if f else 'MEDIA'; measure=_e(f.measure if f else ''); agreement=_e(f.agreement if f else ''); notes=_e(f.followup_notes if f else ''); fd=f.followup_date if f and f.followup_date else ''
        return _page('Seguimiento de convivencia',f'''<div class="page-head"><h1>Seguimiento de incidencia</h1><p>{_e(inc.student.full_name if inc.student else '')} · {inc.day}</p></div><div class="card"><p><b>{_e(inc.category)}</b>: {_e(inc.description)}</p><form method="post" action="/suite/behavior" class="grid"><input type="hidden" name="incident_id" value="{iid}"><label>Gravedad<select name="severity">{''.join(f'<option {"selected" if x==sev else ""}>{x}</option>' for x in ['BAJA','MEDIA','ALTA','URGENTE'])}</select></label><label style="display:flex;align-items:center;gap:8px"><input style="width:auto" type="checkbox" name="recurrence" {'checked' if f and f.recurrence else ''}> Reincidencia</label><label class="wide">Medida aplicada<textarea name="measure">{measure}</textarea></label><label class="wide">Acuerdo<textarea name="agreement">{agreement}</textarea></label><label>Fecha de seguimiento<input type="date" name="followup_date" value="{fd}"></label><label class="wide">Notas de seguimiento<textarea name="followup_notes">{notes}</textarea></label><label style="display:flex;align-items:center;gap:8px"><input style="width:auto" type="checkbox" name="resolved" {'checked' if f and f.resolved else ''}> Caso resuelto</label><div><button>Guardar seguimiento</button></div></form></div>''')

    # 7. Documentos
    @app.route('/suite/documents')
    def suite_documents():
        if not _uid(): return redirect('/login')
        sid=request.args.get('student',type=int); student=_student(sid) if sid else None
        student_opts='<option value="">Selecciona...</option>'+_student_option(sid)
        actions='<div class="doc-actions"><a href="/attendance/list.xlsx">Lista de asistencia Excel</a><a href="/exports">Centro de exportaciones</a>'
        if student:
            actions+=f'<a href="/suite/document/student/{student.id}" target="_blank">Ficha del alumno</a><a href="/suite/document/citation/{student.id}" target="_blank">Citatorio</a><a href="/suite/document/commitment/{student.id}" target="_blank">Carta compromiso</a>'
        actions+='</div>'
        return _page('Documentos',f'<div class="page-head"><h1>Centro de documentos escolares</h1><p>Reutiliza los datos existentes para evitar volver a capturarlos.</p></div><form method="get" class="card grid"><label>Alumno<select name="student">{student_opts}</select></label><div><button>Mostrar documentos del alumno</button></div></form><div class="card"><h2>Formatos disponibles</h2>{actions}</div>')

    def printable_doc(title, student, body):
        return Response(f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{_e(title)}</title><style>body{{font-family:Arial;margin:35px;color:#222}}h1{{text-align:center;font-size:18px}}.head{{text-align:center;font-size:12px;line-height:1.4}}.signature{{margin-top:80px;display:grid;grid-template-columns:1fr 1fr;gap:70px;text-align:center}}@media print{{button{{display:none}}}}</style></head><body><button onclick="print()">Imprimir</button><div class="head"><b>{_e(core.cfg().school)}</b><br>CCT {_e(core.cfg().cct)} · Ciclo {_e(core.cfg().cycle)} · Grupo {_e(_group_label())}</div><h1>{_e(title)}</h1>{body}<div class="signature"><div>____________________________<br>DOCENTE</div><div>____________________________<br>MADRE, PADRE O TUTOR</div></div></body></html>''',mimetype='text/html')

    @app.route('/suite/document/student/<int:sid>')
    def doc_student(sid):
        if not _uid():return redirect('/login')
        s=_student(sid)
        if not s:return Response('No encontrado',404)
        r=_risk(sid); return printable_doc('FICHA DE SEGUIMIENTO DEL ALUMNO',s,f'<p><b>Alumno:</b> {_e(s.full_name)}</p><p><b>Tutor:</b> {_e(s.tutor)} &nbsp; <b>Teléfono:</b> {_e(s.phone)}</p><p><b>Promedio:</b> {r["avg"] if r["avg"] is not None else "—"} &nbsp; <b>Asistencia:</b> {str(r["att"])+"%" if r["att"] is not None else "—"}</p><p><b>Seguimiento:</b> {_e(r["label"])}. {_e(", ".join(r["reasons"]))}</p>')

    @app.route('/suite/document/citation/<int:sid>')
    def doc_citation(sid):
        if not _uid():return redirect('/login')
        s=_student(sid)
        if not s:return Response('No encontrado',404)
        return printable_doc('CITATORIO',s,f'<p>Por medio del presente se solicita la presencia de la madre, padre o tutor de <b>{_e(s.full_name)}</b> el día __________________ a las __________ horas, para tratar asuntos relacionados con su seguimiento escolar.</p><p>Motivo: ________________________________________________________________________________</p>')

    @app.route('/suite/document/commitment/<int:sid>')
    def doc_commitment(sid):
        if not _uid():return redirect('/login')
        s=_student(sid)
        if not s:return Response('No encontrado',404)
        return printable_doc('CARTA COMPROMISO',s,f'<p>Alumno(a): <b>{_e(s.full_name)}</b></p><p>Después de dialogar sobre la situación escolar, se establecen los siguientes compromisos:</p><p>1. ______________________________________________________________________________________</p><p>2. ______________________________________________________________________________________</p><p>3. ______________________________________________________________________________________</p><p>Fecha de seguimiento: ______________________________</p>')

    # 8. Agenda
    @app.route('/suite/agenda', methods=['GET','POST'])
    def suite_agenda():
        if not _uid():return redirect('/login')
        if request.method=='POST' and _can_edit():
            ed=datetime.strptime(request.form['event_date'],'%Y-%m-%d').date(); rec=SchoolAgenda(group_code=_group_code(),event_date=ed,title=request.form['title'].strip(),category=request.form.get('category','ESCOLAR'),details=request.form.get('details',''),all_groups=request.form.get('all_groups')=='on',created_by=_uid());core.db.session.add(rec);core.db.session.commit();flash('Evento agregado.');return redirect('/suite/agenda')
        q=SchoolAgenda.query.filter((SchoolAgenda.group_code==_group_code()) | (SchoolAgenda.all_groups==True)).order_by(SchoolAgenda.event_date.asc()).all()
        rows=''.join(f'<tr><td>{e.event_date}</td><td>{_e(e.title)}</td><td>{_e(e.category)}</td><td>{_e(e.details)}</td></tr>' for e in q)
        form=''
        if _can_edit():form=f'<div class="card"><form method="post" class="grid"><label>Fecha<input type="date" name="event_date" value="{date.today()}" required></label><label>Título<input name="title" required></label><label>Categoría<select name="category"><option>ESCOLAR</option><option>EVALUACIÓN</option><option>REUNIÓN</option><option>CTE</option><option>ADMINISTRATIVO</option><option>PROYECTO</option></select></label><label class="wide">Detalles<textarea name="details"></textarea></label><label style="display:flex;align-items:center;gap:8px"><input style="width:auto" type="checkbox" name="all_groups"> Visible en todos los grupos</label><div><button>Agregar evento</button></div></form></div>'
        return _page('Agenda',f'<div class="page-head"><h1>Agenda docente y escolar</h1></div>{form}<div class="card scroll"><table><tr><th>Fecha</th><th>Evento</th><th>Categoría</th><th>Detalles</th></tr>{rows}</table></div>')

    # 9. Analítica
    @app.route('/suite/analytics')
    def suite_analytics():
        if not _uid():return redirect('/login')
        data=[(s,_risk(s.id)) for s in _students()]; total=len(data); red=sum(1 for _,r in data if r['level']=='RED'); orange=sum(1 for _,r in data if r['level']=='ORANGE'); yellow=sum(1 for _,r in data if r['level']=='YELLOW'); green=sum(1 for _,r in data if r['level']=='GREEN'); avgs=[r['avg'] for _,r in data if r['avg'] is not None]; atts=[r['att'] for _,r in data if r['att'] is not None]
        avg_group=round(sum(avgs)/len(avgs),2) if avgs else None; att_group=round(sum(atts)/len(atts),1) if atts else None; pending=sum(r['missing'] for _,r in data); open_inc=sum(r['incidents'] for _,r in data)
        risk_rows=''.join(f'<tr><td>{_e(s.full_name)}</td><td>{r["avg"] if r["avg"] is not None else "—"}</td><td>{str(r["att"])+"%" if r["att"] is not None else "—"}</td><td>{r["missing"]}</td><td><span class="risk-pill risk-{r["level"]}">{_e(r["label"])}</span></td></tr>' for s,r in sorted(data,key=lambda x:x[1]['score'],reverse=True))
        return _page('Estadísticas',f'<div class="page-head"><h1>Centro de reportes y estadísticas</h1><p>Indicadores del grupo {_e(_group_label())}.</p></div><div class="metric-row"><div class="metric-box">Alumnos<br><b>{total}</b></div><div class="metric-box">Promedio grupal<br><b>{avg_group if avg_group is not None else "—"}</b></div><div class="metric-box">Asistencia media<br><b>{str(att_group)+"%" if att_group is not None else "—"}</b></div><div class="metric-box">Pendientes detectados<br><b>{pending}</b></div></div><div class="card"><h2>Distribución de alertas</h2><p><span class="risk-pill risk-GREEN">Sin riesgo {green}</span> <span class="risk-pill risk-YELLOW">Atención {yellow}</span> <span class="risk-pill risk-ORANGE">Riesgo {orange}</span> <span class="risk-pill risk-RED">Prioritaria {red}</span></p><p>Incidencias abiertas acumuladas: <b>{open_inc}</b></p></div><div class="card scroll"><table><tr><th>Alumno</th><th>Promedio</th><th>Asistencia</th><th>Pendientes</th><th>Alerta</th></tr>{risk_rows}</table></div>')

    # 10. Planeación didáctica
    @app.route('/suite/planning', methods=['GET','POST'])
    def suite_planning():
        if not _uid():return redirect('/login')
        if request.method=='POST' and _can_edit():
            sd=datetime.strptime(request.form['start_date'],'%Y-%m-%d').date();ed=datetime.strptime(request.form['end_date'],'%Y-%m-%d').date();rec=PlanningRecord(group_code=_group_code(),field=request.form.get('field','Lenguajes'),project=request.form['project'].strip(),partial_projects=request.form.get('partial_projects',''),start_date=sd,end_date=ed,session_minutes=request.form.get('session_minutes',type=int) or 90,non_working_days=request.form.get('non_working_days',''),group_observations=request.form.get('group_observations',''),purpose=request.form.get('purpose',''),stages=request.form.get('stages',''),resources=request.form.get('resources',''),assessment=request.form.get('assessment',''),created_by=_uid());core.db.session.add(rec);core.db.session.commit();flash('Planeación registrada.');return redirect('/suite/planning')
        rows=''.join(f'<tr><td>{p.start_date} – {p.end_date}</td><td>{_e(p.field)}</td><td>{_e(p.project)}</td><td>{p.session_minutes} min</td><td><a href="/suite/planning/{p.id}">Ver</a></td></tr>' for p in PlanningRecord.query.filter_by(group_code=_group_code()).order_by(PlanningRecord.start_date.desc()).all())
        form=''
        if _can_edit():form=f'''<div class="card"><h2>Nueva planeación estructurada</h2><p class="muted">Este módulo organiza la planeación; no sustituye el contenido oficial de los libros de proyectos ni inventa etapas que no hayan sido capturadas.</p><form method="post" class="grid"><label>Campo formativo<select name="field">{''.join(f'<option>{_e(x)}</option>' for x in core.FIELDS)}</select></label><label>Proyecto<input name="project" required placeholder="Ej. PPA 1"></label><label>Proyectos académicos / parciales<input name="partial_projects" placeholder="Ej. PA 1, 2 y 3"></label><label>Inicio<input type="date" name="start_date" required></label><label>Término<input type="date" name="end_date" required></label><label>Duración por sesión (min)<input type="number" name="session_minutes" value="90"></label><label class="wide">Días inhábiles / suspensiones<input name="non_working_days"></label><label class="wide">Observaciones del grupo<textarea name="group_observations"></textarea></label><label class="wide">Propósito / intención<textarea name="purpose"></textarea></label><label class="wide">Etapas tal como aparecen en la fuente<textarea name="stages" placeholder="Captura o pega las etapas oficiales"></textarea></label><label class="wide">Recursos específicos<textarea name="resources"></textarea></label><label class="wide">Evaluación / rúbricas<textarea name="assessment"></textarea></label><div><button>Guardar planeación</button></div></form></div>'''
        return _page('Planeación didáctica',f'<div class="page-head"><h1>Planeación didáctica integrada</h1><p>Grupo {_e(_group_label())}. Conserva un historial de planeaciones sin modificar actividades ni calificaciones.</p></div>{form}<div class="card scroll"><table><tr><th>Periodo</th><th>Campo</th><th>Proyecto</th><th>Sesión</th><th></th></tr>{rows}</table></div>')

    @app.route('/suite/planning/<int:pid>')
    def suite_planning_detail(pid):
        if not _uid():return redirect('/login')
        p=core.db.session.get(PlanningRecord,pid)
        if not p:return Response('No encontrada',404)
        return _page('Planeación',f'<div class="page-head"><h1>{_e(p.project)}</h1><p>{p.start_date} – {p.end_date} · {_e(p.field)}</p></div><div class="card"><h2>Proyectos académicos / parciales</h2><p>{_e(p.partial_projects)}</p><h2>Propósito</h2><p>{_e(p.purpose)}</p><h2>Etapas</h2><p style="white-space:pre-wrap">{_e(p.stages)}</p><h2>Recursos</h2><p style="white-space:pre-wrap">{_e(p.resources)}</p><h2>Evaluación</h2><p style="white-space:pre-wrap">{_e(p.assessment)}</p><h2>Observaciones del grupo</h2><p style="white-space:pre-wrap">{_e(p.group_observations)}</p></div>')

    # 11. Evidencias
    @app.route('/suite/evidence', methods=['GET','POST'])
    def suite_evidence():
        if not _uid():return redirect('/login')
        selected=request.values.get('student',type=int)
        if request.method=='POST' and _can_edit():
            sid=request.form.get('student',type=int); f=request.files.get('file')
            if not sid or not f or not f.filename: flash('Selecciona alumno y archivo.'); return redirect('/suite/evidence')
            data=f.read(8*1024*1024+1)
            if not data or len(data)>8*1024*1024: flash('El archivo debe pesar menos de 8 MB.'); return redirect('/suite/evidence')
            mime=(f.mimetype or 'application/octet-stream')[:100]
            allowed=('image/','application/pdf','application/vnd.openxmlformats-officedocument','application/msword','text/plain')
            if not (mime.startswith('image/') or any(mime.startswith(x) for x in allowed[1:])): flash('Tipo de archivo no permitido.'); return redirect('/suite/evidence')
            rec=StudentEvidence(student_id=sid,group_code=_group_code(),evidence_date=datetime.strptime(request.form.get('evidence_date') or str(date.today()),'%Y-%m-%d').date(),category=request.form.get('category','PRODUCTO'),title=request.form.get('title','').strip() or f.filename,notes=request.form.get('notes',''),filename=os.path.basename(f.filename)[:220],mime=mime,data=data,created_by=_uid());core.db.session.add(rec);core.db.session.commit();flash('Evidencia guardada.');return redirect(f'/suite/evidence?student={sid}')
        q=StudentEvidence.query.filter_by(group_code=_group_code())
        if selected:q=q.filter_by(student_id=selected)
        cards=''.join(f'<div class="evidence-card"><b>{_e(e.title)}</b><small>{e.evidence_date} · {_e(e.category)}</small><p class="muted">{_e((_student(e.student_id).full_name if _student(e.student_id) else ""))}</p><a href="/suite/evidence/{e.id}/download">Abrir / descargar</a></div>' for e in q.order_by(StudentEvidence.evidence_date.desc()).limit(100).all())
        form=''
        if _can_edit():form=f'''<div class="card"><h2>Agregar evidencia</h2><form method="post" enctype="multipart/form-data" class="grid"><label>Alumno<select name="student">{_student_option(selected)}</select></label><label>Fecha<input type="date" name="evidence_date" value="{date.today()}"></label><label>Categoría<select name="category"><option>PRODUCTO</option><option>PROYECTO</option><option>RÚBRICA</option><option>INCIDENCIA</option><option>DIAGNÓSTICO</option><option>OTRO</option></select></label><label>Título<input name="title"></label><label class="wide">Archivo<input type="file" name="file" required></label><label class="wide">Notas<textarea name="notes"></textarea></label><div><button>Guardar evidencia</button></div></form></div>'''
        return _page('Portafolio de evidencias',f'<div class="page-head"><h1>Portafolio de evidencias</h1><p>Archivos vinculados al alumno y al grupo activo.</p></div>{form}<div class="card"><div class="portfolio-grid">{cards or "<p class=muted>Sin evidencias registradas.</p>"}</div></div>')

    @app.route('/suite/evidence/<int:eid>/download')
    def evidence_download(eid):
        if not _uid():return redirect('/login')
        e=core.db.session.get(StudentEvidence,eid)
        if not e or e.group_code!=_group_code():return Response('No encontrado',404)
        return send_file(io.BytesIO(bytes(e.data)),as_attachment=False,download_name=e.filename,mimetype=e.mime)

    # Inyección de acceso único, sin reemplazar enlaces existentes.
    @app.after_request
    def integral_suite_ui(response):
        if not _uid() or 'text/html' not in response.headers.get('Content-Type',''):
            return response
        html=response.get_data(as_text=True)
        if 'href="/suite"' not in html:
            link='<a class="nav-link" href="/suite"><span class="nav-icon">◇</span><span>Seguimiento integral</span></a>'
            marker='<a class="nav-link" href="/account/profile"'
            if marker in html: html=html.replace(marker,link+marker,1)
            else:
                marker='<a class="nav-link" href="/users"'
                if marker in html:html=html.replace(marker,link+marker,1)
                else:
                    marker='<a class="nav-link" href="/config"'
                    if marker in html:html=html.replace(marker,link+marker,1)
        response.set_data(html);response.headers['Content-Length']=str(len(response.get_data()));return response
