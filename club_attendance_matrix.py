import calendar
import io
from datetime import date, datetime, timedelta
from html import escape
from urllib.parse import urlencode

import xlsxwriter
from flask import flash, redirect, request, send_file, session

import attendance_list_export as group_attendance_export
import clubs_sports as clubs
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


def _normalize_state(value):
    value = (value or '').strip().upper()
    return 'AUSENTE' if value == 'FALTA' else value


def _range_from_request():
    today = date.today()
    legacy_day = request.values.get('day')
    start = _parse_day(request.values.get('from') or legacy_day, today.replace(day=1))
    end = _parse_day(request.values.get('to') or legacy_day, today)
    notices = []
    if end > today:
        end = today
        notices.append('La fecha final se ajustó a hoy; no se capturan asistencias futuras.')
    if start > end:
        start = end
        notices.append('La fecha inicial se ajustó para conservar un rango válido.')
    if (end - start).days >= MAX_RANGE_DAYS:
        start = end - timedelta(days=MAX_RANGE_DAYS - 1)
        notices.append(f'La vista se limita a {MAX_RANGE_DAYS} días para mantener la tabla legible.')
    return start, end, notices


def _scheduled_weekday(club):
    return 1 if (club.kind or 'CLUB').strip().upper() == 'DEPORTE' else 4


def _schedule_label(club):
    return 'martes' if _scheduled_weekday(club) == 1 else 'viernes'


def _dates_in_range(start, end, scheduled_weekday):
    result = []
    current = start
    while current <= end:
        if current.weekday() == scheduled_weekday:
            result.append(current)
        current += timedelta(days=1)
    return result


def _nearest_scheduled_day(day, scheduled_weekday):
    return day - timedelta(days=(day.weekday() - scheduled_weekday) % 7)


def _state_options(selected, compact=False):
    selected = _normalize_state(selected)
    empty_label = '—' if compact else '— Sin registro —'
    parts = [f'<option value="">{empty_label}</option>']
    for value, (symbol, label) in STATE_META.items():
        text = symbol if compact else label
        mark = ' selected' if selected == value else ''
        parts.append(f'<option value="{value}"{mark}>{text}</option>')
    return ''.join(parts)


def _can_edit(club):
    profile = multi_user._profile(session.get('uid'))
    if not profile or not profile.active:
        return False
    if profile.role == 'ADMIN':
        return True
    if profile.role != 'DOCENTE':
        return False
    try:
        import clubs_permissions
        return clubs_permissions._can_edit_club(club.id)
    except Exception:
        return club.teacher_user_id == session.get('uid')


def _member_rows(club_id):
    return clubs._club_members_data(club_id)


def _query_records(club_id, start, end, student_ids):
    if not student_ids:
        return []
    return clubs.ClubAttendance.query.filter(
        clubs.ClubAttendance.club_id == club_id,
        clubs.ClubAttendance.day.between(start, end),
        clubs.ClubAttendance.student_id.in_(student_ids),
    ).all()


def _redirect_to_range(club_id, start, end, detail_day=None):
    params = {'from': start.isoformat(), 'to': end.isoformat()}
    if detail_day:
        params['detail_day'] = detail_day.isoformat()
    return redirect(f'/clubs/{club_id}/attendance?' + urlencode(params))


def _save_matrix(club, members, start, end):
    allowed_dates = {
        _parse_day(raw, None)
        for raw in request.form.get('matrix_dates', '').split(',')
        if raw.strip()
    }
    allowed_dates = {
        day for day in allowed_dates
        if (
            day is not None
            and start <= day <= end
            and day <= date.today()
            and day.weekday() == _scheduled_weekday(club)
        )
    }
    if not allowed_dates:
        flash('No se recibieron fechas válidas para guardar.')
        return _redirect_to_range(club.id, start, end)

    student_ids = [student.id for _, student in members]
    existing = {
        (row.student_id, row.day): row
        for row in _query_records(club.id, min(allowed_dates), max(allowed_dates), student_ids)
    }
    changed = 0
    created = 0
    for _, student in members:
        for day in allowed_dates:
            state = _normalize_state(request.form.get(f'ca_{student.id}_{day:%Y%m%d}'))
            if state not in STATE_META:
                continue
            row = existing.get((student.id, day))
            if row is None:
                row = clubs.ClubAttendance(club_id=club.id, student_id=student.id, day=day)
                clubs.core.db.session.add(row)
                existing[(student.id, day)] = row
                created += 1
            if _normalize_state(row.state) != state or row.id is None or row.state == 'FALTA':
                row.state = state
                changed += 1
    try:
        clubs.core.db.session.commit()
    except Exception:
        clubs.core.db.session.rollback()
        flash('No se pudo guardar el pase de lista. Inténtalo nuevamente.')
        return _redirect_to_range(club.id, start, end)
    if changed:
        flash(f'Asistencia actualizada: {changed} registro(s), {created} nuevo(s).')
    else:
        flash('No hubo cambios de asistencia por guardar.')
    return _redirect_to_range(club.id, start, end)


