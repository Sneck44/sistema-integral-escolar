from datetime import date
from html import escape

from flask import request, session, redirect, flash, Response
from sqlalchemy import select

import app as core
import multi_user
import group_workspaces as gw


class ClubSport(core.db.Model):
    __tablename__ = 'club_sport'
    id = core.db.Column(core.db.Integer, primary_key=True)
    name = core.db.Column(core.db.String(120), nullable=False)
    kind = core.db.Column(core.db.String(30), default='CLUB')
    teacher_user_id = core.db.Column(core.db.Integer, nullable=False, index=True)
    active = core.db.Column(core.db.Boolean, default=True)


class ClubMember(core.db.Model):
    __tablename__ = 'club_member'
    id = core.db.Column(core.db.Integer, primary_key=True)
    club_id = core.db.Column(core.db.Integer, core.db.ForeignKey('club_sport.id'), nullable=False, index=True)
    student_id = core.db.Column(core.db.Integer, nullable=False, index=True)
    group_code = core.db.Column(core.db.String(8), nullable=False, index=True)
    active = core.db.Column(core.db.Boolean, default=True)
    __table_args__ = (core.db.UniqueConstraint('club_id','student_id', name='uq_club_member_student'),)


class ClubAttendance(core.db.Model):
    __tablename__ = 'club_attendance'
    id = core.db.Column(core.db.Integer, primary_key=True)
    club_id = core.db.Column(core.db.Integer, nullable=False, index=True)
    student_id = core.db.Column(core.db.Integer, nullable=False, index=True)
    day = core.db.Column(core.db.Date, nullable=False, default=date.today)
    state = core.db.Column(core.db.String(20), default='PRESENTE')
    notes = core.db.Column(core.db.String(250), default='')
    __table_args__ = (core.db.UniqueConstraint('club_id','student_id','day', name='uq_club_attendance'),)


class ClubEvaluation(core.db.Model):
    __tablename__ = 'club_evaluation'
    id = core.db.Column(core.db.Integer, primary_key=True)
    club_id = core.db.Column(core.db.Integer, nullable=False, index=True)
    student_id = core.db.Column(core.db.Integer, nullable=False, index=True)
    period = core.db.Column(core.db.String(40), nullable=False, default='PRIMER TRIMESTRE')
    attendance_pts = core.db.Column(core.db.Integer, default=25)
    materials_pts = core.db.Column(core.db.Integer, default=15)
    delivery_pts = core.db.Column(core.db.Integer, default=20)
    quality_pts = core.db.Column(core.db.Integer, default=25)
    participation_pts = core.db.Column(core.db.Integer, default=15)
    extra_pts = core.db.Column(core.db.Integer, default=0)
    notes = core.db.Column(core.db.Text, default='')
    updated_at = core.db.Column(core.db.Date, default=date.today)
    __table_args__ = (core.db.UniqueConstraint('club_id','student_id','period', name='uq_club_evaluation'),)


PERIODS = ['PRIMER TRIMESTRE','SEGUNDO TRIMESTRE','TERCER TRIMESTRE']
RUBRIC = {
 'attendance_pts': [('25','25 · 90–100% puntual'),('20','20 · 80–89%'),('15','15 · 70–79% o hasta 3 retardos'),('5','5 · <70% o 4+ retardos')],
 'materials_pts': [('15','15 · 90–100%'),('12','12 · 80–89%'),('8','8 · 70–79%'),('3','3 · <70%')],
 'delivery_pts': [('20','20 · 100% en fecha'),('16','16 · 80–99%; máx. 1 tardía'),('10','10 · 60–79% o 2 tardías'),('4','4 · <60% o 3+ tardías')],
 'quality_pts': [('25','25 · completo, ordenado y con dominio'),('20','20 · mayoría; una omisión menor'),('14','14 · 2–3 requisitos incompletos'),('6','6 · <mitad o sin terminar')],
 'participation_pts': [('15','15 · 90–100%; coopera y respeta'),('12','12 · 80–89%; máx. 1 recordatorio'),('8','8 · 60–79%; recordatorios frecuentes'),('3','3 · <60% o incumple reglas')],
 'extra_pts': [('0','0 · Sin extra'),('3','+3 · Participa; requiere apoyo'),('5','+5 · Cumple función, horario, uniforme y materiales'),('8','+8 · Además asiste a todos los ensayos'),('10','+10 · Coordina, representa, monta o apoya al equipo')],
}


