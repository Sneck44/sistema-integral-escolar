from html import escape

from flask import request, session, redirect, flash, has_request_context
from sqlalchemy import event, select, exists, and_, delete
from sqlalchemy.orm import Session, with_loader_criteria

import app as core
import multi_user


GROUPS = [
    ('1A', '1.º', 'A'), ('1B', '1.º', 'B'), ('1C', '1.º', 'C'),
    ('2A', '2.º', 'A'), ('2B', '2.º', 'B'), ('2C', '2.º', 'C'),
    ('3A', '3.º', 'A'), ('3B', '3.º', 'B'), ('3C', '3.º', 'C'),
]
GROUP_MAP = {code: (grade, group_name) for code, grade, group_name in GROUPS}

# Datos que pertenecen a un grupo concreto. Usuarios, configuración institucional
# y permisos quedan fuera porque son globales al sistema.
SCOPED_TABLES = {
    'student', 'student_details', 'student_diagnostic',
    'subject', 'activity', 'grade', 'attendance', 'incident',
    'rubric', 'rubric_assessment',
}


class RecordGroup(core.db.Model):
    __tablename__ = 'record_group'
    id = core.db.Column(core.db.Integer, primary_key=True)
    entity_type = core.db.Column(core.db.String(60), nullable=False, index=True)
    entity_id = core.db.Column(core.db.Integer, nullable=False, index=True)
    group_code = core.db.Column(core.db.String(8), nullable=False, index=True)
    __table_args__ = (
        core.db.UniqueConstraint('entity_type', 'entity_id', name='uq_record_group_entity'),
    )


class GroupWorkspaceState(core.db.Model):
    __tablename__ = 'group_workspace_state'
    id = core.db.Column(core.db.Integer, primary_key=True)
    version = core.db.Column(core.db.Integer, default=1, nullable=False)


def _normalize_code(grade, group_name):
    g = (grade or '').strip()
    n = (group_name or '').strip().upper()
    for code, grade_value, group_value in GROUPS:
        if g == grade_value and n == group_value:
            return code
    digits = ''.join(ch for ch in g if ch.isdigit())
    candidate = f'{digits}{n}' if digits and n else ''
    return candidate if candidate in GROUP_MAP else '1A'


def active_group_code():
    code = session.get('active_group') if has_request_context() else None
    return code if code in GROUP_MAP else None


def active_group_tuple():
    code = active_group_code() or '1A'
    grade, group_name = GROUP_MAP[code]
    return grade, group_name


def active_group_label():
    grade, group_name = active_group_tuple()
    return f'{grade} {group_name}'


def _teacher_group_code(uid):
    try:
        import teacher_group_permissions as tgp
        access = tgp._access(uid)
        if access:
            return _normalize_code(access.grade, access.group_name)
    except Exception:
        pass
    return None


def _profile():
    uid = session.get('uid') if has_request_context() else None
    return multi_user._profile(uid) if uid else None


def _scoped_models():
    models = []
    try:
        for mapper in core.db.Model.registry.mappers:
            model = mapper.class_
            table = getattr(model, '__tablename__', None)
            if table in SCOPED_TABLES:
                models.append((table, model))
    except Exception:
        pass
    return models


def _default_group_from_config():
    try:
        c = core.Config.query.order_by(core.Config.id).first()
        if c:
            return _normalize_code(c.grade, c.group)
    except Exception:
        pass
    return '1A'


def _bootstrap_existing_records():
    # La primera vez, conserva todos los datos ya existentes dentro del grupo
    # que estaba configurado previamente. Los demás grupos comienzan limpios.
    state = core.db.session.get(GroupWorkspaceState, 1)
    if state:
        return
    default_code = _default_group_from_config()
    for table, model in _scoped_models():
        try:
            ids = core.db.session.execute(
                select(model.id), execution_options={'group_scope_disabled': True}
            ).scalars().all()
            if not ids:
                continue
            existing = set(core.db.session.execute(
                select(RecordGroup.entity_id).where(RecordGroup.entity_type == table),
                execution_options={'group_scope_disabled': True},
            ).scalars().all())
            for entity_id in ids:
                if entity_id not in existing:
                    core.db.session.add(RecordGroup(
                        entity_type=table,
                        entity_id=entity_id,
                        group_code=default_code,
                    ))
        except Exception:
            continue
    core.db.session.add(GroupWorkspaceState(id=1, version=1))
    core.db.session.commit()


