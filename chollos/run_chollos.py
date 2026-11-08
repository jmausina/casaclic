# Robot de Shorts diarios de «Chollos de Belleza».
# Lee las ofertas del canal de Telegram @ChollosBellezaES, elige las 3 de mayor descuento
# (sin repetir las de los 3 días anteriores), fabrica el Short con make_reel.py y lo sube
# al canal de YouTube @ChollosdeBelleza. Usa SOLO los datos del canal: nunca inventa precios.
#
# Variables de entorno:
#   YT_CLIENT_ID, YT_CLIENT_SECRET   cliente de Google Cloud (el mismo que CasaClic)
#   YT_CHOLLOS_REFRESH_TOKEN         token del canal Chollos de Belleza
#   EVENT_NAME, EVENT_SCHEDULE       los pone el flujo de GitHub (github.event_name / github.event.schedule)
#   DRY_RUN=1                        fabrica el vídeo pero no lo sube (pruebas)
import json, os, re, sys, html, time, subprocess, unicodedata, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(AQUI, 'historial.json')
TZ = ZoneInfo('Europe/Madrid')
CANAL_TG = 'ChollosBellezaES'
CANAL_YT_NOMBRE = 'chollos de belleza'
CANAL_YT_HANDLE = '@chollosdebelleza'
OUT = os.environ.get('OUT_DIR', '/tmp/chollos')


def log(*a):
    print(*a, flush=True)


def salir_sin_error(msg):
    log('FIN SIN SUBIR:', msg)
    sys.exit(0)


# ---------- 0. ¿Toca hoy? (cron de invierno 18:30 UTC / de verano 17:30 UTC) ----------
def toca_por_horario():
    if os.environ.get('EVENT_NAME') != 'schedule':
        return True
    cron = (os.environ.get('EVENT_SCHEDULE') or '').strip()
    offset_h = int(datetime.now(TZ).utcoffset().total_seconds() // 3600)  # 1 = invierno, 2 = verano
    hora_cron = cron.split()[1] if len(cron.split()) > 1 else ''
    esperado = '18' if offset_h == 1 else '17'
    if hora_cron != esperado:
        salir_sin_error(f'este cron ({cron}) no es el de la estación actual (UTC+{offset_h})')
    return True


# ---------- 1. Ofertas del canal de Telegram ----------
def descargar_telegram():
    url = f'https://t.me/s/{CANAL_TG}?v={int(time.time())}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) ChollosBot/1.0',
                                               'Cache-Control': 'no-cache'})
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            log('Telegram falló, reintento', intento + 1, e)
            time.sleep(5)
    raise SystemExit('ERROR: no se pudo descargar el canal de Telegram')


def limpiar(fragmento):
    t = re.sub(r'<br\s*/?>', '\n', fragmento)
    t = re.sub(r'<[^>]+>', '', t)
    return html.unescape(t).replace('\xa0', ' ')


def normaliza(s):
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def euros(s):
    return float(s.replace('€', '').replace('.', '').replace(',', '.').strip())


def parsear(pagina):
    ofertas = []
    trozos = re.split(r'(?=<div class="tgme_widget_message_wrap)', pagina)
    for tr in trozos:
        m = re.search(r'data-post="[^"/]+/(\d+)"', tr)
        if not m:
            continue
        post = int(m.group(1))
        mt = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*)', tr, re.S)
        if not mt:
            continue
        cuerpo = mt.group(1)
        nombre = re.search(r'🔥.*?<b>(.*?)</b>', cuerpo, re.S)
        precios = re.search(r'💰.*?<b>\s*([\d.,]+\s*€)\s*</b>\s*<s>\s*([\d.,]+\s*€)\s*</s>\s*\(\s*(-?\d+)\s*%\s*\)', cuerpo, re.S)
        frase = re.search(r'✨(?:</b></i>)?(.*?)(?:<br|$)', cuerpo, re.S)
        asin = re.search(r'amazon\.es/(?:[^"\s]*/)?dp/([A-Z0-9]{10})', cuerpo)
        if not (nombre and precios and asin):
            continue  # bienvenida, consejos del domingo, etc.
        n = limpiar(nombre.group(1)).strip()
        precio, antes, pct = precios.group(1).strip(), precios.group(2).strip(), abs(int(precios.group(3)))
        try:
            if not (0 < euros(precio) < euros(antes)) or pct <= 0:
                continue
        except ValueError:
            continue
        ofertas.append({
            'post': post, 'asin': asin.group(1), 'nombre': n,
            'precio': precio.replace(' €', ' €'), 'antes': antes, 'pct': pct,
            'frase': limpiar(frase.group(1)).strip() if frase else '',
        })
    ofertas.sort(key=lambda o: o['post'])
    return ofertas


