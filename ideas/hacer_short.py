# Fábrica de Shorts a partir de una «ficha» de idea (la escribe Claude con los resultados del buscador).
# Monta un vídeo vertical 720x1280: voz Piper, fotos libres de Wikimedia Commons (con créditos),
# rótulos y subtítulos, y música propia sin derechos. Lo sube a YouTube en PRIVADO: Jose Miguel decide si se publica.
#
# Uso: python3 ideas/hacer_short.py ideas/fichas/pendientes/xxx.json
# Tokens (secretos de GitHub) según el canal de la ficha. Si falta el token, fabrica el vídeo y no lo sube.
# DRY_RUN=1 → no sube nada.
import json, os, sys, re, math, random, struct, wave, shutil, subprocess, time, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 720, 1280
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
TOKENS = {'CasaClic Oficial': 'YT_REFRESH_TOKEN', 'Chollos de Belleza': 'YT_CHOLLOS_REFRESH_TOKEN',
          'Belleza Ancestral': 'YT_BELLEZA_REFRESH_TOKEN'}
COLORES = {'CasaClic Oficial': ((15, 107, 92), (255, 122, 89)), 'Chollos de Belleza': ((122, 31, 61), (255, 243, 176)),
           'Belleza Ancestral': ((92, 58, 33), (232, 196, 120))}
VOZ_URL = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx'
UA = {'User-Agent': 'IdeasShortsBot/1.0 (https://github.com/jmausina/casaclic; contacto por GitHub)'}
TMP = os.environ.get('OUT_DIR', '/tmp/ideas_short')


def log(*a):
    print(*a, flush=True)


def get(url, binario=True, intentos=4):
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                d = r.read(); return d if binario else d.decode()
        except Exception as e:
            log('reintento', i + 1, url[:90], e); time.sleep(4 * (i + 1))
    raise RuntimeError('no se pudo descargar ' + url)


# ---------- Voz ----------
def preparar_voz():
    os.makedirs(TMP, exist_ok=True)
    m = os.path.join(TMP, 'voz.onnx')
    if not os.path.exists(m):
        open(m, 'wb').write(get(VOZ_URL)); open(m + '.json', 'wb').write(get(VOZ_URL + '.json'))
    from piper import PiperVoice
    return PiperVoice.load(m)


def hablar(voz, texto, ruta):
    with wave.open(ruta, 'wb') as wf:
        if hasattr(voz, 'synthesize_wav'):
            voz.synthesize_wav(texto, wf)
        else:
            voz.synthesize(texto, wf)
    with wave.open(ruta) as wf:
        return wf.getnframes() / wf.getframerate()


# ---------- Imágenes libres (Wikimedia Commons) ----------
VACIAS = {'with', 'from', 'para', 'como', 'the', 'and', 'photo', 'image'}


def buscar_imagen(consultas, usadas):
    """Busca en Wikimedia Commons. Solo acepta fotos cuyo título contenga las palabras clave (evita fotos sin relación).
    `consultas` puede ser un texto o una lista de alternativas (en inglés suele haber más fotos)."""
    for q in ([consultas] if isinstance(consultas, str) else consultas):
        claves = [w for w in re.findall(r'[a-záéíóúñ]+', q.lower()) if len(w) >= 4 and w not in VACIAS]
        necesita = max(1, len(claves) - 1)
        p = dict(action='query', format='json', generator='search', gsrsearch='filetype:bitmap ' + q, gsrnamespace=6, gsrlimit=30,
                 prop='imageinfo', iiprop='url|extmetadata|size|mime', iiurlwidth=1280)
        d = json.loads(get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(p), False))
        time.sleep(1.5)  # evita el error 429 de Wikimedia
        candidatas = []
        for pg in d.get('query', {}).get('pages', {}).values():
            ii = (pg.get('imageinfo') or [{}])[0]
            if ii.get('mime') not in ('image/jpeg', 'image/png') or ii.get('width', 0) < 700 or pg['title'] in usadas:
                continue
            em = ii.get('extmetadata', {})
            lic = em.get('LicenseShortName', {}).get('value', '')
            if not lic or 'fair use' in lic.lower():
                continue
            t = pg['title'].lower().replace('_', ' ')
            puntos = sum(c in t for c in claves)
            if puntos >= necesita:
                candidatas.append((-puntos, pg.get('index', 99), pg, ii, em, lic))
        if candidatas:
            _, _, pg, ii, em, lic = sorted(candidatas, key=lambda x: (x[0], x[1]))[0]
            autor = re.sub(r'<[^>]+>', '', em.get('Artist', {}).get('value', 'Desconocido')).strip()[:60]
            usadas.add(pg['title'])
            log('Imagen:', q, '→', pg['title'])
            return get(ii['thumburl']), f"{pg['title'].replace('File:', '')} — {autor} ({lic})"
        log('Sin imagen clara para:', q)
    return None, None


