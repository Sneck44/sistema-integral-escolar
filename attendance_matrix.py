from datetime import date, datetime, timedelta
from html import escape
from urllib.parse import urlencode

from flask import flash, redirect, request, session

import app as core
import multi_user


STATE_META = {
    'PRESENTE': ('P', 'Presente'),
    'AUSENTE': ('A', 'Ausente'),
    'RETARDO': ('R', 'Retardo'),
    'JUSTIFICADA': ('J', 'Justificada'),
}
WEEKDAYS = ('Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom')
MAX_RANGE_DAYS = 31


def _parse_day(raw, fallback):
    try:
        return datetime.strptime((raw or '').strip(), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return fallback


def _range_from_request():
    today = date.today()
    legacy_day = request.values.get('day')
    default_start = today.replace(day=1)
    start = _parse_day(request.values.get('from') or legacy_day, default_start)
    end = _parse_day(request.values.get('to') or legacy_day, today)
    messages = []

    if end > today:
        end = today
        messages.append('La fecha final se ajustó a hoy; no se capturan asistencias futuras.')
    if start > end:
        start = end
        messages.append('La fecha inicial se ajustó para conservar un rango válido.')
    if (end - start).days >= MAX_RANGE_DAYS:
        start = end - timedelta(days=MAX_RANGE_DAYS - 1)
        messages.append(f'La vista se limita a {MAX_RANGE_DAYS} días para mantener la tabla legible.')
    return start, end, messages


def _dates_in_range(start, end, recorded_days):
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5 or current in recorded_days:
            days.append(current)
        current += timedelta(days=1)
    return days


def _state_options(selected, compact=False):
    empty_label = '—' if compact else '— Sin registro —'
    options = [f'<option value="">{empty_label}</option>']
    for value, (symbol, label) in STATE_META.items():
        text = symbol if compact else label
        is_selected = ' selected' if selected == value else ''
        options.append(f'<option value="{value}"{is_selected}>{text}</option>')
    return ''.join(options)


def _can_edit():
    profile = multi_user._profile(session.get('uid'))
    return not profile or profile.role in ('ADMIN', 'DOCENTE')


def _query_records(start, end, student_ids):
    if not student_ids:
        return []
    return core.Attendance.query.filter(
        core.Attendance.day.between(start, end),
        core.Attendance.student_id.in_(student_ids),
    ).all()


def _redirect_to_range(start, end, detail_day=None):
    params = {'from': start.isoformat(), 'to': end.isoformat()}
    if detail_day:
        params['detail_day'] = detail_day.isoformat()
    return redirect('/attendance?' + urlencode(params))


def _save_matrix(students, start, end):
    allowed_dates = {
        _parse_day(raw, None)
        for raw in request.form.get('matrix_dates', '').split(',')
        if raw.strip()
    }
    allowed_dates = {
        day for day in allowed_dates
        if day is not None and start <= day <= end and day <= date.today()
    }
    if not allowed_dates:
        flash('No se recibieron fechas válidas para guardar.')
        return _redirect_to_range(start, end)

    student_ids = [student.id for student in students]
    existing = {
        (item.student_id, item.day): item
        for item in _query_records(min(allowed_dates), max(allowed_dates), student_ids)
    }
    saved = 0
    created = 0
    for student in students:
        for day in allowed_dates:
            raw = request.form.get(f'a_{student.id}_{day:%Y%m%d}', '').strip().upper()
            if raw not in STATE_META:
                continue
            item = existing.get((student.id, day))
            if item is None:
                item = core.Attendance(day=day, student_id=student.id)
                core.db.session.add(item)
                existing[(student.id, day)] = item
                created += 1
            if item.state != raw or item.id is None:
                item.state = raw
                saved += 1
    core.db.session.commit()
    if saved:
        flash(f'Asistencia actualizada: {saved} registro(s), {created} nuevo(s).')
    else:
        flash('No hubo cambios de asistencia por guardar.')
    return _redirect_to_range(start, end)


def _save_detail(students, start, end):
    detail_day = _parse_day(request.form.get('detail_day'), date.today())
    if detail_day > date.today():
        flash('No se puede registrar asistencia en una fecha futura.')
        return _redirect_to_range(start, end)

    existing = {
        item.student_id: item
        for item in _query_records(detail_day, detail_day, [student.id for student in students])
    }
    saved = 0
    for student in students:
        state = request.form.get(f'ds_{student.id}', '').strip().upper()
        if state not in STATE_META:
            continue
        item = existing.get(student.id)
        if item is None:
            item = core.Attendance(day=detail_day, student_id=student.id)
            core.db.session.add(item)
        item.state = state
        item.notes = request.form.get(f'dn_{student.id}', '').strip()[:250]
        saved += 1
    core.db.session.commit()
    flash(f'Captura detallada guardada para {saved} alumno(s).')
    return _redirect_to_range(start, end, detail_day)


def _summary_card(label, value, note, css_class=''):
    return (
        f'<div class="attendance-kpi {css_class}">'
        f'<span>{escape(label)}</span><b>{escape(str(value))}</b><small>{escape(note)}</small>'
        '</div>'
    )


def _attendance_view():
    auth_redirect = core.require()
    if auth_redirect:
        return auth_redirect

    start, end, range_messages = _range_from_request()
    students = core.Student.query.filter_by(status='ACTIVO').order_by(
        core.Student.list_no, core.Student.paternal, core.Student.maternal, core.Student.names
    ).all()
    can_edit = _can_edit()

    if request.method == 'POST':
        if not can_edit:
            flash('Tu cuenta puede consultar la asistencia, pero no modificarla.')
            return _redirect_to_range(start, end)
        if request.form.get('attendance_action') == 'save_detail':
            return _save_detail(students, start, end)
        return _save_matrix(students, start, end)

    student_ids = [student.id for student in students]
    records = _query_records(start, end, student_ids)
    recorded_days = {item.day for item in records}
    days = _dates_in_range(start, end, recorded_days)
    by_key = {(item.student_id, item.day): item for item in records}

    totals = {state: 0 for state in STATE_META}
    for item in records:
        if item.state in totals and item.day in days:
            totals[item.state] += 1
    expected = len(students) * len(days)
    captured = sum(totals.values())
    missing = max(expected - captured, 0)
    attendance_count = totals['PRESENTE'] + totals['RETARDO'] + totals['JUSTIFICADA']
    attendance_pct = round(attendance_count * 100 / captured, 1) if captured else 0

    head_days = ''.join(
        f'<th class="date-col" title="{WEEKDAYS[day.weekday()]} {day:%d/%m/%Y}">'
        f'<span>{WEEKDAYS[day.weekday()]}</span><b>{day:%d/%m}</b></th>'
        for day in days
    )
    matrix_rows = []
    for student in students:
        student_records = [by_key.get((student.id, day)) for day in days]
        student_captured = sum(1 for item in student_records if item and item.state in STATE_META)
        student_attends = sum(
            1 for item in student_records
            if item and item.state in ('PRESENTE', 'RETARDO', 'JUSTIFICADA')
        )
        student_pct = round(student_attends * 100 / student_captured) if student_captured else None
        student_missing = len(days) - student_captured
        cells = []
        for day, item in zip(days, student_records):
            selected = item.state if item and item.state in STATE_META else ''
            disabled = ' disabled' if not can_edit else ''
            field = f'a_{student.id}_{day:%Y%m%d}'
            aria = f'{student.full_name}, {day:%d/%m/%Y}'
            cells.append(
                f'<td class="state-cell" data-missing="{str(not selected).lower()}">'
                f'<select class="attendance-state" name="{field}" data-state="{selected}" '
                f'aria-label="{escape(aria, quote=True)}" title="{escape(aria, quote=True)}"{disabled}>'
                f'{_state_options(selected, compact=True)}</select></td>'
            )
        pct_text = f'{student_pct}%' if student_pct is not None else '—'
        risk_class = ' incomplete' if student_missing else ''
        matrix_rows.append(
            '<tr>'
            f'<td class="sticky-no">{student.list_no or ""}</td>'
            f'<td class="sticky-name"><b>{escape(student.full_name)}</b></td>'
            + ''.join(cells)
            + f'<td class="summary-cell"><b>{pct_text}</b></td>'
            + f'<td class="summary-cell{risk_class}"><b>{student_missing}</b></td>'
            + '</tr>'
        )

    day_summaries = []
    for day in days:
        day_counts = {state: 0 for state in STATE_META}
        for student in students:
            item = by_key.get((student.id, day))
            if item and item.state in day_counts:
                day_counts[item.state] += 1
        day_missing = max(len(students) - sum(day_counts.values()), 0)
        day_summaries.append(
            '<td class="day-summary" title="Resumen del día">'
            f'<span class="p">P {day_counts["PRESENTE"]}</span>'
            f'<span class="a">A {day_counts["AUSENTE"]}</span>'
            f'<span class="r">R {day_counts["RETARDO"]}</span>'
            f'<span class="j">J {day_counts["JUSTIFICADA"]}</span>'
            f'<span class="m">— {day_missing}</span>'
            '</td>'
        )

    empty_row = ''
    if not students:
        empty_row = f'<tr><td colspan="{len(days) + 4}" class="empty-state">No hay alumnos activos en el grupo seleccionado.</td></tr>'
    elif not days:
        empty_row = '<tr><td colspan="4" class="empty-state">El rango no contiene días escolares.</td></tr>'

    range_note = ''.join(f'<div class="attendance-notice">{escape(message)}</div>' for message in range_messages)
    edit_note = '' if can_edit else '<div class="attendance-notice readonly">Vista de consulta: tu rol no permite modificar registros.</div>'
    disabled = '' if can_edit else ' disabled'
    save_controls = ''
    if can_edit and students and days:
        save_controls = '''
        <div class="matrix-actions">
          <button type="button" class="secondary-action" id="fill-present">Marcar vacíos como presente</button>
          <button type="submit">Guardar cambios de la tabla</button>
        </div>'''

    detail_day = _parse_day(request.args.get('detail_day'), end)
    if detail_day > date.today():
        detail_day = date.today()
    detail_records = {
        item.student_id: item
        for item in _query_records(detail_day, detail_day, student_ids)
    }
    detail_rows = []
    for student in students:
        item = detail_records.get(student.id)
        selected = item.state if item and item.state in STATE_META else ''
        detail_rows.append(
            '<tr>'
            f'<td>{student.list_no or ""}</td><td><b>{escape(student.full_name)}</b></td>'
            f'<td><select name="ds_{student.id}"{disabled}>{_state_options(selected)}</select></td>'
            f'<td><input name="dn_{student.id}" maxlength="250" value="{escape(item.notes if item else "", quote=True)}" '
            f'placeholder="Observación opcional"{disabled}></td>'
            '</tr>'
        )
    detail_submit = '<button type="submit">Guardar captura del día</button>' if can_edit and students else ''

    cards = ''.join([
        _summary_card('Días mostrados', len(days), f'{start:%d/%m/%Y} al {end:%d/%m/%Y}'),
        _summary_card('Registros capturados', captured, f'de {expected} posibles'),
        _summary_card('Registros pendientes', missing, 'celdas sin capturar', 'warning' if missing else 'success'),
        _summary_card('Asistencia registrada', f'{attendance_pct}%', 'P + R + J sobre capturados'),
    ])

    body = f'''
    <style id="attendance-matrix-v1">
    .attendance-heading{{display:flex;justify-content:space-between;align-items:flex-end;gap:18px;margin-bottom:18px}}
    .attendance-heading h1{{margin:0 0 6px}}.attendance-heading p{{margin:0;color:#746a6d}}
    .range-form{{display:grid;grid-template-columns:minmax(155px,1fr) minmax(155px,1fr) auto;gap:12px;align-items:end}}
    .range-form button{{min-width:150px}}.attendance-notice{{padding:10px 13px;border-radius:12px;background:#fff7df;border:1px solid #efd697;color:#76530b;margin:0 0 12px;font-size:13px;font-weight:700}}
    .attendance-notice.readonly{{background:#f3f5f8;border-color:#dbe0e7;color:#5e6672}}
    .attendance-kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 18px}}
    .attendance-kpi{{background:#fff;border:1px solid #eee4e4;border-radius:18px;padding:16px;box-shadow:0 7px 22px rgba(75,18,32,.05)}}
    .attendance-kpi span,.attendance-kpi small{{display:block;color:#786f71}}.attendance-kpi span{{font-size:12px;font-weight:850;text-transform:uppercase;letter-spacing:.35px}}
    .attendance-kpi b{{display:block;color:#5b1020;font-size:27px;margin:5px 0 2px}}.attendance-kpi.warning b{{color:#ad5b00}}.attendance-kpi.success b{{color:#14724b}}
    .attendance-card{{padding:0!important;overflow:hidden}}.attendance-card-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;padding:18px 20px;border-bottom:1px solid #eee7e5}}
    .attendance-card-head h2{{margin:0 0 5px}}.attendance-card-head p{{margin:0}}.attendance-legend{{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}}
    .attendance-legend span{{padding:5px 8px;border-radius:999px;background:#f6f2f2;color:#60575a;font-size:11px;font-weight:850}}
    .attendance-table-wrap{{overflow:auto;max-height:64vh}}.attendance-matrix{{min-width:max-content!important;margin:0}}
    .attendance-matrix th,.attendance-matrix td{{padding:8px;border-right:1px solid #f1eceb;text-align:center;background:#fff}}
    .attendance-matrix thead th{{position:sticky;top:0;z-index:4;background:#faf7f6;color:#5b1020}}
    .attendance-matrix .sticky-no{{position:sticky;left:0;z-index:3;min-width:54px;width:54px;background:#fff}}
    .attendance-matrix .sticky-name{{position:sticky;left:54px;z-index:3;text-align:left;min-width:230px;max-width:230px;background:#fff;box-shadow:7px 0 10px -10px #4e2730}}
    .attendance-matrix thead .sticky-no,.attendance-matrix thead .sticky-name{{z-index:6;background:#faf7f6}}
    .date-col{{min-width:64px}}.date-col span,.date-col b{{display:block}}.date-col span{{font-size:10px;color:#8e7d80;text-transform:uppercase}}.date-col b{{font-size:12px;margin-top:2px}}
    .state-cell{{min-width:64px}}.attendance-state{{width:48px!important;min-width:48px;padding:8px 5px!important;text-align:center;font-weight:900;border-radius:10px!important}}
    .attendance-state[data-state=""]{{background:#fff8df!important;border-color:#e9cd75!important;color:#8a6500!important}}
    .attendance-state[data-state="PRESENTE"]{{background:#e9f8ef!important;border-color:#9fd9b8!important;color:#146b40!important}}
    .attendance-state[data-state="AUSENTE"]{{background:#ffeded!important;border-color:#e9aaaa!important;color:#a32626!important}}
    .attendance-state[data-state="RETARDO"]{{background:#fff3dc!important;border-color:#ebc67c!important;color:#975d00!important}}
    .attendance-state[data-state="JUSTIFICADA"]{{background:#edf3ff!important;border-color:#adc3eb!important;color:#315a9a!important}}
    .summary-cell{{min-width:72px;background:#fcfaf9!important}}.summary-cell.incomplete b{{color:#ad5b00}}
    .day-summary{{font-size:10px;line-height:1.45;background:#faf7f6!important}}.day-summary span{{display:block;font-weight:800}}.day-summary .p{{color:#14724b}}.day-summary .a{{color:#a32626}}.day-summary .r{{color:#975d00}}.day-summary .j{{color:#315a9a}}.day-summary .m{{color:#746a6d}}
    .matrix-actions{{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;padding:16px 20px;border-top:1px solid #eee7e5}}.matrix-actions button{{width:auto;min-width:220px}}
    .secondary-action{{background:#fff!important;color:#5b1020!important;border:1px solid #ccb7bc!important}}
    .empty-state{{padding:28px!important;text-align:center!important;color:#746a6d}}.detail-card summary{{cursor:pointer;font-size:18px;font-weight:850;color:#5b1020}}
    .detail-card summary small{{display:block;font-size:12px;font-weight:500;color:#746a6d;margin:5px 0 0}}.detail-toolbar{{display:grid;grid-template-columns:minmax(180px,260px) auto;gap:10px;align-items:end;margin:18px 0}}
    .detail-toolbar a{{display:inline-flex;min-height:42px;align-items:center;justify-content:center;padding:9px 14px;border:1px solid #ccb7bc;border-radius:10px;text-decoration:none;color:#5b1020;font-weight:800}}
    .report-actions{{display:flex;gap:10px;align-items:end;flex-wrap:wrap}}.report-actions>a{{display:inline-flex;min-height:42px;align-items:center;text-decoration:none;background:#5b1020;color:#fff;padding:10px 15px;border-radius:11px;font-weight:800}}
    .report-actions form{{display:flex;gap:8px;align-items:end;flex-wrap:wrap;margin:0}}.report-actions form label{{min-width:110px}}.report-actions form input,.report-actions form select{{min-height:42px}}.report-actions form button{{width:auto;min-height:42px;background:#217346}}
    @media(max-width:900px){{.attendance-kpis{{grid-template-columns:repeat(2,minmax(0,1fr))}}.attendance-card-head,.attendance-heading{{align-items:flex-start;flex-direction:column}}.attendance-legend{{justify-content:flex-start}}}}
    @media(max-width:650px){{.range-form{{grid-template-columns:1fr 1fr}}.range-form button{{grid-column:1/-1}}.attendance-kpis{{grid-template-columns:1fr 1fr;gap:8px}}.attendance-kpi{{padding:12px;border-radius:14px}}.attendance-kpi b{{font-size:22px}}.attendance-matrix .sticky-name{{min-width:175px;max-width:175px}}.matrix-actions button{{width:100%;min-width:0}}.detail-toolbar{{grid-template-columns:1fr}}}}
    </style>
    <section class="attendance-heading">
      <div><h1>Asistencia</h1><p>Resumen por alumno y fecha del grupo activo.</p></div>
    </section>
    {range_note}{edit_note}
    <div class="card">
      <form method="get" class="range-form">
        <label>Desde<input type="date" name="from" value="{start.isoformat()}" max="{date.today().isoformat()}" required></label>
        <label>Hasta<input type="date" name="to" value="{end.isoformat()}" max="{date.today().isoformat()}" required></label>
        <button type="submit">Mostrar periodo</button>
      </form>
    </div>
    <section class="attendance-kpis">{cards}</section>
    <form method="post" class="card attendance-card">
      <input type="hidden" name="attendance_action" value="save_matrix">
      <input type="hidden" name="from" value="{start.isoformat()}">
      <input type="hidden" name="to" value="{end.isoformat()}">
      <input type="hidden" name="matrix_dates" value="{','.join(day.isoformat() for day in days)}">
      <div class="attendance-card-head">
        <div><h2>Concentrado del periodo</h2><p class="muted">Las celdas amarillas todavía no tienen registro.</p></div>
        <div class="attendance-legend" aria-label="Simbología"><span>P · Presente</span><span>A · Ausente</span><span>R · Retardo</span><span>J · Justificada</span><span>— · Sin registro</span></div>
      </div>
      <div class="attendance-table-wrap">
        <table class="attendance-matrix">
          <thead><tr><th class="sticky-no">No.</th><th class="sticky-name">Alumno</th>{head_days}<th>% asist.</th><th>Pend.</th></tr></thead>
          <tbody>{''.join(matrix_rows)}{empty_row}</tbody>
          <tfoot><tr><th class="sticky-no"></th><th class="sticky-name">Totales por fecha</th>{''.join(day_summaries)}<th colspan="2"></th></tr></tfoot>
        </table>
      </div>
      {save_controls}
    </form>
    <details class="card detail-card" {'open' if request.args.get('detail_day') else ''}>
      <summary>Captura detallada por fecha<small>Edita estados y observaciones individuales sin perder el concentrado.</small></summary>
      <form method="get" class="detail-toolbar">
        <input type="hidden" name="from" value="{start.isoformat()}"><input type="hidden" name="to" value="{end.isoformat()}">
        <label>Fecha para detalle<input type="date" name="detail_day" value="{detail_day.isoformat()}" max="{date.today().isoformat()}" required></label>
        <button type="submit">Cargar detalle</button>
      </form>
      <form method="post">
        <input type="hidden" name="attendance_action" value="save_detail"><input type="hidden" name="from" value="{start.isoformat()}"><input type="hidden" name="to" value="{end.isoformat()}"><input type="hidden" name="detail_day" value="{detail_day.isoformat()}">
        <div class="scroll"><table><thead><tr><th>No.</th><th>Alumno</th><th>Estado</th><th>Observación</th></tr></thead><tbody>{''.join(detail_rows)}</tbody></table></div>
        <div style="margin-top:14px">{detail_submit}</div>
      </form>
    </details>
    <div class="card attendance-list-card">
      <h2>Reportes de asistencia en Excel</h2>
      <p class="muted">Genera la lista institucional o el concentrado mensual del grupo activo.</p>
      <div class="report-actions">
        <a href="/attendance/list.xlsx">Generar lista para imprimir</a>
        <form method="get" action="/attendance/month.xlsx">
          <label>Mes<select name="month">{''.join(f'<option value="{month}" {"selected" if month == date.today().month else ""}>{month:02d}</option>' for month in range(1, 13))}</select></label>
          <label>Año<input type="number" name="year" value="{date.today().year}" min="2020" max="2100"></label>
          <button type="submit">Generar concentrado mensual</button>
        </form>
      </div>
    </div>
    <script>
    (() => {{
      const selects = document.querySelectorAll('.attendance-state');
      const paint = select => {{ select.dataset.state = select.value; select.closest('td').dataset.missing = String(!select.value); }};
      selects.forEach(select => select.addEventListener('change', () => paint(select)));
      const fill = document.getElementById('fill-present');
      if (fill) fill.addEventListener('click', () => {{
        selects.forEach(select => {{ if (!select.value && !select.disabled) {{ select.value = 'PRESENTE'; paint(select); }} }});
      }});
    }})();
    </script>
    '''
    return core.page('Asistencia', body)


def install(app):
    app.view_functions['attendance'] = _attendance_view
