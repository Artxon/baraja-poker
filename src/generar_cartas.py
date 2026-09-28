"""
Genera cada carta de la baraja como imagen lista para imprimir.
 
Lee las fotos de assets/fotos/ con nombres tipo A_picas.jpg, 10_corazones.png,
K_treboles.jpg, joker_1.jpg... y compone cada carta con la foto en el centro
y el valor y el palo en las esquinas. Guarda el resultado en output/cartas/.
 
Uso (desde la raíz del repo):
    python src/generar_cartas.py            # genera las 54 cartas
    python src/generar_cartas.py --parcial  # genera solo las que tengan foto
    python src/generar_cartas.py --guias    # además, previews con líneas de corte
"""
 
import argparse
import sys
import unicodedata
from pathlib import Path
 
from PIL import Image, ImageDraw, ImageFont, ImageOps
 
# ---------------------------------------------------------------- rutas
RAIZ = Path(__file__).resolve().parents[1]
DIR_FOTOS = RAIZ / "assets" / "fotos"
DIR_FUENTES = RAIZ / "assets" / "fuentes"
DIR_CARTAS = RAIZ / "output" / "cartas"
DIR_PREVIEW = RAIZ / "output" / "preview"
FUENTE_SISTEMA = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
 
# ---------------------------------------------------------------- medidas (mm)
DPI = 300
ANCHO, ALTO = 63, 88          # tamaño final de la carta (póker)
SANGRADO = 3                  # por cada lado
FOTO_ANCHO, FOTO_ALTO = 42, 62  # hueco central para la foto
FOTO_RADIO = 2                # esquinas redondeadas de la foto
INDICE_CENTRO_X = 7.0         # centro horizontal de la columna del índice
INDICE_ARRIBA = 4.5           # distancia del valor al borde superior
INDICE_MAX_ANCHO = 6.5        # "10" se encoge para no pasar de aquí
VALOR_TAM = 7.5               # tamaño de fuente del valor
PALO_TAM = 6.5                # tamaño de fuente del símbolo del palo
 
# ---------------------------------------------------------------- baraja
VALORES = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
ROJO, NEGRO = (196, 18, 48), (20, 20, 20)
PALOS = {  # nombre de archivo -> (símbolo, color)
    "picas": ("♠", NEGRO),
    "corazones": ("♥", ROJO),
    "diamantes": ("♦", ROJO),
    "treboles": ("♣", NEGRO),
}
COMODINES = {"joker_1": NEGRO, "joker_2": ROJO}
 
# Las 16 Esquirlas de Adonalsium, una por figura (A, J, Q, K de cada palo).
# (nombre bajo la foto, símbolo a los lados del nombre). Los símbolos están en DejaVu Sans.
ESQUIRLAS = {
    # Reyes
    "K_picas": ("ODIUM", "⚡"),
    "K_corazones": ("HONOR", "⚖"),
    "K_diamantes": ("DOMINION", "♜"),
    "K_treboles": ("AUTONOMY", "☉"),
    # Reinas
    "Q_picas": ("PRESERVATION", "☁"),
    "Q_corazones": ("DEVOTION", "♡"),
    "Q_diamantes": ("ENDOWMENT", "✾"),
    "Q_treboles": ("CULTIVATION", "☘"),
    # Jotas
    "J_picas": ("AMBITION", "⚑"),
    "J_corazones": ("VALOR", "⚔"),
    "J_diamantes": ("INVENTION", "⚙"),
    "J_treboles": ("WHIMSY", "♫"),
    # Ases
    "A_picas": ("RUIN", "☠"),
    "A_corazones": ("MERCY", "☮"),
    "A_diamantes": ("VIRTUOSITY", "✎"),
    "A_treboles": ("REASON", "∴"),
}
# Cada comodín con su nombre y símbolo
COMODIN_TEXTOS = {
    "joker_1": ("HARMONY", "✦"),
    "joker_2": ("RETRIBUTION", "✦"),
}
# Símbolo grande en dorado sobre la foto, según el valor
SIMBOLO_ARRIBA = {
    "J": "⚔",  # espadas cruzadas
    "Q": "♛",  # corona de reina
    "K": "♚",  # corona de rey
    "A": "✺",  # estrella de 16 puntas: Adonalsium
}
DORADO = (176, 136, 52)
ICONO_FRANJA_TAM = 7.5   # mm, tamaño del símbolo sobre la foto
MARCO_FIGURAS = 0.6      # mm, grosor del marco dorado en figuras y comodines
ETIQUETA_TAM = 4.2        # mm, tamaño de fuente del nombre
ETIQUETA_MAX_ANCHO = 38   # mm, icono + nombre + icono no pasan de aquí (los índices ocupan las esquinas)
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}
 
 
def px(mm: float) -> int:
    return round(mm / 25.4 * DPI)
 
 
