# Repaso de TODOS los vídeos de los canales (24/11/2026, pedido por Jose Miguel).
# MODO=revisar  -> solo lee y dice qué le falta a cada vídeo (gasta ~1 unidad por cada 50 vídeos).
# MODO=aplicar  -> arregla lo que falte, hasta PRESUPUESTO unidades de cupo (cada cambio = 50).
# Qué se revisa: lista de reproducción, casilla «Uso de IA» (si lleva voz por ordenador),
# «no es para niños», idioma español y que la descripción empiece por el título.
# No toca títulos ni miniaturas, ni vídeos de menos de 72 h en la descripción (regla del vídeo: 48-72 h sin tocar).
import os, re, sys, json, datetime as dt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import yt_extra

CANALES = {"eab": ("YT_EAB_REFRESH_TOKEN", "Estudio Arte y Bisutería"),
           "chollos": ("YT_CHOLLOS_REFRESH_TOKEN", "Chollos de Belleza"),
           "casaclic": ("YT_REFRESH_TOKEN", "CasaClic Oficial"),
           "ba": ("YT_BELLEZA_REFRESH_TOKEN", "Belleza Ancestral"),
           "ciencia": ("YT_CIENCIA_REFRESH_TOKEN", "Ciencia y Porqués")}
LISTAS = {("eab", "short"): "Trucos de bisutería para empezar", ("eab", "largo"): "Trucos de bisutería para empezar",
          ("chollos", "short"): "Chollos de belleza en Amazon", ("chollos", "largo"): "Chollos de belleza en Amazon",
          ("casaclic", "short"): "Recetas sanas y caseras", ("casaclic", "largo"): "Recetas sanas y caseras",
          ("ba", "short"): "Recetas de belleza natural en 1 minuto",
          ("ba", "largo"): "La vuelta al mundo de la belleza ancestral",
          ("ciencia", "short"): "Ciencia en 1 minuto", ("ciencia", "largo"): "Historia y ciencia explicadas"}
VOZ_SIEMPRE = {"eab", "ba", "ciencia"}
MODO = os.environ.get("MODO", "revisar")
PRESUPUESTO = int(os.environ.get("PRESUPUESTO", "0") or 0)
gastado = 0
resumen = []
HECHO_F = "yt_repaso_hecho.json"  # vídeos ya repasados en modo aplicar (no se repiten)
HECHO = set(json.load(open(HECHO_F))) if os.path.exists(HECHO_F) else set()


