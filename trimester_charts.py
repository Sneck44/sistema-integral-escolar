from io import BytesIO
from html import escape
from collections import defaultdict
from flask import request, session, redirect, send_file

import xlsxwriter
import app as core

TRIMS = ['PRIMER TRIMESTRE', 'SEGUNDO TRIMESTRE', 'TERCER TRIMESTRE']
RISK_THRESHOLD = 6.0


def _student_progress_data(students):
    """Promedio trimestral por alumno sin convertir ausencias de captura en cero.

    Primero promedia las actividades de cada asignatura y después obtiene la
    media de las asignaturas con evidencia. Así una asignatura con más
    actividades no pesa más que las demás.
    """
    student_ids = {student.id for student in students}
    activities = [
        activity for activity in core.Activity.query.all()
        if activity.trimester in TRIMS and activity.max_score and activity.max_score > 0
    ]
    activity_map = {activity.id: activity for activity in activities}
    activity_ids = list(activity_map)
    grades = []
    if activity_ids and student_ids:
        grades = core.Grade.query.filter(
            core.Grade.activity_id.in_(activity_ids),
            core.Grade.student_id.in_(student_ids),
            core.Grade.score.isnot(None),
        ).all()

    subject_scores = defaultdict(list)
    for grade in grades:
        activity = activity_map.get(grade.activity_id)
        if not activity:
            continue
        normalized = max(0, min(10, (grade.score / activity.max_score) * 10))
        subject_scores[(grade.student_id, activity.trimester, activity.subject_id)].append(normalized)

    progress = {}
    for student in students:
        averages = []
        for trimester in TRIMS:
            subject_avgs = []
            for (student_id, trim, _subject_id), scores in subject_scores.items():
                if student_id == student.id and trim == trimester and scores:
                    subject_avgs.append(sum(scores) / len(scores))
            averages.append(round(sum(subject_avgs) / len(subject_avgs), 2) if subject_avgs else None)
        current = next((value for value in reversed(averages) if value is not None), None)
        progress[student.id] = {
            'averages': averages,
            'current': current,
            'at_risk': current is not None and current < RISK_THRESHOLD,
        }
    return progress


def _student_progress_card(student, progress):
    averages = progress['averages']
    current = progress['current']
    at_risk = progress['at_risk']
    if current is None:
        status_class, status_label = 'no-data', 'Sin calificaciones'
    elif at_risk:
        status_class, status_label = 'risk', 'Riesgo de reprobación'
    elif current < 8:
        status_class, status_label = 'followup', 'En seguimiento'
    else:
        status_class, status_label = 'ok', 'Desempeño suficiente'

    bars = ''
    spoken = []
    for index, avg in enumerate(averages, start=1):
        if avg is None:
            bar_class = 'is-empty'
            value = '—'
            score = 0
            spoken.append(f'Trimestre {index}: sin datos')
        else:
            bar_class = 'is-risk' if avg < RISK_THRESHOLD else 'is-safe'
            value = f'{avg:.2f}'
            score = avg
            spoken.append(f'Trimestre {index}: {value}')
        bars += f'''<div class="progress-column">
          <div class="progress-bar {bar_class}" style="--score:{score:.2f}"><strong>{value}</strong></div>
          <span>T{index}</span>
        </div>'''

    card_class = ' is-risk' if at_risk else ''
    current_label = f'{current:.2f}' if current is not None else '—'
    return f'''<article class="student-progress-card{card_class}" id="student-{student.id}">
      <header><div><small>No. {escape(str(student.list_no or '—'))}</small><h3>{escape(student.full_name)}</h3></div><span class="progress-state {status_class}">{status_label}</span></header>
      <div class="progress-plot" role="img" aria-label="{escape('. '.join(spoken))}">
        <div class="risk-threshold"><span>6.0</span></div>
        <div class="progress-bars">{bars}</div>
      </div>
      <footer><span>Último promedio registrado</span><b class="{'risk-number' if at_risk else ''}">{current_label}</b><a href="/suite/student/{student.id}">Abrir expediente</a></footer>
    </article>'''


