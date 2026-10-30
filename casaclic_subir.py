# CasaClic - genera el vídeo del día y lo sube a YouTube con el proyecto propio de Google Cloud
# Se ejecuta en GitHub Actions. Las claves vienen de los Secrets del repositorio:
#   YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
# Uso: python casaclic_subir.py <dia> [public|private|unlisted]
import os, sys, subprocess, requests, numpy as np, scipy.io.wavfile as wv, scipy.signal as sg
from PIL import Image, ImageDraw, ImageFont

FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf";FR="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
POOL=[(7424475,"hd_1920_1080_30fps"),(6247900,"hd_720_1280_24fps"),(7424476,"hd_1920_1080_30fps"),(7657139,"hd_720_1280_50fps"),
(7424485,"hd_1920_1080_30fps"),(5674750,"sd_540_960_25fps"),(7424478,"hd_1920_1080_30fps"),(6247885,"hd_720_1280_24fps"),
(6949812,"hd_1920_1080_25fps"),(8870627,"hd_1920_1080_25fps"),(5423971,"hd_720_1280_24fps"),(12691878,"hd_720_1280_60fps"),
(6998497,"hd_720_1280_50fps"),(6998498,"hd_720_1280_50fps"),(7246469,"hd_720_1280_50fps"),(12691875,"hd_720_1280_60fps"),
(5865597,"hd_1920_1080_25fps"),(5865403,"hd_1920_1080_25fps"),(9021882,"hd_1920_1080_25fps"),(6286086,"hd_1920_1080_25fps"),(5866129,"hd_1920_1080_25fps")]
CTA_BG=(5858137,"hd_1920_1080_25fps")
FRASES=[("Comer sano","puede ser fácil"),("Cocinar juntos","sabe mejor"),("Recetas ricas","en minutos"),("Ingredientes","de siempre"),
("Menús organizados","para toda la semana"),("Sin dietas","imposibles"),("Platos llenos","de sabor"),("120 recetas","+ menú de 21 días"),
("Cocina con","cariño"),("Desayunos","que dan energía"),("Cenas ligeras","y deliciosas"),("Postres","más sanos"),
("Comida casera","de verdad"),("Sin complicarte","la vida"),("Ideas nuevas","cada día"),("Toda la familia","a la mesa"),
("Colores","en tu plato"),("Fácil, rico","y saludable"),("Tu cocina,","tu salud"),("Cuídate","sin pasar hambre"),
("Planifica","y ahorra tiempo"),("Recetas","paso a paso"),("Disfruta","cocinando"),("Más sabor,","menos esfuerzo")]
TITULOS=["Comer sano puede ser fácil 🥗","Cocinar en pareja: recetas fáciles y sanas 👩‍🍳👨‍🍳","Ideas de comida sana para toda la semana 📅",
"Recetas caseras ricas en minutos ⏱️","Así se organiza un menú saludable 🍽️","Cocina sana sin complicarte la vida 🏠",
"Platos llenos de color y sabor 🌈","Comida casera para toda la familia 👨‍👩‍👧","Cenas ligeras y deliciosas 🌙",
"Desayunos sanos que dan energía ☀️","Cocinar con cariño: recetas fáciles 💚","Más sabor, menos esfuerzo 🍳",
"Tu cocina, tu salud 🏡","120 recetas + menú de 21 días 🎁"]
TAGS=["recetas fáciles","comida sana","cocina saludable","cocina casera","CasaClic"]

def yt_meta(dia):
    t=TITULOS[(dia-1)%len(TITULOS)]
    d=("🏠 CasaClic: tu cocina, tu salud, a un clic.\n\nIdeas fáciles para cocinar platos sanos, sabrosos y llenos de color, pensados para la vida real.\n\n"
       "🎁 Recetario de 120 recetas + menú organizado de 21 días: https://hotm.io/n7G5jK\n\n"
       "🔔 Suscríbete para más ideas de cocina saludable.\n\nVídeos de stock: Pexels. Música original de CasaClic.\n\n#Shorts #recetasfaciles #comidasana #cocinasaludable #cocinacasera")
    return {"yt_title":t+" #Shorts","yt_description":d}

