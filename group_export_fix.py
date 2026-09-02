import app as core
from group_workspaces import active_group_tuple


def install():
    try:
        import excel_exports
        if not getattr(excel_exports, '_group_meta_patched', False):
            original_setup = excel_exports._setup

            def scoped_setup(ws, title, cols, landscape=True):
                original_setup(ws, title, cols, landscape)
                grade, group_name = active_group_tuple()
                c = core.cfg()
                last = max(0, cols - 1)
                ws.write(9, 0, f'GRADO: {grade}     GRUPO: {group_name}     CICLO ESCOLAR: {c.cycle}', ws.book_formats['meta'])

            excel_exports._setup = scoped_setup
            excel_exports._group_meta_patched = True
    except Exception:
        pass

    try:
        import trimester_charts
        if not getattr(trimester_charts, '_group_meta_patched', False):
            original_export = trimester_charts._export_workbook

            def scoped_trimester_export():
                c = core.cfg()
                original_grade, original_group = c.grade, c.group
                grade, group_name = active_group_tuple()
                with core.db.session.no_autoflush:
                    c.grade, c.group = grade, group_name
                    try:
                        return original_export()
                    finally:
                        c.grade, c.group = original_grade, original_group

            trimester_charts._export_workbook = scoped_trimester_export
            trimester_charts._group_meta_patched = True
    except Exception:
        pass
