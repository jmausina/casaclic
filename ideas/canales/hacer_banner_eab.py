# Banner de YouTube de Estudio Arte y Bisutería (2560x1440). Crea ideas/canales/eab_banner.png
import math, os
from PIL import Image, ImageDraw, ImageFont
W, H = 2560, 1440
ORO = (196, 154, 60); CIR = (74, 44, 64); CREMA = (247, 240, 230)
COLS = [(214, 140, 150), ORO, (70, 160, 160), (150, 120, 190)]
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
im = Image.new("RGB", (W, H), CIR); d = ImageDraw.Draw(im)
def cuenta(x, y, r, c):
    d.ellipse([x - r, y - r, x + r, y + r], fill=c, outline=(50, 28, 44), width=3)
    d.ellipse([x - r * .45, y - r * .55, x - r * .05, y - r * .2], fill=(255, 255, 255))
for k, (y0, amp) in enumerate([(540, 40), (900, -40)]):
    for i in range(40):
        cuenta(520 + i * 1520 / 39, y0 + amp * math.sin(math.pi * i / 39), 17, COLS[(i + 2 * k) % 4])
def c(t, y, f, col):
    d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill=col)
c("Estudio Arte y Bisutería", 600, ImageFont.truetype(B, 96), ORO)
c("Bisutería fácil desde casa · Tutoriales paso a paso", 735, ImageFont.truetype(R, 50), CREMA)
c("Nuevos vídeos cada semana", 805, ImageFont.truetype(B, 40), COLS[0])
im.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "eab_banner.png"))
print("Banner hecho")
