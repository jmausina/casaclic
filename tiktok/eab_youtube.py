# Sube 1 Short al día al canal de YouTube «Estudio Arte y Bisutería».
# Usa los vídeos que ya hizo el robot de TikTok (eab/videos/eab_<id>.mp4).
# Prioridad: vídeo de hoy por la mañana, luego el de la tarde, luego el primero sin subir.
# No repite: si hoy ya subió uno, termina sin hacer nada (salvo VIDEO puesto a mano).
import json, os, re, sys, datetime
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CANAL = 'Estudio Arte y Bisutería'
AFILIADO = 'https://go.hotmart.com/O101670451Q'
HOY = datetime.datetime.now(ZoneInfo('Europe/Madrid')).strftime('%Y-%m-%d')
REG = 'eab/youtube.json'
reg = json.load(open(REG)) if os.path.exists(REG) else {'subidos': {}}
subidos = reg['subidos']                      # fecha -> {video, id}
hechos_yt = {v['video'] for v in subidos.values()}
guiones = {g['id']: g for g in json.load(open('tiktok/eab_guiones.json'))}
estado = json.load(open('tiktok/eab_estado.json'))
existe = lambda v: os.path.exists(f'eab/videos/eab_{v}.mp4')

def fin(msg):
    print(msg)
    open(os.environ.get('GITHUB_STEP_SUMMARY', '/dev/null'), 'a').write(msg + '\n')
    sys.exit(0)

video = os.environ.get('VIDEO', '').strip()
if not video:
    if HOY in subidos:
        fin(f'Hoy ya se subió «{subidos[HOY]["video"]}». No se repite.')
    cand = [estado['hechos'].get(HOY + '-m'), estado['hechos'].get(HOY + '-t')]
    cand += [v for v in guiones if existe(v)]
    video = next((v for v in cand if v and v not in hechos_yt and existe(v)), None)
    if not video:
        fin('No hay ningún vídeo nuevo para subir hoy.')
if video not in guiones or not existe(video):
    sys.exit(f'ERROR: no existe el vídeo «{video}».')

g = guiones[video]
texto = g['texto']
frase = re.sub(r'#\S+', '', texto).strip()
titulo = re.split(r'(?<=[.!?])\s|\s(?=[¿A-ZÁÉÍÓÚ][^#]*$)', frase)[0].strip()
titulo = re.sub(r'\s+', ' ', titulo)
if len(titulo) > 88:
    titulo = titulo[:88].rsplit(' ', 1)[0]
titulo += ' #Shorts'
tags_txt = ' '.join(re.findall(r'#\S+', texto))
desc = (f'{frase}\n\n'
        f'📚 ¿Quieres aprender bisutería desde cero? Curso recomendado (enlace de afiliado): {AFILIADO}\n\n'
        f'🔔 Suscríbete a Estudio Arte y Bisutería para más trucos.\n'
        f'Ilustraciones propias. Narración con voz generada por ordenador.\n\n{tags_txt} #shorts')
tags = [t.lstrip('#') for t in re.findall(r'#\S+', texto)] + ['bisutería', 'shorts']

cr = Credentials(None, refresh_token=os.environ['YT_EAB_REFRESH_TOKEN'], token_uri='https://oauth2.googleapis.com/token',
                 client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'])
yt = build('youtube', 'v3', credentials=cr, cache_discovery=False)
ch = yt.channels().list(part='snippet', mine=True).execute()['items']
if len(ch) != 1 or ch[0]['snippet']['title'] != CANAL:
    sys.exit(f'ERROR: el permiso no es del canal «{CANAL}» ({[c["snippet"]["title"] for c in ch]}). No se sube nada.')

body = {'snippet': {'title': titulo, 'description': desc, 'tags': tags, 'categoryId': '26',
                    'defaultLanguage': 'es', 'defaultAudioLanguage': 'es'},
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}}
req = yt.videos().insert(part='snippet,status', body=body,
                         media_body=MediaFileUpload(f'eab/videos/eab_{video}.mp4', mimetype='video/mp4', resumable=True))
r = None
while r is None:
    _, r = req.next_chunk()
vid = r['id']
subidos[HOY if HOY not in subidos else f'{HOY}-extra-{len(subidos)}'] = {'video': video, 'id': vid}
reg['subidos'] = dict(sorted(subidos.items())[-90:])
json.dump(reg, open(REG, 'w'), ensure_ascii=False, indent=1)
fin(f'Subido «{video}»: https://youtube.com/shorts/{vid} — {titulo}')
