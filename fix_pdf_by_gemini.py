# -*- coding: utf-8 -*-
"""
Construye el EPUB de "Vertex MCP Bible" a partir del manuscrito en Markdown.
Optimizado con márgenes de impresión (Gutter) para KDP.
"""

import argparse
import html
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import markdown
except ImportError:
    print("Falta la libreria markdown.  pip install markdown", file=sys.stderr)
    sys.exit(1)

# ==================================================================
# METADATOS
# ==================================================================

TITULO = "Vertex MCP Bible"
SUBTITULO = "VIC: ingenieria de un nucleo de ciberseguridad autonoma con MCP, LangGraph y modelos locales"
AUTOR = "Denis Sanchez Leyva"
IDIOMA = "es"
EDITORIAL = "Vertex Coders LLC"
IDENTIFICADOR = "urn:uuid:7f1c2a90-4d5e-4b83-9e21-vertexmcpbible2026"

RAIZ = Path(__file__).parent
MANUSCRITO_FILE = RAIZ / "Vertex MCP Bible.md"
SALIDA = RAIZ / "Vertex-MCP-Bible.epub"

OMITIR_TITULOS = {"tabla de contenidos", "tabla de contenido", "contenido", "contenidos", "indice", "índice", "tabla de contenidos (toc)"}

PORTADAS_POSIBLES = [
    (RAIZ / "assets" / "portada.jpg", "image/jpeg", "portada.jpg"),
    (RAIZ / "assets" / "portada.jpeg", "image/jpeg", "portada.jpg"),
    (RAIZ / "assets" / "portada.png", "image/png", "portada.png"),
]

def buscar_portada():
    for ruta, mime, nombre in PORTADAS_POSIBLES:
        if ruta.exists():
            return ruta, mime, nombre
    return None

def comprobar_portada(ruta: Path) -> list:
    avisos = []
    try:
        from PIL import Image  # type: ignore
        with Image.open(ruta) as img:
            ancho, alto = img.size
            avisos.append(f"dimensiones: {ancho} x {alto}")
            if ancho < 1000:
                avisos.append(f"AVISO: {ancho} px de ancho. KDP pide al menos 1000 y recomienda 1600 x 2560.")
            elif (ancho, alto) != (1600, 2560):
                avisos.append("Nota: KDP recomienda exactamente 1600 x 2560.")
            proporcion = alto / ancho if ancho else 0
            if abs(proporcion - 1.6) > 0.05:
                avisos.append(f"AVISO: la proporcion es 1:{proporcion:.2f} y KDP quiere 1:1.6.")
    except ImportError:
        avisos.append("(instala Pillow para comprobar las dimensiones: pip install Pillow)")
    except Exception as exc:
        avisos.append(f"No se pudo leer la imagen: {exc}")

    kb = ruta.stat().st_size / 1024
    avisos.append(f"peso: {kb:.0f} KB")
    if kb < 150:
        avisos.append("AVISO: pesa poco para una portada. Puede estar muy comprimida.")
    return avisos

# ==================================================================
# LECTURA + LIMPIEZA DEL MANUSCRITO UNICO (REGEX CORREGIDA)
# ==================================================================

# CORRECCIÓN: El guion (-) se coloca al final de la clase para evitar errores de rango
_ESCAPES = re.compile(r"\\([#*~>\[\]!()._`-])")

def _limpiar_escapes_codigo(linea: str) -> str:
    l = linea.replace("\\\\", "\x00")
    l = _ESCAPES.sub(r"\1", l)
    return l.replace("\x00", "\\\\")

def _cargar_lineas_limpias() -> list:
    texto = MANUSCRITO_FILE.read_text(encoding="utf-8")
    salida = []
    dentro_codigo = False

    for linea_raw in texto.split("\n"):
        linea = linea_raw.replace("\\`", "`")

        if linea.lstrip().startswith("```"):
            dentro_codigo = not dentro_codigo
            salida.append(linea)
            continue

        if dentro_codigo:
            if linea.strip() == "":
                continue 
            salida.append(_limpiar_escapes_codigo(linea))
        else:
            salida.append(_ESCAPES.sub(r"\1", linea))

    return salida

