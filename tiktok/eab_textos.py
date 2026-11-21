"""Página con los textos de TikTok de Estudio Arte y Bisutería para copiar desde el móvil.
Crea eab/textos.html (se ve en https://jmausina.github.io/casaclic/eab/textos.html)."""
import html, json, os

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
guiones = {g["id"]: g for g in json.load(open(os.path.join(AQUI, "eab_guiones.json"), encoding="utf-8"))}
estado = json.load(open(os.path.join(AQUI, "eab_estado.json"), encoding="utf-8"))
hechos = sorted(estado.get("hechos", {}).items(), reverse=True)[:8]

bloques = []
for n, (turno, vid) in enumerate(hechos):
    dia, momento = turno[:10], ("mañana" if turno.endswith("-m") else "tarde")
    d, m, a = dia[8:10], dia[5:7], dia[:4]
    texto = guiones.get(vid, {}).get("texto", "")
    bloques.append(f"""<div class="caja">
<p class="fecha">{d}/{m}/{a} · {momento}</p>
<p class="texto" id="t{n}">{html.escape(texto)}</p>
<button onclick="copiar('t{n}', this)">Copiar texto</button>
</div>""")

pagina = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Textos TikTok · Estudio Arte y Bisutería</title>
<style>
body{{font-family:system-ui,sans-serif;background:#f7f0e6;color:#4a2c40;margin:0;padding:16px}}
h1{{font-size:22px;margin:4px 0 4px}} .nota{{font-size:15px;margin:0 0 16px}}
.caja{{background:#fff;border:2px solid #c49a3c;border-radius:14px;padding:14px;margin-bottom:14px}}
.fecha{{font-weight:bold;margin:0 0 8px}} .texto{{font-size:17px;line-height:1.4;margin:0 0 12px}}
button{{background:#4a2c40;color:#fff;border:0;border-radius:10px;padding:12px 18px;font-size:17px;width:100%}}
</style></head><body>
<h1>Textos para TikTok</h1>
<p class="nota">El de arriba es el último vídeo. Pulsa «Copiar texto» y pégalo en el borrador de TikTok.</p>
{''.join(bloques) or '<p>Todavía no hay vídeos.</p>'}
<script>
function copiar(id, b){{navigator.clipboard.writeText(document.getElementById(id).innerText).then(function(){{b.innerText='¡Copiado!';setTimeout(function(){{b.innerText='Copiar texto'}},2000)}})}}
</script>
</body></html>
"""
os.makedirs(os.path.join(RAIZ, "eab"), exist_ok=True)
open(os.path.join(RAIZ, "eab", "textos.html"), "w", encoding="utf-8").write(pagina)
print("eab/textos.html con", len(bloques), "textos")
