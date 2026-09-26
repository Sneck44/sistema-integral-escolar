import io
import random
from datetime import date
from html import escape

from flask import request, redirect, session, flash, send_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

import app as core
import sisat


READINGS = {
    '1': [
        {
            'title': 'La libreta de las lluvias',
            'text': (
                'En San Miguel, las lluvias llegaban cada vez en fechas distintas. Unas veces comenzaban en mayo y otras se retrasaban hasta julio. '
                'Mara, estudiante de primer grado, notó que su abuelo anotaba en una libreta el día de la primera tormenta, la cantidad de agua que reunía '
                'en una cubeta y los cambios que observaba en las plantas. Ella decidió continuar el registro. Colocó un recipiente graduado en el patio y, '
                'cada mañana, escribió la medida antes de vaciarlo. También entrevistó a varias personas mayores de la comunidad. Algunas recordaban que antes '
                'las lluvias eran más constantes; otras explicaron que ahora había menos árboles en los cerros cercanos. Mara no tomó esas opiniones como una '
                'respuesta definitiva. Comparó las notas familiares con información de la estación meteorológica y descubrió que un solo año no bastaba para '
                'afirmar que el clima había cambiado. En la escuela presentó una gráfica y propuso conservar el registro durante varios ciclos escolares. '
                'Sus compañeros añadieron fotografías, fechas de siembra y observaciones sobre el nivel del arroyo. La libreta dejó de ser un recuerdo familiar '
                'y se convirtió en un proyecto colectivo para comprender mejor el lugar donde vivían.'
            ),
            'questions': [
                ('Literal', '¿Qué datos anotaba originalmente el abuelo de Mara?', 'La fecha de la primera tormenta, el agua reunida y cambios en las plantas.'),
                ('Literal', '¿Qué hizo Mara cada mañana con el recipiente graduado?', 'Registró la medida del agua y después vació el recipiente.'),
                ('Literal', '¿Con qué información comparó las notas familiares?', 'Con información de la estación meteorológica.'),
                ('Inferencial', '¿Por qué Mara no consideró definitivas las opiniones de las personas mayores?', 'Porque eran testimonios y necesitaba contrastarlos con registros y más años de observación.'),
                ('Inferencial', '¿Qué demuestra que el proyecto se volvió colectivo?', 'Que sus compañeros agregaron fotografías, fechas de siembra y datos del arroyo.'),
                ('Inferencial', 'Explica la relación posible entre los árboles y la lluvia mencionada en el texto.', 'La pérdida de árboles podría relacionarse con cambios ambientales, aunque el texto no la presenta como causa comprobada.'),
                ('Crítica', '¿Te parece confiable la propuesta de registrar varios ciclos escolares? Justifica.', 'Respuesta argumentada; debe reconocer que más datos permiten comparar tendencias.'),
                ('Crítica', 'Propón otro dato que ayudaría a comprender los cambios del clima local.', 'Respuesta pertinente: temperatura, duración de lluvias, humedad, caudal, entre otros.'),
            ],
        },
        {
            'title': 'El mural que cambió de lugar',
            'text': (
                'El grupo quería pintar un mural sobre la historia de su comunidad. Primero eligieron una pared junto a la cancha porque todos podían verla, '
                'pero al observarla durante varios días descubrieron que recibía humedad y que el balón golpeaba con frecuencia esa zona. Joel propuso usar el '
                'muro de la biblioteca. A varios compañeros no les gustó la idea, pues pensaban que allí menos personas verían el trabajo. Para decidir, hicieron '
                'una lista de ventajas y dificultades. La pared de la cancha tenía mayor visibilidad, aunque la pintura duraría poco. El muro de la biblioteca '
                'estaba protegido y permitía acercarse para leer textos pequeños. Finalmente eligieron la biblioteca y agregaron un código QR con testimonios '
                'grabados por habitantes de la comunidad. El día de la presentación, las familias recorrieron el mural lentamente y escucharon las voces desde '
                'sus teléfonos. El grupo comprendió que un lugar menos transitado podía favorecer una experiencia más atenta. La decisión no había reducido el '
                'alcance del mural; había cambiado la manera de relacionarse con él.'
            ),
            'questions': [
                ('Literal', '¿Dónde querían pintar el mural al principio?', 'En una pared junto a la cancha.'),
                ('Literal', '¿Qué dos problemas tenía la primera pared?', 'Humedad y golpes frecuentes del balón.'),
                ('Literal', '¿Qué recurso añadieron al mural?', 'Un código QR con testimonios grabados.'),
                ('Inferencial', '¿Por qué la biblioteca permitió una observación más atenta?', 'Porque era un espacio protegido donde podían acercarse y leer con calma.'),
                ('Inferencial', '¿Qué criterio fue más importante que la visibilidad?', 'La conservación y la posibilidad de apreciar el contenido.'),
                ('Inferencial', '¿Qué significa que cambió la manera de relacionarse con el mural?', 'Que el público lo recorrió, leyó y escuchó activamente, no solo lo vio al pasar.'),
                ('Crítica', '¿Habrías elegido el mismo lugar? Argumenta con información del texto.', 'Respuesta razonada que usa ventajas o dificultades mencionadas.'),
                ('Crítica', '¿Qué otra acción ayudaría a difundir el mural?', 'Respuesta viable: visita guiada, exposición digital, invitación comunitaria, etc.'),
            ],
        },
    ],
    '2': [
        {
            'title': 'Una señal en el agua',
            'text': (
                'Durante una práctica escolar, el grupo tomó muestras de agua en tres puntos del arroyo: antes de la comunidad, cerca del puente y después de '
                'la zona de cultivos. A simple vista todas parecían iguales. Sin embargo, al dejarlas reposar, la tercera mostró más sedimentos. El equipo de '
                'Lucía pensó que los fertilizantes eran la causa, pero su profesor les pidió distinguir entre una sospecha y una conclusión. Repitieron el '
                'muestreo en distintos días, registraron si había llovido y observaron qué actividades se realizaban cerca de cada punto. Los resultados variaron: '
                'después de lluvias intensas aumentaban los sedimentos en los tres sitios, aunque el incremento era mayor junto a los cultivos. El grupo explicó '
                'que sus datos mostraban una relación, pero no identificaban por sí solos todas las sustancias presentes ni demostraban una causa única. En su '
                'informe recomendaron evitar tirar residuos, conservar vegetación en las orillas y solicitar un análisis especializado. La investigación no '
                'ofreció una respuesta absoluta, pero permitió formular preguntas mejores y tomar precauciones razonables.'
            ),
            'questions': [
                ('Literal', '¿En qué tres puntos tomaron las muestras?', 'Antes de la comunidad, cerca del puente y después de la zona de cultivos.'),
                ('Literal', '¿Cuándo aumentaban los sedimentos en los tres sitios?', 'Después de lluvias intensas.'),
                ('Literal', 'Menciona dos recomendaciones del informe.', 'Evitar residuos, conservar vegetación o solicitar análisis especializado.'),
                ('Inferencial', '¿Por qué el profesor pidió distinguir sospecha y conclusión?', 'Porque una observación inicial no demostraba que los fertilizantes fueran la causa.'),
                ('Inferencial', '¿Qué función tuvo registrar la lluvia?', 'Ayudó a relacionar la cantidad de sedimentos con una variable que podía influir.'),
                ('Inferencial', '¿Por qué solicitaron un análisis especializado?', 'Porque sus observaciones no identificaban sustancias ni causas específicas.'),
                ('Crítica', 'Evalúa si las recomendaciones son válidas aunque no exista una causa única comprobada.', 'Respuesta argumentada; son medidas preventivas razonables basadas en los datos.'),
                ('Crítica', 'Propón una mejora al procedimiento de investigación.', 'Respuesta pertinente: más fechas, instrumentos, controles, análisis químicos, etc.'),
            ],
        },
        {
            'title': 'El costo de llegar temprano',
            'text': (
                'Cuando cambiaron temporalmente la ruta del transporte, varios estudiantes comenzaron a llegar tarde. La primera propuesta fue adelantar treinta '
                'minutos la salida de todas las familias, pero el consejo estudiantil decidió investigar antes de opinar. Registró durante dos semanas la hora de '
                'salida, el medio de transporte, el tiempo de recorrido y las causas de demora. Descubrió que adelantar la salida ayudaba a quienes usaban autobús, '
                'pero no resolvía el problema de quienes dependían de un camino que se inundaba. También observó que algunos retrasos ocurrían porque dos rutas '
                'coincidían en un cruce estrecho. Con los datos elaboraron tres propuestas: ajustar diez minutos el horario de una ruta, limpiar una cuneta y '
                'organizar un punto seguro para compartir vehículos. Las autoridades aceptaron probarlas durante un mes. Al terminar, las llegadas tarde '
                'disminuyeron, aunque no desaparecieron. El consejo concluyó que una solución justa no siempre es idéntica para todos: debe responder a las '
                'condiciones que producen el problema.'
            ),
            'questions': [
                ('Literal', '¿Durante cuánto tiempo registraron información?', 'Durante dos semanas.'),
                ('Literal', '¿Qué problema no resolvía adelantar la salida?', 'La inundación del camino de algunos estudiantes.'),
                ('Literal', '¿Cuánto duraría la prueba de las propuestas?', 'Un mes.'),
                ('Inferencial', '¿Por qué la primera propuesta podía ser injusta?', 'Porque suponía que todos enfrentaban la misma causa de retraso.'),
                ('Inferencial', '¿Qué aportó registrar el medio de transporte?', 'Permitió distinguir necesidades y causas según la forma de traslado.'),
                ('Inferencial', 'Interpreta la conclusión final del consejo.', 'La equidad exige soluciones diferenciadas según las condiciones reales.'),
                ('Crítica', '¿Los resultados justifican mantener las tres medidas? Explica.', 'Respuesta argumentada considerando la disminución y los problemas restantes.'),
                ('Crítica', '¿Qué dato adicional pedirías antes de una decisión definitiva?', 'Respuesta viable: costos, seguridad, resultados por ruta, opinión de familias, etc.'),
            ],
        },
    ],
    '3': [
        {
            'title': 'Memoria digital, memoria común',
            'text': (
                'Un colectivo juvenil propuso crear un archivo digital con fotografías antiguas de la comunidad. La idea parecía sencilla: escanear imágenes, '
                'escribir nombres y publicarlas. Pronto surgieron preguntas difíciles. Algunas fotografías mostraban ceremonias familiares; otras incluían a '
                'personas que no deseaban aparecer en internet. Además, distintas familias recordaban de manera diferente la fecha y el significado de ciertos '
                'acontecimientos. El colectivo estableció entonces un procedimiento: solicitar autorización, conservar una copia sin publicar, registrar quién '
                'aportó cada imagen y distinguir los datos comprobados de los testimonios. Cuando había versiones distintas, las presentaban como perspectivas '
                'y no como errores que debían eliminarse. Esta decisión volvió el proyecto más lento, pero también más responsable. El archivo dejó de ser una '
                'colección de imágenes curiosas y se convirtió en un espacio para analizar cómo se construye la memoria. Sus integrantes comprendieron que '
                'preservar el pasado no significa fijar una sola versión, sino documentar evidencias, reconocer desacuerdos y respetar a las personas relacionadas '
                'con cada historia.'
            ),
            'questions': [
                ('Literal', '¿Qué acciones incluía la idea inicial?', 'Escanear fotografías, escribir nombres y publicarlas.'),
                ('Literal', 'Menciona tres medidas del procedimiento acordado.', 'Autorización, copia no publicada, registro de procedencia y separación de datos y testimonios.'),
                ('Literal', '¿Cómo presentaban las versiones distintas?', 'Como perspectivas diferentes.'),
                ('Inferencial', '¿Por qué el nuevo procedimiento volvió más responsable el proyecto?', 'Porque protegía la privacidad, la procedencia y la incertidumbre de la información.'),
                ('Inferencial', '¿Qué diferencia existe entre un dato comprobado y un testimonio?', 'El dato tiene evidencia verificable; el testimonio expresa el recuerdo o perspectiva de alguien.'),
                ('Inferencial', 'Explica por qué preservar no significa fijar una sola versión.', 'La memoria colectiva puede contener perspectivas diversas que deben documentarse.'),
                ('Crítica', '¿Debe publicarse una fotografía de valor histórico sin autorización? Argumenta.', 'Respuesta razonada que considere valor histórico, privacidad, consentimiento y alternativas.'),
                ('Crítica', 'Formula una regla adicional para el archivo y justifica su utilidad.', 'Regla pertinente y justificación clara.'),
            ],
        },
        {
            'title': 'La plaza y la sombra',
            'text': (
                'El ayuntamiento anunció la renovación de la plaza central y difundió una imagen con piso nuevo, luminarias y espacios para eventos. El proyecto '
                'recibió comentarios favorables, pero un grupo de estudiantes observó que el diseño eliminaba seis árboles maduros. Para comprender el problema '
                'midieron la temperatura en áreas con sombra y en superficies expuestas al sol. Al mediodía encontraron diferencias considerables. También '
                'entrevistaron a comerciantes, personas mayores, niñas y deportistas. No todos defendían exactamente lo mismo: algunos pedían conservar cada árbol; '
                'otros aceptaban trasplantar dos para ampliar el paso. Con esa información, los estudiantes elaboraron una propuesta alternativa que mantuvo cuatro '
                'árboles, incorporó suelo permeable y reorganizó el escenario. Su plano reducía el espacio para eventos masivos, pero aumentaba las zonas de descanso '
                'y el paso del agua hacia el subsuelo. El debate mostró que una obra pública no se evalúa únicamente por su apariencia o costo. También importa '
                'quiénes usan el espacio, qué beneficios ambientales se conservan y qué necesidades se priorizan.'
            ),
            'questions': [
                ('Literal', '¿Cuántos árboles eliminaba el diseño original?', 'Seis árboles maduros.'),
                ('Literal', '¿Qué variables observaron o investigaron los estudiantes?', 'Temperatura, opiniones de usuarios y características del espacio.'),
                ('Literal', '¿Cuántos árboles conservaba la propuesta alternativa?', 'Cuatro árboles.'),
                ('Inferencial', '¿Para qué compararon zonas con sombra y superficies al sol?', 'Para obtener evidencia del efecto térmico de los árboles.'),
                ('Inferencial', '¿Qué intercambio o costo implicaba la propuesta estudiantil?', 'Menos espacio para eventos masivos a cambio de sombra, descanso y permeabilidad.'),
                ('Inferencial', '¿Por qué entrevistaron a grupos diferentes?', 'Porque el espacio público tiene usuarios con necesidades distintas.'),
                ('Crítica', '¿Qué propuesta consideras más equilibrada? Sustenta tu decisión.', 'Respuesta argumentada con criterios sociales y ambientales del texto.'),
                ('Crítica', '¿Qué información faltaría para tomar la decisión final?', 'Respuesta pertinente: costos, estado de árboles, accesibilidad, aforo, mantenimiento, etc.'),
            ],
        },
    ],
}


