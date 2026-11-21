"""Estudio Arte y Bisutería: vídeo vertical para TikTok (borrador en @estudioarteybisuteria).
Uso en GitHub: flujo eab-tiktok.yml (VIDEO=pulsera, DRY_RUN=1 para revisar sin enviar)."""
import math, os, subprocess, wave, json, sys, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
CREMA = (247, 240, 230); ORO = (196, 154, 60); CIRUELA = (74, 44, 64)
ROSA = (214, 140, 150); TURQ = (70, 160, 160); LILA = (150, 120, 190)
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
OUT = os.environ.get("OUT_DIR", "/tmp/eab")
os.makedirs(OUT, exist_ok=True)
VOZ = os.path.join(OUT, "voz.onnx")
_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx"
if not os.path.exists(VOZ):
    urllib.request.urlretrieve(_BASE, VOZ); urllib.request.urlretrieve(_BASE + ".json", VOZ + ".json")
AQUI = os.path.dirname(os.path.abspath(__file__))
GUIONES = json.load(open(os.path.join(AQUI, "eab_guiones.json"), encoding="utf-8"))
POR_ID = {g["id"]: g for g in GUIONES}
ESTADO_F = os.path.join(AQUI, "eab_estado.json")
estado = json.load(open(ESTADO_F)) if os.path.exists(ESTADO_F) else {"siguiente": 0, "hechos": {}}
from datetime import datetime
from zoneinfo import ZoneInfo
ahora = datetime.now(ZoneInfo("Europe/Madrid"))
TURNO = ahora.strftime("%Y-%m-%d") + ("-m" if ahora.hour < 15 else "-t")
VIDEO = (os.environ.get("VIDEO") or "").strip()
AUTO = not VIDEO
if AUTO:
    if TURNO in estado["hechos"]:
        print(f"El turno {TURNO} ya está hecho ({estado['hechos'][TURNO]}). No hago nada."); sys.exit(0)
    VIDEO = GUIONES[estado["siguiente"] % len(GUIONES)]["id"]
if VIDEO not in POR_ID:
    sys.exit(f"Vídeo desconocido: {VIDEO}. Hay: {', '.join(POR_ID)}")
ESCENAS = POR_ID[VIDEO]["escenas"]
TEXTOS = {g["id"]: g["texto"] for g in GUIONES}
COLS = [ROSA, ORO, TURQ, LILA]


def f(sz, b=True):
    return ImageFont.truetype(BOLD if b else REG, sz)


def texto_centrado(d, y, txt, font, fill, maxw=940):
    palabras, lineas, l = txt.split(), [], ""
    for p in palabras:
        t = (l + " " + p).strip()
        if d.textlength(t, font=font) > maxw and l:
            lineas.append(l); l = p
        else:
            l = t
    lineas.append(l)
    for ln in lineas:
        w = d.textlength(ln, font=font)
        d.text(((W - w) / 2, y), ln, font=font, fill=fill)
        y += font.size + 18
    return y


def cuenta(d, x, y, r, col):
    d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=CIRUELA, width=4)
    d.ellipse([x - r * .45, y - r * .55, x - r * .05, y - r * .2], fill=(255, 255, 255))


def pulsera(d, cx, cy, R, n=16, hueco=False):
    for i in range(n):
        if hueco and i in (0, 1):
            continue
        a = 2 * math.pi * i / n - math.pi / 2
        cuenta(d, cx + R * math.cos(a), cy + R * math.sin(a), 52, COLS[i % 4])


def flecha(d, x1, y1, x2, y2, col=CIRUELA, w=10):
    d.line([x1, y1, x2, y2], fill=col, width=w)
    a = math.atan2(y2 - y1, x2 - x1)
    for s in (2.6, -2.6):
        d.line([x2, y2, x2 + 40 * math.cos(a + s), y2 + 40 * math.sin(a + s)], fill=col, width=w)


