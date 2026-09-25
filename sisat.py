import io
import json
import random
from datetime import date, datetime
from fractions import Fraction
from html import escape

import xlsxwriter
from flask import request, redirect, session, flash, send_file

import app as core


SKILLS = {
    'lectura': {
        'title': 'Toma de lectura',
        'components': [
            ('fluidez', 'Fluidez', ('La lectura es fluida', 'La lectura es parcialmente fluida', 'No hay fluidez en la lectura')),
            ('precision', 'Precisión', ('Precisión en la lectura', 'Precisión moderada en la lectura', 'Imprecisión en la lectura')),
            ('palabras_complejas', 'Atención a palabras complejas', ('Atención a palabras complejas', 'Atención en algunas palabras complejas', 'Sin atención a palabras complejas')),
            ('voz', 'Uso de la voz al leer', ('Uso adecuado de la voz al leer', 'Uso inconsistente de la voz al leer', 'Manejo inadecuado de la voz al leer')),
            ('seguridad', 'Seguridad y disposición', ('Seguridad y disposición ante la lectura', 'Seguridad limitada y esfuerzo ante la lectura', 'Inseguridad o indiferencia ante la lectura')),
            ('comprension', 'Comprensión general', ('Comprensión general del texto', 'Comprensión parcial del texto', 'Comprensión deficiente del texto')),
        ],
    },
    'escritura': {
        'title': 'Producción de textos escritos',
        'components': [
            ('legibilidad', 'Legibilidad', ('Es legible', 'Es medianamente legible', 'No se puede leer')),
            ('proposito', 'Propósito comunicativo', ('Cumple con el propósito comunicativo', 'Cumple parcialmente con el propósito comunicativo', 'No cumple con el propósito comunicativo')),
            ('concordancia', 'Relación de palabras y oraciones', ('Relaciona adecuadamente palabras y oraciones', 'Relaciona correctamente algunas palabras u oraciones', 'No relaciona palabras u oraciones')),
            ('vocabulario', 'Diversidad de vocabulario', ('Diversidad de vocabulario', 'Uso limitado de vocabulario', 'Vocabulario limitado o no pertinente')),
            ('puntuacion', 'Signos de puntuación', ('Uso de los signos de puntuación', 'Uso de algunos signos de puntuación', 'No utiliza signos de puntuación')),
            ('ortografia', 'Reglas ortográficas', ('Uso correcto de las reglas ortográficas', 'Uso de algunas reglas ortográficas', 'No respeta las reglas ortográficas')),
        ],
    },
    'calculo': {'title': 'Cálculo mental', 'components': []},
}

LEVEL_COLORS = {'NIVEL ESPERADO': '#DFF2E5', 'EN DESARROLLO': '#FFF0C9', 'REQUIERE APOYO': '#FADDDD'}

RUBRIC_GUIDANCE = {
    'lectura': {
        'fluidez': {
            3: 'Lee palabras, frases y oraciones completas con ritmo y claridad; realiza las pausas indicadas por la puntuación.',
            2: 'Lee con ritmo solo algunas oraciones o párrafos y atiende únicamente algunos signos de puntuación.',
            1: 'Lee de manera monótona e imprecisa y hace pausas constantes que no corresponden a la puntuación.',
        },
        'precision': {
            3: 'Lee correctamente palabras conocidas y desconocidas y articula sin dificultad.',
            2: 'Vacila, sustituye u omite palabras; comete hasta 5% de errores o presenta dificultad con sílabas trabadas.',
            1: 'Comete más de 6% de errores, hace falsos inicios o no logra articular palabras con sílabas trabadas.',
        },
        'palabras_complejas': {
            3: 'Lee cuidadosamente palabras complejas o desconocidas, sin titubeos ni sustituciones.',
            2: 'Se detiene y corrige algunas palabras complejas, o las sustituye por otras similares.',
            1: 'Se equivoca y continúa sin corregir, o evita leer palabras complejas o desconocidas.',
        },
        'voz': {
            3: 'Emplea volumen, entonación y dicción adecuados y atiende signos interrogativos y exclamativos.',
            2: 'El volumen y la entonación son adecuados solo en partes; presenta inconsistencias de expresividad o dicción.',
            1: 'La lectura es monótona, con problemas graves de volumen, entonación o dicción.',
        },
        'seguridad': {
            3: 'Muestra actitud positiva, dominio de la práctica lectora y disfrute al leer.',
            2: 'Presenta tensión o dificultad, aunque logra manejar el momento y continuar.',
            1: 'Muestra contrariedad, nerviosismo que interfiere o apatía ante la lectura.',
        },
        'comprension': {
            3: 'Comunica información específica, reconoce ideas principales, personajes y escenarios, y emite una opinión.',
            2: 'Expone datos generales o algunas ideas y tiene dificultad para emitir una opinión.',
            1: 'No recupera información del texto, no relaciona sus elementos o no logra emitir una opinión.',
        },
    },
    'escritura': {
        'legibilidad': {
            3: 'Separa correctamente las palabras; el trazo, tamaño y organización del texto permiten leerlo.',
            2: 'Presenta algunos errores de separación, trazo o distribución que dificultan parcialmente la lectura.',
            1: 'Los errores de separación, trazo, tamaño u organización impiden leer el texto.',
        },
        'proposito': {
            3: 'Expone, describe, narra o argumenta lo solicitado y corresponde al tipo de texto indicado.',
            2: 'Cumple solo parcialmente la intención o las características del tipo de texto solicitado.',
            1: 'No desarrolla la intención solicitada ni corresponde al tipo de texto requerido.',
        },
        'concordancia': {
            3: 'Relaciona enunciados con nexos pertinentes, mantiene concordancia y usa correctamente los tiempos verbales.',
            2: 'Relaciona algunos enunciados, pero usa pocos nexos y presenta errores de concordancia o conjugación.',
            1: 'No relaciona enunciados, carece de nexos y muestra errores evidentes de concordancia y tiempos verbales.',
        },
        'vocabulario': {
            3: 'Usa vocabulario adecuado y variado considerando quién habla, a quién y para qué.',
            2: 'El vocabulario es limitado o repetitivo y pierde parcialmente de vista la situación o al destinatario.',
            1: 'El vocabulario es muy limitado o no corresponde con la situación comunicativa ni el destinatario.',
        },
        'puntuacion': {
            3: 'Usa correctamente la puntuación para construir el significado del texto.',
            2: 'Emplea algunos signos, pero omite otros o comete errores que afectan parcialmente la lectura.',
            1: 'No usa los signos elementales o los emplea de forma que altera el significado.',
        },
        'ortografia': {
            3: 'Aplica acentuación y reglas ortográficas, incluso en palabras con grafías que pueden confundirse.',
            2: 'Presenta algunos errores de acentuación y errores mínimos en palabras de grafía dudosa.',
            1: 'Muestra numerosos errores de acentuación y un descuido general de las reglas ortográficas.',
        },
    },
}


