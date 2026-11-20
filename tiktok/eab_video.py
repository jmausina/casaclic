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
VIDEO = (os.environ.get("VIDEO") or "pulsera").strip()
TEXTOS = {"pulsera": "El truco para que tu pulsera elástica no se rompa ✨ Guárdalo 📌 #bisuteria #pulseras #hechoamano #diy #manualidadesfaciles"}

VIDEOS = {"pulsera": [
    ("gancho", "¿Tu pulsera elástica se rompe siempre?", "Hazlo así y no se romperá.",
     "¿Tu pulsera elástica se rompe siempre? Hazlo así y no se romperá."),
    ("estirar", "1. Estira el hilo", "Antes de usarlo. Así no se da de sí.",
     "Primero, estira bien el hilo elástico antes de usarlo. Así no se da de sí después."),
    ("cuentas", "2. Corta 25 cm", "Y mete las cuentas.",
     "Corta unos veinticinco centímetros y mete las cuentas."),
    ("nudo", "3. Nudo de cirujano", "Pasa el hilo dos veces y aprieta fuerte.",
     "Haz un nudo de cirujano: como un nudo normal, pero pasando el hilo dos veces. Aprieta fuerte."),
    ("pegamento", "4. Una gota de pegamento", "Y esconde el nudo dentro de una cuenta.",
     "Pon una gota de pegamento en el nudo y escóndelo dentro de una cuenta."),
    ("final", "¡Lista para durar!", "Guárdalo y sígueme para más trucos.",
     "Guárdalo para tu próxima pulsera, y sígueme para más trucos."),
]}
if VIDEO not in VIDEOS:
    sys.exit(f"Vídeo desconocido: {VIDEO}. Hay: {', '.join(VIDEOS)}")
ESCENAS = VIDEOS[VIDEO]
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
resumen = os.environ.get("GITHUB_STEP_SUMMARY")
if resumen:
    with open(resumen, "a") as fh:
        fh.write(f"## Estudio Arte y Bisutería · {VIDEO}\n\nTexto para pegar en TikTok:\n\n{TEXTOS.get(VIDEO, '')}\n")
