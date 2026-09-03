import xlsxwriter


def _image_options(data, mime, x_scale, y_scale, x_offset=3, y_offset=2):
    import io
    stream = io.BytesIO(data)
    ext = 'png' if mime == 'image/png' else ('webp' if mime == 'image/webp' else 'jpg')
    return f'logo.{ext}', {'image_data': stream, 'x_scale': x_scale, 'y_scale': y_scale, 'x_offset': x_offset, 'y_offset': y_offset, 'object_position': 1}


def install():
    try:
        import excel_exports as ex
        import document_logos
    except Exception:
        return

    original_setup = ex._setup

    def setup_with_configured_logos(ws, title, cols, landscape=True):
        # Ejecuta el formato base, pero evita que los archivos estaticos sean insertados.
        old_left, old_right = ex.PUEBLA_LOGOS, ex.TELESEC_LOGO
        try:
            ex.PUEBLA_LOGOS = '__document_logo_managed_left__'
            ex.TELESEC_LOGO = '__document_logo_managed_right__'
            original_setup(ws, title, cols, landscape)
        finally:
            ex.PUEBLA_LOGOS, ex.TELESEC_LOGO = old_left, old_right
        last = max(0, cols - 1)
        try:
            left, lmime = document_logos.get_logo_bytes('left')
            if left:
                name, opts = _image_options(left, lmime, 0.43, 0.43)
                ws.insert_image(0, 0, name, opts)
            right, rmime = document_logos.get_logo_bytes('right')
            if right:
                name, opts = _image_options(right, rmime, 0.48, 0.48)
                ws.insert_image(0, max(0, last - 1), name, opts)
        except Exception:
            pass

    ex._setup = setup_with_configured_logos
