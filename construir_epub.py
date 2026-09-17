# -*- coding: utf-8 -*-
"""
Construye el EPUB de "Vertex MCP Bible" a partir del manuscrito en Markdown.

Adaptado del generador del libro anterior ("Preguntale a tus datos"). El nucleo
de generacion del EPUB (ZIP con estructura EPUB3, nav, ncx, CSS para tinta
electronica) ya estaba probado contra KDP y se conserva intacto. Lo que cambia
es la ENTRADA:

  - Antes: una carpeta manuscrito/ con un archivo por capitulo, ya limpio.
  - Ahora: UN solo archivo "Vertex MCP Bible.md" que salio de Google Docs y trae
    los capitulos con escapes de export (\\#\\#, \\*\\*, vallas de codigo escapadas).

Por eso este script:
  1. Lee el archivo unico y LIMPIA los escapes de Google (sin tocar el codigo).
  2. Lo divide en secciones por los encabezados de nivel 2 (## ...).
  3. Promueve cada capitulo a h1 y sus subsecciones a h2, para que el CSS de
     salto de pagina y tamanos funcione como en el libro anterior.

No hace falta pandoc ni Calibre. Unica dependencia externa:

    pip install markdown

Uso:
    python construir_epub.py                # genera el epub
    python construir_epub.py --revisar      # solo revisa, no genera
    python construir_epub.py --diagnostico  # busca problemas de conversion
    python construir_epub.py --todo         # incluye avisos marginales
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
# KDP asigna su propio identificador. Este UUID solo tiene que ser estable.
IDENTIFICADOR = "urn:uuid:7f1c2a90-4d5e-4b83-9e21-vertexmcpbible2026"

RAIZ = Path(__file__).parent
MANUSCRITO_FILE = RAIZ / "Vertex MCP Bible.md"
SALIDA = RAIZ / "Vertex-MCP-Bible.epub"

# Secciones cuyo unico proposito es indexar; el EPUB genera su propio indice,
# asi que estas se omiten para no duplicar.
OMITIR_TITULOS = {"tabla de contenidos", "tabla de contenido", "contenido", "contenidos", "indice", "índice", "tabla de contenidos (toc)"}

# La portada puede ser JPEG o PNG. KDP acepta los dos.
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
    """Avisa si la portada no cumple lo que pide KDP (1600x2560, 1:1.6)."""
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
# LECTURA + LIMPIEZA DEL MANUSCRITO UNICO
# ==================================================================

# Google Docs escapa la puntuacion de Markdown al exportar. Estos son los
# caracteres que hay que des-escapar EN LA PROSA (fuera de los bloques de codigo,
# donde un backslash puede ser legitimo, p.ej. rutas JSON "G:\\Astra\\.venv").
_ESCAPES = re.compile(r"\\([#*~>\[\]!().\-_`])")


def _cargar_lineas_limpias() -> list:
    """
    Lee el manuscrito y devuelve sus lineas ya des-escapadas, respetando los
    bloques de codigo: dentro de ``` solo se des-escapan las vallas y los
    backticks (artefacto de Google), el resto del codigo queda intacto.
    """
    texto = MANUSCRITO_FILE.read_text(encoding="utf-8")
    salida = []
    dentro_codigo = False

    for linea_raw in texto.split("\n"):
        # Des-escapar backticks primero: convierte las vallas escapadas (\`\`\`)
        # en vallas reales (```) para poder detectar los bloques de codigo.
        linea = linea_raw.replace("\\`", "`")

        if linea.lstrip().startswith("```"):
            dentro_codigo = not dentro_codigo
            salida.append(linea)
            continue

        if dentro_codigo:
            salida.append(linea)  # codigo intacto
        else:
            salida.append(_ESCAPES.sub(r"\1", linea))  # prosa: fuera los escapes

    return salida


def cargar_secciones() -> list:
    """
    Divide el manuscrito limpio en secciones por encabezado de nivel 2 (## ...).
    Cada capitulo se promueve a h1 y sus subsecciones (###, ####) suben un nivel,
    para encajar con el CSS heredado (salto de pagina y tamano de titulo en h1).

    Devuelve [(titulo, markdown_de_la_seccion)], omitiendo indices/TOC.
    Lo que va antes del primer '## ' (titulo del libro, subtitulo, TOC suelto) se
    descarta: la portadilla se genera de los metadatos.
    """
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

        # Un nuevo capitulo/seccion solo empieza con '## ' FUERA de un bloque.
        if not dentro_codigo and linea.startswith("## ") and not linea.startswith("### "):
            flush()
            titulo_actual = linea[3:].strip()
            buffer = ["# " + titulo_actual]  # capitulo promovido a h1
            continue

        if titulo_actual is None:
            continue  # frontmatter previo al primer capitulo: se descarta

        # Promover subsecciones un nivel (### -> ##, #### -> ###), solo en prosa.
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
# ESTILO  (identico al libro anterior: probado en tinta electronica y KDP)
# ==================================================================

