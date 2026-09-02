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


def _book():
    output = BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    return wb, output


def _formats(wb):
    return {
        'inst': wb.add_format({'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter'}),
        'brand': wb.add_format({'bold': True, 'font_size': 10, 'font_color': '#7B1024', 'align': 'center', 'valign': 'vcenter'}),
        'title': wb.add_format({'bold': True, 'font_size': 14, 'font_color': '#7B1024', 'align': 'center', 'valign': 'vcenter'}),
        'meta': wb.add_format({'font_size': 9, 'align': 'center'}),
        'head': wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#7B1024', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True}),
        'cell': wb.add_format({'border': 1, 'valign': 'top', 'text_wrap': True, 'font_size': 9}),
        'center': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9}),
        'score': wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.0'}),
    }


def _setup(ws, title, cols, landscape=True):
    f = ws.book_formats
    last = max(0, cols - 1)
    ws.set_paper(1)
    if landscape:
        ws.set_landscape()
    else:
        ws.set_portrait()
    ws.fit_to_pages(1, 0)
    ws.set_margins(0.28, 0.28, 0.35, 0.35)
    ws.repeat_rows(0, 10)
    ws.hide_gridlines(2)
    ws.merge_range(0, 0, 0, min(2, last), 'PUEBLA · Educación · Pensar en Grande · Por Amor a Puebla', f['brand'])
    ws.merge_range(0, min(3, last), 0, last, HEADER_LINES[0], f['inst'])
    for i, line in enumerate(HEADER_LINES[1:], start=1):
        ws.merge_range(i, 0, i, last, line, f['inst'])

    logo = os.path.join(os.path.dirname(__file__), 'static', 'logo-benito-juarez-final.PNG')
    if os.path.exists(logo) and last >= 2:
        try:
            ws.insert_image(0, last, logo, {'x_scale': 0.20, 'y_scale': 0.20, 'x_offset': 5, 'y_offset': 3, 'object_position': 1})
        except Exception:
            pass

    ws.merge_range(8, 0, 8, last, title, f['title'])
    c = core.cfg()
    ws.merge_range(9, 0, 9, last, f'GRADO: {c.grade}    GRUPO: {c.group}    CICLO: {c.cycle}', f['meta'])
    ws.set_row(8, 24)


def _write_table(ws, headers, rows, widths=None, start=11):
    f = ws.book_formats
    for col, h in enumerate(headers):
        ws.write(start, col, h, f['head'])
    for r_idx, row in enumerate(rows, start=start + 1):
        for c_idx, value in enumerate(row):
            fmt = f['center'] if c_idx == 0 else f['cell']
            if isinstance(value, float) and c_idx > 0:
                fmt = f['score'] if 0 <= value <= 10 else f['cell']
            ws.write(r_idx, c_idx, '' if value is None else value, fmt)
    if widths:
        for i, width in enumerate(widths):
            ws.set_column(i, i, width)
    ws.autofilter(start, 0, max(start + 1, start + len(rows)), len(headers) - 1)
    ws.freeze_panes(start + 1, 0)


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
        rows.append([
            s.list_no or '', s.full_name, s.status, s.tutor or '', s.phone or '',
            d.weight_kg if d else '', d.height_cm if d else '', d.top_size if d else '',
            d.bottom_size if d else '', d.sweater_size if d else '', d.shoe_size if d else '',
            d.uniform_notes if d else ''
        ])
    return rows


def _diagnostic_rows():
    from diagnostic import get_diagnostic
    rows = []
    for s in core.Student.query.order_by(core.Student.list_no, core.Student.paternal).all():
        d = get_diagnostic(s.id)
        rows.append([
            s.list_no or '', s.full_name,
            d.diagnostic_score if d else '', d.learning_pace if d else '', d.learning_style if d else '',
            d.perception_channel if d else '', d.performance_level if d else '',
            d.strengths if d else '', d.support_needs if d else '', d.observations if d else ''
        ])
    return rows


def _activities_rows():
    return [[a.activity_date.strftime('%d/%m/%Y') if a.activity_date else '', a.name, a.subject.name if a.subject else '', a.trimester, a.max_score] for a in core.Activity.query.order_by(core.Activity.activity_date).all()]


def _grades_rows():
    rows = []
    for a in core.Activity.query.order_by(core.Activity.activity_date).all():
        grades = {g.student_id: g for g in core.Grade.query.filter_by(activity_id=a.id).all()}
        for s in core.Student.query.order_by(core.Student.list_no, core.Student.paternal).all():
            g = grades.get(s.id)
            val = g.code if g and g.code else (g.score if g and g.score is not None else '')
            rows.append([s.list_no or '', s.full_name, a.name, a.subject.name if a.subject else '', a.trimester, val, a.max_score])
    return rows


def _attendance_rows():
    students = {s.id: s for s in core.Student.query.all()}
    rows = []
    for a in core.Attendance.query.order_by(core.Attendance.day, core.Attendance.student_id).all():
        s = students.get(a.student_id)
        rows.append([a.day.strftime('%d/%m/%Y') if a.day else '', s.list_no if s else '', s.full_name if s else '', a.state, a.notes or ''])
    return rows


def _incident_rows():
    rows = []
    for i in core.Incident.query.order_by(core.Incident.day).all():
        rows.append([i.day.strftime('%d/%m/%Y') if i.day else '', i.student.full_name if i.student else '', i.category, i.description, i.action or '', i.status])
    return rows


