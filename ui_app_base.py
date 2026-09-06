# Redeploy estable 2026-09-05: restaura la plantilla de acceso sin CSS incrustado en f-string.
import calendar as cal
import base64
from datetime import date

import app as core
from flask import render_template_string, request, Response
from logo_data import LOGO_DATA
from ui_theme import CSS

app = core.app
MONTHS = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


@app.route('/school-logo')
def school_logo():
    payload = LOGO_DATA.split(',', 1)[1] if ',' in LOGO_DATA else LOGO_DATA
    return Response(base64.b64decode(payload), mimetype='image/webp', headers={'Cache-Control': 'public, max-age=86400'})


def nav_link(href, icon, label):
    active = request.path == href or (href != '/' and request.path.startswith(href))
    return f'<a class="nav-link{" active" if active else ""}" href="{href}"><span class="nav-icon">{icon}</span><span>{label}</span></a>'


def calendar_widget():
    today = date.today()
    weeks = cal.Calendar(firstweekday=0).monthdayscalendar(today.year, today.month)
    cells = ''
    for week in weeks:
        for day_num in week:
            if not day_num:
                cells += '<span class="cal-day muted-day"></span>'
            elif day_num == today.day:
                cells += f'<span class="cal-day today">{day_num}</span>'
            else:
                cells += f'<span class="cal-day">{day_num}</span>'
    return f'''<div class="calendar-head"><button type="button" class="ghost-btn">‹</button><strong>{MONTHS[today.month]} {today.year}</strong><button type="button" class="ghost-btn">›</button></div><div class="cal-week"><span>L</span><span>M</span><span>M</span><span>J</span><span>V</span><span>S</span><span>D</span></div><div class="cal-grid">{cells}</div>'''


def attendance_series():
    days = [row[0] for row in core.db.session.query(core.Attendance.day).distinct().order_by(core.Attendance.day.desc()).limit(5).all()]
    days.reverse()
    values = []
    for current_day in days:
        total = core.Attendance.query.filter_by(day=current_day).count()
        present = core.Attendance.query.filter(core.Attendance.day == current_day, core.Attendance.state.in_(['PRESENTE', 'RETARDO'])).count()
        values.append(round(present * 100 / total, 1) if total else 0)
    return days, values


def line_chart(days, values):
    if not days:
        return '<div class="empty-chart">Registra asistencia para visualizar la tendencia semanal.</div>'
    width, height, px, py = 600, 180, 24, 18
    usable_w, usable_h = width - px * 2, height - py * 2
    span = max(len(values) - 1, 1)
    points, circles = [], []
    for index, value in enumerate(values):
        x = px + (usable_w * index / span if len(values) > 1 else usable_w / 2)
        y = py + usable_h * (1 - max(0, min(100, value)) / 100)
        points.append(f'{x:.1f},{y:.1f}')
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5"/>')
    labels = ''.join(f'<span>{d.strftime("%d/%m")}</span>' for d in days)
    return f'''<div class="chart-wrap"><svg class="line-chart" viewBox="0 0 600 180" preserveAspectRatio="none"><line x1="24" y1="18" x2="576" y2="18"/><line x1="24" y1="90" x2="576" y2="90"/><line x1="24" y1="162" x2="576" y2="162"/><polyline points="{' '.join(points)}"/>{''.join(circles)}</svg><div class="chart-labels">{labels}</div></div>'''


