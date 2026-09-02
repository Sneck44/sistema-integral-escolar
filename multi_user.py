from datetime import datetime
from html import escape

from flask import request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

import app as core


ROLES = {
    'ADMIN': 'Administrador',
    'DIRECCION': 'Dirección',
    'DOCENTE': 'Docente',
    'USAER': 'USAER / Apoyo',
    'CONSULTA': 'Solo consulta',
    'PENDIENTE': 'Pendiente de aprobación',
}


class UserProfile(core.db.Model):
    __tablename__ = 'user_profile'
    id = core.db.Column(core.db.Integer, primary_key=True)
    user_id = core.db.Column(core.db.Integer, core.db.ForeignKey('user.id'), unique=True, nullable=False)
    full_name = core.db.Column(core.db.String(150), default='')
    email = core.db.Column(core.db.String(180), unique=True, nullable=True)
    role = core.db.Column(core.db.String(30), default='PENDIENTE', nullable=False)
    active = core.db.Column(core.db.Boolean, default=False, nullable=False)
    created_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = core.db.Column(core.db.DateTime, nullable=True)


def _profile(user_id):
    if not user_id:
        return None
    return UserProfile.query.filter_by(user_id=user_id).first()


def _current_profile():
    return _profile(session.get('uid'))


def _is_admin():
    p = _current_profile()
    return bool(p and p.active and p.role == 'ADMIN')


def _role_label(role):
    return ROLES.get(role or '', role or 'Usuario')


def _ensure_profiles():
    users = core.User.query.order_by(core.User.id).all()
    if not users:
        return
    existing = {p.user_id for p in UserProfile.query.all()}
    has_admin = UserProfile.query.filter_by(role='ADMIN', active=True).first() is not None
    changed = False
    for index, user in enumerate(users):
        if user.id in existing:
            continue
        make_admin = not has_admin and index == 0
        core.db.session.add(UserProfile(
            user_id=user.id,
            full_name=user.username,
            role='ADMIN' if make_admin else 'PENDIENTE',
            active=True if make_admin else False,
        ))
        if make_admin:
            has_admin = True
        changed = True
    if changed:
        core.db.session.commit()