class SisatAssessment(core.db.Model):
    __tablename__ = 'sisat_assessment'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), nullable=False, index=True)
    skill = core.db.Column(core.db.String(20), nullable=False, index=True)
    application_date = core.db.Column(core.db.Date, nullable=False, default=date.today, index=True)
    visit = core.db.Column(core.db.Integer, nullable=False, default=1)
    scores_json = core.db.Column(core.db.Text, default='{}')
    question_set_json = core.db.Column(core.db.Text, default='[]')
    total = core.db.Column(core.db.Integer, default=0)
    level = core.db.Column(core.db.String(30), default='REQUIERE APOYO')
    observations = core.db.Column(core.db.Text, default='')
    applied_by = core.db.Column(core.db.Integer, core.db.ForeignKey('user.id'), nullable=True)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (
        core.db.UniqueConstraint('student_id', 'skill', 'application_date', 'visit', name='uq_sisat_application'),
    )


def _profile():
    try:
        import multi_user
        return multi_user._profile(session.get('uid'))
    except Exception:
        return None


def _can_capture():
    profile = _profile()
    return bool(profile and profile.active and profile.role in ('ADMIN', 'DIRECCION', 'DOCENTE'))


def _can_export():
    profile = _profile()
    return bool(profile and profile.active and profile.role in ('ADMIN', 'DIRECCION'))


def _level(skill, total):
    if skill in ('lectura', 'escritura'):
        return 'NIVEL ESPERADO' if total >= 15 else ('EN DESARROLLO' if total >= 10 else 'REQUIERE APOYO')
    return 'NIVEL ESPERADO' if total >= 8 else ('EN DESARROLLO' if total >= 5 else 'REQUIERE APOYO')


def _scores(row):
    try:
        value = json.loads(row.scores_json or '{}')
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _fraction(value):
    value = Fraction(value).limit_denominator()
    if value.denominator == 1:
        return str(value.numerator)
    return f'{value.numerator}/{value.denominator}'


