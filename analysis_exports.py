import app as core
import excel_exports as base


def _level(avg):
    if avg == '':
        return 'SIN DATOS'
    if avg >= 9:
        return 'DESTACADO'
    if avg >= 8:
        return 'SATISFACTORIO'
    if avg >= 6:
        return 'EN PROCESO'
    return 'REQUIERE APOYO'


def _grade_matrix():
    students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()
    activities = core.Activity.query.order_by(core.Activity.activity_date, core.Activity.id).all()
    grade_map = {(g.student_id, g.activity_id): g for g in core.Grade.query.all()}
    headers = ['No.', 'Alumno']
    for a in activities:
        short = (a.name or 'Actividad').strip()
        if len(short) > 24:
            short = short[:21] + '…'
        headers.append(short)
    headers += ['Promedio', 'Nivel', 'Actividades evaluadas', 'Pendientes']

    rows = []
    for s in students:
        vals = []
        numeric = []
        evaluated = 0
        pending = 0
        for a in activities:
            g = grade_map.get((s.id, a.id))
            if g and g.code:
                vals.append(g.code)
                evaluated += 1
                if g.code.upper() in ('NP', 'NE'):
                    pending += 1
            elif g and g.score is not None:
                scaled = round((g.score / a.max_score) * 10, 1) if a.max_score else round(g.score, 1)
                vals.append(scaled)
                numeric.append(scaled)
                evaluated += 1
            else:
                vals.append('')
                pending += 1
        avg = round(sum(numeric) / len(numeric), 1) if numeric else ''
        rows.append([s.list_no or '', s.full_name] + vals + [avg, _level(avg), evaluated, pending])
    return students, activities, headers, rows


def _add_grade_analysis_sheet(wb):
    students, activities, headers, rows = _grade_matrix()
    ws = wb.add_worksheet('Calificaciones')
    ws.book_formats = base._formats(wb)
    base._setup(ws, 'CONCENTRADO ANALÍTICO DE CALIFICACIONES', len(headers), True)
    f = ws.book_formats
    start = 13
    last_col = len(headers) - 1

    ws.merge_range(10, 0, 10, last_col, 'LECTURA RÁPIDA: verde = desempeño satisfactorio/destacado · amarillo = en proceso · rojo = requiere apoyo', f['legend'])
    ws.merge_range(11, 0, 11, last_col, 'Las calificaciones de actividades con puntaje distinto de 10 se convierten automáticamente a escala de 0 a 10.', f['legend'])

    for c, h in enumerate(headers):
        ws.write(start, c, h, f['head'])
    ws.set_row(start, 42)

    activity_count = len(activities)
    avg_col = 2 + activity_count
    level_col = avg_col + 1
    eval_col = avg_col + 2
    pending_col = avg_col + 3

    for r_idx, row in enumerate(rows, start + 1):
        for c_idx, value in enumerate(row):
            if c_idx == 0:
                fmt = f['center']
            elif c_idx == 1:
                fmt = f['cell']
            elif 2 <= c_idx < avg_col:
                fmt = f['score'] if isinstance(value, (int, float)) else f['center']
            elif c_idx == avg_col:
                fmt = f['score']
            else:
                fmt = f['center']
            ws.write(r_idx, c_idx, value, fmt)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 30)
    if activity_count:
        ws.set_column(2, avg_col - 1, 11)
    ws.set_column(avg_col, avg_col, 11)
    ws.set_column(level_col, level_col, 18)
    ws.set_column(eval_col, pending_col, 13)
    ws.freeze_panes(start + 1, 2)
    last_data = start + max(1, len(rows))
    if rows:
        ws.autofilter(start, 0, last_data, last_col)
        ws.conditional_format(start + 1, avg_col, last_data, avg_col, {'type': 'cell', 'criteria': '<', 'value': 6, 'format': f['absence']})
        ws.conditional_format(start + 1, avg_col, last_data, avg_col, {'type': 'cell', 'criteria': 'between', 'minimum': 6, 'maximum': 7.9, 'format': f['late']})
        ws.conditional_format(start + 1, avg_col, last_data, avg_col, {'type': 'cell', 'criteria': '>=', 'value': 8, 'format': f['present']})

    summary = last_data + 2
    avgs = [r[avg_col] for r in rows if isinstance(r[avg_col], (int, float))]
    group_avg = round(sum(avgs) / len(avgs), 1) if avgs else 0
    support = sum(1 for x in avgs if x < 6)
    process = sum(1 for x in avgs if 6 <= x < 8)
    satisfactory = sum(1 for x in avgs if x >= 8)
    total_pending = sum(r[pending_col] for r in rows) if rows else 0

    ws.merge_range(summary, 0, summary, 2, 'RESUMEN PARA TOMA DE DECISIONES', f['subhead'])
    metrics = [
        ('Promedio grupal', group_avg),
        ('Alumnos con promedio menor a 6', support),
        ('Alumnos en proceso (6.0–7.9)', process),
        ('Alumnos satisfactorios/destacados (8.0–10)', satisfactory),
        ('Actividades pendientes o sin registro', total_pending),
    ]
    for i, (label, value) in enumerate(metrics, summary + 1):
        ws.merge_range(i, 0, i, 1, label, f['summary_label'])
        ws.write(i, 2, value, f['score'] if label == 'Promedio grupal' else f['summary_value'])

    chart_row = summary
    if len(rows) and len(avgs):
        chart = wb.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Promedio',
            'categories': ['Calificaciones', start + 1, 1, last_data, 1],
            'values': ['Calificaciones', start + 1, avg_col, last_data, avg_col],
        })
        chart.set_title({'name': 'Promedio por alumno'})
        chart.set_y_axis({'min': 0, 'max': 10, 'major_unit': 1})
        chart.set_legend({'none': True})
        ws.insert_chart(chart_row, 4, chart, {'x_scale': 1.25, 'y_scale': 1.0})

    base._add_signatures(ws, summary + len(metrics) + 1, len(headers))
    return ws