def _rubric_rows():
    try:
        from rubric_ai import Rubric, RubricAssessment
    except Exception:
        return []
    rows = []
    students = {s.id: s for s in core.Student.query.all()}
    rubrics = {r.id: r for r in Rubric.query.all()}
    for a in RubricAssessment.query.order_by(RubricAssessment.updated_at).all():
        r = rubrics.get(a.rubric_id)
        s = students.get(a.student_id)
        rows.append([r.activity.name if r and r.activity else '', r.title if r else '', s.full_name if s else '', a.percentage, a.final_score, a.feedback or '', 'Sí' if a.ai_assisted else 'No'])
    return rows


def _make_workbook(section='all'):
    wb, output = _book()

    def add_students():
        _add_sheet(wb, 'Alumnos', 'EXPEDIENTE GENERAL DE ALUMNOS', ['No.', 'Alumno', 'Estado', 'Tutor', 'Teléfono', 'Peso kg', 'Estatura cm', 'Playera/Blusa', 'Pantalón/Falda', 'Suéter/Chamarra', 'Calzado', 'Observaciones'], _students_rows(), [6, 28, 10, 24, 14, 10, 11, 13, 13, 15, 10, 32])

    def add_diagnostic():
        _add_sheet(wb, 'Diagnóstico', 'DIAGNÓSTICO DEL GRUPO', ['No.', 'Alumno', 'Calificación', 'Ritmo', 'Estilo de aprendizaje', 'Canal de percepción', 'Nivel', 'Fortalezas', 'Necesidades de apoyo', 'Observaciones'], _diagnostic_rows(), [6, 28, 11, 14, 18, 20, 16, 30, 30, 30])

    if section in ('all', 'students'): add_students()
    if section in ('all', 'diagnostic'): add_diagnostic()
    if section in ('all', 'activities'):
        _add_sheet(wb, 'Actividades', 'REGISTRO DE ACTIVIDADES', ['Fecha', 'Actividad', 'Asignatura', 'Trimestre', 'Puntaje máximo'], _activities_rows(), [12, 35, 24, 22, 14])
    if section in ('all', 'grades'):
        _add_sheet(wb, 'Calificaciones', 'CONCENTRADO DE CALIFICACIONES', ['No.', 'Alumno', 'Actividad', 'Asignatura', 'Trimestre', 'Calificación', 'Máximo'], _grades_rows(), [6, 28, 32, 24, 22, 12, 10])
    if section in ('all', 'attendance'):
        _add_sheet(wb, 'Asistencia', 'REGISTRO DE ASISTENCIA', ['Fecha', 'No.', 'Alumno', 'Estado', 'Observaciones'], _attendance_rows(), [12, 6, 30, 14, 38])
    if section in ('all', 'incidents'):
        _add_sheet(wb, 'Convivencia', 'REGISTRO DE CONVIVENCIA E INCIDENCIAS', ['Fecha', 'Alumno', 'Categoría', 'Descripción', 'Acciones / acuerdos', 'Estado'], _incident_rows(), [12, 28, 18, 40, 40, 14])
    if section in ('all', 'rubrics'):
        _add_sheet(wb, 'Rúbricas', 'RESULTADOS DE RÚBRICAS', ['Actividad', 'Rúbrica', 'Alumno', 'Porcentaje', 'Calificación', 'Retroalimentación', 'Asistida por IA'], _rubric_rows(), [28, 30, 28, 12, 12, 45, 14])

    wb.close()
    output.seek(0)
    return output


def install(app):
    @app.route('/exports')
    def exports_center():
        if not session.get('uid'):
            return redirect('/login')
        cards = [
            ('Todo el sistema', '/exports/all.xlsx', 'Un libro de Excel con una hoja por apartado.'),
            ('Diagnóstico', '/exports/diagnostic.xlsx', 'Calificación, ritmos, estilos, canales, fortalezas y apoyos.'),
            ('Alumnos y tallas', '/exports/students.xlsx', 'Expediente, tutores, teléfonos, peso, estatura, prendas y calzado.'),
            ('Calificaciones', '/exports/grades.xlsx', 'Concentrado de actividades y calificaciones.'),
            ('Asistencia', '/exports/attendance.xlsx', 'Registro completo de asistencia.'),
            ('Convivencia', '/exports/incidents.xlsx', 'Incidencias, acciones y estado.'),
            ('Actividades', '/exports/activities.xlsx', 'Actividades por asignatura y trimestre.'),
            ('Rúbricas', '/exports/rubrics.xlsx', 'Resultados de evaluación mediante rúbricas.'),
        ]
        html = ''.join(f'<div class="card"><h2>{escape(t)}</h2><p>{escape(d)}</p><a href="{u}" style="display:inline-block;background:#217346;color:#fff;text-decoration:none;padding:10px 14px;border-radius:8px;font-weight:800">Exportar Excel</a></div>' for t,u,d in cards)
        return core.page('Exportar a Excel', f'<h1>Centro de exportación</h1><p class="muted">Todos los archivos se generan en formato Excel, configurados para impresión en hoja carta, con el encabezado institucional.</p><div class="grid">{html}</div>')

    @app.route('/exports/<section>.xlsx')
    def export_xlsx(section):
        if not session.get('uid'):
            return redirect('/login')
        allowed = {'all', 'diagnostic', 'students', 'grades', 'attendance', 'incidents', 'activities', 'rubrics'}
        if section not in allowed:
            return redirect('/exports')
        output = _make_workbook(section)
        return send_file(output, as_attachment=True, download_name=f'{section}_2026-2027.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.after_request
    def exports_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if 'href="/exports"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/exports"><span class="nav-icon">📊</span><span>Exportar Excel</span></a>'
            if marker in html:
                html = html.replace(marker, link + marker, 1)
            else:
                marker2 = '<a href="/logout">Salir</a>'
                if marker2 in html:
                    html = html.replace(marker2, '<a href="/exports">Exportar Excel</a>' + marker2, 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
