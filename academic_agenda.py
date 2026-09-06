import calendar
from datetime import date, datetime, timedelta
from html import escape

from flask import request, session, redirect, flash

import app as core
import multi_user


class AcademicAgendaItem(core.db.Model):
    __tablename__ = 'academic_agenda_item'
    id = core.db.Column(core.db.Integer, primary_key=True)
    event_date = core.db.Column(core.db.Date, nullable=False, index=True)
    end_date = core.db.Column(core.db.Date, nullable=True)
    title = core.db.Column(core.db.String(220), nullable=False)
    category = core.db.Column(core.db.String(50), default='PENDIENTE', nullable=False)
    details = core.db.Column(core.db.Text, default='')
    completed = core.db.Column(core.db.Boolean, default=False, nullable=False)
    institutional = core.db.Column(core.db.Boolean, default=False, nullable=False)
    created_by = core.db.Column(core.db.Integer, nullable=True)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


# Calendario federal ya cargado + Agenda Estatal de Telesecundarias Puebla 2026-2027.
SEP_EVENTS = [
 ('2026-08-31','Inicio de clases','SEP'),('2026-09-07','Jornada de concientización sobre la gravedad del abuso sexual y el maltrato infantil','SEP'),('2026-09-16','Suspensión de labores docentes','SEP'),('2026-09-25','Consejo Técnico Escolar · sesión ordinaria','CTE'),('2026-10-30','Consejo Técnico Escolar · sesión ordinaria','CTE'),('2026-11-02','Suspensión de labores docentes','SEP'),('2026-11-13','Registro de calificaciones','EVALUACIÓN'),('2026-11-16','Suspensión de labores docentes','SEP'),('2026-11-23','Comunicación de resultados de evaluación · inicia periodo','EVALUACIÓN'),('2026-11-26','Comunicación de resultados de evaluación · concluye periodo','EVALUACIÓN'),('2026-11-27','Consejo Técnico Escolar · sesión ordinaria','CTE'),('2026-12-21','Receso escolar · inicia','RECESO'),('2027-01-05','Receso escolar · concluye','RECESO'),('2027-01-06','Suspensión de labores docentes','SEP'),('2027-01-29','Consejo Técnico Escolar · sesión ordinaria','CTE'),('2027-02-01','Suspensión de labores docentes','SEP'),('2027-02-02','Preinscripciones 2027–2028 · inicia periodo','SEP'),('2027-02-12','Preinscripciones 2027–2028 · concluye periodo','SEP'),('2027-02-26','Consejo Técnico Escolar · sesión ordinaria','CTE'),('2027-03-05','Registro de calificaciones','EVALUACIÓN'),('2027-03-15','Suspensión de labores docentes','SEP'),('2027-03-16','Comunicación de resultados de evaluación · inicia periodo','EVALUACIÓN'),('2027-03-19','Comunicación de resultados de evaluación · concluye periodo','EVALUACIÓN'),('2027-03-22','Receso escolar · inicia','RECESO'),('2027-04-02','Receso escolar · concluye','RECESO'),('2027-04-30','Consejo Técnico Escolar · sesión ordinaria','CTE'),('2027-05-05','Suspensión de labores docentes','SEP'),('2027-05-28','Consejo Técnico Escolar · sesión ordinaria','CTE'),('2027-06-25','Consejo Técnico Escolar · sesión ordinaria','CTE'),('2027-07-02','Registro de calificaciones','EVALUACIÓN'),('2027-07-08','Comunicación de resultados de evaluación · inicia periodo','EVALUACIÓN'),('2027-07-09','Fin de clases y comunicación de resultados · concluye periodo','SEP')]

