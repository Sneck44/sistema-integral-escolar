import re
from html import escape

from flask import request, session, redirect, flash

import app as core
import multi_user


GROUPS = [
    ('1.º', 'A'), ('1.º', 'B'), ('1.º', 'C'),
    ('2.º', 'A'), ('2.º', 'B'), ('2.º', 'C'),
    ('3.º', 'A'), ('3.º', 'B'), ('3.º', 'C'),
]


class TeacherGroupAccess(core.db.Model):
    __tablename__ = 'teacher_group_access'
    id = core.db.Column(core.db.Integer, primary_key=True)
    user_id = core.db.Column(core.db.Integer, core.db.ForeignKey('user.id'), unique=True, nullable=False)
    grade = core.db.Column(core.db.String(20), nullable=False)
    group_name = core.db.Column(core.db.String(20), nullable=False)


def _access(user_id):
    if not user_id:
        return None
    return TeacherGroupAccess.query.filter_by(user_id=user_id).first()


def _current_config():
    return core.Config.query.order_by(core.Config.id).first()


def _same_group(access, cfg):
    if not access or not cfg:
        return False
    return (access.grade or '').strip() == (cfg.grade or '').strip() and (access.group_name or '').strip().upper() == (cfg.group or '').strip().upper()


def _group_label(access):
    return f'{access.grade} {access.group_name}' if access else 'Sin grupo asignado'


def _options(selected=None):
    current = ((selected.grade, selected.group_name) if selected else None)
    parts = ['<option value="">— Seleccionar grupo —</option>']
    for grade, group_name in GROUPS:
        value = f'{grade}|{group_name}'
        sel = ' selected' if current == (grade, group_name) else ''
        parts.append(f'<option value="{escape(value)}"{sel}>{escape(grade)} {escape(group_name)}</option>')
    return ''.join(parts)


def _inject_group_controls(html):
    if '/users/' not in html or 'Guardar permisos' not in html:
        return html

    pattern = re.compile(
        r'(<form method="post" action="/users/(\d+)/update"[^>]*>.*?</form>)',
        re.S,
    )

    def repl(match):
        original = match.group(1)
        user_id = int(match.group(2))
        profile = multi_user._profile(user_id)
        if not profile:
            return original
        access = _access(user_id)
        disabled = '' if profile.role == 'DOCENTE' else ' disabled'
        note = (
            f'<small style="color:#746a6d">Grupo autorizado: <b>{escape(_group_label(access))}</b></small>'
            if profile.role == 'DOCENTE'
            else '<small style="color:#746a6d">La asignación de grupo se usa únicamente para docentes.</small>'
        )
        control = f'''
        <form method="post" action="/users/{user_id}/group-access" style="display:grid;gap:7px;min-width:190px;margin-top:8px;padding-top:8px;border-top:1px solid #eee8e6">
          <label>Grupo autorizado
            <select name="group_access"{disabled}>{_options(access)}</select>
          </label>
          {note}
          <button{disabled}>Guardar grupo</button>
        </form>'''
        return original + control

    html = pattern.sub(repl, html)
    return html


def install(app):
    try:
        with app.app_context():
            core.db.create_all()
    except Exception:
        pass

    @app.before_request
    def enforce_teacher_single_group():
        uid = session.get('uid')
        if not uid:
            return None
        profile = multi_user._profile(uid)
        if not profile or not profile.active or profile.role != 'DOCENTE':
            return None

        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return None
        if request.path.startswith('/account/password'):
            return None
        # Clubes y deportes tienen su propio control de autorización por docente,
        # club/deporte y grupo, administrado desde el módulo correspondiente.
        if request.path.startswith('/clubs'):
            return None

        access = _access(uid)
        if not access:
            flash('Tu cuenta docente aún no tiene un grupo autorizado. Solicita al administrador que te asigne uno.')
            return redirect(request.referrer or '/')

        cfg = _current_config()
        if not _same_group(access, cfg):
            active = f'{cfg.grade} {cfg.group}' if cfg else 'sin configurar'
            flash(f'No tienes permiso para modificar el grupo {active}. Tu grupo autorizado es {_group_label(access)}.')
            return redirect(request.referrer or '/')
        return None

    @app.route('/users/<int:user_id>/group-access', methods=['POST'])
    def save_teacher_group_access(user_id):
        if not multi_user._is_admin():
            flash('Solo el administrador puede asignar grupos a docentes.')
            return redirect('/')

        profile = multi_user._profile(user_id)
        if not profile:
            flash('Usuario no encontrado.')
            return redirect('/users')
        if profile.role != 'DOCENTE':
            flash('La asignación de grupo solo aplica a usuarios con rol Docente.')
            return redirect('/users')

        raw = request.form.get('group_access', '').strip()
        valid = {f'{g}|{n}': (g, n) for g, n in GROUPS}
        if raw not in valid:
            flash('Selecciona un grupo válido para el docente.')
            return redirect('/users')

        grade, group_name = valid[raw]
        access = _access(user_id)
        if access is None:
            access = TeacherGroupAccess(user_id=user_id, grade=grade, group_name=group_name)
            core.db.session.add(access)
        else:
            access.grade = grade
            access.group_name = group_name
        core.db.session.commit()
        flash(f'Grupo autorizado actualizado: {grade} {group_name}.')
        return redirect('/users')

    @app.after_request
    def teacher_group_permissions_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        uid = session.get('uid')
        if not uid:
            return response
        profile = multi_user._profile(uid)
        html = response.get_data(as_text=True)

        if request.path == '/users' and profile and profile.role == 'ADMIN':
            html = _inject_group_controls(html)

        if profile and profile.role == 'DOCENTE':
            access = _access(uid)
            label = escape(_group_label(access))
            role_text = f'Rol: {escape(multi_user._role_label(profile.role))}'
            target = f'<small>{role_text}</small>'
            if target in html and 'Grupo autorizado:' not in html:
                html = html.replace(target, target + f'<small style="display:block">Grupo autorizado: {label}</small>', 1)

        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
