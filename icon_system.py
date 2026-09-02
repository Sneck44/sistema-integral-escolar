from flask import session


ICON_CSS = r'''
<style id="icon-system-v1">
.ui-icon-svg{width:24px;height:24px;display:block;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round}
.nav-icon .ui-icon-svg{width:22px;height:22px}.quick-icon .ui-icon-svg{width:28px;height:28px}.stat-icon .ui-icon-svg{width:28px;height:28px}.recent-badge .ui-icon-svg{width:22px;height:22px}
.nav-icon,.quick-icon,.stat-icon,.recent-badge{font-family:inherit!important}
.quick-icon{width:54px!important;height:54px!important;min-width:54px!important;min-height:54px!important}
.nav-link .nav-icon{width:42px!important;height:42px!important;min-width:42px!important;min-height:42px!important}
.stat-icon{width:58px!important;height:58px!important;min-width:58px!important;min-height:58px!important}
.nav-icon svg,.quick-icon svg,.stat-icon svg,.recent-badge svg{transition:transform .2s ease}
.nav-link:hover .nav-icon svg,.quick a:hover .quick-icon svg,.stat-card:hover .stat-icon svg{transform:scale(1.08)}
</style>
'''

ICON_JS = r'''
<script id="icon-system-js-v1">
(function(){
 const paths={
  home:'<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10.5V20h14v-9.5"/><path d="M9 20v-6h6v6"/>',
  users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  book:'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
  clipboard:'<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2"/><path d="M9 10h6M9 14h6M9 18h4"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>',
  shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  compass:'<circle cx="12" cy="12" r="9"/><path d="m16 8-2.5 5.5L8 16l2.5-5.5L16 8Z"/>',
  sparkles:'<path d="m12 3-1.4 3.6L7 8l3.6 1.4L12 13l1.4-3.6L17 8l-3.6-1.4L12 3Z"/><path d="m5 14-.8 2.2L2 17l2.2.8L5 20l.8-2.2L8 17l-2.2-.8L5 14ZM19 14l-.6 1.4L17 16l1.4.6L19 18l.6-1.4L21 16l-1.4-.6L19 14Z"/>',
  file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h8"/>',
  chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20V8"/><path d="M2 20h22"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21h-4v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V3h4v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9A1.7 1.7 0 0 0 21 10h.1v4H21a1.7 1.7 0 0 0-1.6 1Z"/>',
  logout:'<path d="M10 17l5-5-5-5"/><path d="M15 12H3"/><path d="M21 19V5a2 2 0 0 0-2-2h-6"/>',
  plus:'<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
  check:'<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
  alert:'<path d="M10.3 3.4 2.6 17a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.4a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>'
 };
 function svg(name){return '<svg class="ui-icon-svg" viewBox="0 0 24 24" aria-hidden="true">'+(paths[name]||paths.file)+'</svg>'}
 function pick(el){
   const a=el.closest('a'); const href=(a&&a.getAttribute('href')||'').toLowerCase(); const text=(a&&a.textContent||el.textContent||'').toLowerCase();
   if(href==='/'||text.includes('inicio')) return 'home';
   if(href.includes('student')||text.includes('alumno')) return 'users';
   if(href.includes('subject')||text.includes('asignatura')) return 'book';
   if(href.includes('activit')||text.includes('actividad')) return 'clipboard';
   if(href.includes('attendance')||text.includes('asistencia')) return 'calendar';
   if(href.includes('incident')||text.includes('convivencia')) return 'shield';
   if(href.includes('diagnostic')||text.includes('diagnóstico')) return 'compass';
   if(href.includes('rubric')||text.includes('rúbrica')) return 'sparkles';
   if(href.includes('trimester')||text.includes('gráfica')) return 'chart';
   if(href.includes('export')||href.includes('.xlsx')||text.includes('excel')) return 'file';
   if(href.includes('users')||text.includes('usuarios')) return 'users';
   if(href.includes('config')||text.includes('configuración')) return 'settings';
   if(href.includes('logout')||text.includes('salir')) return 'logout';
   if(text.includes('agregar')||text.includes('crear')||text.includes('nuevo')) return 'plus';
   if(text.includes('promedio')||text.includes('calificación')) return 'check';
   if(text.includes('incidencia')||text.includes('abierta')) return 'alert';
   return 'file';
 }
 function apply(){document.querySelectorAll('.nav-icon,.quick-icon,.stat-icon,.recent-badge').forEach(el=>{el.innerHTML=svg(pick(el));});}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply);else apply();
})();
</script>
'''


def install(app):
    @app.after_request
    def unified_icons(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if '</head>' in html and 'id="icon-system-v1"' not in html:
            html = html.replace('</head>', ICON_CSS + '</head>', 1)
        if '</body>' in html and 'id="icon-system-js-v1"' not in html:
            html = html.replace('</body>', ICON_JS + '</body>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
