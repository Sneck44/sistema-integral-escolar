from flask import request, session


POLISH_CSS = r'''
<style id="ui-polish-v5">
:root{--ui-radius:18px;--ui-radius-sm:12px;--ui-ease:cubic-bezier(.2,.7,.2,1);--ui-hover:#a31d3a;--ui-hover-dark:#5a0b1b;--ui-gold:#caa45f;--ui-gold-dark:#5a3d0b;--ui-icon:44px;--ui-icon-sm:36px}
.card,.panel,.stat-card,.quick a,.mobile-brand,.login-pane .card{border-radius:var(--ui-radius)!important;transition:transform .22s var(--ui-ease),box-shadow .22s var(--ui-ease),border-color .22s var(--ui-ease),background .22s var(--ui-ease)}
.card:hover,.panel:hover{box-shadow:0 12px 30px rgba(74,18,32,.10)}
button,.action-btn,.btn,.wa-btn,.wa-main,a[href*="/edit"],a[href*="/delete"],a[href*="/exports/"],a[href*=".xlsx"]{border-radius:999px!important;transition:transform .18s var(--ui-ease),box-shadow .18s var(--ui-ease),filter .18s var(--ui-ease),background-color .20s var(--ui-ease),color .20s var(--ui-ease),border-color .20s var(--ui-ease)!important}
button:hover,.action-btn:hover,.btn:hover,.wa-btn:hover,.wa-main:hover,a[href*="/edit"]:hover,a[href*="/exports/"]:hover,a[href*=".xlsx"]:hover{transform:translateY(-2px);background:var(--ui-hover)!important;color:#fff!important;border-color:var(--ui-hover)!important;box-shadow:0 10px 24px rgba(123,16,36,.24)!important}
a[href*="/delete"]:hover{transform:translateY(-2px);background:#b4232f!important;color:#fff!important;border-color:#b4232f!important;box-shadow:0 10px 24px rgba(180,35,47,.22)!important}
button:active,.action-btn:active,.btn:active{transform:translateY(0) scale(.985)}

/* Área institucional del logo: conserva el archivo original y rediseña solamente su marco */
.sidebar{padding-top:0!important;overflow-x:hidden!important}
.brand-card{position:relative!important;margin:0 -9px 16px!important;padding:18px 20px 28px!important;min-height:235px!important;border-radius:0 0 56px 56px!important;background:linear-gradient(155deg,#5a0b1b 0%,#3d0712 100%)!important;border:0!important;border-bottom:2px solid rgba(202,164,95,.9)!important;box-shadow:0 16px 34px rgba(34,3,10,.24)!important;overflow:hidden!important;isolation:isolate}
.brand-card:before{content:"";position:absolute;inset:0;z-index:-2;background:radial-gradient(circle at 18% 16%,rgba(255,255,255,.08) 0 1px,transparent 1.5px);background-size:14px 14px;opacity:.42}
.brand-card:after{content:"";position:absolute;z-index:-1;width:210px;height:210px;border:22px solid rgba(202,164,95,.10);border-radius:50%;right:-105px;top:-100px}
.brand-card img{display:block!important;width:100%!important;height:188px!important;object-fit:contain!important;position:relative!important;z-index:2!important;filter:drop-shadow(0 9px 16px rgba(0,0,0,.18))}
.brand-card .brand-accent{display:none}
.sidebar:before{content:"";position:absolute;top:217px;left:-22px;width:94px;height:94px;border-radius:50%;border:1px solid rgba(202,164,95,.32);pointer-events:none}
.side-nav{position:relative;z-index:2;padding:0 4px!important}

.nav-icon,.quick-icon,.stat-icon,.recent-badge,.mini-mark,.avatar{display:grid!important;place-items:center!important;flex:0 0 auto!important;width:var(--ui-icon)!important;height:var(--ui-icon)!important;min-width:var(--ui-icon)!important;min-height:var(--ui-icon)!important;border-radius:14px!important;font-size:22px!important;line-height:1!important;font-weight:800!important;background:transparent!important;box-shadow:none!important;border:1px solid transparent!important;transition:transform .2s var(--ui-ease),background .2s var(--ui-ease),color .2s var(--ui-ease),box-shadow .2s var(--ui-ease),border-color .2s var(--ui-ease)!important}
.quick-icon,.stat-icon,.recent-badge,.mini-mark{color:#7b1024!important}.quick-icon svg,.stat-icon svg,.recent-badge svg,.mini-mark svg{stroke:currentColor!important}.nav-icon{color:#fff!important}.nav-icon svg{stroke:currentColor!important}
.nav-link:hover .nav-icon,.nav-link.active .nav-icon,.quick a:hover .quick-icon,.quick a.active .quick-icon,.stat-card:hover .stat-icon,.stat-card.active .stat-icon,.recent-item:hover .recent-badge,.recent-item.active .recent-badge{background:var(--ui-gold)!important;color:var(--ui-gold-dark)!important;border-color:rgba(202,164,95,.78)!important;box-shadow:0 9px 20px rgba(202,164,95,.28)!important;transform:scale(1.07)!important}
.nav-link{min-height:54px!important;gap:14px!important;padding:7px 12px!important;transition:background-color .20s var(--ui-ease),transform .18s var(--ui-ease),color .18s var(--ui-ease)!important}.nav-link:hover{background:rgba(202,164,95,.12)!important;transform:translateX(3px)}.nav-link.active{background:rgba(202,164,95,.18)!important;color:#fff!important}.nav-link .nav-icon{width:42px!important;height:42px!important;min-width:42px!important;min-height:42px!important;font-size:21px!important;border-radius:13px!important}
input,select,textarea{border-radius:12px!important;transition:border-color .18s,box-shadow .18s,background .18s}input:hover,select:hover,textarea:hover{border-color:#cab9bd}
.quick{gap:16px!important}.quick a{min-height:126px!important;border:1px solid rgba(123,16,36,.08)!important;border-radius:var(--ui-radius)!important;text-decoration:none;background:linear-gradient(180deg,#fff 0%,#fdfbfa 100%)!important;box-shadow:0 7px 20px rgba(63,22,33,.055)!important;position:relative;overflow:hidden;transition:transform .22s var(--ui-ease),box-shadow .22s var(--ui-ease),border-color .22s var(--ui-ease),background .22s var(--ui-ease),color .22s var(--ui-ease)!important}.quick a:before{content:"";position:absolute;inset:auto -30px -45px auto;width:90px;height:90px;border-radius:50%;background:rgba(202,164,95,.08);transition:transform .25s var(--ui-ease),background .25s var(--ui-ease)}.quick a:hover{transform:translateY(-5px)!important;background:linear-gradient(145deg,#7b1024 0%,#a31d3a 100%)!important;color:#fff!important;border-color:#7b1024!important;box-shadow:0 16px 32px rgba(74,18,32,.20)!important}.quick a:hover:before{transform:scale(1.35);background:rgba(202,164,95,.15)}.quick a:hover .quick-label,.quick a:hover .quick-sub{color:#fff!important}.quick-icon{width:54px!important;height:54px!important;min-width:54px!important;min-height:54px!important;font-size:25px!important;border-radius:16px!important}
.quick a.rubric-ai-card{background:linear-gradient(145deg,#fff 0%,#fff9f4 100%)!important;border-color:rgba(202,164,95,.22)!important}.quick a.rubric-ai-card .quick-icon{background:transparent!important;color:#7b1024!important;box-shadow:none!important;border-color:transparent!important}.quick a.rubric-ai-card .quick-label{font-weight:800;color:#5b1020}.quick a.rubric-ai-card .quick-sub{font-size:10px;color:#806f73;line-height:1.25}.quick a.rubric-ai-card:hover{background:linear-gradient(145deg,#6d0d20,#a31d3a)!important}.quick a.rubric-ai-card:hover .quick-icon{background:var(--ui-gold)!important;color:var(--ui-gold-dark)!important;box-shadow:0 9px 20px rgba(202,164,95,.28)!important}
.stat-card{gap:16px!important}.stat-icon{width:58px!important;height:58px!important;min-width:58px!important;min-height:58px!important;border-radius:17px!important;font-size:26px!important}.recent-badge{width:44px!important;height:44px!important;min-width:44px!important;min-height:44px!important;border-radius:14px!important;font-size:20px!important}.mini-mark{width:54px!important;height:54px!important;min-width:54px!important;min-height:54px!important;border-radius:16px!important;font-size:24px!important}.avatar{width:46px!important;height:46px!important;min-width:46px!important;min-height:46px!important;border-radius:14px!important;font-size:18px!important;background:transparent!important;color:#7b1024!important;border:1px solid rgba(123,16,36,.16)!important}.admin-box:hover .avatar{background:var(--ui-gold)!important;color:var(--ui-gold-dark)!important;border-color:var(--ui-gold)!important;box-shadow:0 9px 20px rgba(202,164,95,.25)!important}
.card a[style*="background"],.panel a[style*="background"]{border-radius:999px!important;transition:transform .18s var(--ui-ease),box-shadow .18s var(--ui-ease),background .20s var(--ui-ease),color .20s var(--ui-ease)!important}.card a[style*="background"]:hover,.panel a[style*="background"]:hover{transform:translateY(-2px);background:var(--ui-hover)!important;color:#fff!important;box-shadow:0 9px 20px rgba(74,18,32,.18)!important}.scroll{border-radius:16px!important}table{border-radius:14px;overflow:hidden}tbody tr td{transition:background .15s}tbody tr:hover td{background:#fff8f5!important}
@media(max-width:720px){:root{--ui-icon:40px}.quick{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:10px!important}.quick a{min-height:112px!important;border-radius:16px!important}.quick-icon{width:48px!important;height:48px!important;min-width:48px!important;min-height:48px!important;font-size:23px!important}.nav-link .nav-icon{width:40px!important;height:40px!important;min-width:40px!important;min-height:40px!important}.mobile-brand{position:relative!important;overflow:hidden!important;border:1px solid rgba(202,164,95,.35)!important;border-radius:22px!important;background:linear-gradient(155deg,#fff,#fffaf3)!important}.mobile-brand:after{content:"";position:absolute;left:12%;right:12%;bottom:0;height:3px;border-radius:999px;background:linear-gradient(90deg,transparent,var(--ui-gold),transparent)}}
</style>
'''


