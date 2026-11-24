# Extras comunes para todos los robots de YouTube (24/11/2026, aprobado por Jose Miguel).
# - contenido sintético: marca la casilla «Contenido alterado o sintético» (voz por ordenador).
# - primera_frase: la descripción empieza con una frase parecida al título.
# - a_lista: mete el vídeo en la lista de reproducción del canal (la crea si no existe).
# - archivo_con_titulo: copia el vídeo con un nombre de archivo parecido al título.
# Nada de esto puede romper una subida: si algo falla, avisa y sigue.
import os, re, shutil, unicodedata

SINTETICO = {"containsSyntheticMedia": True}


def limpia_titulo(titulo):
    t = re.sub(r"#\S+", "", titulo)
    t = re.sub(r"[\U0001F000-\U0001FFFF☀-➿️‍]", "", t)
    return re.sub(r"\s+", " ", t).strip(" |-·")


def primera_frase(titulo, descripcion):
    """Pone delante una frase con el título, salvo que la descripción ya empiece así."""
    t = limpia_titulo(titulo)
    if not t:
        return descripcion
    if _norm(descripcion[:len(t) + 5]).startswith(_norm(t)[:40]):
        return descripcion
    if t[-1] not in ".!?…":
        t += "."
    return f"{t}\n{descripcion}"


def _norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9 ]", "", "".join(c for c in s if not unicodedata.combining(c))).strip()


def slug(titulo, maximo=80):
    s = _norm(limpia_titulo(titulo)).replace(" ", "-")
    return re.sub(r"-+", "-", s)[:maximo].strip("-") or "video"


def archivo_con_titulo(ruta, titulo):
    """Copia el vídeo a /tmp/yt_nombre/<titulo>.mp4 y devuelve la ruta nueva (o la original si falla)."""
    try:
        os.makedirs("/tmp/yt_nombre", exist_ok=True)
        nueva = f"/tmp/yt_nombre/{slug(titulo)}.mp4"
        shutil.copyfile(ruta, nueva)
        return nueva
    except Exception as e:
        print("AVISO nombre de archivo:", e)
        return ruta


def a_lista(yt, video_id, nombre, descripcion=""):
    """Añade el vídeo a la lista «nombre» del canal. Cupo: 1 + 50 (+50 si hay que crearla)."""
    try:
        lista = None
        pt = None
        while True:
            r = yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=pt).execute()
            for it in r.get("items", []):
                if it["snippet"]["title"].strip().lower() == nombre.strip().lower():
                    lista = it["id"]
                    break
            pt = r.get("nextPageToken")
            if lista or not pt:
                break
        if not lista:
            lista = yt.playlists().insert(part="snippet,status", body={
                "snippet": {"title": nombre, "description": descripcion, "defaultLanguage": "es"},
                "status": {"privacyStatus": "public"}}).execute()["id"]
            print("Lista creada:", nombre, lista)
        elif yt.playlistItems().list(part="id", playlistId=lista, videoId=video_id).execute().get("items"):
            print(f"Ya estaba en la lista «{nombre}»")
            return lista
        import time
        for intento in range(4):  # justo después de crear la lista YouTube a veces da 409 pasajero
            try:
                yt.playlistItems().insert(part="snippet", body={"snippet": {
                    "playlistId": lista, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
                break
            except Exception as e:
                if intento == 3 or "409" not in str(e)[:40] and "SERVICE_UNAVAILABLE" not in str(e):
                    raise
                time.sleep(5 * (intento + 1))
        print(f"Añadido a la lista «{nombre}»")
        return lista
    except Exception as e:
        print(f"AVISO lista «{nombre}»:", str(e)[:300])
        return None
