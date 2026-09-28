"""Reportes académicos por grupo: trimestre y diagnóstico por asignatura."""
import io
from collections import defaultdict
from html import escape

import xlsxwriter
from flask import request, session, redirect, send_file

import app as core
import diagnostic


TRIMESTERS = list(core.TRIMS)


def _students():
    return core.Student.query.filter_by(status='ACTIVO').order_by(
        core.Student.list_no, core.Student.paternal, core.Student.maternal, core.Student.names
    ).all()


def _context():
    try:
        import group_workspaces
        return group_workspaces.active_group_label()
    except Exception:
        c = core.cfg()
        return f'{c.grade} {c.group}'


def _subject_averages(trimester):
    students = _students()
    subjects = core.Subject.query.order_by(core.Subject.name).all()
    activities = core.Activity.query.filter_by(trimester=trimester).all()
    # La actividad puede valer distinto puntaje: normalizar cada resultado a escala 0-10.
    activity_map = defaultdict(list)
    for activity in activities:
        if activity.max_score and activity.max_score > 0:
            activity_map[activity.subject_id].append(activity)
    ids = [a.id for a in activities if a.max_score and a.max_score > 0]
    grades = core.Grade.query.filter(core.Grade.activity_id.in_(ids)).all() if ids else []
    grade_map = {(g.student_id, g.activity_id): g for g in grades}
    values = {}
    for s in students:
        for subject in subjects:
            earned = []
            for activity in activity_map[subject.id]:
                g = grade_map.get((s.id, activity.id))
                if g is not None and g.score is not None:
                    earned.append(max(0, min(10, 10 * g.score / activity.max_score)))
            values[(s.id, subject.id)] = round(sum(earned) / len(earned), 2) if earned else None
    return students, subjects, activity_map, values


def _formats(wb):
    return {
        'title': wb.add_format({'bold': True, 'font_size': 15, 'font_color': '#7B1024', 'align': 'center'}),
        'meta': wb.add_format({'bold': True, 'font_size': 10, 'align': 'center'}),
        'head': wb.add_format({'bold': True, 'bg_color': '#7B1024', 'font_color': 'white', 'border': 1, 'text_wrap': True, 'valign': 'vcenter'}),
        'name': wb.add_format({'border': 1, 'font_size': 9}),
        'num': wb.add_format({'border': 1, 'font_size': 9, 'align': 'center'}),
        'score': wb.add_format({'border': 1, 'num_format': '0.00', 'align': 'center'}),
        'summary': wb.add_format({'bold': True, 'bg_color': '#F9EEDB', 'border': 1, 'num_format': '0.00', 'align': 'center'}),
        'note': wb.add_format({'italic': True, 'font_color': '#666666', 'text_wrap': True}),
    }


