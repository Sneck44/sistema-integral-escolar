from datetime import datetime
from html import escape
from flask import request, redirect, session, flash

import app as core


def _auth():
    if not session.get('uid'):
        return redirect('/login')
    return None


def _activity_cleanup(activity_id):
    core.Grade.query.filter_by(activity_id=activity_id).delete(synchronize_session=False)
    try:
        from rubric_ai import Rubric, RubricAssessment
        rubric = Rubric.query.filter_by(activity_id=activity_id).first()
        if rubric:
            RubricAssessment.query.filter_by(rubric_id=rubric.id).delete(synchronize_session=False)
            core.db.session.delete(rubric)
    except Exception:
        pass


def _student_cleanup(student_id):
    core.Grade.query.filter_by(student_id=student_id).delete(synchronize_session=False)
    core.Attendance.query.filter_by(student_id=student_id).delete(synchronize_session=False)
    core.Incident.query.filter_by(student_id=student_id).delete(synchronize_session=False)
    try:
        from student_details import StudentDetails
        StudentDetails.query.filter_by(student_id=student_id).delete(synchronize_session=False)
    except Exception:
        pass
    try:
        from diagnostic import StudentDiagnostic
        StudentDiagnostic.query.filter_by(student_id=student_id).delete(synchronize_session=False)
    except Exception:
        pass
    try:
        from rubric_ai import RubricAssessment
        RubricAssessment.query.filter_by(student_id=student_id).delete(synchronize_session=False)
    except Exception:
        pass


