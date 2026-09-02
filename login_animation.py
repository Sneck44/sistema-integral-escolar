from flask import request

LOGIN_ANIMATION_CSS = r'''
<style id="login-logo-animation-v1">
@keyframes loginLogoEntrance{
  0%{opacity:0;transform:translateY(20px) scale(.94);filter:blur(5px) drop-shadow(0 0 0 rgba(202,164,95,0))}
  65%{opacity:1;transform:translateY(-4px) scale(1.015);filter:blur(0) drop-shadow(0 14px 24px rgba(0,0,0,.16))}
  100%{opacity:1;transform:translateY(0) scale(1);filter:blur(0) drop-shadow(0 10px 18px rgba(0,0,0,.12))}
}
@keyframes loginLogoFloat{
  0%,100%{transform:translateY(0)}
  50%{transform:translateY(-7px)}
}
@keyframes loginGoldGlow{
  0%,100%{opacity:.22;transform:scale(.92)}
  50%{opacity:.52;transform:scale(1.06)}
}
.login-logo-box{
  position:relative!important;
  overflow:visible!important;
  isolation:isolate;
}
.login-logo-box:before{
  content:"";
  position:absolute;
  width:72%;
  aspect-ratio:1/1;
  left:14%;
  top:12%;
  border-radius:50%;
  background:radial-gradient(circle,rgba(202,164,95,.23) 0%,rgba(202,164,95,.09) 38%,transparent 70%);
  filter:blur(8px);
  z-index:-1;
  animation:loginGoldGlow 4.8s ease-in-out infinite;
  pointer-events:none;
}
.login-logo-box img{
  transform-origin:center center;
  animation:loginLogoEntrance .95s cubic-bezier(.2,.75,.2,1) both,loginLogoFloat 5.4s ease-in-out 1.1s infinite;
  will-change:transform,filter;
}
.login-logo-box:hover img{
  animation-play-state:paused;
  transform:translateY(-4px) scale(1.025);
  filter:drop-shadow(0 15px 24px rgba(0,0,0,.18)) drop-shadow(0 0 14px rgba(202,164,95,.18));
  transition:transform .3s ease,filter .3s ease;
}
@media(prefers-reduced-motion:reduce){
  .login-logo-box img,.login-logo-box:before{animation:none!important}
}
</style>
'''


def install(app):
    @app.after_request
    def login_logo_animation(response):
        if 'text/html' not in response.headers.get('Content-Type',''):
            return response
        if request.path != '/login':
            return response
        html = response.get_data(as_text=True)
        if '</head>' in html and 'id="login-logo-animation-v1"' not in html:
            html = html.replace('</head>', LOGIN_ANIMATION_CSS + '</head>', 1)
            response.set_data(html)
            response.headers['Content-Length'] = str(len(response.get_data()))
        return response
