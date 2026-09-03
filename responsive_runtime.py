from flask import request, session


RESPONSIVE_UI = r'''
<style id="responsive-runtime-v1">
html,body{max-width:100%;overflow-x:hidden}
img,svg,video,canvas{max-width:100%}
.main-area,.wrap,.card,.panel,.grid,.dashboard-grid,.dashboard-main,.right-rail,.analytics-row,.quick,.stats{min-width:0}
.card,.panel{max-width:100%}
.scroll,.responsive-table-wrap{width:100%;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;overscroll-behavior-inline:contain}
.responsive-table-wrap table{margin:0}
input,select,textarea,button,a{max-width:100%}
button,a,.nav-link,.bottom-nav a{touch-action:manipulation}
.avatar,.avatar-user-img{overflow:hidden!important;flex:0 0 auto!important}
.avatar-user-img{display:block!important;width:100%!important;height:100%!important;max-width:100%!important;max-height:100%!important;object-fit:cover!important;border-radius:inherit!important}

@media(max-width:1120px){
 .topbar{gap:14px}.top-meta{gap:12px}.admin-copy{max-width:190px}.admin-copy b,.admin-copy small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 .grid{grid-template-columns:repeat(auto-fit,minmax(min(210px,100%),1fr))!important}
}

@media(max-width:900px){
 .topbar{height:auto!important;min-height:72px;padding:10px 16px!important}.title-copy strong{font-size:18px!important}.title-copy small{font-size:12px!important}.cycle{display:none!important}
 .wrap{width:100%!important;max-width:100%!important;padding:16px!important}
 .card,.panel{padding:16px!important}
 .dashboard-grid,.analytics-row{grid-template-columns:minmax(0,1fr)!important}
 .right-rail{grid-template-columns:repeat(2,minmax(0,1fr))!important}
 .hero-panel{grid-template-columns:minmax(0,1fr)!important}.hero-brand{display:none!important}
 .quick{grid-template-columns:repeat(3,minmax(0,1fr))!important}
 .stats{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}

@media(max-width:720px){
 html{-webkit-text-size-adjust:100%}body{width:100%;padding-bottom:78px!important}
 .wrap{padding:10px 10px 18px!important}
 .card,.panel{padding:14px!important;border-radius:14px!important;margin-bottom:12px!important}
 h1,.page-head h1{font-size:22px!important;line-height:1.18!important}.page-head p{font-size:12px!important;line-height:1.45!important}
 h2{font-size:15px!important}
 .mobile-top{display:flex!important;min-width:0}.mobile-top>*{min-width:0}.mobile-top strong,.mobile-top b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 .mobile-brand img{height:auto!important;max-height:130px!important}
 .right-rail{display:block!important}.right-rail .panel{margin-bottom:12px!important}
 .hero-panel{padding:15px!important}.hero-copy h1{font-size:21px!important}.hero-copy p{font-size:12px!important;line-height:1.5!important}
 .stats{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}.stat-card{min-width:0!important;padding:10px!important}.stat-icon{width:44px!important;height:44px!important;min-width:44px!important;min-height:44px!important}.kpi{font-size:25px!important}.stat-label,.stat-sub{font-size:10px!important}
 .quick{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}.quick a{min-width:0!important;padding:10px 6px!important;word-break:break-word}
 .grid{display:grid!important;grid-template-columns:minmax(0,1fr)!important;gap:11px!important}.wide{grid-column:1!important}
 form.grid>*,form .grid>*{min-width:0!important}
 label{font-size:12px!important}input,select,textarea{font-size:16px!important;width:100%!important;min-height:44px!important}textarea{min-height:100px!important}
 button,.btn,.action-btn,.wa-btn,.wa-main,.avatar-upload,a[href*=".xlsx"],a[href*="/exports/"]{min-height:44px!important;max-width:100%!important;white-space:normal!important;line-height:1.2!important}
 .card a[style*="background"],.panel a[style*="background"]{display:flex!important;align-items:center!important;justify-content:center!important;width:100%!important;min-height:44px!important;text-align:center!important;padding:11px 14px!important;white-space:normal!important}
 .avatar-source-actions,.avatar-save-actions{display:grid!important;grid-template-columns:1fr!important;width:100%!important;max-width:100%!important}.avatar-source-actions>*,.avatar-save-actions>*{width:100%!important;max-width:100%!important}
 .avatar-profile-head{display:grid!important;grid-template-columns:auto minmax(0,1fr)!important;gap:12px!important}.avatar-profile-card{max-width:100%!important}.avatar-camera-box{width:100%!important;max-width:420px!important;margin-inline:auto!important}.avatar-profile-current,.avatar-profile-placeholder{width:68px!important;height:68px!important}
 .attendance-list-card a{width:100%!important}
 .scroll,.responsive-table-wrap{margin-inline:0!important;border-radius:10px!important}
 table{min-width:620px!important;width:max-content!important;max-width:none!important}th,td{padding:9px 8px!important;font-size:12px!important;white-space:nowrap}td input,td select{min-width:110px!important;font-size:14px!important;min-height:38px!important}td:nth-child(2){white-space:normal;min-width:190px}
 .footer{display:block!important;text-align:center!important}.footer>*{margin:5px 0!important}
 .calendar-card{overflow:hidden}.cal-day{width:30px!important;height:30px!important;font-size:11px!important}.cal-week,.cal-grid{gap:1px!important}
 .login-layout{display:block!important;min-height:100svh!important}.login-brand{display:none!important}.login-pane{min-height:100svh!important;padding:18px!important}.login-pane-inner{width:100%!important}.login-pane .card{padding:20px!important}
 .bottom-nav{display:flex!important;position:fixed!important;left:0!important;right:0!important;bottom:0!important;z-index:70!important;min-height:66px!important;padding:6px max(6px,env(safe-area-inset-right)) calc(6px + env(safe-area-inset-bottom)) max(6px,env(safe-area-inset-left))!important;overflow-x:auto!important;overflow-y:hidden!important;-webkit-overflow-scrolling:touch!important;gap:4px!important}.bottom-nav a{flex:1 0 62px!important;min-width:62px!important;min-height:52px!important}
 .modal,.dialog,[role="dialog"]{max-width:calc(100vw - 20px)!important;max-height:calc(100svh - 20px)!important;overflow:auto!important}
}

@media(max-width:420px){
 .wrap{padding:8px!important}.card,.panel{padding:12px!important}
 .stats{grid-template-columns:1fr 1fr!important}.stat-card{gap:8px!important}.stat-icon{width:38px!important;height:38px!important;min-width:38px!important;min-height:38px!important}.kpi{font-size:22px!important}
 .quick{grid-template-columns:1fr 1fr!important}.quick a{min-height:96px!important;font-size:11px!important}.quick-icon{width:42px!important;height:42px!important;min-width:42px!important;min-height:42px!important}
 .avatar-profile-head{grid-template-columns:60px minmax(0,1fr)!important}.avatar-profile-current,.avatar-profile-placeholder{width:58px!important;height:58px!important}
}
</style>
<script id="responsive-runtime-script">
(function(){
  function wrapTables(){
    document.querySelectorAll('table').forEach(function(t){
      if(t.closest('.scroll,.responsive-table-wrap')) return;
      var w=document.createElement('div');w.className='responsive-table-wrap';
      t.parentNode.insertBefore(w,t);w.appendChild(t);
    });
  }
  function normalizeActions(){
    document.querySelectorAll('a,button,label.avatar-upload').forEach(function(el){
      if(window.innerWidth<=720 && el.getBoundingClientRect().right>window.innerWidth+2){el.style.maxWidth='100%';}
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){wrapTables();normalizeActions();});
  else{wrapTables();normalizeActions();}
  window.addEventListener('resize',normalizeActions,{passive:true});
})();
</script>
'''


def install(app):
    @app.after_request
    def responsive_runtime(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        html = response.get_data(as_text=True)
        if '</head>' in html and 'id="responsive-runtime-v1"' not in html:
            html = html.replace('</head>', RESPONSIVE_UI + '</head>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
