"""Interfaz Streamlit del algoritmo de informes. Ejecutar: streamlit run app.py"""
from pathlib import Path
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import io
import base64

import pandas as pd
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

from servicio import (TIPOS, abrir_zip, filas_editor, filas_actas, seleccion,
                      generar_documentos, huella_revision, buscar_libreoffice)
from ejemplo import crear_ejemplo

st.set_page_config(page_title='Soporte mensual', page_icon='📁', layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
.block-container{max-width:1280px;padding-top:2.6rem;padding-bottom:2.5rem}
header[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{min-width:245px;max-width:245px}
[data-testid="stSidebar"] .block-container{padding-top:1rem}
h1{font-size:2.55rem!important;letter-spacing:-1.7px;font-weight:700!important;line-height:1.12!important}
h2{font-size:1.45rem!important;letter-spacing:-.45px}
h3{font-size:1.05rem!important}
.eyebrow{font-size:.7rem;letter-spacing:2px;font-weight:700;color:#66776f;margin-bottom:12px}
.hero-sub{font-size:1rem;color:#6a7670;margin-top:7px;margin-bottom:25px}
.brand{display:flex;gap:12px;align-items:center;margin:8px 0 8px;color:white;font-weight:650;font-size:1.08rem;line-height:1.2}
.brand-icon{width:40px;height:40px;background:#d5edb7;color:#173626;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800}
.sidebar-note{font-size:.78rem;color:#a5b7ac;line-height:1.6;margin-bottom:25px}
.section-kicker{color:#52705f;font-size:.72rem;text-transform:uppercase;letter-spacing:1.7px;font-weight:700;margin-bottom:10px}
.empty-card{border:1px dashed #c8d7cd;border-radius:14px;background:#f8fbf8;padding:25px 28px;margin:12px 0 18px}
.empty-card strong{font-size:1.05rem;color:#193d2b}.empty-card p{color:#67766d;font-size:.9rem;line-height:1.6;margin:8px 0 0}
[data-testid="stMetric"]{border:1px solid #e1e8e1;background:#fff;border-radius:12px;padding:16px 20px}
[data-testid="stMetricLabel"]{font-size:.78rem;color:#6c7b71}
[data-testid="stMetricValue"]{font-size:1.85rem!important;letter-spacing:-1px}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px}
.stButton>button,.stDownloadButton>button{border-radius:9px;min-height:2.7rem;font-weight:600}
[data-testid="stFileUploader"]{border-radius:12px}
footer{visibility:hidden}
</style>''', unsafe_allow_html=True)

ETAPAS = ['01 · Cargar', '02 · Revisar', '03 · Generar']
if 'paso' not in st.session_state:
    st.session_state.paso = ETAPAS[0]
if 'periodo' not in st.session_state:
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    hoy = datetime.now(ZoneInfo('America/Bogota'))
    st.session_state.periodo = f'{meses[hoy.month-1].capitalize()} de {hoy.year}'


def guardar_carga(datos, nombre):
    nueva = abrir_zip(datos)
    anterior = st.session_state.get('carga')
    if anterior:
        anterior['temporal'].cleanup()
    st.session_state.carga = nueva
    st.session_state.nombre_carga = nombre
    st.session_state.filas_base = filas_editor(nueva)
    st.session_state.filas_actuales = filas_editor(nueva)
    st.session_state.actas_base = filas_actas(nueva)
    st.session_state.actas_actuales = filas_actas(nueva)
    st.session_state.editor_id = uuid.uuid4().hex[:10]
    st.session_state.pop('resultado', None)
    st.session_state.pop('error_carga', None)
    st.session_state.confirmacion = False
    st.session_state.paso = ETAPAS[1]


def cargar_demo():
    try:
        guardar_carga(crear_ejemplo(), 'Ejemplo de comunicación interna')
    except Exception as error:
        st.session_state.error_carga = str(error)


def cargar_archivo():
    archivo = st.session_state.get('archivo_zip')
    if archivo is None:
        st.session_state.error_carga = 'Selecciona primero un archivo ZIP.'
        return
    try:
        guardar_carga(archivo.getvalue(), archivo.name)
    except Exception as error:
        st.session_state.error_carga = str(error)


def nueva_carga():
    anterior = st.session_state.get('carga')
    if anterior:
        anterior['temporal'].cleanup()
    for clave in ['carga','resultado','filas_base','filas_actuales','actas_base',
                  'actas_actuales','nombre_carga','archivo_zip','error_carga']:
        st.session_state.pop(clave, None)
    st.session_state.paso = ETAPAS[0]
    st.session_state.confirmacion = False


with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-icon">SM</div><span>Soporte<br>mensual</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-note">Tus evidencias, organizadas.<br>Tu informe, más sencillo.</div>', unsafe_allow_html=True)
    st.caption('DATOS DEL INFORME')
    st.text_input('Periodo', key='periodo', max_chars=50)
    st.text_input('Número de contrato (opcional)', key='contrato', placeholder='CTO1229-26', max_chars=30)
    st.divider()
    st.caption('CÓMO FUNCIONA')
    st.markdown('**1. Carga** tu carpeta en ZIP.\n\n**2. Revisa** nombres y categorías.\n\n**3. Descarga** el soporte y el listado.')
    st.divider()
    if st.session_state.get('carga'):
        st.button('Empezar una nueva carga', on_click=nueva_carga, width='stretch', key='nueva_carga')
    st.caption('Prototipo académico · Luis Ángel Aguirre')

st.markdown('<div class="eyebrow">COMUNICACIÓN INTERNA / GESTIÓN DE ACTIVIDADES</div>', unsafe_allow_html=True)
st.title('Tu informe mensual,\nen un solo lugar.')
st.markdown('<div class="hero-sub">Carga tus evidencias, revisa las piezas y genera el soporte PDF y el listado Word.</div>', unsafe_allow_html=True)

carga = st.session_state.get('carga')
# El editor conserva cambios por índice. Guardarlos permite cambiar de etapa
# sin perder la revisión, y mantiene los contadores actualizados.
if carga:
    for prefijo, clave_base, clave_actual, permitidas in [
        ('piezas_', 'filas_base', 'filas_actuales', {'Incluir','Tipo','Actividad','Revisado'}),
        ('actas_', 'actas_base', 'actas_actuales', {'Incluir'})]:
        clave_editor = prefijo + st.session_state.editor_id
        if clave_editor in st.session_state:
            cambios = st.session_state[clave_editor].get('edited_rows', {})
            actualizadas = [dict(f) for f in st.session_state[clave_base]]
            for indice, valores in cambios.items():
                if 0 <= int(indice) < len(actualizadas):
                    actualizadas[int(indice)].update({k:v for k,v in valores.items() if k in permitidas})
            st.session_state[clave_actual] = actualizadas
        elif st.session_state.paso == ETAPAS[1]:
            st.session_state[clave_base] = [dict(f) for f in st.session_state[clave_actual]]
filas = st.session_state.get('filas_actuales', [])
actas_filas = st.session_state.get('actas_actuales', [])
incluidas = [f for f in filas if f['Incluir']]
actas_incluidas = [a for a in actas_filas if a['Incluir']]
eventos = {str(f['Actividad']) for f in incluidas if f['Tipo'] == 'Fotografías'}
c1,c2,c3,c4 = st.columns(4)
c1.metric('Imágenes incluidas', len(incluidas))
c2.metric('Tipos de pieza', len({f['Tipo'] for f in incluidas if f['Tipo'] != 'Fotografías'}))
c3.metric('Registros fotográficos', len(eventos))
c4.metric('Actas seleccionadas', len(actas_incluidas))
st.write('')
st.radio('Etapa del proceso', ETAPAS, horizontal=True, key='paso', label_visibility='collapsed')
st.write('')
if st.session_state.get('error_carga'):
    st.error(st.session_state.error_carga)

if st.session_state.paso == ETAPAS[0]:
    izquierda, derecha = st.columns([1.6, 1], gap='large')
    with izquierda:
        with st.container(border=True):
            st.markdown('<div class="section-kicker">PASO 01</div>', unsafe_allow_html=True)
            st.subheader('Carga las evidencias del mes')
            st.write('Selecciona un ZIP con tus diseños, fotografías y actas de reunión.')
            st.file_uploader('Archivo de evidencias', type=['zip'], key='archivo_zip', label_visibility='collapsed')
            st.caption('JPG y PNG · Actas en PDF o DOCX · Hasta 200 MB en el ZIP')
            st.button('Cargar y clasificar', type='primary', on_click=cargar_archivo, width='stretch', key='analizar_zip')
    with derecha:
        st.markdown('<div class="section-kicker">PRUÉBALO PRIMERO</div>', unsafe_allow_html=True)
        st.subheader('Explora con un ejemplo')
        st.write('Ocho imágenes ficticias y un acta para recorrer todo el proceso y descargar los resultados.')
        st.button('Probar con un ejemplo', on_click=cargar_demo, width='stretch', key='cargar_ejemplo')
        with st.expander('Cómo organizar tu ZIP', expanded=True):
            st.markdown('**Diseños:** pueden ir juntos.\n\n**Fotografías:** usa carpetas como `fotos_evento`.\n\n**Actas:** colócalas dentro de `actas`.\n\n**Conceptualización:** usa `conceptualizacion`.')
    with st.expander('Medidas que reconoce el programa'):
        st.table(pd.DataFrame({'Tipo':['Banner','Wallpaper','Flyer','Popup','Boletín','Diseño vario'],
                               'Medidas':['1240 × 413 o 430','1920 × 1080','1080 de ancho, alto variable',
                                          '800 de ancho, alto ≥ 450','600 × 300, 900 × 400 o 430','Otras dimensiones']}))

elif carga is None:
    st.info('Primero carga tus evidencias o prueba con el ejemplo.')
    st.button('Probar con un ejemplo', on_click=cargar_demo, key='cargar_ejemplo')

elif st.session_state.paso == ETAPAS[1]:
    st.markdown('<div class="section-kicker">PASO 02</div>', unsafe_allow_html=True)
    st.subheader('Revisa las piezas antes de generar')
    st.caption(st.session_state.nombre_carga)
    st.write('Haz clic en una celda para cambiar el tipo o el nombre de la actividad. Desmarca «Incluir» para excluir una imagen.')
    if carga['avisos']:
        with st.expander(f"{len(carga['avisos'])} aviso(s) de la carga"):
            for aviso in carga['avisos']:
                st.write(aviso)
    if filas:
        editor = st.data_editor(pd.DataFrame(st.session_state.filas_base),
            key='piezas_'+st.session_state.editor_id, hide_index=True, width='stretch', height=350,
            disabled=['Archivo', 'Medidas'],
            column_order=['Incluir','Tipo','Actividad','Medidas','Revisado','Archivo'],
            column_config={
                'Incluir':st.column_config.CheckboxColumn('Incluir', width='small'),
                'Revisado':st.column_config.CheckboxColumn('Revisado', width='small'),
                'Tipo':st.column_config.SelectboxColumn('Tipo de pieza', options=TIPOS, required=True, width='medium'),
                'Actividad':st.column_config.TextColumn('Nombre de la actividad', required=True, max_chars=200, width='large'),
                'Archivo':st.column_config.TextColumn('Archivo original', width='large'),
                'Medidas':st.column_config.TextColumn('Dimensiones', width='small')})
        st.session_state.filas_actuales = editor.to_dict('records')
        filas = st.session_state.filas_actuales
        pendientes = sum(f['Incluir'] and not f['Revisado'] for f in filas)
        st.caption(f'{pendientes} imagen(es) sin marcar como revisadas. Las medidas orientan la clasificación; los nombres deben indicar el tema.')
    if actas_filas:
        with st.expander(f'Actas de reunión ({len(actas_filas)})', expanded=False):
            editor_actas = st.data_editor(pd.DataFrame(st.session_state.actas_base),
                key='actas_'+st.session_state.editor_id, hide_index=True, width='stretch',
                disabled=['Acta','Formato'],
                column_config={'Incluir':st.column_config.CheckboxColumn('Incluir')})
            st.session_state.actas_actuales = editor_actas.to_dict('records')
    st.divider()
    st.subheader('Vista previa de una evidencia')
    opciones = [f['Archivo'] for f in filas if f['Incluir']]
    if opciones:
        seleccionada = st.selectbox('Selecciona una imagen', opciones, key='imagen_previa')
        fila = next(f for f in filas if f['Archivo'] == seleccionada)
        a,b = st.columns([1.7,1])
        with a:
            with Image.open(carga['raiz']/seleccionada) as original:
                vista = ImageOps.exif_transpose(original).copy()
                vista.thumbnail((720, 480))
            st.image(vista)
        with b:
            st.markdown('**'+str(fila['Actividad'])+'**')
            st.write(fila['Tipo'])
            st.caption(fila['Medidas']+' px')
            st.caption('Se conserva la proporción original al colocarla en el soporte.')
    st.info('Cuando termines, abre «03 · Generar» para preparar los documentos.')

else:
    st.markdown('<div class="section-kicker">PASO 03</div>', unsafe_allow_html=True)
    st.subheader('Prepara tus documentos')
    try:
        piezas, actas = seleccion(carga, filas, actas_filas)
    except ValueError as error:
        st.error(str(error))
        st.stop()
    if any(a.suffix.lower() == '.docx' for a in actas) and not buscar_libreoffice():
        st.warning('Tus actas están en Word. Para incluirlas en el soporte, instala LibreOffice o vuelve a cargar esas actas como PDF. También puedes excluirlas en la revisión.')
    a,b = st.columns([1.55,1], gap='large')
    with a:
        with st.container(border=True):
            st.markdown('### Esto se incluirá')
            conteos = Counter(p['tipo'] for p in piezas)
            st.dataframe(pd.DataFrame([{'Categoría':t, 'Archivos':n} for t,n in conteos.items()]), hide_index=True, width='stretch')
            st.caption(f'{len(actas)} acta(s) se anexarán completas al final del PDF.')
    with b:
        st.markdown('### Dos documentos, una revisión')
        st.markdown('**Soporte PDF**\n\nImágenes organizadas por tipo, con sus nombres y las actas al final.\n\n**Listado Word**\n\nActividades agrupadas para revisar y copiar al portal.')
    st.checkbox('Revisé los nombres, las categorías y los archivos incluidos.', key='confirmacion')
    firma = huella_revision(filas, actas_filas, st.session_state.periodo, st.session_state.contrato)
    if st.button('Generar PDF y Word', type='primary', disabled=not st.session_state.confirmacion,
                 key='generar', width='stretch'):
        try:
            with st.spinner('Organizando imágenes y preparando documentos…'):
                resultado = generar_documentos(carga, filas, actas_filas,
                                                st.session_state.periodo, st.session_state.contrato)
            st.session_state.resultado = resultado
            st.session_state.firma_resultado = firma
        except Exception as error:
            st.error('No se pudieron generar los documentos: ' + str(error))
    resultado = st.session_state.get('resultado')
    if resultado and st.session_state.get('firma_resultado') == firma:
        st.success(f"Documentos listos: {resultado['paginas']} páginas de soporte, {resultado['imagenes']} imágenes y {resultado['actas']} actas.")
        a,b,c = st.columns(3)
        a.download_button('Descargar soporte PDF', resultado['archivos']['soporte_actividades.pdf'],
                          file_name='soporte_actividades.pdf', mime='application/pdf', width='stretch')
        b.download_button('Descargar listado Word', resultado['archivos']['listado_actividades.docx'],
                          file_name='listado_actividades.docx',
                          mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document', width='stretch')
        c.download_button('Descargar todo en ZIP', resultado['zip'], file_name='informe_y_soporte.zip',
                          mime='application/zip', width='stretch')
        with st.expander('Ver y copiar el listado', expanded=True):
            st.text_area('Listado generado', resultado['texto'], height=360)
        with st.expander('Vista previa del PDF'):
            datos = base64.b64encode(resultado['archivos']['soporte_actividades.pdf']).decode()
            components.html(f'<iframe src="data:application/pdf;base64,{datos}" width="100%" height="680" style="border:0"></iframe>', height=690)
            st.caption('Si tu navegador no muestra la vista previa, descarga y abre el PDF.')
    elif resultado:
        st.info('Cambiaste la revisión o los datos del informe. Genera de nuevo para descargar una versión actualizada.')

st.divider()
st.caption('Los nombres provienen de tus archivos. Revisa el informe antes de usarlo en el portal. Descarga los resultados antes de cerrar la sesión.')
