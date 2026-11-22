# Serie «La vuelta al mundo de la belleza ancestral» en GitHub (22/11/2026).
# El robot de Claude deja el guion en ba/trabajos/<slug>/spec.json y lanza el flujo ba-serie.yml.
# Modos:
#   fotos     -> busca las fotos y guarda ba/trabajos/<slug>/fotos.json + muestra.jpg (para revisarlas).
#   fabricar  -> monta el vídeo (con fotos.json si existe) y lo sube EN PRIVADO a «Belleza Ancestral»
#                con el pase permanente YT_BELLEZA_REFRESH_TOKEN. Guarda resultado.json.
#   publicar  -> pone en público un vídeo ya aprobado por Jose Miguel (VIDEO_ID).
#   comprobar -> solo comprueba que el pase funciona y es del canal correcto.
# Nunca borra vídeos. Nunca sube dos veces el mismo slug (salvo FORZAR=1).
import json, os, sys, time, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("BA_DIR", "/tmp/ba")
NS = {"__name__": "ba_video"}
exec(open(os.path.join(AQUI, "ba_video.py"), encoding="utf-8").read(), NS)
CANAL = "Belleza Ancestral"
RECETARIO = "📖 Recetario de Belleza Ancestral (40 recetas): https://go.hotmart.com/M108343227O"


def log(*a):
    print(*a, flush=True)


def resumen(txt):
    gs = os.environ.get("GITHUB_STEP_SUMMARY")
    if gs:
        open(gs, "a").write(txt + "\n\n")


