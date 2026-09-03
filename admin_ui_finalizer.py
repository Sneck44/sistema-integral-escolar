import re
from flask import request, session


def _profile():
    uid = session.get('uid')
    if not uid:
        return None
    try:
        import multi_user
        return multi_user._profile(uid)
    except Exception:
        return None


def _is_admin():
    p = _profile()
    return bool(p and p.active and p.role == 'ADMIN')


def _section(label):
    return f'<div class="nav-section-label">{label}</div>'


def _reorder_sidebar(html):
    profile = _profile()
    if not profile or not profile.active or '<nav class="side-nav">' not in html:
        return html

    match = re.search(r'<nav class="side-nav">(.*?)</nav>', html, flags=re.S)
    if not match:
        return html

    content = match.group(1)
    anchors = re.findall(r'<a\b[^>]*href="[^"]+"[^>]*>.*?</a>', content, flags=re.S)

    def href_of(anchor):
        m = re.search(r'href="([^"]+)"', anchor)
        return m.group(1) if m else ''

    by_href = {}
    for anchor in anchors:
        href = href_of(anchor)
        if href and href not in by_href:
            by_href[href] = anchor

    # Garantiza accesos estructurales que son agregados por módulos aditivos.
    by_href.setdefault('/suite', '<a class="nav-link" href="/suite"><span class="nav-icon">◎</span><span>Seguimiento integral</span></a>')
    by_href.setdefault('/account/profile', '<a class="nav-link" href="/account/profile"><span class="nav-icon">◎</span><span>Mi perfil</span></a>')
    by_href.setdefault('/logout', '<a class="nav-link logout" href="/logout"><span class="nav-icon">↪</span><span>Cerrar sesión</span></a>')

    # El administrador conserva Usuarios y Configuración; los demás perfiles no
    # reciben accesos administrativos que su rol no puede utilizar.
    if profile.role == 'ADMIN':
        by_href.setdefault('/users', '<a class="nav-link" href="/users"><span class="nav-icon">♙</span><span>Usuarios</span></a>')
        by_href.setdefault('/config', '<a class="nav-link" href="/config"><span class="nav-icon">⚙</span><span>Configuración</span></a>')
    else:
        by_href.pop('/users', None)
        by_href.pop('/config', None)

    known = {'/','/students','/subjects','/activities','/attendance','/suite','/incidents','/account/profile','/users','/config','/logout'}
    extras = [(href, anchor) for href, anchor in by_href.items() if href not in known]

    parts = ['<nav class="side-nav">']
    parts.append(_section('Principal'))
    if '/' in by_href: parts.append(by_href['/'])

    parts.append(_section('Gestión académica'))
    for href in ('/students','/subjects','/activities','/attendance'):
        if href in by_href: parts.append(by_href[href])

    parts.append(_section('Seguimiento y convivencia'))
    for href in ('/suite','/incidents'):
        if href in by_href: parts.append(by_href[href])

    if extras:
        parts.append(_section('Herramientas'))
        for _href, anchor in extras:
            parts.append(anchor)

    parts.append(_section('Cuenta'))
    if '/account/profile' in by_href: parts.append(by_href['/account/profile'])

    if profile.role == 'ADMIN':
        parts.append(_section('Administración'))
        for href in ('/users','/config'):
            if href in by_href: parts.append(by_href[href])

    parts.append(by_href['/logout'])
    parts.append('</nav>')

    new_nav = ''.join(parts)
    return html[:match.start()] + new_nav + html[match.end():]


def _remove_bottom_navigation(html):
    # El menú lateral/desplegable es la única navegación persistente.
    return re.sub(r'<nav class="bottom-nav">.*?</nav>', '', html, flags=re.S)


def _mobile_menu_button(html):
    # Convierte el icono superior móvil en un botón accesible para abrir el mismo sidebar.
    pattern = r'<div class="mobile-top">\s*<span>☰</span>'
    replacement = '<div class="mobile-top"><button class="mobile-menu-trigger" type="button" onclick="toggleSidebar()" aria-label="Abrir menú" aria-controls="sidebar" aria-expanded="false">☰</button>'
    return re.sub(pattern, replacement, html, count=1)


