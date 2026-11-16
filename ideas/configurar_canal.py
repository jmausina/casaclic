# Pone la descripción y las palabras clave de un canal (una sola vez, a mano).
# Uso: python3 ideas/configurar_canal.py ideas/canales/ciencia.json
import json, os, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
c = json.load(open(sys.argv[1]))
cr = Credentials(None, refresh_token=os.environ[c['token']], token_uri='https://oauth2.googleapis.com/token',
                 client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'])
yt = build('youtube', 'v3', credentials=cr, cache_discovery=False)
ch = yt.channels().list(part='brandingSettings,snippet', mine=True).execute()['items'][0]
if ch['snippet']['title'] != c['canal']:
    sys.exit(f"ERROR: el token es de «{ch['snippet']['title']}», no de «{c['canal']}».")
b = ch['brandingSettings']; b.setdefault('channel', {})
b['channel'].update(description=c['descripcion'], keywords=c['palabras_clave'], defaultLanguage='es', country='ES')
yt.channels().update(part='brandingSettings', body={'id': ch['id'], 'brandingSettings': b}).execute()
print('Canal configurado:', ch['snippet']['title'])