# ---------- Dibujo ----------
def fuente(s):
    return ImageFont.truetype(FB, s)


def partir(d, texto, F, maxw):
    pal, lin, cur = texto.split(), [], ''
    for w in pal:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=F) <= maxw: cur = t
        else: lin.append(cur); cur = w
    lin.append(cur); return lin


def fotograma(img_bytes, rotulo, subtitulo, canal, ruta, color):
    base = Image.new('RGB', (W, H), color[0])
    if img_bytes:
        from io import BytesIO
        im = Image.open(BytesIO(img_bytes)).convert('RGB')
        fondo = im.copy(); r = max(W / fondo.width, H / fondo.height)
        fondo = fondo.resize((int(fondo.width * r) + 1, int(fondo.height * r) + 1)).filter(ImageFilter.GaussianBlur(25))
        base.paste(fondo, ((W - fondo.width) // 2, (H - fondo.height) // 2))
        r = min(W / im.width, 760 / im.height); im = im.resize((int(im.width * r), int(im.height * r)))
        base.paste(im, ((W - im.width) // 2, 250 + (760 - im.height) // 2))
    d = ImageDraw.Draw(base, 'RGBA')
    d.text((30, 40), canal, font=fuente(28), fill='white', stroke_width=2, stroke_fill=(0, 0, 0))
    if rotulo:
        F = fuente(52); y = 120
        for l in partir(d, rotulo.upper(), F, 640)[:2]:
            w = d.textlength(l, font=F); d.rounded_rectangle([(W - w) / 2 - 20, y - 6, (W + w) / 2 + 20, y + 64], 16, fill=color[0] + (235,))
            d.text(((W - w) / 2, y), l, font=F, fill='white'); y += 76
    if subtitulo:
        F = fuente(38); lineas = partir(d, subtitulo, F, 640)[:4]; y = 1050 - 24 * (len(lineas) - 1)
        for l in lineas:
            w = d.textlength(l, font=F); d.rounded_rectangle([(W - w) / 2 - 14, y - 4, (W + w) / 2 + 14, y + 48], 10, fill=(0, 0, 0, 170))
            d.text(((W - w) / 2, y), l, font=F, fill=color[1]); y += 54
    base.save(ruta)


# ---------- Música propia (sintetizada, sin derechos) ----------
def musica(ruta, secs, sr=44100, semilla=3):
    random.seed(semilla); n = int(secs * sr); buf = [0.0] * n; beat = 60 / 96
    prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    def add(t0, dur, fr, amp, dec):
        s0 = int(t0 * sr)
        for i in range(int(dur * sr)):
            j = s0 + i
            if j >= n: break
            t = i / sr; buf[j] += amp * math.exp(-t * dec) * min(1, t * 150) * math.sin(2 * math.pi * fr * t)
    t, bar = 0.0, 0
    while t < secs:
        ch = prog[bar % 4]
        add(t, beat * 4, hz(ch[0] - 24), 0.25, 1.0)
        for k in range(8): add(t + k * beat / 2, beat, hz(ch[k % 3] + 12), 0.06, 5)
        t += beat * 4; bar += 1
    pk = max(1e-6, max(abs(x) for x in buf)); fade = int(2 * sr)
    with wave.open(ruta, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b''.join(struct.pack('<h', int(x / pk * 0.6 * min(1, i / (0.5 * sr), (n - i) / fade) * 32767)) for i, x in enumerate(buf)))


# ---------- Montaje ----------
def fabricar(ficha):
    os.makedirs(TMP, exist_ok=True)
    canal = ficha['canal']; color = COLORES.get(canal, ((40, 40, 40), (255, 220, 120)))
    voz = preparar_voz(); usadas = set(); creditos = []; partes = []
    escenas = ficha['escenas'] + [dict(texto=ficha['cierre'], rotulo=ficha.get('rotulo_cierre', 'Suscríbete'), imagen=None)]
    ultima_img = None
    for i, e in enumerate(escenas):
        wav = f'{TMP}/v{i}.wav'; dur = hablar(voz, e['texto'], wav) + 0.35
        img = None
        if e.get('imagen'):
            img, cred = buscar_imagen(e['imagen'], usadas)
            if cred: creditos.append(cred)
            if img: ultima_img = img
        png = f'{TMP}/f{i}.png'; fotograma(img or ultima_img, e.get('rotulo'), e['texto'], canal, png, color)
        mp4 = f'{TMP}/p{i}.mp4'; fr = int(dur * 30)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', png, '-i', wav, '-filter_complex',
                        f"[0:v]scale=1440:2560,zoompan=z='min(zoom+0.0007,1.06)':d={fr}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30,format=yuv420p[v];"
                        f"[1:a]apad=pad_dur=0.35,aresample=44100[a]",
                        '-map', '[v]', '-map', '[a]', '-t', f'{dur:.2f}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26',
                        '-c:a', 'aac', '-b:a', '128k', '-ac', '1', mp4], check=True)
        partes.append((mp4, dur))
    lst = f'{TMP}/lista.txt'; open(lst, 'w').write(''.join(f"file '{p}'\n" for p, _ in partes))
    total = sum(d for _, d in partes); mus = f'{TMP}/m.wav'; musica(mus, total + 1)
    os.makedirs(f'{TMP}/final', exist_ok=True); final = f"{TMP}/final/{ficha.get('id', 'short')}.mp4"
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-i', mus, '-filter_complex',
                    '[1:a]volume=0.13[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]',
                    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', final], check=True)
    log(f'Vídeo: {final} · {total:.1f} s · {os.path.getsize(final)//1024} KB')
    return final, total, creditos


# ---------- Subida (en PRIVADO) ----------
def subir(ruta, ficha, creditos):
    var = TOKENS.get(ficha['canal'])
    if not var or not os.environ.get(var):
        log(f"SIN TOKEN para «{ficha['canal']}»: vídeo fabricado pero no subido."); return None
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    cr = Credentials(None, refresh_token=os.environ[var], token_uri='https://oauth2.googleapis.com/token',
                     client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'])
    yt = build('youtube', 'v3', credentials=cr, cache_discovery=False)
    nombre = yt.channels().list(part='snippet', mine=True).execute()['items'][0]['snippet']['title']
    if nombre.strip().lower() != ficha['canal'].strip().lower():
        raise SystemExit(f"ERROR: el token es de «{nombre}», no de «{ficha['canal']}». No se sube nada.")
    desc = ficha['descripcion'] + '\n\nImágenes de Wikimedia Commons:\n' + '\n'.join('• ' + c for c in creditos) + \
        '\n\nVoz generada por ordenador. Música original.\n\n#Shorts'
    body = {'snippet': {'title': ficha['titulo'][:100], 'description': desc[:4900], 'tags': ficha.get('tags', [])[:15],
                        'categoryId': ficha.get('categoria', '26'), 'defaultLanguage': 'es', 'defaultAudioLanguage': 'es'},
            'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False}}
    req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(ruta, mimetype='video/mp4', resumable=True))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    log(f"SUBIDO EN PRIVADO: https://youtube.com/shorts/{resp['id']}  ({nombre})")
    return resp['id']


if __name__ == '__main__':
    ruta_ficha = sys.argv[1]; ficha = json.load(open(ruta_ficha))
    video, secs, cred = fabricar(ficha)
    vid = None if os.environ.get('DRY_RUN') == '1' else subir(video, ficha, cred)
    ficha['resultado'] = dict(video_id=vid, segundos=round(secs, 1), creditos=cred, fecha=time.strftime('%Y-%m-%d %H:%M'))
    os.makedirs('ideas/fichas/hechas', exist_ok=True)
    json.dump(ficha, open(os.path.join('ideas/fichas/hechas', os.path.basename(ruta_ficha)), 'w'), ensure_ascii=False, indent=1)
    if os.environ.get('DRY_RUN') != '1': os.remove(ruta_ficha)
    gs = os.environ.get('GITHUB_STEP_SUMMARY')
    if gs: open(gs, 'a').write(f"### {ficha['titulo']}\n\n{('https://youtube.com/shorts/' + vid) if vid else 'No subido'} · {secs:.0f} s · privado\n\n")