def _ensure_mobile_menu_runtime(html):
    style = r'''
<style id="single-mobile-menu-v2">
.nav-section-label{padding:12px 14px 4px;color:rgba(255,255,255,.55);font-size:9px;font-weight:850;letter-spacing:.9px;text-transform:uppercase;user-select:none}.nav-section-label:first-child{padding-top:4px}.side-nav .logout{margin-top:12px;border-top:1px solid rgba(255,255,255,.14);border-radius:0;padding-top:14px}
@media(max-width:720px){
 body{padding-bottom:0!important}
 .bottom-nav{display:none!important}
 .sidebar{display:flex!important;position:fixed!important;inset:0 auto 0 0!important;width:min(86vw,300px)!important;max-width:300px!important;transform:translateX(-105%)!important;transition:transform .24s ease!important;z-index:90!important;overflow-y:auto!important;padding-bottom:max(18px,env(safe-area-inset-bottom))!important}
 .sidebar.open{transform:translateX(0)!important}
 .overlay{display:none!important}
 .overlay.open{display:block!important;position:fixed!important;inset:0!important;background:rgba(0,0,0,.48)!important;z-index:80!important}
 .topbar{display:none!important}
 .mobile-top{display:grid!important;grid-template-columns:44px minmax(0,1fr) 44px!important;align-items:center!important;gap:8px!important;padding:5px 10px!important;height:56px!important;position:sticky!important;top:0!important;z-index:70!important}
 .mobile-top b{text-align:center!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
 .mobile-menu-trigger{display:grid!important;place-items:center!important;width:42px!important;height:42px!important;min-height:42px!important;padding:0!important;border:0!important;border-radius:10px!important;background:rgba(255,255,255,.12)!important;color:#fff!important;font-size:24px!important;box-shadow:none!important}
 .mobile-menu-trigger:focus-visible{outline:2px solid #fff!important;outline-offset:2px!important}
 .side-nav{padding-bottom:8px!important}.nav-link{min-height:48px!important}.nav-section-label{padding-top:14px!important}.brand-card{min-height:150px!important}.brand-card img{height:132px!important}
}
</style>
<script id="single-mobile-menu-script-v2">
(function(){
 function setExpanded(value){var b=document.querySelector('.mobile-menu-trigger');if(b)b.setAttribute('aria-expanded',value?'true':'false');}
 function closeMenu(){var s=document.getElementById('sidebar'),o=document.getElementById('overlay');if(s)s.classList.remove('open');if(o)o.classList.remove('open');setExpanded(false);document.body.style.overflow='';}
 function syncButton(){var b=document.querySelector('.mobile-menu-trigger'),s=document.getElementById('sidebar');if(!b||!s)return;b.addEventListener('click',function(){setTimeout(function(){var open=s.classList.contains('open');setExpanded(open);document.body.style.overflow=open?'hidden':'';},0);});}
 function bindLinks(){document.querySelectorAll('.side-nav a').forEach(function(a){if(a.dataset.mobileCloseBound)return;a.dataset.mobileCloseBound='1';a.addEventListener('click',function(){if(window.innerWidth<=720)closeMenu();});});}
 function bindOverlay(){var o=document.getElementById('overlay');if(o&&!o.dataset.mobileCloseBound){o.dataset.mobileCloseBound='1';o.addEventListener('click',closeMenu);}}
 function init(){syncButton();bindLinks();bindOverlay();}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
 window.addEventListener('keydown',function(e){if(e.key==='Escape')closeMenu();});
 window.addEventListener('resize',function(){if(window.innerWidth>720)closeMenu();},{passive:true});
})();
</script>
'''
    if 'id="single-mobile-menu-v2"' not in html and '</head>' in html:
        html = html.replace('</head>', style + '</head>', 1)
    return html


def _ensure_logo_manager(html):
    if request.path != '/config' or not _is_admin() or 'id="document-logos"' in html:
        return html
    try:
        import document_logos
        panel = document_logos._panel()
    except Exception:
        return html
    marker = '<h1>Configuración</h1>'
    start = html.find(marker)
    if start != -1:
        form_end = html.find('</form>', start)
        if form_end != -1:
            pos = form_end + len('</form>')
            return html[:pos] + panel + html[pos:]
    footer = html.find('<footer class="footer">')
    if footer != -1:
        return html[:footer] + panel + html[footer:]
    if '</main>' in html:
        return html.replace('</main>', panel + '</main>', 1)
    return html


def install(app):
    @app.after_request
    def admin_ui_finalizer(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        html = _ensure_logo_manager(html)
        html = _remove_bottom_navigation(html)
        html = _mobile_menu_button(html)
        html = _reorder_sidebar(html)
        html = _ensure_mobile_menu_runtime(html)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
