# Aplica los extras (lista de reproducción y casilla de contenido sintético) a vídeos ya subidos.
# Uso desde el flujo «YouTube - extras a vídeos ya subidos». Variables: CANAL, VIDEOS (ids separados por comas),
# LISTA (nombre de la lista; vacío = no), SINTETICO (1 = marcar la casilla).
import os, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import yt_extra

TOKENS = {"casaclic": ("YT_REFRESH_TOKEN", "CasaClic Oficial"),
          "chollos": ("YT_CHOLLOS_REFRESH_TOKEN", "Chollos de Belleza"),
          "ba": ("YT_BELLEZA_REFRESH_TOKEN", "Belleza Ancestral"),
          "ciencia": ("YT_CIENCIA_REFRESH_TOKEN", "Ciencia y Porqués"),
          "eab": ("YT_EAB_REFRESH_TOKEN", "Estudio Arte y Bisutería")}
var, nombre = TOKENS[os.environ["CANAL"]]
cr = Credentials(None, refresh_token=os.environ[var], token_uri="https://oauth2.googleapis.com/token",
                 client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"])
yt = build("youtube", "v3", credentials=cr, cache_discovery=False)
canal = yt.channels().list(part="snippet", mine=True).execute()["items"][0]["snippet"]["title"]
if canal != nombre:
    sys.exit(f"ERROR: el permiso es de «{canal}», no de «{nombre}». No se toca nada.")
ids = [v.strip() for v in os.environ.get("VIDEOS", "").split(",") if v.strip()]
lista, sint = os.environ.get("LISTA", "").strip(), os.environ.get("SINTETICO") == "1"
fallos = 0
for vid in ids:
    it = yt.videos().list(part="status,snippet", id=vid).execute().get("items", [])
    if not it:
        print("NO ESTÁ en el canal:", vid); fallos += 1; continue
    print("Vídeo:", vid, it[0]["snippet"]["title"])
    if sint:
        st = it[0]["status"]
        if not st.get("containsSyntheticMedia"):
            st["containsSyntheticMedia"] = True
            try:
                yt.videos().update(part="status", body={"id": vid, "status": st}).execute()
                print("  Casilla de contenido sintético: marcada")
            except Exception as e:
                print("  AVISO sintético:", str(e)[:300]); fallos += 1
        else:
            print("  Casilla de contenido sintético: ya estaba")
    if lista and not yt_extra.a_lista(yt, vid, lista):
        fallos += 1
print("Fallos:", fallos)
sys.exit(1 if fallos else 0)