def page(title, body):
    c = core.cfg()
    logged = bool(core.auth())
    tpl = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#7b1024"><title>{{{{title}}}} · Sistema Integral Escolar</title><style>{CSS}</style></head><body>'''

    if logged:
        nav = f'''<aside class="sidebar" id="sidebar"><div class="brand-card"><img src="/school-logo?v=20260901" alt="Logo de la escuela"></div><nav class="side-nav">{nav_link('/', '⌂', 'Inicio')}{nav_link('/students','♟','Alumnos')}{nav_link('/subjects','▤','Asignaturas')}{nav_link('/activities','▥','Actividades y calificaciones')}{nav_link('/attendance','✓','Asistencia')}{nav_link('/incidents','!','Incidencias')}{nav_link('/config','⚙','Configuración')}<a class="nav-link logout" href="/logout"><span class="nav-icon">↪</span><span>Cerrar sesión</span></a></nav><div class="sidebar-art"><div class="sidebar-wave"></div></div></aside>'''
        current = request.path
        def mobile_item(href, icon, label):
            active = current == href or (href != '/' and current.startswith(href))
            return f'<a class="{"active" if active else ""}" href="{href}"><i>{icon}</i><span>{label}</span></a>'
        mobile_nav = ''.join([
            mobile_item('/', '⌂', 'Inicio'), mobile_item('/students', '♟', 'Alumnos'),
            mobile_item('/attendance', '✓', 'Asistencia'), mobile_item('/activities', '▥', 'Calificar'),
            mobile_item('/config', '•••', 'Más')
        ])
        tpl += f'''<div class="app-shell">{nav}<div class="overlay" id="overlay" onclick="toggleSidebar()"></div><section class="main-area"><header class="topbar"><div class="title-block"><button class="drawer-toggle" type="button" onclick="toggleSidebar()">☰</button><div class="mini-mark">▤</div><div class="title-copy"><strong>SISTEMA INTEGRAL ESCOLAR</strong><small>{{{{c.school}}}}</small></div></div><div class="top-meta"><div class="cycle">▣ <span>Ciclo Escolar {{{{c.cycle}}}}</span>⌄</div><div class="bell">♢</div><div class="admin-box"><div class="avatar">A</div><div class="admin-copy"><b>Administrador</b><small>Rol: Administrador</small></div></div></div></header><div class="mobile-top"><span>☰</span><b>Sistema Escolar</b><span>♢</span></div><div class="mobile-brand"><img src="/school-logo?v=20260901" alt="Logo de la escuela"></div><main class="wrap">{{% with ms=get_flashed_messages() %}}{{% for m in ms %}}<div class="alert">{{{{m}}}}</div>{{% endfor %}}{{% endwith %}}{body}<footer class="footer"><span><strong>▣</strong> Sistema Integral Escolar &nbsp; • &nbsp; {{{{c.school}}}} &nbsp; • &nbsp; Beristain, Ahuazotepec, Puebla</span><span>© 2026 Todos los derechos reservados.</span></footer></main></section><nav class="bottom-nav">{mobile_nav}</nav></div><script>function toggleSidebar(){{document.getElementById('sidebar').classList.toggle('open');document.getElementById('overlay').classList.toggle('open')}}</script>'''
    else:
        tpl += f'''<div class="login-layout"><section class="login-brand"><div class="login-logo-box"><img src="/school-logo?v=20260901" alt="Logo de la escuela"></div></section><section class="login-pane"><div class="login-pane-inner">{{% with ms=get_flashed_messages() %}}{{% for m in ms %}}<div class="alert">{{{{m}}}}</div>{{% endfor %}}{{% endwith %}}{body}</div></section></div>'''

    tpl += '</body></html>'
    return render_template_string(tpl, title=title, c=c)


core.page = page


