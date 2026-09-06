import re
from html import escape

from flask import request, session, redirect, flash

import app as core
import multi_user
import clubs_sports
import teacher_group_permissions as tgp
import admin_ui_finalizer


class ClubDualAuthorization(core.db.Model):
    __tablename__ = 'club_dual_authorization'
    id = core.db.Column(core.db.Integer, primary_key=True)
    teacher_user_id = core.db.Column(core.db.Integer, nullable=False, unique=True, index=True)
    club_id = core.db.Column(core.db.Integer, nullable=True, unique=True, index=True)
    sport_id = core.db.Column(core.db.Integer, nullable=True, unique=True, index=True)
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
    return ClubDualAuthorization.query.filter_by(teacher_user_id=uid, active=True).first()


def _can_edit_club(club_id):
    p = _profile()
    if not p or not p.active:
        return False
    if p.role == 'ADMIN':
        return True
    if p.role != 'DOCENTE':
        return False
    auth = _authorization_for_teacher(session.get('uid'))
    if not auth:
        return False
    activity = core.db.session.get(clubs_sports.ClubSport, club_id)
    if not activity:
        return False
    kind = (activity.kind or 'CLUB').strip().upper()
    allowed_id = auth.sport_id if kind == 'DEPORTE' else auth.club_id
    if allowed_id != club_id:
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
    return clubs_sports.ClubSport.query.filter_by(active=True).order_by(clubs_sports.ClubSport.kind, clubs_sports.ClubSport.name).all()


def _club_id_from_path(path):
    m = re.match(r'^/clubs/(\d+)(?:/|$)', path or '')
    return int(m.group(1)) if m else None


def _teacher_options(selected=None):
    rows = multi_user.UserProfile.query.filter_by(role='DOCENTE', active=True).order_by(multi_user.UserProfile.full_name).all()
    return ''.join(
        f'<option value="{p.user_id}" {"selected" if p.user_id == selected else ""}>{escape(p.full_name or str(p.user_id))}</option>'
        for p in rows
    )


def _activity_options(kind, selected=None):
    rows = clubs_sports.ClubSport.query.filter_by(active=True, kind=kind).order_by(clubs_sports.ClubSport.name).all()
    parts = ['<option value="">Sin asignar todavía</option>']
    parts.extend(
        f'<option value="{c.id}" {"selected" if c.id == selected else ""}>{escape(c.name)}</option>'
        for c in rows
    )
    return ''.join(parts)


def _group_options(selected=None):
    return ''.join(
        f'<option value="{code}" {"selected" if code == selected else ""}>{escape(label)}</option>'
        for code, label in GROUPS
    )


def _admin_panel():
    auths = ClubDualAuthorization.query.filter_by(active=True).order_by(ClubDualAuthorization.id).all()
    profile_by_uid = {p.user_id: p for p in multi_user.UserProfile.query.all()}
    activities = {c.id: c for c in clubs_sports.ClubSport.query.all()}
    rows = ''
    for a in auths:
        p = profile_by_uid.get(a.teacher_user_id)
        club = activities.get(a.club_id) if a.club_id else None
        sport = activities.get(a.sport_id) if a.sport_id else None
        rows += f'''<tr><td>{escape((p.full_name if p else '') or str(a.teacher_user_id))}</td><td>{escape(club.name if club else '—')}</td><td>{escape(sport.name if sport else '—')}</td><td>{escape(dict(GROUPS).get(a.group_code, a.group_code))}</td><td><form method="post" action="/clubs/permissions/{a.id}/delete"><button class="btn alt">Revocar</button></form></td></tr>'''
    return f'''
    <div class="card" id="club-permissions-admin">
      <h2>Autorizaciones de docentes</h2>
      <p class="muted">Cada docente puede modificar <b>un club y un deporte</b>, además de su grupo autorizado. El administrador decide cuáles. Los demás espacios permanecen en modo consulta.</p>
      <form method="post" action="/clubs/permissions/save" class="grid">
        <div><label>Docente</label><select name="teacher_user_id" required><option value="">Seleccionar…</option>{_teacher_options()}</select></div>
        <div><label>Club autorizado</label><select name="club_id">{_activity_options('CLUB')}</select></div>
        <div><label>Deporte autorizado</label><select name="sport_id">{_activity_options('DEPORTE')}</select></div>
        <div><label>Grupo autorizado</label><select name="group_code" required><option value="">Seleccionar…</option>{_group_options()}</select></div>
        <div style="align-self:end"><button>Guardar autorización</button></div>
      </form>
      <div class="scroll" style="margin-top:16px"><table><tr><th>Docente</th><th>Club</th><th>Deporte</th><th>Grupo</th><th>Acción</th></tr>{rows or '<tr><td colspan="5">Aún no hay autorizaciones.</td></tr>'}</table></div>
    </div>'''


