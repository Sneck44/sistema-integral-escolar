from flask import request, session


POLISH_CSS = r'''
<style id="ui-polish-v1">
:root{--ui-radius:18px;--ui-radius-sm:12px;--ui-ease:cubic-bezier(.2,.7,.2,1)}

/* Tarjetas más suaves y menos rígidas */
.card,.panel,.stat-card,.quick a,.mobile-brand,.login-pane .card{
  border-radius:var(--ui-radius)!important;
  transition:transform .22s var(--ui-ease),box-shadow .22s var(--ui-ease),border-color .22s var(--ui-ease);
}
.card:hover,.panel:hover{
  box-shadow:0 12px 30px rgba(74,18,32,.10);
}

/* Botones y enlaces de acción */
button,.action-btn,.btn,.wa-btn,.wa-main,
a[href*="/edit"],a[href*="/delete"],a[href*="/exports/"]{
  border-radius:999px!important;
  transition:transform .18s var(--ui-ease),box-shadow .18s var(--ui-ease),filter .18s var(--ui-ease),background .18s var(--ui-ease)!important;
}
button:hover,.action-btn:hover,.btn:hover,.wa-btn:hover,.wa-main:hover,
a[href*="/edit"]:hover,a[href*="/delete"]:hover,a[href*="/exports/"]:hover{
  transform:translateY(-2px);
  filter:brightness(1.03);
  box-shadow:0 10px 22px rgba(123,16,36,.16)!important;
}
button:active,.action-btn:active,.btn:active{transform:translateY(0) scale(.985)}

/* Inputs más amables */
input,select,textarea{border-radius:12px!important;transition:border-color .18s,box-shadow .18s,background .18s}
input:hover,select:hover,textarea:hover{border-color:#cab9bd}

/* Acciones rápidas */
.quick{gap:16px!important}
.quick a{
  min-height:118px!important;
  border:1px solid rgba(123,16,36,.08)!important;
  background:linear-gradient(180deg,#fff 0%,#fdfbfa 100%)!important;
  box-shadow:0 7px 20px rgba(63,22,33,.055)!important;
  position:relative;
  overflow:hidden;
}
.quick a:before{
  content:"";position:absolute;inset:auto -30px -45px auto;width:90px;height:90px;border-radius:50%;
  background:rgba(202,164,95,.09);transition:transform .25s var(--ui-ease);
}
.quick a:hover{
  transform:translateY(-5px)!important;
  border-color:rgba(123,16,36,.20)!important;
  box-shadow:0 15px 30px rgba(74,18,32,.11)!important;
}
.quick a:hover:before{transform:scale(1.25)}
.quick a:hover .quick-icon{transform:scale(1.10) rotate(-3deg)}
.quick-icon{transition:transform .22s var(--ui-ease)}

/* Tarjeta específica de Rúbricas IA */
.quick a.rubric-ai-card{
  background:linear-gradient(145deg,#fff 0%,#fff9f4 100%)!important;
  border-color:rgba(202,164,95,.28)!important;
}
.quick a.rubric-ai-card .quick-icon{
  width:46px;height:46px;border-radius:50%;display:grid;place-items:center;
  background:linear-gradient(145deg,#7b1024,#a31d3a);color:#fff!important;
  box-shadow:0 8px 18px rgba(123,16,36,.20);
}
.quick a.rubric-ai-card .quick-label{font-weight:800;color:#5b1020}
.quick a.rubric-ai-card .quick-sub{font-size:10px;color:#806f73;line-height:1.25}

/* Botones dentro de tarjetas */
.card a[style*="background"],.panel a[style*="background"]{
  border-radius:999px!important;
  transition:transform .18s var(--ui-ease),box-shadow .18s var(--ui-ease),filter .18s!important;
}
.card a[style*="background"]:hover,.panel a[style*="background"]:hover{
  transform:translateY(-2px);filter:brightness(1.04);box-shadow:0 9px 20px rgba(74,18,32,.14)
}

/* Tablas más suaves */
.scroll{border-radius:16px!important}
table{border-radius:14px;overflow:hidden}
tbody tr td{transition:background .15s}

@media(max-width:720px){
  .quick{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:10px!important}
  .quick a{min-height:102px!important;border-radius:16px!important}
}
</style>
'''


def _normalize_rubric_dashboard(html):
    if '<h1>Panel de control</h1>' not in html and 'dashboard-grid' not in html:
        return html

    # Elimina variantes antiguas/sueltas del acceso, conservando el menú lateral.
    old_variants = [
        '<a href="/rubrics/new"><span class="quick-icon">★</span><span>Generar rúbrica IA</span></a>',
        '<a href="/rubrics/new">Generar rúbrica IA</a>',
    ]
    for old in old_variants:
        html = html.replace(old, '')

    # Inserta una sola tarjeta dentro del bloque de acciones rápidas.
    if 'class="rubric-ai-card"' not in html:
        card = (
            '<a class="rubric-ai-card" href="/rubrics/new" aria-label="Generar rúbrica con inteligencia artificial">'
            '<span class="quick-icon">✦</span>'
            '<span class="quick-label">Generar rúbrica IA</span>'
            '<span class="quick-sub">Crear criterios y niveles de desempeño</span>'
            '</a>'
        )
        quick_start = html.find('<div class="quick">')
        if quick_start != -1:
            content_start = quick_start + len('<div class="quick">')
            depth = 1
            pos = content_start
            while pos < len(html):
                next_open = html.find('<div', pos)
                next_close = html.find('</div>', pos)
                if next_close == -1:
                    break
                if next_open != -1 and next_open < next_close:
                    depth += 1
                    pos = next_open + 4
                else:
                    depth -= 1
                    if depth == 0:
                        html = html[:next_close] + card + html[next_close:]
                        break
                    pos = next_close + 6
        else:
            # Respaldo: tarjeta normal dentro del contenido, nunca flotante.
            card_block = (
                '<div class="card"><h2>✦ Rúbricas con IA</h2>'
                '<p class="muted">Genera una rúbrica analítica profesional y después aplícala a tus alumnos.</p>'
                '<a class="action-btn" href="/rubrics/new" style="display:inline-block;background:#7b1024;color:#fff;text-decoration:none;padding:11px 17px;font-weight:800">Generar rúbrica IA</a>'
                '</div>'
            )
            html = html.replace('</main>', card_block + '</main>', 1)
    return html


def install(app):
    @app.after_request
    def ui_polish(response):
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        html = response.get_data(as_text=True)
        if '</head>' in html and 'id="ui-polish-v1"' not in html:
            html = html.replace('</head>', POLISH_CSS + '</head>', 1)
        if session.get('uid') and request.path == '/':
            html = _normalize_rubric_dashboard(html)
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response