def dashboard():
    redirect_response = core.require()
    if redirect_response:
        return redirect_response

    students = core.Student.query.filter_by(status='ACTIVO').all()
    subjects = core.Subject.query.count()
    activities = core.Activity.query.count()
    open_incidents = core.Incident.query.filter_by(status='ABIERTA').count()
    total_att = core.Attendance.query.count()
    present_att = core.Attendance.query.filter(core.Attendance.state.in_(['PRESENTE', 'RETARDO'])).count()
    attendance_pct = round(present_att * 100 / total_att, 1) if total_att else 0
    days, values = attendance_series()

    upcoming = core.Activity.query.filter(core.Activity.activity_date >= date.today()).order_by(core.Activity.activity_date).limit(3).all()
    events = ''.join(f'<div class="event"><span class="event-dot"></span><div><b>{a.name}</b><small>{a.activity_date.strftime("%d/%m/%Y")} · {a.subject.name if a.subject else "Actividad"}</small></div></div>' for a in upcoming)
    if not events:
        events = '<div class="muted" style="padding:8px 0">No hay eventos próximos registrados.</div>'

    recent = []
    last_activity = core.Activity.query.order_by(core.Activity.activity_date.desc()).first()
    last_attendance = core.Attendance.query.order_by(core.Attendance.day.desc()).first()
    last_incident = core.Incident.query.order_by(core.Incident.day.desc()).first()
    if last_activity:
        recent.append(('▥', 'Actividad registrada', last_activity.name, last_activity.activity_date.strftime('%d/%m')))
    if last_attendance:
        recent.append(('✓', 'Asistencia registrada', last_attendance.day.strftime('%d/%m/%Y'), ''))
    if last_incident:
        recent.append(('!', 'Incidencia registrada', last_incident.student.full_name if last_incident.student else last_incident.category, last_incident.day.strftime('%d/%m')))
    recent_html = ''.join(f'<div class="recent-item"><span class="recent-badge">{icon}</span><div><b>{label}</b><br><small>{detail}</small></div><span class="recent-time">{when}</span></div>' for icon, label, detail, when in recent) or '<div class="muted" style="padding:20px 0">Aún no hay actividad reciente.</div>'

    body = f'''<div class="dashboard-grid"><section class="dashboard-main"><section class="panel hero-panel"><div class="hero-copy"><h1>¡Bienvenido, Administrador!</h1><span class="hero-rule"></span><p>Gestiona y administra toda la información escolar de manera segura, rápida y eficiente.</p></div><div class="hero-brand"><img src="/school-logo?v=20260901" alt="Benito Juárez"><div><div class="quote-mark">“</div><div class="quote-text">Entre los individuos, como entre las naciones, el respeto al derecho ajeno es la paz.</div><div class="quote-author">Benito Juárez</div></div></div></section><section class="stats"><div class="stat-card"><span class="stat-icon">♟</span><div><div class="stat-label">Alumnos</div><div class="kpi">{len(students)}</div><div class="stat-sub">Activos</div></div></div><div class="stat-card"><span class="stat-icon gold">▤</span><div><div class="stat-label">Asignaturas</div><div class="kpi">{subjects}</div><div class="stat-sub gold">Registradas</div></div></div><div class="stat-card"><span class="stat-icon">▥</span><div><div class="stat-label">Actividades</div><div class="kpi">{activities}</div><div class="stat-sub">Creadas</div></div></div><div class="stat-card"><span class="stat-icon gold">!</span><div><div class="stat-label">Incidencias</div><div class="kpi">{open_incidents}</div><div class="stat-sub gold">Abiertas</div></div></div></section><section class="panel quick-panel"><h2>Acciones rápidas</h2><div class="quick"><a href="/students"><span class="quick-icon">♟＋</span><span>Nuevo alumno</span></a><a href="/attendance"><span class="quick-icon">✓</span><span>Registrar asistencia</span></a><a href="/incidents"><span class="quick-icon">!</span><span>Nueva incidencia</span></a><a href="/activities"><span class="quick-icon">☆</span><span>Capturar calificaciones</span></a><a href="/subjects"><span class="quick-icon">▤</span><span>Asignaturas</span></a><a href="/config"><span class="quick-icon">➤</span><span>Configuración</span></a></div></section><section class="analytics-row"><div class="panel analytics-card"><div class="analytics-head"><h2>Resumen de asistencias <span class="muted">(últimos registros)</span></h2></div>{line_chart(days, values)}</div><div class="panel analytics-card"><h2>Asistencia promedio</h2><div class="ring-wrap"><div class="ring" style="--pct:{attendance_pct}%"><div class="ring-copy"><b>{attendance_pct}%</b><span>Asistencia<br>promedio</span></div></div><div class="trend">↑<small>seguimiento<br>acumulado</small></div></div></div></section><section class="panel"><div class="analytics-head"><h2>Actividad reciente</h2></div><div class="recent-list">{recent_html}</div></section></section><aside class="right-rail"><section class="panel calendar-card"><div class="calendar-title">▣ <span>Calendario escolar</span></div>{calendar_widget()}</section><section class="panel"><div class="analytics-head"><h2>Eventos próximos</h2><span class="muted">Ver todos</span></div>{events}</section></aside></div>'''
    return page('Inicio', body)


app.view_functions['dashboard'] = dashboard