def _workspace_selector(profile):
    code = active_group_code() or '1A'
    label = active_group_label()
    if profile and profile.role == 'DOCENTE':
        return (
            '<div class="workspace-picker workspace-locked" title="Grupo autorizado">'
            '<span class="workspace-caption">Grupo</span>'
            f'<strong>{escape(label)}</strong>'
            '</div>'
        )
    options = ''.join(
        f'<option value="{c}" {"selected" if c == code else ""}>{escape(g)} {escape(n)}</option>'
        for c, g, n in GROUPS
    )
    return (
        '<form class="workspace-picker" method="post" action="/workspace/group">'
        '<span class="workspace-caption">Grupo</span>'
        f'<select name="group_code" onchange="this.form.submit()">{options}</select>'
        '</form>'
    )


WORKSPACE_CSS = r'''
<style id="group-workspaces-v1">
.workspace-picker{display:flex;align-items:center;gap:8px;padding:7px 10px;border:1px solid rgba(202,164,95,.32);border-radius:16px;background:#fffaf4;box-shadow:0 5px 14px rgba(74,18,32,.05);min-height:44px}
.workspace-picker .workspace-caption{font-size:10px;text-transform:uppercase;letter-spacing:.55px;color:#8a6a2d;font-weight:800}
.workspace-picker select{width:auto!important;min-width:92px;padding:5px 24px 5px 8px!important;border:0!important;background:transparent!important;color:#5b1020!important;font-weight:850!important;box-shadow:none!important;cursor:pointer}
.workspace-picker strong{color:#5b1020;font-size:14px}.workspace-locked{padding-right:14px}
.workspace-mobile{display:none;margin:8px 12px 0;padding:9px 12px;border-radius:14px;background:#fff8ed;border:1px solid rgba(202,164,95,.28);color:#5b1020;font-weight:800;text-align:center}
.workspace-banner{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:11px 15px;margin:0 0 14px;border-radius:16px;background:linear-gradient(90deg,#fff9f1,#fff);border:1px solid rgba(202,164,95,.28);color:#5b1020}
.workspace-banner b{font-size:14px}.workspace-banner small{display:block;color:#806f73;margin-top:2px}
@media(max-width:980px){.workspace-picker{display:none}.workspace-mobile{display:block}}
</style>
'''


def _inject_workspace_ui(html):
    profile = _profile()
    if not profile:
        return html
    selector = _workspace_selector(profile)
    if '<div class="top-meta">' in html and 'class="workspace-picker' not in html:
        html = html.replace('<div class="top-meta">', '<div class="top-meta">' + selector, 1)
    if '<main class="wrap">' in html and 'workspace-banner' not in html:
        banner = (
            '<div class="workspace-banner">'
            f'<div><b>Entorno activo: {escape(active_group_label())}</b>'
            '<small>Los alumnos, calificaciones, asistencia, incidencias, diagnóstico, rúbricas y gráficas corresponden únicamente a este grupo.</small></div>'
            '</div>'
        )
        html = html.replace('<main class="wrap">', '<main class="wrap">' + banner, 1)
    if '<div class="mobile-brand">' in html and 'workspace-mobile' not in html:
        marker = '</div><main class="wrap">'
        mobile = f'<div class="workspace-mobile">Grupo activo · {escape(active_group_label())}</div>'
        html = html.replace(marker, '</div>' + mobile + '<main class="wrap">', 1)
    if '</head>' in html and 'id="group-workspaces-v1"' not in html:
        html = html.replace('</head>', WORKSPACE_CSS + '</head>', 1)
    return html