CSS = """
body { margin: 0 5%; line-height: 1.5; text-align: left; }

h1 { font-size: 1.6em; margin: 2em 0 1em 0; page-break-before: always; }
h2 { font-size: 1.25em; margin: 1.8em 0 0.6em 0; }
h3 { font-size: 1.1em;  margin: 1.4em 0 0.5em 0; }

h1, h2, h3, h4 {
    page-break-after: avoid;
    break-after: avoid-page;
    page-break-inside: avoid;
    break-inside: avoid;
    -webkit-column-break-after: avoid;
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

# ==================================================================
# REVISION PARA TINTA ELECTRONICA
# ==================================================================

MAX_COLUMNAS_TABLA = 3
ANCHO_COMODO = 65
ANCHO_MOLESTO = 72
ANCHO_GRAVE = 85
MARCAS_PROHIBIDAS = ["[VERIFICAR", "[PENDIENTE", "TODO:", "FIXME", "XXX:"]


def revisar(md: str, nombre: str) -> list:
    avisos = []
    for numero, linea in enumerate(md.splitlines(), 1):
        if linea.strip().startswith("|") and linea.count("|") >= 2:
            columnas = len([c for c in linea.split("|")[1:-1]])
            if columnas > MAX_COLUMNAS_TABLA and set(linea.replace("|", "").strip()) <= set("-: "):
                avisos.append(("TABLA", f"{nombre}:{numero}  tabla de {columnas} columnas"))

    dentro = False
    for numero, linea in enumerate(md.splitlines(), 1):
        if linea.startswith("```"):
            dentro = not dentro
            continue
        if not dentro or len(linea) <= ANCHO_COMODO:
            continue
        if len(linea) >= ANCHO_GRAVE:
            gravedad = "GRAVE"
        elif len(linea) >= ANCHO_MOLESTO:
            gravedad = "MOLESTO"
        else:
            gravedad = "MARGINAL"
        avisos.append((gravedad, f"{nombre}:{numero}  {len(linea)} caracteres"))
    return avisos


def buscar_marcas(secciones) -> list:
    encontradas = []
    for titulo, md in secciones:
        for numero, linea in enumerate(md.splitlines(), 1):
            for marca in MARCAS_PROHIBIDAS:
                if marca in linea:
                    encontradas.append(f"{titulo}:{numero}  {linea.strip()[:90]}")
    return encontradas

# ==================================================================
# GENERACION
# ==================================================================

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


# Google Docs exporta entidades HTML nombradas (&nbsp;, &mdash;, &hellip;, comillas
# tipograficas...) que NO son validas en XHTML/XML estricto y hacen fallar al lector
# de EPUB con "Entity 'nbsp' not defined". Se convierten al caracter Unicode real,
# dejando intactas las 5 entidades que XML si define.
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


def diagnosticar() -> int:
    """Busca la causa mas comun de que un capitulo salga cortado: vallas impares."""
    print("=" * 70)
    print(" DIAGNOSTICO DE CONVERSION")
    print("=" * 70)

    if not MANUSCRITO_FILE.exists():
        print(f"NO EXISTE: {MANUSCRITO_FILE}")
        return 1

    secciones = cargar_secciones()
    print(f"{'Seccion':<44} {'MD':>7} {'XHTML':>8} {'Ratio':>7}  Vallas")
    print("-" * 70)

    problemas = []
    for titulo, md in secciones:
        vallas = sum(1 for l in md.splitlines() if l.startswith("```"))
        xhtml = convertir(md)
        ratio = len(xhtml) / len(md) if md else 0
        marca = ""
        if vallas % 2 != 0:
            marca = f"  <-- IMPAR ({vallas}), bloque sin cerrar"
            problemas.append(f"{titulo}: {vallas} vallas, numero impar")
        elif ratio < 0.9:
            marca = "  <-- ratio bajo, posible perdida"
            problemas.append(f"{titulo}: ratio {ratio:.2f}")
        print(f"{titulo[:44]:<44} {len(md):>7} {len(xhtml):>8} {ratio:>6.2f}  {vallas:>3}{marca}")

    print()
    marcas = buscar_marcas(secciones)
    if marcas:
        print("=" * 70)
        print(f" MARCAS DE TRABAJO SIN LIMPIAR: {len(marcas)}")
        print("=" * 70)
        for m in marcas:
            print(f"  {m}")
        problemas.extend(marcas)
        print()

    if problemas:
        print(f"{len(problemas)} PROBLEMA(S):")
        for p in problemas:
            print(f"  - {p}")
    else:
        print(f"Sin problemas: {len(secciones)} secciones, vallas cuadradas, sin perdida.")
    return 1 if problemas else 0


def construir() -> int:
    if not MANUSCRITO_FILE.exists():
        print(f"No existe {MANUSCRITO_FILE}", file=sys.stderr)
        return 1

    secciones = cargar_secciones()
    if not secciones:
        print("No se detecto ninguna seccion (## ...) en el manuscrito.", file=sys.stderr)
        return 1

    documentos = []  # (nombre_archivo, titulo, xhtml)

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

    # ---- indice visible ----
    filas = "\n".join(
        f'    <li><a href="{n}">{html.escape(t)}</a></li>'
        for n, t, _ in documentos[posicion_indice + 1:]
    )
    documentos[posicion_indice] = (
        "indice.xhtml", "Índice",
        a_xhtml("Índice", f'<h1>Índice</h1>\n<ul>\n{filas}\n</ul>'),
    )

    # ---- indice de navegacion (EPUB 3) ----
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

    # ---- indice antiguo (toc.ncx), que Kindle sigue usando ----
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
        f'  <head><meta name="dtb:uid" content="{IDENTIFICADOR}"/></head>\n'
        f'  <docTitle><text>{html.escape(TITULO)}</text></docTitle>\n'
        f'  <navMap>\n{puntos}\n  </navMap>\n'
        '</ncx>\n'
    )

    # ---- manifiesto ----
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

    # ---- empaquetado ----
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

    if portada:
        ruta_portada, mime_portada, _ = portada
        print(f"\n  Portada: {ruta_portada.name}  ({mime_portada})")
        for aviso in comprobar_portada(ruta_portada):
            print(f"    {aviso}")
    else:
        print("\n  SIN PORTADA. Pon una imagen en assets/portada.jpg o assets/portada.png")
        print("  KDP la quiere de 1600x2560 px. Sin ella el libro no se publica.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el EPUB de Vertex MCP Bible")
    parser.add_argument("--revisar", action="store_true", help="Solo revisa el manuscrito para tinta electronica")
    parser.add_argument("--todo", action="store_true", help="Muestra tambien los avisos marginales")
    parser.add_argument("--diagnostico", action="store_true", help="Busca secciones que se convierten mal o salen cortadas")
    args = parser.parse_args()

    if not MANUSCRITO_FILE.exists():
        print(f"No existe el manuscrito: {MANUSCRITO_FILE}", file=sys.stderr)
        return 1

    if args.diagnostico:
        return diagnosticar()

    secciones = cargar_secciones()
    todos = []
    for titulo, md in secciones:
        todos.extend(revisar(md, titulo))

    if todos:
        orden = {"TABLA": 0, "GRAVE": 1, "MOLESTO": 2, "MARGINAL": 3}
        conteo = {}
        for gravedad, _ in todos:
            conteo[gravedad] = conteo.get(gravedad, 0) + 1

        print(f"REVISION PARA TINTA ELECTRONICA: {len(todos)} avisos\n")
        print(f"  TABLA    (mas de 3 columnas, hay que reescribirlas) : {conteo.get('TABLA', 0)}")
        print(f"  GRAVE    (85+ car., parte 2-3 veces, ilegible)      : {conteo.get('GRAVE', 0)}")
        print(f"  MOLESTO  (72-84 car., parte una vez)                : {conteo.get('MOLESTO', 0)}")
        print(f"  MARGINAL (66-71 car., apenas se nota)               : {conteo.get('MARGINAL', 0)}")
        print("\nNota: el CSS fuerza el ajuste de linea, asi que nada se pierde.\n")

        for gravedad, mensaje in sorted(todos, key=lambda a: (orden[a[0]], a[1])):
            if gravedad == "MARGINAL" and not args.todo:
                continue
            print(f"  [{gravedad:<8}] {mensaje}")

        if conteo.get("MARGINAL") and not args.todo:
            print(f"\n  ({conteo['MARGINAL']} avisos MARGINAL ocultos. Usa --todo para verlos.)")
        print()
    else:
        print("Revision limpia.\n")

    if args.revisar:
        return 0
    return construir()


if __name__ == "__main__":
    sys.exit(main())
