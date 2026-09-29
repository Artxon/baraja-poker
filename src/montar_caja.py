"""
Genera la plantilla recortable de la caja (tuck box) para la baraja.
 
Lee:
    assets/caja/delante.(jpg|png|webp)  -> imagen de la cara delantera
    assets/caja/detras.(jpg|png|webp)   -> imagen de la cara trasera
    (si falta alguna, usa la imagen de assets/reverso/)
 
Genera en output/pdf/:
    caja.pdf            -> con líneas de corte (continua) y pliegue (discontinua)
    caja_sin_guias.pdf  -> solo el diseño, por si prefieres imprimir sin líneas
 
Uso (desde la raíz del repo):
    python src/montar_caja.py
 
Esquema (vista del lado impreso):
 
                    [dust]        [dust]   [ tapa + lengüeta ]
          [lateral][ DELANTE ][lateral][    DETRÁS     ][pestaña]
                    [ base + lengüeta ]  [dust]
"""
 
import math
import sys
from pathlib import Path
 
from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
 
RAIZ = Path(__file__).resolve().parents[1]
DIR_CAJA = RAIZ / "assets" / "caja"
DIR_REVERSO = RAIZ / "assets" / "reverso"
DIR_FUENTES = RAIZ / "assets" / "fuentes"
DIR_PDF = RAIZ / "output" / "pdf"
FUENTE_SISTEMA = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp")
 
# ---------------------------------------------------------------- medidas (mm)
ANCHO_CARTA, ALTO_CARTA = 63, 88
GROSOR_BARAJA = 25   # medido: 24-25 mm con las 54 cartas impresas en 350 g/m²
HOLGURA = 1.5        # margen para que las cartas entren y salgan sin forzar
 
W = ANCHO_CARTA + HOLGURA   # ancho de delante / detrás
H = ALTO_CARTA + HOLGURA    # alto de la caja
G = GROSOR_BARAJA + 1       # fondo de la caja (ancho de los laterales)
LENGUETA = 15               # lengüetas que se meten dentro al cerrar
LENGUETA_RADIO = 6          # esquinas redondeadas de las lengüetas
LENGUETA_MARGEN = 1.5       # la lengüeta es un poco más estrecha para que entre
SOLAPA_ALTO = min(G * 0.9, W / 2 - 2)  # solapas pequeñas de los laterales
SOLAPA_BISEL = 3
PESTANA = 10                # pestaña de pegado
PESTANA_BISEL = 4
MUESCA_RADIO = 9            # media luna para sacar las cartas con el pulgar
SANGRADO = 3
 
# ---------------------------------------------------------------- diseño
FONDO = (16, 20, 34)            # color de laterales y solapas
DORADO = (176, 136, 52)
SIMBOLO_TAPA = "✺"               # símbolo en la tapa
ADORNO = "✦"                     # adorno de esquinas, laterales y base
 
 
# ================================================================ utilidades
def rgb(c, color):
    c.setFillColorRGB(*(v / 255 for v in color))
 
 
def rgb_linea(c, color):
    c.setStrokeColorRGB(*(v / 255 for v in color))
 
 
def arco(cx, cy, r, a0, a1, pasos=16):
    """Puntos de un arco (grados), para construir el contorno como polígono."""
    return [
        (cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / pasos)),
         cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / pasos)))
        for i in range(pasos + 1)
    ]
 
 
def registrar_fuentes() -> tuple[str, str]:
    """Devuelve (fuente de símbolos, fuente de títulos)."""
    simbolos = sorted(DIR_FUENTES.glob("*.ttf")) or ([FUENTE_SISTEMA] if FUENTE_SISTEMA.exists() else [])
    if not simbolos:
        sys.exit("No encuentro DejaVuSans-Bold.ttf en assets/fuentes/.")
    pdfmetrics.registerFont(TTFont("Simbolos", str(simbolos[0])))
    carpeta = DIR_FUENTES / "valores"
    titulos = sorted(carpeta.glob("*.ttf")) + sorted(carpeta.glob("*.otf")) if carpeta.exists() else []
    if titulos:
        pdfmetrics.registerFont(TTFont("Titulos", str(titulos[0])))
        return "Simbolos", "Titulos"
    return "Simbolos", "Simbolos"
 
 
