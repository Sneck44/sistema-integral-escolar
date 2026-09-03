import base64
import json
import os
import uuid
import urllib.request
import urllib.error
from datetime import datetime

from flask import request, redirect, session, flash, Response

import app as core
import multi_user

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_AVATAR_BYTES = 8 * 1024 * 1024
DEFAULT_IMAGE_MODEL = 'gpt-image-2'

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
        raise ValueError('Primero toma o selecciona una fotografía válida.')
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
        chunks += [f'--{boundary}\r\n'.encode(), f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(), str(value).encode('utf-8'), b'\r\n']
    for name, filename, mime, data in files:
        chunks += [f'--{boundary}\r\n'.encode(), f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(), f'Content-Type: {mime}\r\n\r\n'.encode(), data, b'\r\n']
    chunks.append(f'--{boundary}--\r\n'.encode())
    return b''.join(chunks), f'multipart/form-data; boundary={boundary}'

def _role_context(profile):
    role = (profile.role or '').upper() if profile else ''
    feminine = session.get('welcome_gender') == 'F'
    if role == 'DOCENTE': return 'una docente de telesecundaria' if feminine else 'un docente de telesecundaria'
    if role == 'DIRECCION': return 'una directiva escolar' if feminine else 'un directivo escolar'
    if role == 'USAER': return 'una profesional de apoyo educativo' if feminine else 'un profesional de apoyo educativo'
    if role == 'ADMIN': return 'una integrante del personal educativo' if feminine else 'un integrante del personal educativo'
    return 'una integrante del personal escolar' if feminine else 'un integrante del personal escolar'

def _generate_ai_avatar(image_bytes, mime, profile):
    key = (os.getenv('OPENAI_API_KEY') or '').strip()
    if not key: raise RuntimeError('La IA aún no está habilitada en producción. Falta configurar OPENAI_API_KEY en Vercel.')
    model = (os.getenv('OPENAI_IMAGE_MODEL') or DEFAULT_IMAGE_MODEL).strip()
    prompt = ('Usa la fotografía suministrada como referencia principal de identidad. Crea un avatar 3D de animación cinematográfica con estética tipo Pixar, cálida, pulida y profesional. '
              'Conserva fielmente identidad, forma del rostro, tono de piel, cabello, ojos, nariz, sonrisa, edad aparente y rasgos distintivos. '
              f'Representa a la persona como {_role_context(profile)}, con presencia profesional, amable y cercana. Encuadre cuadrado de cabeza y hombros, mirada a cámara, '
              'expresión natural, vestimenta profesional-casual apropiada para una escuela, iluminación suave cinematográfica y fondo de aula desenfocado. '
              'No añadas texto, nombres, logotipos, marcas, uniformes inventados ni personajes conocidos. La persona debe ser inmediatamente reconocible.')
    ext = 'png' if mime == 'image/png' else ('webp' if mime == 'image/webp' else 'jpg')
    body, content_type = _multipart({'model': model, 'prompt': prompt, 'size': '1024x1024'}, [('image', f'perfil.{ext}', mime, image_bytes)])
    req = urllib.request.Request('https://api.openai.com/v1/images/edits', data=body, headers={'Authorization': f'Bearer {key}', 'Content-Type': content_type}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=120) as res: data = json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='ignore')[:600]
        raise RuntimeError(f'La IA no pudo generar el avatar ({e.code}). {detail}')
    except Exception as e: raise RuntimeError(f'No fue posible conectar con el servicio de IA: {e}')
    items = data.get('data') or []
    if not items: raise RuntimeError('La IA no devolvió una imagen.')
    item = items[0]
    if item.get('b64_json'): return base64.b64decode(item['b64_json']), 'image/png'
    if item.get('url'):
        with urllib.request.urlopen(item['url'], timeout=45) as res: return res.read(), res.headers.get_content_type() or 'image/png'
    raise RuntimeError('La respuesta de IA no contenía una imagen utilizable.')

