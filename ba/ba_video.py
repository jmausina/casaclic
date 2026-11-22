# v2 · Robot de vídeos Belleza Ancestral
# Uso en el Workbench de Composio:  exec(open('/home/user/ba/ba_video.py').read()); print(step())
# Repite step() en celdas sucesivas hasta que devuelva "LISTO: ..." (cada llamada trabaja <=150 s).
# Copia en GitHub (22/11/2026): la usa ba/serie.py. BA_DIR cambia la carpeta de trabajo.
import os, json, time, wave, subprocess, sys, math, re, struct, random, urllib.request, urllib.parse, shutil

BA = os.environ.get("BA_DIR", "/home/user/ba")
JOB = BA + "/job"
VOZ = BA + "/voz/es_ES-sharvard-medium.onnx"
W, H = 1920, 1080
CREMA, TIERRA, OSCURO, SALVIA = (238, 221, 192), (217, 154, 114), (58, 46, 34), (126, 159, 120)
UA = {"User-Agent": "BellezaAncestralBot/1.0 (bellezaancestral.oficial@gmail.com)"}
BLOCK = ["logo", "map", "mapa", "diagram", "chart", "flag", "coat of arms", "nude", "naked", "desnud", "cannabis", "cbd", "marijuana", "hemp", "drug", "tincture", "weapon", "gun", "blood", "dead", "corpse", "war", "protest", "employee", "advert", "poster", "tattoo", "cigarette", "beer", "wine", "whisky"]
LIC_OK = ("cc0", "public domain", "pd", "cc by", "cc-by", "cc by-sa", "cc-by-sa", "no restrictions")


def _sh(cmd, t=170):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-600:])
    return r.stdout


def ff():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _st():
    p = JOB + "/state.json"
    return json.load(open(p)) if os.path.exists(p) else {}


def _save(st):
    json.dump(st, open(JOB + "/state.json", "w"), ensure_ascii=False, indent=1)


def setup():
    os.makedirs(BA + "/voz", exist_ok=True)
    os.makedirs(BA + "/fonts", exist_ok=True)
    try:
        import piper, imageio_ffmpeg  # noqa
    except Exception:
        _sh([sys.executable, "-m", "pip", "install", "-q", "piper-tts", "imageio-ffmpeg", "pillow", "numpy"])
    base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/"
    for f in ["es_ES-sharvard-medium.onnx", "es_ES-sharvard-medium.onnx.json"]:
        p = BA + "/voz/" + f
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            urllib.request.urlretrieve(base + f, p)
    fonts = {"serif.ttf": "https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf",
             "serif-it.ttf": "https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf"}
    for f, u in fonts.items():
        p = BA + "/fonts/" + f
        if not os.path.exists(p):
            try:
                urllib.request.urlretrieve(u, p)
            except Exception:
                pass
    return "setup ok"


def font(size, italic=False, bold=True):
    from PIL import ImageFont
    p = BA + "/fonts/" + ("serif-it.ttf" if italic else "serif.ttf")
    try:
        f = ImageFont.truetype(p, size)
        try:
            f.set_variation_by_axes([600 if bold else 450])
        except Exception:
            pass
        return f
    except Exception:
        for alt in ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]:
            if os.path.exists(alt):
                return ImageFont.truetype(alt, int(size * 0.8))
        return ImageFont.load_default()


# ---------- 1. Nuevo trabajo ----------
def new_job(spec):
    """spec = {slug,title,yt_title,hook,sections:[{title,paragraphs:[...],queries:[...]}],outro_next,tags}"""
    if os.path.exists(JOB):
        shutil.rmtree(JOB)
    os.makedirs(JOB + "/img", exist_ok=True)
    os.makedirs(JOB + "/aud", exist_ok=True)
    os.makedirs(JOB + "/frm", exist_ok=True)
    os.makedirs(JOB + "/seg", exist_ok=True)
    json.dump(spec, open(JOB + "/spec.json", "w"), ensure_ascii=False, indent=1)
    words = sum(len(p.split()) for s in spec["sections"] for p in s["paragraphs"])
    _save({"stage": "setup", "words": words, "created": time.time()})
    return f"trabajo creado: {spec['slug']} ({words} palabras, {len(spec['sections'])} secciones)"