def buscar_imagen(nombre: str) -> Path | None:
    for ext in EXTENSIONES:
        ruta = DIR_CAJA / f"{nombre}{ext}"
        if ruta.exists():
            return ruta
    return None
 
 
def cargar_imagen(nombre: str, ancho_mm: float, alto_mm: float) -> ImageReader:
    ruta = buscar_imagen(nombre)
    if ruta is None:
        reversos = [p for p in sorted(DIR_REVERSO.glob("*")) if p.suffix.lower() in EXTENSIONES]
        if not reversos:
            sys.exit(f"Falta assets/caja/{nombre}.jpg y no hay reverso para usar en su lugar.")
        ruta = reversos[0]
        print(f"⚠️  No hay assets/caja/{nombre}.*; uso {ruta.name}")
    else:
        print(f"Imagen {nombre}: {ruta.name}")
    img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    objetivo = (round(ancho_mm / 25.4 * 300), round(alto_mm / 25.4 * 300))
    if img.width < objetivo[0] * 0.7:
        print(f"⚠️  {ruta.name} tiene poca resolución ({img.width}x{img.height}); ideal {objetivo[0]}x{objetivo[1]}")
    return ImageReader(ImageOps.fit(img, objetivo, method=Image.LANCZOS))
 
 
# ================================================================ geometría
class Caja:
    def __init__(self, ancho_pagina, alto_pagina):
        total_w = 2 * G + 2 * W + PESTANA
        total_h = 2 * (G + LENGUETA) + H
        if total_w > ancho_pagina - 10 or total_h > alto_pagina - 30:
            sys.exit(f"La caja ({total_w:.0f}x{total_h:.0f} mm) no cabe en A4. Revisa las medidas.")
        self.x0 = (ancho_pagina - total_w) / 2
        self.yb = (alto_pagina - total_h) / 2 + G + LENGUETA + 8  # algo de sitio abajo para la leyenda
        self.yt = self.yb + H
        self.xs1 = self.x0 + G          # empieza DELANTE
        self.xf2 = self.xs1 + W         # termina DELANTE
        self.xs2 = self.xf2 + G         # empieza DETRÁS
        self.xb2 = self.xs2 + W         # termina DETRÁS
        self.xg = self.xb2 + PESTANA
 
    def contorno(self) -> list[tuple[float, float]]:
        x0, xs1, xf2, xs2, xb2, xg = self.x0, self.xs1, self.xf2, self.xs2, self.xb2, self.xg
        yb, yt = self.yb, self.yt
        m, r, dh, db = LENGUETA_MARGEN, LENGUETA_RADIO, SOLAPA_ALTO, SOLAPA_BISEL
        p = [(x0, yb)]
        # --- parte inferior, de izquierda a derecha
        p += [(x0 + db, yb - dh), (xs1 - db, yb - dh), (xs1, yb)]                 # solapa lateral 1
        yl = yb - G                                                                # base
        p += [(xs1, yl), (xs1 + m, yl)]
        p += arco(xs1 + m + r, yl - LENGUETA + r, r, 180, 270)                     # lengüeta base
        p += arco(xf2 - m - r, yl - LENGUETA + r, r, 270, 360)
        p += [(xf2 - m, yl), (xf2, yl), (xf2, yb)]
        p += [(xf2 + db, yb - dh), (xs2 - db, yb - dh), (xs2, yb)]                 # solapa lateral 2
        p += [(xb2, yb)]                                                           # detrás (recto)
        p += [(xg, yb + PESTANA_BISEL), (xg, yt - PESTANA_BISEL), (xb2, yt)]       # pestaña de pegado
        # --- parte superior, de derecha a izquierda
        ya = yt + G                                                                # tapa
        p += [(xb2, ya), (xb2 - m, ya)]
        p += arco(xb2 - m - r, ya + LENGUETA - r, r, 0, 90)                        # lengüeta tapa
        p += arco(xs2 + m + r, ya + LENGUETA - r, r, 90, 180)
        p += [(xs2 + m, ya), (xs2, ya), (xs2, yt)]
        p += [(xs2 - db, yt + dh), (xf2 + db, yt + dh), (xf2, yt)]                 # solapa lateral 2
        cx = (xs1 + xf2) / 2                                                       # delante con muesca
        p += arco(cx, yt, MUESCA_RADIO, 0, -180, 24)
        p += [(xs1, yt)]
        p += [(xs1 - db, yt + dh), (x0 + db, yt + dh), (x0, yt)]                   # solapa lateral 1
        return p
 
    def pliegues(self) -> list[tuple[float, float, float, float]]:
        x0, xs1, xf2, xs2, xb2 = self.x0, self.xs1, self.xf2, self.xs2, self.xb2
        yb, yt, m = self.yb, self.yt, LENGUETA_MARGEN
        return [
            (xs1, yb, xs1, yt), (xf2, yb, xf2, yt), (xs2, yb, xs2, yt), (xb2, yb, xb2, yt),
            (x0, yb, xs1, yb), (x0, yt, xs1, yt), (xf2, yb, xs2, yb), (xf2, yt, xs2, yt),
            (xs1, yb, xf2, yb), (xs1 + m, yb - G, xf2 - m, yb - G),      # base y su lengüeta
            (xs2, yt, xb2, yt), (xs2 + m, yt + G, xb2 - m, yt + G),      # tapa y su lengüeta
        ]
 
 
