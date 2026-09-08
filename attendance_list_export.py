import io
import calendar
from datetime import date

from flask import request, send_file, session
import xlsxwriter

import app as core


MONTHS_ES = {
    1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL', 5: 'MAYO', 6: 'JUNIO',
    7: 'JULIO', 8: 'AGOSTO', 9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
}
STATE_SYMBOL = {'PRESENTE': 'P', 'AUSENTE': 'A', 'RETARDO': 'R', 'JUSTIFICADA': 'J'}


def _cycle_text(value):
    return (value or '2026–2027').replace('–', ' - ').replace('—', ' - ')


def _group_data():
    try:
        import group_workspaces
        return group_workspaces.active_group_tuple()
    except Exception:
        c = core.cfg()
        return c.grade or '1.º', c.group or 'A'


def _grade_title(grade):
    digit = ''.join(ch for ch in (grade or '') if ch.isdigit())
    return {'1': 'PRIMER', '2': 'SEGUNDO', '3': 'TERCER'}.get(digit, (grade or '').upper())


def _teacher_name():
    try:
        import teacher_identity
        return teacher_identity.teacher_name_for_active_group()
    except Exception:
        return 'DOCENTE TITULAR'


def _teacher_label():
    return 'MAESTRA DE GRUPO' if session.get('welcome_gender') == 'F' else 'MAESTRO DE GRUPO'


def _insert_logo(ws, cell, side, x_scale, y_scale):
    try:
        import document_logos
        data, mime = document_logos.get_logo_bytes(side)
        if not data:
            return
        stream = io.BytesIO(data)
        ext = 'png' if mime == 'image/png' else ('webp' if mime == 'image/webp' else 'jpg')
        ws.insert_image(cell, f'logo.{ext}', {'image_data': stream, 'x_scale': x_scale, 'y_scale': y_scale, 'x_offset': 2, 'y_offset': 2, 'object_position': 1})
    except Exception:
        pass


