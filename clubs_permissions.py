import re
from html import escape

from flask import request, session, redirect, flash

import app as core
import multi_user
import clubs_sports
import teacher_group_permissions as tgp
import admin_ui_finalizer


class ClubEditAuthorization(core.db.Model):
    __tablename__ = 'club_edit_authorization'
    id = core.db.Column(core.db.Integer, primary_key=True)
    teacher_user_id = core.db.Column(core.db.Integer, nullable=False, unique=True, index=True)
    club_id = core.db.Column(core.db.Integer, nullable=False, unique=True, index=True)
    group_code = core.db.Column(core.db.String(8), nullable=False)
    active = core.db.Column(core.db.Boolean, default=True, nullable=False)


GROUPS = [
    ('1A', '1.º A'), ('1B', '1.º B'), ('1C', '1.º C'),
    ('2A', '2.º A'), ('2B', '2.º B'), ('2C', '2.º C'),
    ('3A', '3.º A'), ('3B', '3.º B'), ('3C', '3.º C'),
]


def _profile():
    uid = session.get('uid')
    return multi_user._profile(uid) if uid else None


def _is_admin():
    p = _profile()
    return bool(p and p.active and p.role == 'ADMIN')


def _group_code_for_access(access):
    if not access:
        return None
    digits = ''.join(ch for ch in (access.grade or '') if ch.isdigit())
    code = f'{digits}{(access.group_name or "").strip().upper()}'
    return code if code in dict(GROUPS) else None


def _authorization_for_teacher(uid):
    if not uid:
        return None
    return ClubEditAuthorization.query.filter_by(
        teacher_user_id=uid,
        active=True,
    ).first()


def _can_edit_club(club_id):
    p = _profile()
    if not p or not p.active:
        return False
    if p.role == 'ADMIN':
        return True
    if p.role != 'DOCENTE':
        return False
    auth = _authorization_for_teacher(session.get('uid'))
    if not auth or auth.club_id != club_id:
        return False
    return _group_code_for_access(tgp._access(session.get('uid'))) == auth.group_code


def _patched_allowed(club=None):
    p = _profile()
    if not p or not p.active:
        return False
    if request.method == 'GET':
        return True
    if p.role == 'ADMIN':
        return True
    return bool(club and _can_edit_club(club.id))


def _patched_clubs_for_user():
    return clubs_sports.ClubSport.query.filter_by(active=True).order_by(clubs_sports.ClubSport.name).all()


def _club_id_from_path(path):
    m = re.match(r'^/clubs/(\d+)(?:/|$)', path or '')
    return int(m.group(1)) if m else None


def _teacher_options(selected=None):
    rows = multi_user.UserProfile.query.filter_by(role='DOCENTE', active=True).order_by(multi_user.UserProfile.full_name).all()
    return ''.join(
        f'<option value="{p.user_id}" {"selected" if p.user_id == selected else ""}>{escape(p.full_name or str(p.user_id))}</option>'
        for p in rows
    )


def _club_options(selected=None):
    rows = clubs_sports.ClubSport.query.filter_by(active=True).order_by(clubs_sports.ClubSport.name).all()
    return ''.join(
        f'<option value="{c.id}" {"selected" if c.id == selected else ""}>{escape(c.name)} · {escape(c.kind)}</option>'
        for c in rows
    )


def _group_options(selected=None):
    return ''.join(
        f'<option value="{code}" {"selected" if code == selected else ""}>{escape(label)}</option>'
        for code, label in GROUPS
    )