def _profile_avatar_panel(uid):
    record = _avatar(uid); has_avatar = bool(record and (record.avatar_data or record.original_data)); stamp = int(record.updated_at.timestamp()) if record and record.updated_at else 1
    current = f'<img class="avatar-profile-current" src="/account/avatar/image?v={stamp}" alt="Avatar actual">' if has_avatar else '<div class="avatar-profile-placeholder">◎</div>'
    ai_ready = bool((os.getenv('OPENAI_API_KEY') or '').strip()); status = '<span class="avatar-status ok">IA lista</span>' if ai_ready else '<span class="avatar-status warn">IA no disponible</span>'
    return f'''
    <section class="card avatar-profile-card"><div class="avatar-profile-head"><div>{current}</div><div><h2>Foto de perfil</h2><p class="muted">Elige una foto de tu computadora y úsala directamente como avatar. Si lo deseas, también puedes crear una versión con IA.</p>{status}</div></div>
    <form method="post" action="/account/avatar" id="avatarForm"><input type="hidden" name="photo_data" id="avatarPhotoData"><input type="hidden" name="mode" id="avatarMode" value="photo">
    <div class="avatar-camera-box"><video id="avatarVideo" autoplay playsinline muted></video><canvas id="avatarCanvas" width="720" height="720"></canvas><div class="avatar-empty" id="avatarEmpty"><span>◎</span><b>Selecciona una fotografía</b></div><button type="button" id="capturePhoto" class="avatar-capture" disabled>●</button></div>
    <div class="avatar-source-actions"><label class="avatar-upload">Elegir foto de mi PC<input id="avatarFile" type="file" accept="image/jpeg,image/png,image/webp"></label><button type="button" class="avatar-secondary" id="startCamera">Usar cámara</button></div>
    <div class="avatar-save-actions"><button type="submit" class="avatar-photo-main" id="savePhoto" disabled>Guardar foto como avatar</button><button type="submit" class="avatar-ai-main" id="makeAI" disabled>Crear avatar con IA</button></div>
    <p class="muted avatar-note">Guardar la foto como avatar no utiliza IA ni consume créditos.</p></form></section>
    <style id="profile-avatar-style">
    .avatar-profile-card{{margin-top:18px;max-width:760px}}.avatar-profile-head{{display:flex;align-items:center;gap:16px;margin-bottom:18px}}.avatar-profile-head h2{{margin:0 0 5px}}.avatar-profile-current,.avatar-profile-placeholder{{width:82px;height:82px;border-radius:50%;object-fit:cover;border:3px solid #caa45f}}.avatar-profile-placeholder{{display:grid;place-items:center;background:#f5ecee;color:#7b1024;font-size:32px;font-weight:900}}.avatar-status{{display:inline-flex;margin-top:4px;padding:5px 9px;border-radius:999px;font-size:10px;font-weight:900}}.avatar-status.ok{{background:#e7f5ea;color:#236334}}.avatar-status.warn{{background:#fff4dc;color:#76561b}}.avatar-camera-box{{position:relative;width:min(100%,480px);aspect-ratio:1/1;border-radius:22px;overflow:hidden;background:#efe9e8;border:1px solid #eadfdd}}.avatar-camera-box video,.avatar-camera-box canvas{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}.avatar-camera-box canvas{{display:none}}.avatar-empty{{position:absolute;inset:0;display:grid;place-content:center;text-align:center;gap:8px;color:#766b6d}}.avatar-empty span{{font-size:46px;color:#7b1024}}.avatar-capture{{display:none;position:absolute!important;left:50%;bottom:16px;transform:translateX(-50%);width:58px!important;height:58px!important;border-radius:50%!important;padding:0!important;background:#fff!important;color:#7b1024!important;border:5px solid rgba(123,16,36,.22)!important}}.avatar-source-actions,.avatar-save-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px;max-width:480px}}.avatar-source-actions>*,.avatar-save-actions>*{{flex:1 1 180px;text-align:center}}.avatar-secondary,.avatar-upload{{padding:11px 14px;border-radius:10px;font-weight:800;cursor:pointer;background:#f4ecee!important;color:#6d1022!important;border:1px solid #e5d3d8!important}}.avatar-upload input{{display:none}}.avatar-photo-main,.avatar-ai-main{{padding:13px 18px!important;border-radius:11px!important;font-weight:900!important}}.avatar-photo-main{{background:#7b1024!important;color:#fff!important}}.avatar-ai-main{{background:linear-gradient(135deg,#7b1024,#a66a2c)!important;color:#fff!important}}.avatar-photo-main:disabled,.avatar-ai-main:disabled{{opacity:.48;cursor:not-allowed}}.avatar-note{{margin-top:10px}}.avatar-user-img{{width:100%;height:100%;object-fit:cover;border-radius:50%}}@media(max-width:600px){{.avatar-profile-head{{align-items:flex-start}}}}
    </style>
    <script id="profile-avatar-script">(function(){{const video=document.getElementById('avatarVideo'),canvas=document.getElementById('avatarCanvas'),empty=document.getElementById('avatarEmpty'),data=document.getElementById('avatarPhotoData'),mode=document.getElementById('avatarMode'),start=document.getElementById('startCamera'),capture=document.getElementById('capturePhoto'),file=document.getElementById('avatarFile'),save=document.getElementById('savePhoto'),ai=document.getElementById('makeAI');let stream=null;function ready(v){{data.value=v;save.disabled=false;ai.disabled=false;empty.style.display='none';capture.style.display='none';}}start.onclick=async()=>{{try{{if(stream)stream.getTracks().forEach(t=>t.stop());stream=await navigator.mediaDevices.getUserMedia({{video:{{facingMode:'user'}},audio:false}});video.srcObject=stream;video.style.display='block';canvas.style.display='none';empty.style.display='none';capture.disabled=false;capture.style.display='block';}}catch(e){{alert('No fue posible abrir la cámara. Puedes elegir una foto de tu PC.');}}}};capture.onclick=()=>{{const vw=video.videoWidth||720,vh=video.videoHeight||720,s=Math.min(vw,vh),ctx=canvas.getContext('2d');ctx.drawImage(video,(vw-s)/2,(vh-s)/2,s,s,0,0,720,720);canvas.style.display='block';video.style.display='none';ready(canvas.toDataURL('image/jpeg',.9));if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;}};file.onchange=()=>{{const f=file.files&&file.files[0];if(!f)return;if(f.size>5*1024*1024){{alert('La imagen debe pesar menos de 5 MB.');file.value='';return;}}const r=new FileReader();r.onload=()=>{{const img=new Image();img.onload=()=>{{const s=Math.min(img.width,img.height),ctx=canvas.getContext('2d');ctx.drawImage(img,(img.width-s)/2,(img.height-s)/2,s,s,0,0,720,720);canvas.style.display='block';video.style.display='none';ready(canvas.toDataURL('image/jpeg',.9));}};img.src=r.result;}};r.readAsDataURL(f);}};save.onclick=()=>{{mode.value='photo';}};ai.onclick=()=>{{mode.value='ai';}};document.getElementById('avatarForm').addEventListener('submit',e=>{{if(!data.value){{e.preventDefault();alert('Primero selecciona una fotografía.');return;}}if(mode.value==='ai'){{ai.disabled=true;ai.textContent='Creando avatar con IA…';}}else{{save.disabled=true;save.textContent='Guardando…';}}}});}})();</script>'''