def _base_formats(wb):
    black = '#000000'
    return {
        'small': wb.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'left', 'valign': 'vcenter'}),
        'meta': wb.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'align': 'left', 'valign': 'vcenter'}),
        'title': wb.add_format({'font_name': 'Arial', 'font_size': 12, 'bold': True, 'align': 'center', 'valign': 'vcenter'}),
        'group': wb.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'align': 'center', 'valign': 'vcenter'}),
        'head': wb.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': black, 'text_wrap': True}),
        'num': wb.add_format({'font_name': 'Arial', 'font_size': 8, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': black}),
        'name': wb.add_format({'font_name': 'Arial', 'font_size': 8, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': black}),
        'day': wb.add_format({'border': 1, 'border_color': black, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Arial', 'font_size': 7}),
        'date': wb.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter'}),
        'sig': wb.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter'}),
        'pct': wb.add_format({'font_name': 'Arial', 'font_size': 8, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': black, 'num_format': '0.0%'}),
        'weekend': wb.add_format({'font_name': 'Arial', 'font_size': 7, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': black, 'bg_color': '#EEEEEE'}),
    }


def _institution_header(ws, fmts, last_col, title, subtitle):
    cfg = core.cfg(); grade, group_name = _group_data()
    _insert_logo(ws, 'A1', 'left', 0.48, 0.48)
    right_logo_col = max(4, last_col - 3)
    _insert_logo(ws, xlsxwriter.utility.xl_rowcol_to_cell(0, right_logo_col), 'right', 0.20, 0.20)
    center_end = max(8, last_col - 4)
    ws.merge_range(0, 6, 0, center_end, 'SUBSECRETARÍA DE EDUCACIÓN OBLIGATORIA', fmts['small'])
    ws.merge_range(1, 6, 1, center_end, 'DIRECCIÓN GENERAL DE EDUCACIÓN BÁSICA PRIMER NIVEL', fmts['small'])
    ws.merge_range(2, 6, 2, center_end, 'DIRECCIÓN DE EDUCACIÓN TELESECUNDARIA', fmts['small'])
    ws.merge_range(3, 6, 3, center_end, 'TELESECUNDARIA “BENITO JUÁREZ”', fmts['small'])
    split = max(8, last_col // 3)
    ws.merge_range(6, 0, 6, split, 'TURNO: MATUTINO', fmts['meta'])
    ws.merge_range(6, split + 1, 6, last_col, f'CICLO ESCOLAR: {_cycle_text(cfg.cycle)}', fmts['meta'])
    ws.merge_range(7, 0, 7, last_col, 'LOCALIDAD: BERISTAIN, AHUAZOTEPEC, PUEBLA', fmts['meta'])
    ws.merge_range(9, 1, 9, last_col, title, fmts['title'])
    ws.merge_range(10, 0, 10, last_col, f'{_grade_title(grade)} GRADO GRUPO “{group_name}” · {subtitle}', fmts['group'])


def _signature_block(ws, fmts, start_row, last_col):
    left_start, left_end = 2, min(12, max(8, last_col // 3))
    right_start, right_end = max(left_end + 2, last_col // 2), last_col
    ws.merge_range(start_row, 1, start_row, last_col - 1, 'BERISTAIN, AHUAZOTEPEC, PUE., A _______ DE _________________________ DE __________', fmts['date'])
    ws.merge_range(start_row + 2, left_start, start_row + 2, left_end, _teacher_label(), fmts['sig'])
    ws.merge_range(start_row + 2, right_start, start_row + 2, right_end, 'Vo. Bo.', fmts['sig'])
    ws.merge_range(start_row + 3, right_start, start_row + 3, right_end, 'DIRECTORA DE LA ESCUELA', fmts['sig'])
    ws.merge_range(start_row + 5, left_start, start_row + 5, left_end, '___________________________________________', fmts['sig'])
    ws.merge_range(start_row + 5, right_start, start_row + 5, right_end, '_______________________________________', fmts['sig'])
    ws.merge_range(start_row + 6, left_start, start_row + 6, left_end, _teacher_name().upper(), fmts['sig'])
    ws.merge_range(start_row + 6, right_start, start_row + 6, right_end, 'MTRA. NELLY AZUCENA HERNÁNDEZ PICAZO', fmts['sig'])
    return start_row + 7


def build_attendance_workbook():
    output = io.BytesIO(); wb = xlsxwriter.Workbook(output, {'in_memory': True}); ws = wb.add_worksheet('LISTA DE ASISTENCIA'); f = _base_formats(wb)
    ws.set_portrait(); ws.set_paper(1); ws.set_margins(0.31, 0.23, 0.33, 0.02); ws.fit_to_pages(1, 1); ws.hide_gridlines(2)
    ws.set_column('A:A', 0.7); ws.set_column('B:B', 4.2); ws.set_column('C:C', 32.4); ws.set_column('D:AD', 1.9); ws.set_column('AE:AF', 3.2)
    for r, h in enumerate([20, 18, 18, 18, 12]): ws.set_row(r, h)
    _institution_header(ws, f, 29, 'REGISTRO DE ASISTENCIA', '')
    ws.merge_range('B13:B14', 'N/P', f['head']); ws.merge_range('C13:C14', '          NOMBRE DEL ALUMNO', f['head'])
    for col in range(3, 30): ws.merge_range(12, col, 13, col, '', f['head'])
    students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal, core.Student.maternal, core.Student.names).all()
    first_row = 14; data_rows = max(28, len(students))
    for i in range(data_rows):
        row = first_row + i
        if i < len(students):
            s = students[i]; number = s.list_no if s.list_no is not None else i + 1; name = (s.full_name or '').upper()
        else: number, name = '', ''
        ws.write(row, 1, number, f['num']); ws.write(row, 2, name, f['name'])
        for col in range(3, 30): ws.write_blank(row, col, None, f['day'])
        ws.set_row(row, 18)
    end = _signature_block(ws, f, first_row + data_rows + 1, 29)
    ws.print_area(0, 0, end, 29); wb.close(); output.seek(0); return output


def build_monthly_attendance_workbook(year, month):
    output = io.BytesIO(); wb = xlsxwriter.Workbook(output, {'in_memory': True}); ws = wb.add_worksheet('CONCENTRADO MENSUAL'); f = _base_formats(wb)
    days = calendar.monthrange(year, month)[1]
    first_day_col = 3
    total_start = first_day_col + days
    last_col = total_start + 4
    ws.set_landscape(); ws.set_paper(1); ws.set_margins(0.20, 0.20, 0.28, 0.25); ws.fit_to_pages(1, 1); ws.hide_gridlines(2)
    ws.set_column(0, 0, 0.7); ws.set_column(1, 1, 4.2); ws.set_column(2, 2, 28)
    ws.set_column(first_day_col, first_day_col + days - 1, 2.15)
    ws.set_column(total_start, last_col, 5.5)
    for r, h in enumerate([20, 18, 18, 18, 12]): ws.set_row(r, h)
    month_name = MONTHS_ES.get(month, str(month))
    _institution_header(ws, f, last_col, 'CONCENTRADO MENSUAL DE ASISTENCIA', f'{month_name} {year}')

    header_row = 12
    ws.write(header_row, 1, 'N/P', f['head']); ws.write(header_row, 2, 'NOMBRE DEL ALUMNO', f['head'])
    for day in range(1, days + 1):
        d = date(year, month, day)
        label = f'{day}\n{calendar.day_abbr[d.weekday()][0].upper()}'
        ws.write(header_row, first_day_col + day - 1, label, f['head'])
    for idx, label in enumerate(['P', 'A', 'R', 'J', '% ASIST.']): ws.write(header_row, total_start + idx, label, f['head'])
    ws.set_row(header_row, 30)

    students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal, core.Student.maternal, core.Student.names).all()
    start = date(year, month, 1); end_date = date(year, month, days)
    attendance = core.Attendance.query.filter(core.Attendance.day.between(start, end_date)).all()
    by_key = {(a.student_id, a.day.day): a for a in attendance}
    recorded_days = sorted({a.day.day for a in attendance})

    first_row = header_row + 1; data_rows = max(28, len(students))
    for i in range(data_rows):
        row = first_row + i
        if i >= len(students):
            ws.write_blank(row, 1, None, f['num']); ws.write_blank(row, 2, None, f['name'])
            for col in range(first_day_col, last_col + 1): ws.write_blank(row, col, None, f['day'])
            continue
        s = students[i]; ws.write(row, 1, s.list_no if s.list_no is not None else i + 1, f['num']); ws.write(row, 2, (s.full_name or '').upper(), f['name'])
        counts = {'P': 0, 'A': 0, 'R': 0, 'J': 0}
        for day in range(1, days + 1):
            d = date(year, month, day); a = by_key.get((s.id, day)); symbol = STATE_SYMBOL.get(a.state, '') if a else ''
            if symbol: counts[symbol] += 1
            cell_fmt = f['weekend'] if d.weekday() >= 5 else f['day']
            ws.write(row, first_day_col + day - 1, symbol, cell_fmt)
        for j, key in enumerate(['P', 'A', 'R', 'J']): ws.write(row, total_start + j, counts[key], f['num'])
        considered = sum(counts.values())
        attendance_value = ((counts['P'] + counts['R'] + counts['J']) / considered) if considered else 0
        ws.write_number(row, total_start + 4, attendance_value, f['pct'])
        ws.set_row(row, 18)

    summary_row = first_row + data_rows + 1
    ws.merge_range(summary_row, 1, summary_row, 5, 'RESUMEN DEL MES', f['head'])
    ws.merge_range(summary_row + 1, 1, summary_row + 1, 5, f'Días con asistencia registrada: {len(recorded_days)}', f['meta'])
    ws.merge_range(summary_row + 2, 1, summary_row + 2, min(last_col, 14), 'Clave: P = Presente · A = Ausente · R = Retardo · J = Justificada. El porcentaje considera únicamente los días capturados para cada alumno.', f['meta'])
    sig_end = _signature_block(ws, f, summary_row + 4, last_col)
    ws.freeze_panes(first_row, first_day_col)
    ws.repeat_rows(0, header_row)
    ws.print_area(0, 0, sig_end, last_col)
    wb.close(); output.seek(0); return output


def install(app):
    @app.route('/attendance/list.xlsx')
    def attendance_list_xlsx():
        if not session.get('uid'): return core.redirect('/login')
        grade, group_name = _group_data()
        filename = f'Lista_Asistencia_{grade.replace(".º","")}{group_name}_{core.cfg().cycle}.xlsx'.replace('–', '-').replace(' ', '_')
        return send_file(build_attendance_workbook(), as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.route('/attendance/month.xlsx')
    def attendance_month_xlsx():
        if not session.get('uid'): return core.redirect('/login')
        today = date.today()
        try: year = int(request.args.get('year') or today.year)
        except Exception: year = today.year
        try: month = int(request.args.get('month') or today.month)
        except Exception: month = today.month
        month = max(1, min(12, month)); year = max(2020, min(2100, year))
        grade, group_name = _group_data(); month_name = MONTHS_ES[month].title()
        filename = f'Concentrado_Asistencia_{month_name}_{year}_{grade.replace(".º","")}{group_name}.xlsx'.replace(' ', '_')
        return send_file(build_monthly_attendance_workbook(year, month), as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.after_request
    def attendance_export_button(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or request.path != '/attendance' or not session.get('uid'): return response
        html = response.get_data(as_text=True)
        if '/attendance/list.xlsx' not in html:
            today = date.today()
            month_opts = ''.join(f'<option value="{m}" {"selected" if m == today.month else ""}>{MONTHS_ES[m].title()}</option>' for m in range(1, 13))
            button = f'''<div class="card attendance-list-card"><h2>Reportes de asistencia en Excel</h2><p class="muted">Conservan el formato institucional, datos del grupo activo, docente titular y firmas.</p><div style="display:flex;gap:12px;flex-wrap:wrap;align-items:end"><a href="/attendance/list.xlsx" style="display:inline-block;text-decoration:none;background:#7b1024;color:white;padding:11px 16px;border-radius:10px;font-weight:800">Generar lista para imprimir</a><form method="get" action="/attendance/month.xlsx" style="display:flex;gap:8px;align-items:end;flex-wrap:wrap"><label>Mes<select name="month" style="min-width:135px">{month_opts}</select></label><label>Año<input type="number" name="year" value="{today.year}" min="2020" max="2100" style="width:95px"></label><button style="width:auto;background:#217346">Generar concentrado mensual</button></form></div></div>'''
            marker = '<form method="get" class="card">'; html = html.replace(marker, button + marker, 1) if marker in html else html.replace('</main>', button + '</main>', 1)
            response.set_data(html); response.headers['Content-Length'] = str(len(response.get_data()))
        return response
