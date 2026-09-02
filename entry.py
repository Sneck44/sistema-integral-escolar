from flask import Response
import ui_app

LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" role="img" aria-label="Telesecundaria Benito Juárez">
<rect width="800" height="400" rx="18" fill="#ffffff"/>
<g transform="translate(34 28)">
  <circle cx="155" cy="172" r="132" fill="#7b1024" opacity="0.07"/>
  <path d="M74 302c20-45 48-70 77-79-19-12-31-33-31-58 0-42 30-77 71-84 19-3 39 1 55 11-18 2-32 12-43 28 20-6 41 0 54 14-17 1-31 8-41 21 10 2 19 8 25 17-10 5-18 13-23 23-5 10-6 23-3 35 7 26 29 44 55 46-25 12-53 17-81 14-18-2-36-8-52-16-18 8-39 17-63 28z" fill="#151515"/>
  <path d="M77 300c39-7 67-9 105-9 35 0 70 3 105 11-15 18-33 33-55 43H128c-20-10-37-25-51-45z" fill="#151515"/>
</g>
<g transform="translate(330 64)">
  <text x="0" y="12" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700" letter-spacing="2" fill="#b69243">INCLUSIÓN, DEMOCRACIA Y PAZ</text>
  <rect x="0" y="30" width="390" height="4" rx="2" fill="#b69243"/>
  <text x="0" y="106" font-family="Arial, Helvetica, sans-serif" font-size="52" font-weight="800" letter-spacing="1" fill="#7b1024">TELESECUNDARIA</text>
  <text x="0" y="172" font-family="Arial, Helvetica, sans-serif" font-size="66" font-weight="900" letter-spacing="1" fill="#171717">BENITO JUÁREZ</text>
  <rect x="0" y="194" width="390" height="4" rx="2" fill="#7b1024"/>
  <text x="0" y="240" font-family="Arial, Helvetica, sans-serif" font-size="26" font-weight="700" fill="#5d5558">Beristain, Ahuazotepec, Pue.</text>
  <text x="0" y="286" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" letter-spacing="1.5" fill="#b69243">SISTEMA INTEGRAL ESCOLAR</text>
</g>
</svg>'''


def school_logo_svg():
    return Response(
        LOGO_SVG,
        mimetype='image/svg+xml',
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0',
        },
    )

# Un único origen de logo para toda la interfaz.
ui_app.app.view_functions['school_logo'] = school_logo_svg
ui_app.STATIC_LOGO = '/school-logo?v=20260902-svg1'

app = ui_app.app