def dibujo(d, clave):
    cy = 960
    if clave == "gancho":
        pulsera(d, W / 2, cy, 280, hueco=True)
        d.line([W / 2 - 50, cy - 370, W / 2 + 70, cy - 200], fill=(200, 40, 40), width=16)
        d.line([W / 2 + 70, cy - 370, W / 2 - 50, cy - 200], fill=(200, 40, 40), width=16)
    elif clave == "estirar":
        pts = [(120 + i * 42, cy + 45 * math.sin(i / 2)) for i in range(21)]
        d.line(pts, fill=CIRUELA, width=14)
        flecha(d, 300, cy + 140, 140, cy + 140); flecha(d, 780, cy + 140, 940, cy + 140)
        d.text((W / 2 - 150, cy - 160), "hilo elástico", font=f(56, False), fill=CIRUELA)
    elif clave == "cuentas":
        d.rectangle([140, cy - 260, 940, cy - 180], fill=(255, 250, 240), outline=CIRUELA, width=4)
        for i in range(26):
            x = 160 + i * 30
            d.line([x, cy - 260, x, cy - (215 if i % 5 else 195)], fill=CIRUELA, width=3)
        d.text((W / 2 - 70, cy - 150), "25 cm", font=f(56), fill=CIRUELA)
        d.line([120, cy + 80, 960, cy + 80], fill=CIRUELA, width=8)
        for i in range(8):
            cuenta(d, 190 + i * 100, cy + 80, 46, COLS[i % 4])
    elif clave == "nudo":
        # dos vueltas entrelazadas (nudo de cirujano) y los cuatro cabos
        d.ellipse([W/2-170, cy-110, W/2+20, cy+110], outline=CIRUELA, width=14)
        d.ellipse([W/2-20, cy-110, W/2+170, cy+110], outline=CIRUELA, width=14)
        d.ellipse([W/2-150, cy-80, W/2+150, cy+80], outline=ORO, width=10)
        for (x1,y1,x2,y2) in [(130,cy-260,W/2-150,cy-60),(130,cy+260,W/2-150,cy+60),
                              (950,cy-260,W/2+150,cy-60),(950,cy+260,W/2+150,cy+60)]:
            d.line([x1,y1,x2,y2], fill=CIRUELA, width=14)
        d.ellipse([W/2-90, cy+190, W/2+90, cy+370], fill=ORO)
        d.text((W/2-52, cy+225), "x2", font=f(90), fill=(255, 255, 255))
    elif clave == "pegamento":
        d.rounded_rectangle([440, cy - 340, 640, cy - 120], 30, fill=(240, 240, 250), outline=CIRUELA, width=6)
        d.polygon([(480, cy - 120), (600, cy - 120), (540, cy - 40)], fill=CIRUELA)
        d.ellipse([515, cy - 10, 565, cy + 60], fill=(120, 190, 230))
        cuenta(d, 540, cy + 220, 110, ROSA)
        d.line([200, cy + 220, 430, cy + 220], fill=CIRUELA, width=10)
        d.line([650, cy + 220, 880, cy + 220], fill=CIRUELA, width=10)
    elif clave == "final":
        pulsera(d, W / 2, cy, 280)
        d.text((W / 2 - 60, cy - 70), "✓", font=f(140), fill=ORO)
    else:
        icono(d, clave, cy)


def alicate(d, cx, cy, punta):
    # mangos
    d.line([cx - 40, cy + 40, cx - 170, cy + 380], fill=ROSA, width=46)
    d.line([cx + 40, cy + 40, cx + 170, cy + 380], fill=ROSA, width=46)
    d.ellipse([cx - 45, cy - 5, cx + 45, cy + 85], fill=CIRUELA)
    d.ellipse([cx - 15, cy + 25, cx + 15, cy + 55], fill=ORO)
    if punta == "redondo":
        for s in (-1, 1):
            d.polygon([(cx + s * 8, cy + 20), (cx + s * 40, cy + 20), (cx + s * 14, cy - 300), (cx + s * 6, cy - 300)], fill=(150, 150, 160))
            d.ellipse([cx + s * 10 - 12, cy - 318, cx + s * 10 + 12, cy - 294], fill=(150, 150, 160))
    elif punta == "plano":
        for s in (-1, 1):
            d.polygon([(cx + s * 4, cy + 20), (cx + s * 44, cy + 20), (cx + s * 22, cy - 300), (cx + s * 2, cy - 300)], fill=(150, 150, 160))
    else:  # corte
        for s in (-1, 1):
            d.polygon([(cx + s * 2, cy + 20), (cx + s * 60, cy + 10), (cx + s * 40, cy - 120), (cx + s * 2, cy - 170)], fill=(150, 150, 160))
        d.line([cx, cy - 170, cx, cy + 10], fill=CIRUELA, width=4)