def _save_detail(club, members, start, end):
    detail_day = _parse_day(request.form.get('detail_day'), date.today())
    if detail_day > date.today():
        flash('No se puede registrar asistencia en una fecha futura.')
        return _redirect_to_range(club.id, start, end)
    if detail_day.weekday() != _scheduled_weekday(club):
        flash(
            f'La asistencia de este {(club.kind or "club").lower()} '
            f'solo puede registrarse los {_schedule_label(club)}.'
        )
        return _redirect_to_range(club.id, start, end)

    student_ids = [student.id for _, student in members]
    existing = {
        row.student_id: row
        for row in _query_records(club.id, detail_day, detail_day, student_ids)
    }
    saved = 0
    for _, student in members:
        state = _normalize_state(request.form.get(f'cds_{student.id}'))
        if state not in STATE_META:
            continue
        row = existing.get(student.id)
        if row is None:
            row = clubs.ClubAttendance(club_id=club.id, student_id=student.id, day=detail_day)
            clubs.core.db.session.add(row)
        row.state = state
        row.notes = request.form.get(f'cdn_{student.id}', '').strip()[:250]
        saved += 1
    try:
        clubs.core.db.session.commit()
    except Exception:
        clubs.core.db.session.rollback()
        flash('No se pudo guardar la captura detallada. Inténtalo nuevamente.')
        return _redirect_to_range(club.id, start, end, detail_day)
    flash(f'Pase de lista guardado para {saved} integrante(s).')
    return _redirect_to_range(club.id, start, end, detail_day)


def _group_label(member):
    grade, group_name = clubs._group_parts(member.group_code)
    return f'{grade} {group_name}'.strip() or member.group_code


def _summary_card(label, value, note, css_class=''):
    return (
        f'<div class="club-att-kpi {css_class}">'
        f'<span>{escape(label)}</span><b>{escape(str(value))}</b><small>{escape(note)}</small>'
        '</div>'
    )




def _responsible_name(club):
    user_id = club.teacher_user_id
    try:
        import clubs_permissions
        query = clubs_permissions.ClubDualAuthorization.query.filter_by(active=True)
        if (club.kind or 'CLUB').strip().upper() == 'DEPORTE':
            authorization = query.filter_by(sport_id=club.id).first()
        else:
            authorization = query.filter_by(club_id=club.id).first()
        if authorization:
            user_id = authorization.teacher_user_id
    except Exception:
        pass
    profile = multi_user._profile(user_id)
    return ((profile.full_name if profile else '') or 'DOCENTE RESPONSABLE').upper()