# Fechas leídas del calendario oficial de la Dirección de Telesecundarias del Estado de Puebla.
TELESEC_EVENTS = [
 ('2026-09-11','Encuentro Estatal de Vinculación Virtual con Directoras y Directores de Telesecundaria','TELESECUNDARIA'),
 ('2026-10-02','Encuentro Estatal y Análisis Colegiado por Zona Escolar de los PIC','TELESECUNDARIA'),
 ('2026-10-09','Academia Estatal de Fortalecimiento Pedagógico e Innovación Educativa','TELESECUNDARIA'),
 ('2026-10-19','Aniversario de la fundación del Sistema de Telesecundarias','TELESECUNDARIA'),
 ('2026-11-06','Diálogos Pedagógicos · fortalecimiento e innovación de la práctica docente','TELESECUNDARIA'),
 ('2026-11-09','Encuentro Estatal de Vinculación Virtual con Directoras y Directores','TELESECUNDARIA'),
 ('2026-11-18','Organización del avance de los proyectos','TELESECUNDARIA'),
 ('2026-11-19','Presentación del avance de Proyectos','TELESECUNDARIA'),
 ('2026-11-20','45.º Aniversario de las Telesecundarias Estatales · Programa Gabino Barreda','TELESECUNDARIA'),
 ('2026-12-04','Jornadas Deportivas Regionales y Estatal del Personal de Telesecundaria','TELESECUNDARIA'),
 ('2026-12-11','Trayecto Estatal de Profesionalización Docente · Líderes Innovadores Estatales','TELESECUNDARIA'),
 ('2027-01-15','Taller de Inducción para Docentes de Nuevo Ingreso a Telesecundaria','TELESECUNDARIA'),
 ('2027-01-18','Encuentro Estatal de Vinculación Virtual con Directoras y Directores','TELESECUNDARIA'),
 ('2027-01-21','Aniversario de la fundación del Sistema de Telesecundarias','TELESECUNDARIA'),
 ('2027-01-22','Presentación del avance de Proyectos','TELESECUNDARIA'),
 ('2027-02-24','Fecha conmemorativa · referente para reflexión y periódico mural','CONMEMORATIVA'),
 ('2027-03-08','Foro Estatal de Directoras y Directores de Telesecundaria','TELESECUNDARIA'),
 ('2027-03-11','Organización del avance de los proyectos','TELESECUNDARIA'),
 ('2027-03-12','Presentación del avance de Proyectos','TELESECUNDARIA'),
 ('2027-04-09','Jornadas Deportivas Regionales y Estatal del Personal de Telesecundaria','TELESECUNDARIA'),
 ('2027-04-16','Academia Estatal de Fortalecimiento Pedagógico e Innovación Educativa','TELESECUNDARIA'),
 ('2027-04-29','Fecha conmemorativa · referente para reflexión y periódico mural','CONMEMORATIVA'),
 ('2027-05-12','Encuentro Estatal de Vinculación Virtual con Directoras y Directores','TELESECUNDARIA'),
 ('2027-05-21','Diálogos Pedagógicos · fortalecimiento e innovación de la práctica docente','TELESECUNDARIA'),
 ('2027-06-11','Jornadas Deportivas Regionales y Estatal del Personal de Telesecundaria','TELESECUNDARIA'),
 ('2027-06-18','Trayecto Estatal de Profesionalización Docente · Líderes Innovadores Estatales','TELESECUNDARIA'),
 ('2027-06-23','Organización del avance de los proyectos','TELESECUNDARIA'),
 ('2027-06-24','45.º Aniversario de las Telesecundarias Estatales · Programa Gabino Barreda','TELESECUNDARIA'),
]


def _e(v): return escape(str(v or ''))
def _profile():
    uid=session.get('uid'); return multi_user._profile(uid) if uid else None
def _can_edit():
    p=_profile(); return bool(p and p.active and p.role in ('ADMIN','DIRECCION','DOCENTE'))


def _seed_defaults():
    for raw,title,category in SEP_EVENTS + TELESEC_EVENTS:
        d=date.fromisoformat(raw)
        if not AcademicAgendaItem.query.filter_by(event_date=d,title=title,institutional=True).first():
            core.db.session.add(AcademicAgendaItem(event_date=d,title=title,category=category,institutional=True,details='Calendario institucional precargado.'))
    for year,month in [(2026,m) for m in range(8,13)]+[(2027,m) for m in range(1,8)]:
        d=date(year,month,25); title='Día Naranja · acciones por la eliminación de la violencia contra mujeres y niñas'
        if not AcademicAgendaItem.query.filter_by(event_date=d,title=title,institutional=True).first(): core.db.session.add(AcademicAgendaItem(event_date=d,title=title,category='DÍA NARANJA',institutional=True))
    for year,month in [(2026,m) for m in range(9,13)]+[(2027,m) for m in range(1,8)]:
        d1,d2=date(year,month,1),date(year,month,10); title='Entrega mensual · Informe de Igualdad de Género y No Discriminación'
        if not AcademicAgendaItem.query.filter_by(event_date=d1,title=title,institutional=True).first(): core.db.session.add(AcademicAgendaItem(event_date=d1,end_date=d2,title=title,category='INFORME',details='Periodo de entrega: primeros 10 días del mes.',institutional=True))
    core.db.session.commit()


def _month_shift(y,m,delta):
    i=y*12+m-1+delta; return i//12,i%12+1