def anilla(d, cx, cy, r, modo):
    if modo == "cerrada":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ORO, width=30)
    elif modo == "mal":  # separada hacia fuera
        d.arc([cx - r, cy - r, cx + r, cy + r], 290, 250, fill=ORO, width=30)
        d.line([cx + 30, cy - r + 10, cx + 110, cy - r - 60], fill=ORO, width=30)
        d.line([cx - 30, cy - r + 10, cx - 110, cy - r - 60], fill=ORO, width=30)
    else:  # bien: girada (un lado delante, otro detrás)
        d.arc([cx - r, cy - r, cx + r, cy + r], 280, 260, fill=ORO, width=30)
        d.arc([cx - r + 20, cy - r - 40, cx + r + 20, cy + r - 40], 255, 285, fill=(150, 120, 40), width=30)


def icono(d, clave, cy):
    cx = W / 2
    if clave.startswith("num:"):
        t = clave[4:]
        tam = 200 if len(t) <= 6 else 140
        w = d.textlength(t, font=f(tam))
        d.rounded_rectangle([cx - w / 2 - 60, cy - tam * .75, cx + w / 2 + 60, cy + tam * .75], 60, fill=CIRUELA)
        d.text((cx - w / 2, cy - tam * .6), t, font=f(tam), fill=ORO)
    elif clave.startswith("alicate_"):
        alicate(d, cx, cy - 60, clave.split("_")[1])
    elif clave.startswith("anilla_"):
        anilla(d, cx, cy, 180, clave.split("_")[1])
        if clave == "anilla_mal":
            d.text((cx + 200, cy + 120), "✗", font=f(150), fill=(200, 40, 40))
        elif clave == "anilla_bien":
            d.text((cx + 200, cy + 120), "✓", font=f(150), fill=(40, 150, 80))
    elif clave == "joyas":
        pulsera(d, cx - 170, cy + 60, 150, n=12)
        for x in (cx + 200, cx + 340):
            d.arc([x - 40, cy - 330, x + 40, cy - 250], 180, 360, fill=CIRUELA, width=10)
            d.line([x + 40, cy - 290, x + 40, cy - 230], fill=CIRUELA, width=10)
            cuenta(d, x + 40, cy - 180, 46, TURQ)
        for i in range(9):
            a = math.pi * (0.15 + 0.7 * i / 8)
            cuenta(d, cx + 270 + 160 * math.cos(a), cy + 120 + 160 * math.sin(a) - 40, 24, COLS[i % 4])
    elif clave == "pendiente":
        d.arc([cx - 70, cy - 330, cx + 70, cy - 190], 180, 360, fill=CIRUELA, width=14)
        d.line([cx + 70, cy - 260, cx + 70, cy - 120], fill=CIRUELA, width=14)
        d.line([cx - 70, cy - 260, cx - 90, cy - 200], fill=CIRUELA, width=14)
        d.ellipse([cx + 40, cy - 140, cx + 100, cy - 80], outline=ORO, width=14)
        d.line([cx + 70, cy - 80, cx + 70, cy + 20], fill=ORO, width=10)
        cuenta(d, cx + 70, cy + 110, 90, ROSA)
    elif clave == "pin":
        d.rectangle([cx - 70, cy + 240, cx + 70, cy + 260], fill=(150, 150, 160))
        d.line([cx, cy + 240, cx, cy - 300], fill=(150, 150, 160), width=14)
        cuenta(d, cx, cy + 150, 80, TURQ)
    elif clave == "chafa":
        d.line([120, cy - 40, 960, cy - 40], fill=CIRUELA, width=8)
        d.arc([780, cy - 140, 980, cy + 60], 270, 90, fill=CIRUELA, width=8)
        d.line([120, cy + 60, 880, cy + 60], fill=CIRUELA, width=8)
        d.rounded_rectangle([560, cy - 80, 720, cy + 100], 30, fill=(170, 170, 180), outline=CIRUELA, width=5)
        anilla(d, 1000, cy - 40, 60, "cerrada")
        d.text((560, cy + 140), "chafa", font=f(56, False), fill=CIRUELA)
    elif clave == "hilos":
        for k, (col, nom) in enumerate([(ROSA, "elástico"), (CIRUELA, "acero"), (ORO, "encerado")]):
            y = cy - 220 + k * 220
            d.line([(140 + i * 40, y + 30 * math.sin(i / 2 + k)) for i in range(15)], fill=col, width=18)
            d.text((740, y - 30), nom, font=f(52, False), fill=CIRUELA)
    elif clave == "cinta":
        d.ellipse([cx - 230, cy - 230, cx + 230, cy + 230], outline=(240, 200, 80), width=70)
        for k in range(36):
            a = 2 * math.pi * k / 36
            r1, r2 = 195, 225 if k % 3 else 245
            d.line([cx + r1 * math.cos(a), cy + r1 * math.sin(a), cx + r2 * math.cos(a), cy + r2 * math.sin(a)], fill=CIRUELA, width=4)
        d.text((cx - 110, cy - 50), "15 cm", font=f(80), fill=CIRUELA)
    elif clave == "collar":
        for i in range(19):
            a = math.pi * (0.05 + 0.9 * i / 18)
            cuenta(d, cx + 330 * math.cos(a), cy - 200 + 380 * math.sin(a), 36, COLS[i % 4])
        cuenta(d, cx, cy + 250, 70, ORO)
    elif clave == "cuentas_fila":
        d.line([100, cy, 980, cy], fill=CIRUELA, width=8)
        for i in range(9):
            cuenta(d, 150 + i * 98, cy, 46, COLS[i % 4])
    elif clave == "caja":
        d.rounded_rectangle([140, cy - 300, 940, cy + 300], 30, fill=(255, 250, 240), outline=CIRUELA, width=10)
        for k in range(1, 4):
            d.line([140 + k * 200, cy - 300, 140 + k * 200, cy + 300], fill=CIRUELA, width=8)
        d.line([140, cy, 940, cy], fill=CIRUELA, width=8)
        for k in range(8):
            x0, y0 = 140 + (k % 4) * 200, cy - 300 + (k // 4) * 300
            for j in range(3):
                cuenta(d, x0 + 55 + (j % 2) * 80, y0 + 90 + (j // 2) * 110 + (j % 2) * 20, 30, COLS[k % 4])
    elif clave == "agua_no":
        d.polygon([(cx, cy - 300), (cx - 170, cy + 20), (cx + 170, cy + 20)], fill=(120, 190, 230))
        d.ellipse([cx - 170, cy - 140, cx + 170, cy + 200], fill=(120, 190, 230))
        d.line([cx - 260, cy - 260, cx + 260, cy + 260], fill=(200, 40, 40), width=36)
    elif clave == "paleta":
        cuenta(d, cx - 160, cy, 200, ROSA); cuenta(d, cx + 170, cy - 60, 130, LILA); cuenta(d, cx + 160, cy + 190, 70, ORO)
    elif clave == "tijeras":
        d.text((cx - 200, cy - 260), "✂", font=f(400), fill=CIRUELA)
    elif clave == "check":
        d.ellipse([cx - 240, cy - 240, cx + 240, cy + 240], fill=(60, 150, 90))
        d.text((cx - 120, cy - 190), "✓", font=f(330), fill=(255, 255, 255))
    elif clave == "cruz":
        d.ellipse([cx - 240, cy - 240, cx + 240, cy + 240], fill=(200, 60, 60))
        d.text((cx - 110, cy - 190), "✗", font=f(330), fill=(255, 255, 255))
    elif clave == "pulsera":
        pulsera(d, cx, cy, 280)
    elif clave == "letras":
        d.line([100, cy, 980, cy], fill=CIRUELA, width=8)
        for i, l in enumerate("ANALU"):
            x = 220 + i * 160
            d.rounded_rectangle([x - 65, cy - 65, x + 65, cy + 65], 20, fill=(255, 255, 255), outline=CIRUELA, width=5)
            d.text((x - d.textlength(l, font=f(80)) / 2, cy - 48), l, font=f(80), fill=CIRUELA)
    elif clave == "regalo":
        d.rectangle([cx - 230, cy - 120, cx + 230, cy + 260], fill=ROSA)
        d.rectangle([cx - 260, cy - 200, cx + 260, cy - 100], fill=(230, 160, 170))
        d.rectangle([cx - 35, cy - 200, cx + 35, cy + 260], fill=ORO)
        d.ellipse([cx - 160, cy - 330, cx - 10, cy - 200], outline=ORO, width=30)
        d.ellipse([cx + 10, cy - 330, cx + 160, cy - 200], outline=ORO, width=30)
    else:
        raise SystemExit(f"Icono desconocido: {clave}")


def cartel(clave, titulo, sub):
    im = Image.new("RGB", (W, H), CREMA)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 300], fill=CIRUELA)
    t = "Estudio Arte y Bisutería"
    d.text(((W - d.textlength(t, font=f(52))) / 2, 190), t, font=f(52), fill=ORO)
    texto_centrado(d, 350, titulo, f(84), CIRUELA)
    dibujo(d, clave)
    texto_centrado(d, 1340, sub, f(60, False), CIRUELA, maxw=900)
    d.text((W / 2 - 230, 1500), "@estudioarteybisuteria", font=f(40, False), fill=ORO)
    return im


def musica(seg, ruta):
    sr = 22050; t = np.arange(int(seg * sr)) / sr
    acordes = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    y = np.zeros_like(t)
    for i, ac in enumerate(acordes * int(seg // 8 + 1)):
        a, b = i * 2.0, i * 2.0 + 2.2
        m = (t >= a) & (t < b)
        env = np.sin(np.pi * (t[m] - a) / 2.2)
        for fr in ac:
            y[m] += env * np.sin(2 * np.pi * fr * t[m]) / 3
    y = (y / np.abs(y).max() * 0.12 * 32767).astype(np.int16)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())


partes = []
for i, (clave, tit, sub, voz) in enumerate(ESCENAS):
    png, wav, mp4 = f"{OUT}/{i}.png", f"{OUT}/{i}.wav", f"{OUT}/{i}.mp4"
    cartel(clave, tit, sub).save(png)
    subprocess.run(["python3", "-m", "piper", "-m", VOZ, "-f", wav, "--length-scale", "1.0", "--speaker", "1"],
                   input=voz.encode(), check=True, capture_output=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", wav])) + 0.5
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", wav,
                    "-vf", f"zoompan=z='1+0.0006*on':d={int(dur*30)}:s={W}x{H}:fps=30",
                    "-t", f"{dur}", "-af", "apad", "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", mp4], check=True)
    partes.append(mp4)

with open(f"{OUT}/lista.txt", "w") as fl:
    fl.writelines(f"file '{p}'\n" for p in partes)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{OUT}/lista.txt",
                "-c", "copy", f"{OUT}/voz.mp4"], check=True)