# ---------- 2. Imágenes reales de Wikimedia Commons ----------
def _api(params):
    q = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    return json.load(urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=30))


def _strip(h):
    return re.sub(r"<[^>]+>", "", h or "").strip()


def wm_search(query, n=6):
    d = _api({"action": "query", "format": "json", "generator": "search", "gsrsearch": query + " filetype:bitmap",
              "gsrnamespace": 6, "gsrlimit": 25, "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime",
              "iiurlwidth": 1920})
    out = []
    for p in sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        lic = _strip(md.get("LicenseShortName", {}).get("value", ""))
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if ii.get("width", 0) < 1200 or ii.get("height", 0) < 700:
            continue
        if ii.get("width", 1) / max(ii.get("height", 1), 1) < 1.0:
            continue  # solo horizontales
        if not any(lic.lower().startswith(k) for k in LIC_OK):
            continue
        t = p["title"].lower()
        if any(b in t for b in BLOCK):
            continue
        art = " ".join(_strip(md.get("Artist", {}).get("value", "")).split()) or "autor desconocido"
        out.append({"title": p["title"], "url": ii.get("thumburl") or ii["url"], "lic": lic, "author": art[:60]})
        if len(out) >= n:
            break
    return out


def stage_images(budget):
    spec = json.load(open(JOB + "/spec.json"))
    st = _st()
    imgs = st.get("imgs", {})
    used = {x["title"] for v in imgs.values() for x in v}
    t0 = time.time()
    for i, s in enumerate(spec["sections"]):
        k = str(i)
        if k in imgs:
            continue
        if time.time() - t0 > budget:
            break
        got = []
        qs = s.get("queries", [])
        cap = max(2, -(-6 // max(1, len(qs))))
        for q in qs:
            nq = 0
            try:
                for c in wm_search(q, n=cap + 3):
                    if nq >= cap:
                        break
                    if c["title"] in used:
                        continue
                    fn = f"{JOB}/img/{i:02d}_{len(got):02d}.jpg"
                    try:
                        data = urllib.request.urlopen(urllib.request.Request(c["url"], headers=UA), timeout=30).read()
                        open(fn, "wb").write(data)
                        from PIL import Image
                        Image.open(fn).convert("RGB")
                    except Exception:
                        continue
                    c["file"] = fn
                    got.append(c)
                    nq += 1
                    used.add(c["title"])
                    if len(got) >= 6:
                        break
            except Exception:
                continue
            if len(got) >= 6:
                break
        imgs[k] = got
        st["imgs"] = imgs
        _save(st)
    if len(imgs) == len(spec["sections"]):
        st["stage"] = "tts"
        _save(st)
    return f"imágenes: {sum(len(v) for v in imgs.values())} en {len(imgs)}/{len(spec['sections'])} secciones"


# ---------- 3. Voz ----------
def _tts(text, out):
    clean = re.sub(r"[*_#«»\"]", "", text)
    r = subprocess.run([sys.executable, "-m", "piper", "-m", VOZ, "-s", "1", "--length-scale", "1.08",
                        "--sentence-silence", "0.45", "-f", out], input=clean, capture_output=True, text=True, timeout=170)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-400:])


def _wavdur(p):
    w = wave.open(p)
    return w.getnframes() / w.getframerate()


def stage_tts(budget):
    spec = json.load(open(JOB + "/spec.json"))
    st = _st()
    t0 = time.time()
    items = [("intro", spec.get("hook", ""))]
    for i, s in enumerate(spec["sections"]):
        for j, p in enumerate(s["paragraphs"]):
            items.append((f"{i:02d}_{j:02d}", p))
    items.append(("outro", spec.get("outro", "")))
    for key, text in items:
        out = f"{JOB}/aud/{key}.wav"
        if os.path.exists(out) or not text.strip():
            continue
        if time.time() - t0 > budget:
            continue
        _tts(text, out)
    left = [k for k, t in items if t.strip() and not os.path.exists(f"{JOB}/aud/{k}.wav")]
    if not left:
        st["stage"] = "frames"
        _save(st)
    return f"voz: {len(items) - len(left)}/{len(items)} trozos"