WRITING = {
    '1': [
        {'title': 'Una propuesta para mejorar un espacio escolar', 'genre': 'Carta formal', 'audience': 'Dirección escolar', 'purpose': 'Proponer una mejora posible para un espacio de la escuela.', 'instructions': 'Describe el problema, explica a quién afecta, presenta una propuesta concreta y menciona al menos dos razones para realizarla. Cierra con una petición respetuosa.', 'minimum': '180 a 220 palabras'},
        {'title': 'Una experiencia que cambió mi manera de pensar', 'genre': 'Relato personal', 'audience': 'Compañeras y compañeros del grupo', 'purpose': 'Narrar una experiencia y comunicar lo aprendido.', 'instructions': 'Ubica el lugar y el momento, presenta a las personas involucradas, organiza los hechos en secuencia, describe el momento más importante y explica qué aprendiste.', 'minimum': '180 a 220 palabras'},
    ],
    '2': [
        {'title': '¿Cómo podemos reducir los residuos en la escuela?', 'genre': 'Texto argumentativo', 'audience': 'Comunidad escolar', 'purpose': 'Convencer a la comunidad de adoptar una acción concreta.', 'instructions': 'Presenta tu postura, incluye al menos dos argumentos y un ejemplo, considera una posible objeción y concluye con una acción que pueda realizarse durante el próximo mes.', 'minimum': '250 a 300 palabras'},
        {'title': 'Crónica de una actividad comunitaria', 'genre': 'Crónica', 'audience': 'Lectores del periódico escolar', 'purpose': 'Informar y recrear el desarrollo de una actividad real o verosímil.', 'instructions': 'Incluye fecha y lugar, organiza los acontecimientos, incorpora descripciones y una cita o testimonio, y termina explicando la importancia de la actividad.', 'minimum': '250 a 300 palabras'},
    ],
    '3': [
        {'title': 'Tecnología en el aula: condiciones para usarla responsablemente', 'genre': 'Artículo de opinión', 'audience': 'Comunidad escolar', 'purpose': 'Defender una postura equilibrada sobre el uso de tecnología en clase.', 'instructions': 'Formula una tesis, desarrolla tres argumentos, integra un contraargumento y su respuesta, utiliza ejemplos pertinentes y concluye con criterios o acuerdos de uso.', 'minimum': '320 a 380 palabras'},
        {'title': 'Un problema público que requiere participación juvenil', 'genre': 'Ensayo breve', 'audience': 'Autoridades y habitantes de la comunidad', 'purpose': 'Analizar un problema local y proponer participación juvenil informada.', 'instructions': 'Delimita el problema, explica sus causas y consecuencias, diferencia hechos de opiniones, plantea dos acciones viables y cierra valorando la participación de las y los jóvenes.', 'minimum': '320 a 380 palabras'},
    ],
}