def _profile():
    uid=session.get('uid'); return multi_user._profile(uid) if uid else None


def _allowed(club=None):
    p=_profile()
    if not p or not p.active: return False
    if p.role in ('ADMIN','DIRECCION','USAER'): return True
    return p.role=='DOCENTE' and (club is None or club.teacher_user_id==session.get('uid'))


def _all_students():
    students=core.db.session.execute(select(core.Student).execution_options(group_scope_disabled=True)).scalars().all()
    tags=core.db.session.execute(select(gw.RecordGroup).where(gw.RecordGroup.entity_type=='student').execution_options(group_scope_disabled=True)).scalars().all()
    group_by={x.entity_id:x.group_code for x in tags}
    return [(s,group_by.get(s.id,'1A')) for s in students if getattr(s,'status','ACTIVO')=='ACTIVO']


def _student_map(): return {s.id:(s,g) for s,g in _all_students()}


def _clubs_for_user():
    p=_profile(); q=ClubSport.query.filter_by(active=True)
    if p and p.role=='DOCENTE': q=q.filter_by(teacher_user_id=session.get('uid'))
    return q.order_by(ClubSport.name).all()


def _layout(title, body):
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>
    :root{{--wine:#74142b;--wine2:#4f0d1d;--gold:#caa45f;--ink:#17233b;--bg:#f5f7fb}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:var(--ink)}}header{{background:linear-gradient(135deg,var(--wine2),var(--wine));color:white;padding:18px 4vw}}header a{{color:white;text-decoration:none;font-weight:800}}main{{max-width:1450px;margin:auto;padding:22px}}.card{{background:white;border:1px solid #e3e7ef;border-radius:16px;padding:18px;margin-bottom:16px;box-shadow:0 8px 24px #17233b0b}}h1,h2{{margin-top:0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}}label{{font-size:12px;font-weight:800}}input,select,textarea{{width:100%;padding:10px;border:1px solid #ccd3df;border-radius:9px;background:white}}button,.btn{{border:0;border-radius:9px;padding:10px 14px;background:var(--wine);color:white;font-weight:800;text-decoration:none;display:inline-block;cursor:pointer}}.btn.alt{{background:white;color:var(--wine);border:1px solid var(--wine)}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:9px;border-bottom:1px solid #e5e8ef;text-align:left;vertical-align:top}}th{{background:#f0f3f8}}.scroll{{overflow:auto}}.pill{{display:inline-block;padding:4px 8px;border-radius:99px;background:#f7e9ed;color:var(--wine);font-weight:800}}.actions{{display:flex;gap:8px;flex-wrap:wrap}}.muted{{color:#6c7483}}@media(max-width:700px){{main{{padding:12px}}table{{min-width:900px}}}}@media print{{header,.no-print{{display:none!important}}body{{background:white}}main{{max-width:none;padding:0}}.card{{box-shadow:none;border:0}}}}
    </style></head><body><header><a href="/">← Sistema Escolar</a> &nbsp; / &nbsp; <b>Evaluación · Clubes y Deportes</b></header><main><h1>{escape(title)}</h1>{body}</main></body></html>'''


def _select(name, value):
    return '<select name="%s">%s</select>'%(name,''.join(f'<option value="{v}" {"selected" if str(value)==v else ""}>{escape(t)}</option>' for v,t in RUBRIC[name]))


def install(app):
    with app.app_context(): core.db.create_all()

    @app.route('/clubs')
    def clubs_home():
        if not _allowed(): return redirect('/')
        clubs=_clubs_for_user()
        rows=''.join(f'<tr><td><b>{escape(c.name)}</b><br><span class="pill">{escape(c.kind)}</span></td><td>{ClubMember.query.filter_by(club_id=c.id,active=True).count()}</td><td class="actions"><a class="btn" href="/clubs/{c.id}">Abrir</a><a class="btn alt" href="/clubs/{c.id}/print" target="_blank">Lista imprimible</a></td></tr>' for c in clubs)
        create='''<form method="post" action="/clubs/create" class="grid"><div><label>Nombre del club o deporte</label><input name="name" required placeholder="Ej. Banda de guerra, Fútbol"></div><div><label>Tipo</label><select name="kind"><option>CLUB</option><option>DEPORTE</option></select></div><div style="align-self:end"><button>Crear</button></div></form>'''
        body=f'<div class="card"><h2>Mis clubes y deportes</h2><p class="muted">Crea tu lista con estudiantes de cualquier grupo de la escuela, toma asistencia y evalúa con la rúbrica institucional.</p>{create}</div><div class="card scroll"><table><tr><th>Club / deporte</th><th>Integrantes</th><th>Acciones</th></tr>{rows or "<tr><td colspan=3>Aún no hay clubes o deportes.</td></tr>"}</table></div><div class="card"><a class="btn alt" href="/clubs/group-summary">Calificaciones e informes para maestro titular</a></div>'
        return _layout('Evaluación de Clubes y Deportes',body)

    @app.post('/clubs/create')
    def clubs_create():
        if not _allowed(): return redirect('/')
        name=request.form.get('name','').strip(); kind=request.form.get('kind','CLUB').strip()
        if name:
            core.db.session.add(ClubSport(name=name,kind=kind,teacher_user_id=session['uid'])); core.db.session.commit()
        return redirect('/clubs')

    @app.route('/clubs/<int:cid>', methods=['GET','POST'])
    def club_detail(cid):
        club=core.db.session.get(ClubSport,cid)
        if not club or not _allowed(club): return redirect('/clubs')
        if request.method=='POST':
            selected={int(x) for x in request.form.getlist('student_id') if x.isdigit()}
            existing={m.student_id:m for m in ClubMember.query.filter_by(club_id=cid).all()}
            smap=_student_map()
            for sid in selected:
                if sid not in smap: continue
                if sid in existing: existing[sid].active=True
                else: core.db.session.add(ClubMember(club_id=cid,student_id=sid,group_code=smap[sid][1],active=True))
            for sid,m in existing.items():
                if sid not in selected: m.active=False
            core.db.session.commit(); flash('Lista actualizada.')
        members={m.student_id:m for m in ClubMember.query.filter_by(club_id=cid,active=True).all()}
        opts=''.join(f'<label style="display:block;padding:7px;border-bottom:1px solid #eee"><input style="width:auto" type="checkbox" name="student_id" value="{s.id}" {"checked" if s.id in members else ""}> {escape(s.full_name)} · {escape(g)}</label>' for s,g in _all_students())
        body=f'''<div class="card"><div class="actions no-print"><a class="btn" href="/clubs/{cid}/attendance">Pase de lista</a><a class="btn" href="/clubs/{cid}/evaluate">Evaluar con rúbrica</a><a class="btn alt" href="/clubs/{cid}/print" target="_blank">Lista imprimible</a></div><h2>{escape(club.name)}</h2><p>{len(members)} estudiante(s) seleccionado(s).</p></div><form method="post" class="card"><h2>Seleccionar estudiantes de toda la escuela</h2><div style="max-height:520px;overflow:auto">{opts}</div><br><button>Guardar lista</button></form>'''
        return _layout(club.name,body)

    @app.route('/clubs/<int:cid>/attendance', methods=['GET','POST'])
    def club_attendance(cid):
        club=core.db.session.get(ClubSport,cid)
        if not club or not _allowed(club): return redirect('/clubs')
        try: day=date.fromisoformat(request.values.get('day',date.today().isoformat()))
        except: day=date.today()
        members=ClubMember.query.filter_by(club_id=cid,active=True).all(); smap=_student_map()
        if request.method=='POST':
            for m in members:
                state=request.form.get(f's_{m.student_id}','PRESENTE')
                row=ClubAttendance.query.filter_by(club_id=cid,student_id=m.student_id,day=day).first()
                if not row: row=ClubAttendance(club_id=cid,student_id=m.student_id,day=day); core.db.session.add(row)
                row.state=state
            core.db.session.commit(); flash('Asistencia guardada.')
        saved={x.student_id:x.state for x in ClubAttendance.query.filter_by(club_id=cid,day=day).all()}
        rows=''.join(f'<tr><td>{escape(smap[m.student_id][0].full_name)}</td><td>{escape(m.group_code)}</td><td><select name="s_{m.student_id}">'+''.join(f'<option {"selected" if saved.get(m.student_id,"PRESENTE")==v else ""}>{v}</option>' for v in ['PRESENTE','RETARDO','JUSTIFICADA','FALTA'])+'</select></td></tr>' for m in members if m.student_id in smap)
        body=f'<form method="post"><div class="card no-print"><label>Fecha</label><input type="date" name="day" value="{day.isoformat()}" onchange="location.href=\'/clubs/{cid}/attendance?day=\'+this.value"></div><div class="card scroll"><table><tr><th>Estudiante</th><th>Grupo</th><th>Asistencia</th></tr>{rows}</table><br><button>Guardar pase de lista</button></div></form>'
        return _layout('Pase de lista · '+club.name,body)

    @app.route('/clubs/<int:cid>/evaluate', methods=['GET','POST'])
    def club_evaluate(cid):
        club=core.db.session.get(ClubSport,cid)
        if not club or not _allowed(club): return redirect('/clubs')
        period=request.values.get('period','PRIMER TRIMESTRE')
        if period not in PERIODS: period=PERIODS[0]
        members=ClubMember.query.filter_by(club_id=cid,active=True).all(); smap=_student_map()
        if request.method=='POST':
            for m in members:
                row=ClubEvaluation.query.filter_by(club_id=cid,student_id=m.student_id,period=period).first()
                if not row: row=ClubEvaluation(club_id=cid,student_id=m.student_id,period=period); core.db.session.add(row)
                for field in RUBRIC:
                    try: setattr(row,field,int(request.form.get(f'{field}_{m.student_id}',0)))
                    except: pass
                row.notes=request.form.get(f'notes_{m.student_id}','').strip(); row.updated_at=date.today()
            core.db.session.commit(); flash('Evaluación guardada y disponible para los maestros titulares.')
        evals={e.student_id:e for e in ClubEvaluation.query.filter_by(club_id=cid,period=period).all()}
        rows=[]
        for m in members:
            if m.student_id not in smap: continue
            e=evals.get(m.student_id) or ClubEvaluation()
            ordinary=sum(int(getattr(e,f,0) or 0) for f in ['attendance_pts','materials_pts','delivery_pts','quality_pts','participation_pts']); extra=int(getattr(e,'extra_pts',0) or 0); final=min(10,(ordinary+extra)/10)
            cells=''.join(f'<td>{_select(f,getattr(e,f,0) or 0).replace("name=\""+f+"\"","name=\""+f+"_"+str(m.student_id)+"\"")}</td>' for f in RUBRIC)
            rows.append(f'<tr><td><b>{escape(smap[m.student_id][0].full_name)}</b><br>{escape(m.group_code)}</td>{cells}<td><b>{ordinary}/100</b></td><td><b>{final:.1f}</b></td><td><input name="notes_{m.student_id}" value="{escape(getattr(e,"notes","") or "")}"></td></tr>')
        pselect=''.join(f'<option {"selected" if p==period else ""}>{p}</option>' for p in PERIODS)
        body=f'''<div class="card"><h2>Rúbrica institucional</h2><p>Asistencia 25 · Materiales/uniforme 15 · Entrega 20 · Calidad/desempeño 25 · Participación/colaboración/disciplina 15. Extra por eventos: +3, +5, +8 o +10. Calificación final máxima: 10.</p></div><form method="post"><div class="card no-print"><label>Periodo</label><select name="period" onchange="location.href='?period='+encodeURIComponent(this.value)">{pselect}</select></div><div class="card scroll"><table><tr><th>Estudiante</th><th>Asistencia</th><th>Materiales</th><th>Entrega</th><th>Calidad</th><th>Participación</th><th>Extra</th><th>Total</th><th>Calif.</th><th>Observaciones</th></tr>{''.join(rows)}</table><br><button>Guardar evaluaciones</button></div></form>'''
        return _layout('Evaluación · '+club.name,body)

    @app.route('/clubs/<int:cid>/print')
    def club_print(cid):
        club=core.db.session.get(ClubSport,cid)
        if not club or not _allowed(club): return redirect('/clubs')
        smap=_student_map(); members=ClubMember.query.filter_by(club_id=cid,active=True).all()
        rows=''.join(f'<tr><td>{i}</td><td>{escape(smap[m.student_id][0].full_name)}</td><td>{escape(m.group_code)}</td><td style="height:34px"></td><td></td><td></td><td></td></tr>' for i,m in enumerate(members,1) if m.student_id in smap)
        body=f'<div class="card"><h2>{escape(club.name)}</h2><p>Lista de asistencia y seguimiento</p><div class="scroll"><table><tr><th>#</th><th>Estudiante</th><th>Grupo</th><th>Fecha / asistencia</th><th>Fecha / asistencia</th><th>Fecha / asistencia</th><th>Observaciones</th></tr>{rows}</table></div><p>Responsable: ______________________________ &nbsp;&nbsp; Firma: ____________________</p><button class="no-print" onclick="print()">Imprimir</button></div>'
        return _layout('Lista · '+club.name,body)

    @app.route('/clubs/group-summary')
    def club_group_summary():
        p=_profile()
        if not p or not p.active: return redirect('/')
        code=gw.active_group_code() or '1A'; smap=_student_map(); member_rows=ClubMember.query.filter_by(group_code=code,active=True).all(); mids={m.student_id for m in member_rows}
        evaluations=ClubEvaluation.query.filter(ClubEvaluation.student_id.in_(mids)).all() if mids else []
        clubs={c.id:c for c in ClubSport.query.all()}; rows=[]
        for e in evaluations:
            if e.student_id not in smap: continue
            ordinary=sum(getattr(e,f,0) or 0 for f in ['attendance_pts','materials_pts','delivery_pts','quality_pts','participation_pts']); final=min(10,(ordinary+(e.extra_pts or 0))/10)
            rows.append(f'<tr><td>{escape(smap[e.student_id][0].full_name)}</td><td>{escape(clubs[e.club_id].name if e.club_id in clubs else "Club")}</td><td>{escape(e.period)}</td><td>{ordinary}/100</td><td>{e.extra_pts or 0}</td><td><b>{final:.1f}</b></td><td>{escape(e.notes or "")}</td></tr>')
        body=f'<div class="card"><h2>Grupo titular {escape(code)}</h2><p class="muted">Aquí aparecen automáticamente las evaluaciones de clubes y deportes de estudiantes pertenecientes a tu grupo.</p></div><div class="card scroll"><table><tr><th>Estudiante</th><th>Club/deporte</th><th>Periodo</th><th>Puntaje</th><th>Extra</th><th>Calificación</th><th>Informe/observaciones</th></tr>{"".join(rows) or "<tr><td colspan=7>Sin evaluaciones registradas todavía.</td></tr>"}</table><br><button class="no-print" onclick="print()">Imprimir informe</button></div>'
        return _layout('Informe de Clubes y Deportes',body)

    @app.after_request
    def clubs_navigation(response):
        if 'text/html' not in response.headers.get('Content-Type','') or not session.get('uid'): return response
        html=response.get_data(as_text=True)
        link='<a class="nav-link%s" href="/clubs"><span class="nav-icon">★</span><span>Clubes y deportes</span></a>' % (' active' if request.path.startswith('/clubs') else '')
        if '<nav class="side-nav">' in html and 'href="/clubs"' not in html:
            marker='<a class="nav-link logout" href="/logout">'; html=html.replace(marker,link+marker,1)
        if request.path=='/' and 'Evaluación de Clubes y Deportes' not in html and '<main class="wrap">' in html:
            card='<div class="card" style="margin-bottom:16px"><h2>Evaluación de Clubes y Deportes</h2><p class="muted">Listas de integrantes, asistencia, rúbrica institucional e informes para docentes titulares.</p><a class="btn" href="/clubs">Abrir módulo</a></div>'
            html=html.replace('<main class="wrap">','<main class="wrap">'+card,1)
        response.set_data(html); response.headers['Content-Length']=str(len(response.get_data())); return response
