import subprocess, shutil, math, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=1280,720,12
def run(cmd):
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if p.returncode: raise RuntimeError(p.stderr[-2000:])
def font(size,bold=False):
 candidates=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
 for f in candidates:
  if Path(f).exists(): return ImageFont.truetype(f,size)
 return ImageFont.load_default()
def draw_frame(scene, project, frame, total_frames, out):
 im=Image.new("RGB",(W,H),(77,83,79)); d=ImageDraw.Draw(im)
 d.polygon([(0,520),(180,290),(350,520),(540,240),(760,520),(980,300),(1280,510),(1280,720),(0,720)],fill=(48,55,51),outline=(20,21,20),width=10)
 d.rectangle((0,590,W,H),fill=(38,43,39))
 d.rectangle((930,260,1080,510),fill=(65,65,57),outline=(18,18,17),width=9)
 d.polygon([(910,265),(1005,180),(1100,265)],fill=(50,51,46),outline=(18,18,17))
 d.ellipse((570,175,710,315),fill=(190,168,117),outline=(22,22,20),width=8)
 d.polygon([(640,190),(685,245),(640,300),(595,245)],outline=(35,35,30),width=8)
 names=scene.get("characters",["Arman"]); chars=project.get("characters",{}); xs=[390,640,875]
 phase=2*math.pi*frame/max(1,total_frames)
 for j,name in enumerate(names[:3]):
  x=xs[j]+int(12*math.sin(phase+j)); y=460
  color=chars.get(name,{}).get("color","#4b5563"); rgb=tuple(int(color[k:k+2],16) for k in (1,3,5))
  d.polygon([(x-35,y-70),(x+35,y-70),(x+52,y+65),(x-52,y+65)],fill=rgb,outline=(15,15,15),width=8)
  d.ellipse((x-45,y-175,x+45,y-85),fill=(244,240,230),outline=(15,15,15),width=9)
  d.ellipse((x-20,y-145,x-8,y-126),fill=(12,12,12)); d.ellipse((x+8,y-145,x+20,y-126),fill=(12,12,12))
  d.arc((x-17,y-130,x+17,y-100),10,170,fill=(12,12,12),width=5)
  swing=int(24*math.sin(phase+j))
  d.line((x,y-70,x,y+80),fill=(12,12,12),width=14)
  d.line((x,y-30,x-48,y+8+swing),fill=(12,12,12),width=12)
  d.line((x,y-30,x+48,y+8-swing),fill=(12,12,12),width=12)
  d.line((x,y+80,x-32-swing,y+145),fill=(12,12,12),width=14)
  d.line((x,y+80,x+32+swing,y+145),fill=(12,12,12),width=14)
 d.text((55,55),scene.get("title","A new scene"),font=font(38,True),fill=(245,239,222),stroke_width=2,stroke_fill=(20,20,18))
 words=textwrap.wrap(scene.get("narration",""),width=82); caption="\n".join(words[:2])
 d.rounded_rectangle((40,610,1240,700),radius=14,fill=(17,19,18),outline=(160,147,116),width=2)
 d.multiline_text((65,625),caption,font=font(24),fill=(246,241,228),spacing=5)
 d.rectangle((0,0,W-1,H-1),outline=(13,14,13),width=18)
 im.save(out)
def render_project(project,outdir:Path):
 ffmpeg=shutil.which("ffmpeg"); tts=shutil.which("espeak-ng") or shutil.which("espeak")
 if not ffmpeg: raise RuntimeError("FFmpeg is not installed in the cloud worker")
 if not tts: raise RuntimeError("espeak-ng/espeak is not installed in the cloud worker")
 clips=[]; audios=[]; sd=outdir/"scenes"; sd.mkdir(exist_ok=True)
 for i,scene in enumerate(project["scenes"]):
  duration=max(2,float(scene["duration"])); frames=max(1,int(duration*FPS)); frames_dir=sd/f"frames_{i:02d}"; frames_dir.mkdir(exist_ok=True)
  for f in range(frames): draw_frame(scene,project,f,frames,frames_dir/f"frame_{f:05d}.png")
  clip=sd/f"clip_{i:02d}.mp4"
  run([ffmpeg,"-y","-loglevel","error","-framerate",str(FPS),"-i",str(frames_dir/"frame_%05d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-r","24",str(clip)])
  wav=sd/f"voice_{i:02d}.wav"; run([tts,"-s","145","-v","en-us","-w",str(wav),scene["narration"]]); clips.append(clip); audios.append(wav)
 concat=outdir/"clips.txt"; concat.write_text("".join(f"file '{x.as_posix()}'\n" for x in clips)); audio_list=outdir/"audio.txt"; audio_list.write_text("".join(f"file '{x.as_posix()}'\n" for x in audios))
 silent=outdir/"silent.mp4"; voice=outdir/"voice.wav"; final=outdir/"final.mp4"
 run([ffmpeg,"-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
 run([ffmpeg,"-y","-loglevel","error","-f","concat","-safe","0","-i",str(audio_list),"-c:a","pcm_s16le",str(voice)])
 run([ffmpeg,"-y","-loglevel","error","-i",str(silent),"-i",str(voice),"-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-shortest","-movflags","+faststart",str(final)])
 return final
