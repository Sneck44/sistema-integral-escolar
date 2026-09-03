from flask import request


RESPONSIVE_UI = r'''
<style id="responsive-runtime-v2">
:root{--safe-b:env(safe-area-inset-bottom,0px);--safe-l:env(safe-area-inset-left,0px);--safe-r:env(safe-area-inset-right,0px)}
html{width:100%;max-width:100%;-webkit-text-size-adjust:100%;text-size-adjust:100%;scroll-behavior:smooth}
body{width:100%;max-width:100%;overflow-x:hidden}
img,svg,video,canvas,iframe{max-width:100%;height:auto}
.main-area,.wrap,.card,.panel,.grid,.dashboard-grid,.dashboard-main,.right-rail,.analytics-row,.quick,.stats,.suite-grid,.metric-row,.portfolio-grid,.document-logo-grid,.page-head{min-width:0;max-width:100%}
.card,.panel{max-width:100%}
.scroll,.responsive-table-wrap{display:block;width:100%;max-width:100%;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior-inline:contain;scrollbar-gutter:stable}
.responsive-table-wrap table{margin:0}
input,select,textarea,button{max-width:100%}
button,a,.nav-link,.bottom-nav a{touch-action:manipulation;-webkit-tap-highlight-color:transparent}
button,.btn,[role="button"],input,select,textarea{min-height:42px}
.avatar,.avatar-user-img{overflow:hidden!important;flex:0 0 auto!important}.avatar-user-img{display:block!important;width:100%!important;height:100%!important;object-fit:cover!important;border-radius:inherit!important}

@media(max-width:1180px){
 .topbar{gap:12px!important}.top-meta{gap:10px!important;min-width:0}.admin-copy{max-width:180px}.admin-copy b,.admin-copy small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 .grid,.suite-grid{grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr))!important}
 .document-logo-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@media(max-width:980px){
 .topbar{height:auto!important;min-height:68px;padding:10px 14px!important}.title-copy{min-width:0}.title-copy strong{font-size:17px!important}.title-copy small{font-size:11px!important}.cycle{display:none!important}
 .wrap{width:100%!important;max-width:100%!important;padding:14px!important}
 .card,.panel{padding:15px!important}.dashboard-grid,.analytics-row,.hero-panel{grid-template-columns:minmax(0,1fr)!important}.hero-brand{display:none!important}
 .right-rail{grid-template-columns:repeat(2,minmax(0,1fr))!important}.quick{grid-template-columns:repeat(3,minmax(0,1fr))!important}.stats,.metric-row{grid-template-columns:repeat(2,minmax(0,1fr))!important}
 .suite-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@media(max-width:760px){
 body{padding-bottom:calc(82px + var(--safe-b))!important}
 .wrap{padding:10px 10px 20px!important}.card,.panel{padding:14px!important;border-radius:14px!important;margin-bottom:12px!important}
 h1,.page-head h1{font-size:22px!important;line-height:1.18!important;overflow-wrap:anywhere}.page-head p{font-size:12px!important;line-height:1.45!important}h2{font-size:16px!important}
 .mobile-top{display:flex!important;min-width:0}.mobile-top>*{min-width:0}.mobile-top strong,.mobile-top b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.mobile-brand img{max-height:120px!important;width:auto!important}
 .right-rail{display:block!important}.right-rail .panel{margin-bottom:12px!important}.hero-panel{padding:15px!important}.hero-copy h1{font-size:21px!important}.hero-copy p{font-size:12px!important;line-height:1.5!important}
 .stats,.metric-row{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}.stat-card,.metric-box{min-width:0!important;padding:10px!important}.stat-icon{width:42px!important;height:42px!important;min-width:42px!important;min-height:42px!important}.kpi,.metric-box b{font-size:23px!important}.stat-label,.stat-sub{font-size:10px!important}
 .quick{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}.quick a{min-width:0!important;padding:10px 6px!important;overflow-wrap:anywhere}
 .grid,.suite-grid,.document-logo-grid,.portfolio-grid{display:grid!important;grid-template-columns:minmax(0,1fr)!important;gap:11px!important}.wide{grid-column:1!important}form.grid>*,form .grid>*{min-width:0!important}
 label{font-size:12px!important}input,select,textarea{font-size:16px!important;width:100%!important;min-height:46px!important}textarea{min-height:105px!important}
 button,.btn,.action-btn,.wa-btn,.wa-main,.avatar-upload,a[href*=".xlsx"],a[href*="/exports/"],.doc-actions a,.student-tabs a{min-height:46px!important;max-width:100%!important;white-space:normal!important;line-height:1.2!important}
 .suite-form-actions,.doc-actions,.student-tabs,.avatar-source-actions,.avatar-save-actions{display:grid!important;grid-template-columns:1fr!important;width:100%!important;gap:8px!important}.suite-form-actions>*,.doc-actions>*,.student-tabs>*,.avatar-source-actions>*,.avatar-save-actions>*{width:100%!important;max-width:100%!important;text-align:center!important}
 .card a[style*="background"],.panel a[style*="background"]{display:flex!important;align-items:center!important;justify-content:center!important;width:100%!important;min-height:46px!important;text-align:center!important;padding:11px 14px!important;white-space:normal!important}
 .avatar-profile-head{display:grid!important;grid-template-columns:auto minmax(0,1fr)!important;gap:12px!important}.avatar-profile-card{max-width:100%!important}.avatar-camera-box{width:100%!important;max-width:420px!important;margin-inline:auto!important}.avatar-profile-current,.avatar-profile-placeholder{width:68px!important;height:68px!important}
 .attendance-list-card a{width:100%!important}.scroll,.responsive-table-wrap{margin-inline:0!important;border-radius:10px!important;border-bottom:1px solid rgba(0,0,0,.06)}
 table{min-width:660px!important;width:max-content!important;max-width:none!important}th,td{padding:9px 8px!important;font-size:12px!important;white-space:nowrap}td input,td select{min-width:115px!important;font-size:14px!important;min-height:40px!important}td:nth-child(2){white-space:normal;min-width:190px}
 .footer{display:block!important;text-align:center!important}.footer>*{margin:5px 0!important}.calendar-card{overflow:hidden}.cal-day{width:30px!important;height:30px!important;font-size:11px!important}.cal-week,.cal-grid{gap:1px!important}
 .login-layout{display:block!important;min-height:100svh!important}.login-brand{display:none!important}.login-pane{min-height:100svh!important;padding:18px!important}.login-pane-inner{width:100%!important}.login-pane .card{padding:20px!important}
 .bottom-nav{display:flex!important;position:fixed!important;left:0!important;right:0!important;bottom:0!important;z-index:100!important;min-height:68px!important;padding:6px max(6px,var(--safe-r)) calc(6px + var(--safe-b)) max(6px,var(--safe-l))!important;overflow-x:auto!important;overflow-y:hidden!important;-webkit-overflow-scrolling:touch!important;scroll-snap-type:x proximity;gap:4px!important;background:rgba(255,255,255,.98)!important}.bottom-nav a{display:flex!important;flex:0 0 72px!important;min-width:72px!important;min-height:54px!important;scroll-snap-align:start!important;visibility:visible!important;opacity:1!important}
 nav:not(.bottom-nav){max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
 .modal,.dialog,[role="dialog"]{width:min(720px,calc(100vw - 20px))!important;max-width:calc(100vw - 20px)!important;max-height:calc(100svh - 20px)!important;overflow:auto!important}
 .document-logo-preview{height:100px!important}.suite-card{min-height:0!important}.evidence-card{overflow:hidden}.evidence-card a{overflow-wrap:anywhere}
}
@media(max-width:430px){
 .wrap{padding:8px!important}.card,.panel{padding:12px!important}.stats,.metric-row{grid-template-columns:1fr 1fr!important}.stat-card{gap:7px!important}.stat-icon{width:38px!important;height:38px!important;min-width:38px!important;min-height:38px!important}.kpi,.metric-box b{font-size:21px!important}.quick{grid-template-columns:1fr 1fr!important}.quick a{min-height:92px!important;font-size:11px!important}.quick-icon{width:40px!important;height:40px!important;min-width:40px!important;min-height:40px!important}.avatar-profile-head{grid-template-columns:58px minmax(0,1fr)!important}.avatar-profile-current,.avatar-profile-placeholder{width:56px!important;height:56px!important}.bottom-nav a{flex-basis:68px!important;min-width:68px!important}
}
@media(orientation:landscape) and (max-height:520px){body{padding-bottom:66px!important}.bottom-nav{min-height:58px!important}.bottom-nav a{min-height:46px!important}.modal,.dialog,[role="dialog"]{max-height:calc(100svh - 12px)!important}}
@media print{.bottom-nav,.mobile-top,.workspace-mobile,nav,.no-print{display:none!important}body{padding:0!important;background:#fff!important}.wrap{max-width:none!important;padding:0!important}.card,.panel{box-shadow:none!important;break-inside:avoid}.scroll,.responsive-table-wrap{overflow:visible!important}table{width:100%!important;min-width:0!important}}
</style>
<script id="responsive-runtime-script-v2">
(function(){
 function wrapTables(root){(root||document).querySelectorAll('table').forEach(function(t){if(t.closest('.scroll,.responsive-table-wrap'))return;var w=document.createElement('div');w.className='responsive-table-wrap';t.parentNode.insertBefore(w,t);w.appendChild(t);});}
 function protectControls(root){(root||document).querySelectorAll('button,input,select,textarea,a').forEach(function(el){if(el.hasAttribute('disabled'))return;el.style.removeProperty('display');if(el.tagName==='A'&&el.getAttribute('href'))el.setAttribute('data-responsive-action','1');});}
 function labelTableScroll(){document.querySelectorAll('.responsive-table-wrap,.scroll').forEach(function(w){if(w.scrollWidth>w.clientWidth){w.setAttribute('role','region');w.setAttribute('aria-label','Tabla desplazable horizontalmente');w.setAttribute('tabindex','0');}});}
 function run(){wrapTables();protectControls();labelTableScroll();}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
 var observer=new MutationObserver(function(ms){var changed=false;ms.forEach(function(m){if(m.addedNodes.length)changed=true;});if(changed)requestAnimationFrame(run);});
 if(document.documentElement)observer.observe(document.documentElement,{childList:true,subtree:true});
 window.addEventListener('resize',function(){requestAnimationFrame(labelTableScroll);},{passive:true});
 window.addEventListener('orientationchange',function(){setTimeout(run,120);},{passive:true});
})();
</script>
'''


def install(app):
    @app.after_request
    def responsive_runtime(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        html = response.get_data(as_text=True)
        if '</head>' in html and 'id="responsive-runtime-v2"' not in html:
            html = html.replace('</head>', RESPONSIVE_UI + '</head>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