def trazar(c, puntos):
    path = c.beginPath()
    path.moveTo(puntos[0][0] * mm, puntos[0][1] * mm)
    for x, y in puntos[1:]:
        path.lineTo(x * mm, y * mm)
    path.close()
    return path
 
 
# ================================================================ decoración
def marco(c, x, y, w, h, margen=3.0):
    """Doble marco dorado con adornos en las esquinas."""
    rgb_linea(c, DORADO)
    c.setLineWidth(0.9)
    c.rect((x + margen) * mm, (y + margen) * mm, (w - 2 * margen) * mm, (h - 2 * margen) * mm)
    c.setLineWidth(0.35)
    m2 = margen + 1.3
    c.rect((x + m2) * mm, (y + m2) * mm, (w - 2 * m2) * mm, (h - 2 * m2) * mm)
    rgb(c, DORADO)
    c.setFont("Simbolos", 9)
    for ax, ay in ((x + margen, y + margen), (x + w - margen, y + margen),
                   (x + margen, y + h - margen), (x + w - margen, y + h - margen)):
        c.drawCentredString(ax * mm, ay * mm - 3.1, ADORNO)
 
 
def texto_ajustado(c, texto, fuente, max_ancho_mm, max_tam_mm):
    tam = max_tam_mm * mm
    while pdfmetrics.stringWidth(texto, fuente, tam) > max_ancho_mm * mm and tam > 4:
        tam -= 0.5
    return tam
 
 
def lateral(c, x, y):
    """Lateral: fondo, filetes dorados y tres adornos en vertical."""
    rgb_linea(c, DORADO)
    c.setLineWidth(0.5)
    c.line((x + 2) * mm, (y + 4) * mm, (x + 2) * mm, (y + H - 4) * mm)
    c.line((x + G - 2) * mm, (y + 4) * mm, (x + G - 2) * mm, (y + H - 4) * mm)
    rgb(c, DORADO)
    cx = (x + G / 2) * mm
    for fraccion, tam_mm in ((0.2, G * 0.3), (0.5, G * 0.5), (0.8, G * 0.3)):
        tam = tam_mm * mm
        c.setFont("Simbolos", tam)
        c.drawCentredString(cx, (y + H * fraccion) * mm - tam * 0.35, ADORNO)
 
 
