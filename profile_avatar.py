import base64
import json
import os
import uuid
import urllib.request
import urllib.error
from datetime import datetime
from html import escape
from io import BytesIO

from flask import request, redirect, session, flash, Response

import app as core
import multi_user


MAX_IMAGE_BYTES = 5 * 1024 * 1024


class UserAvatar(core.db.Model):
    __tablename__ = 'user_avatar'
    id = core.db.Column(core.db.Integer, primary_key=True)
    user_id = core.db.Column(core.db.Integer, core.db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    original_data = core.db.Column(core.db.LargeBinary, nullable=True)
    original_mime = core.db.Column(core.db.String(40), default='image/jpeg')
    avatar_data = core.db.Column(core.db.LargeBinary, nullable=True)
    avatar_mime = core.db.Column(core.db.String(40), default='image/png')
    updated_at = core.db.Column(core.db.DateTime, default=datetime.utcnow, nullable=False)


def _avatar(uid):
    return UserAvatar.query.filter_by(user_id=uid).first()


def _decode_data_url(value):
    value = (value or '').strip()
    if not value.startswith('data:image/') or ',' not in value:
        raise ValueError('No se recibió una fotografía válida.')
    header, payload = value.split(',', 1)
    mime = header.split(';', 1)[0].replace('data:', '').lower()
    if mime not in ('image/jpeg', 'image/png', 'image/webp'):
        raise ValueError('Formato de imagen no compatible.')
    try:
        raw = base64.b64decode(payload, validate=True)
    except Exception:
        raise ValueError('La fotografía no pudo procesarse.')
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError('La imagen debe pesar menos de 5 MB.')
    return raw, mime


def _multipart(fields, files):
    boundary = '----SchoolAvatar' + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\n'.encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode('utf-8'))
        chunks.append(b'\r\n')
    for name, filename, mime, data in files:
        chunks.append(f'--{boundary}\r\n'.encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        chunks.append(f'Content-Type: {mime}\r\n\r\n'.encode())
        chunks.append(data)
        chunks.append(b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    return b''.join(chunks), f'multipart/form-data; boundary={boundary}'


def _generate_ai_avatar(image_bytes, mime):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('La generación con IA requiere configurar OPENAI_API_KEY.')

    model = os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-1')
    prompt = (
        'Crea un avatar profesional y amable para el perfil de un sistema escolar a partir de esta fotografía. '
        'Conserva claramente la identidad, rasgos faciales, tono de piel, cabello y expresión reconocible de la persona. '
        'Encuadre de cabeza y hombros, mirada natural, iluminación limpia y fondo neutro elegante en tonos claros. '
        'Estilo ilustración digital realista y sobria, apropiada para un docente o personal escolar. '
        'No agregues texto, logotipos, uniformes inventados, accesorios innecesarios ni cambies edad o identidad.'
    )
    ext = 'png' if mime == 'image/png' else ('webp' if mime == 'image/webp' else 'jpg')
    body, content_type = _multipart(
        {
            'model': model,
            'prompt': prompt,
            'size': '1024x1024',
        },
        [('image', f'perfil.{ext}', mime, image_bytes)],
    )
    req = urllib.request.Request(
        'https://api.openai.com/v1/images/edits',
        data=body,
        headers={
            'Authorization': f'Bearer {key}',
            'Content-Type': content_type,
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            data = json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='ignore')[:500]
        raise RuntimeError(f'La IA no pudo generar el avatar ({e.code}). {detail}')
    except Exception as e:
        raise RuntimeError(f'No fue posible conectar con el servicio de IA: {e}')

    items = data.get('data') or []
    if not items:
        raise RuntimeError('La IA no devolvió una imagen.')
    item = items[0]
    if item.get('b64_json'):
        return base64.b64decode(item['b64_json']), 'image/png'
    if item.get('url'):
        with urllib.request.urlopen(item['url'], timeout=45) as res:
            return res.read(), res.headers.get_content_type() or 'image/png'
    raise RuntimeError('La respuesta de IA no contenía una imagen utilizable.')


def _profile_avatar_panel(uid):
    record = _avatar(uid)
    has_avatar = bool(record and (record.avatar_data or record.original_data))
    preview = '/account/avatar/image?v=' + str(int(record.updated_at.timestamp()) if record and record.updated_at else 1) if has_avatar else ''
    current = (
        f'<img class="avatar-profile-current" src="{preview}" alt="Avatar actual">'
        if has_avatar else
        '<div class="avatar-profile-placeholder">◎</div>'
    )
    return f'''
    <section class="card avatar-profile-card">
      <div class="avatar-profile-head">
        <div>{current}</div>
        <div><h2>Avatar de usuario</h2><p class="muted">Toma una fotografía con la cámara y úsala directamente o conviértela en un avatar profesional con IA.</p></div>
      </div>
      <form method="post" action="/account/avatar" id="avatarForm">
        <input type="hidden" name="photo_data" id="avatarPhotoData">
        <div class="avatar-camera-box">
          <video id="avatarVideo" autoplay playsinline muted></video>
          <canvas id="avatarCanvas" width="720" height="720"></canvas>
          <div class="avatar-empty" id="avatarEmpty"><span>◎</span><b>Activa la cámara o elige una foto</b></div>
        </div>
        <div class="avatar-actions">
          <button type="button" class="avatar-secondary" id="startCamera">Abrir cámara</button>
          <button type="button" class="avatar-secondary" id="takePhoto" disabled>Tomar fotografía</button>
          <label class="avatar-upload">Elegir foto<input id="avatarFile" type="file" accept="image/*" capture="user"></label>
          <button type="submit" name="mode" value="photo" id="savePhoto" disabled>Usar como avatar</button>
          <button type="submit" name="mode" value="ai" class="avatar-ai" id="makeAI" disabled>Crear avatar con IA</button>
        </div>
        <p class="muted avatar-note">La fotografía se utiliza únicamente para crear tu avatar de perfil. La opción con IA requiere que el servicio de IA del sistema esté configurado.</p>
      </form>
    </section>
    <style id="profile-avatar-style">
    .avatar-profile-card{{margin-top:18px}}.avatar-profile-head{{display:flex;align-items:center;gap:16px;margin-bottom:18px}}.avatar-profile-head h2{{margin:0 0 5px}}
    .avatar-profile-current,.avatar-profile-placeholder{{width:82px;height:82px;border-radius:50%;object-fit:cover;border:3px solid #caa45f;box-shadow:0 7px 20px rgba(74,18,32,.12)}}
    .avatar-profile-placeholder{{display:grid;place-items:center;background:#f5ecee;color:#7b1024;font-size:32px;font-weight:900}}
    .avatar-camera-box{{position:relative;width:min(100%,520px);aspect-ratio:1/1;border-radius:24px;overflow:hidden;background:#efe9e8;border:1px solid #eadfdd}}
    .avatar-camera-box video,.avatar-camera-box canvas{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}.avatar-camera-box canvas{{display:none}}.avatar-empty{{position:absolute;inset:0;display:grid;place-content:center;text-align:center;gap:8px;color:#766b6d}}.avatar-empty span{{font-size:46px;color:#7b1024}}
    .avatar-actions{{display:flex;flex-wrap:wrap;gap:9px;margin-top:14px;align-items:center}}.avatar-actions button,.avatar-upload{{width:auto!important;padding:10px 14px;border-radius:10px;font-weight:800;cursor:pointer}}
    .avatar-secondary,.avatar-upload{{background:#f4ecee!important;color:#6d1022!important;border:1px solid #e5d3d8!important}}.avatar-upload input{{display:none}}.avatar-ai{{background:linear-gradient(135deg,#7b1024,#a66a2c)!important;color:#fff!important}}.avatar-note{{margin-top:11px;max-width:720px}}
    .avatar-user-img{{width:100%;height:100%;object-fit:cover;border-radius:50%}}
    @media(max-width:600px){{.avatar-profile-head{{align-items:flex-start}}.avatar-actions>*{{flex:1 1 45%;text-align:center}}}}
    </style>
    <script id="profile-avatar-script">
    (function(){{
      const video=document.getElementById('avatarVideo'), canvas=document.getElementById('avatarCanvas'), empty=document.getElementById('avatarEmpty');
      const data=document.getElementById('avatarPhotoData'), start=document.getElementById('startCamera'), take=document.getElementById('takePhoto'), file=document.getElementById('avatarFile');
      const save=document.getElementById('savePhoto'), ai=document.getElementById('makeAI'); let stream=null;
      function ready(v){{data.value=v;save.disabled=false;ai.disabled=false;empty.style.display='none';}}
      start.onclick=async()=>{{try{{stream=await navigator.mediaDevices.getUserMedia({{video:{{facingMode:'user',width:{{ideal:1080}},height:{{ideal:1080}}}},audio:false}});video.srcObject=stream;video.style.display='block';canvas.style.display='none';empty.style.display='none';take.disabled=false;}}catch(e){{alert('No fue posible abrir la cámara. Puedes elegir una fotografía desde tu dispositivo.');}}}};
      take.onclick=()=>{{const s=Math.min(video.videoWidth||720,video.videoHeight||720),sx=((video.videoWidth||720)-s)/2,sy=((video.videoHeight||720)-s)/2;const ctx=canvas.getContext('2d');ctx.drawImage(video,sx,sy,s,s,0,0,720,720);canvas.style.display='block';video.style.display='none';ready(canvas.toDataURL('image/jpeg',.88));if(stream)stream.getTracks().forEach(t=>t.stop());take.disabled=true;}};
      file.onchange=()=>{{const f=file.files&&file.files[0];if(!f)return;const r=new FileReader();r.onload=()=>{{const img=new Image();img.onload=()=>{{const s=Math.min(img.width,img.height),sx=(img.width-s)/2,sy=(img.height-s)/2;const ctx=canvas.getContext('2d');ctx.drawImage(img,sx,sy,s,s,0,0,720,720);canvas.style.display='block';video.style.display='none';ready(canvas.toDataURL('image/jpeg',.88));}};img.src=r.result;}};r.readAsDataURL(f);}};
      document.getElementById('avatarForm').addEventListener('submit',e=>{{if(!data.value){{e.preventDefault();alert('Primero toma o selecciona una fotografía.');return;}}const b=e.submitter;if(b&&b.value==='ai'){{b.disabled=true;b.textContent='Creando avatar…';}}}});
    }})();
    </script>'''


def install(app):
    try:
        with app.app_context():
            core.db.create_all()
    except Exception:
        pass

    @app.route('/account/avatar', methods=['POST'])
    def save_avatar():
        uid = session.get('uid')
        if not uid:
            return redirect('/login')
        profile = multi_user._profile(uid)
        if not profile or not profile.active:
            return redirect('/login')
        try:
            raw, mime = _decode_data_url(request.form.get('photo_data'))
            record = _avatar(uid)
            if not record:
                record = UserAvatar(user_id=uid)
                core.db.session.add(record)
            record.original_data = raw
            record.original_mime = mime
            mode = request.form.get('mode', 'photo')
            if mode == 'ai':
                generated, generated_mime = _generate_ai_avatar(raw, mime)
                if len(generated) > 8 * 1024 * 1024:
                    raise RuntimeError('El avatar generado es demasiado grande.')
                record.avatar_data = generated
                record.avatar_mime = generated_mime
                flash('Tu avatar con IA fue creado y guardado.')
            else:
                record.avatar_data = None
                record.avatar_mime = mime
                flash('Tu fotografía quedó guardada como avatar.')
            record.updated_at = datetime.utcnow()
            core.db.session.commit()
        except Exception as e:
            core.db.session.rollback()
            flash(str(e))
        return redirect('/account/profile')

    @app.route('/account/avatar/image')
    def avatar_image():
        uid = session.get('uid')
        if not uid:
            return Response(status=404)
        record = _avatar(uid)
        if not record:
            return Response(status=404)
        data = record.avatar_data or record.original_data
        mime = record.avatar_mime if record.avatar_data else record.original_mime
        if not data:
            return Response(status=404)
        return Response(data, mimetype=mime or 'image/jpeg', headers={'Cache-Control':'private, no-store, max-age=0'})

    @app.after_request
    def avatar_profile_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        uid = session.get('uid')
        html = response.get_data(as_text=True)
        if request.path == '/account/profile' and 'id="profile-avatar-style"' not in html:
            panel = _profile_avatar_panel(uid)
            marker = '</main>'
            if marker in html:
                html = html.replace(marker, panel + marker, 1)
            elif '</body>' in html:
                html = html.replace('</body>', panel + '</body>', 1)
        record = _avatar(uid)
        if record and (record.avatar_data or record.original_data):
            stamp = int(record.updated_at.timestamp()) if record.updated_at else 1
            img = f'<img class="avatar-user-img" src="/account/avatar/image?v={stamp}" alt="Avatar">'
            html = html.replace('<div class="avatar">A</div>', f'<div class="avatar">{img}</div>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