def _workbook(title, subtitle, students, subjects, values, key_fn, notes):
    out = io.BytesIO()
    wb = xlsxwriter.Workbook(out, {'in_memory': True})
    ws = wb.add_worksheet('CONCENTRADO')
    f = _formats(wb)
    last_col = len(subjects) + 2
    ws.merge_range(0, 0, 0, last_col, 'TELESECUNDARIA BENITO JUÁREZ', f['title'])
    ws.merge_range(1, 0, 1, last_col, title, f['meta'])
    ws.merge_range(2, 0, 2, last_col, f'GRUPO: {_context()} · CICLO: {core.cfg().cycle} · {subtitle}', f['meta'])
    ws.set_row(4, 35)
    ws.write(4, 0, 'N/P', f['head'])
    ws.write(4, 1, 'ALUMNO', f['head'])
    for j, subject in enumerate(subjects, 2):
        ws.write(4, j, subject.name if hasattr(subject, 'name') else subject, f['head'])
    ws.write(4, last_col, 'PROMEDIO', f['head'])
    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 34)
    ws.set_column(2, last_col, 15)
    for i, student in enumerate(students, 5):
        ws.write(i, 0, student.list_no if student.list_no is not None else i - 4, f['num'])
        ws.write(i, 1, student.full_name, f['name'])
        for j, subject in enumerate(subjects, 2):
            value = values.get(key_fn(student, subject))
            if value is None:
                ws.write_blank(i, j, None, f['num'])
            else:
                ws.write_number(i, j, value, f['score'])
        # Promedio sólo de asignaturas con evidencia.
        start = xlsxwriter.utility.xl_col_to_name(2)
        end = xlsxwriter.utility.xl_col_to_name(last_col - 1)
        ws.write_formula(i, last_col, f'=IF(COUNT({start}{i+1}:{end}{i+1})=0,"",AVERAGE({start}{i+1}:{end}{i+1}))', f['summary'])
    row = 5 + len(students)
    ws.write(row, 1, 'PROMEDIO DEL GRUPO', f['head'])
    for j in range(2, last_col + 1):
        col = xlsxwriter.utility.xl_col_to_name(j)
        ws.write_formula(row, j, f'=IF(COUNT({col}6:{col}{row})=0,"",AVERAGE({col}6:{col}{row}))', f['summary'])
    ws.merge_range(row + 2, 0, row + 3, last_col, notes, f['note'])
    ws.freeze_panes(5, 2)
    ws.autofilter(4, 0, row - 1 if students else 4, last_col)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.repeat_rows(0, 4)
    ws.print_area(0, 0, row + 3, last_col)
    wb.close()
    out.seek(0)
    return out


def _diagnostic_data():
    students = _students()
    subjects = diagnostic._subjects_for_active_grade()
    key = diagnostic._active_grade_key()
    rows = diagnostic.DiagnosticSubjectGrade.query.filter_by(grade_level=key).all()
    student_ids = {s.id for s in students}
    values = {(r.student_id, r.subject_name): r.score for r in rows if r.student_id in student_ids}
    return students, subjects, values


def _diagnostic_workbook():
    students, subjects, values = _diagnostic_data()
    out = io.BytesIO()
    wb = xlsxwriter.Workbook(out, {'in_memory': True})
    ws = wb.add_worksheet('DIAGNÓSTICO')
    f = _formats(wb)
    last_col = len(subjects) + 2
    ws.merge_range(0, 0, 0, last_col, 'TELESECUNDARIA BENITO JUÁREZ', f['title'])
    ws.merge_range(1, 0, 1, last_col, 'DIAGNÓSTICO POR ASIGNATURA', f['meta'])
    ws.merge_range(2, 0, 2, last_col, f'GRUPO: {_context()} · CICLO: {core.cfg().cycle}', f['meta'])
    ws.write(4, 0, 'N/P', f['head'])
    ws.write(4, 1, 'ALUMNO', f['head'])
    for j, name in enumerate(subjects, 2):
        ws.write(4, j, name, f['head'])
    ws.write(4, last_col, 'PROMEDIO', f['head'])
    ws.set_row(4, 38)
    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 34)
    ws.set_column(2, last_col, 16)
    for i, s in enumerate(students, 5):
        ws.write(i, 0, s.list_no if s.list_no is not None else i - 4, f['num'])
        ws.write(i, 1, s.full_name, f['name'])
        for j, name in enumerate(subjects, 2):
            value = values.get((s.id, name))
            if value is None:
                ws.write_blank(i, j, None, f['num'])
            else:
                ws.write_number(i, j, value, f['score'])
        start = xlsxwriter.utility.xl_col_to_name(2)
        end = xlsxwriter.utility.xl_col_to_name(last_col - 1)
        ws.write_formula(i, last_col, f'=IF(COUNT({start}{i+1}:{end}{i+1})=0,"",AVERAGE({start}{i+1}:{end}{i+1}))', f['summary'])
    summary = 5 + len(students)
    ws.write(summary, 1, 'PROMEDIO DEL GRUPO', f['head'])
    for j in range(2, last_col + 1):
        col = xlsxwriter.utility.xl_col_to_name(j)
        ws.write_formula(summary, j, f'=IF(COUNT({col}6:{col}{summary})=0,"",AVERAGE({col}6:{col}{summary}))', f['summary'])
    ws.merge_range(summary + 2, 0, summary + 2, last_col, 'Celdas vacías: asignatura sin evaluación registrada. Los promedios excluyen datos faltantes.', f['note'])
    chart_ws = wb.add_worksheet('GRÁFICA POR ASIGNATURA')
    chart_ws.write(0, 0, 'ASIGNATURA', f['head'])
    chart_ws.write(0, 1, 'PROMEDIO', f['head'])
    for i, name in enumerate(subjects, 1):
        chart_ws.write(i, 0, name)
        col = xlsxwriter.utility.xl_col_to_name(i + 1)
        chart_ws.write_formula(i, 1, f"=IF(COUNT('DIAGNÓSTICO'!{col}6:{col}{summary})=0,NA(),AVERAGE('DIAGNÓSTICO'!{col}6:{col}{summary}))", f['score'])
    chart_ws.set_column(0, 0, 30)
    chart_ws.set_column(1, 1, 15)
    chart = wb.add_chart({'type': 'column'})
    chart.add_series({'name': 'Promedio por asignatura', 'categories': ['GRÁFICA POR ASIGNATURA', 1, 0, len(subjects), 0], 'values': ['GRÁFICA POR ASIGNATURA', 1, 1, len(subjects), 1], 'fill': {'color': '#7B1024'}, 'border': {'none': True}})
    chart.set_title({'name': 'Diagnóstico · promedio por asignatura'})
    chart.set_y_axis({'min': 0, 'max': 10, 'name': 'Calificación'})
    chart.set_legend({'none': True})
    chart.set_size({'width': 880, 'height': 440})
    chart_ws.insert_chart('D2', chart)
    ws.freeze_panes(5, 2)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    wb.close()
    out.seek(0)
    return out


