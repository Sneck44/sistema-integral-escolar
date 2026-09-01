import app as core
from flask import render_template_string

app = core.app


def page(title, body):
    c = core.cfg()
    logged = bool(core.auth())
    nav = ''
    if logged:
        nav = '''
        <aside class="sidebar" id="sidebar">
          <div class="brand-card"><img src="/static/logo.webp" alt="Logo Telesecundaria Benito Juárez"></div>
          <nav class="side-nav">
            <a href="/">⌂ <span>Inicio</span></a>
            <a href="/students">♟ <span>Alumnos</span></a>
            <a href="/subjects">▤ <span>Asignaturas</span></a>
            <a href="/activities">✎ <span>Actividades</span></a>
            <a href="/attendance">✓ <span>Asistencia</span></a>
            <a href="/incidents">! <span>Convivencia</span></a>
            <a href="/config">⚙ <span>Configuración</span></a>
            <a class="logout" href="/logout">↪ <span>Cerrar sesión</span></a>
          </nav>
          <div class="sidebar-foot">INCLUSIÓN, DEMOCRACIA Y PAZ</div>
        </aside>'''

    tpl = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Sistema Integral Escolar</title>
    <style>
    :root{--wine:#71303f;--wine2:#4b1925;--rose:#9c6874;--gold:#c8a36b;--ink:#251d20;--muted:#766d70;--line:#eadfe2;--ok:#2f7759}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;background:linear-gradient(135deg,#faf7f7,#f4edef);color:var(--ink)}a{color:var(--wine)}
    .sidebar{position:fixed;inset:0 auto 0 0;width:250px;background:linear-gradient(180deg,var(--wine2),#683040 60%,#4a1924);padding:14px;color:#fff;display:flex;flex-direction:column;z-index:20;box-shadow:10px 0 35px #4a182418}.brand-card{background:#fff;border-radius:17px;padding:11px;margin-bottom:14px;box-shadow:0 10px 28px #0002}.brand-card img{display:block;width:100%;height:148px;object-fit:contain}.side-nav{display:flex;flex-direction:column;gap:5px;flex:1}.side-nav a{color:#fff;text-decoration:none;padding:11px 13px;border-radius:11px;display:flex;align-items:center;gap:11px;font-weight:650}.side-nav a:hover{background:#ffffff18;transform:translateX(2px)}.side-nav .logout{margin-top:auto}.sidebar-foot{font-size:10px;color:#ead0d7;text-align:center;padding:12px 4px 3px;letter-spacing:.8px}
    .main-area{margin-left:250px;min-height:100vh}.topbar{height:80px;background:#fffffff1;backdrop-filter:blur(12px);border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 28px;position:sticky;top:0;z-index:10}.school-title{display:flex;align-items:center;gap:12px}.school-mark{width:42px;height:42px;border-radius:13px;background:linear-gradient(145deg,var(--wine),var(--wine2));color:#fff;display:grid;place-items:center;font-size:20px;box-shadow:0 8px 20px #71303f2c}.school-title b{font-size:18px;display:block}.school-title small{color:var(--muted)}.top-meta{display:flex;align-items:center;gap:12px}.pill{background:#f5edef;color:var(--wine);padding:9px 12px;border-radius:999px;font-size:13px;font-weight:750}.avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(145deg,var(--wine),#a76373);color:#fff;display:grid;place-items:center;font-weight:850}
    .wrap{max-width:1380px;margin:auto;padding:28px}.card{background:#fff;border:1px solid #eee3e6;border-radius:17px;padding:20px;margin-bottom:18px;box-shadow:0 9px 28px #4a18240b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.kpi-card{position:relative;overflow:hidden;min-height:128px}.kpi-card:after{content:"";position:absolute;width:90px;height:90px;border-radius:50%;right:-28px;top:-28px;background:#71303f0a}.kpi-icon{width:44px;height:44px;border-radius:14px;background:#f6ecef;color:var(--wine);display:grid;place-items:center;font-size:20px;margin-bottom:12px}.kpi{font-size:31px;font-weight:850;letter-spacing:-1px}.muted{color:var(--muted);font-size:13px}h1{margin:0 0 7px;font-size:29px;letter-spacing:-.5px}h2{margin-top:0}.page-head{margin-bottom:20px}.page-head p{color:var(--muted);margin:0}
    .hero{display:grid;grid-template-columns:1.6fr .8fr;gap:18px;margin-bottom:18px}.hero-main{background:linear-gradient(135deg,#fff,#fbf5f6);border:1px solid #eee1e4;border-radius:20px;padding:26px;display:flex;justify-content:space-between;align-items:center;overflow:hidden}.hero-main h1{font-size:31px}.hero-main p{color:var(--muted);max-width:610px}.hero-logo{width:165px;height:150px;object-fit:contain;opacity:.9}.quote{border-radius:20px;padding:24px;color:#fff;background:linear-gradient(145deg,var(--wine),var(--wine2));display:flex;flex-direction:column;justify-content:center;box-shadow:0 12px 30px #71303f25}.quote strong{font-size:17px;line-height:1.45}.quote small{margin-top:12px;color:#ead2d8}
    .quick{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:12px}.quick a{text-decoration:none;color:var(--ink);background:#fbf7f8;border:1px solid #f0e5e7;border-radius:14px;padding:16px;text-align:center;font-weight:750;transition:.2s}.quick a:hover{border-color:#d7b9c0;transform:translateY(-2px);box-shadow:0 8px 18px #71303f12}.quick i{display:grid;place-items:center;margin:0 auto 8px;width:42px;height:42px;border-radius:13px;background:#fff;color:var(--wine);font-style:normal;font-size:19px}
    input,select,textarea,button{width:100%;padding:11px 12px;border:1px solid #dccccf;border-radius:10px;font:inherit;background:#fff;color:var(--ink);outline:none}input:focus,select:focus,textarea:focus{border-color:#a96c7b;box-shadow:0 0 0 3px #71303f12}textarea{min-height:90px;resize:vertical}button{background:linear-gradient(135deg,var(--wine),var(--wine2));color:#fff;border:0;font-weight:800;cursor:pointer;box-shadow:0 8px 18px #71303f24}button:hover{filter:brightness(1.06)}label{font-size:13px;font-weight:750;color:#55484d;display:block}label input,label select,label textarea{margin-top:6px}table{width:100%;border-collapse:collapse;min-width:650px}th,td{padding:12px 11px;border-bottom:1px solid #eee5e7;text-align:left}th{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#76676c;background:#fbf8f9}tr:hover td{background:#fdfafb}.scroll{overflow:auto;border-radius:12px}.alert{padding:12px 14px;border-radius:11px;background:#fff2d8;border:1px solid #f1d9a8;margin-bottom:14px}.danger{background:#fde7e7;border-color:#efbcbc}.wide{grid-column:1/-1}
    .login-layout{min-height:100vh;display:grid;grid-template-columns:1fr 1fr}.login-brand{background:linear-gradient(145deg,#4b1723,#7b3141);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:40px;color:#fff;text-align:center}.login-brand img{max-width:360px;width:82%;background:#fff;border-radius:24px;padding:18px;box-shadow:0 25px 60px #0003}.login-brand h2{margin:24px 0 6px;font-size:28px}.login-brand p{margin:0;color:#ead3d9}.login-pane{display:grid;place-items:center;padding:32px}.auth-card{width:min(470px,100%);background:#fff;border-radius:22px;padding:30px;border:1px solid #eee2e5;box-shadow:0 25px 60px #4b172316}.auth-card h1{margin-top:6px}.mobile-toggle{display:none;background:var(--wine);width:42px;height:42px;padding:0;border-radius:11px}
    @media(max-width:980px){.sidebar{transform:translateX(-100%);transition:.25s}.sidebar.open{transform:translateX(0)}.main-area{margin-left:0}.mobile-toggle{display:block}.hero{grid-template-columns:1fr}.topbar{padding:0 16px}.wrap{padding:20px}}
    @media(max-width:700px){.login-layout{grid-template-columns:1fr}.login-brand{padding:24px}.login-brand img{max-width:220px}.hero-main{padding:20px}.hero-logo{display:none}.hero-main h1{font-size:25px}.grid{grid-template-columns:1fr 1fr}.wrap{padding:15px}.card{padding:15px}}
    @media(max-width:480px){.grid{grid-template-columns:1fr}.school-title small{display:none}.topbar{height:72px}}
    </style></head><body>'''

    if logged:
        tpl += '''<div class="app-shell">''' + nav + '''<section class="main-area"><header class="topbar"><div class="school-title"><button class="mobile-toggle" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button><div class="school-mark">▤</div><div><b>Sistema Integral Escolar</b><small>{{c.school}}</small></div></div><div class="top-meta"><span class="pill">Ciclo {{c.cycle}}</span><div class="avatar">A</div></div></header><main class="wrap">{% with ms=get_flashed_messages() %}{% for m in ms %}<div class="alert">{{m}}</div>{% endfor %}{% endwith %}''' + body + '''</main></section></div>'''
    else:
        tpl += '''<div class="login-layout"><section class="login-brand"><img src="/static/logo.webp" alt="Logo Telesecundaria Benito Juárez"><h2>{{c.school}}</h2><p>Ciclo escolar {{c.cycle}}</p></section><section class="login-pane"><div style="width:min(470px,100%)">{% with ms=get_flashed_messages() %}{% for m in ms %}<div class="alert">{{m}}</div>{% endfor %}{% endwith %}''' + body + '''</div></section></div>'''
    tpl += '</body></html>'
    return render_template_string(tpl, title=title, c=c)


core.page = page


def dashboard():
    r = core.require()
    if r: return r
    students = core.Student.query.filter_by(status='ACTIVO').all()
    av = [core.avg_student(s.id) for s in students]
    av = [x for x in av if x is not None]
    total = core.Attendance.query.count()
    present = core.Attendance.query.filter(core.Attendance.state.in_(['PRESENTE','RETARDO'])).count()
    att = round(present*100/total,1) if total else 0
    avg = round(sum(av)/len(av),2) if av else '—'
    inc = core.Incident.query.filter_by(status='ABIERTA').count()
    subjects = core.Subject.query.count()
    activities = core.Activity.query.count()
    body = f'''<section class="hero"><div class="hero-main"><div><div class="muted">PANEL INSTITUCIONAL</div><h1>¡Bienvenido, Administrador!</h1><p>Gestiona evaluación, asistencia y convivencia escolar desde un mismo espacio organizado y fácil de consultar.</p></div><img class="hero-logo" src="/static/logo.webp" alt="Logo"></div><div class="quote"><strong>“La educación es el arma más poderosa que puedes usar para cambiar el mundo.”</strong><small>— Nelson Mandela</small></div></section>
    <div class="grid"><div class="card kpi-card"><div class="kpi-icon">♟</div><div class="muted">Alumnos activos</div><div class="kpi">{len(students)}</div></div><div class="card kpi-card"><div class="kpi-icon">★</div><div class="muted">Promedio general</div><div class="kpi">{avg}</div></div><div class="card kpi-card"><div class="kpi-icon">✓</div><div class="muted">Asistencia acumulada</div><div class="kpi">{att}%</div></div><div class="card kpi-card"><div class="kpi-icon">!</div><div class="muted">Incidencias abiertas</div><div class="kpi">{inc}</div></div></div>
    <div class="card"><h2>Acciones rápidas</h2><div class="quick"><a href="/students"><i>＋</i>Nuevo alumno</a><a href="/attendance"><i>✓</i>Registrar asistencia</a><a href="/activities"><i>✎</i>Nueva actividad</a><a href="/incidents"><i>!</i>Nueva incidencia</a><a href="/subjects"><i>▤</i>Asignaturas</a><a href="/config"><i>⚙</i>Configuración</a></div></div>
    <div class="grid"><div class="card"><h2>Resumen académico</h2><p class="muted">Asignaturas registradas</p><div class="kpi">{subjects}</div></div><div class="card"><h2>Evaluación</h2><p class="muted">Actividades creadas</p><div class="kpi">{activities}</div></div><div class="card"><h2>Estado del sistema</h2><p style="color:var(--ok);font-weight:800">● Base de datos conectada</p><p class="muted">El sistema continúa utilizando la base de datos configurada en producción.</p></div></div>'''
    return page('Inicio', body)


app.view_functions['dashboard'] = dashboard
