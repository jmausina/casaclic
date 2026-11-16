# Buscador de ideas virales de YouTube (versión propia de Jose Miguel, inspirada en Viralyt).
# Busca vídeos que funcionan MUY por encima de lo normal en su canal («outlier») con filtros finos:
# visitas, idioma, periodo, duración, formato (corto/largo), suscriptores, visitas/día, interacción y RPM estimado.
#
# Solo usa datos públicos de la API de YouTube. Nunca inventa cifras:
#   - Retención e ingresos reales de otros canales NO son públicos.
#   - El RPM es una ESTIMACIÓN por nicho (AIR Media-Tech, medianas 2026, 300 canales, en USD),
#     y para cortos se da un rango (3 %–14 % del RPM de vídeo largo, misma fuente).
#   - El cambio USD→EUR se descarga del Banco Central Europeo en cada ejecución.
#
# Variables de entorno: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (cliente de CasaClic, solo lectura aquí).
# Uso: python3 ideas/buscar_ideas.py [config.json]
import json, os, re, sys, csv, statistics, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
TZ = ZoneInfo('Europe/Madrid')
API = 'https://www.googleapis.com/youtube/v3/'

RPM_USD = {  # AIR Media-Tech, «RPM de YouTube por nicho 2026», medianas (USD por 1.000 vistas)
    'Educación y ciencia': 10.22, 'Transporte': 5.69, 'Estilo de vida': 2.98, 'Noticias y política': 2.60,
    'Entretenimiento': 2.43, 'Manualidades y artesanía': 2.39, 'Gadgets y tecnología': 2.33, 'Música': 2.28,
    'Comida y cocina': 2.25, 'Videojuegos': 2.05, 'Negocios y finanzas': 2.01, 'Salud y deporte': 1.23,
    'Niños y adolescentes': 0.33,
}
CATEGORIA_A_NICHO = {  # categorías oficiales de YouTube → nicho de la tabla (solo las que encajan claro)
    '27': 'Educación y ciencia', '28': 'Gadgets y tecnología', '2': 'Transporte', '25': 'Noticias y política',
    '24': 'Entretenimiento', '23': 'Entretenimiento', '10': 'Música', '20': 'Videojuegos', '17': 'Salud y deporte',
    '26': 'Estilo de vida', '22': 'Estilo de vida',
}
SHORT_MIN, SHORT_MAX = 0.03, 0.14
UNIDADES = {'usadas': 0}