def cargar_secciones() -> list:
    lineas = _cargar_lineas_limpias()
    secciones = []
    titulo_actual = None
    buffer = []
    dentro_codigo = False

    def flush():
        if titulo_actual is not None:
            secciones.append((titulo_actual, "\n".join(buffer)))

    for linea in lineas:
        if linea.lstrip().startswith("```"):
            dentro_codigo = not dentro_codigo
            if titulo_actual is not None:
                buffer.append(linea)
            continue

        if not dentro_codigo and linea.startswith("## ") and not linea.startswith("### "):
            flush()
            titulo_actual = linea[3:].strip()
            buffer = ["# " + titulo_actual]
            continue

        if titulo_actual is None:
            continue 

        if not dentro_codigo and (linea.startswith("### ") or linea.startswith("#### ")):
            linea = linea[1:]
        buffer.append(linea)

    flush()

    return [
        (titulo, md)
        for titulo, md in secciones
        if titulo.strip().lower() not in OMITIR_TITULOS
    ]

# ==================================================================
# ESTILO Y CONVERSIÓN (CON SOPORTE DE GUTTER PARA KDP)
# ==================================================================

CSS = """
@page {
    size: 6in 9in;
    margin-top: 0.75in;
    margin-bottom: 0.75in;
    margin-left: 0.875in; /* Margen interior / Gutter forzado > 0.375in */
    margin-right: 0.75in;
}

body { margin: 0; line-height: 1.5; text-align: left; }
h1 { font-size: 1.6em; margin: 2em 0 1em 0; page-break-before: always; }
h2 { font-size: 1.25em; margin: 1.8em 0 0.6em 0; }
h3 { font-size: 1.1em;  margin: 1.4em 0 0.5em 0; }
h1, h2, h3, h4 {
    page-break-after: avoid;
    break-after: avoid-page;
    page-break-inside: avoid;
    break-inside: avoid;
    orphans: 3;
    widows: 3;
}
p, li { orphans: 3; widows: 3; margin: 0.6em 0; }
pre {
    font-family: monospace;
    font-size: 0.75em;
    line-height: 1.35;
    background: #f4f4f4;
    padding: 0.6em;
    margin: 1em 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
}
code { font-family: monospace; font-size: 0.9em; }
blockquote {
    margin: 1.2em 1em;
    padding-left: 0.8em;
    border-left: 3px solid #999;
    font-style: italic;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.8em;
}
th, td {
    border: 1px solid #bbb;
    padding: 0.3em 0.4em;
    text-align: left;
    vertical-align: top;
}
th { background: #eee; font-weight: bold; }
pre, table, blockquote { page-break-inside: avoid; break-inside: avoid; }
ul, ol { margin: 0.6em 0 0.6em 1.2em; }
li { margin: 0.3em 0; }
.portada { text-align: center; margin-top: 25%; }
.portada h1 { font-size: 2.2em; page-break-before: avoid; }
.portada h2 { font-size: 1.2em; font-weight: normal; font-style: italic; }
.portada p { margin-top: 3em; }
"""

PLANTILLA = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"
      lang="{idioma}" xml:lang="{idioma}">
<head>
  <meta charset="utf-8"/>
  <title>{titulo}</title>
  <link rel="stylesheet" type="text/css" href="estilo.css"/>