def _admin_panel():
    auths = ClubEditAuthorization.query.filter_by(active=True).order_by(ClubEditAuthorization.id).all()
    profile_by_uid = {p.user_id: p for p in multi_user.UserProfile.query.all()}
    clubs = {c.id: c for c in clubs_sports.ClubSport.query.all()}
    rows = ''
    for a in auths:
        p = profile_by_uid.get(a.teacher_user_id)
        c = clubs.get(a.club_id)
        rows += f'''<tr><td>{escape((p.full_name if p else '') or str(a.teacher_user_id))}</td><td>{escape(c.name if c else 'Club no disponible')}</td><td>{escape(dict(GROUPS).get(a.group_code, a.group_code))}</td><td><form method="post" action="/clubs/permissions/{a.id}/delete"><button class="btn alt">Revocar</button></form></td></tr>'''
    return f'''
    <div class="card" id="club-permissions-admin">
      <h2>Autorizaciones de docentes</h2>
      <p class="muted">Cada docente puede modificar únicamente un club o deporte y el grupo autorizado por el administrador. Todos los demás usuarios conservan acceso de consulta.</p>
      <form method="post" action="/clubs/permissions/save" class="grid">
        <div><label>Docente</label><select name="teacher_user_id" required><option value="">Seleccionar…</option>{_teacher_options()}</select></div>
        <div><label>Club o deporte autorizado</label><select name="club_id" required><option value="">Seleccionar…</option>{_club_options()}</select></div>
        <div><label>Grupo autorizado</label><select name="group_code" required><option value="">Seleccionar…</option>{_group_options()}</select></div>
        <div style="align-self:end"><button>Guardar autorización</button></div>
      </form>
      <div class="scroll" style="margin-top:16px"><table><tr><th>Docente</th><th>Club / deporte</th><th>Grupo</th><th>Acción</th></tr>{rows or '<tr><td colspan="4">Aún no hay autorizaciones.</td></tr>'}</table></div>
    </div>'''


def _decorate_clubs_page(html):
    p = _profile()
    if not p or not p.active:
        return html
    if request.path == '/clubs':
        if p.role == 'ADMIN':
            marker = '<div class="card scroll">'
            if marker in html and 'id="club-permissions-admin"' not in html:
                html = html.replace(marker, _admin_panel() + marker, 1)
        else:
            html = re.sub(r'<form method="post" action="/clubs/create".*?</form>', '', html, count=1, flags=re.S)
            if p.role == 'DOCENTE':
                auth = _authorization_for_teacher(session.get('uid'))
                if auth:
                    club = core.db.session.get(clubs_sports.ClubSport, auth.club_id)
                    label = club.name if club else 'Club no disponible'
                    note = f'<div class="card"><b>Autorización vigente:</b> {escape(label)} · {escape(dict(GROUPS).get(auth.group_code, auth.group_code))}. Solo este espacio puede ser modificado por tu cuenta.</div>'
                else:
                    note = '<div class="card"><b>Sin autorización de edición.</b> Puedes consultar el módulo, pero el administrador debe asignarte un club o deporte y un grupo para poder modificarlo.</div>'
                html = html.replace('<div class="card scroll">', note + '<div class="card scroll">', 1)
    elif request.path.startswith('/clubs/') and p.role != 'ADMIN':
        cid = _club_id_from_path(request.path)
        editable = bool(cid and _can_edit_club(cid))
        if not editable:
            html = html.replace('</head>', '<style id="clubs-readonly">form[method="post"] button{display:none!important}.readonly-note{background:#fff4d8;border:1px solid #e8c979;padding:11px 14px;border-radius:10px;margin-bottom:14px;font-weight:750}</style></head>', 1)
            html = html.replace('<main>', '<main><div class="readonly-note">Modo consulta: tu usuario puede visualizar esta información, pero no modificar este club o deporte.</div>', 1)
    return html


