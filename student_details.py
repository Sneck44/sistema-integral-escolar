from html import escape

from flask import request, redirect, flash

import app as core


class StudentDetails(core.db.Model):
    __tablename__ = 'student_details'
    id = core.db.Column(core.db.Integer, primary_key=True)
    student_id = core.db.Column(core.db.Integer, core.db.ForeignKey('student.id'), unique=True, nullable=False)
    weight_kg = core.db.Column(core.db.Float, nullable=True)
    height_cm = core.db.Column(core.db.Float, nullable=True)
    top_size = core.db.Column(core.db.String(30), default='')
    bottom_size = core.db.Column(core.db.String(30), default='')
    sweater_size = core.db.Column(core.db.String(30), default='')
    shoe_size = core.db.Column(core.db.String(30), default='')
    uniform_notes = core.db.Column(core.db.String(250), default='')


def _details(student_id):
    return StudentDetails.query.filter_by(student_id=student_id).first()


def _float_or_none(value):
    value = (value or '').strip().replace(',', '.')
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _save_details(student_id):
    details = _details(student_id)
    if not details:
        details = StudentDetails(student_id=student_id)
        core.db.session.add(details)
    details.weight_kg = _float_or_none(request.form.get('weight_kg'))
    details.height_cm = _float_or_none(request.form.get('height_cm'))
    details.top_size = request.form.get('top_size', '').strip()
    details.bottom_size = request.form.get('bottom_size', '').strip()
    details.sweater_size = request.form.get('sweater_size', '').strip()
    details.shoe_size = request.form.get('shoe_size', '').strip()
    details.uniform_notes = request.form.get('uniform_notes', '').strip()
    return details


def _value(value):
    return escape(str(value)) if value not in (None, '') else ''