def install(app):
    try:
        with app.app_context():
            core.db.create_all()
    except Exception:
        pass

    @app.before_request
    def establish_active_workspace():
        uid = session.get('uid')
        if not uid:
            return None
        profile = multi_user._profile(uid)
        if not profile or not profile.active:
            return None
        if profile.role == 'DOCENTE':
            teacher_code = _teacher_group_code(uid)
            if teacher_code:
                session['active_group'] = teacher_code
            else:
                session.pop('active_group', None)
        elif session.get('active_group') not in GROUP_MAP:
            session['active_group'] = _default_group_from_config()
        _bootstrap_existing_records()
        return None

    @app.route('/workspace/group', methods=['POST'])
    def select_workspace_group():
        uid = session.get('uid')
        if not uid:
            return redirect('/login')
        profile = multi_user._profile(uid)
        if not profile or not profile.active:
            return redirect('/login')
        if profile.role == 'DOCENTE':
            code = _teacher_group_code(uid)
            if code:
                session['active_group'] = code
                flash(f'Tu cuenta docente está vinculada al grupo {active_group_label()}.')
            else:
                flash('Tu cuenta docente todavía no tiene un grupo asignado.')
            return redirect(request.referrer or '/')
        code = request.form.get('group_code', '').strip().upper()
        if code not in GROUP_MAP:
            flash('Selecciona un grupo válido.')
            return redirect(request.referrer or '/')
        session['active_group'] = code
        flash(f'Ahora estás trabajando con el grupo {active_group_label()}.')
        return redirect(request.referrer or '/')

    @app.after_request
    def group_workspace_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = _inject_workspace_ui(response.get_data(as_text=True))
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response


# Filtro ORM global: cualquier SELECT de los modelos académicos queda restringido
# al grupo activo de la sesión. Esto protege también accesos por URL directa.
@event.listens_for(Session, 'do_orm_execute')
def _scope_group_queries(orm_execute_state):
    if not orm_execute_state.is_select:
        return
    if orm_execute_state.execution_options.get('group_scope_disabled'):
        return
    if not has_request_context() or not session.get('uid'):
        return
    code = active_group_code()
    if not code:
        return
    statement = orm_execute_state.statement
    for table, model in _scoped_models():
        condition = exists(
            select(RecordGroup.id).where(and_(
                RecordGroup.entity_type == table,
                RecordGroup.entity_id == model.id,
                RecordGroup.group_code == code,
            ))
        )
        statement = statement.options(with_loader_criteria(model, condition, include_aliases=True))
    orm_execute_state.statement = statement


# Cada registro nuevo hereda automáticamente el grupo activo. Al eliminarlo,
# también se elimina su vínculo de grupo.
@event.listens_for(Session, 'after_flush')
def _tag_group_records(session_obj, flush_context):
    if not has_request_context() or not session.get('uid'):
        return
    code = active_group_code()
    if not code:
        return
    try:
        conn = session_obj.connection()
    except Exception:
        return
    model_tables = {model: table for table, model in _scoped_models()}
    for obj in list(session_obj.new):
        table = model_tables.get(type(obj))
        entity_id = getattr(obj, 'id', None)
        if not table or not entity_id:
            continue
        present = conn.execute(
            select(RecordGroup.id).where(and_(
                RecordGroup.entity_type == table,
                RecordGroup.entity_id == entity_id,
            ))
        ).first()
        if not present:
            conn.execute(RecordGroup.__table__.insert().values(
                entity_type=table,
                entity_id=entity_id,
                group_code=code,
            ))
    for obj in list(session_obj.deleted):
        table = model_tables.get(type(obj))
        entity_id = getattr(obj, 'id', None)
        if table and entity_id:
            conn.execute(delete(RecordGroup).where(and_(
                RecordGroup.entity_type == table,
                RecordGroup.entity_id == entity_id,
            )))