def youtube():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    tok = os.environ.get("YT_BELLEZA_REFRESH_TOKEN")
    if not tok:
        raise SystemExit("ERROR: falta el secreto YT_BELLEZA_REFRESH_TOKEN.")
    cr = Credentials(None, refresh_token=tok, token_uri="https://oauth2.googleapis.com/token",
                     client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"])
    yt = build("youtube", "v3", credentials=cr, cache_discovery=False)
    nombre = yt.channels().list(part="snippet", mine=True).execute()["items"][0]["snippet"]["title"]
    if nombre.strip().lower() != CANAL.lower():
        raise SystemExit(f"ERROR: el pase es de «{nombre}», no de «{CANAL}». No se hace nada.")
    return yt


def trabajo(slug):
    d = os.path.join("ba", "trabajos", slug)
    os.makedirs(d, exist_ok=True)
    return d


def correr(hasta):
    """Llama a step() hasta llegar a la etapa `hasta` (o a «listo»)."""
    for _ in range(400):
        st = NS["_st"]()
        if st.get("stage") in (hasta, "listo"):
            return
        r = NS["step"](600)
        log(time.strftime("%H:%M:%S"), r)
    raise SystemExit("ERROR: el montaje no avanza.")


def modo_fotos(slug, spec):
    d = trabajo(slug)
    NS["new_job"](spec)
    correr("tts")
    st = NS["_st"]()
    fotos = {k: [{x: f[x] for x in ("title", "url", "lic", "author")} for f in v] for k, v in st["imgs"].items()}
    json.dump(fotos, open(os.path.join(d, "fotos.json"), "w"), ensure_ascii=False, indent=1)
    # Hoja de muestra: una fila por sección, con el número de cada foto.
    from PIL import Image, ImageDraw
    tw, th, cols = 240, 135, 6
    filas = len(spec["sections"])
    hoja = Image.new("RGB", (60 + cols * (tw + 6), filas * (th + 26) + 10), (250, 246, 238))
    dr = ImageDraw.Draw(hoja)
    for i in range(filas):
        y = 6 + i * (th + 26)
        dr.text((6, y + th // 2), f"S{i}", fill=(0, 0, 0))
        for j, f in enumerate(st["imgs"].get(str(i), [])[:cols]):
            im = Image.open(f["file"]).convert("RGB")
            im.thumbnail((tw, th))
            x = 60 + j * (tw + 6)
            hoja.paste(im, (x, y))
            dr.text((x, y + th + 4), f"{i}.{j} {f['title'][5:38]}", fill=(60, 40, 20))
    hoja.save(os.path.join(d, "muestra.jpg"), quality=80)
    n = sum(len(v) for v in fotos.values())
    vacias = [k for k in map(str, range(filas)) if len(fotos.get(k, [])) < 2]
    log(f"FOTOS: {n} fotos. Secciones con menos de 2: {vacias or 'ninguna'}")
    resumen(f"### Fotos de «{slug}»\n\n{n} fotos. Revisar ba/trabajos/{slug}/muestra.jpg y quitar de fotos.json las que no encajen.")


def modo_fabricar(slug, spec, subir):
    d = trabajo(slug)
    res_p = os.path.join(d, "resultado.json")
    if os.path.exists(res_p) and json.load(open(res_p)).get("youtube_id") and os.environ.get("FORZAR") != "1":
        r = json.load(open(res_p))
        log(f"YA SUBIDO antes: https://youtu.be/{r['youtube_id']} — no se repite.")
        resumen(f"«{slug}» ya estaba subido: https://youtu.be/{r['youtube_id']}")
        return
    NS["new_job"](spec)
    fp = os.path.join(d, "fotos.json")
    if os.path.exists(fp):  # fotos ya revisadas: se usan tal cual
        NS["setup"]()
        fotos = json.load(open(fp))
        # quitar.json = lista de títulos de fotos que no encajan (la escribe el robot al revisar la muestra)
        qp = os.path.join(d, "quitar.json")
        quitar = set(json.load(open(qp))) if os.path.exists(qp) else set()
        if quitar:
            fotos = {k: [f for f in v if f["title"] not in quitar] for k, v in fotos.items()}
            log(f"Fotos quitadas tras la revisión: {len(quitar)}")
        job = NS["JOB"]
        imgs = {}
        for k, lista in fotos.items():
            imgs[k] = []
            for j, f in enumerate(lista):
                fn = f"{job}/img/{int(k):02d}_{j:02d}.jpg"
                for intento in range(4):
                    try:
                        req = urllib.request.Request(f["url"], headers=NS["UA"])
                        open(fn, "wb").write(urllib.request.urlopen(req, timeout=60).read())
                        break
                    except Exception as e:
                        log("reintento foto", f["title"], e)
                        time.sleep(5 * (intento + 1))
                else:
                    continue
                imgs[k].append(dict(f, file=fn))
                time.sleep(0.5)
        for i in range(len(spec["sections"])):
            imgs.setdefault(str(i), [])
        st = NS["_st"]()
        st["imgs"], st["stage"] = imgs, "tts"
        NS["_save"](st)
    correr("listo")
    st = NS["_st"]()
    video, thumb = NS["JOB"] + "/video.mp4", NS["JOB"] + "/thumb.jpg"
    os.makedirs("/tmp/ba_salida", exist_ok=True)
    import shutil, subprocess
    shutil.copy(video, f"/tmp/ba_salida/{slug}.mp4")
    shutil.copy(thumb, f"/tmp/ba_salida/{slug}_miniatura.jpg")
    # 6 fotogramas para revisar sin ver el vídeo entero
    for k in range(6):
        t = st["duration"] * (k + 0.5) / 6
        subprocess.run([NS["ff"](), "-y", "-loglevel", "error", "-ss", f"{t:.1f}", "-i", video, "-frames:v", "1",
                        "-vf", "scale=640:-1", f"/tmp/ba_salida/{slug}_f{k}.jpg"])
    mins = st["duration"] / 60
    log(f"VÍDEO: {mins:.1f} min, {st['size_mb']} MB")
    if not subir:
        log("PRUEBA: no se sube nada.")
        resumen(f"### Prueba «{slug}»\n\n{mins:.1f} min. No se ha subido (prueba).")
        return
    desc = st["description"]
    if not desc.startswith(RECETARIO):
        desc = RECETARIO + "\n\n" + desc
    while len(desc.encode("utf-8")) > 4900:
        desc = desc[:-50]
    yt = youtube()
    from googleapiclient.http import MediaFileUpload
    body = {"snippet": {"title": spec.get("yt_title", spec["title"])[:100], "description": desc,
                        "tags": spec.get("tags", [])[:15], "categoryId": "26",
                        "defaultLanguage": "es", "defaultAudioLanguage": "es"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(video, mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    log(f"SUBIDO (privado): https://youtu.be/{vid}")
    mini = "no"
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb, mimetype="image/jpeg")).execute()
        mini = "sí"
    except Exception as e:
        log("AVISO miniatura:", e)
    json.dump({"slug": slug, "youtube_id": vid, "privacidad": "private", "duracion_min": round(mins, 1),
               "titulo": body["snippet"]["title"], "tags": body["snippet"]["tags"], "descripcion": desc,
               "miniatura": mini, "fecha": time.strftime("%Y-%m-%d %H:%M")},
              open(res_p, "w"), ensure_ascii=False, indent=1)
    resumen(f"### Subido en privado: {body['snippet']['title']}\n\nhttps://studio.youtube.com/video/{vid}/edit · {mins:.1f} min · miniatura: {mini}")


def modo_publicar(vid):
    yt = youtube()
    it = yt.videos().list(part="status,snippet", id=vid).execute().get("items", [])
    if not it:
        raise SystemExit(f"ERROR: el vídeo {vid} no está en el canal.")
    estado = it[0]["status"]
    if estado["privacyStatus"] == "public":
        log(f"YA PÚBLICO: https://youtu.be/{vid}")
        return
    estado["privacyStatus"] = "public"
    estado.pop("publishAt", None)
    yt.videos().update(part="status", body={"id": vid, "status": estado}).execute()
    log(f"PUBLICADO: https://youtu.be/{vid}")
    resumen(f"Publicado: https://youtu.be/{vid} ({it[0]['snippet']['title']})")


if __name__ == "__main__":
    modo = os.environ.get("MODO", "comprobar")
    if modo == "comprobar":
        youtube()
        log(f"PASE OK: canal «{CANAL}».")
        resumen(f"Pase de «{CANAL}» correcto.")
    elif modo == "publicar":
        modo_publicar(os.environ["VIDEO_ID"].strip())
    else:
        slug = os.environ["SLUG"].strip()
        spec = json.load(open(os.path.join("ba", "trabajos", slug, "spec.json"), encoding="utf-8"))
        if modo == "fotos":
            modo_fotos(slug, spec)
        elif modo == "fabricar":
            modo_fabricar(slug, spec, os.environ.get("SUBIR", "1") == "1")
        else:
            raise SystemExit("Modo desconocido: " + modo)