def _ov(lines,path,cta=False):
    im=Image.new("RGBA",(720,1280),(0,0,0,0));d=ImageDraw.Draw(im)
    if cta:
        d.rectangle([0,0,720,1280],fill=(15,107,92,215));f=ImageFont.truetype(FB,64);fs=ImageFont.truetype(FR,36);y=430
        for t,c in [("CasaClic",(255,255,255)),("tu cocina, tu salud",(255,180,158)),("",None),("Enlace en la",(255,255,255)),("descripción",(255,255,255))]:
            if t: w=d.textlength(t,font=f);d.text(((720-w)/2,y),t,font=f,fill=c)
            y+=80
        t="Suscríbete para más recetas";w=d.textlength(t,font=fs);d.text(((720-w)/2,y+40),t,font=fs,fill=(255,255,255))
    else:
        f=ImageFont.truetype(FB,58);y=860
        for j,t in enumerate(lines):
            w=d.textlength(t,font=f);d.rounded_rectangle([(720-w)/2-22,y-8,(720+w)/2+22,y+72],radius=18,fill=(255,122,89,235) if j else (15,107,92,230))
            d.text(((720-w)/2,y),t,font=f,fill=(255,255,255));y+=92
        d.text((40,70),"CasaClic",font=ImageFont.truetype(FB,30),fill=(255,255,255))
    im.save(path)

def _clip(vid,spec,lines,out,tmp,cta=False):
    src=f"{tmp}/src.mp4";ov=f"{tmp}/ov.png"
    r=requests.get(f"https://videos.pexels.com/video-files/{vid}/{vid}-{spec}.mp4",timeout=90,headers={"User-Agent":"Mozilla/5.0"});r.raise_for_status();open(src,"wb").write(r.content)
    _ov(lines,ov,cta);vf="scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=30"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss","1","-t","5","-i",src,"-i",ov,"-filter_complex",f"[0:v]{vf}[b];[b][1:v]overlay=0:0,format=yuv420p","-an","-c:v","libx264","-preset","ultrafast","-threads","1","-crf","24",out],check=True)
    os.remove(src)

def _lofi(path,secs=45,bpm=92,seed=5):
    SR=44100;rng=np.random.default_rng(seed);beat=60/bpm;bar=4*beat;n=int(SR*(secs+2));out=np.zeros(n)
    mid=lambda m:440*2**((m-69)/12)
    progs=[[[38,53,57,60,64],[43,59,62,65,69],[36,52,55,59,62],[33,48,52,55,59]],[[33,48,52,55,59],[38,53,57,60,64],[43,55,59,62,65],[36,52,55,59,64]],[[41,57,60,64,67],[40,55,59,62,67],[38,53,57,60,64],[43,59,62,65,69]]]
    prog=progs[seed%3]
    def ep(f,dur,amp,dec=2.2):
        t=np.arange(int(SR*dur))/SR;env=np.exp(-dec*t)*np.minimum(1,t*80)
        return amp*(np.sin(2*np.pi*f*t+0.7*np.exp(-3*t)*np.sin(2*np.pi*f*7*t))+0.3*np.sin(2*np.pi*2*f*t))*env
    def add(s,t):
        i=int(t*SR);m=min(len(s),n-i)
        if m>0: out[i:i+m]+=s[:m]
    b=0
    while b*bar<secs+1:
        ch=prog[b%4];t0=b*bar
        for j,m in enumerate(ch[1:]): add(ep(mid(m-12),bar*0.95,0.06),t0+j*0.025)
        for k in [0,1.5,2,3.5]: add(ep(mid(ch[0]),beat*0.9,0.30,3.5),t0+k*beat)
        for k,m in zip([0.5,1.5,2.75,3.25],rng.choice(ch[1:],4)): add(ep(mid(m),beat*0.6,0.045),t0+k*beat)
        for k in range(4):
            t=np.arange(int(SR*.3))/SR;kk=.7*np.sin(2*np.pi*(45+70*np.exp(-28*t))*t)*np.exp(-10*t)
            if k in (0,2): add(kk,t0+k*beat)
            if k==2: add(kk*0.6,t0+(k+0.75)*beat)
            if k in (1,3):
                hl=int(SR*.2);x=np.arange(hl)/SR;add(.22*rng.standard_normal(hl)*np.exp(-x*18)+0.15*np.sin(2*np.pi*190*x)*np.exp(-x*25),t0+k*beat)
            for h in (0,0.25,0.5,0.75):
                hl=int(SR*.03);add((.035 if h in (0.25,0.75) else .022)*rng.standard_normal(hl)*np.exp(-np.arange(hl)/SR*140),t0+(k+h+0.03)*beat)
        b+=1
    bl,al=sg.butter(2,4200/(SR/2));out=sg.lfilter(bl,al,out)
    crack=np.zeros(n);idx=rng.integers(0,n,int(secs*15));crack[idx]=rng.uniform(-.12,.12,len(idx));out+=crack
    out=out[:int(SR*secs)];out/=np.max(np.abs(out))*1.1;wv.write(path,SR,(out*32767).astype(np.int16))