def install(app):
    # ---------- CENTRO DE GESTIÓN ----------
    @app.route('/data-management')
    def data_management():
        r = _auth()
        if r: return r
        cards = [
            ('Alumnos', '/students', 'Editar expediente, tutor, teléfono, peso, talla y eliminar alumno.'),
            ('Asignaturas', '/subjects', 'Crear, editar y eliminar asignaturas.'),
            ('Actividades', '/activities', 'Crear, editar y eliminar actividades.'),
            ('Calificaciones', '/grades/manage', 'Editar o eliminar calificaciones individuales.'),
            ('Asistencia', '/attendance/manage', 'Editar o eliminar registros de asistencia.'),
            ('Convivencia', '/incidents/manage', 'Editar o eliminar incidencias.'),
            ('Diagnóstico', '/diagnostic', 'Modificar diagnóstico y eliminar registros individuales.'),
            ('Rúbricas', '/rubrics', 'Editar rúbricas y eliminar las que ya no necesites.'),
            ('Usuarios', '/users', 'Modificar permisos, contraseñas, activar, desactivar o eliminar cuentas.'),
            ('Configuración', '/config', 'Modificar datos generales del grupo y ciclo escolar.'),
        ]
        html=''.join(f'<div class="card"><h2>{escape(t)}</h2><p>{escape(d)}</p><a href="{u}" style="font-weight:800">Administrar →</a></div>' for t,u,d in cards)
        return core.page('Gestión de datos', f'<h1>Gestión de datos</h1><p class="muted">Desde aquí puedes revisar, corregir y eliminar la información registrada. Las eliminaciones que afectan datos relacionados requieren confirmación.</p><div class="grid">{html}</div>')

    # ---------- ASIGNATURAS ----------
    def subjects_crud():
        r=_auth()
        if r:return r
        if request.method=='POST':
            name=request.form.get('name','').strip(); field=request.form.get('field','').strip()
            if not name: flash('Escribe el nombre de la asignatura.')
            else:
                core.db.session.add(core.Subject(name=name,field=field or core.FIELDS[0])); core.db.session.commit(); flash('Asignatura agregada.')
            return redirect('/subjects')
        opts=''.join(f'<option>{escape(x)}</option>' for x in core.FIELDS)
        rows=''
        for s in core.Subject.query.order_by(core.Subject.name).all():
            count=core.Activity.query.filter_by(subject_id=s.id).count()
            rows+=f'<tr><td><b>{escape(s.name)}</b></td><td>{escape(s.field)}</td><td>{count}</td><td><a href="/subjects/{s.id}/edit">Editar</a> · <a href="/subjects/{s.id}/delete" style="color:#a01818">Eliminar</a></td></tr>'
        return core.page('Asignaturas',f'''<h1>Asignaturas</h1><div class="card"><form method="post" class="grid"><label>Asignatura<input name="name" required></label><label>Campo formativo<select name="field">{opts}</select></label><div><button>Agregar</button></div></form></div><div class="card scroll"><table><tr><th>Asignatura</th><th>Campo</th><th>Actividades</th><th>Acciones</th></tr>{rows}</table></div>''')
    app.view_functions['subjects']=subjects_crud

    @app.route('/subjects/<int:sid>/edit',methods=['GET','POST'])
    def subject_edit(sid):
        r=_auth()
        if r:return r
        s=core.db.session.get(core.Subject,sid)
        if not s:return redirect('/subjects')
        if request.method=='POST':
            s.name=request.form.get('name','').strip(); s.field=request.form.get('field',s.field); core.db.session.commit(); flash('Asignatura actualizada.'); return redirect('/subjects')
        opts=''.join(f'<option {"selected" if x==s.field else ""}>{escape(x)}</option>' for x in core.FIELDS)
        return core.page('Editar asignatura',f'<h1>Editar asignatura</h1><div class="card"><form method="post" class="grid"><label>Nombre<input name="name" value="{escape(s.name)}" required></label><label>Campo<select name="field">{opts}</select></label><div><button>Guardar cambios</button></div></form></div>')

    @app.route('/subjects/<int:sid>/delete',methods=['GET','POST'])
    def subject_delete(sid):
        r=_auth()
        if r:return r
        s=core.db.session.get(core.Subject,sid)
        if not s:return redirect('/subjects')
        activities=core.Activity.query.filter_by(subject_id=s.id).all()
        if request.method=='POST' and request.form.get('confirm')=='ELIMINAR':
            for a in activities:
                _activity_cleanup(a.id); core.db.session.delete(a)
            core.db.session.delete(s); core.db.session.commit(); flash('Asignatura y registros relacionados eliminados.'); return redirect('/subjects')
        warning=f'Esta asignatura tiene {len(activities)} actividad(es). También se eliminarán sus calificaciones y rúbricas relacionadas.' if activities else 'La asignatura no tiene actividades relacionadas.'
        return core.page('Eliminar asignatura',f'<h1>Eliminar asignatura</h1><div class="card danger"><h2>{escape(s.name)}</h2><p>{escape(warning)}</p><form method="post"><label>Escribe ELIMINAR para confirmar<input name="confirm" required></label><br><br><button style="background:#a01818">Eliminar definitivamente</button></form></div>')

    # ---------- ALUMNOS ----------
    @app.route('/students/<int:sid>/delete',methods=['GET','POST'])
    def student_delete(sid):
        r=_auth()
        if r:return r
        s=core.db.session.get(core.Student,sid)
        if not s:return redirect('/students')
        if request.method=='POST' and request.form.get('confirm')=='ELIMINAR':
            _student_cleanup(s.id); core.db.session.delete(s); core.db.session.commit(); flash('Alumno y registros relacionados eliminados.'); return redirect('/students')
        return core.page('Eliminar alumno',f'<h1>Eliminar alumno</h1><div class="card danger"><h2>{escape(s.full_name)}</h2><p>Se eliminarán también sus calificaciones, asistencia, incidencias, diagnóstico, tallas y evaluaciones de rúbrica. Esta acción no se puede deshacer.</p><form method="post"><label>Escribe ELIMINAR para confirmar<input name="confirm" required></label><br><br><button style="background:#a01818">Eliminar definitivamente</button></form></div>')

    # ---------- CALIFICACIONES ----------
    @app.route('/grades/manage')
    def grades_manage():
        r=_auth()
        if r:return r
        rows=''
        for g in core.Grade.query.order_by(core.Grade.activity_id,core.Grade.student_id).all():
            s=core.db.session.get(core.Student,g.student_id); a=core.db.session.get(core.Activity,g.activity_id)
            if not s or not a: continue
            val=g.code or ('' if g.score is None else g.score)
            rows+=f'<tr><td>{escape(s.full_name)}</td><td>{escape(a.name)}</td><td>{escape(str(val))}</td><td><a href="/grades/record/{g.id}/edit">Editar</a> · <form method="post" action="/grades/record/{g.id}/delete" style="display:inline" onsubmit="return confirm(\'¿Eliminar esta calificación?\')"><button style="width:auto;background:none;color:#a01818;padding:0">Eliminar</button></form></td></tr>'
        return core.page('Gestionar calificaciones',f'<h1>Gestionar calificaciones</h1><div class="card scroll"><table><tr><th>Alumno</th><th>Actividad</th><th>Calificación</th><th>Acciones</th></tr>{rows}</table></div>')

    @app.route('/grades/record/<int:gid>/edit',methods=['GET','POST'])
    def grade_edit(gid):
        r=_auth()
        if r:return r
        g=core.db.session.get(core.Grade,gid)
        if not g:return redirect('/grades/manage')
        s=core.db.session.get(core.Student,g.student_id); a=core.db.session.get(core.Activity,g.activity_id)
        if request.method=='POST':
            raw=request.form.get('value','').strip()
            if raw.upper() in ('NP','NE','J','P'): g.score=None; g.code=raw.upper()
            elif raw=='': g.score=None; g.code=''
            else:
                try:g.score=float(raw);g.code=''
                except: flash('Valor no válido.'); return redirect(request.path)
            core.db.session.commit(); flash('Calificación actualizada.'); return redirect('/grades/manage')
        val=g.code or ('' if g.score is None else g.score)
        return core.page('Editar calificación',f'<h1>Editar calificación</h1><div class="card"><p><b>{escape(s.full_name if s else "")}</b> · {escape(a.name if a else "")}</p><form method="post"><label>Calificación o código<input name="value" value="{escape(str(val))}"></label><br><br><button>Guardar</button></form></div>')

    @app.route('/grades/record/<int:gid>/delete',methods=['POST'])
    def grade_delete(gid):
        r=_auth()
        if r:return r
        g=core.db.session.get(core.Grade,gid)
        if g: core.db.session.delete(g); core.db.session.commit(); flash('Calificación eliminada.')
        return redirect('/grades/manage')

    # ---------- ASISTENCIA ----------
    @app.route('/attendance/manage')
    def attendance_manage():
        r=_auth()
        if r:return r
        rows=''
        for a in core.Attendance.query.order_by(core.Attendance.day.desc(),core.Attendance.student_id).all():
            s=core.db.session.get(core.Student,a.student_id)
            rows+=f'<tr><td>{a.day.strftime("%d/%m/%Y")}</td><td>{escape(s.full_name if s else "")}</td><td>{escape(a.state)}</td><td>{escape(a.notes or "")}</td><td><a href="/attendance/record/{a.id}/edit">Editar</a> · <form method="post" action="/attendance/record/{a.id}/delete" style="display:inline" onsubmit="return confirm(\'¿Eliminar este registro de asistencia?\')"><button style="width:auto;background:none;color:#a01818;padding:0">Eliminar</button></form></td></tr>'
        return core.page('Gestionar asistencia',f'<h1>Gestionar asistencia</h1><div class="card"><a href="/attendance">← Capturar asistencia</a></div><div class="card scroll"><table><tr><th>Fecha</th><th>Alumno</th><th>Estado</th><th>Observaciones</th><th>Acciones</th></tr>{rows}</table></div>')

    @app.route('/attendance/record/<int:rid>/edit',methods=['GET','POST'])
    def attendance_edit(rid):
        r=_auth()
        if r:return r
        a=core.db.session.get(core.Attendance,rid)
        if not a:return redirect('/attendance/manage')
        s=core.db.session.get(core.Student,a.student_id)
        if request.method=='POST':
            try:a.day=datetime.strptime(request.form.get('day'),'%Y-%m-%d').date()
            except:pass
            a.state=request.form.get('state',a.state);a.notes=request.form.get('notes','').strip();core.db.session.commit();flash('Asistencia actualizada.');return redirect('/attendance/manage')
        states=['PRESENTE','FALTA','RETARDO','JUSTIFICADA'];opts=''.join(f'<option {"selected" if x==a.state else ""}>{x}</option>' for x in states)
        return core.page('Editar asistencia',f'<h1>Editar asistencia</h1><div class="card"><p><b>{escape(s.full_name if s else "")}</b></p><form method="post" class="grid"><label>Fecha<input type="date" name="day" value="{a.day.isoformat()}" required></label><label>Estado<select name="state">{opts}</select></label><label>Observaciones<input name="notes" value="{escape(a.notes or "")}"></label><div><button>Guardar</button></div></form></div>')

    @app.route('/attendance/record/<int:rid>/delete',methods=['POST'])
    def attendance_delete(rid):
        r=_auth()
        if r:return r
        a=core.db.session.get(core.Attendance,rid)
        if a:core.db.session.delete(a);core.db.session.commit();flash('Registro de asistencia eliminado.')
        return redirect('/attendance/manage')

    # ---------- INCIDENCIAS ----------
    @app.route('/incidents/manage')
    def incidents_manage():
        r=_auth()
        if r:return r
        rows=''
        for i in core.Incident.query.order_by(core.Incident.day.desc()).all():
            rows+=f'<tr><td>{i.day.strftime("%d/%m/%Y") if i.day else ""}</td><td>{escape(i.student.full_name if i.student else "")}</td><td>{escape(i.category)}</td><td>{escape(i.status)}</td><td><a href="/incidents/{i.id}/edit">Editar</a> · <form method="post" action="/incidents/{i.id}/delete" style="display:inline" onsubmit="return confirm(\'¿Eliminar esta incidencia?\')"><button style="width:auto;background:none;color:#a01818;padding:0">Eliminar</button></form></td></tr>'
        return core.page('Gestionar convivencia',f'<h1>Gestionar incidencias</h1><div class="card"><a href="/incidents">← Registrar incidencia</a></div><div class="card scroll"><table><tr><th>Fecha</th><th>Alumno</th><th>Categoría</th><th>Estado</th><th>Acciones</th></tr>{rows}</table></div>')

    @app.route('/incidents/<int:iid>/edit',methods=['GET','POST'])
    def incident_edit(iid):
        r=_auth()
        if r:return r
        i=core.db.session.get(core.Incident,iid)
        if not i:return redirect('/incidents/manage')
        students=core.Student.query.order_by(core.Student.list_no).all()
        if request.method=='POST':
            try:i.day=datetime.strptime(request.form.get('day'),'%Y-%m-%d').date()
            except:pass
            i.student_id=int(request.form.get('student_id',i.student_id));i.category=request.form.get('category','').strip();i.description=request.form.get('description','').strip();i.action=request.form.get('action','').strip();i.status=request.form.get('status','ABIERTA');core.db.session.commit();flash('Incidencia actualizada.');return redirect('/incidents/manage')
        so=''.join(f'<option value="{s.id}" {"selected" if s.id==i.student_id else ""}>{escape(s.full_name)}</option>' for s in students)
        st=''.join(f'<option {"selected" if x==i.status else ""}>{x}</option>' for x in ['ABIERTA','EN SEGUIMIENTO','CERRADA'])
        return core.page('Editar incidencia',f'<h1>Editar incidencia</h1><div class="card"><form method="post" class="grid"><label>Fecha<input type="date" name="day" value="{i.day.isoformat() if i.day else ""}"></label><label>Alumno<select name="student_id">{so}</select></label><label>Categoría<input name="category" value="{escape(i.category)}"></label><label>Estado<select name="status">{st}</select></label><label style="grid-column:1/-1">Descripción<textarea name="description">{escape(i.description)}</textarea></label><label style="grid-column:1/-1">Acción / acuerdo<textarea name="action">{escape(i.action or "")}</textarea></label><div><button>Guardar cambios</button></div></form></div>')

    @app.route('/incidents/<int:iid>/delete',methods=['POST'])
    def incident_delete(iid):
        r=_auth()
        if r:return r
        i=core.db.session.get(core.Incident,iid)
        if i:core.db.session.delete(i);core.db.session.commit();flash('Incidencia eliminada.')
        return redirect('/incidents/manage')

    # ---------- DIAGNÓSTICO ----------
    @app.route('/diagnostic/<int:sid>/delete',methods=['POST'])
    def diagnostic_delete(sid):
        r=_auth()
        if r:return r
        try:
            from diagnostic import StudentDiagnostic
            d=StudentDiagnostic.query.filter_by(student_id=sid).first()
            if d:core.db.session.delete(d);core.db.session.commit();flash('Diagnóstico individual eliminado.')
        except Exception:pass
        return redirect('/diagnostic')

    # ---------- RÚBRICAS ----------
    @app.route('/rubrics/<int:rid>/delete',methods=['GET','POST'])
    def rubric_delete(rid):
        r=_auth()
        if r:return r
        try:
            from rubric_ai import Rubric,RubricAssessment
            rubric=core.db.session.get(Rubric,rid)
        except Exception:
            rubric=None
        if not rubric:return redirect('/rubrics')
        if request.method=='POST' and request.form.get('confirm')=='ELIMINAR':
            RubricAssessment.query.filter_by(rubric_id=rid).delete(synchronize_session=False);core.db.session.delete(rubric);core.db.session.commit();flash('Rúbrica y evaluaciones asociadas eliminadas.');return redirect('/rubrics')
        return core.page('Eliminar rúbrica',f'<h1>Eliminar rúbrica</h1><div class="card danger"><h2>{escape(rubric.title)}</h2><p>Se eliminarán también las evaluaciones realizadas con esta rúbrica.</p><form method="post"><label>Escribe ELIMINAR para confirmar<input name="confirm" required></label><br><br><button style="background:#a01818">Eliminar definitivamente</button></form></div>')

    # ---------- USUARIOS ----------
    @app.route('/users/<int:uid>/delete',methods=['GET','POST'])
    def user_delete(uid):
        r=_auth()
        if r:return r
        try:
            import multi_user
            if not multi_user._is_admin():flash('Solo el administrador puede eliminar usuarios.');return redirect('/')
            profile=multi_user.UserProfile.query.filter_by(user_id=uid).first()
        except Exception:
            profile=None
        user=core.db.session.get(core.User,uid)
        if not user:return redirect('/users')
        if uid==session.get('uid'):flash('No puedes eliminar tu propia cuenta mientras estás conectado.');return redirect('/users')
        if request.method=='POST' and request.form.get('confirm')=='ELIMINAR':
            if profile:core.db.session.delete(profile)
            core.db.session.delete(user);core.db.session.commit();flash('Usuario eliminado.');return redirect('/users')
        return core.page('Eliminar usuario',f'<h1>Eliminar usuario</h1><div class="card danger"><h2>{escape(user.username)}</h2><form method="post"><label>Escribe ELIMINAR para confirmar<input name="confirm" required></label><br><br><button style="background:#a01818">Eliminar cuenta</button></form></div>')

    # ---------- UI: accesos directos ----------
    @app.after_request
    def data_management_ui(response):
        if 'text/html' not in response.headers.get('Content-Type','') or not session.get('uid'):
            return response
        html=response.get_data(as_text=True)
        if 'href="/data-management"' not in html:
            marker='<a class="nav-link logout" href="/logout">'
            link='<a class="nav-link" href="/data-management"><span class="nav-icon">🛠️</span><span>Gestión de datos</span></a>'
            if marker in html:html=html.replace(marker,link+marker,1)
            else:
                marker2='<a href="/logout">Salir</a>'
                if marker2 in html:html=html.replace(marker2,'<a href="/data-management">Gestión de datos</a>'+marker2,1)
        if request.path=='/attendance' and '/attendance/manage' not in html:
            html=html.replace('</h1>','</h1><p><a href="/attendance/manage">🛠️ Editar o eliminar registros anteriores</a></p>',1)
        if request.path=='/incidents' and '/incidents/manage' not in html:
            html=html.replace('</h1>','</h1><p><a href="/incidents/manage">🛠️ Editar o eliminar incidencias anteriores</a></p>',1)
        if request.path=='/diagnostic' and '/diagnostic/' not in html:
            html=html.replace('</form>','</form><p class="muted">Para eliminar un diagnóstico individual, entra a Gestión de datos → Diagnóstico.</p>',1)
        if request.path.startswith('/students/') and request.path.endswith('/edit') and '/delete' not in html:
            sid=request.path.split('/')[2]
            html=html.replace('</main>',f'<div class="card danger"><h2>Eliminar alumno</h2><p>Esta opción elimina también sus registros relacionados.</p><a href="/students/{sid}/delete" style="color:#a01818;font-weight:800">Eliminar alumno definitivamente</a></div></main>',1)
        response.set_data(html);response.headers['Content-Length']=str(len(response.get_data()));return response