def _styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('Title', parent=base['Title'], fontName='Helvetica-Bold', fontSize=17, leading=20, textColor=colors.HexColor('#7B1024'), spaceAfter=8),
        'subtitle': ParagraphStyle('Subtitle', parent=base['Normal'], fontName='Helvetica', fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor('#657085')),
        'h2': ParagraphStyle('H2', parent=base['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#217346'), spaceBefore=8, spaceAfter=6),
        'body': ParagraphStyle('Body', parent=base['BodyText'], fontName='Helvetica', fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=7),
        'small': ParagraphStyle('Small', parent=base['BodyText'], fontName='Helvetica', fontSize=8.5, leading=11),
        'question': ParagraphStyle('Question', parent=base['BodyText'], fontName='Helvetica', fontSize=10, leading=13, spaceAfter=4),
    }


def _page(canvas, doc, config):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#7B1024')); canvas.setLineWidth(1.2)
    canvas.line(1.6 * cm, 1.25 * cm, 19.9 * cm, 1.25 * cm)
    canvas.setFont('Helvetica', 7.5); canvas.setFillColor(colors.HexColor('#657085'))
    canvas.drawString(1.6 * cm, 0.82 * cm, f'{config.school} · SiSAT')
    canvas.drawRightString(19.9 * cm, 0.82 * cm, f'Página {doc.page}')
    canvas.restoreState()