def _trimester_data(trimester):
    activities = core.Activity.query.filter_by(trimester=trimester).order_by(core.Activity.activity_date).all()
    subjects = {}
    subject_scores = defaultdict(list)
    student_scores = defaultdict(list)

    for a in activities:
        if a.subject:
            subjects[a.subject_id] = a.subject.name
        grades = core.Grade.query.filter_by(activity_id=a.id).all()
        for g in grades:
            if g.score is None or not a.max_score:
                continue
            normalized = max(0, min(10, (g.score / a.max_score) * 10))
            subject_scores[a.subject_id].append(normalized)
            student_scores[g.student_id].append(normalized)

    subject_avgs = []
    for sid, name in sorted(subjects.items(), key=lambda x: x[1].lower()):
        vals = subject_scores.get(sid, [])
        avg = round(sum(vals) / len(vals), 2) if vals else None
        subject_avgs.append((name, avg))

    bands = {'Destacado (9–10)': 0, 'Esperado (8–8.9)': 0, 'En desarrollo (6–7.9)': 0, 'Requiere apoyo (<6)': 0}
    student_avgs = []
    for s in core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all():
        vals = student_scores.get(s.id, [])
        avg = round(sum(vals) / len(vals), 2) if vals else None
        student_avgs.append((s, avg))
        if avg is None:
            continue
        if avg >= 9:
            bands['Destacado (9–10)'] += 1
        elif avg >= 8:
            bands['Esperado (8–8.9)'] += 1
        elif avg >= 6:
            bands['En desarrollo (6–7.9)'] += 1
        else:
            bands['Requiere apoyo (<6)'] += 1

    all_vals = [v for vals in student_scores.values() for v in vals]
    group_avg = round(sum(all_vals) / len(all_vals), 2) if all_vals else None
    return {
        'activities': activities,
        'subject_avgs': subject_avgs,
        'bands': bands,
        'student_avgs': student_avgs,
        'group_avg': group_avg,
    }


def _bar_rows(subject_avgs):
    html = ''
    for name, avg in subject_avgs:
        val = avg if avg is not None else 0
        width = max(0, min(100, val * 10))
        label = f'{avg:.2f}' if avg is not None else '—'
        html += f'''<div class="tri-bar-row"><div class="tri-bar-label">{escape(name)}</div><div class="tri-bar-track"><div class="tri-bar-fill" style="width:{width}%"></div></div><div class="tri-bar-value">{label}</div></div>'''
    return html or '<p class="muted">Aún no hay calificaciones registradas para este trimestre.</p>'


def _band_rows(bands):
    total = sum(bands.values())
    html = ''
    for label, count in bands.items():
        pct = round(count * 100 / total, 1) if total else 0
        html += f'''<div class="tri-band"><div><b>{escape(label)}</b><small>{count} alumno(s)</small></div><div class="tri-band-track"><span style="width:{pct}%"></span></div><strong>{pct}%</strong></div>'''
    return html