total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                       "-of", "csv=p=0", f"{OUT}/voz.mp4"]))
musica(total + 1, f"{OUT}/musica.wav")
final = os.path.join(OUT, f"eab_{VIDEO}.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/voz.mp4", "-i", f"{OUT}/musica.wav",
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-vf", "scale=720:1280", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", final], check=True)
print(json.dumps({"duracion": round(total, 1), "MB": round(os.path.getsize(final) / 1e6, 2)}))

if os.environ.get("DRY_RUN", "0") != "1":
    os.environ["TT_CUENTA"] = "eab"
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tiktok_api
    pid = tiktok_api.subir_borrador(final)
    print("Borrador enviado a @estudioarteybisuteria:", pid)
    if AUTO:
        estado["hechos"][TURNO] = VIDEO
        estado["siguiente"] = estado["siguiente"] + 1
        estado["hechos"] = dict(sorted(estado["hechos"].items())[-60:])
        json.dump(estado, open(ESTADO_F, "w"), ensure_ascii=False, indent=1)
resumen = os.environ.get("GITHUB_STEP_SUMMARY")
if resumen:
    with open(resumen, "a") as fh:
        fh.write(f"## Estudio Arte y Bisutería · {VIDEO}\n\nTexto para pegar en TikTok:\n\n{TEXTOS.get(VIDEO, '')}\n")
