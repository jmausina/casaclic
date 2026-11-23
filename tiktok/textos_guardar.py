"""Guarda el texto de TikTok de cada borrador para la página https://jmausina.github.io/casaclic/textos.html
Cada cuenta tiene su propio archivo (así dos robots a la vez no chocan): tiktok/textos_<cuenta>.json"""
import json, os, time

AQUI = os.path.dirname(os.path.abspath(__file__))


def guardar(cuenta, texto, maximo=20):
    ruta = os.path.join(AQUI, f"textos_{cuenta}.json")
    try:
        lista = json.load(open(ruta, encoding="utf-8"))
    except Exception:
        lista = []
    os.environ.setdefault("TZ", "Europe/Madrid")
    try:
        time.tzset()
    except Exception:
        pass
    lista.insert(0, {"fecha": time.strftime("%Y-%m-%d %H:%M"), "texto": texto})
    json.dump(lista[:maximo], open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Texto guardado para la página de textos:", ruta)
