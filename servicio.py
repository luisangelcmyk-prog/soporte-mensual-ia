"""Carga, revisión y exportación del prototipo. El algoritmo original está en algoritmo.py."""
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import csv
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import zipfile

from docx import Document
from pypdf import PdfReader
from algoritmo import leer_archivos, crear_pdf, crear_word, agregar_actas

TIPOS = ['Banners', 'Flyers', 'Wallpapers', 'Popups', 'Imágenes de boletín',
         'Diseños varios', 'Fotografías', 'Conceptualización']
MAX_ZIP = 200 * 1024 * 1024
MAX_EXTRAIDO = 500 * 1024 * 1024


def abrir_zip(datos):
    """Cada sesión tiene su propia carpeta. Nunca se escribe fuera de ella."""
    if len(datos) > MAX_ZIP:
        raise ValueError('El ZIP supera los 200 MB permitidos.')
    temporal = TemporaryDirectory(prefix='soporte_entrada_')
    raiz = Path(temporal.name)
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as archivo_zip:
            entradas = archivo_zip.infolist()
            if len(entradas) > 2000 or sum(e.file_size for e in entradas) > MAX_EXTRAIDO:
                raise ValueError('El ZIP supera 2000 archivos o 500 MB descomprimidos.')
            vistos = set()
            for entrada in entradas:
                nombre = entrada.filename.replace('\\', '/')
                partes = PurePosixPath(nombre).parts
                if (not partes or nombre.startswith('/') or '..' in partes
                        or any(':' in parte for parte in partes)
                        or stat.S_ISLNK(entrada.external_attr >> 16)):
                    raise ValueError('El ZIP contiene una ruta no válida.')
                if entrada.is_dir():
                    continue
                if '__MACOSX' in partes or Path(nombre).name.startswith('.'):
                    continue
                if nombre.casefold() in vistos:
                    raise ValueError('El ZIP contiene rutas duplicadas: ' + nombre)
                vistos.add(nombre.casefold())
                destino = raiz.joinpath(*partes)
                if not destino.resolve().is_relative_to(raiz.resolve()):
                    raise ValueError('Ruta fuera de la carpeta de trabajo.')
                destino.parent.mkdir(parents=True, exist_ok=True)
                with archivo_zip.open(entrada) as origen, destino.open('wb') as salida:
                    shutil.copyfileobj(origen, salida)
        hijos = list(raiz.iterdir())
        if len(hijos) == 1 and hijos[0].is_dir():
            raiz = hijos[0]
        piezas, actas, avisos = leer_archivos(raiz)
        if not piezas and not actas:
            raise ValueError('No se encontraron imágenes JPG/PNG ni actas PDF/DOCX dentro de actas.')
        return {'temporal': temporal, 'raiz': raiz, 'piezas': piezas, 'actas': actas,
                'avisos': avisos, 'id': hashlib.sha256(datos).hexdigest()[:12]}
    except Exception:
        temporal.cleanup()
        raise


def filas_editor(carga):
    filas = []
    for pieza in carga['piezas']:
        filas.append({'Incluir': True, 'Archivo': pieza['ruta'], 'Tipo': pieza['tipo'],
                      'Actividad': pieza['nombre'],
                      'Medidas': f"{pieza['ancho']} × {pieza['alto']}",
                      'Revisado': False})
    return filas


def filas_actas(carga):
    return [{'Incluir': True, 'Acta': a.relative_to(carga['raiz']).as_posix(),
             'Formato': a.suffix[1:].upper()} for a in carga['actas']]


def seleccion(carga, filas, actas_filas):
    """Solo se aceptan archivos que realmente estaban en la carga original."""
    originales = {p['ruta']: p for p in carga['piezas']}
    piezas = []
    for fila in filas:
        if not fila['Incluir']:
            continue
        if fila['Archivo'] not in originales:
            raise ValueError('Archivo desconocido en la revisión.')
        tipo = str(fila['Tipo'])
        nombre = str(fila['Actividad']).strip()
        if tipo not in TIPOS or not nombre or nombre.lower() == 'nan' or len(nombre) > 200:
            raise ValueError('Revisa las categorías y los nombres: no pueden estar vacíos ni superar 200 caracteres.')
        p = dict(originales[fila['Archivo']])
        p.update(tipo=tipo, nombre=nombre)
        piezas.append(p)
    mapa_actas = {a.relative_to(carga['raiz']).as_posix(): a for a in carga['actas']}
    actas = []
    for fila in actas_filas:
        if fila['Incluir']:
            if fila['Acta'] not in mapa_actas:
                raise ValueError('Acta desconocida.')
            actas.append(mapa_actas[fila['Acta']])
    if not piezas and not actas:
        raise ValueError('Selecciona al menos una imagen o un acta.')
    return piezas, actas