def install(app):
    @app.route('/quarterly-grades')
    def quarterly_grades():
        if not session.get('uid'):
            return redirect('/login')
        trimester = request.args.get('trimester', TRIMESTERS[0])
        if trimester not in TRIMESTERS:
            trimester = TRIMESTERS[0]
        students, subjects, activity_map, values = _subject_averages(trimester)
        options = ''.join(f'<option value="{escape(t)}" {"selected" if t == trimester else ""}>{escape(t.title())}</option>' for t in TRIMESTERS)
        headers = ''.join(f'<th>{escape(s.name)}<br><small>{len(activity_map[s.id])} actividades</small></th>' for s in subjects)
        rows = ''
        for s in students:
            scores = [values.get((s.id, sub.id)) for sub in subjects]
            available = [v for v in scores if v is not None]
            avg = round(sum(available) / len(available), 2) if available else None
            cells = ''.join(f'<td>{"—" if v is None else f"{v:.2f}"}</td>' for v in scores)
            rows += f'<tr><td>{escape(str(s.list_no or ""))}</td><td>{escape(s.full_name)}</td>{cells}<td><b>{"—" if avg is None else f"{avg:.2f}"}</b></td></tr>'
        summary = ''.join(f'<td>{"—" if not (v := [values[(s.id, sub.id)] for s in students if values.get((s.id, sub.id)) is not None]) else f"{sum(v)/len(v):.2f}"}</td>' for sub in subjects)
        body = f'''<h1>Calificaciones trimestrales · {escape(_context())}</h1>
        <div class="card"><form method="get" style="display:flex;align-items:end;gap:12px;flex-wrap:wrap"><label>Trimestre<select name="trimester">{options}</select></label><button style="width:auto">Consultar</button><a href="/quarterly-grades.xlsx?trimester={escape(trimester)}" style="padding:11px 15px;background:#217346;color:white;border-radius:9px;text-decoration:none;font-weight:bold">Exportar Excel</a></form>
        <p class="muted">Cada actividad o examen registrado se normaliza a 0–10; el promedio por asignatura es la media de sus actividades calificadas. El promedio general es la media de las asignaturas con evidencia. No se imputan ceros por registros faltantes.</p></div>
        <div class="card scroll"><table><tr><th>N/P</th><th>Alumno</th>{headers}<th>Promedio</th></tr>{rows}<tr><th></th><th>Promedio del grupo</th>{summary}<th></th></tr></table></div>'''
        return core.page('Calificaciones trimestrales', body)

    @app.route('/quarterly-grades.xlsx')
    def quarterly_grades_excel():
        if not session.get('uid'):
            return redirect('/login')
        trimester = request.args.get('trimester', TRIMESTERS[0])
        if trimester not in TRIMESTERS:
            trimester = TRIMESTERS[0]
        students, subjects, _, values = _subject_averages(trimester)
        out = _workbook('CONCENTRADO DE CALIFICACIONES TRIMESTRALES', trimester, students, subjects, values, lambda s, sub: (s.id, sub.id), 'Cada actividad y examen se convierte a escala 0–10. Promedio por asignatura: media simple de actividades calificadas. Sin registro no equivale a cero.')
        return send_file(out, as_attachment=True, download_name=f'Calificaciones_{_context().replace(" ", "")}_{trimester.replace(" ", "_")}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.route('/diagnostic/subjects.xlsx')
    def diagnostic_subjects_excel():
        if not session.get('uid'):
            return redirect('/login')
        return send_file(_diagnostic_workbook(), as_attachment=True, download_name=f'Diagnostico_por_asignatura_{_context().replace(" ", "")}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.after_request
    def academic_report_links(response):
        if not session.get('uid') or 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        html = response.get_data(as_text=True)
        if request.path == '/diagnostic' and '/diagnostic/subjects.xlsx' not in html:
            students, subjects, values = _diagnostic_data()
            bars = ''
            for name in subjects:
                nums = [values[(s.id, name)] for s in students if values.get((s.id, name)) is not None]
                avg = sum(nums) / len(nums) if nums else None
                width = 0 if avg is None else round(avg * 10, 1)
                bars += f'<div style="margin:10px 0"><div style="display:flex;justify-content:space-between;gap:12px"><b>{escape(name)}</b><span>{"Sin datos" if avg is None else f"{avg:.2f}"}</span></div><div style="height:15px;border-radius:9px;background:#eee;overflow:hidden"><div style="height:100%;width:{width}%;background:#7b1024"></div></div></div>'
            panel = f'<div class="card"><h2>Gráfica diagnóstica por asignatura</h2><p class="muted">Promedio del grupo (0–10), calculado únicamente con las calificaciones capturadas.</p>{bars}<a href="/diagnostic/subjects.xlsx" style="display:inline-block;padding:11px 15px;background:#217346;color:white;text-decoration:none;border-radius:9px;font-weight:bold">Exportar diagnóstico por asignatura y gráfica a Excel</a></div>'
            html = html.replace('</main>', panel + '</main>', 1)
        if request.path == '/' and '/quarterly-grades' not in html:
            panel = '<div class="card"><h2>Calificaciones trimestrales</h2><p>Promedios automáticos de actividades y exámenes por asignatura y grupo.</p><a href="/quarterly-grades" style="display:inline-block;padding:11px 15px;background:#7b1024;color:white;text-decoration:none;border-radius:9px;font-weight:bold">Abrir calificaciones trimestrales</a></div>'
            html = html.replace('</main>', panel + '</main>', 1)
        if 'href="/quarterly-grades"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/quarterly-grades"><span class="nav-icon">📊</span><span>Calificaciones trimestrales</span></a>'
            if marker in html:
                html = html.replace(marker, link + marker, 1)
        if html != response.get_data(as_text=True):
            response.set_data(html)
            response.headers['Content-Length'] = str(len(response.get_data()))
        return response
