# GENERADOR SENCILLO DE SOPORTE PDF Y LISTADO WORD
# Las bibliotecas se encargan de abrir imágenes y escribir documentos.
from pathlib import Path
from PIL import Image, ImageOps
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ImagenPDF, KeepTogether, PageBreak, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from pypdf import PdfReader, PdfWriter
from xml.sax.saxutils import escape
import io
import shutil
import subprocess

# Estas son las reglas de clasificación. Python las revisa en orden.
def clasificar(ancho, alto):
    if ancho == 1240 and alto in [413, 430]:
        return 'Banners'
    elif ancho == 1920 and alto == 1080:
        return 'Wallpapers'
    elif ancho == 1080:
        return 'Flyers'
    elif ancho == 800 and alto >= 450:
        return 'Popups'
    elif (ancho == 600 and alto == 300) or (ancho == 900 and alto in [400, 430]):
        return 'Imágenes de boletín'
    else:
        return 'Diseños varios'

# Convertir el nombre del archivo en un título legible.
def limpiar_nombre(nombre):
    return nombre.replace('_', ' ').replace('-', ' ').strip()

# Leer todos los archivos de la carpeta y sus subcarpetas.
def leer_archivos(carpeta, correcciones=None):
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        raise ValueError('No existe la carpeta de entrada.')
    correcciones = correcciones or {}
    piezas = []
    actas = []
    avisos = []
    for archivo in sorted(carpeta.rglob('*')):
        if not archivo.is_file():
            continue
        relativa = archivo.relative_to(carpeta).as_posix()
        subcarpetas = [parte.lower() for parte in archivo.relative_to(carpeta).parts[:-1]]
        extension = archivo.suffix.lower()
        if 'actas' in subcarpetas and extension in ['.pdf', '.docx']:
            actas.append(archivo)
        elif extension in ['.jpg', '.jpeg', '.png']:
            try:
                with Image.open(archivo) as imagen:
                    imagen = ImageOps.exif_transpose(imagen)
                    imagen.load()
                    ancho, alto = imagen.size
            except Exception:
                avisos.append('No se pudo abrir: ' + relativa)
                continue
            tipo = clasificar(ancho, alto)
            nombre = limpiar_nombre(archivo.stem)
            # Una foto no se identifica por tamaño: se reconoce por la carpeta.
            carpetas_foto = [p for p in subcarpetas if p.startswith('fotos') or p == 'fotografias']
            if carpetas_foto:
                tipo = 'Fotografías'
                nombre = limpiar_nombre(archivo.parent.name)
            if 'conceptualizacion' in subcarpetas:
                tipo = 'Conceptualización'
            # Permite corregir una pieza sin cambiar sus medidas ni el original.
            if relativa in correcciones:
                tipo = correcciones[relativa]['tipo']
                nombre = correcciones[relativa].get('nombre', nombre)
            piezas.append({'archivo': archivo, 'ruta': relativa, 'tipo': tipo,
                           'nombre': nombre, 'ancho': ancho, 'alto': alto})
        else:
            avisos.append('Archivo no incluido: ' + relativa)
    return piezas, actas, avisos