# ---------- 2. Recortes sin cortar palabras ----------
def recorta(texto, maximo, seps=(':', '. ', ';', ' —', ' –', ',')):
    texto = re.sub(r'\s+', ' ', texto).strip()
    if len(texto) <= maximo:
        return texto
    # Primero, una frase o trozo completo (hasta : , ; . —) si cabe y tiene sentido
    for sep in seps:
        trozo = texto.split(sep)[0].strip()
        if 15 <= len(trozo) <= maximo:
            return trozo.rstrip(' ,;:.–—')
    corte = ''
    for palabra in texto.split(' '):
        prueba = (corte + ' ' + palabra).strip()
        if len(prueba) > maximo:
            break
        corte = prueba
    corte = corte.rstrip(' ,;:.–—-(')
    # que no termine en palabra «colgada» (de, y, para, con, el...)
    colgadas = {'de', 'del', 'y', 'e', 'o', 'u', 'a', 'al', 'para', 'con', 'sin', 'en', 'el', 'la', 'los', 'las', 'un', 'una', 'por', 'que', '–', '-', '—'}
    palabras = corte.split(' ')
    while len(palabras) > 2 and palabras[-1].lower() in colgadas:
        palabras.pop()
    return ' '.join(palabras).rstrip(' ,;:.–—-(')


def nombre_corto(nombre, maximo=38):
    base = re.split(r' [–—-] |\(|,', nombre)[0].strip()
    return recorta(base, maximo, ())


# ---------- 3. Historial ----------
def leer_historial():
    try:
        return json.load(open(HIST))
    except Exception:
        return {'dias': []}


def vetados(hist, hoy):
    desde = hoy - timedelta(days=3)
    asins, nombres = set(), set()
    for d in hist.get('dias', []):
        try:
            f = datetime.strptime(d['fecha'], '%Y-%m-%d').date()
        except Exception:
            continue
        if desde <= f <= hoy:
            for p in d.get('productos', []):
                asins.add(p.get('asin'))
                nombres.add(normaliza(p.get('nombre', '')))
    return asins, nombres


