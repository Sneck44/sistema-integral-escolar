import calendar as cal
from datetime import date, timedelta
from flask import request

import ui_app_base as ui

app = ui.app

# Un único origen para el logo. La ruta /school-logo la resuelve entry.py.
STATIC_LOGO = '/school-logo?v=20260902-finalpng'

MONTHS = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
          'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

SEP_EVENTS = {}

def add_event(d, kind, label):
    SEP_EVENTS.setdefault(d, []).append((kind, label))

def add_range(start, end, kind, label):
    d = start
    while d <= end:
        add_event(d, kind, label)
        d += timedelta(days=1)

# Calendario SEP 2026-2027 para educación básica (185 días).
add_range(date(2026, 8, 24), date(2026, 8, 28), 'intensive', 'CTE · Fase intensiva')
add_event(date(2026, 8, 31), 'start', 'Inicio de clases')
add_event(date(2026, 9, 7), 'awareness', 'Jornada de concientización sobre abuso sexual y maltrato infantil')
for d in [date(2026,9,25), date(2026,10,30), date(2026,11,27),
          date(2027,1,29), date(2027,2,26), date(2027,4,30),
          date(2027,5,28), date(2027,6,25)]:
    add_event(d, 'cte', 'Consejo Técnico Escolar')
for d in [date(2026,9,16), date(2026,11,2), date(2026,11,16), date(2026,12,25),
          date(2027,1,1), date(2027,1,6), date(2027,2,1), date(2027,3,15), date(2027,5,5)]:
    add_event(d, 'suspension', 'Suspensión de labores docentes')
add_range(date(2026,12,21), date(2027,1,5), 'recess', 'Receso de clases')
add_range(date(2027,3,22), date(2027,4,3), 'recess', 'Receso de clases')
add_range(date(2027,2,2), date(2027,2,12), 'pre', 'Preinscripciones 2027-2028')
add_event(date(2027,7,9), 'end', 'Fin de clases')

COLORS = {
    'start': '#24934d', 'end': '#7b1024', 'suspension': '#c51631',
    'cte': '#7b1024', 'intensive': '#8d5b9f', 'recess': '#caa45f',
    'pre': '#3a78b8', 'awareness': '#d17835',
}

LEGEND = [
    ('start', 'Inicio/fin'), ('suspension', 'Suspensión'), ('cte', 'CTE'),
    ('recess', 'Receso'), ('pre', 'Preinscripción'), ('awareness', 'Jornada SEP')
]

def month_from_request():
    raw = request.args.get('cal', '').strip()
    if raw:
        try:
            y, m = map(int, raw.split('-'))
            if (2026, 8) <= (y, m) <= (2027, 7):
                return y, m
        except (ValueError, TypeError):
            pass
    today = date.today()
    if today < date(2026, 8, 1):
        return 2026, 8
    if today > date(2027, 7, 31):
        return 2027, 7
    return today.year, today.month

def shift_month(y, m, delta):
    n = y * 12 + (m - 1) + delta
    return n // 12, n % 12 + 1

def calendar_widget():
    y, m = month_from_request()
    prev_y, prev_m = shift_month(y, m, -1)
    next_y, next_m = shift_month(y, m, 1)
    prev_href = f'?cal={prev_y:04d}-{prev_m:02d}' if (prev_y, prev_m) >= (2026, 8) else '#'
    next_href = f'?cal={next_y:04d}-{next_m:02d}' if (next_y, next_m) <= (2027, 7) else '#'
    today = date.today()
    cells = ''
    month_events = []
    seen = set()
    for week in cal.Calendar(firstweekday=0).monthdayscalendar(y, m):
        for day_num in week:
            if not day_num:
                cells += '<span class="cal-day muted-day"></span>'
                continue
            d = date(y, m, day_num)
            events = SEP_EVENTS.get(d, [])
            title = ' · '.join(label for _, label in events)
            style = ''
            if events:
                color = COLORS.get(events[0][0], '#7b1024')
                style = f'background:{color};color:#fff;font-weight:800;box-shadow:0 2px 7px {color}55;'
                for kind, label in events:
                    key = (label, kind)
                    if key not in seen:
                        month_events.append((d, kind, label))
                        seen.add(key)
            if d == today:
                style += 'outline:2px solid #211b1d;outline-offset:2px;'
            cells += f'<span class="cal-day" style="{style}" title="{title}">{day_num}</span>'
    legend = ''.join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;margin:3px 8px 3px 0;font-size:10px;color:#5f5659"><i style="width:8px;height:8px;border-radius:50%;background:{COLORS[k]};display:inline-block"></i>{label}</span>'
        for k, label in LEGEND
    )
    details = ''
    for d, kind, label in sorted(month_events, key=lambda x: x[0]):
        details += f'<div style="display:grid;grid-template-columns:9px 1fr;gap:8px;padding:5px 0;align-items:start"><i style="width:8px;height:8px;border-radius:50%;margin-top:4px;background:{COLORS[kind]}"></i><div style="font-size:10px;line-height:1.35"><b>{d.day} de {MONTHS[m].lower()}</b> · {label}</div></div>'
    if not details:
        details = '<div class="muted" style="font-size:10px;padding-top:6px">Sin fechas SEP destacadas este mes.</div>'
    return f'''<div class="calendar-head"><a class="ghost-btn" href="{prev_href}" style="display:grid;place-items:center;text-decoration:none">‹</a><strong>{MONTHS[m]} {y}</strong><a class="ghost-btn" href="{next_href}" style="display:grid;place-items:center;text-decoration:none">›</a></div><div class="cal-week"><span>L</span><span>M</span><span>M</span><span>J</span><span>V</span><span>S</span><span>D</span></div><div class="cal-grid">{cells}</div><div style="border-top:1px solid #eee8e6;margin-top:10px;padding-top:8px">{legend}</div><div style="border-top:1px solid #f1ecea;margin-top:7px;padding-top:7px"><b style="font-size:11px;color:#7b1024">Fechas SEP del mes</b>{details}</div>'''

ui.calendar_widget = calendar_widget

# Todas las pantallas usan la misma ruta física del logo.
_original_page = ui.page

def page(title, body):
    for old_logo in (
        '/school-logo?v=20260901',
        '/static/logo-school.jpeg?v=20260901-final',
        '/school-logo-final?v=20260902',
    ):
        body = body.replace(old_logo, STATIC_LOGO)
    response = _original_page(title, body)
    if isinstance(response, str):
        for old_logo in (
            '/school-logo?v=20260901',
            '/static/logo-school.jpeg?v=20260901-final',
            '/school-logo-final?v=20260902',
        ):
            response = response.replace(old_logo, STATIC_LOGO)
    return response

ui.page = page
ui.core.page = page
app.view_functions['dashboard'] = ui.dashboard