def _header(story, styles, config, title, grade):
    story.append(Paragraph('INSTRUMENTO COMPLEMENTARIO SiSAT', styles['title']))
    story.append(Paragraph(f'{escape(config.school)} · CCT {escape(config.cct or "Sin registro")} · Ciclo {escape(config.cycle or "")} · {grade}.º de secundaria', styles['subtitle']))
    story.append(Spacer(1, 8))
    table = Table([['Alumno(a):', '_____________________________________________', 'Fecha:', '____________']], colWidths=[1.7*cm, 10.5*cm, 1.4*cm, 3.6*cm])
    table.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),8.5),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(table)
    table2 = Table([['Grupo:', '________', 'Visita:', '________', 'Docente:', '_____________________']], colWidths=[1.4*cm,2.2*cm,1.4*cm,2.2*cm,1.5*cm,8.5*cm])
    table2.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),8.5),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(table2)
    story.append(Paragraph(escape(title), styles['h2']))


def _rubric_table(styles, skill='lectura'):
    if skill == 'lectura':
        rows = [['Componente', '3 puntos', '2 puntos', '1 punto']]
        for _, label, descriptors in sisat.SKILLS['lectura']['components']:
            rows.append([Paragraph(label, styles['small'])] + [Paragraph(text, styles['small']) for text in descriptors])
    else:
        rows = [['Componente', '3 puntos', '2 puntos', '1 punto']]
        for _, label, descriptors in sisat.SKILLS['escritura']['components']:
            rows.append([Paragraph(label, styles['small'])] + [Paragraph(text, styles['small']) for text in descriptors])
    table = Table(rows, colWidths=[3.1*cm,4.7*cm,4.7*cm,4.7*cm], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#217346')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#C9D1DA')),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,1),(0,-1),colors.HexColor('#F1F5F9')),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ]))
    return table


def _reading_pdf(grade, item):
    output = io.BytesIO(); styles = _styles(); config = core.cfg(); story = []
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=1.6*cm, leftMargin=1.6*cm, topMargin=1.4*cm, bottomMargin=1.6*cm, title=f'SiSAT Lectura {grade} - {item["title"]}', author=config.school)
    _header(story, styles, config, item['title'], grade)
    story.append(Paragraph('<b>Indicaciones:</b> Lee el texto en voz alta. Después responde las preguntas de comprensión. El docente registrará fluidez, precisión, palabras complejas, voz, seguridad y comprensión.', styles['body']))
    story.append(Paragraph(escape(item['text']), styles['body']))
    story.append(Paragraph('Preguntas de comprensión', styles['h2']))
    for number, (level, question, _) in enumerate(item['questions'], 1):
        story.append(Paragraph(f'<b>{number}. [{escape(level)}]</b> {escape(question)}', styles['question']))
        story.append(Spacer(1, 0.55*cm))
    story.append(PageBreak())
    story.append(Paragraph('GUÍA DE VALORACIÓN DOCENTE - NO ENTREGAR AL ESTUDIANTE', styles['title']))
    story.append(Paragraph(f'<b>Texto:</b> {escape(item["title"])} · <b>Grado:</b> {grade}.º de secundaria', styles['body']))
    story.append(Paragraph('Respuestas esperadas', styles['h2']))
    answers = [[Paragraph('<b>N.º</b>', styles['small']), Paragraph('<b>Nivel</b>', styles['small']), Paragraph('<b>Respuesta o criterio esperado</b>', styles['small'])]]
    for number, (level, _, answer) in enumerate(item['questions'], 1):
        answers.append([str(number), level, Paragraph(escape(answer), styles['small'])])
    answer_table = Table(answers, colWidths=[1*cm,2.4*cm,13.8*cm], repeatRows=1)
    answer_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#7B1024')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#C9D1DA')),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTSIZE',(0,1),(1,-1),8.5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(answer_table); story.append(Spacer(1,8)); story.append(Paragraph('Rúbrica de toma de lectura', styles['h2'])); story.append(_rubric_table(styles, 'lectura'))
    story.append(Paragraph('<b>Resultado global:</b> 15-18 Nivel esperado · 10-14 En desarrollo · 0-9 Requiere apoyo.', styles['body']))
    doc.build(story, onFirstPage=lambda c,d:_page(c,d,config), onLaterPages=lambda c,d:_page(c,d,config)); output.seek(0); return output