def log(*a):
    print(*a, flush=True)


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def token():
    body = urllib.parse.urlencode({'client_id': os.environ['YT_CLIENT_ID'], 'client_secret': os.environ['YT_CLIENT_SECRET'],
                                   'refresh_token': os.environ['YT_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()
    return json.loads(http('https://oauth2.googleapis.com/token', body))['access_token']


def yt(tok, recurso, coste, **params):
    UNIDADES['usadas'] += coste
    url = API + recurso + '?' + urllib.parse.urlencode(params)
    try:
        return json.loads(http(url, headers={'Authorization': 'Bearer ' + tok}))
    except urllib.error.HTTPError as e:
        txt = e.read().decode()[:400]
        if e.code == 403 and 'quota' in txt.lower():
            raise SystemExit('CUPO DE YOUTUBE AGOTADO: ' + txt)
        raise SystemExit(f'Error de YouTube {e.code}: {txt}')


def usd_a_eur():
    try:
        x = http('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml').decode()
        m = re.search(r"currency='USD' rate='([\d.]+)'", x)
        return 1 / float(m.group(1)), re.search(r"time='([\d-]+)'", x).group(1)
    except Exception as e:
        log('Aviso: no se pudo leer el cambio del BCE:', e)
        return None, None


ES = set('de la que el en y los las por con para una del como tu tus esto este esta más sin pelo piel receta casera casero fácil cómo así tu perro gato ya hazlo nunca'.split())
EN = set('the and with your this how to of for at stop make you is my at home try'.split())
PT = set('não você cabelo para com que faz uma seu sua isso queda'.split())


def idioma_titulo(t):
    """Si YouTube no dice el idioma, se adivina por las palabras del título (es / en / pt)."""
    w = re.findall(r"[a-záéíóúñãõç]+", t.lower())
    puntos = {'es': sum(x in ES for x in w) + 2 * bool(re.search(r'[ñ¿¡]', t)), 'en': sum(x in EN for x in w),
              'pt': sum(x in PT for x in w) + 2 * bool(re.search(r'[ãõç]|ção', t.lower()))}
    mejor = max(puntos, key=puntos.get)
    return mejor if puntos[mejor] > 0 else ''


def segundos(iso):
    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso or '')
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def trozos(lst, n=50):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def filtro(f, clave):
    return f.get(clave)


def duracion_api(f):
    """Filtro grueso de la API para ahorrar resultados; el fino se hace después en segundos."""
    mn, mx = f.get('duracion_min_seg'), f.get('duracion_max_seg')
    if f.get('formato') == 'largos' and (mn or 0) >= 1200:
        return 'long'
    if mx is not None and mx < 240:
        return 'short'
    if mn is not None and mn >= 240 and mx is not None and mx <= 1200:
        return 'medium'
    return 'any'


def main():
    cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, 'config.json')))
    hoy = datetime.now(TZ)
    tok = token()
    cambio, fecha_cambio = usd_a_eur()
    presupuesto = cfg.get('presupuesto_unidades', 1500)
    todas = []

    for b in cfg['busquedas']:
        f = dict(cfg['filtros']); f.update(b.get('filtros', {}))
        desde = (datetime.now(timezone.utc) - timedelta(days=f['periodo_dias'])).strftime('%Y-%m-%dT%H:%M:%SZ')
        ids = {}
        for q in b['consultas']:
            if UNIDADES['usadas'] + 100 > presupuesto - 150:
                log('Presupuesto de cupo alcanzado; se salta:', q); continue
            p = dict(part='snippet', type='video', q=q, order='viewCount', maxResults=50, publishedAfter=desde,
                     videoDuration=duracion_api(f))
            if f.get('idioma'): p['relevanceLanguage'] = f['idioma']
            if f.get('pais'): p['regionCode'] = f['pais']
            for it in yt(tok, 'search', 100, **p).get('items', []):
                ids.setdefault(it['id']['videoId'], q)
        log(f"[{b['nombre']}] candidatos: {len(ids)}")

        videos = []
        for lote in trozos(list(ids)):
            videos += yt(tok, 'videos', 1, part='snippet,statistics,contentDetails', id=','.join(lote)).get('items', [])

        canales = {}
        for lote in trozos(list({v['snippet']['channelId'] for v in videos})):
            for c in yt(tok, 'channels', 1, part='snippet,statistics,contentDetails', id=','.join(lote)).get('items', []):
                canales[c['id']] = c

        filas = []
        for v in videos:
            sn, st = v['snippet'], v.get('statistics', {})
            vistas = int(st.get('viewCount', 0)); likes = int(st.get('likeCount', 0)); coms = int(st.get('commentCount', 0))
            seg = segundos(v['contentDetails'].get('duration'))
            if seg == 0:
                continue  # directos en curso
            corto = seg <= 180
            pub = datetime.fromisoformat(sn['publishedAt'].replace('Z', '+00:00'))
            dias = max(1.0, (datetime.now(timezone.utc) - pub).total_seconds() / 86400)
            c = canales.get(sn['channelId'], {})
            subs = None if c.get('statistics', {}).get('hiddenSubscriberCount') else int(c.get('statistics', {}).get('subscriberCount', 0) or 0)
            lang = (sn.get('defaultAudioLanguage') or sn.get('defaultLanguage') or '').lower() or idioma_titulo(sn['title'])
            texto = (sn['title'] + ' ' + sn.get('description', '')[:300]).lower()
            if any(x.lower() in texto for x in b.get('excluir', []) + cfg.get('excluir_siempre', [])):
                continue
            nicho = b.get('nicho_rpm') or CATEGORIA_A_NICHO.get(sn.get('categoryId'))
            rpm_largo = RPM_USD.get(nicho)
            rpm = None if rpm_largo is None else ((rpm_largo * SHORT_MIN, rpm_largo * SHORT_MAX) if corto else (rpm_largo, rpm_largo))
            fila = dict(
                busqueda=b['nombre'], canal_destino=b.get('canal_destino'), consulta=ids[v['id']],
                video_id=v['id'], url=('https://youtube.com/shorts/' if corto else 'https://youtu.be/') + v['id'],
                titulo=sn['title'], canal=sn['channelTitle'], canal_id=sn['channelId'], publicado=pub.strftime('%Y-%m-%d'),
                idioma=lang or '?', duracion_seg=seg, formato='corto' if corto else 'largo',
                visitas=vistas, visitas_dia=round(vistas / dias), likes=likes, comentarios=coms,
                interaccion_pct=round(100 * (likes + coms) / vistas, 2) if vistas else 0,
                suscriptores=subs, nicho_rpm=nicho, rpm_usd=rpm,
                uploads=c.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads'),
                etiquetas=(sn.get('tags') or [])[:12], miniatura=sn.get('thumbnails', {}).get('high', {}).get('url'),
            )
            # --- filtros finos (todo lo que no necesita más cupo) ---
            if f.get('idioma_estricto') and f.get('idioma') and lang and not lang.startswith(f['idioma']): continue
            if f.get('visitas_min') and vistas < f['visitas_min']: continue
            if f.get('visitas_max') and vistas > f['visitas_max']: continue
            if f.get('duracion_min_seg') and seg < f['duracion_min_seg']: continue
            if f.get('duracion_max_seg') and seg > f['duracion_max_seg']: continue
            if f.get('formato') == 'cortos' and not corto: continue
            if f.get('formato') == 'largos' and corto: continue
            if subs is not None and f.get('suscriptores_min') and subs < f['suscriptores_min']: continue
            if subs is not None and f.get('suscriptores_max') and subs > f['suscriptores_max']: continue
            if f.get('visitas_dia_min') and fila['visitas_dia'] < f['visitas_dia_min']: continue
            if f.get('interaccion_min_pct') and fila['interaccion_pct'] < f['interaccion_min_pct']: continue
            if f.get('rpm_min_usd') and (rpm is None or rpm[1] < f['rpm_min_usd']): continue
            filas.append(fila)

        # --- outlier: visitas / mediana de los últimos vídeos del mismo canal (cuesta 1 unidad por canal) ---
        filas.sort(key=lambda x: x['visitas'], reverse=True)
        medianas = {}
        for fila in filas[:60]:
            cid = fila['canal_id']
            if cid not in medianas and fila['uploads'] and UNIDADES['usadas'] + 2 < presupuesto:
                pl = yt(tok, 'playlistItems', 1, part='contentDetails', playlistId=fila['uploads'], maxResults=25).get('items', [])
                vids = [x['contentDetails']['videoId'] for x in pl]
                st = yt(tok, 'videos', 1, part='statistics', id=','.join(vids)).get('items', []) if vids else []
                medianas[cid] = {x['id']: int(x.get('statistics', {}).get('viewCount', 0)) for x in st}
            otras = [n for k, n in medianas.get(cid, {}).items() if k != fila['video_id']]
            if len(otras) >= 3:
                med = statistics.median(otras)
                fila['mediana_canal'] = int(med)
                fila['outlier'] = round(fila['visitas'] / max(med, 1), 1)
            elif fila['suscriptores']:
                fila['mediana_canal'] = None
                fila['outlier'] = round(fila['visitas'] / fila['suscriptores'], 1)  # plan B: visitas / suscriptores
            else:
                fila['mediana_canal'] = None; fila['outlier'] = None
        filas = filas[:60]
        if f.get('outlier_min'):
            filas = [x for x in filas if x['outlier'] is not None and x['outlier'] >= f['outlier_min']]
        clave = {'outlier': 'outlier', 'visitas': 'visitas', 'visitas_dia': 'visitas_dia', 'interaccion': 'interaccion_pct'}.get(f.get('orden'), 'outlier')
        filas.sort(key=lambda x: x.get(clave) or 0, reverse=True)
        filas = filas[:cfg.get('resultados_por_busqueda', 15)]
        for x in filas:
            if x['rpm_usd'] and cambio:
                lo, hi = x['rpm_usd']
                x['ingresos_est_eur'] = [round(x['visitas'] / 1000 * lo * cambio), round(x['visitas'] / 1000 * hi * cambio)]
            else:
                x['ingresos_est_eur'] = None
            x.pop('uploads', None)
        log(f"[{b['nombre']}] ideas que pasan los filtros: {len(filas)}")
        todas += filas

    guardar(cfg, todas, hoy, cambio, fecha_cambio)


