from datetime import datetime
from flask import request, redirect, session, flash

import app as core
import multi_user


class UserRequestDecision(core.db.Model):
    __tablename__ = 'user_request_decision'
    id = core.db.Column(core.db.Integer, primary_key=True)
    user_id = core.db.Column(core.db.Integer, unique=True, nullable=False, index=True)
    status = core.db.Column(core.db.String(20), default='PENDIENTE', nullable=False)
    decided_at = core.db.Column(core.db.DateTime, nullable=True)
    decided_by = core.db.Column(core.db.Integer, nullable=True)


def _admin_only():
    return multi_user._is_admin()


def _decision(user_id):
    return UserRequestDecision.query.filter_by(user_id=user_id).first()


def install(app):
    @app.before_request
    def ensure_request_decision_table():
        # create_all es idempotente y permite desplegar este módulo sin migración manual.
        if request.path.startswith('/users'):
            core.db.create_all()

    @app.route('/users/<int:user_id>/reject', methods=['POST'])
    def reject_user_request(user_id):
        if not _admin_only():
            flash('Solo el administrador puede rechazar solicitudes.')
            return redirect('/')
        if user_id == session.get('uid'):
            flash('No puedes rechazar tu propia cuenta.')
            return redirect('/users')
        user = core.db.session.get(core.User, user_id)
        profile = multi_user._profile(user_id)
        if not user or not profile:
            flash('Solicitud no encontrada.')
            return redirect('/users')
        if profile.role != 'PENDIENTE' and profile.active:
            flash('Solo pueden rechazarse solicitudes pendientes.')
            return redirect('/users')

        profile.active = False
        profile.role = 'PENDIENTE'
        decision = _decision(user_id)
        if not decision:
            decision = UserRequestDecision(user_id=user_id)
            core.db.session.add(decision)
        decision.status = 'RECHAZADA'
        decision.decided_at = datetime.utcnow()
        decision.decided_by = session.get('uid')
        core.db.session.commit()
        flash('Solicitud rechazada. La cuenta no podrá iniciar sesión.')
        return redirect('/users')

    @app.route('/users/<int:user_id>/restore-request', methods=['POST'])
    def restore_user_request(user_id):
        if not _admin_only():
            return redirect('/')
        profile = multi_user._profile(user_id)
        decision = _decision(user_id)
        if not profile:
            flash('Solicitud no encontrada.')
            return redirect('/users')
        profile.active = False
        profile.role = 'PENDIENTE'
        if decision:
            decision.status = 'PENDIENTE'
            decision.decided_at = datetime.utcnow()
            decision.decided_by = session.get('uid')
        core.db.session.commit()
        flash('La solicitud volvió a estado pendiente.')
        return redirect('/users')

    @app.route('/users/<int:user_id>/delete-request', methods=['POST'])
    def delete_user_request(user_id):
        if not _admin_only():
            flash('Solo el administrador puede eliminar solicitudes.')
            return redirect('/')
        if user_id == session.get('uid'):
            flash('No puedes eliminar tu propia cuenta.')
            return redirect('/users')
        user = core.db.session.get(core.User, user_id)
        profile = multi_user._profile(user_id)
        if not user or not profile:
            flash('Solicitud no encontrada.')
            return redirect('/users')
        if profile.active and profile.role != 'PENDIENTE':
            flash('Esta acción está reservada para solicitudes pendientes o rechazadas.')
            return redirect('/users')

        # Limpia registros auxiliares que dependan de user_id (por ejemplo, grupo autorizado).
        # Se excluyen las tablas principales para respetar el orden de borrado.
        for table in reversed(core.db.metadata.sorted_tables):
            if table.name in ('user', 'user_profile'):
                continue
            if 'user_id' in table.c:
                try:
                    core.db.session.execute(table.delete().where(table.c.user_id == user_id))
                except Exception:
                    core.db.session.rollback()
                    # Reabrimos una transacción y continuamos con la limpieza explícita conocida.
                    break

        # La decisión puede no estar en metadata durante despliegues antiguos; se elimina explícitamente.
        decision = _decision(user_id)
        if decision:
            core.db.session.delete(decision)
        profile = multi_user._profile(user_id)
        if profile:
            core.db.session.delete(profile)
        user = core.db.session.get(core.User, user_id)
        if user:
            core.db.session.delete(user)
        core.db.session.commit()
        flash('Solicitud eliminada definitivamente.')
        return redirect('/users')

    @app.after_request
    def request_actions_ui(response):
        if request.path != '/users' or 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        if not session.get('uid') or not _admin_only():
            return response

        rejected_ids = [str(d.user_id) for d in UserRequestDecision.query.filter_by(status='RECHAZADA').all()]
        ids_json = '[' + ','.join(rejected_ids) + ']'
        css = '''<style id="request-actions-style">
        .request-actions{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}
        .request-actions form{margin:0}.request-actions button{width:auto!important;padding:8px 13px!important;font-size:11px!important}
        .request-reject{background:#9b6517!important}.request-delete{background:#a6222e!important}.request-restore{background:#6d5a35!important}
        .request-status{display:inline-flex;margin-top:5px;padding:4px 9px;border-radius:999px;background:#fff3d8;color:#7a5010;font-size:10px;font-weight:800;border:1px solid #ead1a0}
        </style>'''
        js = f'''<script id="request-actions-js">(function(){{
          const rejected=new Set({ids_json});
          document.querySelectorAll('table tr').forEach(row=>{{
            const update=row.querySelector('form[action^="/users/"][action$="/update"]');
            if(!update)return;
            const m=update.getAttribute('action').match(/\/users\/(\d+)\/update/);if(!m)return;
            const uid=m[1]; const cells=row.querySelectorAll('td'); if(cells.length<3)return;
            const statusCell=cells[2]; const isPending=(statusCell.textContent||'').toLowerCase().includes('pendiente');
            const isRejected=rejected.has(uid);
            if(!isPending&&!isRejected)return;
            if(isRejected){{
              statusCell.innerHTML='<span class="request-status">Solicitud rechazada</span><br><small>Sin acceso al sistema</small>';
              update.style.display='none';
            }}
            const box=document.createElement('div');box.className='request-actions';
            if(!isRejected) box.innerHTML+='<form method="post" action="/users/'+uid+'/reject"><button class="request-reject" type="submit" onclick="return confirm(\'¿Rechazar esta solicitud? El usuario no podrá iniciar sesión.\')">Rechazar</button></form>';
            if(isRejected) box.innerHTML+='<form method="post" action="/users/'+uid+'/restore-request"><button class="request-restore" type="submit">Volver a pendiente</button></form>';
            box.innerHTML+='<form method="post" action="/users/'+uid+'/delete-request"><button class="request-delete" type="submit" onclick="return confirm(\'¿Eliminar definitivamente esta solicitud y su cuenta? Esta acción no se puede deshacer.\')">Eliminar solicitud</button></form>';
            cells[cells.length-1].appendChild(box);
          }});
        }})();</script>'''
        html = response.get_data(as_text=True)
        if '</head>' in html and 'id="request-actions-style"' not in html:
            html = html.replace('</head>', css + '</head>', 1)
        if '</body>' in html and 'id="request-actions-js"' not in html:
            html = html.replace('</body>', js + '</body>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
