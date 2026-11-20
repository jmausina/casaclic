# Free-369 Mascotas · vídeos de producto para TikTok (@369jma), enviados como BORRADOR.
# Lunes, miércoles y viernes: toma el siguiente producto de la lista (free369_guiones.json), monta un vídeo
# vertical de unos 25 s con las fotos de la tienda, voz Piper, música propia, precio y «Envío gratis en España»,
# y lo manda a la bandeja de TikTok de @369jma. Jose Miguel solo pulsa «Publicar» y pega el texto.
#
# Uso: python3 tiktok/free369_video.py            (siguiente producto)
#      PRODUCTO=<handle> python3 tiktok/free369_video.py
# DRY_RUN=1 -> fabrica sin enviar y sin avanzar el turno. MANUAL=1 -> no mira si ya se envió hoy.
import json, os, sys, time, wave, subprocess, urllib.request
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
TIENDA = 'https://free-369.myshopify.com'
TIENDA_TXT = 'free-369.myshopify.com'
W, H = 720, 1280
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
NARANJA, MARRON, CREMA = (255, 138, 61), (59, 31, 14), (255, 243, 224)
VOZ_URL = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx'
UA = {'User-Agent': 'Mozilla/5.0 (Free369Bot; https://github.com/jmausina/casaclic)'}
TMP = os.environ.get('OUT_DIR', '/tmp/free369')
ESTADO = os.path.join(AQUI, 'free369_estado.json')


def log(*a):
    print(*a, flush=True)


def get(url, intentos=4):
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:
            log('reintento', i + 1, url[:90], e); time.sleep(4 * (i + 1))
    raise RuntimeError('no se pudo descargar ' + url)


def euros(x):
    return f'{float(x):.2f}'.replace('.', ',') + ' €'


def euros_voz(x):
    e, c = f'{float(x):.2f}'.split('.')
    return f'{e} euros' if c == '00' else f'{e} euros con {int(c)}'


# ---------- Producto (datos reales de la tienda, cada vez) ----------
def producto(handle):
    p = json.loads(get(f'{TIENDA}/products/{handle}.json'))['product']
    precios = sorted(float(v['price']) for v in p['variants'])
    return dict(titulo=p['title'], precio=precios[0], varios=precios[0] != precios[-1],
                imagenes=[i['src'] for i in p['images']], url=f'{TIENDA}/products/{handle}')


# ---------- Voz y música ----------
def preparar_voz():
    os.makedirs(TMP, exist_ok=True)
    m = os.path.join(TMP, 'voz.onnx')
    if not os.path.exists(m):
        open(m, 'wb').write(get(VOZ_URL)); open(m + '.json', 'wb').write(get(VOZ_URL + '.json'))
    from piper import PiperVoice
    return PiperVoice.load(m)


def hablar(voz, texto, ruta):
    with wave.open(ruta, 'wb') as wf:
        (voz.synthesize_wav if hasattr(voz, 'synthesize_wav') else voz.synthesize)(texto, wf)
    with wave.open(ruta) as wf:
        return wf.getnframes() / wf.getframerate()


def musica(ruta, secs, sr=44100):
    """Música alegre propia (sintetizada, sin derechos)."""
    import numpy as np
    n = int(secs * sr); buf = np.zeros(n + sr * 4); beat = 60 / 112
    prog = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    def add(t0, dur, fr, amp, dec):
        t = np.arange(int(dur * sr)) / sr; s0 = int(t0 * sr)
        buf[s0:s0 + len(t)] += amp * np.exp(-t * dec) * np.minimum(1, t * 150) * np.sin(2 * np.pi * fr * t)
    t, bar = 0.0, 0
    while t < secs:
        ch = prog[bar % 4]
        add(t, beat * 4, hz(ch[0] - 24), 0.25, 1.2)
        for k in range(8): add(t + k * beat / 2, beat * 0.9, hz(ch[k % 3] + 12), 0.07, 6)
        for k in range(4): add(t + k * beat, 0.15, 55, 0.3, 25)
        t += beat * 4; bar += 1
    buf = buf[:n]; buf /= max(1e-6, np.abs(buf).max())
    i = np.arange(n); env = np.minimum(1, np.minimum(i / (0.3 * sr), (n - i) / (1.5 * sr)))
    with wave.open(ruta, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((buf * env * 0.6 * 32767).astype('<i2').tobytes())


# ---------- Dibujo ----------
def F(s):
    return ImageFont.truetype(FB, s)


def partir(d, texto, fnt, maxw):
    pal, lin, cur = texto.split(), [], ''
    for w in pal:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=fnt) <= maxw: cur = t
        else: lin.append(cur); cur = w
    lin.append(cur); return lin


def cabecera(d):
    t = 'FREE-369 MASCOTAS'; fnt = F(30); w = d.textlength(t, font=fnt)
    d.rounded_rectangle([(W - w) / 2 - 22, 52, (W + w) / 2 + 22, 100], 24, fill=NARANJA + (255,))
    d.text(((W - w) / 2, 60), t, font=fnt, fill='white')