def euros(x):
    return '—' if not x else (f'{x[0]} €' if x[0] == x[1] else f'{x[0]}–{x[1]} €')


def guardar(cfg, filas, hoy, cambio, fecha_cambio):
    carpeta = os.path.join(AQUI, 'resultados'); os.makedirs(carpeta, exist_ok=True)
    base = os.path.join(carpeta, hoy.strftime('%Y-%m-%d') + '_ideas')
    meta = dict(fecha=hoy.strftime('%Y-%m-%d %H:%M'), unidades_usadas=UNIDADES['usadas'], usd_eur=cambio, fecha_cambio=fecha_cambio,
                filtros=cfg['filtros'], fuente_rpm='AIR Media-Tech, RPM por nicho 2026 (medianas, USD); cortos 3–14 % del largo')
    json.dump(dict(meta=meta, ideas=filas), open(base + '.json', 'w'), ensure_ascii=False, indent=1)
    cols = ['busqueda', 'canal_destino', 'outlier', 'titulo', 'url', 'canal', 'suscriptores', 'mediana_canal', 'visitas', 'visitas_dia',
            'interaccion_pct', 'formato', 'duracion_seg', 'idioma', 'publicado', 'nicho_rpm', 'ingresos_est_eur', 'consulta']
    with open(base + '.csv', 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(cols)
        for x in filas:
            w.writerow([euros(x[c]) if c == 'ingresos_est_eur' else x.get(c) for c in cols])
    md = [f"# Ideas virales — {meta['fecha']}", '',
          f"Cupo de YouTube usado: {meta['unidades_usadas']} unidades. Ingresos = estimación orientativa (RPM por nicho, AIR Media-Tech 2026; cambio BCE {fecha_cambio}).", '']
    for nombre in dict.fromkeys(x['busqueda'] for x in filas):
        md += [f'## {nombre}', '', '| Outlier | Título | Canal (subs) | Visitas | Vis./día | Formato | Ingresos est. |', '|---|---|---|---|---|---|---|']
        for x in [y for y in filas if y['busqueda'] == nombre]:
            t = x['titulo'].replace('|', '/')
            md.append(f"| ×{x['outlier']} | [{t}]({x['url']}) | {x['canal']} ({x['suscriptores'] if x['suscriptores'] is not None else 'oculto'}) | "
                      f"{x['visitas']:,} | {x['visitas_dia']:,} | {x['formato']} {x['duracion_seg']//60}:{x['duracion_seg']%60:02d} | {euros(x['ingresos_est_eur'])} |".replace(',', '.'))
        md.append('')
    open(base + '.md', 'w').write('\n'.join(md))
    gs = os.environ.get('GITHUB_STEP_SUMMARY')
    if gs:
        open(gs, 'a').write('\n'.join(md))
    log('Guardado:', base + '.{json,csv,md}', '| unidades usadas:', UNIDADES['usadas'])


if __name__ == '__main__':
    main()
