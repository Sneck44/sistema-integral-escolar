from flask import request, session


MODERN_UI = r'''
<style id="modern-ui-2026">
:root{
  --wine:#71152a;--wine-strong:#54101f;--wine-soft:#f8edf0;
  --gold:#c9a55e;--gold-soft:#fbf6e9;--ink:#211d22;--muted:#736b72;
  --surface:#ffffff;--surface-2:#faf9f8;--canvas:#f4f3f2;--line:#e8e3e4;
  --success:#287a4d;--danger:#b63140;--info:#3b6f9c;
  --radius:18px;--radius-sm:12px;--shadow:0 8px 28px rgba(48,28,35,.07);
  --shadow-lg:0 18px 50px rgba(48,18,29,.12);
}
*{box-sizing:border-box}
body{background:var(--canvas)!important;color:var(--ink)!important;letter-spacing:-.006em}
.app-shell{background:linear-gradient(135deg,#f7f5f4 0%,#f2f1f0 55%,#f8f6f3 100%)}

/* Navegación principal */
.sidebar{width:272px!important;padding:18px 14px!important;background:linear-gradient(180deg,#641225 0%,#4b0d1b 100%)!important;box-shadow:12px 0 38px rgba(47,8,18,.13)!important}
.brand-card{display:block!important;width:100%!important;height:auto!important;min-height:0!important;margin:0 0 16px!important;padding:6px 8px 14px!important;border:0!important;border-bottom:1px solid rgba(214,179,105,.32)!important;border-radius:0!important;background:transparent!important;box-shadow:none!important;overflow:visible!important;isolation:auto!important}
.brand-card:before,.brand-card:after,.sidebar:before{display:none!important}
.brand-logo{display:flex!important;align-items:center!important;justify-content:center!important;width:100%!important;height:auto!important;min-height:158px!important;flex:none!important;border:0!important;border-radius:0!important;background:transparent!important;overflow:visible!important;box-shadow:none!important}
.brand-card .brand-logo img{display:block!important;width:auto!important;max-width:100%!important;height:158px!important;max-height:158px!important;aspect-ratio:auto!important;object-fit:contain!important;object-position:center!important;background:transparent!important;filter:drop-shadow(0 0 1px rgba(255,255,255,.98)) drop-shadow(0 0 5px rgba(255,255,255,.68)) drop-shadow(0 10px 16px rgba(25,3,9,.28))!important}
.brand-copy{display:none!important}
.side-nav{padding:0!important;gap:3px!important}
.nav-section-label{margin:14px 10px 5px!important;padding:0!important;color:rgba(255,255,255,.46)!important;font-size:9px!important;letter-spacing:1.25px!important}
.nav-link{min-height:45px!important;padding:6px 9px!important;gap:10px!important;border-radius:11px!important;color:rgba(255,255,255,.82)!important;font-size:12px!important;font-weight:650!important}
.nav-link .nav-icon{width:32px!important;height:32px!important;min-width:32px!important;min-height:32px!important;border-radius:9px!important;color:rgba(255,255,255,.9)!important}
.nav-link .nav-icon .ui-icon-svg{width:19px!important;height:19px!important}
.nav-link:hover{transform:none!important;background:rgba(255,255,255,.08)!important;color:#fff!important}
.nav-link.active{background:#fff!important;color:var(--wine)!important;box-shadow:0 8px 22px rgba(28,4,11,.18)!important}
.nav-link.active .nav-icon{background:var(--wine-soft)!important;color:var(--wine)!important;border-color:transparent!important;box-shadow:none!important;transform:none!important}
.nav-link:hover .nav-icon{background:rgba(255,255,255,.10)!important;color:#fff!important;border-color:transparent!important;box-shadow:none!important;transform:none!important}
.nav-link.logout{margin-top:12px!important;padding-top:7px!important;border:0!important;background:rgba(255,255,255,.04)}
.sidebar-foot{margin-top:auto;display:flex;align-items:center;gap:8px;padding:14px 10px 2px;color:rgba(255,255,255,.58);font-size:10px}.status-dot{width:7px;height:7px;border-radius:50%;background:#70d99a;box-shadow:0 0 0 4px rgba(112,217,154,.12)}

/* Encabezado */
.main-area{margin-left:272px!important}.topbar{height:78px!important;padding:0 28px!important;background:rgba(255,255,255,.88)!important;backdrop-filter:blur(18px);border-bottom:1px solid rgba(93,61,71,.08)!important}
.title-copy small{font-size:9px!important;letter-spacing:1.35px;color:#9a858c;font-weight:800}.title-copy strong{font-size:18px!important;color:var(--ink)!important;margin-top:3px}
.cycle{display:grid!important;gap:2px!important;padding-right:20px;border-right:1px solid var(--line)}.cycle small{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.7px}.cycle b{font-size:12px;color:var(--wine)}
.account-shortcut{display:flex!important;align-items:center;gap:9px;text-decoration:none;padding:6px 9px 6px 6px;border:1px solid var(--line);border-radius:13px;background:#fff;color:var(--ink)}
.account-avatar,.mobile-profile{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;background:linear-gradient(145deg,var(--wine),#9b2942);color:#fff;font-size:11px;font-weight:850;text-decoration:none}.account-shortcut>span:last-child{display:grid;gap:1px}.account-shortcut b{font-size:11px}.account-shortcut small{font-size:9px;color:var(--muted)}
.wrap{max-width:1540px!important;padding:24px 28px 32px!important}

/* Encabezados y superficies */
.page-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin:0 0 18px}.page-heading h1{margin:3px 0 4px!important;font-size:27px!important;letter-spacing:-.035em}.page-heading p{margin:0;color:var(--muted);font-size:12px}.eyebrow,.hero-kicker{display:block;color:var(--wine);font-size:9px;font-weight:850;letter-spacing:1.3px}.heading-meta{min-width:130px;padding:10px 13px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.75)}.heading-meta span{display:block;font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}.heading-meta b{display:block;margin-top:2px;color:var(--wine);font-size:14px}
.panel,.card{border:1px solid rgba(91,61,71,.09)!important;border-radius:var(--radius)!important;background:rgba(255,255,255,.96)!important;box-shadow:var(--shadow)!important}
.panel:hover,.card:hover{box-shadow:var(--shadow)!important}.panel{padding:20px!important;margin-bottom:15px!important}.card{padding:20px!important;margin-bottom:16px!important}
.section-head,.analytics-head{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:16px}.section-head h2,.analytics-head h2{margin:3px 0 0!important;font-size:16px!important;letter-spacing:-.02em}
h1{color:var(--ink);letter-spacing:-.035em}h2,h3{color:var(--ink)}

/* Panel principal */
.dashboard-grid{grid-template-columns:minmax(0,1fr) 316px!important;gap:16px!important}
.hero-panel{min-height:225px!important;padding:30px!important;grid-template-columns:minmax(0,1fr) 315px!important;background:linear-gradient(135deg,#fff 0%,#fff 58%,#fbf4f5 100%)!important;border-color:rgba(113,21,42,.12)!important}
.hero-panel:before{content:"";position:absolute;width:260px;height:260px;border-radius:50%;right:-80px;top:-100px;background:radial-gradient(circle,rgba(201,165,94,.18),rgba(201,165,94,0) 68%)}.hero-panel:after{width:150px!important;height:150px!important;right:260px!important;bottom:-112px!important;border-color:rgba(113,21,42,.05)!important}
.hero-copy h1{font-size:29px!important;color:var(--ink)!important;line-height:1.14!important;margin:8px 0 12px!important}.hero-copy p{font-size:12px!important;line-height:1.65!important;color:var(--muted)!important;max-width:580px!important}
.hero-actions{display:flex;gap:9px;margin-top:19px}.hero-actions a{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 15px;border-radius:11px;background:var(--wine);color:#fff;text-decoration:none;font-size:11px;font-weight:800;box-shadow:0 7px 18px rgba(113,21,42,.18)}.hero-actions a.secondary{background:#fff;color:var(--wine);border:1px solid #ddc8ce;box-shadow:none}
.hero-brand{grid-template-columns:104px 1fr!important;gap:14px!important;padding:15px;border:1px solid rgba(113,21,42,.09);border-radius:17px;background:rgba(255,255,255,.68)}.hero-brand img{width:104px!important;height:104px!important}.quote-mark{font-size:34px!important}.quote-text{font-size:12px!important;line-height:1.45!important}.quote-author{font-size:10px!important;margin-top:5px}
.stats{gap:11px!important;margin:14px 0!important}.stat-card{position:relative;min-height:110px!important;padding:16px!important;border-radius:16px!important;border:1px solid rgba(91,61,71,.08)!important;box-shadow:0 6px 20px rgba(48,28,35,.05)!important;overflow:hidden}
.stat-icon{width:44px!important;height:44px!important;min-width:44px!important;min-height:44px!important;border-radius:12px!important;background:var(--wine-soft)!important;color:var(--wine)!important;border:0!important;box-shadow:none!important}.stat-icon.gold{background:var(--gold-soft)!important;color:#9b752c!important}.stat-icon .ui-icon-svg{width:23px!important;height:23px!important}.stat-label{font-size:10px!important;color:var(--muted)}.kpi{font-size:26px!important;color:var(--ink);margin:2px 0!important}.stat-sub{font-size:9px!important;color:var(--wine)!important}
.quick-panel{padding:20px!important}.quick{grid-template-columns:repeat(6,minmax(0,1fr))!important;gap:10px!important}.quick a{min-height:116px!important;padding:12px 7px!important;border-radius:15px!important;border:1px solid rgba(91,61,71,.08)!important;background:var(--surface-2)!important;box-shadow:none!important;gap:5px!important;isolation:isolate}.quick a:hover{transform:translateY(-3px)!important;background:#fff!important;color:var(--ink)!important;border-color:#d9bcc4!important;box-shadow:0 12px 25px rgba(71,27,40,.09)!important}.quick-icon{width:42px!important;height:42px!important;min-width:42px!important;min-height:42px!important;border-radius:12px!important;background:var(--wine-soft)!important;color:var(--wine)!important}.quick a:hover .quick-icon{background:var(--wine)!important;color:#fff!important;transform:none!important;box-shadow:none!important}.quick-label{font-size:11px;font-weight:800}.quick-sub{font-size:8px!important;color:var(--muted)!important;line-height:1.25}.quick a:hover .quick-label{color:var(--ink)!important}.quick a:hover .quick-sub{color:var(--muted)!important}
/* Ningún adorno debe cubrir el texto o los iconos de controles interactivos. */
button:before,button:after,.btn:before,.btn:after,.action-btn:before,.action-btn:after,
.quick a:before,.quick a:after,.hero-actions a:before,.hero-actions a:after,
.doc-actions a:before,.doc-actions a:after,.student-tabs a:before,.student-tabs a:after,
.card a[style*="background"]:before,.card a[style*="background"]:after,
.panel a[style*="background"]:before,.panel a[style*="background"]:after,
.stat-card:before,.stat-card:after{content:none!important;display:none!important}
.quick a>* ,.hero-actions a>* ,.doc-actions a>* ,.student-tabs a>*{position:relative;z-index:2}
.analytics-row{grid-template-columns:minmax(0,1.55fr) minmax(250px,.75fr)!important;gap:14px!important}.analytics-card{min-height:242px!important}.line-chart polyline{stroke:var(--wine)!important;stroke-width:3!important}.line-chart circle{fill:#fff!important;stroke:var(--wine);stroke-width:3}.attendance-summary .ring-wrap{justify-content:flex-start!important}.ring{width:128px!important;height:128px!important;background:conic-gradient(var(--wine) var(--pct),#f0ecee 0)!important}.ring:after{width:96px!important;height:96px!important}.ring-copy b{font-size:25px!important}.ring-copy span{font-size:9px!important;color:var(--muted)}.trend{display:grid;gap:4px}.trend b{font-size:12px;color:var(--success)}.trend small{max-width:100px;line-height:1.35}
.recent-panel{padding-bottom:12px!important}.recent-item{grid-template-columns:36px 1fr auto!important;padding:10px 0!important}.recent-badge{width:34px!important;height:34px!important;min-width:34px!important;min-height:34px!important;border-radius:10px!important;background:var(--wine-soft)!important;color:var(--wine)!important}.recent-badge .ui-icon-svg{width:18px!important;height:18px!important}.recent-item b{font-size:11px!important}.recent-item small,.recent-time{font-size:9px!important}
.calendar-card{padding:19px!important}.calendar-title{justify-content:space-between!important;margin-bottom:16px!important}.calendar-title span{font-size:14px}.calendar-title a{font-size:9px;text-decoration:none;color:var(--wine);font-weight:800}.calendar-head strong{font-size:12px}.cal-day{font-size:10px!important}.upcoming-panel .event{padding:10px 0}.event-dot{width:7px!important;height:7px!important}.event b{font-size:11px!important}.event small{font-size:9px!important}

/* Formularios, tablas y mensajes */
label{display:grid;gap:6px;color:#544c52;font-size:11px!important;font-weight:750!important}input,select,textarea{width:100%;border:1px solid #dcd5d8!important;border-radius:11px!important;background:#fff!important;color:var(--ink)!important;padding:10px 12px!important;box-shadow:0 1px 0 rgba(255,255,255,.7) inset}input:focus,select:focus,textarea:focus{outline:0!important;border-color:#b77484!important;box-shadow:0 0 0 4px rgba(113,21,42,.08)!important}textarea{line-height:1.5}
button,.btn,.action-btn{border-radius:11px!important;background:var(--wine)!important;color:#fff!important;box-shadow:0 6px 16px rgba(113,21,42,.15)!important;font-size:11px!important;font-weight:800!important}button:hover,.btn:hover,.action-btn:hover{transform:translateY(-1px)!important;background:var(--wine-strong)!important;box-shadow:0 9px 20px rgba(113,21,42,.19)!important}
.alert{border:1px solid #ead69d!important;border-left:4px solid var(--gold)!important;border-radius:12px!important;background:#fffaf0!important;color:#5f4b1e!important;padding:12px 14px!important;box-shadow:0 5px 16px rgba(71,53,18,.05)}
.scroll,.responsive-table-wrap{border:1px solid var(--line);border-radius:13px!important;background:#fff}.card.scroll{border:1px solid rgba(91,61,71,.09)!important}.scroll table,.responsive-table-wrap table{border-radius:0!important}table{border-collapse:separate!important;border-spacing:0!important}th{padding:11px 10px!important;background:#f7f4f5!important;color:#675a60!important;font-size:9px!important;text-transform:uppercase;letter-spacing:.55px;border-bottom:1px solid var(--line)!important}td{padding:11px 10px!important;font-size:11px!important;border-bottom:1px solid #f0edef!important}tbody tr:last-child td{border-bottom:0!important}tbody tr:hover td{background:#fcf8f9!important}
.muted{color:var(--muted)!important}.footer{margin-top:26px!important;padding:18px 4px 5px!important;border-top:1px solid rgba(91,61,71,.10)!important;color:var(--muted)!important;font-size:9px!important}.footer span:first-child{display:grid;gap:3px}.footer strong{color:var(--wine);font-size:10px}.footer small{font-size:9px}

/* Acceso */
.login-layout{background:linear-gradient(135deg,#4f0d1d,#7a1830 48%,#f3ece9 48%)!important}.login-brand{background:transparent!important}.login-logo-box{max-width:380px!important;border:0!important;border-radius:0!important;padding:26px!important;background:transparent!important;box-shadow:none!important}.login-logo-box img{background:transparent!important;filter:drop-shadow(0 0 1px rgba(255,255,255,.98)) drop-shadow(0 0 7px rgba(255,255,255,.72)) drop-shadow(0 16px 28px rgba(25,3,9,.28))!important}.login-pane{background:transparent!important}.login-pane .card{border-radius:24px!important;padding:32px!important;box-shadow:0 22px 55px rgba(45,20,28,.13)!important}.login-pane h1{font-size:28px!important}.login-pane button{min-height:48px}

@media(max-width:1180px){.quick{grid-template-columns:repeat(3,minmax(0,1fr))!important}.hero-panel{grid-template-columns:minmax(0,1fr) 270px!important}.dashboard-grid{grid-template-columns:minmax(0,1fr) 290px!important}}
@media(max-width:980px){.sidebar{width:272px!important}.main-area{margin-left:0!important}.dashboard-grid{grid-template-columns:1fr!important}.right-rail{display:grid!important;grid-template-columns:1fr 1fr!important}.hero-panel{grid-template-columns:1fr!important}.hero-brand{display:none!important}}
@media(max-width:760px){
 .sidebar{width:min(88vw,290px)!important;padding:14px 12px!important}.brand-card{height:auto!important;min-height:0!important;padding-top:2px!important}.brand-logo{min-height:142px!important}.brand-card .brand-logo img{width:auto!important;max-width:100%!important;height:142px!important;max-height:142px!important}.main-area{margin:0!important}.mobile-top{height:58px!important;padding:7px 12px!important;background:rgba(91,15,34,.96)!important;backdrop-filter:blur(12px)}.mobile-profile{width:36px;height:36px}
 .wrap{padding:13px 11px 22px!important}.page-heading{align-items:flex-start;margin-bottom:13px}.page-heading h1{font-size:23px!important}.page-heading p{max-width:250px;font-size:10px!important}.heading-meta{display:none}
 .panel,.card{padding:15px!important;border-radius:15px!important}.hero-panel{padding:20px!important;min-height:0!important}.hero-copy h1{font-size:24px!important}.hero-actions{display:grid;grid-template-columns:1fr 1fr}.hero-actions a{padding:0 10px;font-size:10px}
 .stats{grid-template-columns:1fr 1fr!important}.stat-card{min-height:96px!important;padding:12px!important}.stat-icon{width:38px!important;height:38px!important;min-width:38px!important;min-height:38px!important}.kpi{font-size:22px!important}
 .quick{grid-template-columns:1fr 1fr!important}.quick a{min-height:102px!important}.analytics-row,.right-rail{display:block!important}.attendance-summary .ring-wrap{justify-content:center!important}
 .section-head{align-items:flex-start}.section-head>.muted{display:none}.footer{text-align:left!important}.footer>span:last-child{margin-top:9px!important}
 .login-layout{background:#f5f1f0!important}.login-pane{padding:18px 12px!important}.login-pane .card{padding:24px!important}
}
@media(max-width:420px){.hero-actions{grid-template-columns:1fr}.stats{gap:7px!important}.stat-card{gap:8px!important}.stat-sub{line-height:1.2}.quick a{min-height:96px!important}.page-heading p{max-width:210px}}
@media print{.sidebar,.topbar,.mobile-top,.sidebar-foot,.hero-actions{display:none!important}.main-area{margin:0!important}.wrap{padding:0!important;background:#fff}.panel,.card{border:1px solid #ddd!important;box-shadow:none!important}}
</style>
'''


def install(app):
    @app.after_request
    def modern_ui(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        html = response.get_data(as_text=True)
        if '</head>' in html and 'id="modern-ui-2026"' not in html:
            html = html.replace('</head>', MODERN_UI + '</head>', 1)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