def _normalize_rubric_dashboard(html):
    if '<h1>Panel de control</h1>' not in html and 'dashboard-grid' not in html:return html
    for old in ['<a href="/rubrics/new"><span class="quick-icon">★</span><span>Generar rúbrica IA</span></a>','<a href="/rubrics/new">Generar rúbrica IA</a>']:html=html.replace(old,'')
    if 'class="rubric-ai-card"' not in html:
        card=('<a class="rubric-ai-card" href="/rubrics/new" aria-label="Generar rúbrica con inteligencia artificial"><span class="quick-icon">✦</span><span class="quick-label">Generar rúbrica IA</span><span class="quick-sub">Crear criterios y niveles de desempeño</span></a>')
        quick_start=html.find('<div class="quick">')
        if quick_start!=-1:
            content_start=quick_start+len('<div class="quick">');depth=1;pos=content_start
            while pos<len(html):
                next_open=html.find('<div',pos);next_close=html.find('</div>',pos)
                if next_close==-1:break
                if next_open!=-1 and next_open<next_close:depth+=1;pos=next_open+4
                else:
                    depth-=1
                    if depth==0:html=html[:next_close]+card+html[next_close:];break
                    pos=next_close+6
    return html


def install(app):
    @app.after_request
    def ui_polish(response):
        if 'text/html' not in response.headers.get('Content-Type',''):return response
        html=response.get_data(as_text=True)
        if '</head>' in html and 'id="ui-polish-v5"' not in html:html=html.replace('</head>',POLISH_CSS+'</head>',1)
        if session.get('uid') and request.path=='/':html=_normalize_rubric_dashboard(html)
        response.set_data(html);response.headers['Content-Length']=str(len(response.get_data()));return response
