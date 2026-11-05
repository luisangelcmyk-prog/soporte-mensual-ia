# Soporte mensual

Prototipo funcional en Streamlit para organizar evidencias de diseño gráfico y generar el soporte PDF y el listado Word de actividades.

## Abrirlo en tu computador

1. Descomprime el ZIP en una carpeta.
2. Si usas Windows y tienes Python instalado, abre `INICIAR_WINDOWS.bat`.
3. La primera vez se instalan las bibliotecas. Después se abre la aplicación en tu navegador.
4. Pulsa **Probar con un ejemplo** para recorrer la aplicación sin cargar archivos.

También puedes abrir una terminal en la carpeta y ejecutar:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

En Windows puedes sustituir `python` por `py`. Se recomienda Python 3.11 o 3.12. Si necesitas instalarlo: https://www.python.org/downloads/.

Una ejecución local abre una dirección como localhost:8501. Esa dirección solo sirve en tu computador. Para obtener un enlace compartible, publica la aplicación con los pasos de `PUBLICAR_EN_STREAMLIT.md`.

## Lo que puedes hacer

- Cargar un ZIP con JPG/PNG y actas PDF/DOCX.
- Leer dimensiones y clasificar automáticamente banners, flyers, wallpapers, popups y boletines.
- Cambiar nombres y categorías en una tabla.
- Excluir imágenes o actas y marcar las imágenes revisadas.
- Ver las imágenes antes de generar los documentos.
- Generar un soporte PDF con imágenes en dos columnas y actas anexas.
- Descargar el listado Word y copiar su texto desde la aplicación.
- Descargar un ZIP con PDF, Word, inventario, revisión y avisos.

Si cambias los datos o las evidencias después de generar, las descargas anteriores se ocultan hasta generar de nuevo. El programa conserva los originales sin modificarlos.

## Organización del ZIP

Los diseños pueden ir juntos, en la raíz o en una carpeta `piezas`. Las fotos deben ir en carpetas como `fotos_halloween` o dentro de `fotografias`, con una subcarpeta por evento. Las actas van dentro de `actas`. Las evidencias para la obligación 3 se pueden colocar en `conceptualizacion`.

El programa acepta una carpeta exterior del mes. Los nombres se obtienen de los archivos: si un archivo tiene un nombre técnico, corrígelo en la tabla. Un evento con varias fotos se menciona una vez en Word. Los archivos duplicados se incluyen por separado mientras no los excluyas.

## Medidas reconocidas

| Tipo | Dimensiones |
| --- | --- |
| Banner | 1240 × 413 o 1240 × 430 |
| Wallpaper | 1920 × 1080 |
| Flyer | Ancho 1080, alto variable |
| Popup | Ancho 800, alto mayor o igual a 450 |
| Boletín | 600 × 300, 900 × 400 o 900 × 430 |
| Diseño vario | Las demás dimensiones |

El tamaño orienta la clasificación; puedes corregir cualquier caso en la tabla. Las fotografías se identifican por la carpeta, no por sus dimensiones.

## Actas Word

Para convertir actas DOCX y añadirlas completas al soporte necesitas LibreOffice. La aplicación intenta encontrarlo automáticamente en Windows o en PATH. Descarga: https://www.libreoffice.org/download/.

Si no está instalado, puedes exportar las actas a PDF desde Word y cargarlas así. En Streamlit Community Cloud, el archivo `packages.txt` indica que debe instalarse `libreoffice-writer`. Siempre se revisa que la conversión produzca un PDF. Si falla, la aplicación muestra el error y no declara los documentos terminados.

## Cómo explicar el proyecto

- `app.py`: interfaz. Presenta botones, la tabla de revisión y las descargas.
- `servicio.py`: recibe el ZIP, aplica las decisiones de la revisión y prepara los resultados.
- `algoritmo.py`: código original extraído del PDF entregado. Mantiene las reglas y las funciones de generación.
- `ejemplo.py`: crea datos ficticios para probar.
- `requirements.txt`: bibliotecas Python.
- `packages.txt`: conversor de actas para publicar en Community Cloud.
- `.streamlit/config.toml`: aspecto visual y configuración.
- `test_prototipo.py`: pruebas del servicio y de la interfaz.

Streamlit vuelve a ejecutar el archivo cuando interactúas con un botón o una tabla. `st.session_state` conserva la carga, la revisión y los resultados de esa sesión. Cada carga tiene una carpeta temporal diferente.

## Pruebas

```bash
python -m unittest -v
```

Se comprueban la lectura y clasificación, la edición de nombres, las exclusiones, el PDF con actas, el Word, la agrupación de eventos, el ZIP de salida, los datos no válidos y el recorrido simulado de la interfaz con Streamlit AppTest. El registro de la ejecución de esta entrega está en `PRUEBAS.txt`.

El código no requiere clave de IA ni llama al portal del contratista. El nombre de una pieza no se deduce de su contenido visual. Antes de radicar, revisa temas, cantidades, obligaciones y la legibilidad de las actas convertidas.

## Archivos y publicación

Al ejecutarlo localmente, los archivos se procesan en tu computador. Si lo publicas, los archivos se procesan temporalmente en el servidor de Streamlit, separados por sesión. No se envían a un modelo de IA. Descarga tus documentos antes de reiniciar o cerrar la sesión. Este prototipo no incluye cuentas de usuario ni un archivo histórico de informes.
