"""Datos ficticios para probar la aplicación sin información personal."""
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas


def fuente(tamano):
    try:
        return ImageFont.truetype('DejaVuSans.ttf', tamano)
    except OSError:
        return ImageFont.load_default(size=tamano)


def crear_ejemplo():
    ejemplos = [
        ('piezas/banner_bienestar.jpg', (1240, 430), 'BIENESTAR', 'Tu bienestar también cuenta', '#deecd9'),
        ('piezas/flyer_encuentro_equipo.png', (1080, 1920), 'ENCUENTRO', 'Un espacio para compartir', '#eadfd6'),
        ('piezas/wallpaper_cultura.jpg', (1920, 1080), 'CULTURA', 'Juntos hacemos la diferencia', '#dce6ef'),
        ('piezas/popup_convocatoria.png', (800, 600), 'CONVOCATORIA', 'Participa y suma tus ideas', '#f1e8c9'),
        ('piezas/boletin_novedades.jpg', (900, 430), 'NOVEDADES', 'Esto pasa en nuestro equipo', '#e6e2f3'),
        ('piezas/boton_inscripciones.png', (300, 300), 'BOTÓN', 'Inscripciones', '#d6e6e3'),
        ('fotos_encuentro_equipo/foto_01.jpg', (1400, 900), 'ENCUENTRO', 'Registro de ejemplo 01', '#cbdcd3'),
        ('fotos_encuentro_equipo/foto_02.jpg', (1400, 900), 'ENCUENTRO', 'Registro de ejemplo 02', '#d5dfce'),
    ]
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, 'w', zipfile.ZIP_DEFLATED) as z:
        for ruta, medidas, titulo, subtitulo, color in ejemplos:
            imagen = Image.new('RGB', medidas, color)
            dibujo = ImageDraw.Draw(imagen)
            w, h = medidas
            margen = max(20, int(w * .07))
            grande = max(20, int(w * .065))
            dibujo.rounded_rectangle((w*.72, h*.12, w*1.02, h*.85), radius=max(20, w//10), fill='#244b3b')
            dibujo.text((margen, h*.25), titulo, font=fuente(grande), fill='#142d23')
            dibujo.text((margen, h*.5), subtitulo, font=fuente(max(14, grande//3)), fill='#244b3b')
            dibujo.text((margen, h*.83), 'EJEMPLO FICTICIO', font=fuente(max(11, grande//4)), fill='#244b3b')
            datos = io.BytesIO()
            imagen.save(datos, format='PNG' if ruta.endswith('.png') else 'JPEG')
            z.writestr(ruta, datos.getvalue())
        acta = io.BytesIO()
        pdf = canvas.Canvas(acta, pagesize=(612, 792))
        pdf.setFont('Helvetica-Bold', 20)
        pdf.drawString(60, 710, 'Acta de reunión de ejemplo')
        pdf.setFont('Helvetica', 12)
        for i, linea in enumerate(['Documento ficticio para probar el prototipo.',
                                    'Tema: seguimiento del equipo de comunicaciones.',
                                    'Actividad: revisar avances y próximos entregables.']):
            pdf.drawString(60, 655 - i*25, linea)
        pdf.save()
        z.writestr('actas/Acta_seguimiento_equipo.pdf', acta.getvalue())
    return memoria.getvalue()