def _export_workbook():
    output = BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})

    title_fmt = wb.add_format({'bold': True, 'font_size': 15, 'font_color': '#7B1024', 'align': 'center'})
    meta_fmt = wb.add_format({'bold': True, 'font_size': 9, 'align': 'center'})
    head_fmt = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#7B1024', 'border': 1, 'align': 'center'})
    cell_fmt = wb.add_format({'border': 1, 'font_size': 9})
    num_fmt = wb.add_format({'border': 1, 'font_size': 9, 'num_format': '0.00', 'align': 'center'})
    sig_fmt = wb.add_format({'bold': True, 'font_size': 9, 'align': 'center'})
    small_fmt = wb.add_format({'font_size': 8, 'align': 'center'})

    cfg = core.cfg()
    for idx, trimester in enumerate(TRIMS, start=1):
        data = _trimester_data(trimester)
        ws = wb.add_worksheet(f'Trimestre {idx}')
        ws.set_paper(1)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.set_margins(0.3, 0.3, 0.35, 0.35)
        ws.hide_gridlines(2)
        ws.set_column('A:A', 3)
        ws.set_column('B:B', 30)
        ws.set_column('C:C', 14)
        ws.set_column('E:E', 26)
        ws.set_column('F:F', 12)

        ws.merge_range('A1:H1', 'TELESECUNDARIA FEDERAL “BENITO JUÁREZ” · C.C.T. 21DTV0109Z', meta_fmt)
        ws.merge_range('A2:H2', f'CICLO ESCOLAR {cfg.cycle} · GRADO {cfg.grade} · GRUPO {cfg.group}', meta_fmt)
        ws.merge_range('A4:H4', f'GRÁFICAS Y ANÁLISIS · {trimester}', title_fmt)
        ws.merge_range('A5:H5', f'Promedio general del trimestre: {data["group_avg"] if data["group_avg"] is not None else "—"}', small_fmt)

        ws.write('B7', 'Asignatura', head_fmt)
        ws.write('C7', 'Promedio', head_fmt)
        row = 7
        for name, avg in data['subject_avgs']:
            ws.write(row, 1, name, cell_fmt)
            if avg is None:
                ws.write(row, 2, '', cell_fmt)
            else:
                ws.write_number(row, 2, avg, num_fmt)
            row += 1
        if row == 7:
            ws.write(row, 1, 'Sin datos', cell_fmt)
            ws.write(row, 2, '', cell_fmt)
            row += 1

        chart1 = wb.add_chart({'type': 'column'})
        chart1.add_series({
            'name': 'Promedio por asignatura',
            'categories': [ws.name, 7, 1, row - 1, 1],
            'values': [ws.name, 7, 2, row - 1, 2],
            'fill': {'color': '#7B1024'},
            'border': {'none': True},
        })
        chart1.set_title({'name': 'Promedio por asignatura'})
        chart1.set_y_axis({'min': 0, 'max': 10, 'major_unit': 1})
        chart1.set_legend({'none': True})
        chart1.set_style(10)
        ws.insert_chart('E7', chart1, {'x_scale': 1.15, 'y_scale': 1.05})

        band_start = max(row + 3, 22)
        ws.write(band_start, 1, 'Nivel de desempeño', head_fmt)
        ws.write(band_start, 2, 'Alumnos', head_fmt)
        r = band_start + 1
        for label, count in data['bands'].items():
            ws.write(r, 1, label, cell_fmt)
            ws.write_number(r, 2, count, cell_fmt)
            r += 1

        chart2 = wb.add_chart({'type': 'pie'})
        chart2.add_series({
            'name': 'Distribución de desempeño',
            'categories': [ws.name, band_start + 1, 1, r - 1, 1],
            'values': [ws.name, band_start + 1, 2, r - 1, 2],
            'data_labels': {'percentage': True, 'category': True, 'leader_lines': True},
        })
        chart2.set_title({'name': 'Distribución del desempeño'})
        chart2.set_style(10)
        ws.insert_chart(band_start, 4, chart2, {'x_scale': 1.12, 'y_scale': 1.0})

        sig_row = max(r + 3, band_start + 18)
        ws.merge_range(sig_row, 0, sig_row, 2, '__________________________________', sig_fmt)
        ws.merge_range(sig_row + 1, 0, sig_row + 1, 2, 'NOMBRE Y FIRMA DEL DOCENTE', sig_fmt)
        ws.merge_range(sig_row, 5, sig_row, 7, '__________________________________', sig_fmt)
        ws.merge_range(sig_row + 1, 5, sig_row + 1, 7, 'Vo. Bo. DIRECTORA', sig_fmt)
        ws.merge_range(sig_row + 2, 5, sig_row + 2, 7, 'MTRA. NELLY AZUCENA HERNÁNDEZ PICAZO', sig_fmt)
        ws.print_area(0, 0, sig_row + 2, 7)

    wb.close()
    output.seek(0)
    return output


