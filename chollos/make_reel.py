# Generador de reels de Chollos de Belleza.
# Uso: python3 make_reel.py deals.json salida.mp4   — deals.json es una lista de {"name","price","old","pct","why"}
# v2 (2026-11-01): portada con gancho, ritmo más rápido y música de fondo propia (sintetizada, sin derechos de autor).
# Si ffmpeg no está instalado, instala imageio-ffmpeg automáticamente.
import json, sys, subprocess, os, wave, struct, math, random
from PIL import Image, ImageDraw, ImageFont
W,H=1080,1920
B=sys.argv[3] if len(sys.argv)>3 else '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def f(s): return ImageFont.truetype(B,s)
def bg():
    im=Image.new('RGB',(W,H)); d=ImageDraw.Draw(im)
    for y in range(H):
        t=y/H; d.line([(0,y),(W,y)],fill=(int(247-30*t),int(198-110*t),int(208-80*t)))
    return im,d
def wrap(d,text,font,maxw):
    words=text.split(); lines=[]; cur=''
    for w in words:
        t=(cur+' '+w).strip()
        if d.textlength(t,font=font)<=maxw: cur=t
        else: lines.append(cur); cur=w
    lines.append(cur); return lines
def block(d,y,text,size,fill='white',maxw=940,gap=18):
    F=f(size)
    for l in wrap(d,text,F,maxw):
        w=d.textlength(l,font=F); d.text(((W-w)/2,y),l,font=F,fill=fill,stroke_width=3 if fill=='white' else 0,stroke_fill=(150,40,80)); y+=size+gap
    return y
def pill(d,y,text,size,bgc=(122,31,61),fg='white'):
    F=f(size); w=d.textlength(text,font=F); pad=40
    d.rounded_rectangle([(W-w)/2-pad,y,(W+w)/2+pad,y+size+50],radius=50,fill=bgc)
    d.text(((W-w)/2,y+22),text,font=F,fill=fg); return y+size+90

def music(path,secs,sr=44100):
    """Música alegre y suave (pop, 112 BPM): acordes C-G-Am-F, bajo, arpegio y percusión ligera."""
    random.seed(7)
    n=int(secs*sr); buf=[0.0]*n
    bpm=112; beat=60/bpm
    prog=[[60,64,67],[55,59,62],[57,60,64],[53,57,60]]  # C G Am F
    hz=lambda m:440*2**((m-69)/12)
    def add(t0,dur,freq,amp,decay,kind='sine'):
        s0=int(t0*sr); ln=int(dur*sr)
        for i in range(ln):
            j=s0+i
            if j>=n: break
            t=i/sr; env=math.exp(-t*decay)*min(1,t*200)
            ph=2*math.pi*freq*t
            v=math.sin(ph)+0.3*math.sin(2*ph) if kind=='sine' else math.sin(ph)
            buf[j]+=amp*env*v
    t=0.0; bar=0
    while t<secs:
        ch=prog[bar%4]
        add(t,beat*4,hz(ch[0]-24),0.22,1.2,'bass')                 # bajo
        for k in range(8):                                        # arpegio en corcheas
            m=ch[k%3]+(12 if k%4==3 else 0)
            add(t+k*beat/2,beat*0.9,hz(m+12),0.07,6)
        for k in range(4):                                        # bombo suave en cada tiempo
            add(t+k*beat,0.18,55,0.35,25,'bass')
        t+=beat*4; bar+=1
    for k in range(int(secs/(beat/2))):                           # hi-hat
        s0=int((k*beat/2+beat/4)*sr)
        for i in range(int(0.03*sr)):
            if s0+i<n: buf[s0+i]+=0.025*(random.random()*2-1)*(1-i/(0.03*sr))
    fade=int(1.5*sr); peak=max(1e-6,max(abs(x) for x in buf))
    with wave.open(path,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        fr=bytearray()
        for i,x in enumerate(buf):
            g=min(1,i/(0.3*sr),(n-i)/fade)
            fr+=struct.pack('<h',int(max(-1,min(1,x/peak*0.6*g))*32767))
        w.writeframes(bytes(fr))

deals=json.load(open(sys.argv[1])); out=sys.argv[2]; tmp=os.path.dirname(os.path.abspath(out))
maxpc=max(int(x['pct'].strip('-%')) for x in deals)
files=[]
# Portada con gancho
im,d=bg(); y=380; y=pill(d,y,'¡NO PAGUES DE MÁS!',64,bgc=(255,243,176),fg=(122,31,61)); y=block(d,y+60,'CHOLLOS DE BELLEZA',110); y=block(d,y+40,'en Amazon HOY',80,fill=(122,31,61)); y=pill(d,y+100,f'Hasta -{maxpc}%',110,bgc=(122,31,61)); block(d,y+40,f'{len(deals)} ofertas que no vas a querer perderte',56,fill=(122,31,61)); p=f'{tmp}/s0.png'; im.save(p); files.append(p)
for i,x in enumerate(deals):
    im,d=bg(); y=420; y=pill(d,y,f'CHOLLO {i+1}/{len(deals)}',60); y=block(d,y+40,x['name'],80); y=block(d,y+40,x['why'],52,fill=(122,31,61))
    F=f(170); w=d.textlength(x['price'],font=F); d.text(((W-w)/2,y+80),x['price'],font=F,fill='white',stroke_width=5,stroke_fill=(150,40,80))
    F2=f(70); w2=d.textlength(x['old'],font=F2); yy=y+300; d.text(((W-w2)/2,yy),x['old'],font=F2,fill=(122,31,61)); d.line([((W-w2)/2-10,yy+40),((W+w2)/2+10,yy+40)],fill=(122,31,61),width=7)
    pill(d,yy+130,x['pct'],90,bgc=(255,243,176),fg=(122,31,61)); p=f'{tmp}/s{i+1}.png'; im.save(p); files.append(p)
im,d=bg(); y=520; y=block(d,y,'Cada día nuevos chollos de belleza',90); y=block(d,y+40,'Gratis en Telegram',70,fill=(122,31,61)); y=pill(d,y+80,'@ChollosBellezaES',80); y=block(d,y+40,'Enlace en el perfil',60); block(d,y+30,'Guárdalo y compártelo con tu amiga',52,fill=(122,31,61)); p=f'{tmp}/sz.png'; im.save(p); files.append(p)
durs=[2.5]+[4]*len(deals)+[4]
lst=f'{tmp}/list.txt'
with open(lst,'w') as fh:
    for fl,du in zip(files,durs): fh.write(f"file '{fl}'\nduration {du}\n")
    fh.write(f"file '{files[-1]}'\n")
total=sum(durs)
aud=f'{tmp}/music.wav'
try:
    music(aud,total); ain=['-i',aud]
except Exception as ex:
    print('music fallback',ex); ain=['-f','lavfi','-t',str(total),'-i','anullsrc=r=44100:cl=stereo']
import shutil
FF=shutil.which('ffmpeg')
if not FF:
    subprocess.run([sys.executable,'-m','pip','install','-q','imageio-ffmpeg'],check=True)
    import imageio_ffmpeg; FF=imageio_ffmpeg.get_ffmpeg_exe()
cmd=[FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',lst]+ain+[
     '-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','ultrafast','-threads','1','-crf','23','-c:a','aac','-b:a','128k','-ar','44100','-ac','2','-t',str(total),'-movflags','+faststart',out]
subprocess.run(cmd,check=True); print('ok',out)