def segundos(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def lleva_voz(clave, desc):
    return clave in VOZ_SIEMPRE or bool(re.search(r"voz (generada|narradora)|narraci[oó]n con voz|piper", desc, re.I))


def gastar(n):
    global gastado
    if MODO != "aplicar" or gastado + n > PRESUPUESTO:
        return False
    gastado += n
    return True


def unir_duplicadas(yt, canal):
    """Si hay dos listas con el mismo nombre: la más nueva pasa a privada («duplicada») y sus vídeos se copian a la buena."""
    todas, pt = [], None
    while True:
        r = yt.playlists().list(part="snippet,status,contentDetails", mine=True, maxResults=50, pageToken=pt).execute()
        todas += r["items"]; pt = r.get("nextPageToken")
        if not pt: break
    por_nombre = {}
    for p in todas:
        if "(duplicada)" not in p["snippet"]["title"]:
            por_nombre.setdefault(p["snippet"]["title"].strip().lower(), []).append(p)
    for nom, ps in por_nombre.items():
        if len(ps) < 2: continue
        ps.sort(key=lambda p: p["snippet"]["publishedAt"])
        buena = ps[0]
        dentro, pt = set(), None
        while True:
            r = yt.playlistItems().list(part="contentDetails", playlistId=buena["id"], maxResults=50, pageToken=pt).execute()
            dentro |= {i["contentDetails"]["videoId"] for i in r["items"]}; pt = r.get("nextPageToken")
            if not pt: break
        for dup in ps[1:]:
            if MODO != "aplicar": print(f"  DUPLICADA: «{nom}» {dup['id']}"); continue
            if gastar(50):
                sn = dup["snippet"]
                yt.playlists().update(part="snippet,status", body={"id": dup["id"], "snippet": {
                    "title": sn["title"] + " (duplicada)", "description": sn.get("description", "")},
                    "status": {"privacyStatus": "private"}}).execute()
                print(f"  Lista duplicada «{nom}» {dup['id']} → privada")
            pt, movidos = None, 0
            while True:
                r = yt.playlistItems().list(part="contentDetails", playlistId=dup["id"], maxResults=50, pageToken=pt).execute()
                for i in r["items"]:
                    vid = i["contentDetails"]["videoId"]
                    if vid not in dentro and gastar(50):
                        yt_extra.a_lista(yt, vid, sn["title"], lista_id=buena["id"]); dentro.add(vid); movidos += 1
                pt = r.get("nextPageToken")
                if not pt: break
            print(f"  Pasados a la lista buena: {movidos} (faltan los que no cupieron)")


def revisar_canal(clave):
    var, nombre = CANALES[clave]
    if not os.environ.get(var):
        print(f"\n## {nombre}: SIN PERMISO, se salta"); return
    cr = Credentials(None, refresh_token=os.environ[var], token_uri="https://oauth2.googleapis.com/token",
                     client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"])
    yt = build("youtube", "v3", credentials=cr, cache_discovery=False)
    ch = yt.channels().list(part="snippet,contentDetails", mine=True).execute()["items"][0]
    if ch["snippet"]["title"] != nombre:
        print(f"\n## ERROR: el permiso es de «{ch['snippet']['title']}», no de «{nombre}». Se salta."); return
    subidas = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, pt = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=subidas, maxResults=50, pageToken=pt).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        pt = r.get("nextPageToken")
        if not pt: break
    # listas que ya existen y sus vídeos
    listas, pt = {}, None
    while True:
        r = yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=pt).execute()
        for p in r["items"]: listas[p["snippet"]["title"].strip().lower()] = p["id"]
        pt = r.get("nextPageToken")
        if not pt: break
    en_lista = {}
    for nom in {v for (c, _), v in LISTAS.items() if c == clave}:
        pid, dentro, pt = listas.get(nom.lower()), set(), None
        while pid:
            r = yt.playlistItems().list(part="contentDetails", playlistId=pid, maxResults=50, pageToken=pt).execute()
            dentro |= {i["contentDetails"]["videoId"] for i in r["items"]}
            pt = r.get("nextPageToken")
            if not pt: break
        en_lista[nom] = dentro
    unir_duplicadas(yt, nombre)
    ahora = dt.datetime.now(dt.timezone.utc)
    print(f"\n## {nombre}: {len(ids)} vídeos")
    for k in range(0, len(ids), 50):
        for v in yt.videos().list(part="snippet,status,contentDetails", id=",".join(ids[k:k + 50])).execute()["items"]:
            sn, st = v["snippet"], v["status"]
            if st.get("uploadStatus") not in ("processed", "uploaded"):
                print(f"- {v['id']} · saltado (estado {st.get('uploadStatus')})"); continue
            if st.get("privacyStatus") != "public":
                linea = f"- {v['id']} · saltado (no es público: {st.get('privacyStatus')}) · {sn['title'][:60]}"
                print(linea); resumen.append(linea); continue
            formato = "short" if segundos(v["contentDetails"]["duration"]) <= 180 else "largo"
            lista = LISTAS[(clave, formato)]
            edad_h = (ahora - dt.datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))).total_seconds() / 3600
            desc = sn.get("description", "")
            falta, cambios_snip, cambios_st = [], {}, {}
            if v["id"] not in en_lista.get(lista, set()): falta.append("lista")
            if st.get("selfDeclaredMadeForKids") is not False: falta.append("no-niños"); cambios_st["selfDeclaredMadeForKids"] = False
            if sn.get("defaultLanguage") != "es": falta.append("idioma"); cambios_snip["defaultLanguage"] = "es"
            if sn.get("defaultAudioLanguage") not in ("es", "es-ES"): falta.append("idioma-audio"); cambios_snip["defaultAudioLanguage"] = "es"
            nueva = yt_extra.primera_frase(sn["title"], desc)
            if nueva != desc:
                if edad_h >= 72 and len(nueva) <= 4990:
                    falta.append("1.ª frase"); cambios_snip["description"] = nueva
                else:
                    falta.append("1.ª frase (espera 72 h)")
            ia = lleva_voz(clave, desc)
            if ia and v["id"] not in HECHO:
                cambios_st["containsSyntheticMedia"] = True  # la API no devuelve la casilla: se pone una vez
            hecho = []
            if MODO == "aplicar":
                if cambios_snip or cambios_st:
                    if gastar(50):
                        snip = {x: sn[x] for x in ("title", "description", "tags", "categoryId", "defaultLanguage",
                                                   "defaultAudioLanguage") if x in sn}
                        snip.update(cambios_snip)
                        stat = {x: st[x] for x in ("privacyStatus", "embeddable", "license", "publicStatsViewable",
                                                   "selfDeclaredMadeForKids") if x in st}
                        if st.get("publishAt") and st["privacyStatus"] == "private": stat["publishAt"] = st["publishAt"]
                        stat.update(cambios_st)
                        try:
                            yt.videos().update(part="snippet,status", body={"id": v["id"], "snippet": snip, "status": stat}).execute()
                            hecho.append("datos")
                        except Exception as e:
                            hecho.append("ERROR datos: " + str(e)[:150])
                    else:
                        hecho.append("sin cupo")
                if "lista" in falta:
                    if gastar(51 if lista.lower() in listas else 101):
                        pid = yt_extra.a_lista(yt, v["id"], lista, lista_id=listas.get(lista.lower()))
                        if pid:
                            listas[lista.lower()] = pid; en_lista.setdefault(lista, set()).add(v["id"]); hecho.append("lista")
                        else:
                            hecho.append("ERROR lista")
                    else:
                        hecho.append("sin cupo lista")
            if MODO == "aplicar" and not any(h.startswith(("ERROR", "sin cupo")) for h in hecho):
                HECHO.add(v["id"])
            linea = (f"- {v['id']} · {formato} · {st['privacyStatus']} · {sn['title'][:60]} · "
                     f"falta: {', '.join(falta) or 'nada'}{' · IA' if ia else ''}"
                     f"{' · hecho: ' + ', '.join(hecho) if hecho else ''}")
            print(linea); resumen.append(linea)


for c in (os.environ.get("CANALES") or "eab,chollos,casaclic,ba,ciencia").split(","):
    try:
        revisar_canal(c.strip())
    except Exception as e:
        print(f"\n## {c}: ERROR {str(e)[:300]}")
if MODO == "aplicar":
    json.dump(sorted(HECHO), open(HECHO_F, "w"), indent=0)
print(f"\nModo: {MODO} · cupo gastado: {gastado} de {PRESUPUESTO}")
gs = os.environ.get("GITHUB_STEP_SUMMARY")
if gs:
    open(gs, "a").write(f"### Repaso ({MODO}) · cupo {gastado}\n\n" + "\n".join(resumen) + "\n")
