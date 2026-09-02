from flask import request, session, redirect, flash

import multi_user
import teacher_group_permissions as tgp
from group_workspaces import active_group_code, active_group_label, _normalize_code


def install(app):
    def enforce_teacher_workspace():
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

        access = tgp._access(uid)
        if not access:
            flash('Tu cuenta docente aún no tiene un grupo autorizado. Solicita al administrador que te asigne uno.')
            return redirect(request.referrer or '/')

        allowed = _normalize_code(access.grade, access.group_name)
        current = active_group_code()
        if current != allowed:
            session['active_group'] = allowed
            flash(f'Por seguridad se restableció tu entorno autorizado: {active_group_label()}.')
            return redirect(request.referrer or '/')
        return None

    funcs = app.before_request_funcs.get(None, [])
    for index, fn in enumerate(list(funcs)):
        if getattr(fn, '__name__', '') == 'enforce_teacher_single_group':
            funcs[index] = enforce_teacher_workspace
            break