# ---------- 4. YouTube ----------
def http_json(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def token_acceso():
    cid, sec, rt = (os.environ.get(k, '').strip() for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_CHOLLOS_REFRESH_TOKEN'))
    if not (cid and sec and rt):
        raise SystemExit('ERROR: faltan los secretos YT_CLIENT_ID / YT_CLIENT_SECRET / YT_CHOLLOS_REFRESH_TOKEN')
    body = urllib.parse.urlencode({'client_id': cid, 'client_secret': sec, 'refresh_token': rt,
                                   'grant_type': 'refresh_token'}).encode()
    st, _, raw = http_json('https://oauth2.googleapis.com/token', body,
                           {'Content-Type': 'application/x-www-form-urlencoded'})
    if st != 200:
        raise SystemExit(f'ERROR: Google no dio acceso ({st}): {raw[:300]!r}')
    return json.loads(raw)['access_token']


def comprobar_canal(tok):
    st, _, raw = http_json('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
                           headers={'Authorization': f'Bearer {tok}'})
    if st != 200:
        raise SystemExit(f'ERROR: channels.list falló ({st}): {raw[:300]!r}')
    items = json.loads(raw).get('items', [])
    if len(items) != 1:
        raise SystemExit(f'ERROR: el token no apunta a un único canal ({len(items)})')
    sn = items[0]['snippet']
    titulo, handle = sn.get('title', ''), (sn.get('customUrl') or '').lower()
    log('Canal del token:', titulo, handle, items[0]['id'])
    if normaliza(titulo) != normaliza(CANAL_YT_NOMBRE) and handle != CANAL_YT_HANDLE:
        raise SystemExit(f'ERROR: el token es del canal «{titulo}», no de Chollos de Belleza. No se sube nada.')
    return items[0]['id']


def subir(tok, ruta, titulo, descripcion, tags):
    meta = {
        'snippet': {'title': titulo, 'description': descripcion, 'tags': tags, 'categoryId': '26',
                    'defaultLanguage': 'es', 'defaultAudioLanguage': 'es'},
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False, 'embeddable': True},
    }
    tam = os.path.getsize(ruta)
    st, hd, raw = http_json(
        'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
        json.dumps(meta).encode(),
        {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json; charset=UTF-8',
         'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(tam)}, 'POST')
    loc = {k.lower(): v for k, v in hd.items()}.get('location')
    if st != 200 or not loc:
        raise SystemExit(f'ERROR: YouTube no aceptó la subida ({st}): {raw[:500]!r}')
    with open(ruta, 'rb') as fh:
        datos = fh.read()
    st, _, raw = http_json(loc, datos, {'Authorization': f'Bearer {tok}', 'Content-Type': 'video/mp4',
                                        'Content-Length': str(tam)}, 'PUT')
    if st not in (200, 201):
        raise SystemExit(f'ERROR: fallo al enviar el vídeo ({st}): {raw[:500]!r}')
    return json.loads(raw)['id']


# ---------- Principal ----------
def main():
    toca_por_horario()
    ahora = datetime.now(TZ)
    hoy = ahora.date()
    hist = leer_historial()
    if os.environ.get('EVENT_NAME') == 'schedule' and any(
            d.get('fecha') == hoy.isoformat() and d.get('video') for d in hist.get('dias', [])):
        salir_sin_error('hoy ya se subió un Short')

    ofertas = parsear(descargar_telegram())
    log('Ofertas encontradas en la página:', len(ofertas))
    recientes = ofertas[-12:]
    vistos_asin, vistos_nom, unicas = set(), set(), []
    for o in reversed(recientes):  # de la más nueva a la más antigua
        k = normaliza(o['nombre'])
        if o['asin'] in vistos_asin or k in vistos_nom:
            continue
        vistos_asin.add(o['asin']); vistos_nom.add(k); unicas.append(o)
    ban_asin, ban_nom = vetados(hist, hoy)
    nuevas = [o for o in unicas if o['asin'] not in ban_asin and normaliza(o['nombre']) not in ban_nom]
    log('Únicas:', len(unicas), '· nuevas (no salieron en 3 días):', len(nuevas))
    if len(nuevas) < 2:
        salir_sin_error('menos de 2 ofertas nuevas hoy')
    elegidas = sorted(nuevas, key=lambda o: (-o['pct'], -o['post']))[:3]

    deals = [{'name': recorta(o['nombre'], 45, (' –', ' —', ' - ', ',', ' (')), 'price': o['precio'], 'old': o['antes'],
              'pct': f"-{o['pct']}%", 'why': recorta(o['frase'], 50) or 'Oferta de belleza en Amazon'}
             for o in elegidas]
    os.makedirs(OUT, exist_ok=True)
    json.dump(deals, open(f'{OUT}/deals.json', 'w'), ensure_ascii=False, indent=1)
    log(json.dumps(deals, ensure_ascii=False, indent=1))

    video = f'{OUT}/short.mp4'
    subprocess.run([sys.executable, os.path.join(AQUI, 'make_reel.py'), f'{OUT}/deals.json', video], check=True)
    if os.path.getsize(video) < 100_000:
        raise SystemExit('ERROR: el vídeo salió vacío')

    mejor = elegidas[0]
    titulo = f"{nombre_corto(mejor['nombre'])} de {mejor['antes']} hoy por {mejor['precio']} #Shorts"
    if len(titulo) > 100:
        titulo = f"{len(elegidas)} chollos de belleza en Amazon hoy #Shorts"
    numeros = ['1⃣', '2⃣', '3⃣']
    lineas = [f"{numeros[i]} {o['nombre']} → {o['precio']} (antes {o['antes']})" for i, o in enumerate(elegidas)]
    descripcion = ('Chollos de belleza en Amazon hoy 💄\n\n' + '\n'.join(lineas) +
                   '\n\n👉 Los enlaces y nuevas ofertas cada día, gratis en nuestro canal de Telegram: https://t.me/ChollosBellezaES'
                   '\n\nComo Afiliado de Amazon, obtenemos ingresos por las compras adscritas que cumplen los requisitos aplicables. Los precios pueden cambiar en cualquier momento.'
                   '\n#chollos #belleza #ofertas #amazon #skincare #chollosamazon #shorts')
    tags = ['chollos', 'belleza', 'ofertas', 'amazon', 'skincare', 'chollos amazon', 'shorts', 'chollos de belleza']
    log('Título:', titulo)
    log('Descripción:\n' + descripcion)

    if os.environ.get('DRY_RUN') == '1':
        salir_sin_error('DRY_RUN: vídeo fabricado, no se sube')

    tok = token_acceso()
    canal = comprobar_canal(tok)
    vid = subir(tok, video, titulo, descripcion, tags)
    log('SUBIDO: https://youtube.com/shorts/' + vid)

    hist.setdefault('dias', []).append({
        'fecha': hoy.isoformat(), 'hora': ahora.strftime('%H:%M'), 'video': vid, 'canal': canal, 'titulo': titulo,
        'productos': [{'asin': o['asin'], 'nombre': o['nombre'], 'precio': o['precio'], 'antes': o['antes']} for o in elegidas],
    })
    limite = (hoy - timedelta(days=30)).isoformat()
    hist['dias'] = [d for d in hist['dias'] if d.get('fecha', '') >= limite]
    json.dump(hist, open(HIST, 'w'), ensure_ascii=False, indent=1)
    with open(os.environ.get('GITHUB_STEP_SUMMARY', os.devnull), 'a') as s:
        s.write(f'Short subido: https://youtube.com/shorts/{vid}\n\n{titulo}\n')


if __name__ == '__main__':
    main()