def buscar_libreoffice():
    for nombre in ['libreoffice', 'soffice', 'soffice.exe']:
        programa = shutil.which(nombre)
        if programa:
            return programa
    for variable in ['ProgramFiles', 'ProgramFiles(x86)']:
        base = os.environ.get(variable)
        if base:
            candidato = Path(base) / 'LibreOffice' / 'program' / 'soffice.exe'
            if candidato.is_file():
                return str(candidato)
    return None


def convertir_actas(actas, temporal):
    pdfs = []
    for i, acta in enumerate(actas):
        if acta.suffix.lower() == '.pdf':
            pdfs.append(acta)
            continue
        programa = buscar_libreoffice()
        if not programa:
            raise ValueError('Hay actas Word seleccionadas. Instala LibreOffice o vuelve a cargar esas actas como PDF.')
        carpeta = Path(temporal) / f'acta_{i}'
        carpeta.mkdir(parents=True)
        perfil = (carpeta / 'perfil').resolve().as_uri()
        try:
            subprocess.run([programa, '-env:UserInstallation=' + perfil, '--headless',
                            '--convert-to', 'pdf', '--outdir', str(carpeta), str(acta)],
                           capture_output=True, check=True, timeout=120)
        except (subprocess.SubprocessError, OSError) as error:
            raise ValueError('No se pudo convertir el acta: ' + acta.name) from error
        pdf = carpeta / (acta.stem + '.pdf')
        if not pdf.is_file():
            raise ValueError('El conversor no generó el PDF de ' + acta.name)
        pdfs.append(pdf)
    return pdfs


def generar_documentos(carga, filas, actas_filas, periodo, contrato=''):
    piezas, actas = seleccion(carga, filas, actas_filas)
    periodo = periodo.strip()
    if not periodo or len(periodo) > 50 or len(contrato.strip()) > 30:
        raise ValueError('Escribe un periodo de hasta 50 caracteres y un contrato de hasta 30.')
    rotulo = periodo + (' | ' + contrato.strip() if contrato.strip() else '')
    with TemporaryDirectory(prefix='soporte_salida_') as temporal:
        carpeta = Path(temporal)
        pdf_actas = convertir_actas(actas, carpeta)
        crear_pdf(piezas, carpeta / 'imagenes.pdf', rotulo)
        paginas_actas = agregar_actas(carpeta / 'imagenes.pdf', pdf_actas,
                                     carpeta / 'soporte_actividades.pdf', carpeta / 'convertidas')
        crear_word(piezas, actas, carpeta / 'listado_actividades.docx', rotulo)
        archivos = {nombre: (carpeta / nombre).read_bytes()
                    for nombre in ['soporte_actividades.pdf', 'listado_actividades.docx']}
        salida_csv = io.StringIO(newline='')
        tabla = csv.writer(salida_csv)
        tabla.writerow(['Archivo', 'Tipo', 'Actividad', 'Ancho', 'Alto'])
        for p in piezas:
            tabla.writerow([p['ruta'], p['tipo'], p['nombre'], p['ancho'], p['alto']])
        archivos['inventario.csv'] = salida_csv.getvalue().encode('utf-8-sig')
        configuracion = {'periodo': periodo, 'contrato': contrato,
                         'piezas': filas, 'actas': actas_filas}
        archivos['revision.json'] = json.dumps(configuracion, ensure_ascii=False, indent=2).encode()
        archivos['avisos.txt'] = ('\n'.join(carga['avisos']) or 'Sin avisos.').encode()
        doc = Document(io.BytesIO(archivos['listado_actividades.docx']))
        texto = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        archivos['listado_para_copiar.txt'] = texto.encode()
        paquete = io.BytesIO()
        with zipfile.ZipFile(paquete, 'w', zipfile.ZIP_DEFLATED) as z:
            for nombre, datos in archivos.items():
                z.writestr(nombre, datos)
        return {'archivos': archivos, 'zip': paquete.getvalue(), 'texto': texto,
                'paginas': len(PdfReader(io.BytesIO(archivos['soporte_actividades.pdf'])).pages),
                'paginas_actas': paginas_actas, 'imagenes': len(piezas), 'actas': len(actas)}


def huella_revision(filas, actas, periodo, contrato):
    datos = json.dumps([filas, actas, periodo, contrato], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(datos.encode()).hexdigest()