def _club_header(ws, fmts, last_col, club, title, subtitle):
    cfg = clubs.core.cfg()
    group_attendance_export._insert_logo(ws, 'A1', 'left', 0.48, 0.48)
    right_logo_col = max(4, last_col - 3)
    group_attendance_export._insert_logo(
        ws,
        xlsxwriter.utility.xl_rowcol_to_cell(0, right_logo_col),
        'right',
        0.20,
        0.20,
    )
    center_end = max(8, last_col - 4)
    ws.merge_range(0, 6, 0, center_end, 'SUBSECRETARÍA DE EDUCACIÓN OBLIGATORIA', fmts['small'])
    ws.merge_range(1, 6, 1, center_end, 'DIRECCIÓN GENERAL DE EDUCACIÓN BÁSICA PRIMER NIVEL', fmts['small'])
    ws.merge_range(2, 6, 2, center_end, 'DIRECCIÓN DE EDUCACIÓN TELESECUNDARIA', fmts['small'])
    ws.merge_range(3, 6, 3, center_end, 'TELESECUNDARIA “BENITO JUÁREZ”', fmts['small'])
    split = max(8, last_col // 3)
    ws.merge_range(6, 0, 6, split, 'TURNO: MATUTINO', fmts['meta'])
    ws.merge_range(
        6,
        split + 1,
        6,
        last_col,
        f'CICLO ESCOLAR: {group_attendance_export._cycle_text(cfg.cycle)}',
        fmts['meta'],
    )
    ws.merge_range(7, 0, 7, last_col, 'LOCALIDAD: BERISTAIN, AHUAZOTEPEC, PUEBLA', fmts['meta'])
    ws.merge_range(9, 1, 9, last_col, title, fmts['title'])
    activity = f'{(club.kind or "CLUB").strip().upper()}: “{(club.name or "").strip().upper()}”'
    if subtitle:
        activity += f' · {subtitle}'
    ws.merge_range(10, 0, 10, last_col, activity, fmts['group'])


def _club_signature_block(ws, fmts, start_row, last_col, club):
    left_start, left_end = 2, min(12, max(8, last_col // 3))
    right_start, right_end = max(left_end + 2, last_col // 2), last_col
    ws.merge_range(
        start_row,
        1,
        start_row,
        last_col - 1,
        'BERISTAIN, AHUAZOTEPEC, PUE., A _______ DE _________________________ DE __________',
        fmts['date'],
    )
    ws.merge_range(start_row + 2, left_start, start_row + 2, left_end, 'DOCENTE RESPONSABLE', fmts['sig'])
    ws.merge_range(start_row + 2, right_start, start_row + 2, right_end, 'Vo. Bo.', fmts['sig'])
    ws.merge_range(start_row + 3, right_start, start_row + 3, right_end, 'DIRECTORA DE LA ESCUELA', fmts['sig'])
    ws.merge_range(start_row + 5, left_start, start_row + 5, left_end, '___________________________________________', fmts['sig'])
    ws.merge_range(start_row + 5, right_start, start_row + 5, right_end, '_______________________________________', fmts['sig'])
    ws.merge_range(start_row + 6, left_start, start_row + 6, left_end, _responsible_name(club), fmts['sig'])
    ws.merge_range(
        start_row + 6,
        right_start,
        start_row + 6,
        right_end,
        'MTRA. NELLY AZUCENA HERNÁNDEZ PICAZO',
        fmts['sig'],
    )
    return start_row + 7


def _build_club_attendance_list(club):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet('LISTA DE ASISTENCIA')
    formats = group_attendance_export._base_formats(workbook)
    last_col = 30

    sheet.set_portrait()
    sheet.set_paper(1)
    sheet.set_margins(0.31, 0.23, 0.33, 0.02)
    sheet.fit_to_pages(1, 1)
    sheet.hide_gridlines(2)
    sheet.set_column('A:A', 0.7)
    sheet.set_column('B:B', 4.2)
    sheet.set_column('C:C', 29)
    sheet.set_column('D:D', 6.5)
    sheet.set_column('E:AE', 1.9)
    for row, height in enumerate([20, 18, 18, 18, 12]):
        sheet.set_row(row, height)

    _club_header(
        sheet,
        formats,
        last_col,
        club,
        'REGISTRO DE ASISTENCIA',
        f'SESIONES: {_schedule_label(club).upper()}',
    )
    sheet.merge_range('B13:B14', 'N/P', formats['head'])
    sheet.merge_range('C13:C14', '          NOMBRE DEL INTEGRANTE', formats['head'])
    sheet.merge_range('D13:D14', 'GRUPO', formats['head'])
    for col in range(4, last_col + 1):
        sheet.merge_range(12, col, 13, col, '', formats['head'])

    members = _member_rows(club.id)
    first_row = 14
    data_rows = max(28, len(members))
    for index in range(data_rows):
        row = first_row + index
        if index < len(members):
            member, student = members[index]
            number = index + 1
            name = (student.full_name or '').upper()
            group_label = _group_label(member)
        else:
            number, name, group_label = '', '', ''
        sheet.write(row, 1, number, formats['num'])
        sheet.write(row, 2, name, formats['name'])
        sheet.write(row, 3, group_label, formats['num'])
        for col in range(4, last_col + 1):
            sheet.write_blank(row, col, None, formats['day'])
        sheet.set_row(row, 18)

    signature_end = _club_signature_block(
        sheet,
        formats,
        first_row + data_rows + 1,
        last_col,
        club,
    )
    sheet.print_area(0, 0, signature_end, last_col)
    workbook.close()
    output.seek(0)
    return output


def _build_club_monthly_attendance(club, year, month):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet('CONCENTRADO MENSUAL')
    formats = group_attendance_export._base_formats(workbook)
    days_in_month = calendar.monthrange(year, month)[1]
    first_day_col = 4
    total_start = first_day_col + days_in_month
    last_col = total_start + 4

    sheet.set_landscape()
    sheet.set_paper(1)
    sheet.set_margins(0.20, 0.20, 0.28, 0.25)
    sheet.fit_to_pages(1, 1)
    sheet.hide_gridlines(2)
    sheet.set_column(0, 0, 0.7)
    sheet.set_column(1, 1, 4.2)
    sheet.set_column(2, 2, 27)
    sheet.set_column(3, 3, 6.5)
    sheet.set_column(first_day_col, first_day_col + days_in_month - 1, 2.15)
    sheet.set_column(total_start, last_col, 5.5)
    for row, height in enumerate([20, 18, 18, 18, 12]):
        sheet.set_row(row, height)

    month_name = group_attendance_export.MONTHS_ES.get(month, str(month))
    _club_header(
        sheet,
        formats,
        last_col,
        club,
        'CONCENTRADO MENSUAL DE ASISTENCIA',
        f'{month_name} {year} · SESIONES: {_schedule_label(club).upper()}',
    )

    header_row = 12
    sheet.write(header_row, 1, 'N/P', formats['head'])
    sheet.write(header_row, 2, 'NOMBRE DEL INTEGRANTE', formats['head'])
    sheet.write(header_row, 3, 'GRUPO', formats['head'])
    for day_number in range(1, days_in_month + 1):
        current_day = date(year, month, day_number)
        label = f'{day_number}\n{calendar.day_abbr[current_day.weekday()][0].upper()}'
        sheet.write(header_row, first_day_col + day_number - 1, label, formats['head'])
    for offset, label in enumerate(['P', 'A', 'R', 'J', '% ASIST.']):
        sheet.write(header_row, total_start + offset, label, formats['head'])
    sheet.set_row(header_row, 30)

    members = _member_rows(club.id)
    student_ids = [student.id for _, student in members]
    start = date(year, month, 1)
    end = date(year, month, days_in_month)
    attendance = _query_records(club.id, start, end, student_ids)
    by_key = {(row.student_id, row.day.day): row for row in attendance}
    scheduled_weekday = _scheduled_weekday(club)
    recorded_days = sorted({
        row.day.day for row in attendance
        if row.day.weekday() == scheduled_weekday
    })

    first_row = header_row + 1
    data_rows = max(28, len(members))
    for index in range(data_rows):
        row_number = first_row + index
        if index >= len(members):
            sheet.write_blank(row_number, 1, None, formats['num'])
            sheet.write_blank(row_number, 2, None, formats['name'])
            sheet.write_blank(row_number, 3, None, formats['num'])
            for col in range(first_day_col, last_col + 1):
                sheet.write_blank(row_number, col, None, formats['day'])
            continue

        member, student = members[index]
        sheet.write(row_number, 1, index + 1, formats['num'])
        sheet.write(row_number, 2, (student.full_name or '').upper(), formats['name'])
        sheet.write(row_number, 3, _group_label(member), formats['num'])
        counts = {'P': 0, 'A': 0, 'R': 0, 'J': 0}
        for day_number in range(1, days_in_month + 1):
            current_day = date(year, month, day_number)
            is_session_day = current_day.weekday() == scheduled_weekday
            attendance_row = by_key.get((student.id, day_number)) if is_session_day else None
            state = _normalize_state(attendance_row.state) if attendance_row else ''
            symbol = STATE_META.get(state, ('', ''))[0]
            if symbol:
                counts[symbol] += 1
            cell_format = formats['day'] if is_session_day else formats['weekend']
            sheet.write(
                row_number,
                first_day_col + day_number - 1,
                symbol,
                cell_format,
            )
        for offset, key in enumerate(['P', 'A', 'R', 'J']):
            sheet.write(row_number, total_start + offset, counts[key], formats['num'])
        considered = sum(counts.values())
        attendance_value = (
            (counts['P'] + counts['R'] + counts['J']) / considered
            if considered else 0
        )
        sheet.write_number(row_number, total_start + 4, attendance_value, formats['pct'])
        sheet.set_row(row_number, 18)

    summary_row = first_row + data_rows + 1
    sheet.merge_range(summary_row, 1, summary_row, 6, 'RESUMEN DEL MES', formats['head'])
    sheet.merge_range(
        summary_row + 1,
        1,
        summary_row + 1,
        7,
        f'Sesiones de {_schedule_label(club)} con asistencia registrada: {len(recorded_days)}',
        formats['meta'],
    )
    sheet.merge_range(
        summary_row + 2,
        1,
        summary_row + 2,
        min(last_col, 17),
        'Clave: P = Presente · A = Ausente · R = Retardo · J = Justificada. '
        'El porcentaje considera únicamente los días capturados para cada integrante.',
        formats['meta'],
    )
    signature_end = _club_signature_block(
        sheet,
        formats,
        summary_row + 4,
        last_col,
        club,
    )
    sheet.freeze_panes(first_row, first_day_col)
    sheet.repeat_rows(0, header_row)
    sheet.print_area(0, 0, signature_end, last_col)
    workbook.close()
    output.seek(0)
    return output


def _club_attendance_view(cid):
    club = clubs.core.db.session.get(clubs.ClubSport, cid)
    if not club or not clubs._allowed(club):
        return redirect('/clubs')

    start, end, notices = _range_from_request()
    members = _member_rows(cid)
    can_edit = _can_edit(club)

    if request.method == 'POST':
        if not can_edit:
            flash('Tu cuenta puede consultar este pase de lista, pero no modificarlo.')
            return _redirect_to_range(cid, start, end)
        if request.form.get('club_attendance_action') == 'save_detail':
            return _save_detail(club, members, start, end)
        return _save_matrix(club, members, start, end)

    student_ids = [student.id for _, student in members]
    records = _query_records(cid, start, end, student_ids)
    scheduled_weekday = _scheduled_weekday(club)
    schedule_label = _schedule_label(club)
    days = _dates_in_range(start, end, scheduled_weekday)
    by_key = {(row.student_id, row.day): row for row in records}

    totals = {state: 0 for state in STATE_META}
    for row in records:
        state = _normalize_state(row.state)
        if state in totals and row.day in days:
            totals[state] += 1
    expected = len(members) * len(days)
    captured = sum(totals.values())
    missing = max(expected - captured, 0)
    attendance_count = totals['PRESENTE'] + totals['RETARDO'] + totals['JUSTIFICADA']
    attendance_pct = round(attendance_count * 100 / captured, 1) if captured else 0

    date_headers = ''.join(
        f'<th class="club-date-col" title="{WEEKDAYS[day.weekday()]} {day:%d/%m/%Y}">'
        f'<span>{WEEKDAYS[day.weekday()]}</span><b>{day:%d/%m}</b></th>'
        for day in days
    )
    table_rows = []
    for number, (member, student) in enumerate(members, 1):
        member_records = [by_key.get((student.id, day)) for day in days]
        member_captured = sum(
            1 for row in member_records if row and _normalize_state(row.state) in STATE_META
        )
        member_attends = sum(
            1 for row in member_records
            if row and _normalize_state(row.state) in ('PRESENTE', 'RETARDO', 'JUSTIFICADA')
        )
        member_pct = round(member_attends * 100 / member_captured) if member_captured else None
        member_missing = len(days) - member_captured
        cells = []
        for day, row in zip(days, member_records):
            selected = _normalize_state(row.state) if row else ''
            if selected not in STATE_META:
                selected = ''
            disabled = ' disabled' if not can_edit else ''
            aria = f'{student.full_name}, {day:%d/%m/%Y}'
            cells.append(
                f'<td class="club-state-cell" data-missing="{str(not selected).lower()}">'
                f'<select class="club-attendance-state" name="ca_{student.id}_{day:%Y%m%d}" '
                f'data-state="{selected}" aria-label="{escape(aria, quote=True)}" '
                f'title="{escape(aria, quote=True)}"{disabled}>'
                f'{_state_options(selected, compact=True)}</select></td>'
            )
        pct_text = f'{member_pct}%' if member_pct is not None else '—'
        missing_class = ' incomplete' if member_missing else ''
        table_rows.append(
            '<tr>'
            f'<td class="club-sticky-no">{number}</td>'
            f'<td class="club-sticky-name"><b>{escape(student.full_name)}</b></td>'
            f'<td class="club-sticky-group">{escape(_group_label(member))}</td>'
            + ''.join(cells)
            + f'<td class="club-summary-cell"><b>{pct_text}</b></td>'
            + f'<td class="club-summary-cell{missing_class}"><b>{member_missing}</b></td>'
            + '</tr>'
        )

    daily_totals = []
    for day in days:
        counts = {state: 0 for state in STATE_META}
        for _, student in members:
            row = by_key.get((student.id, day))
            state = _normalize_state(row.state) if row else ''
            if state in counts:
                counts[state] += 1
        day_missing = max(len(members) - sum(counts.values()), 0)
        daily_totals.append(
            '<td class="club-day-summary">'
            f'<span class="p">P {counts["PRESENTE"]}</span>'
            f'<span class="a">A {counts["AUSENTE"]}</span>'
            f'<span class="r">R {counts["RETARDO"]}</span>'
            f'<span class="j">J {counts["JUSTIFICADA"]}</span>'
            f'<span class="m">— {day_missing}</span>'
            '</td>'
        )

    if not members:
        empty_row = f'<tr><td colspan="{len(days) + 5}" class="club-empty">Este club o deporte todavía no tiene integrantes activos.</td></tr>'
    elif not days:
        empty_row = '<tr><td colspan="5" class="club-empty">El rango no contiene días escolares.</td></tr>'
    else:
        empty_row = ''

    notice_html = (
        f'<div class="club-att-notice schedule">'
        f'Calendario de este {(club.kind or "club").lower()}: '
        f'<b>asistencia únicamente los {schedule_label}</b>.'
        f'</div>'
        + ''.join(
            f'<div class="club-att-notice">{escape(message)}</div>'
            for message in notices
        )
    )
    if not can_edit:
        notice_html += '<div class="club-att-notice readonly">Modo consulta: solo el administrador o el docente autorizado puede registrar asistencia.</div>'

    save_actions = ''
    if can_edit and members and days:
        save_actions = '''
        <div class="club-matrix-actions">
          <button type="button" class="btn alt" id="club-fill-present">Marcar vacíos como presente</button>
          <button type="submit">Guardar cambios de la tabla</button>
        </div>'''

    detail_day = _parse_day(request.args.get('detail_day'), end)
    if detail_day > date.today():
        detail_day = date.today()
    detail_day = _nearest_scheduled_day(detail_day, scheduled_weekday)
    detail_records = {
        row.student_id: row
        for row in _query_records(cid, detail_day, detail_day, student_ids)
    }
    detail_rows = []
    disabled = '' if can_edit else ' disabled'
    for number, (member, student) in enumerate(members, 1):
        row = detail_records.get(student.id)
        selected = _normalize_state(row.state) if row else ''
        if selected not in STATE_META:
            selected = ''
        detail_rows.append(
            '<tr>'
            f'<td>{number}</td><td><b>{escape(student.full_name)}</b></td>'
            f'<td>{escape(_group_label(member))}</td>'
            f'<td><select name="cds_{student.id}"{disabled}>{_state_options(selected)}</select></td>'
            f'<td><input name="cdn_{student.id}" maxlength="250" '
            f'value="{escape(row.notes if row else "", quote=True)}" '
            f'placeholder="Observación opcional"{disabled}></td>'
            '</tr>'
        )
    detail_submit = '<button type="submit">Guardar pase de lista del día</button>' if can_edit and members else ''

    cards = ''.join([
        _summary_card('Días mostrados', len(days), f'{start:%d/%m/%Y} al {end:%d/%m/%Y}'),
        _summary_card('Registros capturados', captured, f'de {expected} posibles'),
        _summary_card('Registros pendientes', missing, 'celdas sin capturar', 'warning' if missing else 'success'),
        _summary_card('Asistencia registrada', f'{attendance_pct}%', 'P + R + J sobre capturados'),
    ])

    kind_label = escape((club.kind or 'CLUB').title())
    club_name = escape(club.name)
    body = f'''
    <style id="club-attendance-matrix-v1">
    .club-att-heading{{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;margin-bottom:16px}}
    .club-att-heading h2{{margin:0 0 5px}}.club-att-heading p{{margin:0}}
    .club-att-toolbar{{display:flex;gap:8px;flex-wrap:wrap}}.club-range-form{{display:grid;grid-template-columns:minmax(155px,1fr) minmax(155px,1fr) auto;gap:12px;align-items:end}}
    .club-att-notice{{padding:10px 13px;border-radius:12px;background:#fff7df;border:1px solid #efd697;color:#76530b;margin:0 0 12px;font-size:13px;font-weight:700}}
    .club-att-notice.readonly{{background:#f3f5f8;border-color:#dbe0e7;color:#5e6672}}.club-att-notice.schedule{{background:#edf3ff;border-color:#adc3eb;color:#315a9a}}
    .club-att-kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 16px}}
    .club-att-kpi{{background:#fff;border:1px solid #e3e7ef;border-radius:16px;padding:15px;box-shadow:0 7px 22px rgba(23,35,59,.05)}}
    .club-att-kpi span,.club-att-kpi small{{display:block;color:#6c7483}}.club-att-kpi span{{font-size:11px;font-weight:850;text-transform:uppercase;letter-spacing:.35px}}
    .club-att-kpi b{{display:block;color:#74142b;font-size:26px;margin:5px 0 2px}}.club-att-kpi.warning b{{color:#ad5b00}}.club-att-kpi.success b{{color:#14724b}}
    .club-att-card{{padding:0!important;overflow:hidden}}.club-att-card-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:17px 19px;border-bottom:1px solid #e5e8ef}}
    .club-att-card-head h2{{margin:0 0 5px}}.club-att-legend{{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}}
    .club-att-legend span{{padding:5px 8px;border-radius:99px;background:#f3f0f1;color:#5c5054;font-size:11px;font-weight:850}}
    .club-att-table-wrap{{overflow:auto;max-height:64vh}}.club-att-matrix{{min-width:max-content}}
    .club-att-matrix th,.club-att-matrix td{{padding:8px;border-right:1px solid #edeff3;text-align:center;background:#fff}}
    .club-att-matrix thead th{{position:sticky;top:0;z-index:4;background:#f3f0f1;color:#74142b}}
    .club-sticky-no{{position:sticky;left:0;z-index:3;min-width:48px;width:48px;background:#fff!important}}
    .club-sticky-name{{position:sticky;left:48px;z-index:3;text-align:left!important;min-width:220px;max-width:220px;background:#fff!important}}
    .club-sticky-group{{position:sticky;left:268px;z-index:3;min-width:78px;background:#fff!important;box-shadow:7px 0 10px -10px #17233b}}
    thead .club-sticky-no,thead .club-sticky-name,thead .club-sticky-group{{z-index:6;background:#f3f0f1!important}}
    .club-date-col{{min-width:64px}}.club-date-col span,.club-date-col b{{display:block}}.club-date-col span{{font-size:10px;color:#82777a;text-transform:uppercase}}.club-date-col b{{font-size:12px;margin-top:2px}}
    .club-state-cell{{min-width:64px}}.club-attendance-state{{width:48px!important;min-width:48px;padding:8px 5px!important;text-align:center;font-weight:900;border-radius:10px!important}}
    .club-attendance-state[data-state=""]{{background:#fff8df!important;border-color:#e9cd75!important;color:#8a6500!important}}
    .club-attendance-state[data-state="PRESENTE"]{{background:#e9f8ef!important;border-color:#9fd9b8!important;color:#146b40!important}}
    .club-attendance-state[data-state="AUSENTE"]{{background:#ffeded!important;border-color:#e9aaaa!important;color:#a32626!important}}
    .club-attendance-state[data-state="RETARDO"]{{background:#fff3dc!important;border-color:#ebc67c!important;color:#975d00!important}}
    .club-attendance-state[data-state="JUSTIFICADA"]{{background:#edf3ff!important;border-color:#adc3eb!important;color:#315a9a!important}}
    .club-summary-cell{{min-width:72px;background:#fcfaf9!important}}.club-summary-cell.incomplete b{{color:#ad5b00}}
    .club-day-summary{{font-size:10px;line-height:1.45;background:#f8f6f6!important}}.club-day-summary span{{display:block;font-weight:800}}.club-day-summary .p{{color:#14724b}}.club-day-summary .a{{color:#a32626}}.club-day-summary .r{{color:#975d00}}.club-day-summary .j{{color:#315a9a}}.club-day-summary .m{{color:#6c7483}}
    .club-matrix-actions{{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;padding:15px 19px;border-top:1px solid #e5e8ef}}.club-matrix-actions button{{width:auto;min-width:220px}}
    .club-empty{{padding:28px!important;text-align:center!important;color:#6c7483}}.club-detail-card summary{{cursor:pointer;font-size:18px;font-weight:850;color:#74142b}}
    .club-detail-card summary small{{display:block;font-size:12px;font-weight:500;color:#6c7483;margin-top:5px}}.club-detail-toolbar{{display:grid;grid-template-columns:minmax(180px,260px) auto;gap:10px;align-items:end;margin:18px 0}}
    .club-export-actions{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.club-export-actions form{display:flex;gap:8px;align-items:end;flex-wrap:wrap;margin:0}.club-export-actions form label{min-width:120px}.club-export-actions form button{width:auto;min-height:42px}.club-excel-button{background:#217346!important}
    @media(max-width:900px){{.club-att-kpis{{grid-template-columns:repeat(2,minmax(0,1fr))}}.club-att-card-head,.club-att-heading{{align-items:flex-start;flex-direction:column}}.club-att-legend{{justify-content:flex-start}}}}
    @media(max-width:700px){{.club-range-form{{grid-template-columns:1fr 1fr}}.club-range-form button{{grid-column:1/-1}}.club-att-kpis{{gap:8px}}.club-att-kpi{{padding:12px}}.club-att-kpi b{{font-size:22px}}.club-sticky-name{{min-width:180px;max-width:180px}}.club-sticky-group{{left:228px}}.club-matrix-actions button{{width:100%;min-width:0}}.club-detail-toolbar{{grid-template-columns:1fr}}}}
    </style>
    <section class="club-att-heading">
      <div><span class="pill">{kind_label}</span><h2>{club_name}</h2><p class="muted">Pase de lista y concentrado de asistencia · sesiones los {schedule_label}.</p></div>
      <div class="club-att-toolbar no-print"><a class="btn alt" href="/clubs/{cid}">Volver a integrantes</a><a class="btn alt" href="/clubs/{cid}/attendance/list.xlsx">Formato Excel</a><a class="btn" href="/clubs/{cid}/evaluate">Evaluar</a></div>
    </section>
    {notice_html}
    <div class="card no-print">
      <form method="get" class="club-range-form">
        <label>Desde<input type="date" name="from" value="{start.isoformat()}" max="{date.today().isoformat()}" required></label>
        <label>Hasta<input type="date" name="to" value="{end.isoformat()}" max="{date.today().isoformat()}" required></label>
        <button type="submit">Mostrar periodo</button>
      </form>
    </div>
    <section class="club-att-kpis">{cards}</section>
    <form method="post" class="card club-att-card">
      <input type="hidden" name="club_attendance_action" value="save_matrix">
      <input type="hidden" name="from" value="{start.isoformat()}"><input type="hidden" name="to" value="{end.isoformat()}">
      <input type="hidden" name="matrix_dates" value="{','.join(day.isoformat() for day in days)}">
      <div class="club-att-card-head">
        <div><h2>Concentrado del periodo</h2><p class="muted">Las celdas amarillas todavía no tienen registro.</p></div>
        <div class="club-att-legend"><span>P · Presente</span><span>A · Ausente</span><span>R · Retardo</span><span>J · Justificada</span><span>— · Sin registro</span></div>
      </div>
      <div class="club-att-table-wrap"><table class="club-att-matrix">
        <thead><tr><th class="club-sticky-no">N/P</th><th class="club-sticky-name">Integrante</th><th class="club-sticky-group">Grupo</th>{date_headers}<th>% asist.</th><th>Pend.</th></tr></thead>
        <tbody>{''.join(table_rows)}{empty_row}</tbody>
        <tfoot><tr><th class="club-sticky-no"></th><th class="club-sticky-name">Totales por fecha</th><th class="club-sticky-group"></th>{''.join(daily_totals)}<th colspan="2"></th></tr></tfoot>
      </table></div>
      {save_actions}
    </form>
    <details class="card club-detail-card" {'open' if request.args.get('detail_day') else ''}>
      <summary>Captura detallada por fecha<small>Edita estados y observaciones individuales sin perder el concentrado.</small></summary>
      <form method="get" class="club-detail-toolbar no-print">
        <input type="hidden" name="from" value="{start.isoformat()}"><input type="hidden" name="to" value="{end.isoformat()}">
        <label>Fecha para detalle ({schedule_label})<input id="club-detail-day" type="date" name="detail_day" value="{detail_day.isoformat()}" data-last-valid="{detail_day.isoformat()}" data-weekday="{(scheduled_weekday + 1) % 7}" max="{date.today().isoformat()}" required></label>
        <button type="submit">Cargar detalle</button>
      </form>
      <form method="post">
        <input type="hidden" name="club_attendance_action" value="save_detail">
        <input type="hidden" name="from" value="{start.isoformat()}"><input type="hidden" name="to" value="{end.isoformat()}"><input type="hidden" name="detail_day" value="{detail_day.isoformat()}">
        <div class="scroll"><table><thead><tr><th>N/P</th><th>Integrante</th><th>Grupo</th><th>Estado</th><th>Observación</th></tr></thead><tbody>{''.join(detail_rows)}</tbody></table></div>
        <div style="margin-top:14px">{detail_submit}</div>
      </form>
    </details>

    <div class="card attendance-list-card">
      <h2>Exportar asistencia en Excel</h2>
      <p class="muted">Los archivos conservan el mismo encabezado institucional, logotipos, firmas y configuración de impresión del pase de lista por grupo.</p>
      <div class="club-export-actions no-print">
        <a class="btn" href="/clubs/{cid}/attendance/list.xlsx">Generar lista para imprimir</a>
        <form method="get" action="/clubs/{cid}/attendance/month.xlsx">
          <label>Mes<select name="month">{''.join(f'<option value="{month}" {"selected" if month == date.today().month else ""}>{group_attendance_export.MONTHS_ES[month].title()}</option>' for month in range(1, 13))}</select></label>
          <label>Año<input type="number" name="year" value="{date.today().year}" min="2020" max="2100"></label>
          <button type="submit" class="club-excel-button">Generar concentrado mensual</button>
        </form>
      </div>
    </div>

    <script>
    (() => {{
      const selects = document.querySelectorAll('.club-attendance-state');
      const paint = select => {{ select.dataset.state = select.value; select.closest('td').dataset.missing = String(!select.value); }};
      selects.forEach(select => select.addEventListener('change', () => paint(select)));
      const fill = document.getElementById('club-fill-present');
      if (fill) fill.addEventListener('click', () => {{
        selects.forEach(select => {{
          if (!select.value && !select.disabled) {{ select.value = 'PRESENTE'; paint(select); }}
        }});
      }});
      const detailDay = document.getElementById('club-detail-day');
      if (detailDay) detailDay.addEventListener('change', () => {{
        const selected = new Date(detailDay.value + 'T12:00:00Z');
        if (selected.getUTCDay() !== Number(detailDay.dataset.weekday)) {{
          alert('Selecciona un ' + '{schedule_label}' + ' para registrar la asistencia.');
          detailDay.value = detailDay.dataset.lastValid;
        }} else {{
          detailDay.dataset.lastValid = detailDay.value;
        }}
      }});
    }})();
    </script>
    '''
    return clubs._layout(f'Pase de lista · {club.name}', body)


def install(app):
    app.view_functions['club_attendance'] = _club_attendance_view

    @app.route('/clubs/<int:cid>/attendance/list.xlsx')
    def club_attendance_list_xlsx(cid):
        club = clubs.core.db.session.get(clubs.ClubSport, cid)
        if not club or not clubs._allowed(club):
            return redirect('/clubs')
        filename = (
            f'Lista_Asistencia_{clubs._safe_filename(club.name)}_'
            f'{clubs._safe_filename(clubs.core.cfg().cycle)}.xlsx'
        )
        return send_file(
            _build_club_attendance_list(club),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    @app.route('/clubs/<int:cid>/attendance/month.xlsx')
    def club_attendance_month_xlsx(cid):
        club = clubs.core.db.session.get(clubs.ClubSport, cid)
        if not club or not clubs._allowed(club):
            return redirect('/clubs')
        today = date.today()
        try:
            year = int(request.args.get('year') or today.year)
        except (TypeError, ValueError):
            year = today.year
        try:
            month = int(request.args.get('month') or today.month)
        except (TypeError, ValueError):
            month = today.month
        month = max(1, min(12, month))
        year = max(2020, min(2100, year))
        month_name = group_attendance_export.MONTHS_ES[month].title()
        filename = (
            f'Concentrado_Asistencia_{clubs._safe_filename(club.name)}_'
            f'{clubs._safe_filename(month_name)}_{year}.xlsx'
        )
        return send_file(
            _build_club_monthly_attendance(club, year, month),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    @app.after_request
    def club_attendance_shortcuts(response):
        if (
            'text/html' not in response.headers.get('Content-Type', '')
            or not session.get('uid')
            or not request.path.startswith('/clubs')
        ):
            return response
        html = response.get_data(as_text=True)
        for club in clubs._clubs_for_user():
            marker = f'<a class="btn" href="/clubs/{club.id}">Abrir</a>'
            attendance_link = f'<a class="btn" href="/clubs/{club.id}/attendance">Pase de lista</a>'
            if marker in html and attendance_link not in html:
                html = html.replace(marker, marker + attendance_link, 1)
            old_print = f'<a class="btn alt" href="/clubs/{club.id}/print" target="_blank">Lista imprimible</a>'
            excel_print = f'<a class="btn alt" href="/clubs/{club.id}/attendance/list.xlsx">Formato de asistencia</a>'
            if old_print in html:
                html = html.replace(old_print, excel_print, 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