def make_yt(dia,tmp="/tmp/ytc"):
    os.makedirs(tmp,exist_ok=True);start=((dia-1)*7)%len(POOL);fr=((dia-1)*5)%len(FRASES);files=[]
    for k in range(8):
        vid,spec=POOL[(start+k)%len(POOL)];out=f"{tmp}/c{k}.mp4"
        try: _clip(vid,spec,list(FRASES[(fr+k)%len(FRASES)]),out,tmp)
        except Exception as e: print("clip fallo",vid,e);continue
        files.append(out)
    out=f"{tmp}/c9.mp4";_clip(CTA_BG[0],CTA_BG[1],[],out,tmp,cta=True);files.append(out)
    with open(f"{tmp}/list.txt","w") as fh:
        for f in files: fh.write(f"file '{f}'\n")
    secs=len(files)*5;_lofi(f"{tmp}/m.wav",secs=secs,seed=dia);final=f"{tmp}/CasaClic_YT_dia{dia}.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",f"{tmp}/list.txt","-i",f"{tmp}/m.wav","-map","0:v","-map","1:a","-c:v","copy","-af",f"afade=t=in:d=0.5,afade=t=out:st={secs-3}:d=3","-c:a","aac","-b:a","160k","-shortest",final],check=True)
    return final

def subir(path,meta,privacidad="public"):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds=Credentials(None,refresh_token=os.environ["YT_REFRESH_TOKEN"],token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/youtube"])
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    canal=yt.channels().list(part="snippet",mine=True).execute()["items"][0]["snippet"]["title"]
    print("Canal autorizado:",canal)
    if canal!="CasaClic Oficial":
        sys.exit(f"ERROR: el token es del canal '{canal}', no de 'CasaClic Oficial'. No subo nada.")
    body={"snippet":{"title":meta["yt_title"],"description":meta["yt_description"],"tags":TAGS,"categoryId":"26","defaultLanguage":"es"},
          "status":{"privacyStatus":privacidad,"selfDeclaredMadeForKids":False}}
    req=yt.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(path,mimetype="video/mp4",chunksize=-1,resumable=True))
    resp=None
    while resp is None:
        _,resp=req.next_chunk()
    vid=resp["id"]
    print(f"SUBIDO: https://youtu.be/{vid}  (visibilidad: {resp['status']['privacyStatus']})")
    gs=os.environ.get("GITHUB_STEP_SUMMARY")
    if gs:
        with open(gs,"a") as f: f.write(f"### Vídeo subido\n\n**{meta['yt_title']}**\n\nhttps://youtu.be/{vid} · visibilidad: {resp['status']['privacyStatus']}\n")
    return vid

if __name__=="__main__":
    dia=int(sys.argv[1]); priv=sys.argv[2] if len(sys.argv)>2 else "public"
    m=yt_meta(dia); print("Día",dia,"·",m["yt_title"])
    p=make_yt(dia); print("Vídeo generado:",p,os.path.getsize(p)//1024,"KB")
    subir(p,m,priv)
