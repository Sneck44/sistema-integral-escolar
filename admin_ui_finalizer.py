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


def _reorder_sidebar(html):
    if '<nav class="side-nav">' not in html:
        return html

    match = re.search(r'<nav class="side-nav">(.*?)</nav>', html, flags=re.S)
    if not match:
        return html

    content = match.group(1)
    anchors = re.findall(r'<a\b[^>]*href="[^"]+"[^>]*>.*?</a>', content, flags=re.S)
    if not anchors:
        return html

    def href_of(anchor):
        m = re.search(r'href="([^"]+)"', anchor)
        return m.group(1) if m else ''

    by_href = {}
    unknown = []
    for anchor in anchors:
        href = href_of(anchor)
        if href and href not in by_href:
            by_href[href] = anchor
        elif href:
            unknown.append(anchor)

    priority = [
        '/',
        '/students',
        '/attendance',
        '/activities',
        '/subjects',
        '/suite',
        '/incidents',
        '/account/profile',
        '/users',
        '/config',
    ]

    ordered = []
    for href in priority:
        if href in by_href:
            ordered.append(by_href.pop(href))

    # Conserva cualquier módulo adicional que pueda agregarse en el futuro.
    for anchor in anchors:
        href = href_of(anchor)
        if href in by_href and href != '/logout':
            ordered.append(by_href.pop(href))

    if '/logout' in by_href:
        ordered.append(by_href['/logout'])
    else:
        logout = next((a for a in anchors if href_of(a) == '/logout'), None)
        if logout and logout not in ordered:
            ordered.append(logout)

    new_nav = '<nav class="side-nav">' + ''.join(ordered) + '</nav>'
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
<style id="single-mobile-menu-v1">
@media(max-width:720px){
 body{padding-bottom:0!important}
 .bottom-nav{display:none!important}
 .sidebar{display:flex!important;position:fixed!important;inset:0 auto 0 0!important;width:min(86vw,300px)!important;max-width:300px!important;transform:translateX(-105%)!important;transition:transform .24s ease!important;z-index:90!important;overflow-y:auto!important;padding-bottom:max(18px,env(safe-area-inset-bottom))!important}
 .sidebar.open{transform:translateX(0)!important}
 .overlay{display:none!important}
 .overlay.open{display:block!important;position:fixed!important;inset:0!important;background:rgba(0,0,0,.48)!important;z-index:80!important}
 .topbar{display:none!important}
 .mobile-top{display:grid!important;grid-template-columns:44px minmax(0,1fr) 44px!important;align-items:center!important;gap:8px!important;padding:5px 10px!important;height:56px!important}
 .mobile-top b{text-align:center!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
 .mobile-menu-trigger{display:grid!important;place-items:center!important;width:42px!important;height:42px!important;min-height:42px!important;padding:0!important;border:0!important;border-radius:10px!important;background:rgba(255,255,255,.12)!important;color:#fff!important;font-size:24px!important;box-shadow:none!important}
 .mobile-menu-trigger:focus-visible{outline:2px solid #fff!important;outline-offset:2px!important}
 .side-nav{padding-bottom:8px!important}
 .nav-link{min-height:48px!important}
 .nav-link.logout{margin-top:12px!important}
}
</style>
<script id="single-mobile-menu-script-v1">
(function(){
 function setExpanded(value){var b=document.querySelector('.mobile-menu-trigger');if(b)b.setAttribute('aria-expanded',value?'true':'false');}
 function closeMenu(){var s=document.getElementById('sidebar'),o=document.getElementById('overlay');if(s)s.classList.remove('open');if(o)o.classList.remove('open');setExpanded(false);}
 function syncButton(){var b=document.querySelector('.mobile-menu-trigger'),s=document.getElementById('sidebar');if(!b||!s)return;b.addEventListener('click',function(){setTimeout(function(){setExpanded(s.classList.contains('open'));},0);});}
 function bindLinks(){document.querySelectorAll('.side-nav a').forEach(function(a){if(a.dataset.mobileCloseBound)return;a.dataset.mobileCloseBound='1';a.addEventListener('click',function(){if(window.innerWidth<=720)closeMenu();});});}
 function bindOverlay(){var o=document.getElementById('overlay');if(o&&!o.dataset.mobileCloseBound){o.dataset.mobileCloseBound='1';o.addEventListener('click',closeMenu);}}
 function init(){syncButton();bindLinks();bindOverlay();}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
 window.addEventListener('keydown',function(e){if(e.key==='Escape')closeMenu();});
})();
</script>
'''
    if 'id="single-mobile-menu-v1"' not in html and '</head>' in html:
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
