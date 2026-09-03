import io

from flask import request, send_file, session
import xlsxwriter

import app as core


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
        ws.insert_image(cell, f'logo.{ext}', {'image_data':stream,'x_scale':x_scale,'y_scale':y_scale,'x_offset':2,'y_offset':2,'object_position':1})
    except Exception:
        pass


def build_attendance_workbook():
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet('LISTA DE ASISTENCIA')

    black = '#000000'
    fmt_small = wb.add_format({'font_name':'Arial','font_size':8,'bold':True,'align':'left','valign':'vcenter'})
    fmt_meta = wb.add_format({'font_name':'Arial','font_size':9,'bold':True,'align':'left','valign':'vcenter'})
    fmt_title = wb.add_format({'font_name':'Arial','font_size':12,'bold':True,'align':'center','valign':'vcenter'})
    fmt_group = wb.add_format({'font_name':'Arial','font_size':10,'bold':True,'align':'center','valign':'vcenter'})
    fmt_head = wb.add_format({'font_name':'Arial','font_size':8,'bold':True,'align':'center','valign':'vcenter','border':1,'border_color':black})
    fmt_num = wb.add_format({'font_name':'Arial','font_size':8,'align':'center','valign':'vcenter','border':1,'border_color':black})
    fmt_name = wb.add_format({'font_name':'Arial','font_size':8,'align':'left','valign':'vcenter','border':1,'border_color':black})
    fmt_day = wb.add_format({'border':1,'border_color':black,'align':'center','valign':'vcenter','font_name':'Arial','font_size':7})
    fmt_date_line = wb.add_format({'font_name':'Arial','font_size':9,'bold':True,'align':'center','valign':'vcenter'})
    fmt_sig = wb.add_format({'font_name':'Arial','font_size':9,'bold':True,'align':'center','valign':'vcenter'})
    fmt_sig_name = wb.add_format({'font_name':'Arial','font_size':9,'bold':True,'align':'center','valign':'vcenter'})

    ws.set_portrait(); ws.set_paper(1); ws.set_margins(0.31, 0.23, 0.33, 0.02); ws.fit_to_pages(1, 1); ws.hide_gridlines(2)
    ws.set_column('A:A', 0.7); ws.set_column('B:B', 4.2); ws.set_column('C:C', 32.4); ws.set_column('D:AD', 1.9); ws.set_column('AE:AF', 3.2)
    ws.set_row(0, 20); ws.set_row(1, 18); ws.set_row(2, 18); ws.set_row(3, 18); ws.set_row(4, 12)

    _insert_logo(ws, 'A1', 'left', 0.48, 0.48)
    _insert_logo(ws, 'AA1', 'right', 0.20, 0.20)
    ws.merge_range('G1:Z1', 'SUBSECRETARÍA DE EDUCACIÓN OBLIGATORIA', fmt_small)
    ws.merge_range('G2:Z2', 'DIRECCIÓN GENERAL DE EDUCACIÓN BÁSICA PRIMER NIVEL', fmt_small)
    ws.merge_range('G3:Z3', 'DIRECCIÓN DE EDUCACIÓN TELESECUNDARIA', fmt_small)
    ws.merge_range('G4:Z4', 'TELESECUNDARIA “BENITO JUÁREZ”', fmt_small)

    cfg = core.cfg(); grade, group_name = _group_data()
    ws.merge_range('A7:J7', 'TURNO: MATUTINO', fmt_meta)
    ws.merge_range('K7:AA7', f'CICLO ESCOLAR: {_cycle_text(cfg.cycle)}', fmt_meta)
    ws.merge_range('A8:J8', 'LOCALIDAD: BERISTAIN, AHUAZOTEPEC, PUEBLA', fmt_meta)
    ws.merge_range('B10:AD10', 'REGISTRO DE ASISTENCIA', fmt_title)
    ws.merge_range('A11:AD11', f'{_grade_title(grade)} GRADO GRUPO “{group_name}”', fmt_group)
    ws.merge_range('B13:B14', 'N/P', fmt_head); ws.merge_range('C13:C14', '          NOMBRE DEL ALUMNO', fmt_head)
    for col in range(3, 30): ws.merge_range(12, col, 13, col, '', fmt_head)

    students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal, core.Student.maternal, core.Student.names).all()
    first_row = 14; data_rows = max(28, len(students))
    for i in range(data_rows):
        row = first_row + i
        if i < len(students):
            s = students[i]; number = s.list_no if s.list_no is not None else i + 1; name = (s.full_name or '').upper()
        else: number, name = '', ''
        ws.write(row, 1, number, fmt_num); ws.write(row, 2, name, fmt_name)
        for col in range(3, 30): ws.write_blank(row, col, None, fmt_day)
        ws.set_row(row, 18)

    end_data = first_row + data_rows - 1; date_row = end_data + 2; teacher_role_row = date_row + 2; director_role_row = teacher_role_row + 1; line_row = teacher_role_row + 3; name_row = line_row + 1
    ws.merge_range(date_row, 1, date_row, 28, 'BERISTAIN, AHUAZOTEPEC, PUE., A _______ DE _________________________ DE __________', fmt_date_line)
    ws.merge_range(teacher_role_row, 2, teacher_role_row, 9, _teacher_label(), fmt_sig)
    ws.merge_range(teacher_role_row, 11, teacher_role_row, 29, 'Vo. Bo.', fmt_sig)
    ws.merge_range(director_role_row, 11, director_role_row, 29, 'DIRECTORA DE LA ESCUELA', fmt_sig)
    ws.merge_range(line_row, 2, line_row, 9, '___________________________________________', fmt_sig); ws.merge_range(line_row, 11, line_row, 29, '_______________________________________', fmt_sig)
    ws.merge_range(name_row, 2, name_row, 9, _teacher_name().upper(), fmt_sig_name); ws.merge_range(name_row, 11, name_row, 29, 'MTRA. NELLY AZUCENA HERNÁNDEZ PICAZO', fmt_sig_name)
    ws.print_area(0, 0, name_row + 1, 29); wb.close(); output.seek(0); return output


def install(app):
    @app.route('/attendance/list.xlsx')
    def attendance_list_xlsx():
        if not session.get('uid'): return core.redirect('/login')
        grade, group_name = _group_data()
        filename = f'Lista_Asistencia_{grade.replace(".º","")}{group_name}_{core.cfg().cycle}.xlsx'.replace('–','-').replace(' ','_')
        return send_file(build_attendance_workbook(), as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.after_request
    def attendance_export_button(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or request.path != '/attendance' or not session.get('uid'): return response
        html = response.get_data(as_text=True)
        if '/attendance/list.xlsx' not in html:
            button = '<div class="card attendance-list-card"><h2>Lista de asistencia para imprimir</h2><p class="muted">Genera el mismo formato institucional con el ciclo escolar, grado y grupo, docente titular y alumnos del grupo activo.</p><a href="/attendance/list.xlsx" style="display:inline-block;text-decoration:none;background:#7b1024;color:white;padding:11px 16px;border-radius:10px;font-weight:800">Generar lista de asistencia en Excel</a></div>'
            marker = '<form method="get" class="card">'; html = html.replace(marker, button + marker, 1) if marker in html else html.replace('</main>', button + '</main>', 1)
            response.set_data(html); response.headers['Content-Length'] = str(len(response.get_data()))
        return response