def dibujar(c, caja: Caja, frente: ImageReader, trasera: ImageReader, fuentes, guias: bool):
    contorno = caja.contorno()
 
    # Fondo del troquel con sangrado alrededor (relleno + trazo grueso del mismo color)
    rgb(c, FONDO)
    rgb_linea(c, FONDO)
    c.setLineWidth(2 * SANGRADO * mm)
    c.setLineJoin(1)
    c.drawPath(trazar(c, contorno), stroke=1, fill=1)
 
    c.saveState()
    c.clipPath(trazar(c, contorno), stroke=0, fill=0)
 
    # Caras con imagen
    c.drawImage(frente, caja.xs1 * mm, caja.yb * mm, W * mm, H * mm)
    c.drawImage(trasera, caja.xs2 * mm, caja.yb * mm, W * mm, H * mm)
    marco(c, caja.xs1, caja.yb, W, H)
    marco(c, caja.xs2, caja.yb, W, H)
 
    # Laterales
    lateral(c, caja.x0, caja.yb)
    lateral(c, caja.xf2, caja.yb)
 
    # Tapa: símbolo grande
    rgb(c, DORADO)
    tam = min(G * 0.7, 14) * mm
    c.setFont("Simbolos", tam)
    c.drawCentredString((caja.xs2 + W / 2) * mm, (caja.yt + G / 2) * mm - tam * 0.35, SIMBOLO_TAPA)
    rgb_linea(c, DORADO)
    c.setLineWidth(0.5)
    c.rect((caja.xs2 + 2) * mm, (caja.yt + 2) * mm, (W - 4) * mm, (G - 4) * mm)
 
    # Base: adorno
    tam = min(G * 0.45, 9) * mm
    c.setFont("Simbolos", tam)
    c.drawCentredString((caja.xs1 + W / 2) * mm, (caja.yb - G / 2) * mm - tam * 0.35, ADORNO)
    c.rect((caja.xs1 + 2) * mm, (caja.yb - G + 2) * mm, (W - 4) * mm, (G - 4) * mm)
 
    # Pestaña de pegado sin tinta (el pegamento agarra mejor)
    c.setFillColorRGB(1, 1, 1)
    c.rect(caja.xb2 * mm, (caja.yb - 1) * mm, (PESTANA + 1) * mm, (H + 2) * mm, stroke=0, fill=1)
 
    c.restoreState()
 
    if guias:
        # Corte: línea continua; pliegue: discontinua
        c.setStrokeGray(0.55)
        c.setLineWidth(0.4)
        c.setDash()
        c.drawPath(trazar(c, contorno), stroke=1, fill=0)
        c.setDash(3, 2)
        for x1, y1, x2, y2 in caja.pliegues():
            c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)
        c.setDash()
 
    c.showPage()
 
 
def main():
    fuentes = registrar_fuentes()
    ancho_pag, alto_pag = A4[0] / mm, A4[1] / mm
    caja = Caja(ancho_pag, alto_pag)
    frente = cargar_imagen("delante", W, H)
    trasera = cargar_imagen("detras", W, H)
 
    DIR_PDF.mkdir(parents=True, exist_ok=True)
    for nombre, guias in (("caja.pdf", True), ("caja_sin_guias.pdf", False)):
        c = canvas.Canvas(str(DIR_PDF / nombre), pagesize=A4)
        c.setTitle(nombre.removesuffix(".pdf"))
        dibujar(c, caja, frente, trasera, fuentes, guias)
        c.save()
 
    print(f"Caja interior: {W:.1f} × {H:.1f} × {G:.1f} mm")
    print(f"✅ PDFs guardados en {DIR_PDF.relative_to(RAIZ)}: caja.pdf y caja_sin_guias.pdf")
 
 
if __name__ == "__main__":
    main()