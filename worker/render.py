import subprocess, shutil, math, textwrap, random, os, wave, re, gc
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS=12
INK=(29,30,27)
PAPER=(220,211,190)
PALETTE=[(204,194,170),(173,177,153),(166,169,164),(216,207,185),(151,158,145)]
def run(cmd):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or "Render command failed")[-2500:])
def dimensions(ratio):
    return {"16:9":(1280,720),"9:16":(720,1280),"1:1":(960,960)}.get(ratio,(1280,720))
def font(size,bold=False):
    paths=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
           "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    for p in paths:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()
def draw_person(d,x,y,scale,color,phase,pose=0):
    s=scale
    # soft clothing silhouette and inked stick-figure limbs
    d.ellipse((x-34*s,y-184*s,x+34*s,y-116*s),fill=(242,238,224),outline=INK,width=max(2,int(5*s)))
    d.ellipse((x-16*s,y-159*s,x-8*s,y-149*s),fill=INK)
    d.ellipse((x+8*s,y-159*s,x+16*s,y-149*s),fill=INK)
    d.arc((x-12*s,y-150*s,x+12*s,y-132*s),5,165,fill=INK,width=max(2,int(2*s)))
    # loose hair strokes
    d.arc((x-30*s,y-190*s,x+20*s,y-150*s),185,270,fill=INK,width=max(2,int(3*s)))
    d.line((x-19*s,y-180*s,x-4*s,y-193*s,x+5*s,y-181*s),fill=INK,width=max(2,int(3*s)))
    d.rounded_rectangle((x-29*s,y-118*s,x+29*s,y+8*s),radius=int(15*s),fill=color,outline=INK,width=max(2,int(5*s)))
    d.line((x,y+5*s,x,y+104*s),fill=INK,width=max(3,int(7*s)))
    swing=math.sin(phase)*18*s
    if pose==1: arms=[(x-48*s,y-48*s,x-62*s,y-90*s),(x+48*s,y-48*s,x+60*s,y-8*s)]
    elif pose==2: arms=[(x-48*s,y-48*s,x-80*s,y-25*s),(x+48*s,y-48*s,x+78*s,y-25*s)]
    else: arms=[(x-48*s,y-48*s,x-58*s-swing,y+2*s),(x+48*s,y-48*s,x+58*s+swing,y+2*s)]
    for a in arms: d.line(a,fill=INK,width=max(3,int(7*s)))
    d.line((x,y+104*s,x-28*s-swing,y+178*s),fill=INK,width=max(3,int(8*s)))
    d.line((x,y+104*s,x+28*s+swing,y+178*s),fill=INK,width=max(3,int(8*s)))