def install(app):
    try:
        with app.app_context(): core.db.create_all()
    except Exception: pass
    @app.route('/account/avatar', methods=['POST'])
    def save_avatar():
        uid=session.get('uid')
        if not uid: return redirect('/login')
        profile=multi_user._profile(uid)
        if not profile or not profile.active: return redirect('/login')
        try:
            raw,mime=_decode_data_url(request.form.get('photo_data')); mode=request.form.get('mode','photo'); record=_avatar(uid)
            if not record:
                record=UserAvatar(user_id=uid); core.db.session.add(record)
            record.original_data=raw; record.original_mime=mime
            if mode=='ai':
                generated,generated_mime=_generate_ai_avatar(raw,mime,profile)
                if not generated or len(generated)>MAX_AVATAR_BYTES: raise RuntimeError('El avatar generado no pudo guardarse correctamente.')
                record.avatar_data=generated; record.avatar_mime=generated_mime; flash('Tu avatar con IA fue creado y guardado correctamente.')
            else:
                record.avatar_data=None; record.avatar_mime=mime; flash('Tu fotografía fue guardada como avatar correctamente.')
            record.updated_at=datetime.utcnow(); core.db.session.commit()
        except Exception as e:
            core.db.session.rollback(); flash(str(e))
        return redirect('/account/profile')
    @app.route('/account/avatar/image')
    def avatar_image():
        uid=session.get('uid')
        if not uid: return Response(status=404)
        record=_avatar(uid)
        if not record: return Response(status=404)
        data=record.avatar_data or record.original_data; mime=record.avatar_mime if record.avatar_data else record.original_mime
        if not data: return Response(status=404)
        return Response(data,mimetype=mime or 'image/png',headers={'Cache-Control':'private, no-store, max-age=0'})
    @app.after_request
    def avatar_profile_ui(response):
        if 'text/html' not in response.headers.get('Content-Type','') or not session.get('uid'): return response
        uid=session.get('uid'); html=response.get_data(as_text=True)
        if request.path=='/account/profile' and 'id="profile-avatar-style"' not in html:
            panel=_profile_avatar_panel(uid)
            if '</main>' in html: html=html.replace('</main>',panel+'</main>',1)
            elif '</body>' in html: html=html.replace('</body>',panel+'</body>',1)
        record=_avatar(uid)
        if record and (record.avatar_data or record.original_data):
            stamp=int(record.updated_at.timestamp()) if record.updated_at else 1; img=f'<img class="avatar-user-img" src="/account/avatar/image?v={stamp}" alt="Avatar">'; html=html.replace('<div class="avatar">A</div>',f'<div class="avatar">{img}</div>',1)
        response.set_data(html); response.headers['Content-Length']=str(len(response.get_data())); return response