def caja_texto(d, y, texto, tam, fondo, color, maxl=3):
    fnt = F(tam)
    for l in partir(d, texto, fnt, W - 90)[:maxl]:
        w = d.textlength(l, font=fnt)
        d.rounded_rectangle([(W - w) / 2 - 18, y - 6, (W + w) / 2 + 18, y + tam + 12], 14, fill=fondo)
        d.text(((W - w) / 2, y), l, font=fnt, fill=color); y += tam + 22
    return y


def fotograma(img_bytes, rotulo, subtitulo, ruta):
    base = Image.new('RGB', (W, H), CREMA)
    if img_bytes:
        im = Image.open(BytesIO(img_bytes)).convert('RGB')
        fondo = im.copy(); r = max(W / fondo.width, H / fondo.height)
        fondo = fondo.resize((int(fondo.width * r) + 1, int(fondo.height * r) + 1)).filter(ImageFilter.GaussianBlur(28))
        base.paste(fondo, ((W - fondo.width) // 2, (H - fondo.height) // 2))
        caja_y, caja_h = 260, 700
        r = min((W - 40) / im.width, caja_h / im.height); im = im.resize((int(im.width * r), int(im.height * r)))
        base.paste(im, ((W - im.width) // 2, caja_y + (caja_h - im.height) // 2))
    d = ImageDraw.Draw(base, 'RGBA'); cabecera(d)
    if rotulo:
        caja_texto(d, 130, rotulo.upper(), 46, NARANJA + (240,), 'white', maxl=2)
    if subtitulo:
        # Por encima de la franja inferior de TikTok (texto y botones).
        caja_texto(d, 985, subtitulo, 36, (0, 0, 0, 175), (255, 214, 170), maxl=3)
    base.save(ruta)


def tarjeta(lineas, ruta, img_bytes=None):
    """Tarjeta de precio o de cierre: fondo naranja, textos grandes."""
    base = Image.new('RGB', (W, H), NARANJA); d = ImageDraw.Draw(base, 'RGBA')
    if img_bytes:
        im = Image.open(BytesIO(img_bytes)).convert('RGB'); r = min(460 / im.width, 460 / im.height)
        im = im.resize((int(im.width * r), int(im.height * r)))
        d.rounded_rectangle([(W - im.width) / 2 - 14, 186, (W + im.width) / 2 + 14, 214 + im.height], 26, fill=(255, 255, 255))
        base.paste(im, ((W - im.width) // 2, 200))
        y = 720
    else:
        y = 330
    d.text(((W - d.textlength('FREE-369 MASCOTAS', font=F(30))) / 2, 70), 'FREE-369 MASCOTAS', font=F(30), fill='white')
    for texto, tam, color in lineas:
        for l in partir(d, texto, F(tam), W - 80):
            w = d.textlength(l, font=F(tam)); d.text(((W - w) / 2, y), l, font=F(tam), fill=color,
                                                     stroke_width=3 if color == 'white' else 0, stroke_fill=MARRON)
            y += tam + 18
        y += 26
    base.save(ruta)


def plano(png, wav, dur, mp4, zoom=True):
    fr = int(dur * 30)
    vf = (f"[0:v]scale={W*2}:{H*2},zoompan=z='min(zoom+0.0009,1.08)':d={fr}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30,format=yuv420p[v]"
          if zoom else f"[0:v]scale={W}:{H},fps=30,format=yuv420p[v]")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', png, '-i', wav, '-filter_complex',
                    vf + ";[1:a]apad=pad_dur=0.3,aresample=44100[a]", '-map', '[v]', '-map', '[a]', '-t', f'{dur:.2f}',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-c:a', 'aac', '-b:a', '128k', '-ac', '1', mp4], check=True)


def fabricar(g, p):
    os.makedirs(TMP, exist_ok=True)
    voz = preparar_voz()
    # Fotos elegidas a mano en el guion (sin tablas de tallas ni textos en inglés); [n, x0, y0, x1, y1] = recorte.
    fotos = []
    for sel in g.get('fotos') or list(range(min(6, len(p['imagenes'])))):
        n, rec = (sel, None) if isinstance(sel, int) else (sel[0], sel[1:])
        if n >= len(p['imagenes']): continue
        try:
            b = get(p['imagenes'][n])
            if rec:
                im = Image.open(BytesIO(b)).convert('RGB'); w, h = im.size
                im = im.crop((int(rec[0] * w), int(rec[1] * h), int(rec[2] * w), int(rec[3] * h)))
                out = BytesIO(); im.save(out, 'JPEG', quality=92); b = out.getvalue()
            fotos.append(b)
        except Exception as e: log('foto no disponible', n, e)
    if not fotos:
        sys.exit('El producto no tiene fotos en la tienda.')
    desde = 'Desde ' if p['varios'] else ''
    escenas = [(g['gancho'], f) for f in g['frases']]
    partes = []
    for i, (rot, texto) in enumerate(escenas):
        wav = f'{TMP}/v{i}.wav'; dur = hablar(voz, texto, wav) + 0.3
        png = f'{TMP}/f{i}.png'; fotograma(fotos[i % len(fotos)], rot if i == 0 else None, texto, png)
        mp4 = f'{TMP}/p{i}.mp4'; plano(png, wav, dur, mp4); partes.append((mp4, dur))
    # Precio
    i = len(escenas); wav = f'{TMP}/v{i}.wav'
    dur = hablar(voz, f"{desde}{euros_voz(p['precio'])}, con envío gratis en España.", wav) + 0.4
    png = f'{TMP}/f{i}.png'
    tarjeta([(g['nombre_corto'], 44, MARRON), (desde + euros(p['precio']), 96, 'white'), ('ENVÍO GRATIS EN ESPAÑA', 40, MARRON)], png, fotos[0])
    mp4 = f'{TMP}/p{i}.mp4'; plano(png, wav, dur, mp4, zoom=False); partes.append((mp4, dur))
    # Cierre
    i += 1; wav = f'{TMP}/v{i}.wav'
    dur = hablar(voz, 'Lo tienes en la tienda Free-369. Síguenos para más ideas para tu mascota.', wav) + 0.6
    png = f'{TMP}/f{i}.png'
    tarjeta([('Lo tienes en', 48, MARRON), ('FREE-369', 110, 'white'), (TIENDA_TXT, 36, MARRON), ('Síguenos para más ideas', 40, 'white')], png)
    mp4 = f'{TMP}/p{i}.mp4'; plano(png, wav, dur, mp4, zoom=False); partes.append((mp4, dur))

    lst = f'{TMP}/lista.txt'; open(lst, 'w').write(''.join(f"file '{m}'\n" for m, _ in partes))
    total = sum(d for _, d in partes); mus = f'{TMP}/m.wav'; musica(mus, total + 1)
    os.makedirs(f'{TMP}/final', exist_ok=True); final = f"{TMP}/final/free369_{g['handle']}.mp4"
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-i', mus, '-filter_complex',
                    '[1:a]volume=0.14[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]',
                    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', final], check=True)
    log(f'Vídeo: {final} · {total:.1f} s · {os.path.getsize(final)//1024} KB')
    return final, total


def texto_tiktok(g, p):
    desde = 'desde ' if p['varios'] else ''
    return (f"{g['gancho']} 🐾 {p['titulo']}: {desde}{euros(p['precio'])} con envío gratis en España. "
            f"Lo tienes en {TIENDA_TXT} {g['hashtags']}")


if __name__ == '__main__':
    guiones = json.load(open(os.path.join(AQUI, 'free369_guiones.json')))
    estado = json.load(open(ESTADO)) if os.path.exists(ESTADO) else {'siguiente': 0, 'ultimo_envio': '', 'historial': []}
    hoy = time.strftime('%Y-%m-%d'); dry = os.environ.get('DRY_RUN') == '1'
    if not dry and os.environ.get('MANUAL') != '1' and estado.get('ultimo_envio') == hoy:
        log('Hoy ya se envió un vídeo a TikTok. Nada que hacer.'); sys.exit(0)
    pedido = os.environ.get('PRODUCTO', '').strip()
    if pedido:
        g = next(x for x in guiones if x['handle'] == pedido)
    else:
        g = guiones[estado['siguiente'] % len(guiones)]
    p = producto(g['handle'])
    video, secs = fabricar(g, p)
    texto = texto_tiktok(g, p)
    log('TEXTO PARA TIKTOK:', texto)
    gs = os.environ.get('GITHUB_STEP_SUMMARY')
    if dry:
        if gs: open(gs, 'a').write(f"### Prueba (sin enviar): {p['titulo']}\n\n{secs:.0f} s\n\nTexto: {texto}\n\n")
        sys.exit(0)
    os.environ['TT_CUENTA'] = '369jma'
    sys.path.insert(0, AQUI)
    import tiktok_api
    pid = tiktok_api.subir_borrador(video)
    if not pedido:
        estado['siguiente'] = (estado['siguiente'] + 1) % len(guiones)
    estado['ultimo_envio'] = hoy
    estado['historial'] = (estado.get('historial', []) + [dict(fecha=hoy, producto=g['handle'], id=pid)])[-60:]
    json.dump(estado, open(ESTADO, 'w'), ensure_ascii=False, indent=1)
    if gs: open(gs, 'a').write(f"### TikTok Free-369 Mascotas: borrador enviado\n\n{p['titulo']} · {secs:.0f} s\n\n"
                               f"**Texto para pegar al publicar:**\n\n{texto}\n\n")