def _writing_pdf(grade, item):
    output = io.BytesIO(); styles = _styles(); config = core.cfg(); story = []
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=1.6*cm, leftMargin=1.6*cm, topMargin=1.4*cm, bottomMargin=1.6*cm, title=f'SiSAT Escritura {grade} - {item["title"]}', author=config.school)
    _header(story, styles, config, item['title'], grade)
    info = [[Paragraph('<b>Tipo de texto</b>',styles['small']), item['genre'], Paragraph('<b>Destinatario</b>',styles['small']), item['audience']], [Paragraph('<b>Propósito</b>',styles['small']), Paragraph(item['purpose'],styles['small']), Paragraph('<b>Extensión</b>',styles['small']), item['minimum']]]
    info_table=Table(info,colWidths=[2.5*cm,5.6*cm,2.5*cm,6.6*cm]); info_table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#C9D1DA')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F1F5F9')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#F1F5F9')),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTSIZE',(0,0),(-1,-1),8.5),('PADDING',(0,0),(-1,-1),5)])); story.append(info_table)
    story.append(Paragraph('<b>Consigna:</b> '+escape(item['instructions']), styles['body']))
    story.append(Paragraph('Planeación breve', styles['h2']))
    planning=[['Idea principal o postura','Datos, ejemplos o acontecimientos que incluiré','Orden y cierre del texto'],['','','']]
    pt=Table(planning,colWidths=[5.7*cm]*3,rowHeights=[0.7*cm,2.4*cm]); pt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#217346')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),8),('ALIGN',(0,0),(-1,0),'CENTER'),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#9AA6B2'))])); story.append(pt)
    story.append(Paragraph('Antes de redactar, revisa que tu planeación corresponda al propósito, al destinatario y al tipo de texto solicitado.', styles['body']))
    story.append(PageBreak()); story.append(Paragraph('TEXTO FINAL', styles['title']))
    story.append(Paragraph(f'<b>{escape(item["title"])}</b> · Extensión sugerida: {escape(item["minimum"])}', styles['body']))
    lines=[[''] for _ in range(30)]; lt=Table(lines,colWidths=[17.1*cm],rowHeights=[0.68*cm]*30); lt.setStyle(TableStyle([('LINEBELOW',(0,0),(-1,-1),0.35,colors.HexColor('#AAB4C3'))])); story.append(lt)
    if grade == '3':
        story.append(PageBreak()); story.append(Paragraph('TEXTO FINAL - CONTINUACIÓN', styles['title']))
        more_lines=[[''] for _ in range(30)]; mt=Table(more_lines,colWidths=[17.1*cm],rowHeights=[0.68*cm]*30); mt.setStyle(TableStyle([('LINEBELOW',(0,0),(-1,-1),0.35,colors.HexColor('#AAB4C3'))])); story.append(mt)
    story.append(PageBreak()); story.append(Paragraph('GUÍA DE VALORACIÓN DOCENTE - NO ENTREGAR AL ESTUDIANTE', styles['title']))
    story.append(Paragraph(f'<b>Actividad:</b> {escape(item["title"])} · <b>Grado:</b> {grade}.º de secundaria', styles['body']))
    story.append(Paragraph('La consigna exige destinatario y propósito definidos, organización de ideas, vocabulario pertinente, puntuación, ortografía y producción manuscrita legible. Esto permite observar directamente los seis componentes de la rúbrica.', styles['body']))
    story.append(_rubric_table(styles, 'escritura')); story.append(Spacer(1,8))
    score_rows=[['Componente','Puntaje'],['Legibilidad','___ / 3'],['Propósito comunicativo','___ / 3'],['Relación de palabras y oraciones','___ / 3'],['Diversidad de vocabulario','___ / 3'],['Signos de puntuación','___ / 3'],['Reglas ortográficas','___ / 3'],['TOTAL','___ / 18']]
    score=Table(score_rows,colWidths=[10.5*cm,3*cm]); score.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#7B1024')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#C9D1DA')),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),('ALIGN',(1,1),(1,-1),'CENTER'),('PADDING',(0,0),(-1,-1),5)])); story.append(score)
    story.append(Paragraph('<b>Resultado global:</b> 15-18 Nivel esperado · 10-14 En desarrollo · 0-9 Requiere apoyo.', styles['body']))
    doc.build(story, onFirstPage=lambda c,d:_page(c,d,config), onLaterPages=lambda c,d:_page(c,d,config)); output.seek(0); return output


