from flask import session


def install(app):
    @app.after_request
    def keep_user_avatar_compact(response):
        if 'text/html' not in response.headers.get('Content-Type', '') or not session.get('uid'):
            return response
        html = response.get_data(as_text=True)
        if 'id="avatar-global-fix"' not in html and '</head>' in html:
            css = '''<style id="avatar-global-fix">
.avatar{width:42px!important;height:42px!important;min-width:42px!important;min-height:42px!important;max-width:42px!important;max-height:42px!important;border-radius:50%!important;overflow:hidden!important;display:flex!important;align-items:center!important;justify-content:center!important;flex:0 0 42px!important}
.avatar .avatar-user-img{width:42px!important;height:42px!important;min-width:42px!important;min-height:42px!important;max-width:42px!important;max-height:42px!important;object-fit:cover!important;object-position:center!important;border-radius:50%!important;display:block!important;margin:0!important;padding:0!important}
.account-avatar .avatar-user-img,.mobile-profile .avatar-user-img,.nav-icon .avatar-user-img{display:block!important;width:100%!important;height:100%!important;min-width:0!important;min-height:0!important;max-width:100%!important;max-height:100%!important;margin:0!important;padding:0!important;border-radius:inherit!important;object-fit:cover!important;object-position:center!important}
</style>'''
            html = html.replace('</head>', css + '</head>', 1)
            response.set_data(html)
            response.headers['Content-Length'] = str(len(response.get_data()))
        return response