# ---------- 4. Fotogramas ----------
def _cover(im):
    from PIL import Image
    r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def _wrap(draw, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def card(title, sub, out, kicker=""):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), CREMA)
    d = ImageDraw.Draw(im)
    for k, (col, y0) in enumerate([((183, 169, 140), 760), ((169, 165, 133), 820), (SALVIA, 880), ((79, 113, 72), 950), ((61, 90, 56), 1010)]):
        pts = [(x, y0 + 28 * math.sin(x / 260 + k * 1.7)) for x in range(0, W + 41, 40)]
        d.polygon(pts + [(W, H), (0, H)], fill=col)
    d.ellipse((1440, 520, 1680, 760), fill=TIERRA)
    y = 230
    if kicker:
        f = font(42, bold=False)
        d.text((180, y), kicker.upper(), font=f, fill=(90, 74, 56))
        y += 80
    f = font(110)
    for ln in _wrap(d, title, f, 1250)[:3]:
        d.text((180, y), ln, font=f, fill=OSCURO)
        y += 125
    if sub:
        f2 = font(56, italic=True, bold=False)
        for ln in _wrap(d, sub, f2, 1250)[:2]:
            d.text((180, y + 20), ln, font=f2, fill=(90, 74, 56))
            y += 70
    im.save(out, quality=92)


def photo(src, out, credit):
    from PIL import Image, ImageDraw
    im = _cover(Image.open(src).convert("RGB"))
    credit = " ".join(credit.split())
    d = ImageDraw.Draw(im, "RGBA")
    f = font(24, bold=False)
    tw = d.textlength(credit, font=f)
    d.rectangle((W - tw - 40, H - 46, W, H), fill=(0, 0, 0, 110))
    d.text((W - tw - 20, H - 40), credit, font=f, fill=(240, 235, 225, 255))
    im.save(out, quality=90)


def stage_frames(budget):
    spec = json.load(open(JOB + "/spec.json"))
    st = _st()
    t0 = time.time()
    card(spec["title"], "Belleza Ancestral · Belleza de siempre, hecha en casa", JOB + "/frm/intro.jpg")
    card("Gracias por acompañarme", spec.get("outro_next", "Suscríbete para el próximo ritual"), JOB + "/frm/outro.jpg", "Belleza Ancestral")
    for i, s in enumerate(spec["sections"]):
        c = f"{JOB}/frm/{i:02d}_card.jpg"
        if not os.path.exists(c):
            card(s["title"], s.get("sub", ""), c, f"Parte {i + 1}" if not s.get("kicker") else s["kicker"])
        for j, im in enumerate(st["imgs"].get(str(i), [])):
            o = f"{JOB}/frm/{i:02d}_{j:02d}.jpg"
            if not os.path.exists(o):
                photo(im["file"], o, f"Foto: {im['author'][:40]} · {im['lic']} · Wikimedia Commons")
            if time.time() - t0 > budget:
                return "fotogramas: a medias"
    st["stage"] = "render"
    _save(st)
    return "fotogramas: ok"


# ---------- 5. Montaje ----------
def _concat_wavs(paths, out, gap=0.9):
    w0 = wave.open(paths[0])
    prm = w0.getparams()
    sil = b"\x00" * int(prm.framerate * gap) * prm.sampwidth * prm.nchannels
    o = wave.open(out, "wb")
    o.setparams(prm)
    for p in paths:
        w = wave.open(p)
        o.writeframes(w.readframes(w.getnframes()))
        o.writeframes(sil)
    o.close()
    return _wavdur(out)


