from flask import request, session


POLISH_CSS = r'''
<style id="ui-polish-v3">
:root{--ui-radius:18px;--ui-radius-sm:12px;--ui-ease:cubic-bezier(.2,.7,.2,1);--ui-hover:#a31d3a;--ui-hover-dark:#5a0b1b;--ui-gold:#caa45f;--ui-icon:44px;--ui-icon-sm:36px}

.card,.panel,.stat-card,.quick a,.mobile-brand,.login-pane .card{
  border-radius:var(--ui-radius)!important;
  transition:transform .22s var(--ui-ease),box-shadow .22s var(--ui-ease),border-color .22s var(--ui-ease),background .22s var(--ui-ease);
}
.card:hover,.panel:hover{box-shadow:0 12px 30px rgba(74,18,32,.10)}

button,.action-btn,.btn,.wa-btn,.wa-main,
a[href*="/edit"],a[href*="/delete"],a[href*="/exports/"],a[href*=".xlsx"]{
  border-radius:999px!important;
  transition:transform .18s var(--ui-ease),box-shadow .18s var(--ui-ease),filter .18s var(--ui-ease),background-color .20s var(--ui-ease),color .20s var(--ui-ease),border-color .20s var(--ui-ease)!important;
}
button:hover,.action-btn:hover,.btn:hover,.wa-btn:hover,.wa-main:hover,
a[href*="/edit"]:hover,a[href*="/exports/"]:hover,a[href*=".xlsx"]:hover{
  transform:translateY(-2px);background:var(--ui-hover)!important;color:#fff!important;border-color:var(--ui-hover)!important;
  box-shadow:0 10px 24px rgba(123,16,36,.24)!important;
}
a[href*="/delete"]:hover{transform:translateY(-2px);background:#b4232f!important;color:#fff!important;border-color:#b4232f!important;box-shadow:0 10px 24px rgba(180,35,47,.22)!important}
button:active,.action-btn:active,.btn:active{transform:translateY(0) scale(.985)}

/* Sistema visual único para iconos */
.nav-icon,.quick-icon,.stat-icon,.recent-badge,.mini-mark,.avatar{
  display:grid!important;place-items:center!important;flex:0 0 auto!important;
  width:var(--ui-icon)!important;height:var(--ui-icon)!important;min-width:var(--ui-icon)!important;min-height:var(--ui-icon)!important;
  border-radius:14px!important;font-size:22px!important;line-height:1!important;font-weight:800!important;
  background:linear-gradient(145deg,#8a1530,#651022)!important;color:#fff!important;
  box-shadow:0 7px 16px rgba(87,14,35,.16)!important;
  transition:transform .2s var(--ui-ease),background .2s var(--ui-ease),color .2s var(--ui-ease),box-shadow .2s var(--ui-ease)!important;
}
.nav-link:nth-child(even) .nav-icon,.quick a:nth-child(even) .quick-icon,.stat-card:nth-child(even) .stat-icon,.recent-item:nth-child(even) .recent-badge{
  background:linear-gradient(145deg,#d3b06a,#b88b39)!important;color:#4e0917!important;
}
.nav-link:hover .nav-icon,.quick a:hover .quick-icon,.stat-card:hover .stat-icon{
  transform:scale(1.08) rotate(-2deg)!important;background:var(--ui-gold)!important;color:#4e0917!important;
  box-shadow:0 10px 22px rgba(202,164,95,.24)!important;
}

/* Menú lateral: iconos más grandes y alineados */
.nav-link{min-height:54px!important;gap:14px!important;padding:7px 12px!important;transition:background-color .20s var(--ui-ease),transform .18s var(--ui-ease),color .18s var(--ui-ease)!important}
.nav-link:hover{background:rgba(202,164,95,.28)!important;transform:translateX(3px)}
.nav-link.active{background:rgba(196,27,58,.72)!important}
.nav-link .nav-icon{width:40px!important;height:40px!important;min-width:40px!important;min-height:40px!important;font-size:20px!important;border-radius:12px!important}

input,select,textarea{border-radius:12px!important;transition:border-color .18s,box-shadow .18s,background .18s}
input:hover,select:hover,textarea:hover{border-color:#cab9bd}

.quick{gap:16px!important}
.quick a{
  min-height:126px!important;border:1px solid rgba(123,16,36,.08)!important;border-radius:var(--ui-radius)!important;text-decoration:none;
  background:linear-gradient(180deg,#fff 0%,#fdfbfa 100%)!important;box-shadow:0 7px 20px rgba(63,22,33,.055)!important;
  position:relative;overflow:hidden;transition:transform .22s var(--ui-ease),box-shadow .22s var(--ui-ease),border-color .22s var(--ui-ease),background .22s var(--ui-ease),color .22s var(--ui-ease)!important;
}
.quick a:before{content:"";position:absolute;inset:auto -30px -45px auto;width:90px;height:90px;border-radius:50%;background:rgba(202,164,95,.11);transition:transform .25s var(--ui-ease),background .25s var(--ui-ease)}
.quick a:hover{transform:translateY(-5px)!important;background:linear-gradient(145deg,#7b1024 0%,#a31d3a 100%)!important;color:#fff!important;border-color:#7b1024!important;box-shadow:0 16px 32px rgba(74,18,32,.20)!important}
.quick a:hover:before{transform:scale(1.35);background:rgba(202,164,95,.20)}
.quick a:hover .quick-label,.quick a:hover .quick-sub{color:#fff!important}
.quick-icon{width:50px!important;height:50px!important;min-width:50px!important;min-height:50px!important;font-size:24px!important;border-radius:15px!important}

.quick a.rubric-ai-card{background:linear-gradient(145deg,#fff 0%,#fff9f4 100%)!important;border-color:rgba(202,164,95,.28)!important}
.quick a.rubric-ai-card .quick-icon{width:50px!important;height:50px!important;border-radius:15px!important;background:linear-gradient(145deg,#7b1024,#a31d3a)!important;color:#fff!important;box-shadow:0 8px 18px rgba(123,16,36,.20)!important}
.quick a.rubric-ai-card .quick-label{font-weight:800;color:#5b1020}.quick a.rubric-ai-card .quick-sub{font-size:10px;color:#806f73;line-height:1.25}
.quick a.rubric-ai-card:hover{background:linear-gradient(145deg,#6d0d20,#a31d3a)!important}

/* Métricas e iconos secundarios */
.stat-card{gap:16px!important}.stat-icon{width:56px!important;height:56px!important;min-width:56px!important;min-height:56px!important;border-radius:16px!important;font-size:25px!important}
.recent-badge{width:42px!important;height:42px!important;min-width:42px!important;min-height:42px!important;border-radius:13px!important;font-size:20px!important}
.mini-mark{width:52px!important;height:52px!important;min-width:52px!important;min-height:52px!important;border-radius:15px!important;font-size:24px!important}
.avatar{width:46px!important;height:46px!important;min-width:46px!important;min-height:46px!important;border-radius:14px!important;font-size:18px!important}

.card a[style*="background"],.panel a[style*="background"]{border-radius:999px!important;transition:transform .18s var(--ui-ease),box-shadow .18s var(--ui-ease),background .20s var(--ui-ease),color .20s var(--ui-ease)!important}
.card a[style*="background"]:hover,.panel a[style*="background"]:hover{transform:translateY(-2px);background:var(--ui-hover)!important;color:#fff!important;box-shadow:0 9px 20px rgba(74,18,32,.18)!important}

.scroll{border-radius:16px!important}table{border-radius:14px;overflow:hidden}tbody tr td{transition:background .15s}tbody tr:hover td{background:#fff8f5!important}

@media(max-width:720px){
  :root{--ui-icon:40px}.quick{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:10px!important}.quick a{min-height:112px!important;border-radius:16px!important}
  .quick-icon{width:46px!important;height:46px!important;min-width:46px!important;min-height:46px!important;font-size:22px!important}
  .nav-link .nav-icon{width:38px!important;height:38px!important;min-width:38px!important;min-height:38px!important}
}
</style>
'''


