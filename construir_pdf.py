# -*- coding: utf-8 -*-
"""
Construye el PDF INTERIOR (6x9") de "Vertex MCP Bible" para el paperback de KDP,
a partir del mismo manuscrito Markdown que usa construir_epub.py.

Reutiliza la limpieza de escapes de Google y la division por capitulos del
generador de EPUB, pero produce un PDF de tamano fijo con:
  - Pagina 6 x 9 pulgadas (estandar de libro tecnico).
  - Margenes KDP con gutter interior generoso (0.85") para la encuadernacion.
  - Numeros de pagina al pie.
  - Portadilla + pagina de creditos.
  - Cada capitulo empieza en pagina nueva; marcadores (bookmarks) por capitulo.

Usa xhtml2pdf porque instala LIMPIO en Windows con solo pip (no necesita las
librerias de sistema GTK/cairo que exige weasyprint).

Dependencias:
    pip install markdown xhtml2pdf pypdf

Uso:
    python construir_pdf.py

IMPORTANTE: KDP NO usa este PDF como portada. La portada del paperback es un
archivo aparte (frente + lomo + dorso) cuyo ancho de lomo depende del numero de
paginas que reporta este script al terminar.
"""

import html
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print("Falta 'markdown'.  pip install markdown", file=sys.stderr)
    sys.exit(1)

try:
    from xhtml2pdf import pisa
except ImportError:
    print("Falta 'xhtml2pdf'.  pip install xhtml2pdf", file=sys.stderr)
    sys.exit(1)

# ==================================================================
# METADATOS
# ==================================================================

TITULO = "Vertex MCP Bible"
SUBTITULO = "VIC: ingenieria de un nucleo de ciberseguridad autonoma con MCP, LangGraph y modelos locales"
AUTOR = "Denis Sanchez Leyva"
EDITORIAL = "Vertex Coders LLC"
ANIO = "2026"

RAIZ = Path(__file__).parent
MANUSCRITO_FILE = RAIZ / "Vertex MCP Bible.md"
SALIDA = RAIZ / "Vertex-MCP-Bible-interior.pdf"

OMITIR_TITULOS = {
    "tabla de contenidos", "tabla de contenido", "contenido", "contenidos",
    "indice", "índice", "tabla de contenidos (toc)",
}

# ==================================================================
# LECTURA + LIMPIEZA  (misma logica que construir_epub.py)
# ==================================================================

_ESCAPES = re.compile(r"\\([#*~>\[\]!().\-_`])")
_ENTIDADES_XML_OK = {"amp", "lt", "gt", "quot", "apos"}
_ENTIDAD_NOMBRADA = re.compile(r"&([a-zA-Z][a-zA-Z0-9]*);")


def _limpiar_escapes_codigo(linea: str) -> str:
    # Los bloques de codigo del export de Google tambien traen escapes (\#, \-)
    # que hay que quitar, pero SIN tocar los backslashes dobles legitimos de las
    # rutas JSON (p.ej. "G:\\Astra\\.venv"). Se protegen los dobles primero.
    l = linea.replace("\\\\", "\x00")
    l = _ESCAPES.sub(r"\1", l)
    return l.replace("\x00", "\\\\")


def _envolver_codigo(linea: str, ancho: int = 62) -> list:
    # xhtml2pdf NO hace word-wrap en <pre>, asi que partimos a mano las lineas de
    # codigo largas para que no se desborden del margen (KDP rechaza el PDF si el
    # contenido invade el gutter). La continuacion se indenta, y NUNCA se corta
    # dentro de esa sangria: asi cada iteracion acorta y no hay bucle infinito.
    if len(linea) <= ancho:
        return [linea]
    indent = len(linea) - len(linea.lstrip())
    sangria = min(indent + 4, 12)
    prefijo = " " * sangria
    minimo = sangria + 1  # progreso garantizado: el corte siempre supera al prefijo
    partes, resto = [], linea
    while len(resto) > ancho:
        corte = -1
        for sep in ("/", " ", ",", "&", ";", "="):
            idx = resto.rfind(sep, minimo, ancho)
            if idx > corte:
                corte = idx
        corte = (corte + 1) if corte >= minimo else ancho
        partes.append(resto[:corte])
        resto = prefijo + resto[corte:]
    partes.append(resto)
    return partes


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
            # Quitamos las lineas en blanco espurias que Google intercala entre
            # cada linea de codigo, y limpiamos los escapes conservando los \\.
            if linea.strip() == "":
                continue
            salida.extend(_envolver_codigo(_limpiar_escapes_codigo(linea)))
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
    return [(t, md) for t, md in secciones if t.strip().lower() not in OMITIR_TITULOS]


def normalizar_entidades(texto: str) -> str:
    def _repl(m):
        if m.group(1) in _ENTIDADES_XML_OK:
            return m.group(0)
        return html.unescape(m.group(0))
    return _ENTIDAD_NOMBRADA.sub(_repl, texto)


def convertir(md: str) -> str:
    md = normalizar_entidades(md)
    return markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"], output_format="html5")

# ==================================================================
# ESTILO DEL PDF (6x9, KDP)
# ==================================================================
# Fuentes: usamos las de Windows (Georgia serif + Consolas mono), presentes en
# cualquier instalacion, con buen soporte Unicode (flechas, tildes, guiones).