def _segment(frames, durs, wav, out):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for fr, du in zip(frames, durs):
            f.write(f"file '{fr}'\nduration {du:.3f}\n")
        f.write(f"file '{frames[-1]}'\n")
    _sh([ff(), "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-vf", "fps=5,format=yuv420p",
         "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "24", "-threads", "1", "-x264-params", "rc-lookahead=4:ref=1:bframes=0", "-c:a", "aac", "-b:a", "160k",
         "-ar", "44100", "-ac", "2", "-shortest", out])


def stage_render(budget):
    spec = json.load(open(JOB + "/spec.json"))
    st = _st()
    t0 = time.time()
    parts = [("intro", ["intro"]), *[(f"{i:02d}", [f"{i:02d}_{j:02d}" for j in range(len(s["paragraphs"]))]) for i, s in enumerate(spec["sections"])], ("outro", ["outro"])]
    for key, auds in parts:
        out = f"{JOB}/seg/{key}.mp4"
        if os.path.exists(out):
            continue
        if time.time() - t0 > budget:
            return f"montaje: {len([x for x in os.listdir(JOB + '/seg') if x.endswith('.mp4')])} partes hechas"
        paths = [f"{JOB}/aud/{a}.wav" for a in auds if os.path.exists(f"{JOB}/aud/{a}.wav")]
        wav = f"{JOB}/seg/{key}.wav"
        dur = _concat_wavs(paths, wav, gap=0.9 if key not in ("intro", "outro") else 1.2)
        if key in ("intro", "outro"):
            frames, durs = [f"{JOB}/frm/{key}.jpg"], [dur + 0.5]
        else:
            ph = sorted(x for x in os.listdir(JOB + "/frm") if x.startswith(key + "_") and not x.endswith("card.jpg"))
            ph = [f"{JOB}/frm/{x}" for x in ph] or [f"{JOB}/frm/{key}_card.jpg"]
            cd = min(7.0, dur * 0.25)
            rest = dur - cd
            n = max(1, round(rest / 11))
            seq = [ph[k % len(ph)] for k in range(n)]
            frames = [f"{JOB}/frm/{key}_card.jpg"] + seq
            durs = [cd] + [rest / n] * n
            durs[-1] += 0.5
        _segment(frames, durs, wav, out)
        os.remove(wav)
    tcur, chapters = 0.0, []
    for key, _ in parts:
        probe = subprocess.run([ff(), "-i", f"{JOB}/seg/{key}.mp4"], capture_output=True, text=True).stderr
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe)
        d = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        if key == "intro":
            chapters.append((0, "Introducción"))
        elif key == "outro":
            chapters.append((tcur, "Despedida"))
        else:
            chapters.append((tcur, spec["sections"][int(key)]["title"]))
        tcur += d
    st["chapters"], st["duration"], st["stage"] = chapters, tcur, "final"
    _save(st)
    return f"montaje: ok ({tcur / 60:.1f} min)"