# Crear el soporte. ReportLab calcula los saltos de página automáticamente.
def crear_pdf(piezas, destino, periodo):
    estilos = getSampleStyleSheet()
    estilos['Heading1'].textColor = colors.HexColor('#CE1535')
    contenido = []
    tipos = ['Banners', 'Flyers', 'Wallpapers', 'Popups', 'Imágenes de boletín',
             'Diseños varios', 'Fotografías', 'Conceptualización']
    for tipo in tipos:
        grupo = [p for p in piezas if p['tipo'] == tipo]
        if not grupo:
            continue
        if contenido:
            contenido.append(PageBreak())
        contenido.append(Paragraph(escape(tipo), estilos['Heading1']))
        fila = []
        for pieza in grupo:
            with Image.open(pieza['archivo']) as imagen:
                imagen = ImageOps.exif_transpose(imagen).convert('RGBA')
                fondo = Image.new('RGBA', imagen.size, 'white')
                fondo.alpha_composite(imagen)
                imagen = fondo.convert('RGB')
                imagen.thumbnail((1800, 2200))
                memoria = io.BytesIO()
                imagen.save(memoria, format='JPEG', quality=87)
                memoria.seek(0)
                ancho, alto = imagen.size
            # Usar el mismo factor para ancho y alto evita deformar la imagen.
            factor = min(220 / ancho, 265 / alto)
            bloque = [Paragraph(escape(pieza['nombre']), estilos['Normal']), Spacer(1, 6),
                      ImagenPDF(memoria, width=ancho*factor, height=alto*factor), Spacer(1, 18)]
            # Dos columnas: cada fila contiene hasta dos piezas.
            fila.append(bloque)
            if len(fila) == 2:
                contenido.append(Table([fila], colWidths=[240, 240], style=[('VALIGN', (0, 0), (-1, -1), 'TOP')]))
                fila = []
        if fila:
            contenido.append(Table([fila + ['']], colWidths=[240, 240], style=[('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    if not contenido:
        contenido.append(Paragraph('No se suministraron imágenes.', estilos['Normal']))
    def encabezado(canvas, documento):
        canvas.setFillColor(colors.HexColor('#CE1535'))
        canvas.rect(0, 750, 612, 30, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 15)
        canvas.drawString(48, 760, 'SOPORTE DE ACTIVIDADES')
        canvas.setFillColor(colors.black)
        canvas.setFont('Helvetica', 9)
        canvas.drawString(48, 732, periodo[:95])
        canvas.drawRightString(564, 25, 'Página ' + str(documento.page))
    SimpleDocTemplate(str(destino), pagesize=(612, 792), topMargin=85,
                      bottomMargin=45, leftMargin=60, rightMargin=60).build(
                          contenido, onFirstPage=encabezado, onLaterPages=encabezado)

# Añadir las actas completas al final. Los DOCX se convierten con LibreOffice.
def agregar_actas(pdf_imagenes, actas, destino, temporal):
    escritor = PdfWriter()
    escritor.append(str(pdf_imagenes))
    paginas_actas = 0
    for acta in actas:
        pdf_acta = acta
        if acta.suffix.lower() == '.docx':
            programa = shutil.which('libreoffice') or shutil.which('soffice')
            if not programa:
                raise RuntimeError('Instala LibreOffice o convierte las actas a PDF antes de ejecutar.')
            carpeta_acta = Path(temporal) / str(paginas_actas)
            carpeta_acta.mkdir(parents=True, exist_ok=True)
            subprocess.run([programa, '-env:UserInstallation=' + (carpeta_acta/'perfil').resolve().as_uri(),
                            '--headless', '--convert-to', 'pdf', '--outdir', str(carpeta_acta), str(acta)],
                           check=True, capture_output=True, timeout=120)
            pdf_acta = carpeta_acta / (acta.stem + '.pdf')
        lector = PdfReader(str(pdf_acta))
        if not lector.pages:
            raise ValueError('Acta sin páginas: ' + acta.name)
        paginas_actas += len(lector.pages)
        escritor.append(str(pdf_acta))
    escritor.write(str(destino))
    escritor.close()
    return paginas_actas

# Crear el Word para copiar y pegar en el portal.
def crear_word(piezas, actas, destino, periodo):
    documento = Document()
    normal = documento.styles['Normal']
    normal.font.name = 'Calibri'
    normal.font.size = Pt(11)
    documento.styles['Title'].font.color.rgb = RGBColor(0, 0, 0)
    # Quitar bordes decorativos heredados de la plantilla de Word.
    for borde in documento.styles.element.xpath('.//w:pBdr'):
        borde.getparent().remove(borde)
    documento.add_paragraph('Listado de actividades', style='Title')
    documento.add_paragraph(periodo)
    documento.add_paragraph('Revisar nombres, cantidades y obligaciones antes de copiar al portal.')
    documento.add_heading('Obligación 1 Diseño de piezas gráficas', level=1)
    for tipo in ['Banners', 'Flyers', 'Wallpapers', 'Popups', 'Imágenes de boletín', 'Diseños varios']:
        grupo = [p for p in piezas if p['tipo'] == tipo]
        if grupo:
            documento.add_heading(tipo + ' (' + str(len(grupo)) + ')', level=2)
            for pieza in grupo:
                documento.add_paragraph(pieza['nombre'], style='List Bullet')
    documento.add_heading('Obligación 2 Registros fotográficos', level=1)
    eventos = []
    for pieza in piezas:
        if pieza['tipo'] == 'Fotografías' and pieza['nombre'] not in eventos:
            eventos.append(pieza['nombre'])
    for evento in eventos:
        documento.add_paragraph(evento, style='List Bullet')
    if not eventos:
        documento.add_paragraph('No se suministraron registros fotográficos.')
    documento.add_heading('Obligación 3 Conceptualización', level=1)
    conceptos = [p for p in piezas if p['tipo'] == 'Conceptualización']
    for pieza in conceptos:
        documento.add_paragraph(pieza['nombre'], style='List Bullet')
    if not conceptos:
        documento.add_paragraph('Completar manualmente si se realizaron actividades de conceptualización.')
    documento.add_heading('Obligación 6 Reuniones', level=1)
    for acta in actas:
        documento.add_paragraph(limpiar_nombre(acta.stem), style='List Bullet')
    if not actas:
        documento.add_paragraph('No se suministraron actas.')
    documento.save(str(destino))

# Esta función ejecuta el proceso completo en orden.
def generar(carpeta, salida, periodo, correcciones=None):
    piezas, actas, avisos = leer_archivos(carpeta, correcciones)
    if not piezas and not actas:
        raise ValueError('No hay imágenes ni actas válidas en la carpeta.')
    tipos_validos = ['Banners', 'Flyers', 'Wallpapers', 'Popups', 'Imágenes de boletín',
                     'Diseños varios', 'Fotografías', 'Conceptualización']
    for pieza in piezas:
        if pieza['tipo'] not in tipos_validos:
            raise ValueError('Tipo no válido: ' + pieza['tipo'])
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    temporal = salida / 'temporal'
    temporal.mkdir(exist_ok=True)
    crear_pdf(piezas, temporal/'imagenes.pdf', periodo)
    paginas_actas = agregar_actas(temporal/'imagenes.pdf', actas, salida/'soporte_actividades.pdf', temporal)
    crear_word(piezas, actas, salida/'listado_actividades.docx', periodo)
    import csv
    with (salida/'inventario.csv').open('w', encoding='utf-8-sig', newline='') as archivo:
        tabla = csv.writer(archivo)
        tabla.writerow(['Archivo', 'Tipo', 'Nombre', 'Ancho', 'Alto'])
        for p in piezas:
            tabla.writerow([p['ruta'], p['tipo'], p['nombre'], p['ancho'], p['alto']])
    (salida/'avisos.txt').write_text('\n'.join(avisos) or 'Sin avisos.', encoding='utf-8')
    shutil.rmtree(temporal)
    print('Proceso terminado:', len(piezas), 'imágenes y', len(actas), 'actas.')
    return piezas, actas, paginas_actas