def _add_overview_sheet(wb):
    students = core.Student.query.filter_by(status='ACTIVO').all()
    _, _, _, grade_rows = _grade_matrix()
    avg_values = []
    if grade_rows:
        activity_count = len(core.Activity.query.all())
        avg_col = 2 + activity_count
        avg_values = [r[avg_col] for r in grade_rows if isinstance(r[avg_col], (int, float))]

    attendance_headers, attendance_rows, _ = base._attendance_matrix()
    attendance_values = [r[-1] for r in attendance_rows if isinstance(r[-1], (int, float))]
    incidents_open = core.Incident.query.filter_by(status='ABIERTA').count()

    ws = wb.add_worksheet('Resumen')
    ws.book_formats = base._formats(wb)
    base._setup(ws, 'RESUMEN EJECUTIVO DEL GRUPO', 6, False)
    f = ws.book_formats
    ws.merge_range(11, 0, 11, 5, 'INDICADORES CLAVE PARA ANÁLISIS RÁPIDO', f['subhead'])
    values = [
        ('Alumnos activos', len(students), 'Matrícula vigente del grupo'),
        ('Promedio grupal', round(sum(avg_values)/len(avg_values), 1) if avg_values else '—', 'Promedio de actividades registradas'),
        ('Asistencia grupal', round(sum(attendance_values)/len(attendance_values), 1) if attendance_values else '—', 'Porcentaje medio de asistencia'),
        ('Requieren apoyo académico', sum(1 for x in avg_values if x < 6), 'Promedio menor a 6'),
        ('Incidencias abiertas', incidents_open, 'Casos pendientes de seguimiento'),
    ]
    for idx, (label, value, note) in enumerate(values, 13):
        ws.merge_range(idx, 0, idx, 2, label, f['summary_label'])
        ws.write(idx, 3, value, f['summary_value'])
        ws.merge_range(idx, 4, idx, 5, note, f['cell'])
    ws.set_column(0, 2, 18)
    ws.set_column(3, 3, 14)
    ws.set_column(4, 5, 24)
    base._add_signatures(ws, 19, 6)
    return ws


def _make_workbook(section='all'):
    wb, output = base._book()

    if section == 'all':
        _add_overview_sheet(wb)
    if section in ('all', 'students'):
        base._add_sheet(wb, 'Alumnos', 'EXPEDIENTE GENERAL DE ALUMNOS', ['No.', 'Alumno', 'Estado', 'Tutor', 'Teléfono', 'Peso kg', 'Estatura cm', 'Playera/Blusa', 'Pantalón/Falda', 'Suéter/Chamarra', 'Calzado', 'Observaciones'], base._students_rows(), [6, 28, 10, 24, 14, 10, 11, 13, 13, 15, 10, 32])
    if section in ('all', 'diagnostic'):
        base._add_sheet(wb, 'Diagnóstico', 'DIAGNÓSTICO DEL GRUPO', ['No.', 'Alumno', 'Calificación', 'Ritmo', 'Estilo de aprendizaje', 'Canal de percepción', 'Nivel', 'Fortalezas', 'Necesidades de apoyo', 'Observaciones'], base._diagnostic_rows(), [6, 28, 11, 14, 18, 20, 16, 30, 30, 30])
    if section in ('all', 'activities'):
        base._add_sheet(wb, 'Actividades', 'REGISTRO DE ACTIVIDADES', ['Fecha', 'Actividad', 'Asignatura', 'Trimestre', 'Puntaje máximo'], base._activities_rows(), [12, 35, 24, 22, 14], False)
    if section in ('all', 'grades'):
        _add_grade_analysis_sheet(wb)
    if section in ('all', 'attendance'):
        base._add_attendance_sheet(wb)
    if section in ('all', 'incidents'):
        base._add_sheet(wb, 'Convivencia', 'REGISTRO DE CONVIVENCIA E INCIDENCIAS', ['Fecha', 'Alumno', 'Categoría', 'Descripción', 'Acciones / acuerdos', 'Estado'], base._incident_rows(), [12, 28, 18, 40, 40, 14])
    if section in ('all', 'rubrics'):
        base._add_sheet(wb, 'Rúbricas', 'RESULTADOS DE RÚBRICAS', ['Actividad', 'Rúbrica', 'Alumno', 'Porcentaje', 'Calificación', 'Retroalimentación', 'Asistida por IA'], base._rubric_rows(), [28, 30, 28, 12, 12, 45, 14])

    wb.close()
    output.seek(0)
    return output


def install():
    base._make_workbook = _make_workbook