def _teacher_authorization_note(auth):
    if not auth:
        return '<div class="card"><b>Sin autorización de edición.</b> Puedes consultar el módulo, pero el administrador debe asignarte un club, un deporte y tu grupo para que puedas modificarlos.</div>'
    activities = {c.id: c for c in clubs_sports.ClubSport.query.all()}
    club = activities.get(auth.club_id) if auth.club_id else None
    sport = activities.get(auth.sport_id) if auth.sport_id else None
    club_name = club.name if club else 'Sin club asignado'
    sport_name = sport.name if sport else 'Sin deporte asignado'
    return (
        '<div class="card"><b>Autorización vigente:</b> '
        f'Club: {escape(club_name)} · Deporte: {escape(sport_name)} · '
        f'Grupo: {escape(dict(GROUPS).get(auth.group_code, auth.group_code))}. '
        'Solo esos dos espacios pueden ser modificados por tu cuenta.</div>'
    )


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
                html = html.replace(
                    '<div class="card scroll">',
                    _teacher_authorization_note(_authorization_for_teacher(session.get('uid'))) + '<div class="card scroll">',
                    1,
                )
    elif request.path.startswith('/clubs/') and p.role != 'ADMIN':
        cid = _club_id_from_path(request.path)
        editable = bool(cid and _can_edit_club(cid))
        if not editable:
            html = html.replace('</head>', '<style id="clubs-readonly">form[method="post"] button{display:none!important}.readonly-note{background:#fff4d8;border:1px solid #e8c979;padding:11px 14px;border-radius:10px;margin-bottom:14px;font-weight:750}</style></head>', 1)
            html = html.replace('<main>', '<main><div class="readonly-note">Modo consulta: puedes visualizar esta información, pero solo puedes modificar el club y el deporte que el administrador te asignó.</div>', 1)
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


def _migrate_legacy_authorizations():
    try:
        legacy_table = core.db.metadata.tables.get('club_edit_authorization')
        if legacy_table is None:
            return
        rows = core.db.session.execute(legacy_table.select().where(legacy_table.c.active.is_(True))).mappings().all()
        for old in rows:
            uid = old.get('teacher_user_id')
            if not uid or ClubDualAuthorization.query.filter_by(teacher_user_id=uid).first():
                continue
            activity = core.db.session.get(clubs_sports.ClubSport, old.get('club_id'))
            if not activity:
                continue
            kind = (activity.kind or 'CLUB').strip().upper()
            row = ClubDualAuthorization(teacher_user_id=uid, group_code=old.get('group_code') or '1A', active=True)
            if kind == 'DEPORTE':
                row.sport_id = activity.id
            else:
                row.club_id = activity.id
            core.db.session.add(row)
        core.db.session.commit()
    except Exception:
        core.db.session.rollback()


def install(app):
    with app.app_context():
        core.db.create_all()
        _migrate_legacy_authorizations()

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
        flash('Este apartado es de consulta para tu cuenta. Solo puedes modificar el club y el deporte que el administrador te haya asignado.')
        return redirect(request.referrer or '/clubs')

    @app.post('/clubs/permissions/save')
    def save_club_permission():
        if not _is_admin():
            return redirect('/clubs')
        try:
            teacher_uid = int(request.form.get('teacher_user_id', '0'))
        except ValueError:
            teacher_uid = 0

        def optional_id(name):
            raw = request.form.get(name, '').strip()
            if not raw:
                return None
            try:
                return int(raw)
            except ValueError:
                return None

        club_id = optional_id('club_id')
        sport_id = optional_id('sport_id')
        group_code = request.form.get('group_code', '').strip().upper()
        p = multi_user._profile(teacher_uid)
        club = core.db.session.get(clubs_sports.ClubSport, club_id) if club_id else None
        sport = core.db.session.get(clubs_sports.ClubSport, sport_id) if sport_id else None

        if not p or p.role != 'DOCENTE' or not p.active or group_code not in dict(GROUPS):
            flash('Selecciona un docente activo y un grupo válidos.')
            return redirect('/clubs')
        if club and (club.kind or '').strip().upper() != 'CLUB':
            flash('El espacio seleccionado como club no corresponde a un CLUB.')
            return redirect('/clubs')
        if sport and (sport.kind or '').strip().upper() != 'DEPORTE':
            flash('El espacio seleccionado como deporte no corresponde a un DEPORTE.')
            return redirect('/clubs')
        if not club and not sport:
            flash('Asigna al menos un club o un deporte.')
            return redirect('/clubs')

        if club_id:
            occupied = ClubDualAuthorization.query.filter(
                ClubDualAuthorization.club_id == club_id,
                ClubDualAuthorization.teacher_user_id != teacher_uid,
                ClubDualAuthorization.active.is_(True),
            ).first()
            if occupied:
                flash('Ese club ya está autorizado a otro docente. Revoca o cambia esa autorización primero.')
                return redirect('/clubs')
        if sport_id:
            occupied = ClubDualAuthorization.query.filter(
                ClubDualAuthorization.sport_id == sport_id,
                ClubDualAuthorization.teacher_user_id != teacher_uid,
                ClubDualAuthorization.active.is_(True),
            ).first()
            if occupied:
                flash('Ese deporte ya está autorizado a otro docente. Revoca o cambia esa autorización primero.')
                return redirect('/clubs')

        auth = ClubDualAuthorization.query.filter_by(teacher_user_id=teacher_uid).first()
        if auth is None:
            auth = ClubDualAuthorization(teacher_user_id=teacher_uid, group_code=group_code, active=True)
            core.db.session.add(auth)
        auth.club_id = club_id
        auth.sport_id = sport_id
        auth.group_code = group_code
        auth.active = True

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
        club_name = club.name if club else 'sin club'
        sport_name = sport.name if sport else 'sin deporte'
        flash(f'Autorización guardada para {p.full_name}: club {club_name}, deporte {sport_name}, grupo {dict(GROUPS)[group_code]}.')
        return redirect('/clubs')

    @app.post('/clubs/permissions/<int:auth_id>/delete')
    def delete_club_permission(auth_id):
        if not _is_admin():
            return redirect('/clubs')
        row = core.db.session.get(ClubDualAuthorization, auth_id)
        if row:
            core.db.session.delete(row)
            core.db.session.commit()
            flash('Autorización de club y deporte revocada.')
        return redirect('/clubs')

    @app.after_request
    def clubs_permissions_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = _decorate_clubs_page(response.get_data(as_text=True))
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
