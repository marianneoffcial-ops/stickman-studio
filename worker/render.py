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
def draw_person(d,x,y,scale,color,phase,pose=0,role='',action='idle'):
    """Consistently inked stick figure with restrained, scene-specific keyframed motion."""
    q=scale; sw=max(2,int(5*q)); limb=max(3,int(7*q))
    cx=x; cy=y-151*q; r=34*q
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(244,240,226),outline=INK,width=sw)
    d.ellipse((cx-16*q,cy-5*q,cx-8*q,cy+5*q),fill=INK); d.ellipse((cx+8*q,cy-5*q,cx+16*q,cy+5*q),fill=INK)
    d.arc((cx-19*q,cy-19*q,cx-5*q,cy-10*q),190,340,fill=INK,width=max(2,int(2*q)))
    d.arc((cx+5*q,cy-19*q,cx+19*q,cy-10*q),200,350,fill=INK,width=max(2,int(2*q)))
    d.arc((cx-11*q,cy+7*q,cx+11*q,cy+23*q),5,170,fill=INK,width=max(2,int(2*q)))
    d.arc((cx-31*q,cy-39*q,cx+22*q,cy+1*q),185,270,fill=INK,width=max(2,int(3*q)))
    d.line((cx-21*q,cy-30*q,cx-7*q,cy-43*q,cx+5*q,cy-31*q),fill=INK,width=max(2,int(3*q)))
    shoulder_y=y-104*q
    d.rounded_rectangle((x-29*q,y-119*q,x+29*q,y+8*q),radius=int(13*q),fill=color,outline=INK,width=sw)
    if role.lower() in ('emperor','official'): d.line((x,y-110*q,x,y-12*q),fill=(193,174,133),width=max(2,int(3*q)))
    elif role.lower() in ('scholar','architect'): d.line((x-17*q,y-84*q,x+17*q,y-84*q),fill=(211,198,166),width=max(2,int(3*q)))
    wave=math.sin(phase)
    if action=='walk':
        arm_a=wave*25*q; leg_a=wave*24*q
        left=(x-28*q,shoulder_y,x-54*q+arm_a,y-25*q); right=(x+28*q,shoulder_y,x+54*q-arm_a,y-25*q)
    elif action in ('point','present'):
        left=(x-28*q,shoulder_y,x-55*q,y-36*q); right=(x+28*q,shoulder_y,x+66*q,y-105*q+wave*4*q); leg_a=wave*3*q
    elif action in ('study','observe'):
        left=(x-28*q,shoulder_y,x-39*q,y-48*q); right=(x+28*q,shoulder_y,x+39*q,y-48*q); leg_a=wave*2*q
    elif action=='turn':
        left=(x-28*q,shoulder_y,x-52*q+wave*5*q,y-12*q); right=(x+28*q,shoulder_y,x+48*q-wave*5*q,y-22*q); leg_a=wave*5*q
    elif action=='gesture':
        left=(x-28*q,shoulder_y,x-63*q,y-72*q+wave*7*q); right=(x+28*q,shoulder_y,x+62*q,y-65*q-wave*7*q); leg_a=wave*3*q
    else:
        left=(x-28*q,shoulder_y,x-48*q+wave*5*q,y-5*q); right=(x+28*q,shoulder_y,x+48*q-wave*5*q,y-5*q); leg_a=wave*5*q
    d.line(left,fill=INK,width=limb); d.ellipse((left[2]-3*q,left[3]-3*q,left[2]+3*q,left[3]+3*q),fill=INK)
    d.line(right,fill=INK,width=limb); d.ellipse((right[2]-3*q,right[3]-3*q,right[2]+3*q,right[3]+3*q),fill=INK)
    d.line((x,y+5*q,x-27*q-leg_a,y+178*q),fill=INK,width=limb); d.line((x,y+5*q,x+27*q+leg_a,y+178*q),fill=INK,width=limb)
    d.line((x-27*q-leg_a,y+178*q,x-12*q-leg_a,y+178*q),fill=INK,width=max(2,int(5*q)))
    d.line((x+27*q+leg_a,y+178*q,x+42*q+leg_a,y+178*q),fill=INK,width=max(2,int(5*q)))
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
    # Scene-specific narrative props for the Mansa Musa brief and related historical stories.
    if any(k in prompt for k in ('throne','emperor','crowned','king','sovereign')):
        tx,ty=int(w*.48),int(h*.53)
        d.rectangle((tx,ty,tx+int(w*.14),int(h*.74)),fill=(112,86,57),outline=INK,width=4)
        d.arc((tx,ty-int(h*.13),tx+int(w*.14),ty+int(h*.12)),180,360,fill=INK,width=5)
        d.rectangle((tx+int(w*.025),ty+int(h*.06),tx+int(w*.115),ty+int(h*.19)),fill=(157,132,87),outline=INK,width=3)
    if any(k in prompt for k in ('gold','nugget','gold dust','golden')):
        for j in range(7):
            gx=int(w*(.57+(j%4)*.055)); gy=int(h*(.66-(j//4)*.025))
            d.ellipse((gx,gy,gx+int(w*.045),gy+int(h*.035)),fill=(171,139,76),outline=INK,width=2)
    if any(k in prompt for k in ('staff','scepter','banner')):
        for j in range(3):
            sx=int(w*(.16+j*.055))
            d.line((sx,int(h*.42),sx,int(h*.72)),fill=(139,105,65),width=max(3,int(w*.004)))
            d.ellipse((sx-int(w*.006),int(h*.405),sx+int(w*.006),int(h*.43)),fill=(177,145,82),outline=INK)
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
    prompt=(scene.get("visual_prompt","")+" "+scene.get("visual","")+" "+scene.get("title","")).lower()
    rng=random.Random(int(scene.get("scene_index",0))+41)
    if any(k in prompt for k in ("snow","winter","ice","antarctic")):
        for j in range(28):
            px=(rng.random()*w+math.sin(phase+j)*w*.012)%w; py=(rng.random()*h+frame*1.8+j*7)%h
            d.ellipse((px,py,px+max(2,w*.003),py+max(2,w*.003)),fill=(239,235,220))
    elif any(k in prompt for k in ("rain","storm","wet")):
        for j in range(55):
            px=(rng.random()*w+j*17)%w; py=(rng.random()*h+frame*5+j*11)%h
            d.line((px,py,px-w*.006,py+h*.018),fill=(111,121,116),width=max(1,int(w*.0015)))
    elif any(k in prompt for k in ("wind","dust","desert","smoke","fog","sea","ocean")):
        for j in range(12):
            px=(rng.random()*w+frame*(.35+j*.025))%w; py=h*(.2+rng.random()*.55)
            d.ellipse((px,py,px+w*.012,py+h*.004),fill=(205,198,178))
    scale=min(w/1280,h/720); names=scene.get("characters",["Narrator"])
    positions=[.30,.52,.74] if w/h>1 else [.36,.66,.50]
    action=scene.get("action","idle")
    for j,name in enumerate(names[:3]):
        drift=math.sin(phase*2+j)*w*.004; x=int(w*positions[j]+drift); y=int(h*.70)
        color=project.get("characters",{}).get(name,{}).get("color","#34465a")
        rgb=tuple(int(color[k:k+2],16) for k in (1,3,5))
        draw_person(d,x,y,scale*(1.0 if w/h>1 else .82),rgb,phase+j,int(scene.get("scene_index",0))%3,name,action)
    # The brief prohibits burned-in titles, captions and subtitles.
    vign=Image.new("L",(w,h),0); vd=ImageDraw.Draw(vign)
    vd.ellipse((-w*.12,-h*.12,w*1.12,h*1.12),fill=230)
    vign=vign.filter(ImageFilter.GaussianBlur(max(10,int(w*.07))))
    dark=Image.new("RGB",(w,h),(15,16,15)); im=Image.composite(im,dark,vign)
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
        # Keep clip duration locked to the requested four-second beat (or final remainder).
        duration=float(scene["duration"])
        frames=max(1,int(round(duration*FPS)))
        clip_duration=frames/FPS
        if speech_seconds > clip_duration-0.08:
            tempo=speech_seconds/max(0.25,clip_duration-0.08)
            if tempo > 1.55:
                raise RuntimeError(f"Scene {i+1} narration is too long for its {duration:g}-second beat; shorten the script to about 9–10 words per 4 seconds.")
            fitted=sd/f"voice_fitted_{i:03d}.wav"
            run([ffmpeg,"-y","-loglevel","error","-i",str(wav),"-af",f"atempo={tempo:.4f}","-t",f"{clip_duration-0.04:.3f}","-ar","24000","-ac","1",str(fitted)])
            wav=fitted
            with wave.open(str(wav),"rb") as wf:
                speech_seconds=wf.getnframes()/float(wf.getframerate())
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
        # Pad each narration beat to its matching clip duration so the voice remains
        # distributed throughout the full episode instead of ending early and leaving silence.
        padded_wav=sd/f"voice_padded_{i:03d}.wav"
        pad_seconds=max(0.0,clip_duration-speech_seconds)
        run([ffmpeg,"-y","-loglevel","error","-i",str(wav),"-af",f"apad=pad_dur={pad_seconds:.3f}",
             "-t",f"{clip_duration:.3f}","-ar","24000","-ac","1",str(padded_wav)])
        clips.append(clip); audios.append(padded_wav)
    concat=outdir/"clips.txt"; concat.write_text("".join(f"file '{x.as_posix()}'\n" for x in clips))
    audio_list=outdir/"audio.txt"; audio_list.write_text("".join(f"file '{x.as_posix()}'\n" for x in audios))
    silent=outdir/"silent.mp4"; voice=outdir/"voice.wav"; final=outdir/"final.mp4"
    run([ffmpeg,"-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
    run([ffmpeg,"-y","-loglevel","error","-f","concat","-safe","0","-i",str(audio_list),"-c:a","pcm_s16le",str(voice)])
    run([ffmpeg,"-y","-loglevel","error","-i",str(silent),"-i",str(voice),"-map","0:v","-map","1:a",
         "-c:v","copy","-af","apad","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(final)])
    project["voice_engine"]=voice_engine
    # Matching illustrated 16:9 thumbnail with the recurring character and a <=4-word headline.
    thumb=outdir/"thumbnail.jpg"
    thumb_im=Image.new("RGB",(1280,720),PAPER); td=ImageDraw.Draw(thumb_im)
    first_scene=project.get("scenes",[{}])[0]
    draw_background(thumb_im,td,0,0,first_scene)
    name=(first_scene.get("characters") or ["Narrator"])[0]
    color=project.get("characters",{}).get(name,{}).get("color","#34465a")
    rgb=tuple(int(color[k:k+2],16) for k in (1,3,5))
    draw_person(td,330,500,1.0,rgb,0,0,name,"observe")
    words=re.findall(r"[A-Za-z0-9']+",project.get("title","STICKMAN STORY").upper())[:4]
    headline=" ".join(words) or "STICKMAN STORY"
    td.rounded_rectangle((590,190,1225,555),radius=18,fill=(30,32,29),outline=(192,174,137),width=5)
    lines=textwrap.wrap(headline,width=12)[:3]
    td.multiline_text((640,260),"\\n".join(lines),font=font(76,True),fill=(244,237,218),spacing=8,stroke_width=1,stroke_fill=INK)
    thumb_im.save(thumb,quality=92)
    project["thumbnail_path"]=str(thumb)
    return final
