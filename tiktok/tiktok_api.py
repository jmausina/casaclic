# CasaClic - envío de vídeos a TikTok como BORRADOR (Content Posting API, modo "Upload").
# El vídeo llega a la bandeja de TikTok de casaclic_oficial; Jose Miguel solo pulsa «Publicar».
#
# Secretos de GitHub: TT_CLIENT_KEY y TT_CLIENT_SECRET (app CasaClic, sandbox «Robot CasaClic").
# El permiso de la cuenta (refresh_token) se guarda CIFRADO en tiktok/token.enc con una llave
# derivada de TT_CLIENT_SECRET. Sin ese secreto no se puede leer. Cada uso lo renueva y lo vuelve a guardar.
import os, sys, json, time, base64, hashlib, requests
from cryptography.fernet import Fernet

API = "https://open.tiktokapis.com/v2"
AQUI = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(AQUI, "token.enc")
REDIRECT = "https://jmausina.github.io/casaclic/tiktok.html"


def _f():
    k = hashlib.sha256(os.environ["TT_CLIENT_SECRET"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(k))


def _guardar(datos):
    open(TOKEN_FILE, "wb").write(_f().encrypt(json.dumps(datos).encode()))


def _token(body):
    body.update({"client_key": os.environ["TT_CLIENT_KEY"], "client_secret": os.environ["TT_CLIENT_SECRET"]})
    r = requests.post(f"{API}/oauth/token/", data=body, timeout=30,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    d = r.json()
    if "access_token" not in d:
        sys.exit("TikTok rechazó el permiso: " + json.dumps(d)[:400])
    return d


def autorizar(code):
    """Canjea el código de la página tiktok.html y guarda el permiso cifrado."""
    if "code=" in code:
        from urllib.parse import urlparse, parse_qs
        code = parse_qs(urlparse(code).query).get("code", [""])[0]
    d = _token({"code": code, "grant_type": "authorization_code", "redirect_uri": REDIRECT})
    _guardar({"refresh_token": d["refresh_token"], "open_id": d.get("open_id"), "scope": d.get("scope"),
              "guardado": time.strftime("%Y-%m-%d")})
    return d["access_token"], d.get("scope")


def acceso():
    """Devuelve un access_token nuevo y guarda el refresh_token renovado."""
    if not os.path.exists(TOKEN_FILE):
        sys.exit("Falta el permiso de TikTok (tiktok/token.enc). Hay que lanzar «TikTok - autorizar».")
    viejo = json.loads(_f().decrypt(open(TOKEN_FILE, "rb").read()))
    d = _token({"grant_type": "refresh_token", "refresh_token": viejo["refresh_token"]})
    viejo.update({"refresh_token": d.get("refresh_token", viejo["refresh_token"]), "guardado": time.strftime("%Y-%m-%d")})
    _guardar(viejo)
    return d["access_token"]


def cuenta(at):
    r = requests.get(f"{API}/user/info/?fields=open_id,display_name", headers={"Authorization": "Bearer " + at}, timeout=30)
    return r.json().get("data", {}).get("user", {})


def subir_borrador(path, at=None):
    """Sube el vídeo a la bandeja de TikTok como borrador. Devuelve el publish_id."""
    at = at or acceso()
    print("Cuenta de TikTok:", cuenta(at).get("display_name"))
    n = os.path.getsize(path)
    if n > 64_000_000:
        sys.exit("El vídeo pasa de 64 MB; TikTok pide trocearlo y este robot no lo hace.")
    h = {"Authorization": "Bearer " + at, "Content-Type": "application/json; charset=UTF-8"}
    r = requests.post(f"{API}/post/publish/inbox/video/init/", headers=h, timeout=30,
                      json={"source_info": {"source": "FILE_UPLOAD", "video_size": n, "chunk_size": n, "total_chunk_count": 1}}).json()
    if r.get("error", {}).get("code") != "ok":
        sys.exit("TikTok no aceptó el envío: " + json.dumps(r)[:400])
    pid, url = r["data"]["publish_id"], r["data"]["upload_url"]
    up = requests.put(url, data=open(path, "rb").read(), timeout=300,
                      headers={"Content-Type": "video/mp4", "Content-Length": str(n), "Content-Range": f"bytes 0-{n-1}/{n}"})
    if up.status_code not in (200, 201):
        sys.exit(f"Falló la subida a TikTok ({up.status_code}): {up.text[:300]}")
    estado = "?"
    for espera in (5, 10, 15, 20, 30, 30, 30):
        time.sleep(espera)
        s = requests.post(f"{API}/post/publish/status/fetch/", headers=h, json={"publish_id": pid}, timeout=30).json()
        estado = s.get("data", {}).get("status", "?")
        if estado in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            break
        if estado == "FAILED":
            sys.exit("TikTok falló al procesar el vídeo: " + json.dumps(s)[:400])
    print(f"TIKTOK: borrador enviado a la bandeja de casaclic_oficial (estado {estado}, id {pid})")
    return pid


if __name__ == "__main__":
    # Uso: python tiktok/tiktok_api.py autorizar <código o dirección completa>
    #      python tiktok/tiktok_api.py subir <video.mp4>
    if sys.argv[1] == "enlace":
        # La clave de cliente es pública (va en el propio enlace de TikTok); el secreto nunca se muestra.
        from urllib.parse import urlencode
        print("ENLACE: https://www.tiktok.com/v2/auth/authorize/?" + urlencode({"client_key": os.environ["TT_CLIENT_KEY"],
              "scope": "user.info.basic,video.upload", "response_type": "code", "redirect_uri": REDIRECT, "state": "casaclic"}))
    elif sys.argv[1] == "autorizar":
        at, scope = autorizar(sys.argv[2])
        print("Permiso guardado. Ámbitos:", scope, "· Cuenta:", cuenta(at).get("display_name"))
    elif sys.argv[1] == "subir":
        subir_borrador(sys.argv[2])