def install(app):
    @app.before_request
    def multi_user_bootstrap():
        # core.boot() ya ejecutó db.create_all(); este modelo queda incluido
        # desde que este módulo fue importado por entry.py.
        _ensure_profiles()

    @app.before_request
    def multi_user_access_control():
        path = request.path
        public_prefixes = (
            '/login', '/logout', '/setup', '/register', '/db-missing',
            '/school-logo', '/apple-touch-icon', '/favicon', '/static/'
        )
        if path.startswith(public_prefixes):
            return None

        uid = session.get('uid')
        if not uid:
            return None
        profile = _profile(uid)
        if not profile or not profile.active or profile.role == 'PENDIENTE':
            session.clear()
            flash('Tu cuenta está pendiente de aprobación o fue desactivada.')
            return redirect('/login')

        if path.startswith('/users') and profile.role != 'ADMIN':
            flash('Solo el administrador puede gestionar usuarios.')
            return redirect('/')
        if path.startswith('/config') and profile.role != 'ADMIN':
            flash('Solo el administrador puede modificar la configuración general.')
            return redirect('/')

        if request.method == 'POST':
            if path.startswith('/account/password'):
                return None
            if profile.role == 'CONSULTA':
                flash('Tu cuenta es de solo consulta.')
                return redirect(request.referrer or '/')
            if profile.role in ('DIRECCION', 'USAER') and not path.startswith('/incidents'):
                flash('Tu rol no permite modificar este módulo.')
                return redirect(request.referrer or '/')
        return None

    def login_multi():
        if not core.User.query.first():
            return redirect('/setup')
        if request.method == 'POST':
            username = request.form.get('user', '').strip()
            password = request.form.get('password', '')
            user = core.User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                profile = _profile(user.id)
                if not profile or not profile.active or profile.role == 'PENDIENTE':
                    flash('Tu cuenta aún no está autorizada para ingresar.')
                else:
                    session.clear()
                    session['uid'] = user.id
                    profile.last_login = datetime.utcnow()
                    core.db.session.commit()
                    return redirect('/')
            else:
                flash('Usuario o contraseña incorrectos.')
        body = '''
        <div class="card" style="max-width:460px;margin:auto">
          <h1>Acceso</h1>
          <form method="post">
            <label>Usuario<input name="user" autocomplete="username" required></label><br><br>
            <label>Contraseña<input name="password" type="password" autocomplete="current-password" required></label><br><br>
            <button>Entrar</button>
          </form>
          <p class="muted" style="margin-top:18px;text-align:center">¿Eres nuevo? <a href="/register">Solicitar una cuenta</a></p>
        </div>'''
        return core.page('Acceso', body)

    app.view_functions['login'] = login_multi

    @app.route('/register', methods=['GET', 'POST'])
    def register_user():
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower() or None
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            if len(full_name) < 3 or len(username) < 3:
                flash('Escribe tu nombre completo y un usuario válido.')
            elif len(password) < 10:
                flash('La contraseña debe tener al menos 10 caracteres.')
            elif core.User.query.filter_by(username=username).first():
                flash('Ese nombre de usuario ya está registrado.')
            elif email and UserProfile.query.filter_by(email=email).first():
                flash('Ese correo ya está registrado.')
            else:
                user = core.User(username=username, password=generate_password_hash(password))
                core.db.session.add(user)
                core.db.session.flush()
                core.db.session.add(UserProfile(
                    user_id=user.id,
                    full_name=full_name,
                    email=email,
                    role='PENDIENTE',
                    active=False,
                ))
                core.db.session.commit()
                flash('Solicitud enviada. Un administrador debe aprobar tu cuenta antes de que puedas entrar.')
                return redirect('/login')
        body = '''
        <div class="card" style="max-width:560px;margin:auto">
          <h1>Solicitar cuenta</h1>
          <p class="muted">Tu cuenta quedará pendiente hasta que un administrador la autorice y asigne un rol.</p>
          <form method="post">
            <label>Nombre completo<input name="full_name" required maxlength="150"></label><br><br>
            <label>Correo electrónico<input name="email" type="email" maxlength="180"></label><br><br>
            <label>Usuario<input name="username" required minlength="3" maxlength="80" autocomplete="username"></label><br><br>
            <label>Contraseña<input name="password" type="password" required minlength="10" autocomplete="new-password"></label><br><br>
            <button>Enviar solicitud</button>
          </form>
          <p style="margin-top:16px"><a href="/login">← Volver al acceso</a></p>
        </div>'''
        return core.page('Solicitar cuenta', body)

    @app.route('/users', methods=['GET', 'POST'])
    def users_admin():
        if not _is_admin():
            flash('Solo el administrador puede gestionar usuarios.')
            return redirect('/')

        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower() or None
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            role = request.form.get('role', 'DOCENTE')
            if role not in ROLES or role == 'PENDIENTE':
                role = 'DOCENTE'
            if len(password) < 10:
                flash('La contraseña temporal debe tener al menos 10 caracteres.')
            elif core.User.query.filter_by(username=username).first():
                flash('Ese usuario ya existe.')
            elif email and UserProfile.query.filter_by(email=email).first():
                flash('Ese correo ya está registrado.')
            else:
                user = core.User(username=username, password=generate_password_hash(password))
                core.db.session.add(user)
                core.db.session.flush()
                core.db.session.add(UserProfile(
                    user_id=user.id,
                    full_name=full_name or username,
                    email=email,
                    role=role,
                    active=True,
                ))
                core.db.session.commit()
                flash('Usuario creado y activado.')
                return redirect('/users')

        role_options = ''.join(
            f'<option value="{escape(key)}">{escape(label)}</option>'
            for key, label in ROLES.items() if key != 'PENDIENTE'
        )
        rows = ''
        for user in core.User.query.order_by(core.User.id).all():
            p = _profile(user.id)
            if not p:
                continue
            status = 'Activo' if p.active else ('Pendiente' if p.role == 'PENDIENTE' else 'Inactivo')
            checked = 'checked' if p.active else ''
            roles = ''.join(
                f'<option value="{escape(key)}" {"selected" if p.role == key else ""}>{escape(label)}</option>'
                for key, label in ROLES.items() if key != 'PENDIENTE'
            )
            last_login = p.last_login.strftime('%d/%m/%Y %H:%M') if p.last_login else '—'
            rows += f'''
            <tr>
              <td><b>{escape(p.full_name or user.username)}</b><br><small>{escape(user.username)}</small></td>
              <td>{escape(p.email or '—')}</td>
              <td><span>{escape(status)}</span><br><small>Último acceso: {escape(last_login)}</small></td>
              <td>
                <form method="post" action="/users/{user.id}/update" style="display:grid;gap:7px;min-width:190px">
                  <select name="role">{roles}</select>
                  <label style="display:flex;gap:7px;align-items:center"><input style="width:auto" type="checkbox" name="active" {checked}> Cuenta activa</label>
                  <button>Guardar permisos</button>
                </form>
              </td>
              <td>
                <form method="post" action="/users/{user.id}/password" style="display:grid;gap:7px;min-width:180px">
                  <input name="password" type="password" minlength="10" placeholder="Nueva contraseña" required>
                  <button>Restablecer</button>
                </form>
              </td>
            </tr>'''

        body = f'''
        <h1>Usuarios y permisos</h1>
        <div class="card">
          <h2>Crear usuario</h2>
          <form method="post" class="grid">
            <label>Nombre completo<input name="full_name" required></label>
            <label>Correo<input name="email" type="email"></label>
            <label>Usuario<input name="username" required minlength="3"></label>
            <label>Contraseña temporal<input name="password" type="password" required minlength="10"></label>
            <label>Rol<select name="role">{role_options}</select></label>
            <div><button>Crear usuario</button></div>
          </form>
        </div>
        <div class="card scroll">
          <h2>Cuentas registradas</h2>
          <table><tr><th>Persona</th><th>Correo</th><th>Estado</th><th>Rol y acceso</th><th>Contraseña</th></tr>{rows}</table>
        </div>'''
        return core.page('Usuarios', body)

    @app.route('/users/<int:user_id>/update', methods=['POST'])
    def user_update(user_id):
        if not _is_admin():
            return redirect('/')
        p = _profile(user_id)
        if not p:
            flash('Usuario no encontrado.')
            return redirect('/users')
        current_uid = session.get('uid')
        role = request.form.get('role', p.role)
        active = request.form.get('active') == 'on'
        if role not in ROLES or role == 'PENDIENTE':
            role = 'DOCENTE'
        if user_id == current_uid and (role != 'ADMIN' or not active):
            flash('No puedes quitarte a ti mismo el rol de administrador ni desactivar tu propia cuenta.')
            return redirect('/users')
        p.role = role
        p.active = active
        core.db.session.commit()
        flash('Permisos actualizados.')
        return redirect('/users')

    @app.route('/users/<int:user_id>/password', methods=['POST'])
    def user_password_reset(user_id):
        if not _is_admin():
            return redirect('/')
        user = core.db.session.get(core.User, user_id)
        password = request.form.get('password', '')
        if not user:
            flash('Usuario no encontrado.')
        elif len(password) < 10:
            flash('La nueva contraseña debe tener al menos 10 caracteres.')
        else:
            user.password = generate_password_hash(password)
            core.db.session.commit()
            flash('Contraseña restablecida.')
        return redirect('/users')

    @app.route('/account/password', methods=['GET', 'POST'])
    def account_password():
        uid = session.get('uid')
        if not uid:
            return redirect('/login')
        user = core.db.session.get(core.User, uid)
        if request.method == 'POST':
            current = request.form.get('current_password', '')
            new = request.form.get('new_password', '')
            if not check_password_hash(user.password, current):
                flash('La contraseña actual no es correcta.')
            elif len(new) < 10:
                flash('La nueva contraseña debe tener al menos 10 caracteres.')
            else:
                user.password = generate_password_hash(new)
                core.db.session.commit()
                flash('Contraseña actualizada.')
                return redirect('/')
        return core.page('Mi cuenta', '''
        <h1>Mi cuenta</h1><div class="card" style="max-width:560px">
        <h2>Cambiar contraseña</h2><form method="post">
        <label>Contraseña actual<input name="current_password" type="password" required></label><br><br>
        <label>Nueva contraseña<input name="new_password" type="password" minlength="10" required></label><br><br>
        <button>Actualizar contraseña</button></form></div>''')

    @app.after_request
    def multi_user_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        uid = session.get('uid')
        profile = _profile(uid) if uid else None
        if not profile:
            return response
        user = core.db.session.get(core.User, uid)
        html = response.get_data(as_text=True)
        display_name = escape(profile.full_name or (user.username if user else 'Usuario'))
        role_label = escape(_role_label(profile.role))
        html = html.replace('<b>Administrador</b>', f'<b>{display_name}</b>')
        html = html.replace('<small>Rol: Administrador</small>', f'<small>Rol: {role_label}</small>')
        if profile.role == 'ADMIN' and 'href="/users"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            users_link = '<a class="nav-link" href="/users"><span class="nav-icon">♙</span><span>Usuarios</span></a>'
            html = html.replace(marker, users_link + marker, 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