def _patch_menu():
    original = admin_ui_finalizer._reorder_sidebar
    if getattr(original, '_clubs_menu_patch', False):
        return

    def wrapped(html):
        if '<nav class="side-nav">' in html and 'href="/clubs"' not in html:
            marker = '</nav>'
            link = '<a class="nav-link" href="/clubs"><span class="nav-icon">◉</span><span>Evaluación clubes y deportes</span></a>'
            html = html.replace(marker, link + marker, 1)
        out = original(html)
        match = re.search(r'<nav class="side-nav">(.*?)</nav>', out, flags=re.S)
        if not match:
            return out
        nav = match.group(1)
        club_match = re.search(r'<a\b[^>]*href="/clubs"[^>]*>.*?</a>', nav, flags=re.S)
        if not club_match:
            return out
        club_anchor = club_match.group(0)
        if request.path.startswith('/clubs'):
            club_anchor = club_anchor.replace('class="nav-link"', 'class="nav-link active"', 1)
        nav = nav[:club_match.start()] + nav[club_match.end():]
        section = '<div class="nav-section-label">Seguimiento y convivencia</div>'
        if section in nav:
            nav = nav.replace(section, club_anchor + section, 1)
        else:
            nav += club_anchor
        return out[:match.start(1)] + nav + out[match.end(1):]

    wrapped._clubs_menu_patch = True
    admin_ui_finalizer._reorder_sidebar = wrapped


def install(app):
    with app.app_context():
        core.db.create_all()

    clubs_sports._allowed = _patched_allowed
    clubs_sports._clubs_for_user = _patched_clubs_for_user
    _patch_menu()

    @app.before_request
    def protect_club_writes():
        if not request.path.startswith('/clubs') or request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return None
        p = _profile()
        if not p or not p.active:
            return redirect('/login')
        if p.role == 'ADMIN':
            return None
        cid = _club_id_from_path(request.path)
        if p.role == 'DOCENTE' and cid and _can_edit_club(cid):
            return None
        flash('Este apartado es de consulta para tu cuenta. Solo el administrador puede autorizar a un docente para modificar un club o deporte y su grupo.')
        return redirect(request.referrer or '/clubs')

    @app.post('/clubs/permissions/save')
    def save_club_permission():
        if not _is_admin():
            return redirect('/clubs')
        try:
            teacher_uid = int(request.form.get('teacher_user_id', '0'))
            club_id = int(request.form.get('club_id', '0'))
        except ValueError:
            teacher_uid = club_id = 0
        group_code = request.form.get('group_code', '').strip().upper()
        p = multi_user._profile(teacher_uid)
        club = core.db.session.get(clubs_sports.ClubSport, club_id)
        if not p or p.role != 'DOCENTE' or not p.active or not club or group_code not in dict(GROUPS):
            flash('Selecciona un docente activo, un club/deporte y un grupo válidos.')
            return redirect('/clubs')

        for old in ClubEditAuthorization.query.filter(
            (ClubEditAuthorization.teacher_user_id == teacher_uid) | (ClubEditAuthorization.club_id == club_id)
        ).all():
            core.db.session.delete(old)
        auth = ClubEditAuthorization(teacher_user_id=teacher_uid, club_id=club_id, group_code=group_code, active=True)
        core.db.session.add(auth)

        grade = f'{group_code[0]}.º'
        group_name = group_code[1]
        access = tgp._access(teacher_uid)
        if access is None:
            access = tgp.TeacherGroupAccess(user_id=teacher_uid, grade=grade, group_name=group_name)
            core.db.session.add(access)
        else:
            access.grade = grade
            access.group_name = group_name
        core.db.session.commit()
        flash(f'Autorización guardada: {p.full_name} puede modificar {club.name} en el grupo {dict(GROUPS)[group_code]}.')
        return redirect('/clubs')

    @app.post('/clubs/permissions/<int:auth_id>/delete')
    def delete_club_permission(auth_id):
        if not _is_admin():
            return redirect('/clubs')
        row = core.db.session.get(ClubEditAuthorization, auth_id)
        if row:
            core.db.session.delete(row)
            core.db.session.commit()
            flash('Autorización de club/deporte revocada.')
        return redirect('/clubs')

    @app.after_request
    def clubs_permissions_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = _decorate_clubs_page(response.get_data(as_text=True))
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
