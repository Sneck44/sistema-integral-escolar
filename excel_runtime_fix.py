"""Correcciones de compatibilidad para exportaciones XlsxWriter.

Este módulo se instala después de excel_exports para sustituir únicamente
las funciones con incompatibilidades, sin alterar los datos ni las rutas.
"""
import excel_exports as exports


def _add_signatures_fixed(ws, last_data_row, cols):
    f = ws.book_formats
    last = max(1, cols - 1)
    sig_row = last_data_row + 4
    left_end = max(1, last // 2 - 1)
    right_start = min(last, last // 2 + 1)

    ws.merge_range(sig_row, 0, sig_row, left_end,
                   '________________________________________', f['signature'])
    ws.merge_range(sig_row + 1, 0, sig_row + 1, left_end,
                   'NOMBRE Y FIRMA DEL DOCENTE', f['signature'])
    ws.merge_range(sig_row, right_start, sig_row, last,
                   '________________________________________', f['signature'])
    ws.merge_range(sig_row + 1, right_start, sig_row + 1, last,
                   'Vo. Bo. DIRECTORA', f['signature'])
    ws.merge_range(sig_row + 2, right_start, sig_row + 2, last,
                   'MTRA. NELLY AZUCENA HERNÁNDEZ PICAZO', f['signature_name'])
    ws.set_row(sig_row, 24)
    ws.set_row(sig_row + 1, 18)
    ws.set_row(sig_row + 2, 18)

    # XlsxWriter usa print_area(); set_print_area() no existe.
    ws.print_area(0, 0, sig_row + 2, last)


def install():
    exports._add_signatures = _add_signatures_fixed