CSS = """
@font-face { font-family: "BodySerif"; src: url("C:/Windows/Fonts/georgia.ttf"); }
@font-face { font-family: "BodySerif"; src: url("C:/Windows/Fonts/georgiab.ttf"); font-weight: bold; }
@font-face { font-family: "BodySerif"; src: url("C:/Windows/Fonts/georgiai.ttf"); font-style: italic; }
@font-face { font-family: "CodeMono"; src: url("C:/Windows/Fonts/consola.ttf"); }

@page {
    size: 6in 9in;
    margin-top: 0.75in;
    margin-bottom: 0.75in;
    margin-left: 0.85in;
    margin-right: 0.6in;
    @frame footer {
        -pdf-frame-content: footerContent;
        bottom: 0.45in;
        margin-left: 0.6in;
        margin-right: 0.6in;
        height: 0.25in;
    }
}

body { font-family: "BodySerif"; font-size: 11pt; line-height: 1.4; color: #111111; text-align: left; }
h1 { font-family: "BodySerif"; font-weight: bold; font-size: 20pt; color: #0a2233;
     page-break-before: always; -pdf-outline: true; -pdf-outline-level: 0;
     margin-top: 0.5in; margin-bottom: 0.2in; }
h2 { font-family: "BodySerif"; font-weight: bold; font-size: 14pt; color: #123;
     margin-top: 16pt; margin-bottom: 4pt; -pdf-keep-with-next: true; }
h3 { font-family: "BodySerif"; font-weight: bold; font-size: 12pt;
     margin-top: 12pt; margin-bottom: 3pt; -pdf-keep-with-next: true; }
p { margin: 5pt 0; }
strong, b { font-weight: bold; }
em, i { font-style: italic; }
pre { font-family: "CodeMono"; font-size: 8.5pt; background-color: #f4f4f4;
      padding: 6pt; margin: 8pt 0; }
code { font-family: "CodeMono"; font-size: 9.5pt; }
ul, ol { margin: 5pt 0 5pt 16pt; }
li { margin: 2pt 0; }
table { border-collapse: collapse; margin: 8pt 0; }
th, td { border: 0.5pt solid #999999; padding: 3pt 5pt; font-size: 9pt; }
th { background-color: #eeeeee; font-weight: bold; }
.frontmatter { text-align: center; }
"""


def construir() -> int:
    if not MANUSCRITO_FILE.exists():
        print(f"No existe {MANUSCRITO_FILE}", file=sys.stderr)
        return 1

    secciones = cargar_secciones()
    if not secciones:
        print("No se detecto ninguna seccion (## ...).", file=sys.stderr)
        return 1

    # ---- Portadilla + creditos (front matter, sin salto forzado del h1) ----
    portadilla = (
        '<div class="frontmatter">'
        '<div style="margin-top: 2.2in; font-size: 30pt; font-weight: bold; color:#0a2233;">'
        f'{html.escape(TITULO)}</div>'
        f'<div style="margin-top: 0.3in; font-size: 12.5pt; font-style: italic;">{html.escape(SUBTITULO)}</div>'
        f'<div style="margin-top: 1.6in; font-size: 13pt;">{html.escape(AUTOR)}</div>'
        f'<div style="font-size: 11pt; color:#555;">{html.escape(EDITORIAL)}</div>'
        '</div>'
        '<div style="page-break-after: always;"></div>'
    )
    creditos = (
        '<div style="margin-top: 5.5in; font-size: 9pt; color:#333; line-height:1.5;">'
        f'&#169; {ANIO} {html.escape(AUTOR)} / {html.escape(EDITORIAL)}, Miami, FL.<br/>'
        'Todos los derechos reservados. Ninguna parte de esta publicacion puede ser '
        'reproducida sin autorizacion previa del autor.<br/><br/>'
        f'{html.escape(TITULO)}<br/>Primera edicion, {ANIO}.'
        '</div>'
        '<div style="page-break-after: always;"></div>'
    )

    cuerpo = [portadilla, creditos]
    for titulo, md in secciones:
        cuerpo.append(convertir(md))

    # Pie con numero de pagina (xhtml2pdf lo repite en cada pagina via @frame)
    footer = (
        '<div id="footerContent" style="text-align:center; font-family:CodeMono; '
        'font-size:9pt; color:#777;"><pdf:pagenumber /></div>'
    )

    documento = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        f"<style>{CSS}</style></head><body>"
        + "".join(cuerpo)
        + footer
        + "</body></html>"
    )

    with open(SALIDA, "wb") as f:
        estado = pisa.CreatePDF(documento, dest=f, encoding="utf-8")

    if estado.err:
        print(f"xhtml2pdf reporto {estado.err} error(es) al generar el PDF.", file=sys.stderr)
        return 1

    print(f"Generado: {SALIDA}")
    print(f"  {len(secciones)} secciones + portadilla + creditos")

    # ---- Conteo de paginas (clave para el ancho del lomo de la portada) ----
    try:
        from pypdf import PdfReader
        n = len(PdfReader(str(SALIDA)).pages)
        print(f"\n  >>> PAGINAS: {n}  <<<")
        print("  Con este numero se calcula el lomo de la portada del paperback.")
        # Regla KDP de margen interior minimo segun paginas:
        if n <= 150:
            rec = "0.375in (tienes 0.85in, sobra)"
        elif n <= 300:
            rec = "0.5in (tienes 0.85in, OK)"
        elif n <= 500:
            rec = "0.625in (tienes 0.85in, OK)"
        elif n <= 700:
            rec = "0.75in (tienes 0.85in, OK)"
        else:
            rec = "0.875in (AJUSTA: sube el gutter a 0.9in)"
        print(f"  Gutter minimo KDP para {n} paginas: {rec}")
    except ImportError:
        print("\n  (instala pypdf para ver el conteo de paginas: pip install pypdf)")

    print("\n  NOTA: revisa el PDF en un lector antes de subirlo. Si alguna fuente")
    print("  no cargo, ajusta las rutas de C:/Windows/Fonts en el CSS.")
    return 0


if __name__ == "__main__":
    sys.exit(construir())