def cartas_esperadas() -> list[str]:
    """Las 54 claves en orden: picas A-K, corazones, diamantes, tréboles, comodines."""
    return [f"{v}_{p}" for p in PALOS for v in VALORES] + list(COMODINES)
 
 
def normalizar(nombre: str) -> str:
    """'a_Tréboles' -> 'A_treboles', 'Joker_1' -> 'joker_1'."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn"
    )
    partes = sin_tildes.strip().split("_")
    if len(partes) != 2:
        return sin_tildes
    valor, palo = partes
    if valor.lower() == "joker":
        return f"joker_{palo}"
    return f"{valor.upper()}_{palo.lower()}"
 
 
def buscar_fotos() -> tuple[dict[str, Path], list[str]]:
    """Devuelve {clave: ruta} y una lista de avisos."""
    esperadas = set(cartas_esperadas())
    encontradas: dict[str, Path] = {}
    avisos = []
    for ruta in sorted(DIR_FOTOS.iterdir()):
        if ruta.name.startswith("."):
            continue
        if ruta.suffix.lower() in {".heic", ".heif"}:
            avisos.append(f"{ruta.name}: formato HEIC no soportado, conviértela a JPG")
            continue
        if ruta.suffix.lower() not in EXTENSIONES:
            continue
        clave = normalizar(ruta.stem)
        if clave not in esperadas:
            avisos.append(f"Nombre no reconocido, se ignora: {ruta.name}")
        elif clave in encontradas:
            avisos.append(f"Foto duplicada para {clave}: {encontradas[clave].name} y {ruta.name}")
        else:
            encontradas[clave] = ruta
    return encontradas, avisos
 
 
def cargar_fuente() -> Path:
    locales = sorted(DIR_FUENTES.glob("*.ttf")) + sorted(DIR_FUENTES.glob("*.otf"))
    if locales:
        return locales[0]
    if FUENTE_SISTEMA.exists():
        return FUENTE_SISTEMA
    sys.exit(
        "No encuentro ninguna fuente. Copia DejaVuSans-Bold.ttf (o otra .ttf con los "
        "símbolos ♠♥♦♣) en assets/fuentes/."
    )
 
 
def fuente_valores(ruta_por_defecto: Path) -> Path:
    """Fuente decorativa para números y letras si hay una en assets/fuentes/valores/."""
    carpeta = DIR_FUENTES / "valores"
    if carpeta.exists():
        opciones = sorted(carpeta.glob("*.ttf")) + sorted(carpeta.glob("*.otf"))
        if opciones:
            return opciones[0]
    return ruta_por_defecto
 
 
def fuente(ruta: Path, tam_mm: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ruta), px(tam_mm))
 
 
def texto_centrado(draw, cx, arriba, texto, font, color):
    """Dibuja texto centrado en cx con su borde superior visible en 'arriba'. Devuelve el borde inferior."""
    x0, y0, x1, y1 = draw.textbbox((0, 0), texto, font=font)
    draw.text((cx - (x0 + x1) / 2, arriba - y0), texto, font=font, fill=color)
    return arriba + (y1 - y0)
 
 
def dibujar_indice(capa: Image.Image, clave: str, ruta_fuente: Path):
    """Dibuja el índice de la esquina superior izquierda en una capa transparente."""
    draw = ImageDraw.Draw(capa)
    cx = px(SANGRADO + INDICE_CENTRO_X)
    arriba = px(SANGRADO + INDICE_ARRIBA)
    ruta_valores = fuente_valores(ruta_fuente)
 
    if clave in COMODINES:
        color = COMODINES[clave]
        f = fuente(ruta_valores, 3.4)
        for letra in "JOKER":
            arriba = texto_centrado(draw, cx, arriba, letra, f, color) + px(0.6)
        texto_centrado(draw, cx, arriba + px(0.4), COMODIN_TEXTOS[clave][1], fuente(ruta_fuente, 4.5), color)
        return
 
    valor, palo = clave.split("_")
    simbolo, color = PALOS[palo]
 
    tam = VALOR_TAM
    f_valor = fuente(ruta_valores, tam)
    def ancho(texto, f):
        x0, _, x1, _ = draw.textbbox((0, 0), texto, font=f)
        return x1 - x0
 
    while ancho(valor, f_valor) > px(INDICE_MAX_ANCHO) and tam > 3:
        tam -= 0.25
        f_valor = fuente(ruta_valores, tam)
 
    abajo = texto_centrado(draw, cx, arriba, valor, f_valor, color)
    texto_centrado(draw, cx, abajo + px(1.0), simbolo, fuente(ruta_fuente, PALO_TAM), color)
 
 
def dibujar_simbolo_arriba(draw, simbolo: str, ruta_fuente: Path):
    """Símbolo dorado centrado en la franja blanca sobre la foto (solo arriba)."""
    franja = (ALTO - FOTO_ALTO) / 2
    f = fuente(ruta_fuente, min(ICONO_FRANJA_TAM, franja * 0.75))
    x0, y0, x1, y1 = draw.textbbox((0, 0), simbolo, font=f)
    cx = px(SANGRADO + ANCHO / 2)
    cy = px(SANGRADO + franja / 2)
    draw.text((cx - (x0 + x1) / 2, cy - (y0 + y1) / 2), simbolo, font=f, fill=DORADO)
 
 
def tiene_glifo(f: ImageFont.FreeTypeFont, caracter: str) -> bool:
    """False si la fuente dibuja el cuadradito de 'carácter no disponible'."""
    def huella(c):
        img = Image.new("L", (f.size * 2, f.size * 2), 0)
        ImageDraw.Draw(img).text((0, 0), c, font=f, fill=255)
        return img.tobytes()
    return huella(caracter) != huella("\ue000")
 
 
def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
 
 
def dibujar_franja(draw, icono: str, etiqueta: str | None, ruta_fuente: Path, ruta_valores: Path):
    """Franja blanca bajo la foto: '✺ BATEKOA ✺' en dorado. Solo abajo, sin copia invertida."""
    franja = (ALTO - FOTO_ALTO) / 2
    cx = px(SANGRADO + ANCHO / 2)
    cy = px(SANGRADO + ALTO - franja / 2)
 
    def poner(texto, f, x_centro):
        x0, y0, x1, y1 = draw.textbbox((0, 0), texto, font=f)
        draw.text((x_centro - (x0 + x1) / 2, cy - (y0 + y1) / 2), texto, font=f, fill=DORADO)
 
    def ancho(texto, f):
        x0, _, x1, _ = draw.textbbox((0, 0), texto, font=f)
        return x1 - x0
 
    if not etiqueta:  # solo el icono, grande
        poner(icono, fuente(ruta_fuente, min(ICONO_FRANJA_TAM, franja * 0.75)), cx)
        return
 
    prueba = fuente(ruta_valores, ETIQUETA_TAM)
    if not all(tiene_glifo(prueba, c) for c in etiqueta if c != " "):
        etiqueta = sin_tildes(etiqueta)  # la fuente decorativa no tiene tildes
 
    tam = min(ETIQUETA_TAM, franja * 0.45)
    while True:
        f_txt = fuente(ruta_valores, tam)
        f_ico = fuente(ruta_fuente, tam * 1.1)
        hueco = px(tam * 0.45)
        w_txt, w_ico = ancho(etiqueta, f_txt), ancho(icono, f_ico)
        total = w_txt + 2 * (w_ico + hueco)
        if total <= px(ETIQUETA_MAX_ANCHO) or tam <= 2:
            break
        tam -= 0.2
 
    poner(etiqueta, f_txt, cx)
    desplazamiento = w_txt / 2 + hueco + w_ico / 2
    poner(icono, f_ico, cx - desplazamiento)
    poner(icono, f_ico, cx + desplazamiento)
 
 
def preparar_foto(ruta: Path) -> tuple[Image.Image, str | None]:
    img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    ancho, alto = px(FOTO_ANCHO), px(FOTO_ALTO)
    aviso = None
    # Resolución disponible tras recortar a la proporción del hueco
    escala = min(img.width / ancho, img.height / alto)
    if escala < 1:
        aviso = (
            f"{ruta.name}: resolución baja ({img.width}x{img.height}); "
            f"se verá a ~{round(DPI * escala)} ppp (ideal 300)"
        )
    foto = ImageOps.fit(img, (ancho, alto), method=Image.LANCZOS, centering=(0.5, 0.5))
 
    mascara = Image.new("L", foto.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, ancho - 1, alto - 1), radius=px(FOTO_RADIO), fill=255
    )
    foto.putalpha(mascara)
    return foto, aviso
 
 
def componer_carta(clave: str, ruta_foto: Path, ruta_fuente: Path) -> tuple[Image.Image, str | None]:
    lienzo_w, lienzo_h = px(ANCHO + 2 * SANGRADO), px(ALTO + 2 * SANGRADO)
    carta = Image.new("RGBA", (lienzo_w, lienzo_h), "white")
 
    foto, aviso = preparar_foto(ruta_foto)
    fx = (lienzo_w - foto.width) // 2
    fy = (lienzo_h - foto.height) // 2
    carta.alpha_composite(foto, (fx, fy))
    especial = clave in COMODINES or clave in ESQUIRLAS
    ImageDraw.Draw(carta).rounded_rectangle(
        (fx, fy, fx + foto.width - 1, fy + foto.height - 1),
        radius=px(FOTO_RADIO),
        outline=DORADO if especial else (60, 60, 60),
        width=px(MARCO_FIGURAS) if especial else max(1, px(0.25)),
    )
 
    # Índice arriba a la izquierda y, girado 180°, abajo a la derecha
    capa = Image.new("RGBA", carta.size, (0, 0, 0, 0))
    dibujar_indice(capa, clave, ruta_fuente)
    carta.alpha_composite(capa)
    carta.alpha_composite(capa.rotate(180))
 
    # Nombre bajo la foto, solo una vez (se dibuja después de girar)
    draw = ImageDraw.Draw(carta)
    datos = COMODIN_TEXTOS.get(clave) if clave in COMODINES else ESQUIRLAS.get(clave)
    if datos:
        nombre, icono = datos
        dibujar_franja(draw, icono, nombre, ruta_fuente, fuente_valores(ruta_fuente))
    valor = clave.split("_")[0]
    if clave not in COMODINES and valor in SIMBOLO_ARRIBA:
        dibujar_simbolo_arriba(draw, SIMBOLO_ARRIBA[valor], ruta_fuente)
    return carta.convert("RGB"), aviso
 
 
def con_guias(carta: Image.Image) -> Image.Image:
    """Copia de la carta con la línea de corte (rojo) y el margen de seguridad (azul)."""
    prev = carta.copy()
    d = ImageDraw.Draw(prev)
    s, w, h = px(SANGRADO), px(ANCHO), px(ALTO)
    d.rectangle((s, s, s + w, s + h), outline=(255, 0, 0), width=2)
    m = px(3)
    d.rectangle((s + m, s + m, s + w - m, s + h - m), outline=(0, 120, 255), width=2)
    return prev
 
 
def main():
    parser = argparse.ArgumentParser(description="Genera las cartas de la baraja.")
    parser.add_argument("--parcial", action="store_true", help="generar aunque falten fotos")
    parser.add_argument("--guias", action="store_true", help="guardar previews con líneas de corte")
    args = parser.parse_args()
 
    if not DIR_FOTOS.exists():
        sys.exit(f"No existe la carpeta {DIR_FOTOS}")
 
    fotos, avisos = buscar_fotos()
    faltan = [c for c in cartas_esperadas() if c not in fotos]
 
    for a in avisos:
        print(f"⚠️  {a}")
    print(f"Fotos encontradas: {len(fotos)}/54")
    if faltan:
        print("Faltan:", ", ".join(faltan))
        if not args.parcial:
            sys.exit("Añade las fotos que faltan o ejecuta con --parcial para probar.")
 
    ruta_fuente = cargar_fuente()
    print(f"Fuente de palos: {ruta_fuente.name}")
    print(f"Fuente de valores: {fuente_valores(ruta_fuente).name}")
 
    DIR_CARTAS.mkdir(parents=True, exist_ok=True)
    for viejo in DIR_CARTAS.glob("*.jpg"):
        viejo.unlink()
    if args.guias:
        DIR_PREVIEW.mkdir(parents=True, exist_ok=True)
 
    for i, clave in enumerate(cartas_esperadas(), start=1):
        if clave not in fotos:
            continue
        carta, aviso = componer_carta(clave, fotos[clave], ruta_fuente)
        if aviso:
            print(f"⚠️  {aviso}")
        nombre = f"{i:02d}_{clave}.jpg"
        carta.save(DIR_CARTAS / nombre, quality=95, subsampling=0, dpi=(DPI, DPI))
        if args.guias:
            con_guias(carta).save(DIR_PREVIEW / nombre, quality=90)
 
    print(f"✅ Cartas guardadas en {DIR_CARTAS.relative_to(RAIZ)}")
 
 
if __name__ == "__main__":
    main()