import math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BUNGEE = 'Bungee-Regular.ttf'
POPPINS = 'Poppins-ExtraBold.ttf'
AMARILLO = (255, 214, 10)
CIAN = (0, 229, 255)
ROSA = (255, 46, 160)
NEGRO = (15, 10, 30)
random.seed(7)


def degradado(w, h, c1, c2, c3):
    img = Image.new('RGB', (w, h))
    px = img.load()
    for y in range(h):
        for x in range(0, w):
            t = (x / w * 0.6 + y / h * 0.4)
            if t < 0.5:
                a, b, k = c1, c2, t / 0.5
            else:
                a, b, k = c2, c3, (t - 0.5) / 0.5
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
    return img


def rayos(img, cx, cy, n=28, color=(255, 255, 255), alpha=26):
    w, h = img.size
    capa = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    r = max(w, h) * 1.5
    for i in range(n):
        a1 = 2 * math.pi * i / n
        a2 = a1 + math.pi / n
        d.polygon([(cx, cy), (cx + r * math.cos(a1), cy + r * math.sin(a1)), (cx + r * math.cos(a2), cy + r * math.sin(a2))],
                  fill=color + (alpha,))
    img.paste(capa, (0, 0), capa)


def estrellas(d, w, h, n, zona=None):
    for _ in range(n):
        x, y = random.randint(0, w), random.randint(0, h)
        s = random.choice([3, 4, 6, 9])
        c = random.choice([(255, 255, 255), AMARILLO, CIAN])
        d.polygon([(x, y - s * 2), (x + s * 0.5, y - s * 0.5), (x + s * 2, y), (x + s * 0.5, y + s * 0.5),
                   (x, y + s * 2), (x - s * 0.5, y + s * 0.5), (x - s * 2, y), (x - s * 0.5, y - s * 0.5)], fill=c)


def texto_pop(img, xy, texto, fuente, relleno, borde=NEGRO, grosor=14, sombra=ROSA, desp=(12, 12), anchor='mm'):
    d = ImageDraw.Draw(img)
    x, y = xy
    d.text((x + desp[0], y + desp[1]), texto, font=fuente, fill=sombra, stroke_width=grosor, stroke_fill=sombra, anchor=anchor)
    d.text((x, y), texto, font=fuente, fill=relleno, stroke_width=grosor, stroke_fill=borde, anchor=anchor)


def atomo(img, cx, cy, r, grosor):
    capa = Image.new('RGBA', img.size, (0, 0, 0, 0))
    for ang in (0, 60, 120):
        e = Image.new('RGBA', (int(r * 2.4), int(r * 2.4)), (0, 0, 0, 0))
        de = ImageDraw.Draw(e)
        bw, bh = r * 2.2, r * 0.8
        x0, y0 = (e.width - bw) / 2, (e.height - bh) / 2
        de.ellipse([x0, y0, x0 + bw, y0 + bh], outline=NEGRO + (255,), width=grosor + 10)
        de.ellipse([x0, y0, x0 + bw, y0 + bh], outline=CIAN + (255,), width=grosor)
        de.ellipse([x0 + bw - grosor * 2.2, e.height / 2 - grosor * 1.4, x0 + bw + grosor * 0.6, e.height / 2 + grosor * 1.4],
                   fill=AMARILLO + (255,), outline=NEGRO + (255,), width=5)
        e = e.rotate(ang, resample=Image.BICUBIC)
        capa.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))
    img.paste(capa, (0, 0), capa)


def logo(tam=800, s=2):
    W = tam * s
    img = degradado(W, W, (88, 24, 214), (214, 34, 160), (255, 120, 30))
    rayos(img, W / 2, W / 2, n=24, alpha=34)
    d = ImageDraw.Draw(img)
    estrellas(d, W, W, 40)
    atomo(img, W / 2, W / 2, W * 0.36, 26)
    f = ImageFont.truetype(BUNGEE, int(W * 0.62))
    texto_pop(img, (W / 2, W / 2 + W * 0.04), '?', f, AMARILLO, grosor=28, desp=(26, 26))
    return img.resize((tam, tam), Image.LANCZOS)


