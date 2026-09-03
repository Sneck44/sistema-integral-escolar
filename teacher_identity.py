from html import escape

from flask import request, redirect, session, flash

import app as core
import multi_user


def current_profile():
    uid = session.get('uid')
    return multi_user._profile(uid) if uid else None


def teacher_name_for_active_group():
    """Devuelve el nombre del docente titular del grupo activo.

    Si quien exporta es DOCENTE, usa su propio perfil. Para ADMIN/DIRECCION/etc.
    busca al docente asignado al entorno activo mediante TeacherGroupAccess.
    """
    profile = current_profile()
    if profile and profile.role == 'DOCENTE':
        return (profile.full_name or '').strip() or 'DOCENTE TITULAR'

    try:
        import group_workspaces
        import teacher_group_permissions as tgp
        grade, group_name = group_workspaces.active_group_tuple()
        access = tgp.TeacherGroupAccess.query.filter_by(
            grade=grade, group_name=group_name
        ).first()
        if access:
            p = multi_user._profile(access.user_id)
            if p and p.active and p.role == 'DOCENTE':
                return (p.full_name or '').strip() or 'DOCENTE TITULAR'
    except Exception:
        pass
    return 'DOCENTE TITULAR'


def _patch_excel_signatures():
    try:
        import excel_exports

        def add_signatures(ws, last_data_row, cols):
            f = ws.book_formats
            last = max(1, cols - 1)
            sig_row = last_data_row + 4
            left_end = max(1, last // 2 - 1)
            right_start = min(last, last // 2 + 1)
            teacher = teacher_name_for_active_group()

            ws.merge_range(sig_row, 0, sig_row, left_end, '________________________________________', f['signature'])
            ws.merge_range(sig_row + 1, 0, sig_row + 1, left_end, teacher.upper(), f['signature_name'])
            ws.merge_range(sig_row + 2, 0, sig_row + 2, left_end, 'DOCENTE TITULAR DEL GRUPO', f['signature'])
            ws.merge_range(sig_row, right_start, sig_row, last, '________________________________________', f['signature'])
            ws.merge_range(sig_row + 1, right_start, sig_row + 1, last, 'Vo. Bo. DIRECTORA', f['signature'])
            ws.merge_range(sig_row + 2, right_start, sig_row + 2, last, 'MTRA. NELLY AZUCENA HERNÁNDEZ PICAZO', f['signature_name'])
            ws.set_row(sig_row, 24)
            ws.set_row(sig_row + 1, 18)
            ws.set_row(sig_row + 2, 18)
            try:
                ws.print_area(0, 0, sig_row + 2, last)
            except Exception:
                pass

        excel_exports._add_signatures = add_signatures
    except Exception:
        pass


def install(app):
    _patch_excel_signatures()

    @app.route('/account/profile', methods=['GET', 'POST'])
    def account_profile():
        uid = session.get('uid')
        if not uid:
            return redirect('/login')
        profile = multi_user._profile(uid)
        if not profile or not profile.active:
            return redirect('/login')

        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            if len(full_name) < 5:
                flash('Escribe tu nombre completo.')
                return redirect('/account/profile')
            profile.full_name = full_name[:150]
            core.db.session.commit()
            flash('Tu nombre fue actualizado correctamente. Se usará en tu grupo y en las exportaciones.')
            return redirect('/account/profile')

        role = escape(multi_user._role_label(profile.role))
        current_name = escape(profile.full_name or '')
        note = (
            'Este será el nombre que aparecerá como docente titular en los documentos y archivos Excel de tu grupo.'
            if profile.role == 'DOCENTE'
            else 'Este nombre se utilizará para identificar tu cuenta dentro del sistema.'
        )
        body = f'''
        <div class="page-head"><h1>Mi perfil</h1><p>Actualiza tus datos personales de identificación.</p></div>
        <div class="card" style="max-width:680px">
          <form method="post">
            <label>Nombre completo
              <input name="full_name" value="{current_name}" maxlength="150" required>
            </label>
            <p class="muted" style="margin:8px 0 18px">{escape(note)}</p>
            <label>Rol
              <input value="{role}" disabled>
            </label>
            <div style="margin-top:18px"><button style="width:auto">Guardar mi nombre</button></div>
          </form>
        </div>'''
        return core.page('Mi perfil', body)

    @app.after_request
    def personalized_identity_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        profile = current_profile()
        if not profile:
            return response

        html = response.get_data(as_text=True)
        display_name = escape((profile.full_name or '').strip() or 'Usuario')
        role_label = escape(multi_user._role_label(profile.role))

        # Hero de bienvenida: deja de depender del texto fijo "Administrador".
        import re
        html = re.sub(
            r'<h1>¡Bienvenido,\s*[^<]+!</h1>',
            f'<h1>¡Bienvenido, {display_name}!</h1>',
            html,
            count=1,
        )

        # Si por algún módulo todavía quedó el saludo fijo original, también se sustituye.
        html = html.replace('<h1>¡Bienvenido, Administrador!</h1>', f'<h1>¡Bienvenido, {display_name}!</h1>')

        # En el encabezado se muestra nombre y rol reales.
        html = html.replace('<b>Administrador</b>', f'<b>{display_name}</b>')
        html = html.replace('<small>Rol: Administrador</small>', f'<small>Rol: {role_label}</small>')

        # Acceso a Mi perfil para que cada usuario, especialmente el docente, capture su propio nombre.
        if 'href="/account/profile"' not in html:
            marker = '<a class="nav-link logout" href="/logout">'
            link = '<a class="nav-link" href="/account/profile"><span class="nav-icon">◎</span><span>Mi perfil</span></a>'
            if marker in html:
                html = html.replace(marker, link + marker, 1)

        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