def _mental_questions(grade, rng=None):
    rng = rng or random.SystemRandom()
    questions = []

    def add(prompt, answer, category):
        questions.append({'number': len(questions) + 1, 'prompt': prompt, 'answer': str(answer), 'category': category})

    if grade == '1':
        a = rng.randint(24, 69); b = rng.randint(16, 39); add(f'{a} más {b}', a + b, 'Suma de naturales')
        a = rng.randint(6, 14); b = rng.randint(4, 9); add(f'{a} por {b}', a * b, 'Multiplicación')
        a = rng.randint(12, 25); b = rng.randint(2, 4); c = rng.randint(8, 22); add(f'{a} por {b} menos {c}', a * b - c, 'Operaciones combinadas')
        den = rng.choice([4, 6, 8]); n1 = rng.randint(1, den - 2); n2 = rng.randint(1, den - n1); add(f'{n1}/{den} más {n2}/{den}', _fraction(Fraction(n1 + n2, den)), 'Suma de fracciones')
        den = rng.choice([2, 4, 5, 10]); num = rng.randint(1, den - 1); add(f'Convierte {num}/{den} en número decimal', f'{num/den:g}', 'Fracción a decimal')
        d1, d2 = rng.choice([(2, 3), (3, 4), (3, 5), (4, 5)]); n1 = rng.randint(1, d1 - 1); n2 = rng.randint(1, d2 - 1); add(f'{n1}/{d1} por {n2}/{d2}', _fraction(Fraction(n1*n2, d1*d2)), 'Multiplicación de fracciones')
        b = rng.choice([10.2, 11.5, 12.4, 15.25]); result = rng.randint(70, 130); a = result + b; add(f'{a:g} menos {b:g}', f'{result:g}', 'Resta de decimales')
        x = rng.randint(4, 11); d = rng.choice([0.25, 0.5, 0.75]); sub = rng.randint(2, 5); add(f'{x-d:g} más {d:g} menos {sub}', x-sub, 'Operaciones con decimales')
        a = rng.randint(4, 12); add(f'¿Cuánto es {a} al cuadrado?', a*a, 'Potencia cuadrada')
        den = rng.choice([2, 4]); frac = Fraction(rng.randint(1, den-1), den); whole = rng.randint(2, 5); sub = Fraction(rng.randint(1, 3), 3); add(f'{float(frac):g} más {whole} menos {_fraction(sub)}', _fraction(frac + whole - sub), 'Fracciones y decimales')
    elif grade == '2':
        h = rng.randint(1, 2); minutes = rng.choice([15, 25, 35, 45]); extra = rng.choice([20, 30, 40, 50]); total = h*60 + minutes + extra; add(f'¿Cuánto es {h} hora{'' if h == 1 else 's'} {minutes} minutos más {extra} minutos?', f'{total//60} h {total%60:02d} min', 'Suma de tiempo')
        divisor = rng.choice([3, 4, 5]); result = rng.randint(8, 20); add(f'{"Tercera" if divisor == 3 else "Cuarta" if divisor == 4 else "Quinta"} parte de {divisor*result}', result, 'Parte de una cantidad')
        pct = rng.choice([10, 20, 25, 50]); base = rng.choice([40, 60, 80, 90, 120, 160]); add(f'{pct}% de {base}', int(base*pct/100), 'Porcentaje')
        a = rng.randint(12, 35); b = rng.randint(2, a-3); add(f'{a}x menos {b}x', f'{a-b}x', 'Términos semejantes')
        start = rng.choice([0.2, 0.4, 0.6, 1.1]); step = rng.choice([0.2, 0.3, 0.5]); seq = [start + step*i for i in range(5)]; add(f'¿Qué números siguen en esta serie: {seq[0]:g}, {seq[1]:g}, {seq[2]:g}, __, __?', f'{seq[3]:g} y {seq[4]:g}', 'Sucesión decimal')
        result = rng.choice([20.5, 25.5, 30.5, 35.5]); b = rng.choice([11.5, 12.5, 13.5]); add(f'{result+b:g} menos {b:g}', f'{result:g}', 'Resta de decimales')
        den = rng.choice([2, 4, 5]); num = rng.randint(1, den-1); whole = den*rng.randint(8, 16); add(f'{num}/{den} de {whole}', int(num*whole/den), 'Fracción de una cantidad')
        decimal = rng.choice([0.25, 0.5, 0.75]); whole = rng.choice([40, 60, 80, 120]); add(f'{decimal:g} por {whole}', f'{decimal*whole:g}', 'Producto decimal')
        a = rng.randint(2, 5); add(f'¿Cuánto es {a} al cubo?', a**3, 'Potencia cúbica')
        n1, d1, n2, d2 = rng.choice([(1,2,1,4),(2,3,1,3),(3,4,1,2)]); add(f'{n1}/{d1} entre {n2}/{d2}', _fraction(Fraction(n1,d1)/Fraction(n2,d2)), 'División de fracciones')
    else:
        result = rng.choice([600, 700, 800, 900]); b = rng.randint(21, 79); add(f'{result-b} más {b}', result, 'Suma de naturales')
        a = rng.choice([600, 700, 800, 900]); b = rng.randint(41, 129); add(f'{a} menos {b}', a-b, 'Resta de naturales')
        a = rng.choice([20, 30, 40, 50, 60, 70]); b = rng.choice([200, 300, 400, 500]); add(f'{a} por {b}', a*b, 'Multiplicación')
        divisor = rng.randint(3, 9); first = divisor*rng.randint(5, 12); multiplier = rng.randint(3, 8); add(f'{first} entre {divisor} por {multiplier}', first//divisor*multiplier, 'División y multiplicación')
        a = rng.randint(3, 6); sub = rng.randint(2, 9); add(f'{a} al cubo, menos {sub}', a**3-sub, 'Potencia y resta')
        x = rng.randint(2, 12); coef = rng.randint(2, 7); add(f'¿Cuál es el valor de x en {coef}x menos {coef*x} = 0?', x, 'Ecuación lineal')
        values = rng.choice([(Fraction(1,2),Fraction(3,4),Fraction(2,8)),(Fraction(2,3),Fraction(1,2),Fraction(1,6)),(Fraction(3,4),Fraction(2,3),Fraction(5,12))]); add(f'{_fraction(values[0])} más {_fraction(values[1])} menos {_fraction(values[2])}', _fraction(values[0]+values[1]-values[2]), 'Operaciones con fracciones')
        frac = rng.choice([Fraction(1,2),Fraction(3,4),Fraction(2,5)]); dec = rng.choice([0.25,0.5,0.75]); add(f'{dec:g} más {_fraction(frac)}', _fraction(Fraction(str(dec))+frac), 'Decimal y fracción')
        den = rng.choice([3,5,7]); seq = [Fraction(2**i, den*(2**i)) for i in range(4)]; add(f'¿Qué fracciones siguen en esta serie: 1/{den}, 2/{den*2}, 4/{den*4}, __, __?', f'8/{den*8} y 16/{den*16}', 'Sucesión de fracciones equivalentes')
        a = rng.randint(30, 70); b = rng.randint(20, 100-a); add(f'Dos ángulos interiores de un triángulo miden {a}° y {b}°. ¿Cuánto mide el tercer ángulo?', f'{180-a-b}°', 'Ángulos de un triángulo')
    return questions


def _practice_questions(grade):
    return {
        '1': [('600 menos 500', '100'), ('¿Cuánto es la mitad de 62?', '31')],
        '2': [('15 por 10', '150'), ('¿60 entre qué número da 20?', '3')],
        '3': [('20 más 18', '38'), ('¿Qué número multiplicado por 5 da 40?', '8')],
    }[grade]


def _all_assessments():
    return SisatAssessment.query.execution_options(group_scope_disabled=True).all()


def _all_students():
    return core.Student.query.execution_options(group_scope_disabled=True).all()


def _student_groups():
    try:
        import group_workspaces
        rows = group_workspaces.RecordGroup.query.filter_by(entity_type='student').all()
        return {row.entity_id: row.group_code for row in rows}
    except Exception:
        return {}


def _active_group():
    try:
        import group_workspaces
        return group_workspaces.active_group_code() or '1A'
    except Exception:
        return '1A'


def _summary_rows(assessments, students):
    student_map = {student.id: student for student in students}
    groups = _student_groups()
    rows = []
    for assessment in assessments:
        student = student_map.get(assessment.student_id)
        if not student:
            continue
        rows.append({
            'group': groups.get(student.id, ''), 'list_no': student.list_no or '', 'student': student.full_name,
            'skill': SKILLS.get(assessment.skill, {}).get('title', assessment.skill),
            'date': assessment.application_date, 'visit': assessment.visit, 'scores': _scores(assessment),
            'total': assessment.total, 'level': assessment.level, 'observations': assessment.observations or '',
            'student_id': student.id,
        })
    return rows


def _export_workbook(scope, skill='', student_id=None):
    assessments = _all_assessments()
    students = _all_students()
    groups = _student_groups()
    active_group = _active_group()
    if scope == 'group':
        allowed_ids = {student.id for student in students if groups.get(student.id) == active_group}
        assessments = [row for row in assessments if row.student_id in allowed_ids]
        students = [student for student in students if student.id in allowed_ids]
    elif scope == 'student':
        assessments = [row for row in assessments if row.student_id == student_id]
        students = [student for student in students if student.id == student_id]
    if skill in SKILLS:
        assessments = [row for row in assessments if row.skill == skill]
    rows = _summary_rows(assessments, students)

    output = io.BytesIO(); wb = xlsxwriter.Workbook(output, {'in_memory': True})
    title = wb.add_format({'bold': True, 'font_size': 16, 'font_color': '#FFFFFF', 'bg_color': '#7B1024', 'align': 'center', 'valign': 'vcenter'})
    header = wb.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#217346', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'border': 1})
    cell = wb.add_format({'border': 1, 'valign': 'top'}); center = wb.add_format({'border': 1, 'align': 'center', 'valign': 'top'})
    date_fmt = wb.add_format({'border': 1, 'align': 'center', 'num_format': 'dd/mm/yyyy'})
    percent_fmt = wb.add_format({'border': 1, 'align': 'center', 'num_format': '0.0%'})
    level_formats = {key: wb.add_format({'border': 1, 'align': 'center', 'bold': True, 'bg_color': color}) for key, color in LEVEL_COLORS.items()}

    ws = wb.add_worksheet('Resumen')
    ws.merge_range(0, 0, 0, 7, 'CONCENTRADO DE RESULTADOS SiSAT', title)
    ws.write_row(2, 0, ['Ámbito', 'Alumnos evaluados', 'Aplicaciones', 'Nivel esperado', 'En desarrollo', 'Requiere apoyo', 'Promedio lectura/escritura', 'Promedio cálculo'], header)
    unique_students = len({row['student_id'] for row in rows}); levels = {level: sum(1 for row in rows if row['level'] == level) for level in LEVEL_COLORS}
    lit = [row['total'] for row in rows if row['skill'] != 'Cálculo mental']; mental = [row['total'] for row in rows if row['skill'] == 'Cálculo mental']
    label = 'Escuela' if scope == 'school' else (f'Grupo {active_group}' if scope == 'group' else (students[0].full_name if students else 'Alumno'))
    ws.write_row(3, 0, [label, unique_students, len(rows), levels['NIVEL ESPERADO'], levels['EN DESARROLLO'], levels['REQUIERE APOYO'], round(sum(lit)/len(lit), 2) if lit else '', round(sum(mental)/len(mental), 2) if mental else ''], center)
    ws.write(6, 0, 'Distribución por habilidad', header)
    ws.write_row(7, 0, ['Habilidad', 'Aplicaciones', 'Nivel esperado', 'En desarrollo', 'Requiere apoyo', 'Promedio'], header)
    out_row = 8
    for skill_key, config in SKILLS.items():
        subset = [row for row in rows if row['skill'] == config['title']]
        if not subset: continue
        ws.write_row(out_row, 0, [config['title'], len(subset), sum(1 for row in subset if row['level']=='NIVEL ESPERADO'), sum(1 for row in subset if row['level']=='EN DESARROLLO'), sum(1 for row in subset if row['level']=='REQUIERE APOYO'), round(sum(row['total'] for row in subset)/len(subset),2)], center); out_row += 1
    if scope == 'school':
        out_row += 2; ws.write(out_row, 0, 'Resultados por grupo', header); out_row += 1
        ws.write_row(out_row, 0, ['Grupo', 'Alumnos evaluados', 'Aplicaciones', 'Nivel esperado', 'En desarrollo', 'Requiere apoyo', 'Promedio'], header); out_row += 1
        for group_code in sorted({row['group'] for row in rows if row['group']}):
            subset = [row for row in rows if row['group'] == group_code]
            ws.write_row(out_row, 0, [group_code, len({row['student_id'] for row in subset}), len(subset), sum(1 for row in subset if row['level']=='NIVEL ESPERADO'), sum(1 for row in subset if row['level']=='EN DESARROLLO'), sum(1 for row in subset if row['level']=='REQUIERE APOYO'), round(sum(row['total'] for row in subset)/len(subset),2)], center); out_row += 1
    ws.set_column(0, 0, 30); ws.set_column(1, 7, 18); ws.freeze_panes(3, 0)

    detail = wb.add_worksheet('Detalle')
    detail.merge_range(0, 0, 0, 9, 'DETALLE DE RESULTADOS SiSAT', title)
    headers = ['Grupo', 'No.', 'Alumno', 'Habilidad', 'Fecha', 'Visita', 'Puntaje', 'Resultado', 'Resultados por componente/pregunta', 'Observaciones']
    detail.write_row(2, 0, headers, header)
    for index, row in enumerate(rows, start=3):
        score_text = ', '.join(f'{key}: {value}' for key, value in row['scores'].items())
        values = [row['group'], row['list_no'], row['student'], row['skill'], row['date'], row['visit'], row['total'], row['level'], score_text, row['observations']]
        for col, value in enumerate(values):
            fmt = date_fmt if col == 4 else (level_formats.get(row['level'], center) if col == 7 else (center if col in (0,1,5,6) else cell))
            detail.write(index, col, value, fmt)
    detail.autofilter(2, 0, max(3, len(rows)+2), 9); detail.freeze_panes(3, 3)
    detail.set_column(0, 1, 10); detail.set_column(2, 3, 28); detail.set_column(4, 7, 16); detail.set_column(8, 9, 48)
    detail.conditional_format(3, 6, max(3, len(rows)+2), 6, {'type': '3_color_scale', 'min_color': '#FADDDD', 'mid_color': '#FFF0C9', 'max_color': '#DFF2E5'})

    analysis = wb.add_worksheet('Componentes')
    analysis.merge_range(0, 0, 0, 6, 'ANÁLISIS POR COMPONENTE Y PREGUNTA', title)
    analysis.write_row(2, 0, ['Habilidad', 'Componente / pregunta', 'Registros', 'Puntaje obtenido', 'Puntaje posible', 'Porcentaje', 'Interpretación'], header)
    analysis_row = 3
    for skill_key, config in SKILLS.items():
        subset = [row for row in rows if row['skill'] == config['title']]
        if not subset: continue
        if skill_key in ('lectura', 'escritura'):
            measures = [(key, label, 3) for key, label, _ in config['components']]
        else:
            measures = [(f'P{number}', f'Pregunta {number}', 1) for number in range(1, 11)]
        for key, label_text, maximum in measures:
            values = [row['scores'].get(key) for row in subset if row['scores'].get(key) not in (None, '', 0, '0')]
            if skill_key == 'calculo':
                obtained = sum(1 for value in values if value in ('1', '1V')); count = len(subset); possible = count
                visual = sum(1 for value in values if value == '1V')
            else:
                numeric = [int(value) for value in values if str(value).isdigit()]; obtained = sum(numeric); count = len(numeric); possible = count * maximum; visual = 0
            percentage = obtained / possible if possible else 0
            if skill_key == 'calculo':
                interpretation = 'Desarrollo generalizado' if percentage >= .81 else ('Diferencias de desempeño' if percentage >= .51 else 'Dificultad generalizada')
                if percentage >= .81 and obtained and visual / obtained >= .5: interpretation += '; reforzar presentación verbal'
            else:
                interpretation = 'Manejo adecuado' if percentage >= .81 else ('Avance significativo' if percentage >= .56 else 'Poco avance')
            values_out = [config['title'], label_text, count, obtained, possible, percentage, interpretation]
            for col, value in enumerate(values_out): analysis.write(analysis_row, col, value, percent_fmt if col == 5 else (center if col in (2,3,4) else cell))
            analysis.set_row(analysis_row, 28); analysis_row += 1
    analysis.set_column(0, 1, 30); analysis.set_column(2, 4, 16); analysis.set_column(5, 5, 14); analysis.set_column(6, 6, 38)
    analysis.autofilter(2, 0, max(3, analysis_row-1), 6); analysis.freeze_panes(3, 2)

    rubric_sheet = wb.add_worksheet('Rúbricas')
    rubric_sheet.merge_range(0, 0, 0, 5, 'RÚBRICAS DE LECTURA Y PRODUCCIÓN DE TEXTOS', title)
    rubric_sheet.write_row(2, 0, ['Habilidad', 'Componente', '3 puntos', '2 puntos', '1 punto', 'Rango global'], header)
    rubric_row = 3
    for skill_key in ('lectura', 'escritura'):
        config = SKILLS[skill_key]
        for key, label_text, descriptors in config['components']:
            rubric_sheet.write_row(rubric_row, 0, [config['title'], label_text, f'{descriptors[0]}. {RUBRIC_GUIDANCE[skill_key][key][3]}', f'{descriptors[1]}. {RUBRIC_GUIDANCE[skill_key][key][2]}', f'{descriptors[2]}. {RUBRIC_GUIDANCE[skill_key][key][1]}', '15–18: Nivel esperado · 10–14: En desarrollo · 9 o menos: Requiere apoyo'], cell)
            rubric_sheet.set_row(rubric_row, 72); rubric_row += 1
    rubric_sheet.write_row(rubric_row, 0, ['Cálculo mental', 'Códigos y nivel', '1 = correcta sin apoyo visual', '1V = correcta con apoyo visual', '0 = equivocada o sin respuesta', '8–10: Nivel esperado · 5–7: En desarrollo · 0–4: Requiere apoyo'], cell)
    rubric_sheet.set_row(rubric_row, 54)
    rubric_sheet.set_column(0, 1, 28); rubric_sheet.set_column(2, 4, 46); rubric_sheet.set_column(5, 5, 34); rubric_sheet.freeze_panes(3, 2)
    wb.close(); output.seek(0); return output


def install(app):
    try:
        with app.app_context(): core.db.create_all()
    except Exception:
        pass

    @app.route('/sisat')
    def sisat_dashboard():
        if not session.get('uid'): return redirect('/login')
        group = _active_group(); students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()
        student_ids = [student.id for student in students]
        rows = SisatAssessment.query.filter(SisatAssessment.student_id.in_(student_ids)).all() if student_ids else []
        cards = ''
        for key, config in SKILLS.items():
            subset = [row for row in rows if row.skill == key]
            completed = len({row.student_id for row in subset}); priority = sum(1 for row in subset if row.level == 'REQUIERE APOYO')
            cards += f'''<div class="card"><h2>{escape(config['title'])}</h2><div class="kpi">{completed}/{len(students)}</div><p class="muted">Alumnos con registro · {priority} aplicaciones requieren apoyo</p><a href="/sisat/capture/{key}" class="sisat-btn">Capturar resultados</a></div>'''
        export_block = ''
        if _can_export():
            student_options = ''.join(f'<option value="{s.id}">{escape(s.full_name)}</option>' for s in students)
            export_block = f'''<div class="card"><h2>Exportar resultados</h2><p class="muted">Administración y Dirección pueden generar concentrados por escuela, grupo activo o alumno.</p><form method="get" action="/sisat/export.xlsx" class="grid"><label>Ámbito<select name="scope" id="sisat-scope" onchange="document.getElementById('sisat-student').style.display=this.value==='student'?'block':'none'"><option value="school">Toda la escuela</option><option value="group">Grupo {group}</option><option value="student">Alumno</option></select></label><label>Habilidad<select name="skill"><option value="">Todas</option>{''.join(f'<option value="{k}">{escape(v["title"])}</option>' for k,v in SKILLS.items())}</select></label><label id="sisat-student" style="display:none">Alumno<select name="student_id">{student_options}</select></label><div><button>Exportar Excel</button></div></form></div>'''
        body = f'''<h1>SiSAT · Grupo {group}</h1><p class="muted">Exploración de habilidades básicas en lectura, producción de textos escritos y cálculo mental.</p><div class="grid">{cards}</div><div class="card"><h2>Prueba de cálculo mental</h2><p>Genera diez reactivos aleatorios con el mismo nivel y tipo de habilidad que los instrumentos oficiales de cada grado.</p><a href="/sisat/mental-test" class="sisat-btn">Generar prueba</a></div>{export_block}<style>.sisat-btn{{display:inline-block;background:#7b1024;color:white;text-decoration:none;padding:10px 14px;border-radius:9px;font-weight:800}}</style>'''
        return core.page('SiSAT', body)

    @app.route('/sisat/capture/<skill>', methods=['GET', 'POST'])
    def sisat_capture(skill):
        if not session.get('uid'): return redirect('/login')
        if skill not in SKILLS: return redirect('/sisat')
        if not _can_capture(): flash('Tu rol no permite capturar resultados SiSAT.'); return redirect('/sisat')
        students = core.Student.query.filter_by(status='ACTIVO').order_by(core.Student.list_no, core.Student.paternal).all()
        app_date = request.values.get('date') or str(date.today()); visit = request.values.get('visit', type=int) or 1
        try: parsed_date = datetime.strptime(app_date, '%Y-%m-%d').date()
        except ValueError: parsed_date = date.today(); app_date = str(parsed_date)
        existing = {row.student_id: row for row in SisatAssessment.query.filter_by(skill=skill, application_date=parsed_date, visit=visit).all()}
        if request.method == 'POST':
            for student in students:
                if request.form.get(f'enabled_{student.id}') != '1': continue
                scores = {}
                if skill in ('lectura', 'escritura'):
                    for key, _, _ in SKILLS[skill]['components']:
                        value = request.form.get(f'{key}_{student.id}', type=int)
                        scores[key] = value if value in (1,2,3) else 0
                    total = sum(scores.values())
                else:
                    for number in range(1, 11):
                        code = request.form.get(f'q{number}_{student.id}', '0')
                        scores[f'P{number}'] = code if code in ('1', '1V', '0') else '0'
                    total = sum(1 for value in scores.values() if value in ('1','1V'))
                row = existing.get(student.id) or SisatAssessment(student_id=student.id, skill=skill, application_date=parsed_date, visit=visit)
                row.scores_json = json.dumps(scores, ensure_ascii=False); row.total = total; row.level = _level(skill, total)
                row.observations = request.form.get(f'obs_{student.id}', '').strip(); row.applied_by = session.get('uid')
                core.db.session.add(row)
            core.db.session.commit(); flash(f'Resultados de {SKILLS[skill]["title"]} guardados.'); return redirect(f'/sisat/capture/{skill}?date={app_date}&visit={visit}')
        headers = ''; rows_html = ''
        if skill in ('lectura', 'escritura'):
            headers = ''.join(f'<th>{escape(label)}</th>' for _, label, _ in SKILLS[skill]['components'])
        else: headers = ''.join(f'<th>P{number}</th>' for number in range(1,11))
        for student in students:
            row = existing.get(student.id); values = _scores(row) if row else {}; cells = ''
            if skill in ('lectura', 'escritura'):
                for key, _, descriptors in SKILLS[skill]['components']:
                    selected = int(values.get(key, 0) or 0)
                    options = '<option value="0">Sin valorar</option>' + ''.join(f'<option value="{score}" {"selected" if selected==score else ""}>{score} · {escape(descriptors[3-score])}</option>' for score in (3,2,1))
                    cells += f'<td><select name="{key}_{student.id}" style="min-width:190px">{options}</select></td>'
            else:
                for number in range(1,11):
                    selected = values.get(f'P{number}', '0'); options = ''.join(f'<option value="{code}" {"selected" if selected==code else ""}>{label}</option>' for code,label in [('1','1 · Correcta sin apoyo'),('1V','1V · Correcta con apoyo visual'),('0','0 · Incorrecta o sin respuesta')]); cells += f'<td><select name="q{number}_{student.id}" style="min-width:130px">{options}</select></td>'
            total = row.total if row else 0; level = row.level if row else 'SIN REGISTRO'; obs = row.observations if row else ''
            rows_html += f'''<tr><td><input class="sisat-enable" type="checkbox" name="enabled_{student.id}" value="1" {"checked" if row else ""} style="width:auto"></td><td>{student.list_no or ''}</td><td class="sticky-student"><b>{escape(student.full_name)}</b></td>{cells}<td><b>{total}</b></td><td>{escape(level)}</td><td><textarea name="obs_{student.id}" rows="2" style="min-width:210px">{escape(obs)}</textarea></td></tr>'''
        rubric = ''
        if skill in ('lectura','escritura'):
            rubric = '<details class="card"><summary><b>Consultar rúbrica de valoración</b></summary><div class="grid" style="margin-top:14px">' + ''.join(f'<div><h3>{escape(label)}</h3><p><b>3 · {escape(desc[0])}:</b> {escape(RUBRIC_GUIDANCE[skill][key][3])}<br><br><b>2 · {escape(desc[1])}:</b> {escape(RUBRIC_GUIDANCE[skill][key][2])}<br><br><b>1 · {escape(desc[2])}:</b> {escape(RUBRIC_GUIDANCE[skill][key][1])}</p></div>' for key,label,desc in SKILLS[skill]['components']) + '</div></details>'
        else:
            rubric = '<div class="card"><b>Códigos:</b> 1 = respuesta correcta sin presentación visual · 1V = respuesta correcta con presentación visual · 0 = respuesta equivocada o sin respuesta. Detenga la aplicación después de seis errores consecutivos.</div>'
        body = f'''<h1>{escape(SKILLS[skill]['title'])}</h1><form method="get" class="card grid"><label>Fecha<input type="date" name="date" value="{app_date}"></label><label>Visita<input type="number" name="visit" min="1" max="9" value="{visit}"></label><div><button>Cargar aplicación</button></div></form>{rubric}<form method="post" class="card"><input type="hidden" name="date" value="{app_date}"><input type="hidden" name="visit" value="{visit}"><div style="display:flex;gap:10px;margin-bottom:12px"><button type="button" style="width:auto" onclick="document.querySelectorAll('.sisat-enable').forEach(x=>x.checked=true)">Seleccionar todos</button><button type="button" style="width:auto;background:#6d737c" onclick="document.querySelectorAll('.sisat-enable').forEach(x=>x.checked=false)">Quitar selección</button></div><p class="muted">Solo se guardarán los alumnos seleccionados en la primera columna.</p><div class="scroll"><table class="sisat-capture"><tr><th>Aplicar</th><th>No.</th><th>Alumno</th>{headers}<th>Total</th><th>Resultado</th><th>Observaciones</th></tr>{rows_html}</table></div><br><button>Guardar resultados</button></form><style>.sisat-capture{{min-width:{'1800' if skill != 'calculo' else '2300'}px}}.sticky-student{{position:sticky;left:0;background:white;z-index:2;min-width:220px}}</style>'''
        return core.page(SKILLS[skill]['title'], body)

    @app.route('/sisat/mental-test')
    def sisat_mental_test():
        if not session.get('uid'): return redirect('/login')
        grade = request.args.get('grade', '1'); grade = grade if grade in ('1','2','3') else '1'
        questions = _mental_questions(grade); practice = _practice_questions(grade)
        practice_rows = ''.join(f'<tr><td>Ej. {i}</td><td>{escape(q)}</td><td class="answer">{escape(a)}</td></tr>' for i,(q,a) in enumerate(practice,1))
        question_rows = ''.join(f'<tr><td>{q["number"]}</td><td>{escape(q["prompt"])}</td><td class="answer">{escape(q["answer"])}</td><td class="category">{escape(q["category"])}</td></tr>' for q in questions)
        body = f'''<div class="no-print card"><h1>Generador de cálculo mental</h1><form method="get" class="grid"><label>Grado<select name="grade"><option value="1" {"selected" if grade=="1" else ""}>Primer grado</option><option value="2" {"selected" if grade=="2" else ""}>Segundo grado</option><option value="3" {"selected" if grade=="3" else ""}>Tercer grado</option></select></label><div><button>Generar otra prueba</button></div><div><button type="button" onclick="window.print()">Imprimir prueba</button></div><div><button type="button" onclick="document.body.classList.toggle('show-answers')">Mostrar u ocultar respuestas</button></div></form></div><div class="card mental-sheet"><h1>CÁLCULO MENTAL · {grade}.º DE SECUNDARIA</h1><p>Aplicación individual. Plantee cada pregunta de forma oral. Muestre apoyo visual únicamente conforme al procedimiento SiSAT.</p><table><tr><th>No.</th><th>Pregunta</th><th class="answer">Respuesta</th><th class="category">Habilidad equivalente</th></tr>{practice_rows}{question_rows}</table><p class="muted">Códigos de registro: 1 correcta sin apoyo visual · 1V correcta con apoyo visual · 0 equivocada o sin respuesta.</p></div><style>.mental-sheet{{max-width:920px;margin:auto}}.mental-sheet table{{min-width:0}}.mental-sheet td:first-child{{width:70px;text-align:center;font-weight:800}}.answer,.category{{display:none}}.show-answers .answer,.show-answers .category{{display:table-cell}}@media print{{.sidebar,.topbar,.bottom-nav,.footer,.workspace-banner,.workspace-mobile,.no-print{{display:none!important}}.main-area,.wrap{{margin:0!important;padding:0!important;max-width:none!important}}.mental-sheet{{box-shadow:none!important;border:0!important}}.mental-sheet .answer,.mental-sheet .category{{display:none!important}}}}</style>'''
        return core.page('Prueba de cálculo mental', body)

    @app.route('/sisat/export.xlsx')
    def sisat_export():
        if not session.get('uid'): return redirect('/login')
        if not _can_export(): flash('Solo Administración y Dirección pueden exportar concentrados SiSAT.'); return redirect('/sisat')
        scope = request.args.get('scope', 'group'); scope = scope if scope in ('school','group','student') else 'group'
        skill = request.args.get('skill', ''); student_id = request.args.get('student_id', type=int)
        output = _export_workbook(scope, skill, student_id)
        return send_file(output, as_attachment=True, download_name=f'sisat_{scope}_{date.today().isoformat()}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.after_request
    def sisat_navigation(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'): return response
        html = response.get_data(as_text=True)
        if 'href="/sisat"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'; link = '<a class="nav-link" href="/sisat"><span class="nav-icon">▦</span><span>SiSAT</span></a>'
            if marker in html: html = html.replace(marker, link + marker, 1)
        response.set_data(html); response.headers['Content-Length'] = str(len(response.get_data())); return response