def _music(out, secs=90, sr=44100):
    import numpy as np
    t = np.arange(int(secs * sr)) / sr
    chords = [[220.0, 277.18, 329.63], [196.0, 246.94, 293.66], [174.61, 220.0, 261.63], [196.0, 246.94, 329.63]]
    sig = np.zeros_like(t)
    seg = secs / len(chords)
    for k, ch in enumerate(chords):
        m = (t >= k * seg) & (t < (k + 1) * seg)
        tt = t[m] - k * seg
        env = np.minimum(1, tt / 4) * np.minimum(1, (seg - tt) / 4)
        for f in ch:
            sig[m] += env * (np.sin(2 * np.pi * f * t[m]) + 0.3 * np.sin(2 * np.pi * f * 2 * t[m])) / len(ch)
    sig = (sig / np.max(np.abs(sig)) * 0.6 * 32767).astype("int16")
    w = wave.open(out, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(sig.tobytes())
    w.close()


def stage_final(budget):
    spec = json.load(open(JOB + "/spec.json"))
    st = _st()
    keys = ["intro"] + [f"{i:02d}" for i in range(len(spec["sections"]))] + ["outro"]
    lst = JOB + "/all.txt"
    open(lst, "w").write("".join(f"file '{JOB}/seg/{k}.mp4'\n" for k in keys))
    _sh([ff(), "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", JOB + "/joined.mp4"])
    _music(JOB + "/music.wav")
    _sh([ff(), "-y", "-i", JOB + "/joined.mp4", "-stream_loop", "-1", "-i", JOB + "/music.wav", "-filter_complex",
         "[1:a]volume=0.06,aformat=channel_layouts=stereo[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
         JOB + "/video.mp4"], t=900)
    os.remove(JOB + "/joined.mp4")
    thumb(spec)
    st["stage"], st["size_mb"] = "listo", round(os.path.getsize(JOB + "/video.mp4") / 1e6, 1)
    st["description"] = describe(spec, st)
    _save(st)
    return f"LISTO: {JOB}/video.mp4 ({st['duration'] / 60:.1f} min, {st['size_mb']} MB)"


def thumb(spec):
    from PIL import Image, ImageDraw
    st = _st()
    ts = st["imgs"].get(str(spec.get("thumb_section", 1))) or []
    first = ts[0]["file"] if ts else next((x["file"] for v in st["imgs"].values() for x in v), None)
    im = _cover(Image.open(first).convert("RGB")) if first else Image.new("RGB", (W, H), CREMA)
    im = im.resize((1280, 720))
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 760, 720), fill=(238, 221, 192, 225))
    f = font(92)
    y = 150
    for ln in _wrap(d, spec.get("thumb_text", spec["title"]), f, 660)[:4]:
        d.text((50, y), ln, font=f, fill=OSCURO)
        y += 104
    d.text((50, 600), "BELLEZA ANCESTRAL", font=font(38, bold=False), fill=(90, 74, 56))
    im.save(JOB + "/thumb.jpg", quality=90)


def _ts(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def describe(spec, st):
    caps = "\n".join(f"{_ts(t)} {n}" for t, n in st["chapters"])
    cred = {}
    for v in st["imgs"].values():
        for x in v:
            cred.setdefault(x["lic"], set()).add(x["author"])
    credits = "\n".join(f"{k}: {', '.join(sorted(a))}" for k, a in cred.items())
    return (f"{spec['description']}\n\n⏱️ CAPÍTULOS\n{caps}\n\n"
            "🔔 Suscríbete a Belleza Ancestral para descubrir nuevos rituales cada semana.\n"
            f"💬 {spec.get('question', '¿Cuál es tu ritual? Cuéntanoslo en los comentarios.')}\n"
            f"{spec.get('outro_next', '')}\n\n"
            "🎙️ Voz narradora generada con inteligencia artificial: modelo Piper «es_ES-sharvard-medium» (licencia CC BY 3.0, corpus Sharvard, Universidad de Edimburgo).\n"
            "🎵 Música ambiental creada por Belleza Ancestral.\n"
            f"📷 Imágenes: Wikimedia Commons. Autores y licencias:\n{credits}\n\n"
            f"⚠️ Aviso: {spec.get('disclaimer', 'este vídeo comparte rituales tradicionales con fines divulgativos. No son tratamientos médicos ni sustituyen el consejo de un profesional. Haz siempre una prueba previa en la piel y, ante cualquier problema, consulta a un especialista.')}\n\n"
            f"{' '.join(spec.get('hashtags', ['#BellezaAncestral']))}")[:4900]


# ---------- Bucle ----------
def step(budget=140):
    st = _st()
    stg = st.get("stage")
    if stg is None:
        return "No hay trabajo. Llama a new_job(spec)."
    if stg == "setup":
        setup(); st["stage"] = "images"; _save(st); return "setup ok"
    if stg == "images":
        return stage_images(budget)
    if stg == "tts":
        return stage_tts(budget)
    if stg == "frames":
        return stage_frames(budget)
    if stg == "render":
        return stage_render(budget)
    if stg == "final":
        return stage_final(budget)
    if stg == "listo":
        return f"LISTO: {JOB}/video.mp4 ({st['duration'] / 60:.1f} min, {st['size_mb']} MB)"
    return stg