def banner(s=1):
    W, H = 2560 * s, 1440 * s
    img = degradado(W, H, (70, 20, 200), (220, 30, 150), (255, 140, 20))
    rayos(img, W / 2, H / 2, n=40, alpha=22)
    d = ImageDraw.Draw(img, 'RGBA')
    # puntos tipo cómic
    for y in range(0, H, 34 * s):
        for x in range(0, W, 34 * s):
            if (x + y) % (68 * s) == 0:
                d.ellipse([x, y, x + 7 * s, y + 7 * s], fill=(255, 255, 255, 28))
    estrellas(d, W, H, 120)
    # planeta a la derecha (fuera de la zona segura en parte)
    px, py, pr = W * 0.80, H * 0.38, 260 * s
    caja = [px - pr * 1.75, py - pr * 0.42, px + pr * 1.75, py + pr * 0.42]
    d.arc(caja, 180, 360, fill=NEGRO, width=44 * s); d.arc(caja, 180, 360, fill=AMARILLO, width=24 * s)
    d.ellipse([px - pr - 14, py - pr - 14, px + pr + 14, py + pr + 14], fill=NEGRO)
    d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=CIAN)
    d.ellipse([px - pr * 0.6, py - pr * 0.7, px + pr * 0.1, py - pr * 0.1], fill=(140, 245, 255))
    d.pieslice([px - pr, py - pr, px + pr, py + pr], 20, 160, fill=(0, 190, 225))
    d.arc(caja, 0, 180, fill=NEGRO, width=44 * s); d.arc(caja, 0, 180, fill=AMARILLO, width=24 * s)
    # zona segura: x 507-2053, y 508-931
    icono = Image.open('ciencia_logo_800.png').convert('RGB').resize((380 * s, 380 * s), Image.LANCZOS)
    m = Image.new('L', icono.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, icono.width, icono.height], fill=255)
    d.ellipse([560 * s - 12, 530 * s - 12, 560 * s + icono.width + 12, 530 * s + icono.height + 12], fill=NEGRO)
    img.paste(icono, (560 * s, 530 * s), m)
    f1 = ImageFont.truetype(BUNGEE, 150 * s)
    texto_pop(img, (1430 * s, 640 * s), 'CIENCIA', f1, AMARILLO, grosor=16 * s, desp=(12 * s, 12 * s))
    f1b = ImageFont.truetype(BUNGEE, 120 * s)
    texto_pop(img, (1430 * s, 790 * s), 'Y PORQUÉS', f1b, (255, 255, 255), grosor=14 * s, sombra=(30, 120, 255), desp=(10 * s, 10 * s))
    f2 = ImageFont.truetype(POPPINS, 44 * s)
    texto_pop(img, (1430 * s, 892 * s), 'HISTORIA · CIENCIA · UNIVERSO · CÓMO FUNCIONA', f2, (255, 255, 255), grosor=8 * s,
              sombra=NEGRO, desp=(4 * s, 4 * s))
    # insignia
    ins = Image.new('RGBA', (620 * s, 120 * s), (0, 0, 0, 0))
    di = ImageDraw.Draw(ins)
    di.rounded_rectangle([0, 0, ins.width - 1, ins.height - 1], 60 * s, fill=NEGRO)
    di.rounded_rectangle([8 * s, 8 * s, ins.width - 9 * s, ins.height - 9 * s], 54 * s, fill=(235, 20, 60))
    di.text((ins.width / 2, ins.height / 2), '¡VÍDEO NUEVO CADA SEMANA!', font=ImageFont.truetype(POPPINS, 38 * s), fill='white', anchor='mm')
    ins = ins.rotate(6, expand=True, resample=Image.BICUBIC)
    img.paste(ins, (int(1430 * s - ins.width / 2), int(395 * s)), ins)
    return img


if __name__ == '__main__':
    logo().save('ciencia_logo_800.png')
    banner().save('ciencia_banner_2560x1440.png', optimize=True)
    print('ok')