def draw_background(im,d,index,phase,scene=None):
    w,h=im.size; base=PALETTE[index%len(PALETTE)]
    im.paste(base,(0,0,w,h))
    horizon=int(h*.69)
    # distant layered hills and architecture
    d.polygon([(0,horizon),(w*.16,h*.42),(w*.31,horizon),(w*.5,h*.35),(w*.68,horizon),(w*.86,h*.46),(w,horizon),(w,h),(0,h)],fill=(133,139,124),outline=INK,width=4)
    d.rectangle((0,horizon,w,h),fill=(184,176,151))
    # scene-specific landmark silhouettes
    prompt=((scene or {}).get('visual_prompt','')+' '+(scene or {}).get('visual','')+' '+(scene or {}).get('title','')).lower()
    if any(k in prompt for k in ('ship','vessel','boat','ocean','sea','sail')): mode=2
    elif any(k in prompt for k in ('library','archive','book','scholar','manuscript','document','ledger')): mode=3
    elif any(k in prompt for k in ('map','atlas','chart','route','letter','close-up','close up')): mode=5
    elif any(k in prompt for k in ('mosque','palace','temple','cathedral','monument','architecture')): mode=0
    elif any(k in prompt for k in ('market','street','city','cairo','town','crowd')): mode=1
    elif any(k in prompt for k in ('snow','ice','antarctic','winter','mountain','desert','sahara','dune')): mode=4
    else: mode=index%6
    if mode==0: # old tower
        x=int(w*.72); bw=int(w*.13)
        d.rectangle((x,h*.25,x+bw,h*.73),fill=(157,151,132),outline=INK,width=5)
        d.polygon([(x-12,h*.25),(x+bw/2,h*.12),(x+bw+12,h*.25)],fill=(120,119,105),outline=INK)
        for yy in [.36,.48,.60]: d.rectangle((x+bw*.35,h*yy,x+bw*.62,h*(yy+.07)),fill=(55,59,54),outline=INK,width=2)
    elif mode==1: # city / street
        for j in range(5):
            x=int(w*(.06+j*.18)); hh=int(h*(.20+(j%3)*.06))
            d.rectangle((x,horizon-hh,x+w*.12,horizon),fill=(169,160,140),outline=INK,width=4)
            for yy in range(3): d.rectangle((x+w*.025,horizon-hh+yy*24,x+w*.05,horizon-hh+yy*24+12),fill=(75,78,70))
    elif mode==2: # sea / ship
        d.rectangle((0,h*.48,w,h*.72),fill=(142,154,147))
        d.polygon([(w*.2,h*.59),(w*.72,h*.59),(w*.63,h*.68),(w*.29,h*.68)],fill=(83,85,78),outline=INK,width=4)
        d.line((w*.47,h*.58,w*.47,h*.28),fill=INK,width=5)
        d.polygon([(w*.48,h*.29),(w*.65,h*.52),(w*.48,h*.52)],fill=(211,201,179),outline=INK,width=3)
    elif mode==3: # archive / interior
        d.rectangle((w*.08,h*.18,w*.92,h*.72),fill=(190,177,151),outline=INK,width=5)
        for j in range(4):
            x=w*(.14+j*.19)
            d.rectangle((x,h*.26,x+w*.12,h*.68),fill=(126,111,91),outline=INK,width=3)
            for k in range(4): d.rectangle((x+8,h*(.29+k*.09),x+w*.10,h*(.32+k*.09)),fill=(207,194,165))
    elif mode==4: # mountain / wilderness
        d.polygon([(0,h*.72),(w*.2,h*.22),(w*.42,h*.72),(w*.64,h*.16),(w*.92,h*.72)],fill=(128,137,123),outline=INK,width=4)
    else: # monumental doorway
        d.rectangle((w*.61,h*.22,w*.88,h*.74),fill=(147,140,120),outline=INK,width=5)
        d.arc((w*.61,h*.15,w*.88,h*.48),180,360,fill=INK,width=5)
        d.rectangle((w*.70,h*.40,w*.79,h*.74),fill=(65,68,62),outline=INK,width=3)
    # Distinct foreground props keyed to the actual storyboard description
    if any(k in prompt for k in ('camel','caravan','desert','sahara','dune')):
        for j in range(3):
            cx=int(w*(.20+j*.25)); cy=int(h*.64)
            d.ellipse((cx-24,cy-18,cx+28,cy+20),fill=(139,119,91),outline=INK,width=3)
            d.arc((cx-8,cy-44,cx+24,cy+4),180,350,fill=INK,width=4)
            d.line((cx+18,cy-12,cx+31,cy-35),fill=INK,width=3)
    if any(k in prompt for k in ('map','atlas','chart','route')):
        d.rounded_rectangle((w*.12,h*.27,w*.48,h*.58),radius=8,fill=(220,207,174),outline=INK,width=4)
        for j in range(5): d.arc((w*(.16+j*.045),h*.31,w*(.31+j*.045),h*.54),20,250,fill=(112,103,82),width=2)
        d.line((w*.18,h*.50,w*.40,h*.35),fill=(139,72,57),width=4)
    if any(k in prompt for k in ('market','merchant','shop','gold','coin')):
        for j in range(3):
            xx=w*(.58+j*.11)
            d.rectangle((xx,h*.49,xx+w*.075,h*.67),fill=(151,124,88),outline=INK,width=3)
            d.arc((xx+4,h*.44,xx+w*.07,h*.57),180,360,fill=INK,width=3)
    if any(k in prompt for k in ('mosque','palace','temple','monument')):
        d.rectangle((w*.54,h*.43,w*.87,h*.70),fill=(184,171,145),outline=INK,width=4)
        d.arc((w*.61,h*.29,w*.80,h*.56),180,360,fill=INK,width=4)
        for xx in (.61,.70,.79): d.rectangle((w*xx,h*.53,w*(xx+.035),h*.70),fill=(72,72,65),outline=INK,width=2)
    if any(k in prompt for k in ('snow','winter','ice','antarctic')):
        rng_snow=random.Random(index+91)
        for _ in range(35):
            sx=rng_snow.randrange(w); sy=rng_snow.randrange(int(h*.62))
            d.ellipse((sx,sy,sx+3,sy+3),fill=(238,234,219))
    # paper grain and scanlines
    grain=Image.new("RGBA",(w,h),(0,0,0,0)); gd=ImageDraw.Draw(grain)
    rng=random.Random(index+17)
    for _ in range(max(150,w*h//9500)):
        x=rng.randrange(w); y=rng.randrange(h)
        gd.point((x,y),fill=(30,28,22,rng.randrange(8,24)))
    for y in range(0,h,5): gd.line((0,y,w,y),fill=(30,28,22,12),width=1)
    im.paste(Image.alpha_composite(im.convert("RGBA"),grain).convert("RGB"))
def draw_frame(scene,project,frame,total_frames,out):
    w,h=dimensions(project.get("aspect_ratio","16:9"))
    im=Image.new("RGB",(w,h),PAPER); d=ImageDraw.Draw(im)
    phase=2*math.pi*frame/max(1,total_frames)
    draw_background(im,d,int(scene.get("scene_index",0)),phase,scene)
    # camera framing adapts to portrait and square
    scale=min(w/1280,h/720)
    names=scene.get("characters",["Narrator"])
    positions=[.30,.52,.74] if w/h>1 else [.36,.66,.50]
    for j,name in enumerate(names[:3]):
        drift=math.sin(phase*2+j)*w*.008
        x=int(w*positions[j]+drift); y=int(h*.70)
        color=project.get("characters",{}).get(name,{}).get("color","#34465a")
        rgb=tuple(int(color[k:k+2],16) for k in (1,3,5))
        draw_person(d,x,y,scale*(1.0 if w/h>1 else .82),rgb,phase+j,int(scene.get("scene_index",0))%3)
    title=scene.get("title","A new chapter")
    d.text((int(w*.045),int(h*.055)),title,font=font(max(22,int(w*.034)),True),fill=(246,239,220),stroke_width=2,stroke_fill=INK)
    caption=scene.get("narration","")
    max_chars=max(24,int(w/(max(16,w*.023)*.58)))
    lines=textwrap.wrap(caption,width=max_chars)[:3]
    box_top=int(h*.84) if h/w<1.5 else int(h*.845)
    d.rounded_rectangle((int(w*.035),box_top,int(w*.965),int(h*.965)),radius=max(8,int(w*.012)),fill=(30,32,29),outline=(173,157,124),width=max(1,int(scale*2)))
    d.multiline_text((int(w*.06),box_top+int(h*.025)),"\n".join(lines),font=font(max(16,int(w*.022))),fill=(244,238,222),spacing=5)
    # darkened vignette
    vign=Image.new("L",(w,h),0); vd=ImageDraw.Draw(vign)
    vd.ellipse((-w*.12,-h*.12,w*1.12,h*1.12),fill=230)
    vign=vign.filter(ImageFilter.GaussianBlur(max(10,int(w*.07))))
    dark=Image.new("RGB",(w,h),(15,16,15)); im=Image.composite(im,dark,Image.eval(vign,lambda p:255-p))
    im.save(out,quality=92)
def synthesize_voice(text,destination,ffmpeg):
    edge=shutil.which("edge-tts")
    if edge:
        mp3=destination.with_suffix(".mp3")
        try:
            run([edge,"--voice","en-US-GuyNeural","--rate","+0%","--text",text,"--write-media",str(mp3)])
            run([ffmpeg,"-y","-loglevel","error","-i",str(mp3),"-ar","24000","-ac","1",str(destination)])
            return "Microsoft neural en-US-GuyNeural"
        except Exception:
            pass
    tts=shutil.which("espeak-ng") or shutil.which("espeak")
    if not tts: raise RuntimeError("No TTS engine available. Check cloud network access for Edge TTS.")
    run([tts,"-s","150","-v","en-us","-w",str(destination),text])
    return "eSpeak fallback (robotic; neural voice unavailable)"
def render_project(project,outdir:Path):
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg: raise RuntimeError("FFmpeg is not installed in the cloud worker")
    clips=[]; audios=[]; sd=outdir/"scenes"; sd.mkdir(exist_ok=True)
    voice_engine=None
    for i,scene in enumerate(project["scenes"]):
        scene["scene_index"]=i
        wav=sd/f"voice_{i:03d}.wav"
        engine=synthesize_voice(scene["narration"],wav,ffmpeg); voice_engine=engine
        with wave.open(str(wav),"rb") as wf:
            speech_seconds=wf.getnframes()/float(wf.getframerate())
        duration=max(.5,float(scene["duration"]),speech_seconds+0.12)
        scene["duration"]=round(duration,3)
        frames=max(1,int(math.ceil(duration*FPS)))
        frames_dir=sd/f"frames_{i:03d}"; frames_dir.mkdir(exist_ok=True)
        for f in range(frames): draw_frame(scene,project,f,frames,frames_dir/f"frame_{f:05d}.png")
        clip=sd/f"clip_{i:03d}.mp4"
        width,height=dimensions(project.get("aspect_ratio","16:9"))
        camera_index=i%4
        x_expr=["iw/2-(iw/zoom/2)","iw-iw/zoom","0","iw/2-(iw/zoom/2)"][camera_index]
        y_expr=["ih/2-(ih/zoom/2)","ih/2-(ih/zoom/2)","ih/2-(ih/zoom/2)","0"][camera_index]
        camera_filter=f"zoompan=z='min(zoom+0.0007,1.05)':x='{x_expr}':y='{y_expr}':d=1:s={width}x{height}:fps=24,format=yuv420p"
        run([ffmpeg,"-y","-loglevel","error","-framerate",str(FPS),"-i",str(frames_dir/"frame_%05d.png"),
             "-vf",camera_filter,"-c:v","libx264","-preset","veryfast","-crf","19",str(clip)])
        shutil.rmtree(frames_dir,ignore_errors=True); gc.collect()
        clips.append(clip); audios.append(wav)
    concat=outdir/"clips.txt"; concat.write_text("".join(f"file '{x.as_posix()}'\n" for x in clips))
    audio_list=outdir/"audio.txt"; audio_list.write_text("".join(f"file '{x.as_posix()}'\n" for x in audios))
    silent=outdir/"silent.mp4"; voice=outdir/"voice.wav"; final=outdir/"final.mp4"
    run([ffmpeg,"-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
    run([ffmpeg,"-y","-loglevel","error","-f","concat","-safe","0","-i",str(audio_list),"-c:a","pcm_s16le",str(voice)])
    run([ffmpeg,"-y","-loglevel","error","-i",str(silent),"-i",str(voice),"-map","0:v","-map","1:a",
         "-c:v","copy","-af","apad","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(final)])
    project["voice_engine"]=voice_engine
    # Matching 16:9 thumbnail regardless of video aspect ratio
    thumb=outdir/"thumbnail.jpg"
    thumb_im=Image.new("RGB",(1280,720),PAPER); td=ImageDraw.Draw(thumb_im)
    draw_background(thumb_im,td,0,0)
    td.rectangle((40,470,1240,675),fill=(28,30,27),outline=(192,174,137),width=4)
    title=project.get("title","STICKMAN EXPLAINER")
    lines=textwrap.wrap(title,width=34)[:3]
    td.multiline_text((75,500),"\n".join(lines),font=font(48,True),fill=(244,237,218),spacing=8)
    thumb_im.save(thumb,quality=92)
    project["thumbnail_path"]=str(thumb)
    return final