def _calendar_html(year,month,rows):
    by_day={}
    for item in rows: by_day.setdefault(item.event_date.day,[]).append(item)
    weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(year,month); today=date.today(); body=''
    for week in weeks:
        body+='<tr>'
        for day in week:
            if not day: body+='<td class="empty"></td>'; continue
            d=date(year,month,day); items=by_day.get(day,[])
            chips=''.join(f'<div class="agenda-chip">{_e(i.title)}</div>' for i in items[:3]); more=f'<small>+{len(items)-3} más</small>' if len(items)>3 else ''
            # Un clic sobre cualquier día abre el formulario rápido ya fechado.
            body+=f'<td class="agenda-day {"today" if d==today else ""}" data-date="{d.isoformat()}" onclick="agendaPickDate(\'{d.isoformat()}\')"><div class="day-top"><b>{day}</b><button type="button" class="day-add" aria-label="Agregar pendiente el {day}">＋</button></div>{chips}{more}</td>'
        body+='</tr>'
    heads=''.join(f'<th>{x}</th>' for x in ('Lun','Mar','Mié','Jue','Vie','Sáb','Dom'))
    return f'<div class="agenda-calendar"><table><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>'


def _page(year,month,selected_date=None):
    start=date(year,month,1); end=date(year,month,calendar.monthrange(year,month)[1])
    rows=AcademicAgendaItem.query.filter(AcademicAgendaItem.event_date.between(start,end)).order_by(AcademicAgendaItem.event_date,AcademicAgendaItem.id).all()
    upcoming=AcademicAgendaItem.query.filter(AcademicAgendaItem.event_date>=date.today(),AcademicAgendaItem.completed.is_(False)).order_by(AcademicAgendaItem.event_date).limit(14).all()
    py,pm=_month_shift(year,month,-1); ny,nm=_month_shift(year,month,1); months=['','Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    chosen=selected_date or date.today().isoformat()
    edit=''
    if _can_edit():
        edit=f'''<div class="card quick-card" id="agenda-quick"><div class="quick-title"><div><h2>Agregar pendiente</h2><p>Haz clic en cualquier fecha del calendario y escribe la actividad.</p></div><b id="picked-date-label">{_e(chosen)}</b></div><form method="post" action="/agenda/create" class="agenda-form"><label>Fecha<input id="agenda-event-date" type="date" name="event_date" value="{_e(chosen)}" required></label><label>Título<input id="agenda-title" name="title" maxlength="220" placeholder="Ej. Entregar informe, reunión, ensayo…" required></label><label>Categoría<select name="category"><option>PENDIENTE</option><option>REUNIÓN</option><option>ENTREGA</option><option>EVALUACIÓN</option><option>EVENTO</option><option>PERSONAL</option></select></label><label>Hasta (opcional)<input type="date" name="end_date"></label><label class="wide">Detalles<textarea name="details" rows="2" placeholder="Notas opcionales"></textarea></label><div><button>＋ Guardar pendiente</button></div></form></div>'''
    cards=''
    for i in upcoming:
        span=f' al {i.end_date.strftime("%d/%m/%Y")}' if i.end_date else ''; action=''
        if _can_edit() and not i.institutional: action=f'<form method="post" action="/agenda/{i.id}/complete"><button class="btn alt">✓ Realizada</button></form>'
        cards+=f'<div class="agenda-next"><div><b>{i.event_date.strftime("%d/%m/%Y")}{span}</b><span>{_e(i.category)}</span><strong>{_e(i.title)}</strong><small>{_e(i.details)}</small></div>{action}</div>'
    css='''<style>.agenda-head,.quick-title{display:flex;justify-content:space-between;align-items:center;gap:12px}.agenda-head a{text-decoration:none;font-weight:850;font-size:20px}.quick-title p{margin:0;color:#746a6d}.quick-title h2{margin-bottom:3px}.quick-title>b{background:#7b1024;color:white;padding:7px 11px;border-radius:999px}.agenda-layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:14px}.agenda-calendar{overflow:auto}.agenda-calendar table{table-layout:fixed;min-width:720px}.agenda-calendar td{height:118px;vertical-align:top;padding:7px}.agenda-day{cursor:pointer;transition:.15s}.agenda-day:hover{background:#fff8e8}.agenda-calendar td.today{outline:2px solid #7b1024;outline-offset:-2px}.agenda-calendar td.empty{background:#faf8f8}.day-top{display:flex;justify-content:space-between;align-items:center}.day-add{border:0!important;background:#f1e5e8!important;color:#7b1024!important;width:25px!important;height:25px!important;min-height:25px!important;padding:0!important;border-radius:50%!important;font-size:17px!important;box-shadow:none!important}.agenda-chip{margin-top:4px;padding:4px 5px;border-radius:6px;background:#f5edef;font-size:9px;line-height:1.2}.agenda-form{display:grid;grid-template-columns:1fr 2fr 1fr 1fr;gap:10px}.agenda-form .wide{grid-column:span 3}.agenda-next{display:flex;justify-content:space-between;gap:8px;padding:10px 0;border-bottom:1px solid #eee}.agenda-next b,.agenda-next strong,.agenda-next small{display:block}.agenda-next span{display:inline-block;margin:3px 0;font-size:9px;font-weight:850;color:#7b1024}.agenda-next small{color:#746a6d}@media(max-width:850px){.agenda-layout{grid-template-columns:1fr}.agenda-form{grid-template-columns:1fr}.agenda-form .wide{grid-column:auto}.quick-title{align-items:flex-start}.agenda-calendar td{height:95px}}</style><script>function agendaPickDate(d){var f=document.getElementById('agenda-event-date'),l=document.getElementById('picked-date-label'),t=document.getElementById('agenda-title');if(f)f.value=d;if(l)l.textContent=d;if(t){t.focus();}var q=document.getElementById('agenda-quick');if(q)q.scrollIntoView({behavior:'smooth',block:'start'});}</script>'''
    body=f'''{css}<div class="page-head"><h1>Agenda</h1><p>Calendario SEP + Agenda Estatal de Telesecundarias Puebla + pendientes y recordatorios institucionales.</p></div>{edit}<div class="agenda-layout"><div class="card"><div class="agenda-head"><a href="/agenda?year={py}&month={pm}">‹</a><h2>{months[month]} {year}</h2><a href="/agenda?year={ny}&month={nm}">›</a></div>{_calendar_html(year,month,rows)}</div><div class="card"><h2>Próximos pendientes</h2>{cards or '<p class="muted">No hay pendientes próximos.</p>'}</div></div>'''
    return core.page('Agenda',body)


def install(app):
    with app.app_context(): core.db.create_all(); _seed_defaults()
    @app.get('/agenda')
    def academic_agenda_home():
        if not session.get('uid'): return redirect('/login')
        today=date.today()
        try:
            year=int(request.args.get('year',today.year)); month=int(request.args.get('month',today.month)); selected=request.args.get('date') or None
            if month<1 or month>12: raise ValueError
        except ValueError: year,month,selected=today.year,today.month,None
        return _page(year,month,selected)
    @app.post('/agenda/create')
    def academic_agenda_create():
        if not session.get('uid') or not _can_edit(): flash('Tu perfil tiene acceso de consulta a la agenda.'); return redirect('/agenda')
        try:
            d=date.fromisoformat(request.form.get('event_date','')); raw=request.form.get('end_date','').strip(); end=date.fromisoformat(raw) if raw else None
        except ValueError: flash('Revisa las fechas.'); return redirect('/agenda')
        title=request.form.get('title','').strip()
        if not title: flash('Escribe el nombre de la actividad.'); return redirect('/agenda')
        core.db.session.add(AcademicAgendaItem(event_date=d,end_date=end,title=title,category=request.form.get('category','PENDIENTE')[:50],details=request.form.get('details','').strip(),created_by=session.get('uid'))); core.db.session.commit(); flash('Actividad agregada a la agenda.'); return redirect(f'/agenda?year={d.year}&month={d.month}')
    @app.post('/agenda/<int:item_id>/complete')
    def academic_agenda_complete(item_id):
        if not _can_edit(): return redirect('/agenda')
        item=core.db.session.get(AcademicAgendaItem,item_id)
        if item and not item.institutional: item.completed=True; core.db.session.commit(); flash('Actividad marcada como realizada.')
        return redirect(request.referrer or '/agenda')
    @app.after_request
    def agenda_notifications(response):
        if 'text/html' not in response.headers.get('Content-Type','') or not session.get('uid'): return response
        html=response.get_data(as_text=True); today=date.today(); limit=today+timedelta(days=7); due=AcademicAgendaItem.query.filter(AcademicAgendaItem.event_date.between(today,limit),AcademicAgendaItem.completed.is_(False)).count()
        if due and '<main' in html and request.path!='/agenda':
            note=f'<a href="/agenda" class="agenda-global-notice" style="display:block;margin:0 0 10px;padding:9px 12px;border-radius:10px;background:#fff4d8;color:#6b4d00;text-decoration:none;font-weight:800">🔔 Agenda: {due} actividad(es) o recordatorio(s) en los próximos 7 días.</a>'; pos=html.find('>',html.find('<main'))+1; html=html[:pos]+note+html[pos:]
        response.set_data(html); response.headers['Content-Length']=str(len(response.get_data())); return response