def install(app):
    @app.route('/trimester-charts')
    def trimester_charts():
        if not session.get('uid'):
            return redirect('/login')

        students = core.Student.query.filter_by(status='ACTIVO').order_by(
            core.Student.list_no, core.Student.paternal, core.Student.maternal, core.Student.names
        ).all()
        progress = _student_progress_data(students)
        selected_id = request.args.get('student', type=int)
        if selected_id not in {student.id for student in students}:
            selected_id = None
        visible_students = [student for student in students if not selected_id or student.id == selected_id]
        student_cards = ''.join(
            _student_progress_card(student, progress[student.id]) for student in visible_students
        ) or '<div class="tri-empty">Aún no hay alumnos activos en este grupo.</div>'
        risk_count = sum(1 for item in progress.values() if item['at_risk'])
        student_options = '<option value="">Todos los alumnos</option>' + ''.join(
            f'<option value="{student.id}" {"selected" if selected_id == student.id else ""}>{escape(str(student.list_no or "—"))} · {escape(student.full_name)}</option>'
            for student in students
        )

        sections = ''
        for idx, trimester in enumerate(TRIMS, start=1):
            data = _trimester_data(trimester)
            avg = data['group_avg'] if data['group_avg'] is not None else '—'
            sections += f'''
            <section class="tri-card" id="t{idx}">
              <div class="tri-head"><div><span class="tri-chip">Trimestre {idx}</span><h2>{escape(trimester.title())}</h2></div><div class="tri-kpi"><small>Promedio general</small><b>{avg}</b></div></div>
              <div class="tri-grid">
                <div class="tri-chart-box"><h3>Promedio por asignatura</h3>{_bar_rows(data['subject_avgs'])}</div>
                <div class="tri-chart-box"><h3>Distribución del desempeño</h3>{_band_rows(data['bands'])}</div>
              </div>
            </section>'''

        body = f'''
        <div class="page-head"><h1>Gráficas por trimestre</h1><p>Consulta el avance del grupo y la evolución individual de cada estudiante.</p></div>
        <div class="tri-actions"><a class="tri-primary" href="/trimester-charts.xlsx">📊 Exportar gráficas a Excel</a></div>
        <section class="individual-progress">
          <div class="individual-head">
            <div><span class="tri-chip">Seguimiento individual</span><h2>Promedio de cada alumno por trimestre</h2><p>Las barras rojas indican un promedio menor a 6.0. Los trimestres sin captura aparecen con “—” y no se convierten en cero.</p></div>
            <div class="risk-summary"><small>Riesgo actual</small><b>{risk_count}</b><span>de {len(students)} alumno(s)</span></div>
          </div>
          <form class="student-filter" method="get" action="/trimester-charts">
            <label>Buscar alumno<select name="student" onchange="this.form.submit()">{student_options}</select></label>
            {'<a href="/trimester-charts">Ver todo el grupo</a>' if selected_id else ''}
          </form>
          <div class="student-progress-grid">{student_cards}</div>
        </section>
        {sections}
        <style>
        .tri-actions{{display:flex;justify-content:flex-end;margin:0 0 16px}}.tri-primary{{text-decoration:none;background:#7b1024;color:#fff;padding:12px 18px;border-radius:999px;font-weight:800;box-shadow:0 8px 20px rgba(123,16,36,.18);transition:.2s}}.tri-primary:hover{{transform:translateY(-2px);box-shadow:0 12px 26px rgba(123,16,36,.24)}}
        .individual-progress{{background:#fff;border:1px solid #eee8e6;border-radius:24px;padding:22px;margin-bottom:22px;box-shadow:0 10px 28px rgba(74,18,32,.07)}}.individual-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:16px}}.individual-head h2{{margin:8px 0 4px;color:#4e0917}}.individual-head p{{margin:0;color:#746a6d;max-width:760px;font-size:13px;line-height:1.5}}.risk-summary{{flex:0 0 auto;min-width:150px;padding:13px 16px;border:1px solid #f0c3c9;border-radius:18px;background:#fff7f8;text-align:center}}.risk-summary small,.risk-summary span{{display:block;color:#876b70;font-size:11px}}.risk-summary b{{display:block;color:#b42338;font-size:30px;line-height:1.1;margin:3px 0}}
        .student-filter{{display:flex;align-items:flex-end;gap:10px;margin:0 0 18px;padding:13px;border-radius:16px;background:#faf7f5;border:1px solid #eee5e2}}.student-filter label{{min-width:min(100%,360px)}}.student-filter select{{margin-top:5px}}.student-filter a{{display:inline-flex;align-items:center;min-height:40px;padding:9px 13px;border-radius:10px;background:#7b1024;color:#fff;text-decoration:none;font-size:12px;font-weight:800}}
        .student-progress-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px}}.student-progress-card{{min-width:0;border:1px solid #eadfe1;border-radius:19px;padding:15px;background:linear-gradient(180deg,#fff,#fdfbfa);box-shadow:0 7px 20px rgba(74,18,32,.05);scroll-margin-top:90px}}.student-progress-card.is-risk{{border-color:#dc6d7c;box-shadow:0 8px 24px rgba(180,35,56,.13)}}.student-progress-card header{{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;min-height:55px}}.student-progress-card header small{{color:#8a7d81;font-size:10px;font-weight:800}}.student-progress-card h3{{margin:3px 0 0;font-size:14px;line-height:1.25;color:#332a2d}}.progress-state{{flex:0 0 auto;display:inline-flex;padding:5px 8px;border-radius:999px;font-size:9px;font-weight:900;text-transform:uppercase;letter-spacing:.25px}}.progress-state.risk{{background:#fde1e5;color:#a51e33}}.progress-state.followup{{background:#fff1c9;color:#765610}}.progress-state.ok{{background:#e6f4ea;color:#24643a}}.progress-state.no-data{{background:#ece9ea;color:#6e6467}}
        .progress-plot{{position:relative;height:165px;margin:14px 4px 35px 30px;border-left:1px solid #d8ced1;border-bottom:1px solid #d8ced1;background:repeating-linear-gradient(to top,transparent 0,transparent calc(20% - 1px),#eee8e9 calc(20% - 1px),#eee8e9 20%)}}.risk-threshold{{position:absolute;z-index:1;left:0;right:0;bottom:60%;border-top:2px dashed rgba(190,42,61,.58)}}.risk-threshold span{{position:absolute;right:4px;top:-18px;color:#aa2639;font-size:9px;font-weight:900;background:#fff;padding:1px 4px;border-radius:5px}}.progress-bars{{position:absolute;z-index:2;inset:0;display:grid;grid-template-columns:repeat(3,1fr);gap:14px;padding:0 16px}}.progress-column{{position:relative;height:100%;display:flex;align-items:flex-end;justify-content:center}}.progress-column>span{{position:absolute;bottom:-27px;font-size:10px;color:#756a6e;font-weight:850}}.progress-bar{{position:relative;width:min(46px,72%);height:max(5px,calc(var(--score) * 10%));border-radius:9px 9px 3px 3px;background:linear-gradient(180deg,#8d1c34,#631124);box-shadow:0 5px 12px rgba(91,15,34,.16);transition:.2s}}.progress-bar.is-risk{{background:linear-gradient(180deg,#dc5264,#b42338);box-shadow:0 6px 14px rgba(180,35,56,.24)}}.progress-bar.is-empty{{height:4px;background:#d9d2d4;box-shadow:none}}.progress-bar strong{{position:absolute;top:-22px;left:50%;transform:translateX(-50%);font-size:10px;color:#50464a;white-space:nowrap}}.student-progress-card footer{{display:grid;grid-template-columns:1fr auto;gap:4px 10px;align-items:center;padding-top:11px;border-top:1px solid #eee8e9}}.student-progress-card footer span{{font-size:10px;color:#796e72}}.student-progress-card footer b{{font-size:18px;color:#6d1022}}.student-progress-card footer b.risk-number{{color:#b42338}}.student-progress-card footer a{{grid-column:1/-1;margin-top:6px;color:#7b1024;font-size:11px;font-weight:850;text-decoration:none}}
        .tri-card{{background:#fff;border:1px solid #eee8e6;border-radius:24px;padding:22px;margin-bottom:18px;box-shadow:0 10px 28px rgba(74,18,32,.07)}}.tri-head{{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}}.tri-chip{{display:inline-block;padding:7px 11px;border-radius:999px;background:#f3e7ea;color:#7b1024;font-size:12px;font-weight:800}}.tri-head h2{{margin:8px 0 0;font-size:20px;color:#4e0917}}.tri-kpi{{text-align:right;background:#faf6f7;border-radius:18px;padding:12px 16px;min-width:140px}}.tri-kpi small{{display:block;color:#746a6d}}.tri-kpi b{{display:block;font-size:30px;color:#7b1024}}
        .tri-grid{{display:grid;grid-template-columns:1.25fr .9fr;gap:18px}}.tri-chart-box{{background:#fcfaf9;border:1px solid #f0e9e7;border-radius:20px;padding:18px}}.tri-chart-box h3{{margin:0 0 16px;font-size:15px}}.tri-bar-row{{display:grid;grid-template-columns:180px 1fr 54px;gap:10px;align-items:center;margin:11px 0}}.tri-bar-label{{font-size:12px;font-weight:700}}.tri-bar-track,.tri-band-track{{height:12px;border-radius:999px;background:#ece5e3;overflow:hidden}}.tri-bar-fill,.tri-band-track span{{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#7b1024,#caa45f)}}.tri-bar-value{{text-align:right;font-weight:800;color:#7b1024}}.tri-band{{display:grid;grid-template-columns:minmax(170px,1fr) 1.2fr 58px;gap:12px;align-items:center;padding:9px 0}}.tri-band b{{font-size:12px;display:block}}.tri-band small{{color:#746a6d;font-size:11px}}.tri-band strong{{text-align:right;color:#7b1024}}
        .tri-empty{{grid-column:1/-1;padding:24px;text-align:center;border:1px dashed #d9cdd0;border-radius:16px;color:#756a6e}}@media(max-width:900px){{.tri-grid{{grid-template-columns:1fr}}.tri-bar-row{{grid-template-columns:130px 1fr 48px}}}}@media(max-width:620px){{.individual-progress,.tri-card{{padding:15px;border-radius:18px}}.individual-head{{display:block}}.risk-summary{{margin-top:13px}}.student-filter{{display:grid}}.student-filter label{{min-width:0}}.student-progress-grid{{grid-template-columns:1fr}}.student-progress-card header{{display:grid}}.progress-state{{justify-self:start}}.tri-head{{align-items:flex-start}}.tri-kpi{{min-width:105px}}.tri-bar-row{{grid-template-columns:1fr 90px 42px}}.tri-band{{grid-template-columns:1fr}}.tri-band strong{{text-align:left}}}}
        </style>'''
        return core.page('Gráficas por trimestre', body)

    @app.route('/trimester-charts.xlsx')
    def trimester_charts_export():
        if not session.get('uid'):
            return redirect('/login')
        output = _export_workbook()
        return send_file(output, as_attachment=True, download_name='graficas_por_trimestre_2026-2027.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.after_request
    def trimester_charts_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if 'href="/trimester-charts"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/trimester-charts"><span class="nav-icon">📈</span><span>Gráficas trimestrales</span></a>'
            if marker in html:
                html = html.replace(marker, link + marker, 1)
            else:
                marker2 = '<a href="/logout">Salir</a>'
                if marker2 in html:
                    html = html.replace(marker2, '<a href="/trimester-charts">Gráficas trimestrales</a>' + marker2, 1)
        if '<h1>Panel de control</h1>' in html and 'Gráficas por trimestre' not in html:
            card = '''<div class="card"><h2>📈 Gráficas por trimestre</h2><p>Analiza promedios por asignatura y distribución del desempeño de cada trimestre.</p><a href="/trimester-charts" style="display:inline-block;background:#7b1024;color:#fff;text-decoration:none;padding:11px 16px;border-radius:999px;font-weight:800;box-shadow:0 8px 18px rgba(123,16,36,.16)">Ver gráficas</a></div>'''
            html = html.replace('</main>', card + '</main>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
