"""
Monta las cartas de output/cartas/ en hojas A4 (3x3) listas para la imprenta.
 
Genera en output/pdf/:
    baraja_doble_cara.pdf  -> anverso, reverso, anverso, reverso... (para imprimir a doble cara)
    prueba_doble_cara.pdf  -> solo la primera hoja por las dos caras (para la hoja de prueba)
    anversos.pdf           -> solo anversos (plan B: imprimir por separado y pegar)
    reversos.pdf           -> solo reversos
 
Uso (desde la raíz del repo):
    python src/montar_pdf.py
"""
 
import sys
from pathlib import Path
 
from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
 
RAIZ = Path(__file__).resolve().parents[1]
DIR_CARTAS = RAIZ / "output" / "cartas"
DIR_REVERSO = RAIZ / "assets" / "reverso"
DIR_PDF = RAIZ / "output" / "pdf"
 
ANCHO, ALTO, SANGRADO = 63, 88, 3  # mm, igual que en generar_cartas.py
COLUMNAS, FILAS = 3, 3
POR_HOJA = COLUMNAS * FILAS
DPI = 300
 
MARCA_LARGO = 2.5   # mm de cada marca de corte
MARCA_SEPARACION = 0.5  # mm entre la esquina de la carta y el inicio de la marca
 
CELDA_W = ANCHO + 2 * SANGRADO
CELDA_H = ALTO + 2 * SANGRADO
PAGINA_W, PAGINA_H = A4[0] / mm, A4[1] / mm
# Cuadrícula centrada: imprescindible para que el reverso coincida al voltear la hoja
ORIGEN_X = (PAGINA_W - COLUMNAS * CELDA_W) / 2
ORIGEN_Y = (PAGINA_H - FILAS * CELDA_H) / 2
 
 
def posicion(indice: int, espejo: bool = False) -> tuple[float, float]:
    """Esquina inferior izquierda (mm) de la celda. Fila 0 = arriba."""
    fila, col = divmod(indice, COLUMNAS)
    if espejo:  # al voltear por el lado largo, las columnas se invierten
        col = COLUMNAS - 1 - col
    x = ORIGEN_X + col * CELDA_W
    y = PAGINA_H - ORIGEN_Y - (fila + 1) * CELDA_H
    return x, y
 
 
def cargar_reverso() -> ImageReader:
    candidatos = [p for p in sorted(DIR_REVERSO.iterdir())
                  if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    if not candidatos:
        sys.exit(f"No hay imagen de reverso en {DIR_REVERSO.relative_to(RAIZ)}")
    ruta = candidatos[0]
    img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    objetivo = (round(CELDA_W / 25.4 * DPI), round(CELDA_H / 25.4 * DPI))
    prop_img, prop_obj = img.width / img.height, objetivo[0] / objetivo[1]
    if abs(prop_img - prop_obj) > 0.02:
        print(f"⚠️  El reverso {ruta.name} no tiene la proporción de la carta; se recortará al centro.")
    if img.width < objetivo[0] * 0.8:
        print(f"⚠️  El reverso tiene poca resolución ({img.width}x{img.height}); ideal {objetivo[0]}x{objetivo[1]}.")
    print(f"Reverso: {ruta.name}")
    return ImageReader(ImageOps.fit(img, objetivo, method=Image.LANCZOS))
 
 
def marcas_de_corte(c: canvas.Canvas, x: float, y: float):
    """Marcas en las 4 esquinas de la línea de corte, hacia fuera (caen en la zona que se tira)."""
    izq, der = x + SANGRADO, x + SANGRADO + ANCHO
    abajo, arriba = y + SANGRADO, y + SANGRADO + ALTO
    s, l = MARCA_SEPARACION, MARCA_SEPARACION + MARCA_LARGO
    for cx, dx in ((izq, -1), (der, 1)):
        for cy, dy in ((abajo, -1), (arriba, 1)):
            c.line((cx + dx * s) * mm, cy * mm, (cx + dx * l) * mm, cy * mm)  # horizontal
            c.line(cx * mm, (cy + dy * s) * mm, cx * mm, (cy + dy * l) * mm)  # vertical
 
 
def pagina_anversos(c: canvas.Canvas, cartas: list[Path]):
    for i, ruta in enumerate(cartas):
        x, y = posicion(i)
        c.drawImage(str(ruta), x * mm, y * mm, CELDA_W * mm, CELDA_H * mm)
    c.setLineWidth(0.3)
    c.setStrokeColorRGB(0, 0, 0)
    for i in range(len(cartas)):
        marcas_de_corte(c, *posicion(i))
    c.showPage()
 
 
def pagina_reversos(c: canvas.Canvas, reverso: ImageReader, cantidad: int):
    for i in range(cantidad):
        x, y = posicion(i, espejo=True)
        c.drawImage(reverso, x * mm, y * mm, CELDA_W * mm, CELDA_H * mm)
    c.showPage()
 
 
def nuevo_pdf(nombre: str) -> canvas.Canvas:
    c = canvas.Canvas(str(DIR_PDF / nombre), pagesize=A4)
    c.setTitle(nombre.removesuffix(".pdf"))
    return c
 
 
def main():
    cartas = sorted(DIR_CARTAS.glob("*.jpg"))
    if not cartas:
        sys.exit("No hay cartas en output/cartas/. Ejecuta antes: python src/generar_cartas.py")
    reverso = cargar_reverso()
    DIR_PDF.mkdir(parents=True, exist_ok=True)
 
    hojas = [cartas[i:i + POR_HOJA] for i in range(0, len(cartas), POR_HOJA)]
    print(f"{len(cartas)} cartas -> {len(hojas)} hojas A4")
    print(f"Margen de la cuadrícula: {ORIGEN_X:.1f} mm a los lados, {ORIGEN_Y:.1f} mm arriba y abajo")
 
    doble = nuevo_pdf("baraja_doble_cara.pdf")
    anv = nuevo_pdf("anversos.pdf")
    rev = nuevo_pdf("reversos.pdf")
    prueba = nuevo_pdf("prueba_doble_cara.pdf")
 
    for n, hoja in enumerate(hojas):
        pagina_anversos(doble, hoja)
        pagina_reversos(doble, reverso, len(hoja))
        pagina_anversos(anv, hoja)
        pagina_reversos(rev, reverso, len(hoja))
        if n == 0:
            pagina_anversos(prueba, hoja)
            pagina_reversos(prueba, reverso, len(hoja))
 
    for c in (doble, anv, rev, prueba):
        c.save()
    print(f"✅ PDFs guardados en {DIR_PDF.relative_to(RAIZ)}")
 
 
if __name__ == "__main__":
    main()