def install(app):
    @app.route('/sisat/materiales')
    def sisat_materials():
        if not session.get('uid'): return redirect('/login')
        if not sisat._can_capture():
            flash('Tu rol no permite generar instrumentos SiSAT.')
            return redirect('/sisat')
        body = '''<h1>Generador de actividades SiSAT</h1><p class="muted">Crea instrumentos originales, graduados e imprimibles. Cada PDF incluye la actividad para el estudiante y una guía de valoración docente.</p><div class="grid"><div class="card"><h2>Toma de lectura</h2><p>Lectura inédita con preguntas literales, inferenciales y críticas, respuestas esperadas y rúbrica de seis componentes.</p><form method="get" action="/sisat/material.pdf"><input type="hidden" name="skill" value="lectura"><label>Grado<select name="grade"><option value="1">1.º de secundaria</option><option value="2">2.º de secundaria</option><option value="3">3.º de secundaria</option></select></label><br><button>Generar nueva lectura PDF</button></form></div><div class="card"><h2>Producción de textos</h2><p>Consigna acorde al grado para observar propósito, organización, vocabulario, puntuación, ortografía y legibilidad.</p><form method="get" action="/sisat/material.pdf"><input type="hidden" name="skill" value="escritura"><label>Grado<select name="grade"><option value="1">1.º de secundaria</option><option value="2">2.º de secundaria</option><option value="3">3.º de secundaria</option></select></label><br><button>Generar nuevo ejercicio PDF</button></form></div></div><a href="/sisat">← Volver a SiSAT</a>'''
        return core.page('Materiales SiSAT', body)

    @app.route('/sisat/material.pdf')
    def sisat_material_pdf():
        if not session.get('uid'): return redirect('/login')
        if not sisat._can_capture():
            flash('Tu rol no permite generar instrumentos SiSAT.')
            return redirect('/sisat')
        skill = request.args.get('skill', 'lectura')
        grade = request.args.get('grade', '1')
        if grade not in ('1','2','3') or skill not in ('lectura','escritura'):
            flash('Selecciona una habilidad y un grado válidos.')
            return redirect('/sisat/materiales')
        rng = random.SystemRandom()
        item = rng.choice(READINGS[grade] if skill == 'lectura' else WRITING[grade])
        output = _reading_pdf(grade, item) if skill == 'lectura' else _writing_pdf(grade, item)
        filename = f'sisat_{skill}_{grade}grado_{date.today().isoformat()}.pdf'
        return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')