def install(app):
    def students_extended():
        r = core.require()
        if r:
            return r

        if request.method == 'POST':
            student = core.Student(
                list_no=request.form.get('list_no', type=int),
                paternal=request.form['paternal'].strip(),
                maternal=request.form.get('maternal', '').strip(),
                names=request.form['names'].strip(),
                tutor=request.form.get('tutor', '').strip(),
                phone=request.form.get('phone', '').strip(),
            )
            core.db.session.add(student)
            core.db.session.flush()
            _save_details(student.id)
            core.db.session.commit()
            flash('Alumno y datos de talla guardados.')
            return redirect('/students')

        rows = ''
        for student in core.Student.query.order_by(core.Student.list_no, core.Student.paternal).all():
            d = _details(student.id)
            weight = f'{d.weight_kg:g} kg' if d and d.weight_kg is not None else '—'
            height = f'{d.height_cm:g} cm' if d and d.height_cm is not None else '—'
            clothing = ' / '.join(x for x in [
                f'Sup. {d.top_size}' if d and d.top_size else '',
                f'Inf. {d.bottom_size}' if d and d.bottom_size else '',
                f'Suéter {d.sweater_size}' if d and d.sweater_size else '',
            ] if x) or '—'
            shoe = d.shoe_size if d and d.shoe_size else '—'
            rows += f'''<tr>
              <td>{student.list_no or ''}</td>
              <td><b>{escape(student.full_name)}</b><br><small>{escape(student.status or '')}</small></td>
              <td>{escape(weight)}</td>
              <td>{escape(height)}</td>
              <td>{escape(clothing)}</td>
              <td>{escape(shoe)}</td>
              <td>{escape(student.tutor or '—')}<br><small>{escape(student.phone or '')}</small></td>
              <td><a href="/students/{student.id}/edit" style="font-weight:700">Editar</a></td>
            </tr>'''

        body = f'''
        <h1>Alumnos</h1>
        <div class="card">
          <h2>Agregar alumno</h2>
          <form method="post" class="grid">
            <label>No. de lista<input name="list_no" type="number" min="1"></label>
            <label>Apellido paterno<input name="paternal" required></label>
            <label>Apellido materno<input name="maternal"></label>
            <label>Nombre(s)<input name="names" required></label>
            <label>Tutor<input name="tutor"></label>
            <label>Teléfono<input name="phone"></label>
          </form>
        </div>
        <div class="card">
          <h2>Peso, estatura y tallas</h2>
          <form method="post" class="grid" id="student-complete-form">
            <input type="hidden" name="list_no" id="f-list_no">
            <input type="hidden" name="paternal" id="f-paternal">
            <input type="hidden" name="maternal" id="f-maternal">
            <input type="hidden" name="names" id="f-names">
            <input type="hidden" name="tutor" id="f-tutor">
            <input type="hidden" name="phone" id="f-phone">
            <label>Peso (kg)<input name="weight_kg" type="number" step="0.1" min="0" placeholder="Ej. 45.5"></label>
            <label>Estatura (cm)<input name="height_cm" type="number" step="0.1" min="0" placeholder="Ej. 152"></label>
            <label>Talla playera / blusa<input name="top_size" placeholder="Ej. 14, CH, M"></label>
            <label>Talla pantalón / falda<input name="bottom_size" placeholder="Ej. 14, 28, M"></label>
            <label>Talla suéter / chamarra<input name="sweater_size" placeholder="Ej. CH, M, G"></label>
            <label>Número de calzado<input name="shoe_size" placeholder="Ej. 24.5"></label>
            <label style="grid-column:1/-1">Observaciones de uniforme<textarea name="uniform_notes" rows="2" placeholder="Ajustes, talla especial, observaciones..."></textarea></label>
            <div><button type="submit">Agregar alumno</button></div>
          </form>
          <script>
          (function(){{
            const firstForm = document.querySelector('.card form.grid:not(#student-complete-form)');
            const fullForm = document.getElementById('student-complete-form');
            if (!firstForm || !fullForm) return;
            firstForm.addEventListener('submit', function(e){{e.preventDefault();}});
            fullForm.addEventListener('submit', function(){{
              ['list_no','paternal','maternal','names','tutor','phone'].forEach(function(n){{
                const src=firstForm.querySelector('[name="'+n+'"]');
                const dst=document.getElementById('f-'+n);
                if(src && dst) dst.value=src.value;
              }});
            }});
          }})();
          </script>
        </div>
        <div class="card scroll">
          <h2>Alumnos registrados</h2>
          <table>
            <tr><th>No.</th><th>Alumno</th><th>Peso</th><th>Estatura</th><th>Tallas de prendas</th><th>Calzado</th><th>Tutor</th><th></th></tr>
            {rows}
          </table>
        </div>'''
        return core.page('Alumnos', body)

    app.view_functions['students'] = students_extended

    @app.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
    def edit_student(student_id):
        r = core.require()
        if r:
            return r
        student = core.db.session.get(core.Student, student_id)
        if not student:
            flash('Alumno no encontrado.')
            return redirect('/students')

        if request.method == 'POST':
            student.list_no = request.form.get('list_no', type=int)
            student.paternal = request.form.get('paternal', '').strip()
            student.maternal = request.form.get('maternal', '').strip()
            student.names = request.form.get('names', '').strip()
            student.status = request.form.get('status', 'ACTIVO').strip() or 'ACTIVO'
            student.tutor = request.form.get('tutor', '').strip()
            student.phone = request.form.get('phone', '').strip()
            _save_details(student.id)
            core.db.session.commit()
            flash('Datos del alumno actualizados.')
            return redirect('/students')

        d = _details(student.id)
        body = f'''
        <h1>Editar alumno</h1>
        <div class="card">
          <h2>Datos generales</h2>
          <form method="post" class="grid">
            <label>No. de lista<input name="list_no" type="number" value="{_value(student.list_no)}"></label>
            <label>Apellido paterno<input name="paternal" required value="{_value(student.paternal)}"></label>
            <label>Apellido materno<input name="maternal" value="{_value(student.maternal)}"></label>
            <label>Nombre(s)<input name="names" required value="{_value(student.names)}"></label>
            <label>Estado<select name="status"><option {'selected' if student.status == 'ACTIVO' else ''}>ACTIVO</option><option {'selected' if student.status == 'BAJA' else ''}>BAJA</option></select></label>
            <label>Tutor<input name="tutor" value="{_value(student.tutor)}"></label>
            <label>Teléfono<input name="phone" value="{_value(student.phone)}"></label>
            <div style="grid-column:1/-1"><h2 style="margin-top:12px">Peso, estatura y tallas</h2></div>
            <label>Peso (kg)<input name="weight_kg" type="number" step="0.1" min="0" value="{_value(d.weight_kg if d else '')}"></label>
            <label>Estatura (cm)<input name="height_cm" type="number" step="0.1" min="0" value="{_value(d.height_cm if d else '')}"></label>
            <label>Talla playera / blusa<input name="top_size" value="{_value(d.top_size if d else '')}"></label>
            <label>Talla pantalón / falda<input name="bottom_size" value="{_value(d.bottom_size if d else '')}"></label>
            <label>Talla suéter / chamarra<input name="sweater_size" value="{_value(d.sweater_size if d else '')}"></label>
            <label>Número de calzado<input name="shoe_size" value="{_value(d.shoe_size if d else '')}"></label>
            <label style="grid-column:1/-1">Observaciones de uniforme<textarea name="uniform_notes" rows="3">{_value(d.uniform_notes if d else '')}</textarea></label>
            <div><button>Guardar cambios</button></div>
            <div><a href="/students" style="display:block;padding:10px;text-align:center">Cancelar</a></div>
          </form>
        </div>'''
        return core.page('Editar alumno', body)
