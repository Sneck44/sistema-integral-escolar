import os
from io import BytesIO
from html import escape
from flask import session, redirect, send_file

import xlsxwriter
import app as core


HEADER_LINES = [
    'SUBSECRETARÍA DE EDUCACIÓN OBLIGATORIA',
    'DIRECCIÓN GENERAL DE EDUCACIÓN BÁSICA PRIMER NIVEL',
    'DIRECCIÓN DE EDUCACIÓN TELESECUNDARIA',
    'JEFATURA DE SECTOR 4 FEDERAL CCT 21FTS4004Q',
    'SUPERVISIÓN ESCOLAR 24 CCT 21FTV2524Z',
    'TELESECUNDARIA FEDERAL “BENITO JUÁREZ” C.C.T. 21DTV0109Z',
    'CICLO ESCOLAR 2026-2027',
]

BASE_DIR = os.path.dirname(__file__)
PUEBLA_LOGOS = os.path.join(BASE_DIR, 'static', 'encabezado-logos-puebla.png')
TELESEC_LOGO = os.path.join(BASE_DIR, 'static', 'encabezado-logo-telesecundaria.jpeg')


def _book():
    output = BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    return wb, output


def _formats(wb):
    return {
        'inst': wb.add_format({'bold': True, 'font_size': 8, 'align': 'center', 'valign': 'vcenter'}),
        'title': wb.add_format({'bold': True, 'font_size': 14, 'font_color': '#7B1024', 'align': 'center', 'valign': 'vcenter'}),
        'meta': wb.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter'}),
        'head': wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#7B1024', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True}),
        'subhead': wb.add_format({'bold': True, 'bg_color': '#EAD9DE', 'font_color': '#5A0C1B', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True}),
        'cell': wb.add_format({'border': 1, 'valign': 'top', 'text_wrap': True, 'font_size': 9}),
        'center': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9}),
        'score': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.0', 'font_size': 9}),
        'pct': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.0"%"', 'font_size': 9}),
        'present': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9EAD3', 'font_color': '#245B20', 'bold': True}),
        'absence': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F4CCCC', 'font_color': '#8A1C1C', 'bold': True}),
        'late': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FCE5CD', 'font_color': '#8A4B08', 'bold': True}),
        'justified': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9EAF7', 'font_color': '#174A78', 'bold': True}),
        'good': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9EAD3', 'font_color': '#245B20', 'bold': True, 'num_format': '0.0'}),
        'warn': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFF2CC', 'font_color': '#7A5A00', 'bold': True, 'num_format': '0.0'}),
        'bad': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F4CCCC', 'font_color': '#8A1C1C', 'bold': True, 'num_format': '0.0'}),
        'legend': wb.add_format({'font_size': 8, 'italic': True, 'align': 'left'}),
        'summary_label': wb.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'right'}),
        'summary_value': wb.add_format({'bold': True, 'border': 1, 'align': 'center'}),
        'kpi_label': wb.add_format({'bold': True, 'font_size': 9, 'font_color': '#666666', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#F7F7F7'}),
        'kpi_value': wb.add_format({'bold': True, 'font_size': 18, 'font_color': '#7B1024', 'align': 'center', 'valign': 'vcenter', 'border': 1}),
        'note': wb.add_format({'font_size': 9, 'text_wrap': True, 'valign': 'top'}),
        'signature': wb.add_format({'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'top'}),
        'signature_name': wb.add_format({'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'top', 'top': 1}),
    }


def _setup(ws, title, cols, landscape=True):
    f = ws.book_formats
    last = max(0, cols - 1)
    ws.set_paper(1)
    ws.set_landscape() if landscape else ws.set_portrait()
    ws.fit_to_pages(1, 0)
    ws.set_margins(0.28, 0.28, 0.30, 0.30)
    ws.hide_gridlines(2)
    for r in range(7):
        ws.set_row(r, 34 if r == 0 else 18)
    try:
        if os.path.exists(PUEBLA_LOGOS):
            ws.insert_image(0, 0, PUEBLA_LOGOS, {'x_scale': 0.43, 'y_scale': 0.43, 'x_offset': 3, 'y_offset': 2, 'object_position': 1})
        if os.path.exists(TELESEC_LOGO):
            ws.insert_image(0, max(0, last - 1), TELESEC_LOGO, {'x_scale': 0.48, 'y_scale': 0.48, 'x_offset': 3, 'y_offset': 2, 'object_position': 1})
    except Exception:
        pass

    center_start = min(3, last)
    center_end = max(center_start, last - 2)
    for i, line in enumerate(HEADER_LINES):
        ws.merge_range(i, center_start, i, center_end, line, f['inst'])

    ws.merge_range(8, 0, 8, last, title, f['title'])
    c = core.cfg()
    ws.merge_range(9, 0, 9, last, f'GRADO: {c.grade}     GRUPO: {c.group}     CICLO ESCOLAR: {c.cycle}', f['meta'])
    ws.set_row(8, 24)
    ws.repeat_rows(0, 11)


def _add_signatures(ws, last_data_row, cols):
    f = ws.book_formats
    last = max(1, cols - 1)
    sig_row = last_data_row + 4
    left_end = max(1, last // 2 - 1)
    right_start = min(last, last // 2 + 1)
    ws.merge_range(sig_row, 0, sig_row, left_end, '________________________________________', f['signature'])
    ws.merge_range(sig_row + 1, 0, sig_row + 1, left_end, 'NOMBRE Y FIRMA DEL DOCENTE', f['signature'])
    ws.merge_range(sig_row, right_start, sig_row, last, '________________________________________', f['signature'])
    ws.merge_range(sig_row + 1, right_start, sig_row + 1, last, 'Vo. Bo. DIRECTORA', f['signature'])
    ws.merge_range(sig_row + 2, right_start, sig_row + 2, last, 'MTRA. NELLY AZUCENA HERNÁNDEZ PICAZO', f['signature_name'])
    ws.set_print_area(0, 0, sig_row + 2, last)


def _write_table(ws, headers, rows, widths=None, start=11):
    f = ws.book_formats
    for col, h in enumerate(headers):
        ws.write(start, col, h, f['head'])
    ws.set_row(start, 30)
    for r_idx, row in enumerate(rows, start=start + 1):
        for c_idx, value in enumerate(row):
            fmt = f['center'] if c_idx == 0 else f['cell']
            if isinstance(value, float) and c_idx > 0:
                fmt = f['score'] if 0 <= value <= 10 else f['cell']
            ws.write(r_idx, c_idx, '' if value is None else value, fmt)
    if widths:
        for i, width in enumerate(widths):
            ws.set_column(i, i, width)
    last_data = start + max(1, len(rows))
    ws.autofilter(start, 0, last_data, len(headers) - 1)
    ws.freeze_panes(start + 1, 2 if len(headers) > 6 else 0)
    _add_signatures(ws, last_data, len(headers))
    return last_data


def _add_sheet(wb, name, title, headers, rows, widths=None, landscape=True):
    ws = wb.add_worksheet(name[:31])
    ws.book_formats = _formats(wb)
    _setup(ws, title, len(headers), landscape)
    _write_table(ws, headers, rows, widths)
    return ws


def _students_rows():
    try:
        from student_details import StudentDetails
    except Exception:
        StudentDetails = None
    rows = []
    for s in core.Student.query.order_by(core.Student.list_no, core.Student.paternal).all():
        d = StudentDetails.query.filter_by(student_id=s.id).first() if StudentDetails else None
        rows.append([s.list_no or '', s.full_name, s.status, s.tutor or '', s.phone or '', d.weight_kg if d else '', d.height_cm if d else '', d.top_size if d else '', d.bottom_size if d else '', d.sweater_size if d else '', d.shoe_size if d else '', d.uniform_notes if d else ''])
    return rows


def _diagnostic_rows():
    from diagnostic import get_diagnostic
    rows = []
    for s in core.Student.query.order_by(core.Student.list_no, core.Student.paternal).all():
        d = get_diagnostic(s.id)
        rows.append([s.list_no or '', s.full_name, d.diagnostic_score if d else '', d.learning_pace if d else '', d.learning_style if d else '', d.perception_channel if d else '', d.performance_level if d else '', d.strengths if d else '', d.support_needs if d else '', d.observations if d else ''])
    return rows


def _activities_rows():
    return [[a.activity_date.strftime('%d/%m/%Y') if a.activity_date else '', a.name, a.subject.name if a.subject else '', a.trimester, a.max_score] for a in core.Activity.query.order_by(core.Activity.activity_date).all()]


def _grade_value_10(g, activity):
    if not g or g.score is None or not activity or not activity.max_score:
        return None
    return round((g.score / activity.max_score) * 10, 1)


def _grades_matrix():
    students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()
    activities = core.Activity.query.order_by(core.Activity.activity_date, core.Activity.id).all()
    headers = ['No.', 'Alumno'] + [a.name for a in activities] + ['PROMEDIO', 'NIVEL', 'SEGUIMIENTO']
    rows = []
    for s in students:
        values = []
        numeric = []
        for a in activities:
            g = core.Grade.query.filter_by(student_id=s.id, activity_id=a.id).first()
            if g and g.code:
                value = g.code
            else:
                value = _grade_value_10(g, a)
                if value is not None:
                    numeric.append(value)
            values.append('' if value is None else value)
        avg = round(sum(numeric) / len(numeric), 1) if numeric else ''
        if avg == '':
            level, follow = 'SIN DATOS', 'Capturar evidencias'
        elif avg >= 9:
            level, follow = 'DESTACADO', 'Mantener y enriquecer'
        elif avg >= 8:
            level, follow = 'SATISFACTORIO', 'Seguimiento ordinario'
        elif avg >= 6:
            level, follow = 'EN PROCESO', 'Reforzar aprendizajes'
        else:
            level, follow = 'REQUIERE APOYO', 'Atención prioritaria'
        rows.append([s.list_no or '', s.full_name] + values + [avg, level, follow])
    return headers, rows, activities


def _add_grades_sheet(wb):
    headers, rows, activities = _grades_matrix()
    ws = wb.add_worksheet('Calificaciones')
    ws.book_formats = _formats(wb)
    _setup(ws, 'CONCENTRADO DE CALIFICACIONES DEL GRUPO', len(headers), True)
    f = ws.book_formats
    start = 12
    ws.merge_range(10, 0, 10, len(headers)-1, 'LECTURA RÁPIDA: verde = desempeño favorable · amarillo = requiere refuerzo · rojo = atención prioritaria. Las actividades se normalizan a escala de 10.', f['legend'])
    for col, h in enumerate(headers):
        ws.write(start, col, h, f['head'])
    ws.set_row(start, 42)
    act_count = len(activities)
    avg_col = 2 + act_count
    for r_idx, row in enumerate(rows, start=start + 1):
        for c_idx, value in enumerate(row):
            if c_idx == 0:
                fmt = f['center']
            elif c_idx == 1:
                fmt = f['cell']
            elif c_idx == avg_col and isinstance(value, (int, float)):
                fmt = f['good'] if value >= 8 else f['warn'] if value >= 6 else f['bad']
            else:
                fmt = f['center'] if c_idx >= 2 else f['cell']
            ws.write(r_idx, c_idx, value, fmt)
    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 30)
    if act_count:
        ws.set_column(2, 1 + act_count, 12)
    ws.set_column(avg_col, avg_col, 11)
    ws.set_column(avg_col + 1, avg_col + 1, 18)
    ws.set_column(avg_col + 2, avg_col + 2, 24)
    ws.freeze_panes(start + 1, 2)
    ws.autofilter(start, 0, start + max(1, len(rows)), len(headers)-1)
    if rows and act_count:
        ws.conditional_format(start + 1, 2, start + len(rows), 1 + act_count, {'type': 'cell', 'criteria': '<', 'value': 6, 'format': f['bad']})
        ws.conditional_format(start + 1, 2, start + len(rows), 1 + act_count, {'type': 'cell', 'criteria': 'between', 'minimum': 6, 'maximum': 7.9, 'format': f['warn']})
        ws.conditional_format(start + 1, 2, start + len(rows), 1 + act_count, {'type': 'cell', 'criteria': '>=', 'value': 8, 'format': f['good']})
    summary = start + max(1, len(rows)) + 2
    avgs = [r[avg_col] for r in rows if isinstance(r[avg_col], (int, float))]
    group_avg = round(sum(avgs) / len(avgs), 1) if avgs else 0
    priority = sum(1 for r in rows if isinstance(r[avg_col], (int, float)) and r[avg_col] < 6)
    reinforcement = sum(1 for r in rows if isinstance(r[avg_col], (int, float)) and 6 <= r[avg_col] < 8)
    favorable = sum(1 for r in rows if isinstance(r[avg_col], (int, float)) and r[avg_col] >= 8)
    ws.merge_range(summary, 0, summary, 1, 'RESUMEN PARA TOMA DE DECISIONES', f['subhead'])
    labels = [('Promedio grupal', group_avg), ('Atención prioritaria (<6)', priority), ('Requieren refuerzo (6–7.9)', reinforcement), ('Desempeño favorable (≥8)', favorable)]
    for i, (label, value) in enumerate(labels, start=1):
        ws.write(summary+i, 0, label, f['summary_label']); ws.write(summary+i, 1, value, f['summary_value'])
    _add_signatures(ws, summary + len(labels), len(headers))
    return ws


def _attendance_matrix():
    students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()
    records = core.Attendance.query.order_by(core.Attendance.day, core.Attendance.student_id).all()
    days = sorted({a.day for a in records if a.day})
    by_key = {(a.student_id, a.day): (a.state or '').upper() for a in records}
    headers = ['No.', 'Alumno'] + [d.strftime('%d/%m') for d in days] + ['P', 'F', 'R', 'J', '% ASIST.', 'SEGUIMIENTO']
    rows = []
    for s in students:
        states = []; p = f = r = j = 0
        for d in days:
            state = by_key.get((s.id, d), '')
            if state in ('PRESENTE', 'P'): code = 'P'; p += 1
            elif state in ('RETARDO', 'R'): code = 'R'; r += 1
            elif state in ('JUSTIFICADA', 'JUSTIFICADO', 'J'): code = 'J'; j += 1
            elif state in ('FALTA', 'AUSENTE', 'F'): code = 'F'; f += 1
            elif state: code = state[:1]
            else: code = ''
            states.append(code)
        considered = p + f + r + j
        pct = round(((p + r + j) / considered) * 100, 1) if considered else ''
        follow = 'Sin datos' if pct == '' else ('Atención prioritaria' if pct < 80 else 'Vigilar' if pct < 90 else 'Adecuada')
        rows.append([s.list_no or '', s.full_name] + states + [p, f, r, j, pct, follow])
    return headers, rows, days


def _add_attendance_sheet(wb):
    headers, rows, days = _attendance_matrix()
    ws = wb.add_worksheet('Asistencia')
    ws.book_formats = _formats(wb)
    _setup(ws, 'CONCENTRADO DE ASISTENCIA DEL GRUPO', len(headers), True)
    f = ws.book_formats
    start = 12
    ws.merge_range(10, 0, 10, len(headers)-1, 'CLAVES: P = Presente   F = Falta   R = Retardo   J = Justificada. Seguimiento: <80% atención prioritaria; 80–89.9% vigilar; ≥90% adecuada.', f['legend'])
    for col, h in enumerate(headers): ws.write(start, col, h, f['head'])
    ws.set_row(start, 32)
    day_count = len(days)
    pct_col = len(headers) - 2
    for r_idx, row in enumerate(rows, start=start + 1):
        for c_idx, value in enumerate(row):
            if c_idx == 0: fmt = f['center']
            elif 2 <= c_idx < 2 + day_count: fmt = {'P': f['present'], 'F': f['absence'], 'R': f['late'], 'J': f['justified']}.get(value, f['center'])
            elif c_idx == pct_col and isinstance(value, (int, float)): fmt = f['good'] if value >= 90 else f['warn'] if value >= 80 else f['bad']
            else: fmt = f['center'] if c_idx >= 2 + day_count else f['cell']
            ws.write(r_idx, c_idx, value, fmt)
    ws.set_column(0, 0, 5); ws.set_column(1, 1, 28)
    if day_count: ws.set_column(2, 1 + day_count, 5)
    ws.set_column(2 + day_count, len(headers)-2, 9); ws.set_column(len(headers)-1, len(headers)-1, 22)
    ws.freeze_panes(start + 1, 2)
    last_data = start + max(1, len(rows))
    summary_row = last_data + 2
    total_marks = sum((r[-6] + r[-5] + r[-4] + r[-3]) for r in rows) if rows else 0
    total_present = sum(r[-6] for r in rows) if rows else 0
    total_late = sum(r[-4] for r in rows) if rows else 0
    total_just = sum(r[-3] for r in rows) if rows else 0
    group_pct = round(((total_present + total_late + total_just) / total_marks) * 100, 1) if total_marks else 0
    priority = sum(1 for r in rows if isinstance(r[-2], (int, float)) and r[-2] < 80)
    ws.merge_range(summary_row, 0, summary_row, 1, 'RESUMEN DEL GRUPO', f['subhead'])
    ws.write(summary_row+1, 0, 'Alumnos activos', f['summary_label']); ws.write(summary_row+1, 1, len(rows), f['summary_value'])
    ws.write(summary_row+2, 0, '% asistencia grupal', f['summary_label']); ws.write(summary_row+2, 1, group_pct, f['summary_value'])
    ws.write(summary_row+3, 0, 'Atención prioritaria', f['summary_label']); ws.write(summary_row+3, 1, priority, f['summary_value'])
    _add_signatures(ws, summary_row + 3, len(headers))
    return ws


def _incident_rows():
    return [[i.day.strftime('%d/%m/%Y') if i.day else '', i.student.full_name if i.student else '', i.category, i.description, i.action or '', i.status] for i in core.Incident.query.order_by(core.Incident.day).all()]


def _rubric_rows():
    try:
        from rubric_ai import Rubric, RubricAssessment
    except Exception:
        return []
    rows = []; students = {s.id: s for s in core.Student.query.all()}; rubrics = {r.id: r for r in Rubric.query.all()}
    for a in RubricAssessment.query.order_by(RubricAssessment.updated_at).all():
        r = rubrics.get(a.rubric_id); s = students.get(a.student_id)
        rows.append([r.activity.name if r and r.activity else '', r.title if r else '', s.full_name if s else '', a.percentage, a.final_score, a.feedback or '', 'Sí' if a.ai_assisted else 'No'])
    return rows


def _overview_metrics():
    students = core.Student.query.filter_by(status='ACTIVO').all()
    student_avgs = []
    for s in students:
        vals = []
        for g in core.Grade.query.filter_by(student_id=s.id).all():
            a = core.db.session.get(core.Activity, g.activity_id)
            v = _grade_value_10(g, a)
            if v is not None: vals.append(v)
        if vals: student_avgs.append(sum(vals)/len(vals))
    group_avg = round(sum(student_avgs)/len(student_avgs), 1) if student_avgs else 0
    total = core.Attendance.query.count()
    present = core.Attendance.query.filter(core.Attendance.state.in_(['PRESENTE','RETARDO','JUSTIFICADA','JUSTIFICADO'])).count()
    attendance = round(present*100/total, 1) if total else 0
    open_incidents = core.Incident.query.filter_by(status='ABIERTA').count()
    priority = sum(1 for x in student_avgs if x < 6)
    return len(students), group_avg, attendance, open_incidents, priority


def _add_overview_sheet(wb):
    ws = wb.add_worksheet('Resumen')
    ws.book_formats = _formats(wb)
    _setup(ws, 'RESUMEN EJECUTIVO DEL GRUPO', 8, True)
    f = ws.book_formats
    students, avg, attendance, incidents, priority = _overview_metrics()
    kpis = [('Alumnos activos', students), ('Promedio grupal', avg), ('Asistencia', f'{attendance}%'), ('Incidencias abiertas', incidents), ('Atención prioritaria', priority)]
    col = 0
    for label, value in kpis:
        ws.merge_range(12, col, 12, col+1, label, f['kpi_label'])
        ws.merge_range(13, col, 14, col+1, value, f['kpi_value'])
        col += 2
        if col >= 8: break
    ws.merge_range(17, 0, 17, 7, 'LECTURA RÁPIDA', f['subhead'])
    notes = [
        '• Promedio menor de 6: atención prioritaria y recuperación de aprendizajes.',
        '• Promedio de 6 a 7.9: reforzar y dar seguimiento.',
        '• Promedio de 8 o más: desempeño favorable.',
        '• Asistencia menor de 80%: atención prioritaria; de 80 a 89.9%: vigilar; 90% o más: adecuada.',
        '• Utiliza los filtros de cada hoja para localizar rápidamente alumnos, niveles, incidencias o necesidades de apoyo.'
    ]
    ws.merge_range(18, 0, 23, 7, '\n'.join(notes), f['note'])
    ws.set_column(0, 7, 15)
    ws.set_row(18, 88)
    return ws


def _make_workbook(section='all'):
    wb, output = _book()
    if section == 'all':
        _add_overview_sheet(wb)
    if section in ('all', 'students'):
        _add_sheet(wb, 'Alumnos', 'EXPEDIENTE GENERAL DE ALUMNOS', ['No.', 'Alumno', 'Estado', 'Tutor', 'Teléfono', 'Peso kg', 'Estatura cm', 'Playera/Blusa', 'Pantalón/Falda', 'Suéter/Chamarra', 'Calzado', 'Observaciones'], _students_rows(), [6, 28, 10, 24, 14, 10, 11, 13, 13, 15, 10, 32])
    if section in ('all', 'diagnostic'):
        _add_sheet(wb, 'Diagnóstico', 'DIAGNÓSTICO DEL GRUPO', ['No.', 'Alumno', 'Calificación', 'Ritmo', 'Estilo de aprendizaje', 'Canal de percepción', 'Nivel', 'Fortalezas', 'Necesidades de apoyo', 'Observaciones'], _diagnostic_rows(), [6, 28, 11, 14, 18, 20, 16, 30, 30, 30])
    if section in ('all', 'activities'):
        _add_sheet(wb, 'Actividades', 'REGISTRO DE ACTIVIDADES', ['Fecha', 'Actividad', 'Asignatura', 'Trimestre', 'Puntaje máximo'], _activities_rows(), [12, 35, 24, 22, 14], False)
    if section in ('all', 'grades'):
        _add_grades_sheet(wb)
    if section in ('all', 'attendance'):
        _add_attendance_sheet(wb)
    if section in ('all', 'incidents'):
        _add_sheet(wb, 'Convivencia', 'REGISTRO DE CONVIVENCIA E INCIDENCIAS', ['Fecha', 'Alumno', 'Categoría', 'Descripción', 'Acciones / acuerdos', 'Estado'], _incident_rows(), [12, 28, 18, 40, 40, 14])
    if section in ('all', 'rubrics'):
        _add_sheet(wb, 'Rúbricas', 'RESULTADOS DE RÚBRICAS', ['Actividad', 'Rúbrica', 'Alumno', 'Porcentaje', 'Calificación', 'Retroalimentación', 'Asistida por IA'], _rubric_rows(), [28, 30, 28, 12, 12, 45, 14])
    wb.close(); output.seek(0); return output


def install(app):
    @app.route('/exports')
    def exports_center():
        if not session.get('uid'): return redirect('/login')
        cards = [
            ('Todo el sistema', '/exports/all.xlsx', 'Incluye una primera hoja de resumen ejecutivo y concentrados listos para analizar.'),
            ('Diagnóstico', '/exports/diagnostic.xlsx', 'Calificación, ritmos, estilos, canales, fortalezas y necesidades de apoyo.'),
            ('Alumnos y tallas', '/exports/students.xlsx', 'Expediente, tutores, teléfonos, peso, estatura, prendas y calzado.'),
            ('Calificaciones', '/exports/grades.xlsx', 'Un alumno por fila, actividades por columnas, promedio, nivel y seguimiento.'),
            ('Asistencia', '/exports/attendance.xlsx', 'Matriz por alumno y fecha, porcentaje y alerta de seguimiento.'),
            ('Convivencia', '/exports/incidents.xlsx', 'Incidencias, acciones, acuerdos y estado.'),
            ('Actividades', '/exports/activities.xlsx', 'Actividades por asignatura y trimestre.'),
            ('Rúbricas', '/exports/rubrics.xlsx', 'Resultados de evaluación mediante rúbricas.'),
        ]
        html = ''.join(f'<div class="card"><h2>{escape(t)}</h2><p>{escape(d)}</p><a href="{u}" style="display:inline-block;background:#217346;color:#fff;text-decoration:none;padding:10px 14px;border-radius:8px;font-weight:800">Exportar Excel</a></div>' for t,u,d in cards)
        return core.page('Exportar a Excel', f'<h1>Centro de exportación</h1><p class="muted">Los concentrados ahora priorizan lectura rápida, análisis docente, filtros, alertas visuales y toma de decisiones.</p><div class="grid">{html}</div>')

    @app.route('/exports/<section>.xlsx')
    def export_xlsx(section):
        if not session.get('uid'): return redirect('/login')
        allowed = {'all', 'diagnostic', 'students', 'grades', 'attendance', 'incidents', 'activities', 'rubrics'}
        if section not in allowed: return redirect('/exports')
        output = _make_workbook(section)
        return send_file(output, as_attachment=True, download_name=f'{section}_2026-2027.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.after_request
    def exports_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'): return response
        html = response.get_data(as_text=True)
        if 'href="/exports"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/exports"><span class="nav-icon">📊</span><span>Exportar Excel</span></a>'
            if marker in html: html = html.replace(marker, link + marker, 1)
            else:
                marker2 = '<a href="/logout">Salir</a>'
                if marker2 in html: html = html.replace(marker2, '<a href="/exports">Exportar Excel</a>' + marker2, 1)
        response.set_data(html); response.headers['Content-Length'] = str(len(response.get_data())); return response
