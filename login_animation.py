from flask import request

LOGIN_ANIMATION_CSS = r'''
<style id="login-logo-animation-v2">
@property --ring-progress{
  syntax:'<percentage>';
  inherits:false;
  initial-value:0%;
}
@keyframes loginLogoEntrance{
  0%{opacity:0;transform:translateY(20px) scale(.94);filter:blur(5px) drop-shadow(0 0 0 rgba(202,164,95,0))}
  65%{opacity:1;transform:translateY(-4px) scale(1.015);filter:blur(0) drop-shadow(0 14px 24px rgba(0,0,0,.16))}
  100%{opacity:1;transform:translateY(0) scale(1);filter:blur(0) drop-shadow(0 10px 18px rgba(0,0,0,.12))}
}
@keyframes loginLogoFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes loginGoldGlow{0%,100%{opacity:.18;transform:scale(.96)}50%{opacity:.42;transform:scale(1.035)}}
@keyframes drawGoldRing{0%{--ring-progress:0%;opacity:.2}12%{opacity:1}100%{--ring-progress:100%;opacity:1}}
@keyframes goldRingPulse{0%,100%{filter:drop-shadow(0 0 5px rgba(202,164,95,.30))}50%{filter:drop-shadow(0 0 13px rgba(246,204,105,.66))}}

.login-logo-box{
  position:relative!important;
  overflow:visible!important;
  isolation:isolate;
}
.login-logo-box:before{
  content:"";
  position:absolute;
  inset:-16px;
  border-radius:34px;
  background:radial-gradient(circle at 50% 50%,rgba(202,164,95,.14) 0%,rgba(202,164,95,.055) 45%,transparent 72%);
  filter:blur(10px);
  z-index:-2;
  animation:loginGoldGlow 4.8s ease-in-out infinite;
  pointer-events:none;
}
.login-logo-box:after{
  content:"";
  position:absolute;
  inset:-8px;
  border-radius:30px;
  padding:3px;
  background:conic-gradient(from -90deg,#f6d27c 0%,#caa45f var(--ring-progress),rgba(202,164,95,.08) var(--ring-progress),rgba(202,164,95,.08) 100%);
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;
  mask-composite:exclude;
  z-index:3;
  pointer-events:none;
  animation:drawGoldRing 2.6s cubic-bezier(.22,.72,.2,1) .2s both,goldRingPulse 3.8s ease-in-out 2.8s infinite;
}
.login-logo-box img{
  position:relative;
  z-index:2;
  transform-origin:center center;
  animation:loginLogoEntrance .95s cubic-bezier(.2,.75,.2,1) both,loginLogoFloat 5.4s ease-in-out 1.1s infinite;
  will-change:transform,filter;
}
.login-logo-box:hover:after{
  box-shadow:0 0 26px rgba(202,164,95,.28);
}
.login-logo-box:hover img{
  animation-play-state:paused;
  transform:translateY(-4px) scale(1.025);
  filter:drop-shadow(0 15px 24px rgba(0,0,0,.18)) drop-shadow(0 0 14px rgba(202,164,95,.18));
  transition:transform .3s ease,filter .3s ease;
}
@supports not (background:conic-gradient(red,blue)){
  .login-logo-box:after{background:transparent;border:3px solid #caa45f}
}
@media(prefers-reduced-motion:reduce){
  .login-logo-box img,.login-logo-box:before,.login-logo-box:after{animation:none!important}
  .login-logo-box:after{--ring-progress:100%}
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
        if '</head>' in html and 'id="login-logo-animation-v2"' not in html:
            html = html.replace('</head>', LOGIN_ANIMATION_CSS + '</head>', 1)
            response.set_data(html)
            response.headers['Content-Length'] = str(len(response.get_data()))
        return response