</head>
<body>
{cuerpo}
</body>
</html>
"""

def a_xhtml(titulo: str, cuerpo: str) -> str:
    return PLANTILLA.format(idioma=IDIOMA, titulo=html.escape(titulo), cuerpo=cuerpo)

_ENTIDADES_XML_OK = {"amp", "lt", "gt", "quot", "apos"}
_ENTIDAD_NOMBRADA = re.compile(r"&([a-zA-Z][a-zA-Z0-9]*);")

def normalizar_entidades(texto: str) -> str:
    def _repl(m):
        if m.group(1) in _ENTIDADES_XML_OK:
            return m.group(0)
        return html.unescape(m.group(0))
    return _ENTIDAD_NOMBRADA.sub(_repl, texto)

def convertir(md: str) -> str:
    md = normalizar_entidades(md)
    return markdown.markdown(
        md,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="xhtml",
    )

def construir() -> int:
    if not MANUSCRITO_FILE.exists():
        print(f"No existe {MANUSCRITO_FILE}", file=sys.stderr)
        return 1

    secciones = cargar_secciones()
    if not secciones:
        print("No se detecto ninguna seccion (## ...) en el manuscrito.", file=sys.stderr)
        return 1

    documentos = []
    portadilla = (
        f'<div class="portada">\n'
        f'  <h1>{html.escape(TITULO)}</h1>\n'
        f'  <h2>{html.escape(SUBTITULO)}</h2>\n'
        f'  <p>{html.escape(AUTOR)}</p>\n'
        f'  <p>{html.escape(EDITORIAL)}</p>\n'
        f'</div>'
    )
    documentos.append(("portadilla.xhtml", TITULO, a_xhtml(TITULO, portadilla)))

    posicion_indice = len(documentos)
    documentos.append(("indice.xhtml", "Índice", ""))

    for i, (titulo, md) in enumerate(secciones):
        documentos.append((f"seccion-{i:02d}.xhtml", titulo, a_xhtml(titulo, convertir(md))))

    filas = "\n".join(
        f'    <li><a href="{n}">{html.escape(t)}</a></li>'
        for n, t, _ in documentos[posicion_indice + 1:]
    )
    documentos[posicion_indice] = (
        "indice.xhtml", "Índice",
        a_xhtml("Índice", f'<h1>Índice</h1>\n<ul>\n{filas}\n</ul>'),
    )

    enlaces = "\n".join(
        f'      <li><a href="{n}">{html.escape(t)}</a></li>'
        for n, t, _ in documentos[1:]
    )
    nav = a_xhtml("Índice", (
        '<nav epub:type="toc" id="toc">\n'
        '  <h1>Índice</h1>\n'
        '  <ol>\n' + enlaces + '\n  </ol>\n'
        '</nav>'
    ))

    puntos = "\n".join(
        f'    <navPoint id="n{i}" playOrder="{i}">\n'
        f'      <navLabel><text>{html.escape(t)}</text></navLabel>\n'
        f'      <content src="{n}"/>\n'
        f'    </navPoint>'
        for i, (n, t, _) in enumerate(documentos, 1)
    )
    ncx = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
        '  <head><meta name="dtb:uid" content="' + IDENTIFICADOR + '"/></head>\n'
        '  <docTitle><text>' + html.escape(TITULO) + '</text></docTitle>\n'
        '  <navMap>\n' + puntos + '\n  </navMap>\n'
        '</ncx>\n'
    )

    portada = buscar_portada()
    items = [
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '    <item id="css" href="estilo.css" media-type="text/css"/>',
    ]
    if portada:
        _, mime_portada, nombre_portada = portada
        items.append(f'    <item id="cover-image" href="{nombre_portada}" '
                     f'media-type="{mime_portada}" properties="cover-image"/>')

    columna = []
    for i, (nombre, _, _) in enumerate(documentos):
        ident = f"doc{i}"
        items.append(f'    <item id="{ident}" href="{nombre}" media-type="application/xhtml+xml"/>')
        columna.append(f'    <itemref idref="{ident}"/>')

    modificado = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f'    <dc:identifier id="pub-id">{IDENTIFICADOR}</dc:identifier>\n'
        f'    <dc:title>{html.escape(TITULO)}: {html.escape(SUBTITULO)}</dc:title>\n'
        f'    <dc:creator>{html.escape(AUTOR)}</dc:creator>\n'
        f'    <dc:publisher>{html.escape(EDITORIAL)}</dc:publisher>\n'
        f'    <dc:language>{IDIOMA}</dc:language>\n'
        f'    <meta property="dcterms:modified">{modificado}</meta>\n'
        + ('    <meta name="cover" content="cover-image"/>\n' if portada else '')
        + '  </metadata>\n'
        '  <manifest>\n' + "\n".join(items) + '\n  </manifest>\n'
        '  <spine toc="ncx">\n' + "\n".join(columna) + '\n  </spine>\n'
        '</package>\n'
    )

    with zipfile.ZipFile(SALIDA, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml",
                   '<?xml version="1.0" encoding="utf-8"?>\n'
                   '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
                   '  <rootfiles>\n'
                   '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
                   '  </rootfiles>\n'
                   '</container>\n',
                   compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/estilo.css", CSS, zipfile.ZIP_DEFLATED)
        for nombre, _, contenido in documentos:
            z.writestr(f"OEBPS/{nombre}", contenido, zipfile.ZIP_DEFLATED)
        if portada:
            ruta_portada, _, nombre_portada = portada
            z.write(ruta_portada, f"OEBPS/{nombre_portada}", zipfile.ZIP_DEFLATED)

    tamano = SALIDA.stat().st_size / 1024
    print(f"Generado: {SALIDA}")
    print(f"  {len(secciones)} secciones, {len(documentos)} documentos, {tamano:.0f} KB")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el EPUB de Vertex MCP Bible")
    args = parser.parse_args()
    return construir()

if __name__ == "__main__":
    sys.exit(main())