def _normalize_rubric_dashboard(html):
    if '<h1>Panel de control</h1>' not in html and 'dashboard-grid' not in html:
        return html
    old_variants = [
        '<a href="/rubrics/new"><span class="quick-icon">★</span><span>Generar rúbrica IA</span></a>',
        '<a href="/rubrics/new">Generar rúbrica IA</a>',
    ]
    for old in old_variants:
        html = html.replace(old, '')
    if 'class="rubric-ai-card"' not in html:
        card = ('<a class="rubric-ai-card" href="/rubrics/new" aria-label="Generar rúbrica con inteligencia artificial">'
                '<span class="quick-icon">✦</span><span class="quick-label">Generar rúbrica IA</span>'
                '<span class="quick-sub">Crear criterios y niveles de desempeño</span></a>')
        quick_start = html.find('<div class="quick">')
        if quick_start != -1:
            content_start = quick_start + len('<div class="quick">'); depth = 1; pos = content_start
            while pos < len(html):
                next_open = html.find('<div', pos); next_close = html.find('</div>', pos)
                if next_close == -1: break
                if next_open != -1 and next_open < next_close:
                    depth += 1; pos = next_open + 4
                else:
                    depth -= 1
                    if depth == 0:
                        html = html[:next_close] + card + html[next_close:]; break
                    pos = next_close + 6
        else:
            card_block = ('<div class="card"><h2>✦ Rúbricas con IA</h2><p class="muted">Genera una rúbrica analítica profesional y después aplícala a tus alumnos.</p>'
                          '<a class="action-btn" href="/rubrics/new" style="display:inline-block;background:#7b1024;color:#fff;text-decoration:none;padding:11px 17px;font-weight:800">Generar rúbrica IA</a></div>')
            html = html.replace('</main>', card_block + '</main>', 1)
    return html


def install(app):
    @app.after_request
    def ui_polish(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        html = response.get_data(as_text=True)
        if '</head>' in html and 'id="ui-polish-v3"' not in html:
            html = html.replace('</head>', POLISH_CSS + '</head>', 1)
        if session.get('uid') and request.path == '/':
            html = _normalize_rubric_dashboard(html)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
