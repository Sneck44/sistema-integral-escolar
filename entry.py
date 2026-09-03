import os
from flask import send_file
import ui_app

app = ui_app.app

BASE_DIR = os.path.dirname(__file__)
LOGO_FILE = os.path.join(BASE_DIR, 'static', 'logo-benito-juarez-final.PNG')
APP_ICON_FILE = os.path.join(BASE_DIR, 'static', 'apple-touch-icon.PNG')


def school_logo_exact():
    return send_file(LOGO_FILE, mimetype='image/png', conditional=True, max_age=0, download_name='logo-benito-juarez-final.PNG')


def apple_touch_icon_exact():
    return send_file(APP_ICON_FILE, mimetype='image/png', conditional=True, max_age=0, download_name='apple-touch-icon.PNG')


app.view_functions['school_logo'] = school_logo_exact
app.add_url_rule('/apple-touch-icon.png', 'apple_touch_icon_png_exact', apple_touch_icon_exact)
app.add_url_rule('/apple-touch-icon-precomposed.png', 'apple_touch_icon_precomposed_exact', apple_touch_icon_exact)
app.add_url_rule('/favicon.png', 'favicon_png_exact', apple_touch_icon_exact)

@app.after_request
def add_ios_app_icon(response):
    content_type = response.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        html = response.get_data(as_text=True)
        if '</head>' in html:
            tags = ('<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png?v=f45126bd">'
                    '<link rel="apple-touch-icon-precomposed" href="/apple-touch-icon-precomposed.png?v=f45126bd">'
                    '<link rel="icon" type="image/png" href="/favicon.png?v=f45126bd">'
                    '<meta name="apple-mobile-web-app-capable" content="yes">'
                    '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
                    '<meta name="apple-mobile-web-app-title" content="Sistema Escolar">')
            html = html.replace('</head>', tags + '</head>', 1); response.set_data(html); response.headers['Content-Length'] = str(len(response.get_data()))
    return response

ui_app.STATIC_LOGO = '/school-logo?v=20260902-finalpng'

# Se registra primero para que su after_request se ejecute al final y deje
# definitivamente ordenado el menú y visible el gestor de logotipos.
from admin_ui_finalizer import install as install_admin_ui_finalizer
install_admin_ui_finalizer(app)

from multi_user import install as install_multi_user
install_multi_user(app)
from admin_user_security import install as install_admin_user_security
install_admin_user_security(app)
from group_workspaces import install as install_group_workspaces
install_group_workspaces(app)
from teacher_group_permissions import install as install_teacher_group_permissions
install_teacher_group_permissions(app)
from teacher_workspace_fix import install as install_teacher_workspace_fix
install_teacher_workspace_fix(app)
from request_actions import install as install_request_actions
install_request_actions(app)
from student_details import install as install_student_details
install_student_details(app)
from ui_polish import install as install_ui_polish
install_ui_polish(app)
from rubric_ai import install as install_rubric_ai
install_rubric_ai(app)
from whatsapp_group import install as install_whatsapp_group
install_whatsapp_group(app)
from diagnostic import install as install_diagnostic
install_diagnostic(app)
from excel_exports import install as install_excel_exports
install_excel_exports(app)
from excel_runtime_fix import install as install_excel_runtime_fix
install_excel_runtime_fix()
from activity_manager import install as install_activity_manager
install_activity_manager(app)
from data_manager import install as install_data_manager
install_data_manager(app)
from trimester_charts import install as install_trimester_charts
install_trimester_charts(app)
from group_export_fix import install as install_group_export_fix
install_group_export_fix()
from teacher_identity import install as install_teacher_identity
install_teacher_identity(app)

from document_logos import install as install_document_logos
install_document_logos(app)
from document_logo_exports import install as install_document_logo_exports
install_document_logo_exports()

from attendance_list_export import install as install_attendance_list_export
install_attendance_list_export(app)
from attendance_ui_fix import install as install_attendance_ui_fix
install_attendance_ui_fix(app)
from profile_avatar import install as install_profile_avatar
install_profile_avatar(app)
from avatar_global_fix import install as install_avatar_global_fix
install_avatar_global_fix(app)
from responsive_runtime import install as install_responsive_runtime
install_responsive_runtime(app)
from icon_system import install as install_icon_system
install_icon_system(app)
from login_animation import install as install_login_animation
install_login_animation(app)
