import os
from datetime import datetime

from flask import request, session, redirect, flash, Response

import app as core
import multi_user

MAX_LOGO_BYTES = 4 * 1024 * 1024
ALLOWED_MIME = {'image/png', 'image/jpeg', 'image/webp'}


class DocumentLogos(core.db.Model):
    __tablename__ = 'document_logos'
    id = core.db.Column(core.db.Integer, primary_key=True)
    left_data = core.db.Column(core.db.LargeBinary, nullable=True)
    left_mime = core.db.Column(core.db.String(40), nullable=True)
    right_data = core.db.Column(core.db.LargeBinary, nullable=True)
    right_mime = core.db.Column(core.db.String(40), nullable=True)
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


def _record():
    return DocumentLogos.query.order_by(DocumentLogos.id.asc()).first()


def _is_admin():
    uid = session.get('uid')
    if not uid:
        return False
    try:
        p = multi_user._profile(uid)
        return bool(p and p.active and p.role == 'ADMIN')
    except Exception:
        return False


def _fallback(side):
    base = os.path.join(os.path.dirname(__file__), 'static')
    candidates = (
        ['encabezado-logos-puebla.png', 'encabezado-izquierdo.png']
        if side == 'left'
        else ['encabezado-logo-telesecundaria.jpeg', 'encabezado-derecho.png', 'logo-benito-juarez-final.PNG']
    )
    for name in candidates:
        path = os.path.join(base, name)
        if os.path.exists(path):
            return path
    return None


def get_logo_bytes(side):
    rec = _record()
    if rec:
        data = rec.left_data if side == 'left' else rec.right_data
        mime = rec.left_mime if side == 'left' else rec.right_mime
        if data:
            return bytes(data), mime or 'image/png'
    path = _fallback(side)
    if not path:
        return None, None
    try:
        with open(path, 'rb') as fh:
            data = fh.read()
        ext = os.path.splitext(path)[1].lower()
        mime = 'image/png' if ext == '.png' else ('image/webp' if ext == '.webp' else 'image/jpeg')
        return data, mime
    except Exception:
        return None, None


def _save_upload(side, file):
    if not file or not file.filename:
        raise ValueError('Selecciona una imagen antes de guardar.')
    mime = (file.mimetype or '').lower()
    if mime not in ALLOWED_MIME:
        raise ValueError('Usa una imagen PNG, JPG/JPEG o WebP.')
    data = file.read(MAX_LOGO_BYTES + 1)
    if not data or len(data) > MAX_LOGO_BYTES:
        raise ValueError('Cada logotipo debe pesar menos de 4 MB.')
    rec = _record()
    if not rec:
        rec = DocumentLogos()
        core.db.session.add(rec)
    if side == 'left':
        rec.left_data, rec.left_mime = data, mime
    else:
        rec.right_data, rec.right_mime = data, mime
    rec.updated_at = datetime.utcnow()
    core.db.session.commit()


def _panel():
    rec = _record()
    stamp = int(rec.updated_at.timestamp()) if rec and rec.updated_at else 1
    return f'''<section class="card document-logo-card" id="document-logos">
      <h2>Logotipos de los formatos</h2>
      <p class="muted">Selecciona manualmente las imágenes que aparecerán en todos los formatos institucionales. Solo el administrador puede modificarlas.</p>
      <div class="document-logo-grid">
        <form method="post" action="/config/document-logos/left" enctype="multipart/form-data" class="document-logo-box">
          <b>Logotipo izquierdo</b><div class="document-logo-preview"><img src="/document-logo/left?v={stamp}" alt="Logotipo izquierdo"></div>
          <label>Elegir imagen<input type="file" name="logo" accept="image/png,image/jpeg,image/webp" required></label>
          <button type="submit">Guardar logotipo izquierdo</button>
        </form>
        <form method="post" action="/config/document-logos/right" enctype="multipart/form-data" class="document-logo-box">
          <b>Logotipo derecho</b><div class="document-logo-preview"><img src="/document-logo/right?v={stamp}" alt="Logotipo derecho"></div>
          <label>Elegir imagen<input type="file" name="logo" accept="image/png,image/jpeg,image/webp" required></label>
          <button type="submit">Guardar logotipo derecho</button>
        </form>
      </div><p class="muted">Formatos admitidos: PNG, JPG/JPEG y WebP. Máximo 4 MB por imagen.</p>
    </section>
    <style id="document-logo-style">.document-logo-card{{margin-top:16px}}.document-logo-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:14px}}.document-logo-box{{border:1px solid #eee8e6;border-radius:14px;padding:14px;min-width:0}}.document-logo-preview{{height:115px;display:grid;place-items:center;background:#faf8f7;border:1px dashed #d9cdca;border-radius:12px;margin:10px 0;overflow:hidden}}.document-logo-preview img{{display:block;max-width:96%;max-height:100px;width:auto;height:auto;object-fit:contain}}.document-logo-box input{{margin:7px 0 10px}}@media(max-width:720px){{.document-logo-grid{{grid-template-columns:1fr}}.document-logo-box button{{min-height:46px}}}}</style>'''


def install(app):
    try:
        with app.app_context():
            core.db.create_all()
    except Exception:
        pass

    @app.route('/document-logo/<side>')
    def document_logo_image(side):
        if side not in ('left', 'right') or not session.get('uid'):
            return Response(status=404)
        data, mime = get_logo_bytes(side)
        if not data:
            return Response(status=404)
        return Response(data, mimetype=mime or 'image/png', headers={'Cache-Control':'private, no-store, max-age=0'})

    @app.route('/config/document-logos/<side>', methods=['POST'])
    def save_document_logo(side):
        if not _is_admin():
            flash('Solo el administrador puede modificar los logotipos de los formatos.')
            return redirect('/config')
        if side not in ('left', 'right'):
            return Response(status=404)
        try:
            _save_upload(side, request.files.get('logo'))
            flash(('Logotipo izquierdo' if side == 'left' else 'Logotipo derecho') + ' actualizado correctamente.')
        except Exception as exc:
            core.db.session.rollback()
            flash(str(exc))
        return redirect('/config#document-logos')

    @app.after_request
    def document_logo_config_ui(response):
        if request.path != '/config' or not _is_admin() or 'text/html' not in response.headers.get('Content-Type',''):
            return response
        html = response.get_data(as_text=True)
        if 'id="document-logos"' not in html:
            panel = _panel()
            if '</main>' in html:
                html = html.replace('</main>', panel + '</main>', 1)
            elif '</body>' in html:
                html = html.replace('</body>', panel + '</body>', 1)
            response.set_data(html)
            response.headers['Content-Length'] = str(len(response.get_data()))
        return response
