import subprocess, shutil, math, textwrap, random, os, wave, re, gc
from pathlib import Path
from array import array
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
    presets={"16:9":(1280,720),"9:16":(720,1280),"1:1":(960,960)}
    if ratio in presets: return presets[ratio]
    try:
        a,b=(int(x) for x in ratio.split(":",1))
        if a<1 or b<1: raise ValueError()
        if a>=b: return (1280,max(2,int(round(1280*b/a/2)*2)))
        return (max(2,int(round(1280*a/b/2)*2)),1280)
    except Exception:
        return (1280,720)
def font(size,bold=False):
    paths=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
           "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    for p in paths:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()
def draw_person(d,x,y,scale,color,phase,pose=0,role='',action='idle',expression='neutral'):
    """Draw a consistent inked character with articulated, gently animated limbs."""
    q=scale
    # A small double-step body bounce gives the torso weight while the legs stay grounded.
    upper_y=float(y - (abs(math.sin(phase*2))*2.5*q if action=='walk' else 0.0))
    outline=max(2,int(5*q)); limb=max(3,int(7*q))
    cx=float(x); head_y=float(upper_y-151*q); radius=34*q
    breath=math.sin(phase*2)*2.0*q
    head_tilt=math.sin(phase*1.4)*2.0*q
    # Neck and compact jacket silhouette
    d.line((cx,head_y+radius-1*q,cx,upper_y-119*q),fill=INK,width=max(3,int(6*q)))
    torso=[(cx-22*q,upper_y-118*q),(cx+22*q,upper_y-118*q),(cx+30*q,upper_y-91*q),
           (cx+26*q,upper_y+4*q),(cx-26*q,upper_y+4*q),(cx-30*q,upper_y-91*q)]
    d.polygon(torso,fill=color,outline=INK)
    d.line((cx-22*q,upper_y-118*q,cx+22*q,upper_y-118*q),fill=INK,width=max(2,int(3*q)))
    # Subtle seams and folds keep the clothing from reading as a plain rectangle.
    d.line((cx-14*q,upper_y-83*q,cx-9*q,upper_y-22*q),fill=tuple(max(0,int(c*.78)) for c in color),width=max(1,int(2*q)))
    d.line((cx+15*q,upper_y-70*q,cx+11*q,upper_y-36*q),fill=tuple(min(255,int(c*1.12)) for c in color),width=max(1,int(2*q)))
    if role.lower() in ('emperor','official'):
        d.line((cx,upper_y-111*q,cx,upper_y-10*q),fill=(193,174,133),width=max(2,int(3*q)))
    elif role.lower() in ('scholar','architect'):
        d.line((cx-17*q,upper_y-84*q,cx+17*q,upper_y-84*q),fill=(211,198,166),width=max(2,int(3*q)))
    sway=math.sin(phase)
    shoulder_l=(cx-25*q,upper_y-100*q+breath); shoulder_r=(cx+25*q,upper_y-100*q+breath)
    hip_l=(cx-12*q,upper_y+1*q); hip_r=(cx+12*q,upper_y+1*q)
    # Jointed arms: shoulder, elbow and hand positions change smoothly by action.
    if action=='walk':
        arm=26*q*sway; leg=25*q*sway
        elbows=[(cx-43*q+arm*.35,upper_y-65*q),(cx+43*q-arm*.35,upper_y-65*q)]
        hands=[(cx-48*q+arm,upper_y-26*q),(cx+48*q-arm,upper_y-26*q)]
    elif action=='point':
        leg=3*q*sway
        elbows=[(cx-43*q,upper_y-64*q),(cx+46*q,upper_y-116*q)]
        hands=[(cx-54*q,upper_y-34*q),(cx+76*q,upper_y-129*q+4*q*sway)]
    elif action=='present':
        reach=(.5-.5*math.cos(phase))*5*q
        leg=3*q*sway
        elbows=[(cx-43*q,upper_y-64*q),(cx+46*q+reach,upper_y-116*q)]
        hands=[(cx-54*q,upper_y-34*q),(cx+76*q+reach,upper_y-129*q+4*q*sway)]
    elif action=='reveal':
        # The raised hand eases upward, holds, then settles instead of remaining static.
        lift=(.5-.5*math.cos(phase))*7*q
        leg=3*q*sway
        elbows=[(cx-43*q,upper_y-66*q),(cx+38*q,upper_y-121*q-lift*.55)]
        hands=[(cx-55*q,upper_y-34*q),(cx+43*q,upper_y-163*q-lift+5*q*sway)]
        head_tilt-=3*q+math.sin(phase)*1.2*q
    elif action=='ponder':
        # A restrained chin-touch and head tilt create a living thinking pose.
        nod=math.sin(phase*1.5)*2.2*q
        leg=2*q*sway
        elbows=[(cx-38*q,upper_y-67*q),(cx+35*q,upper_y-73*q+nod)]
        hands=[(cx-30*q,upper_y-44*q),(cx+18*q,upper_y-119*q+nod+3*q*sway)]
        head_tilt+=5*q
    elif action in ('study','observe'):
        leg=2*q*sway
        elbows=[(cx-36*q,upper_y-68*q),(cx+36*q,upper_y-68*q)]
        hands=[(cx-28*q,upper_y-45*q),(cx+28*q,upper_y-45*q)]
    elif action=='turn':
        leg=7*q*sway
        elbows=[(cx-43*q+5*q*sway,upper_y-59*q),(cx+42*q-5*q*sway,upper_y-68*q)]
        hands=[(cx-52*q+6*q*sway,upper_y-18*q),(cx+48*q-6*q*sway,upper_y-29*q)]
    elif action=='gesture':
        # Alternating arm emphasis gives speeches a readable, gentle cadence.
        emphasis=math.sin(phase*2)
        leg=4*q*sway
        elbows=[(cx-46*q,upper_y-83*q+7*q*sway),(cx+46*q,upper_y-80*q-7*q*sway)]
        hands=[(cx-67*q,upper_y-104*q+10*q*sway),(cx+68*q,upper_y-101*q-10*q*sway-5*q*max(0,emphasis))]

    else:
        leg=5*q*sway
        elbows=[(cx-40*q+5*q*sway,upper_y-60*q),(cx+40*q-5*q*sway,upper_y-60*q)]
        hands=[(cx-49*q+6*q*sway,upper_y-8*q),(cx+49*q-6*q*sway,upper_y-8*q)]
    for shoulder,elbow,hand in ((shoulder_l,elbows[0],hands[0]),(shoulder_r,elbows[1],hands[1])):
        d.line((shoulder,elbow,hand),fill=INK,width=limb,joint='curve')
        rr=max(2,3*q)
        d.ellipse((elbow[0]-rr,elbow[1]-rr,elbow[0]+rr,elbow[1]+rr),fill=INK)
        d.ellipse((hand[0]-rr,hand[1]-rr,hand[0]+rr,hand[1]+rr),fill=INK)
        # Small cuff marks make hand/arm direction legible at normal viewing size.
        d.line((hand[0]-3*q,hand[1],hand[0]+3*q,hand[1]),fill=(224,216,195),width=max(1,int(2*q)))
    # Bent legs with knees and simple shoes; walking feet lift alternately
    # so the character reads as stepping forward rather than sliding.
    if action=='walk':
        lift_l=max(0.0,sway)*12*q
        lift_r=max(0.0,-sway)*12*q
    else:
        lift_l=lift_r=0.0
    knee_l=(cx-20*q-leg*.55,y+83*q-lift_l*.48)
    knee_r=(cx+20*q+leg*.55,y+83*q-lift_r*.48)
    foot_l=(cx-34*q-leg,y+174*q-lift_l)
    foot_r=(cx+34*q+leg,y+174*q-lift_r)
    d.line((hip_l,knee_l,foot_l),fill=INK,width=limb,joint='curve')
    d.line((hip_r,knee_r,foot_r),fill=INK,width=limb,joint='curve')
    for px,py in (knee_l,knee_r):
        rr=max(2,3*q); d.ellipse((px-rr,py-rr,px+rr,py+rr),fill=INK)
    d.line((foot_l[0],foot_l[1],foot_l[0]+15*q,foot_l[1]),fill=INK,width=max(3,int(7*q)))
    d.line((foot_r[0],foot_r[1],foot_r[0]+15*q,foot_r[1]),fill=INK,width=max(3,int(7*q)))
    # Round head, expressive brows and a blink on a slow cycle.
    hx=cx+head_tilt; hy=head_y+breath*.35
    d.ellipse((hx-radius,hy-radius,hx+radius,hy+radius),fill=(244,240,226),outline=INK,width=outline)
    blink=(math.sin(phase*1.7+0.6)>.985)
    eye_y=hy-4*q
    if blink:
        d.line((hx-17*q,eye_y,hx-8*q,eye_y),fill=INK,width=max(2,int(3*q)))
        d.line((hx+8*q,eye_y,hx+17*q,eye_y),fill=INK,width=max(2,int(3*q)))
    else:
        d.ellipse((hx-17*q,eye_y-4*q,hx-8*q,eye_y+5*q),fill=INK)
        d.ellipse((hx+8*q,eye_y-4*q,hx+17*q,eye_y+5*q),fill=INK)
    # Facial features are driven by the narrative beat, not one repeated smile.
    if expression == 'surprised':
        d.arc((hx-22*q,hy-29*q,hx-4*q,hy-12*q),190,350,fill=INK,width=max(2,int(3*q)))
        d.arc((hx+4*q,hy-29*q,hx+22*q,hy-12*q),190,350,fill=INK,width=max(2,int(3*q)))
        d.ellipse((hx-7*q,hy+8*q,hx+7*q,hy+25*q),outline=INK,width=max(2,int(2*q)))
    elif expression == 'concerned':
        d.line((hx-21*q,hy-13*q,hx-6*q,hy-19*q),fill=INK,width=max(2,int(3*q)))
        d.line((hx+6*q,hy-19*q,hx+21*q,hy-13*q),fill=INK,width=max(2,int(3*q)))
        d.arc((hx-10*q,hy+13*q,hx+10*q,hy+27*q),195,345,fill=INK,width=max(2,int(2*q)))
    elif expression == 'weary':
        d.line((hx-21*q,hy-13*q,hx-6*q,hy-11*q),fill=INK,width=max(2,int(3*q)))
        d.line((hx+6*q,hy-11*q,hx+21*q,hy-13*q),fill=INK,width=max(2,int(3*q)))
        d.line((hx-8*q,hy+17*q,hx+8*q,hy+17*q),fill=INK,width=max(2,int(2*q)))
    elif expression == 'resolved':
        d.line((hx-21*q,hy-17*q,hx-6*q,hy-12*q),fill=INK,width=max(2,int(3*q)))
        d.line((hx+6*q,hy-12*q,hx+21*q,hy-17*q),fill=INK,width=max(2,int(3*q)))
        d.line((hx-9*q,hy+16*q,hx+9*q,hy+16*q),fill=INK,width=max(2,int(3*q)))
    else:
        brow_l=(hx-20*q,hy-18*q,hx-5*q,hy-10*q)
        brow_r=(hx+5*q,hy-18*q,hx+20*q,hy-10*q)
        d.arc(brow_l,195,340,fill=INK,width=max(2,int(2*q)))
        d.arc(brow_r,200,345,fill=INK,width=max(2,int(2*q)))
        if action in ('study','observe','turn'):
            d.arc((hx-10*q,hy+8*q,hx+10*q,hy+20*q),195,345,fill=INK,width=max(2,int(2*q)))
        elif action in ('gesture','point','present'):
            d.arc((hx-10*q,hy+7*q,hx+10*q,hy+23*q),5,175,fill=INK,width=max(2,int(2*q)))
        else:
            d.arc((hx-10*q,hy+7*q,hx+10*q,hy+21*q),10,170,fill=INK,width=max(2,int(2*q)))
    # A few loose, repeatable hair strokes finish the hand-inked silhouette.
    d.arc((hx-29*q,hy-39*q,hx+18*q,hy+2*q),185,270,fill=INK,width=max(2,int(3*q)))
    d.line((hx-22*q,hy-29*q,hx-8*q,hy-43*q,hx+4*q,hy-31*q),fill=INK,width=max(2,int(3*q)))

def scene_description(scene):
    """Return scene meaning without repeated visual-style or safety instructions."""
    scene = scene or {}
    title = str(scene.get("title", "")).strip()
    visual = str(scene.get("visual", "")).strip()
    if not visual:
        prompt = str(scene.get("visual_prompt", ""))
        match = re.search(r"Background and story action:\s*(.*?)\s*Shot composition:", prompt, re.I | re.S)
        visual = match.group(1).strip() if match else prompt
    return (title + " " + visual).strip().lower()


def contains_any(text, terms):
    """Match complete words/phrases, avoiding false positives such as restrained/train."""
    value = str(text or "").lower()
    return any(re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", value)
               for term in terms)



def scene_transport_kind(prompt):
    """Choose one dominant transport motif so mixed keywords cannot stack props."""
    p = str(prompt or "").lower()
    if contains_any(p, ("ship", "vessel", "boat", "ocean", "sea", "sail", "coast")):
        return "sea"
    if contains_any(p, ("train", "railway", "locomotive", "carriage")):
        return "rail"
    if contains_any(p, ("aircraft", "airplane", "plane", "parachute", "flight", "pilot")):
        return "air"
    return "none"



def scene_background_mode(prompt,index=0):
    """Return one dominant environment for a scene's background illustration."""
    if contains_any(prompt, ('ship','vessel','boat','ocean','sea','sail')): return 2
    if contains_any(prompt, ('library','archive','book','scholar','manuscript','document','ledger','letter','paper')): return 3
    if contains_any(prompt, ('map','atlas','chart','route')): return 5
    if contains_any(prompt, ('mosque','palace','temple','cathedral','monument','architecture')): return 0
    if contains_any(prompt, ('market','street','city','cairo','town','crowd')): return 1
    if contains_any(prompt, ('snow','ice','antarctic','winter','mountain','desert','sahara','dune')): return 4
    return index%6


def draw_background(im,d,index,phase,scene=None,closeup=False):
    w,h=im.size; base=PALETTE[index%len(PALETTE)]
    im.paste(base,(0,0,w,h))
    if closeup:
        # Object close-ups use a quiet illustrated tabletop/paper stage rather than
        # repeating the full landscape, buildings and secondary story props.
        d.rectangle((0,h*.64,w,h),fill=(177,166,142))
        d.line((0,h*.64,w,h*.64),fill=(83,78,67),width=max(2,int(w*.002)))
        d.line((0,h*.665,w,h*.665),fill=(207,195,169),width=max(1,int(w*.001)))
        # Sparse hand-drawn grain marks keep the surface tactile but uncluttered.
        rng=random.Random(index+4401)
        for _ in range(max(18,w//35)):
            x=rng.randrange(w); y=rng.randrange(int(h*.68),h)
            d.line((x,y,x+rng.randrange(4,18),y-rng.randrange(0,3)),fill=(145,133,111),width=1)
        return
    horizon=int(h*.69)
    # Keep the ground plane neutral. Each semantic setting below draws its own
    # silhouette; a generic mountain skyline behind every setting caused visual
    # contradictions (for example, indoor archives with outdoor hills).
    d.rectangle((0,horizon,w,h),fill=(184,176,151))
    # scene-specific landmark silhouettes
    prompt=scene_description(scene)
    mode=scene_background_mode(prompt,index)
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
    elif mode==2: # sea / ship, with restrained bobbing and moving wave lines
        d.rectangle((0,h*.48,w,h*.72),fill=(142,154,147))
        shift=math.sin(phase)*w*.022; bob=math.sin(phase*2)*h*.008
        d.polygon([(w*.2+shift,h*.59+bob),(w*.72+shift,h*.59+bob),(w*.63+shift,h*.68+bob),(w*.29+shift,h*.68+bob)],fill=(83,85,78),outline=INK,width=4)
        d.line((w*.47+shift,h*.58+bob,w*.47+shift,h*.28+bob),fill=INK,width=5)
        d.polygon([(w*.48+shift,h*.29+bob),(w*.65+shift,h*.52+bob),(w*.48+shift,h*.52+bob)],fill=(211,201,179),outline=INK,width=3)
        for j in range(7):
            xx=((j*.17+phase*.035)%1.15-.08)*w
            yy=h*(.72+j%3*.018)
            d.arc((xx,yy,xx+w*.13,yy+h*.035),185,345,fill=(91,111,107),width=2)
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
    if mode==4 and contains_any(prompt, ('camel','caravan','desert','sahara','dune')):
        for j in range(3):
            cx=int(w*(.20+j*.25)); cy=int(h*.64)
            d.ellipse((cx-24,cy-18,cx+28,cy+20),fill=(139,119,91),outline=INK,width=3)
            d.arc((cx-8,cy-44,cx+24,cy+4),180,350,fill=INK,width=4)
            d.line((cx+18,cy-12,cx+31,cy-35),fill=INK,width=3)
    if mode==5 and contains_any(prompt, ('map','atlas','chart','route')):
        d.rounded_rectangle((w*.12,h*.27,w*.48,h*.58),radius=8,fill=(220,207,174),outline=INK,width=4)
        for j in range(5): d.arc((w*(.16+j*.045),h*.31,w*(.31+j*.045),h*.54),20,250,fill=(112,103,82),width=2)
        d.line((w*.18,h*.50,w*.40,h*.35),fill=(139,72,57),width=4)
    if mode==1 and contains_any(prompt, ('market','merchant','shop','gold','coin')):
        for j in range(3):
            xx=w*(.58+j*.11)
            d.rectangle((xx,h*.49,xx+w*.075,h*.67),fill=(151,124,88),outline=INK,width=3)
            d.arc((xx+4,h*.44,xx+w*.07,h*.57),180,360,fill=INK,width=3)
    if mode==0 and contains_any(prompt, ('mosque','palace','temple','monument')):
        d.rectangle((w*.54,h*.43,w*.87,h*.70),fill=(184,171,145),outline=INK,width=4)
        d.arc((w*.61,h*.29,w*.80,h*.56),180,360,fill=INK,width=4)
        for xx in (.61,.70,.79): d.rectangle((w*xx,h*.53,w*(xx+.035),h*.70),fill=(72,72,65),outline=INK,width=2)
    if contains_any(prompt, ('snow','winter','ice','antarctic')):
        rng_snow=random.Random(index+91)
        for _ in range(35):
            sx=rng_snow.randrange(w); sy=rng_snow.randrange(int(h*.62))
            d.ellipse((sx,sy,sx+3,sy+3),fill=(238,234,219))
    # Scene-specific narrative props for the Mansa Musa brief and related historical stories.
    if contains_any(prompt, ('throne','emperor','crowned','king','sovereign')):
        tx,ty=int(w*.48),int(h*.53)
        d.rectangle((tx,ty,tx+int(w*.14),int(h*.74)),fill=(112,86,57),outline=INK,width=4)
        d.arc((tx,ty-int(h*.13),tx+int(w*.14),ty+int(h*.12)),180,360,fill=INK,width=5)
        d.rectangle((tx+int(w*.025),ty+int(h*.06),tx+int(w*.115),ty+int(h*.19)),fill=(157,132,87),outline=INK,width=3)
    if contains_any(prompt, ('gold','nugget','gold dust','golden')):
        for j in range(7):
            gx=int(w*(.57+(j%4)*.055)); gy=int(h*(.66-(j//4)*.025))
            d.ellipse((gx,gy,gx+int(w*.045),gy+int(h*.035)),fill=(171,139,76),outline=INK,width=2)
    if contains_any(prompt, ('staff','scepter','banner')):
        for j in range(3):
            sx=int(w*(.16+j*.055))
            d.line((sx,int(h*.42),sx,int(h*.72)),fill=(139,105,65),width=max(3,int(w*.004)))
            d.ellipse((sx-int(w*.006),int(h*.405),sx+int(w*.006),int(h*.43)),fill=(177,145,82),outline=INK)
def story_prop_kind(prompt):
    """Classify the main non-character object for a readable close-up illustration."""
    p=(prompt or "").lower()
    rules=[
        (("compass","navigation"),"compass"),
        (("lantern","lamp","light"),"lantern"),
        (("key","keys"),"key"),
        (("watch","pocket watch","clock"),"watch"),
        (("letter","telegram","message slip","sealed paper"),"letter"),
        (("map","chart","atlas","blueprint","route"),"map"),
        (("ledger","journal","record book","account book"),"ledger"),
        (("satchel","travel bag","travel chest","suitcase"),"satchel"),
        (("gear","mechanism","machine","engine"),"gear"),
        (("newspaper","timetable"),"paper"),
        (("telescope","spyglass"),"telescope"),
        (("scale","brass weight"),"scale"),
    ]
    for terms,kind in rules:
        if contains_any(p, terms):
            return kind
    return "object"


def draw_primary_story_prop(d,w,h,kind,phase=0.0,center_x=.70,center_y=.49,size_factor=1.0):
    """Draw one oversized, simple inked prop on the right side of the composition."""
    ink=INK
    cx,cy=w*center_x,h*center_y
    unit=min(w,h)*size_factor
    if kind=="map":
        box=(cx-unit*.22,cy-unit*.15,cx+unit*.22,cy+unit*.15)
        d.polygon([(box[0],box[1]+unit*.035),(box[0]+unit*.13,box[1]),(box[2],box[1]+unit*.025),
                   (box[2]-unit*.02,box[3]),(cx,box[3]-unit*.015),(box[0],box[3])],
                  fill=(221,208,177),outline=ink)
        d.line((cx-unit*.16,cy+unit*.075,cx-unit*.07,cy-unit*.035,cx+unit*.02,cy+unit*.045,
                cx+unit*.14,cy-unit*.075),fill=(143,75,59),width=max(3,int(unit*.008)))
        # A small moving marker makes the route legible without adding labels.
        marker_x=cx-unit*.13+((phase%math.tau)/math.tau)*unit*.24
        marker_y=cy+unit*.035-math.sin((phase%math.tau))*unit*.045
        d.ellipse((marker_x-unit*.012,marker_y-unit*.012,marker_x+unit*.012,marker_y+unit*.012),fill=(143,75,59))
        d.ellipse((cx+unit*.105,cy-unit*.11,cx+unit*.15,cy-unit*.065),outline=ink,width=3)
        # A tiny route marker travels along the inked path as the map is studied.
        marker=(phase%(math.tau))/math.tau
        mx=cx-unit*.16+marker*unit*.30
        my=cy+unit*.075-math.sin(marker*math.pi)*unit*.11
        d.ellipse((mx-unit*.014,my-unit*.014,mx+unit*.014,my+unit*.014),fill=(143,75,59),outline=ink,width=2)
    elif kind=="letter":
        d.rounded_rectangle((cx-unit*.18,cy-unit*.19,cx+unit*.18,cy+unit*.19),radius=int(unit*.012),
                            fill=(225,214,187),outline=ink,width=5)
        for j in range(5):
            yy=cy-unit*.10+j*unit*.045
            d.line((cx-unit*.12,yy,cx+unit*(.07 if j%2 else .12),yy-unit*.006),fill=(124,113,94),width=3)
        d.ellipse((cx+unit*.085,cy+unit*.105,cx+unit*.145,cy+unit*.165),fill=(151,83,67),outline=ink,width=3)
        fold=math.sin(phase*1.7)*unit*.009
        d.polygon([(cx+unit*.18,cy-unit*.19),(cx+unit*.18,cy-unit*.10+fold),(cx+unit*.09,cy-unit*.19)],
                  fill=(196,184,157),outline=ink)
    elif kind=="compass":
        r=unit*.19
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(207,196,169),outline=ink,width=6)
        d.ellipse((cx-r*.78,cy-r*.78,cx+r*.78,cy+r*.78),outline=(115,105,86),width=3)
        angle=phase*.85
        tip=(cx+math.sin(angle)*r*.68,cy-math.cos(angle)*r*.68)
        tail=(cx-math.sin(angle)*r*.30,cy+math.cos(angle)*r*.30)
        d.polygon([tip,(cx+unit*.035,cy+unit*.035),tail,(cx-unit*.035,cy+unit*.035)],
                  fill=(143,75,59),outline=ink)
        d.ellipse((cx-unit*.018,cy-unit*.018,cx+unit*.018,cy+unit*.018),fill=ink)
    elif kind=="lantern":
        d.arc((cx-unit*.10,cy-unit*.22,cx+unit*.10,cy+unit*.03),180,360,fill=ink,width=5)
        d.rounded_rectangle((cx-unit*.105,cy-unit*.12,cx+unit*.105,cy+unit*.18),radius=int(unit*.025),
                            fill=(151,139,111),outline=ink,width=5)
        flicker=.5+.5*math.sin(phase*3.1)
        glow=(min(235,int(205+18*flicker)),min(220,int(187+17*flicker)),min(185,int(148+18*flicker)))
        d.rectangle((cx-unit*.065,cy-unit*.075,cx+unit*.065,cy+unit*.12),fill=glow,outline=ink,width=3)
        flame_y=cy+unit*(.015+.012*math.sin(phase*2.4))
        d.ellipse((cx-unit*.018,flame_y-unit*.045,cx+unit*.018,flame_y+unit*.045),fill=(174,126,75),outline=(116,94,66),width=2)
        d.line((cx-unit*.12,cy+unit*.19,cx+unit*.12,cy+unit*.19),fill=ink,width=5)
    elif kind=="key":
        r=unit*.075
        d.ellipse((cx-unit*.19,cy-unit*.075,cx-unit*.04,cy+unit*.075),outline=ink,width=7)
        d.ellipse((cx-unit*.15,cy-unit*.035,cx-unit*.08,cy+unit*.035),outline=ink,width=3)
        key_sway=math.sin(phase*1.3)*unit*.012
        d.line((cx-unit*.04,cy+key_sway,cx+unit*.20,cy-key_sway),fill=ink,width=9)
        d.line((cx+unit*.12,cy-key_sway,cx+unit*.12,cy+unit*.075-key_sway),fill=ink,width=7)
        d.line((cx+unit*.18,cy-key_sway,cx+unit*.18,cy+unit*.05-key_sway),fill=ink,width=7)
    elif kind=="watch":
        r=unit*.17
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(218,207,181),outline=ink,width=6)
        d.ellipse((cx-r*.78,cy-r*.78,cx+r*.78,cy+r*.78),outline=ink,width=3)
        minute=phase*.22
        hour=phase*.018+math.pi*.18
        d.line((cx,cy,cx+math.sin(hour)*r*.43,cy-math.cos(hour)*r*.43),fill=ink,width=5)
        d.line((cx,cy,cx+math.sin(minute)*r*.68,cy-math.cos(minute)*r*.68),fill=ink,width=4)
        d.arc((cx-unit*.04,cy-unit*.24,cx+unit*.04,cy-unit*.14),180,360,fill=ink,width=4)
    elif kind=="ledger":
        d.polygon([(cx-unit*.19,cy-unit*.17),(cx,cy-unit*.14),(cx,cy+unit*.17),(cx-unit*.19,cy+unit*.14)],
                  fill=(170,143,108),outline=ink)
        d.polygon([(cx,cy-unit*.14),(cx+unit*.19,cy-unit*.17),(cx+unit*.19,cy+unit*.14),(cx,cy+unit*.17)],
                  fill=(220,207,178),outline=ink)
        for j in range(5):
            yy=cy-unit*.085+j*unit*.045
            d.line((cx-unit*.15,yy,cx-unit*.035,yy+unit*.005),fill=ink,width=2)
            d.line((cx+unit*.035,yy+unit*.005,cx+unit*.15,yy),fill=ink,width=2)
        d.line((cx,cy-unit*.14,cx,cy+unit*.17),fill=ink,width=4)
        page_lift=math.sin(phase*1.5)*unit*.008
        d.polygon([(cx+unit*.19,cy-unit*.17),(cx+unit*.19,cy-unit*.08+page_lift),
                   (cx+unit*.10,cy-unit*.17)],fill=(191,176,147),outline=ink)
    elif kind=="satchel":
        d.rounded_rectangle((cx-unit*.19,cy-unit*.08,cx+unit*.19,cy+unit*.17),radius=int(unit*.025),
                            fill=(142,117,88),outline=ink,width=6)
        strap_sway=math.sin(phase*1.4)*unit*.012
        d.arc((cx-unit*.10,cy-unit*.20+strap_sway,cx+unit*.10,cy+unit*.06+strap_sway),180,360,fill=ink,width=6)
        d.rectangle((cx-unit*.04,cy-unit*.01,cx+unit*.04,cy+unit*.055),fill=(206,190,155),outline=ink,width=3)
    elif kind=="gear":
        r=unit*.15
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(157,151,132),outline=ink,width=6)
        d.ellipse((cx-r*.36,cy-r*.36,cx+r*.36,cy+r*.36),fill=(215,204,179),outline=ink,width=4)
        for a in range(8):
            angle=math.tau*a/8+phase*.16
            x1=cx+math.cos(angle)*r*.72; y1=cy+math.sin(angle)*r*.72
            x2=cx+math.cos(angle)*r*1.22; y2=cy+math.sin(angle)*r*1.22
            d.line((x1,y1,x2,y2),fill=ink,width=max(4,int(unit*.025)))
    elif kind=="paper":
        d.rectangle((cx-unit*.18,cy-unit*.20,cx+unit*.18,cy+unit*.20),fill=(223,212,185),outline=ink,width=5)
        for j in range(7):
            yy=cy-unit*.13+j*unit*.04
            d.line((cx-unit*.13,yy,cx+unit*(.08 if j%3==0 else .13),yy),fill=(119,111,94),width=2)
        d.rectangle((cx-unit*.12,cy-unit*.16,cx+unit*.12,cy-unit*.12),outline=(132,77,62),width=2)
        corner=math.sin(phase*1.8)*unit*.01
        d.polygon([(cx+unit*.18,cy-unit*.20),(cx+unit*.18,cy-unit*.09+corner),
                   (cx+unit*.07,cy-unit*.20)],fill=(193,181,154),outline=ink)
    elif kind=="telescope":
        pivot=math.sin(phase*1.2)*.025
        ex=cx+unit*(.17-math.sin(pivot)*.10)
        ey=cy-unit*(.10+math.cos(pivot)*.02)
        d.line((cx-unit*.20,cy+unit*.10,ex,ey),fill=ink,width=max(5,int(unit*.07)))
        d.line((cx-unit*.19,cy+unit*.055,cx+unit*(.19-math.sin(pivot)*.08),cy-unit*(.15+math.cos(pivot)*.02)),fill=(163,148,118),width=max(5,int(unit*.035)))
        d.ellipse((ex-unit*.05,ey-unit*.10,ex+unit*.05,ey),fill=(191,184,162),outline=ink,width=4)
        d.line((cx,cy+unit*.07,cx-unit*.04,cy+unit*.20),fill=ink,width=4)
    elif kind=="scale":
        d.line((cx,cy-unit*.18,cx,cy+unit*.17),fill=ink,width=6)
        beam_angle=math.sin(phase*1.1)*.045
        left=(cx-unit*.17,cy-unit*.08+math.sin(beam_angle)*unit*.17)
        right=(cx+unit*.17,cy-unit*.08-math.sin(beam_angle)*unit*.17)
        d.line((left,right),fill=ink,width=6)
        for side,point in ((-1,left),(1,right)):
            sx,sy=point
            d.line((sx,sy,sx,sy+unit*.12),fill=ink,width=3)
            d.arc((sx-unit*.08,sy+unit*.07,sx+unit*.08,sy+unit*.22),0,180,fill=ink,width=4)
        d.line((cx-unit*.09,cy+unit*.17,cx+unit*.09,cy+unit*.17),fill=ink,width=6)
    else:
        d.rounded_rectangle((cx-unit*.16,cy-unit*.13,cx+unit*.16,cy+unit*.13),radius=int(unit*.025),
                            fill=(190,177,151),outline=ink,width=5)
        d.ellipse((cx-unit*.035,cy-unit*.035,cx+unit*.035,cy+unit*.035),outline=ink,width=3)


def draw_story_details(im,d,index,phase,scene):
    """Add large, legible story-specific ink illustrations to each scene."""
    w,h=im.size
    p=scene_description(scene)
    ink=INK
    if contains_any(p, ("night","midnight","moon","stars")):
        d.ellipse((w*.78,h*.08,w*.88,h*.22),fill=(225,218,195),outline=ink,width=4)
        rng=random.Random(index+310)
        for _ in range(18):
            x=rng.uniform(.05,.95)*w; y=rng.uniform(.04,.32)*h
            d.line((x-3,y,x+3,y),fill=(93,98,91),width=2)
            d.line((x,y-3,x,y+3),fill=(93,98,91),width=1)
    else:
        d.ellipse((w*.08,h*.10,w*.17,h*.24),fill=(211,197,164),outline=ink,width=4)
        for j in range(3):
            yy=h*(.18+j*.06)
            d.arc((w*(.27+j*.12),yy,w*(.42+j*.12),yy+h*.07),190,345,fill=(125,128,115),width=2)
    transport = scene_transport_kind(p)
    if transport in ("sea", "air") or contains_any(p, ("mountain",)):
        for j in range(3):
            bx=w*(.61+j*.045)+math.sin(phase+j)*w*.002; by=h*(.25+j*.025)
            d.arc((bx,by,bx+w*.018,by+h*.012),190,345,fill=ink,width=2)
    if transport == "rail":
        y=h*.66; x=w*.60
        d.rectangle((x,y-h*.16,w*.94,y),fill=(105,108,100),outline=ink,width=4)
        for j in range(2):
            xx=x+w*(.025+j*.13)
            d.rectangle((xx,y-h*.12,xx+w*.08,y-h*.055),fill=(211,201,177),outline=ink,width=3)
        for xx in (x+w*.06,x+w*.25):
            d.ellipse((xx,y-h*.035,xx+w*.055,y+h*.045),fill=(63,65,60),outline=ink,width=4)
        d.line((w*.54,h*.76,w*.98,h*.76),fill=ink,width=3)
    elif transport == "air":
        x=w*(.69+math.sin(phase)*.006); y=h*.36
        d.polygon([(x,y),(x+w*.20,y-h*.018),(x+w*.12,y+h*.018),(x+w*.07,y+h*.012)],fill=(119,124,116),outline=ink)
        if "parachute" in p:
            px=w*.81; py=h*.18
            d.arc((px-w*.06,py-h*.045,px+w*.06,py+h*.055),180,360,fill=ink,width=4)
            d.line((px-w*.05,py,px,py+h*.14,px+w*.05,py),fill=ink,width=2)
    elif contains_any(p, ("prison","cell","alcatraz","bars","jail")):
        x,y=w*.72,h*.34
        d.rectangle((x,y,x+w*.19,h*.72),fill=(99,103,96),outline=ink,width=5)
        for j in range(5):
            xx=x+w*(.025+j*.035); d.line((xx,y,xx,h*.72),fill=(43,46,43),width=4)
        d.rectangle((x+w*.04,h*.56,x+w*.15,h*.70),fill=(174,163,139),outline=ink,width=3)
    elif contains_any(p, ("clock","watch","time","hour","minute")):
        x,y=w*.77,h*.42; r=min(w,h)*.105
        d.ellipse((x-r,y-r,x+r,y+r),fill=(220,211,190),outline=ink,width=5)
        for j in range(12):
            a=math.tau*j/12
            d.ellipse((x+math.sin(a)*r*.82-2,y-math.cos(a)*r*.82-2,x+math.sin(a)*r*.82+2,y-math.cos(a)*r*.82+2),fill=ink)
        a=phase*.05
        d.line((x,y,x+math.sin(a)*r*.55,y-math.cos(a)*r*.55),fill=ink,width=4)
        d.line((x,y,x+r*.48,y+r*.20),fill=ink,width=3)
    elif contains_any(p, ("museum","painting","artwork","gallery","portrait")):
        x,y=w*.70,h*.30
        d.rectangle((x,y,x+w*.20,y+h*.31),fill=(111,89,65),outline=ink,width=5)
        d.rectangle((x+w*.018,y+h*.025,x+w*.182,y+h*.285),fill=(211,198,170),outline=ink,width=3)
        d.arc((x+w*.055,y+h*.06,x+w*.15,y+h*.25),180,350,fill=(115,120,105),width=4)
    elif contains_any(p, ("telegraph","cable","wire","signal","message")):
        for x in (w*.68,w*.91):
            d.line((x,h*.28,x,h*.70),fill=ink,width=5)
            d.line((x-w*.025,h*.34,x+w*.025,h*.34),fill=ink,width=4)
        d.arc((w*.68,h*.29,w*.91,h*.49),180,360,fill=(78,82,75),width=3)
    elif contains_any(p, ("spacecraft","rocket","moon landing","lunar","astronaut")):
        x,y=w*.78,h*.39
        d.polygon([(x,y-h*.12),(x+w*.035,y-h*.04),(x+w*.035,y+h*.10),(x-w*.01,y+h*.10),(x-w*.01,y-h*.04)],fill=(193,187,169),outline=ink,width=4)
        d.polygon([(x-w*.01,y-h*.04),(x-w*.045,y+h*.04),(x-w*.01,y+h*.035)],fill=(147,139,120),outline=ink)
        d.polygon([(x+w*.035,y-h*.04),(x+w*.07,y+h*.04),(x+w*.035,y+h*.035)],fill=(147,139,120),outline=ink)
    elif contains_any(p, ("mine","mining","tunnel","underground","cave")):
        x,y=w*.70,h*.38
        d.arc((x,y-h*.13,x+w*.22,y+h*.20),180,360,fill=ink,width=6)
        d.rectangle((x,y,x+w*.22,h*.72),fill=(83,85,78),outline=ink,width=4)
        d.rectangle((x+w*.045,y+h*.10,x+w*.175,h*.72),fill=(48,51,48),outline=ink,width=3)
    elif contains_any(p, ("book","manuscript","letter","document","ledger","archive","library","paper")):
        x,y=w*.68,h*.49
        d.polygon([(x,y),(x+w*.17,y-h*.035),(x+w*.19,y+h*.15),(x+w*.02,y+h*.19)],fill=(220,207,176),outline=ink)
        for j in range(3):
            d.line((x+w*.03,y+h*(.035+j*.04),x+w*.15,y+h*(.005+j*.04)),fill=(119,108,88),width=2)
    elif contains_any(p, ("door","room","office","meeting","desk","council")):
        x,y=w*.75,h*.30
        d.rectangle((x,y,x+w*.16,h*.72),fill=(139,119,91),outline=ink,width=5)
        d.arc((x+w*.02,y-h*.06,x+w*.14,y+h*.13),180,360,fill=ink,width=4)
        d.ellipse((x+w*.13,h*.52,x+w*.145,h*.54),fill=(225,210,174),outline=ink)
    # Distinct, readable illustrated motifs for historical events that do not fit
    # the broad transport / archive categories above. Keep these symbolic and safe.
    if contains_any(p, ("molasses","flood","overflow","rising water","inundat")):
        # Layered wave bands and a small street-side tank make the event legible.
        for j in range(4):
            yy=h*(.57+j*.045)+math.sin(phase*1.4+j)*h*.006
            d.arc((w*.04,yy,w*.62,yy+h*.12),185,350,fill=(105,77,55),width=max(3,int(w*.003)))
        d.rectangle((w*.72,h*.34,w*.88,h*.60),fill=(125,111,91),outline=ink,width=5)
        d.arc((w*.72,h*.27,w*.88,h*.43),180,360,fill=ink,width=4)
    if contains_any(p, ("volcano","eruption","ash cloud","pompeii")):
        d.polygon([(w*.54,h*.69),(w*.68,h*.35),(w*.77,h*.48),(w*.87,h*.27),(w*.98,h*.69)],
                  fill=(112,108,96),outline=ink)
        d.ellipse((w*.68,h*.13,w*.91,h*.35),fill=(151,145,128),outline=ink,width=3)
        for j in range(5):
            xx=w*(.70+j*.045)
            d.ellipse((xx,h*(.20+(j%2)*.035),xx+w*.025,h*(.24+(j%2)*.035)),fill=(151,145,128))
    if contains_any(p, ("canal","lock gate","waterway","panama")):
        d.polygon([(w*.50,h*.38),(w*.68,h*.38),(w*.84,h*.76),(w*.35,h*.76)],
                  fill=(137,153,145),outline=ink)
        for xx in (.53,.76):
            d.line((w*xx,h*.35,w*xx,h*.72),fill=(83,86,79),width=6)
        d.line((w*.37,h*.58,w*.82,h*.58),fill=(83,86,79),width=4)
    if contains_any(p, ("telegraph","morse","telegram","transatlantic cable","signal")):
        for j in range(7):
            xx=w*(.10+j*.12)
            d.line((xx,h*.45,xx,h*.69),fill=ink,width=3)
            d.ellipse((xx-w*.008,h*.42,xx+w*.008,h*.46),fill=(154,137,105),outline=ink)
        d.arc((w*.10,h*.32,w*.82,h*.62),190,350,fill=(71,77,71),width=3)
    if contains_any(p, ("smog","fog","pollution","industrial haze","soot")):
        for j in range(5):
            yy=h*(.25+j*.075)+math.sin(phase+j)*h*.008
            d.arc((w*(.12+j*.035),yy,w*(.82-j*.025),yy+h*.12),180,350,
                  fill=(159,158,146),width=max(4,int(w*.006)))
        for j in range(3):
            xx=w*(.60+j*.09)
            d.rectangle((xx,h*.43,xx+w*.055,h*.70),fill=(116,116,105),outline=ink,width=3)
            d.rectangle((xx+w*.012,h*.30,xx+w*.027,h*.44),fill=(92,95,88),outline=ink,width=2)
    if contains_any(p, ("arctic","expedition","ice floe","polar","franklin")):
        for j in range(4):
            xx=w*(.52+j*.11); yy=h*(.57+(j%2)*.07)
            d.polygon([(xx,yy),(xx+w*.10,yy-h*.035),(xx+w*.18,yy),(xx+w*.11,yy+h*.035)],
                      fill=(206,208,195),outline=ink)
        d.line((w*.72,h*.18,w*.72,h*.55),fill=ink,width=4)
        d.polygon([(w*.72,h*.20),(w*.84,h*.40),(w*.72,h*.40)],fill=(208,201,180),outline=ink)
    if contains_any(p, ("library of alexandria","ancient library","scroll","papyrus")):
        for j in range(5):
            xx=w*(.56+j*.075)
            d.rectangle((xx,h*.35,xx+w*.052,h*.70),fill=(135,112,83),outline=ink,width=3)
            for k in range(3):
                yy=h*(.40+k*.085)
                d.line((xx+w*.009,yy,xx+w*.043,yy),fill=(218,205,177),width=3)
    if contains_any(p, ("earthquake","san francisco","collapsed building","rebuilding")):
        for j in range(3):
            xx=w*(.58+j*.12)
            d.polygon([(xx,h*.70),(xx,h*.43),(xx+w*.08,h*.38),(xx+w*.10,h*.70)],
                      fill=(157,148,128),outline=ink)
            d.line((xx+w*.025,h*.48,xx+w*.045,h*.54,xx+w*.035,h*.61),fill=ink,width=3)
    if contains_any(p, ("race to the south pole","south pole","antarctic race")):
        for j in range(3):
            xx=w*(.60+j*.10); yy=h*(.58+(j%2)*.035)
            d.line((xx,yy,xx,yy-h*.16),fill=ink,width=3)
            d.polygon([(xx,yy-h*.16),(xx+w*.065,yy-h*.12),(xx,yy-h*.08)],
                      fill=(170,150,121),outline=ink)
    # In close-up beats, give the story's named object a large, clean silhouette.
    # This is the focal subject; the recurring figure remains a small observer.
    if "close-up" in (scene.get("camera","") or "").lower():
        draw_primary_story_prop(d,w,h,story_prop_kind(p),phase)
    # Light foreground hatching adds imperfect hand-inked contours without clutter.
    rng=random.Random(index+909)
    for _ in range(18):
        x=rng.uniform(.03,.97)*w; y=rng.uniform(.73,.94)*h
        d.line((x,y,x+rng.uniform(.008,.025)*w,y-rng.uniform(.001,.009)*h),fill=(113,111,96),width=1)
    if contains_any(p, ("street","city","market","crowd","harbour","port")):
        for j in range(4):
            x=w*(.03+j*.13); y=h*.69
            d.ellipse((x,y-h*.035,x+w*.025,y+h*.005),fill=(104,104,94),outline=ink,width=2)
            d.polygon([(x+w*.005,y),(x+w*.02,y),(x+w*.026,y+h*.09),(x,y+h*.09)],fill=(104,104,94),outline=ink)

_TEXTURE_CACHE = {}

def apply_house_texture(im,scene_index):
    """Reuse one subtle paper-grain overlay for every frame in a scene."""
    w,h=im.size
    key=(w,h,scene_index)
    overlay=_TEXTURE_CACHE.get(key)
    if overlay is None:
        overlay=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(overlay)
        rng=random.Random(scene_index+1701)
        for _ in range(max(700,w*h//90000)):
            x=rng.randrange(w); y=rng.randrange(h)
            d.point((x,y),fill=(38,34,27,rng.randrange(5,15)))
        for y in range(0,h,5):
            d.line((0,y,w,y),fill=(32,30,26,9),width=1)
        _TEXTURE_CACHE.clear()
        _TEXTURE_CACHE[key]=overlay
    im.paste(Image.alpha_composite(im.convert("RGBA"),overlay).convert("RGB"))

def character_scale(width,height,camera=""):
    """Return a frame-aware character scale with shot-specific framing."""
    camera=(camera or "").lower()
    scale=(height/720) if width/height<=1 else min(width/1280,height/720)
    if "wide silhouette" in camera:
        scale*=.62
    elif "wide establishing" in camera:
        scale*=.78
    elif "side-on tracking" in camera:
        scale*=.88
    elif "overhead" in camera:
        scale*=.72
    elif "low-angle" in camera:
        scale*=1.08
    elif "interior" in camera:
        scale*=.92
    return scale


def scene_composition(width,height,camera="",frame=0,total_frames=1):
    """Choose a readable subject scale and position for the semantic camera shot."""
    camera=(camera or "").lower()
    scale=character_scale(width,height,camera)
    x_fraction=.50
    y_fraction=.70
    if "close-up" in camera:
        # Keep the recurring character as a small foreground observer while
        # the story-specific prop on the right becomes the visual subject.
        scale*=.55
        x_fraction=.16
        y_fraction=.82
    elif "wide silhouette" in camera:
        x_fraction=.76
        y_fraction=.73
    elif "wide establishing" in camera:
        x_fraction=.28
        y_fraction=.73
    elif "side-on tracking" in camera:
        x_fraction=.18+.64*(frame/max(1,total_frames-1))
        y_fraction=.70
    elif "overhead" in camera:
        x_fraction=.54
        y_fraction=.72
    elif "low-angle" in camera:
        x_fraction=.52
        y_fraction=.64
    elif "interior" in camera:
        x_fraction=.50
        y_fraction=.70
    return scale,x_fraction,y_fraction


def camera_crop_box(width,height,camera="",frame=0,total_frames=1):
    """Return a gentle per-frame camera crop for restrained cinematic movement."""
    camera=(camera or "").lower()
    progress=max(0.0,min(1.0,frame/max(1,total_frames-1)))
    zoom=1.0
    pan_x=0.0
    pan_y=0.0
    if "close-up" in camera:
        zoom=1.015+0.012*progress
    elif "wide establishing" in camera:
        zoom=1.0+0.035*progress
    elif "side-on tracking" in camera:
        zoom=1.025
        pan_x=-0.035+0.07*progress
    elif "overhead" in camera:
        zoom=1.018
        pan_x=0.012*math.sin(progress*math.pi*2)
        pan_y=-0.008*progress
    elif "low-angle" in camera:
        zoom=1.0+0.025*progress
        pan_y=-0.012*progress
    elif "interior" in camera:
        zoom=1.0+0.018*progress
    elif "wide silhouette" in camera:
        zoom=1.0+0.012*progress
    crop_w=width/zoom
    crop_h=height/zoom
    center_x=width*(.5+pan_x)
    center_y=height*(.5+pan_y)
    left=max(0.0,min(width-crop_w,center_x-crop_w/2))
    top=max(0.0,min(height-crop_h,center_y-crop_h/2))
    return (int(round(left)),int(round(top)),
            int(round(left+crop_w)),int(round(top+crop_h)))


def blend_scene_transition(previous,current,frame,transition_frames=3):
    """Cross-dissolve the opening frames of a scene from the prior scene's final frame."""
    if previous is None or transition_frames <= 0 or frame >= transition_frames:
        return current
    progress=(frame+1)/transition_frames
    return Image.blend(previous.convert("RGB"),current.convert("RGB"),progress)


def atmosphere_particles(scene,frame,total_frames,width,height):
    """Return deterministic, gently moving environmental particles for a story beat."""
    prompt=scene_description(scene)
    progress=max(0.0,frame/max(1,total_frames-1))
    rng=random.Random(int(scene.get("scene_index",0))+41)
    particles=[]
    if contains_any(prompt, ("snow","winter","ice","antarctic")):
        kind="snow"; count=34
    elif contains_any(prompt, ("rain","storm","wet")):
        kind="rain"; count=58
    elif contains_any(prompt, ("steam","factory","train","engine","smoke","fog")):
        kind="steam"; count=18
    elif contains_any(prompt, ("wind","dust","desert","sea","ocean","ship")):
        kind="dust"; count=16
    else:
        kind="dust"; count=8
    for j in range(count):
        base_x=rng.random()*width
        base_y=rng.random()*height
        if kind=="rain":
            x=(base_x+progress*width*.16+j*17)%width
            y=(base_y+progress*height*.65+j*11)%height
        elif kind=="snow":
            x=(base_x+math.sin(progress*math.pi*2+j)*width*.018)%width
            y=(base_y+progress*height*.12+j*5)%height
        elif kind=="steam":
            x=(base_x+math.sin(progress*math.pi*2+j*.7)*width*.012)%width
            y=(base_y-progress*height*.09-j*2)%height
        else:
            x=(base_x+progress*width*(.025+j*.001))%width
            y=base_y+math.sin(progress*math.pi*2+j)*height*.012
        particles.append((kind,int(x),int(y)))
    return particles


def draw_atmosphere(draw,scene,frame,total_frames,width,height):
    """Draw restrained motion accents without adding expensive render dependencies."""
    for kind,x,y in atmosphere_particles(scene,frame,total_frames,width,height):
        if kind=="rain":
            draw.line((x,y,x-width*.006,y+height*.018),fill=(111,121,116),width=max(1,int(width*.0015)))
        elif kind=="snow":
            radius=max(2,int(width*.0025))
            draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=(239,235,220))
        elif kind=="steam":
            radius=max(3,int(width*.006))
            draw.ellipse((x-radius,y-radius*.35,x+radius,y+radius*.35),fill=(194,190,174))
        else:
            draw.ellipse((x,y,x+width*.009,y+height*.0035),fill=(205,198,178))


def draw_frame(scene,project,frame,total_frames,out):
    # Draw above delivery resolution, then downsample once with Lanczos. This
    # smooths the hand-inked linework and small facial details without changing
    # the exported frame size or asking the free CPU worker for a GPU.
    output_w,output_h=dimensions(project.get("aspect_ratio","16:9"))
    render_scale=1.5
    w,h=int(round(output_w*render_scale)),int(round(output_h*render_scale))
    im=Image.new("RGB",(w,h),PAPER); d=ImageDraw.Draw(im)
    phase=2*math.pi*frame/max(1,total_frames)
    camera=(scene.get("camera","") or "").lower()
    closeup="close-up" in camera
    draw_background(im,d,int(scene.get("scene_index",0)),phase,scene,closeup=closeup)
    if closeup:
        # Render only the focal prop on this clean stage; drawing the full scene
        # details as well creates duplicate, overlapping versions of the same object.
        draw_primary_story_prop(d,w,h,story_prop_kind(scene_description(scene)),phase)
    else:
        draw_story_details(im,d,int(scene.get("scene_index",0)),phase,scene)
    prompt=scene_description(scene)
    draw_atmosphere(d,scene,frame,total_frames,w,h)
    # Framing follows the output orientation and the semantic shot selected
    # by the storyboard engine; portrait figures stay readable without clipping.
    scale,x_fraction,y_fraction=scene_composition(w,h,camera,frame,total_frames)
    names=scene.get("characters",["Narrator"])
    positions=[x_fraction] if len(names)==1 else ([.30,.52,.74] if w/h>1 else [.36,.66,.50])
    action=scene.get("action","idle")
    for j,name in enumerate(names[:3]):
        drift=math.sin(phase*2+j)*w*.004
        if action=="walk" and len(names)==1:
            positions[j]=.20+.60*(frame/max(1,total_frames-1))
        x=int(w*positions[j]+drift); y=int(h*y_fraction)
        color=project.get("characters",{}).get(name,{}).get("color","#34465a")
        rgb=tuple(int(color[k:k+2],16) for k in (1,3,5))
        # A soft, restrained ground shadow anchors the figure to the illustrated set.
        foot_y=y+174*scale
        shadow_w=46*scale
        d.ellipse((x-shadow_w,foot_y-5*scale,x+shadow_w,foot_y+7*scale),
                  fill=(126,119,102))
        draw_person(d,x,y,scale,rgb,phase+j,int(scene.get("scene_index",0))%3,name,action,scene.get("expression","neutral"))
    apply_house_texture(im,int(scene.get("scene_index",0)))
    # The brief prohibits burned-in titles, captions and subtitles.
    vign=Image.new("L",(w,h),0); vd=ImageDraw.Draw(vign)
    vd.ellipse((-w*.12,-h*.12,w*1.12,h*1.12),fill=230)
    vign=vign.filter(ImageFilter.GaussianBlur(max(10,int(w*.07))))
    dark=Image.new("RGB",(w,h),(15,16,15)); im=Image.composite(im,dark,vign)
    # A restrained crop animation gives each semantic shot camera movement
    # without changing the requested output dimensions or requiring 3D/GPU tools.
    crop=camera_crop_box(w,h,camera,frame,total_frames)
    im=im.crop(crop).resize((w,h),Image.Resampling.LANCZOS)
    # Keep the public video dimensions unchanged; only the drawing pass is larger.
    im=im.resize((output_w,output_h),Image.Resampling.LANCZOS)
    im.save(out,quality=94)
def ambience_profile(scene):
    """Choose a restrained sound-bed profile from the illustrated environment."""
    prompt=(str(scene.get("visual",""))+" "+str(scene.get("title",""))+" "+str(scene.get("visual_prompt",""))).lower()
    if contains_any(prompt, ("rain","storm","wet")): return (640,92,.62)
    if contains_any(prompt, ("sea","ocean","ship","harbour","port")): return (430,54,.72)
    if contains_any(prompt, ("wind","desert","snow","mountain","antarctic")): return (360,66,.58)
    if contains_any(prompt, ("machine","factory","engine","train","clock","workshop")): return (250,78,.42)
    if contains_any(prompt, ("library","archive","room","office","court","interior")): return (105,38,.25)
    if contains_any(prompt, ("market","street","crowd","city")): return (185,120,.30)
    return (125,46,.30)


def synthesize_ambience(scene,destination,duration):
    """Create a softly shaped, non-musical ambient bed using only Python's standard library."""
    amp,freq,noise_mix=ambience_profile(scene)
    rate=24000; count=max(1,int(rate*duration)); rng=random.Random(scene.get("scene_index",0)+701)
    samples=array("h")
    fade=min(.32,max(.04,duration*.12))
    for i in range(count):
        t=i/rate
        # Slow amplitude movement avoids a flat synthetic drone.
        swell=.78+.22*math.sin(2*math.pi*.11*t+0.4)
        low=math.sin(2*math.pi*freq*t)*amp*.34
        undertone=math.sin(2*math.pi*(freq*.47)*t+0.7)*amp*.12
        noise=rng.uniform(-1,1)*amp*noise_mix
        fade_in=min(1.0,t/fade)
        fade_out=min(1.0,max(0.0,(duration-t)/fade))
        envelope=min(fade_in,fade_out)*swell
        sample=(low+undertone+noise)*envelope
        samples.append(int(max(-32767,min(32767,sample))))
    with wave.open(str(destination),"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate); wf.writeframes(samples.tobytes())

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
def render_project(project,outdir:Path,progress_callback=None):
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg: raise RuntimeError("FFmpeg is not installed in the cloud worker")
    clips=[]; audios=[]; sd=outdir/"scenes"; sd.mkdir(exist_ok=True)
    voice_engine=None
    previous_scene_frame=None
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
        for f in range(frames):
            frame_path=frames_dir/f"frame_{f:05d}.png"
            draw_frame(scene,project,f,frames,frame_path)
            if i > 0 and f < 3 and previous_scene_frame is not None:
                with Image.open(frame_path) as current_image:
                    transitioned=blend_scene_transition(previous_scene_frame,current_image,f,3)
                    transitioned.save(frame_path,quality=94)
        # Retain only one decoded frame between scenes for a short visual dissolve.
        with Image.open(frames_dir/f"frame_{frames-1:05d}.png") as last_image:
            previous_scene_frame=last_image.convert("RGB").copy()
        clip=sd/f"clip_{i:03d}.mp4"
        width,height=dimensions(project.get("aspect_ratio","16:9"))
        camera=(scene.get("camera","") or "").lower()
        zoom_expr="min(zoom+0.0007,1.05)"
        x_expr="iw/2-(iw/zoom/2)"
        y_expr="ih/2-(ih/zoom/2)"
        if "pull-back" in camera:
            zoom_expr="max(1.05-on*0.0005,1.0)"
        elif "close-up" in camera:
            # The right-side story prop is the focal subject in close-up shots.
            zoom_expr="min(1.35+on*0.001,1.40)"
            x_expr="min(iw-iw/zoom,max(0,iw*0.70-iw/zoom/2))"
        if "lateral pan" in camera or "tracking" in camera:
            x_expr="min(iw-iw/zoom,max(0,iw/2-(iw/zoom/2)+on*0.22))"
        elif "gentle pan" in camera:
            x_expr="min(iw-iw/zoom,max(0,iw/2-(iw/zoom/2)-on*0.16))"
        if "tilt upward" in camera:
            y_expr="max(0,ih/2-(ih/zoom/2)-on*0.12)"
        camera_filter=f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d=2:s={width}x{height}:fps=24,format=yuv420p"
        run([ffmpeg,"-y","-loglevel","error","-framerate",str(FPS),"-i",str(frames_dir/"frame_%05d.png"),
             "-vf",camera_filter,"-c:v","libx264","-preset","veryfast","-crf","19",str(clip)])
        shutil.rmtree(frames_dir,ignore_errors=True); gc.collect()
        # Pad each narration beat to its matching clip duration so the voice remains
        # distributed throughout the full episode instead of ending early and leaving silence.
        padded_wav=sd/f"voice_padded_{i:03d}.wav"
        pad_seconds=max(0.0,clip_duration-speech_seconds)
        run([ffmpeg,"-y","-loglevel","error","-i",str(wav),"-af",f"apad=pad_dur={pad_seconds:.3f}",
             "-t",f"{clip_duration:.3f}","-ar","24000","-ac","1",str(padded_wav)])
        ambience=sd/f"ambience_{i:03d}.wav"
        synthesize_ambience(scene,ambience,clip_duration)
        mixed=sd/f"mixed_audio_{i:03d}.wav"
        run([ffmpeg,"-y","-loglevel","error","-i",str(padded_wav),"-i",str(ambience),
             "-filter_complex","[0:a]volume=1.0[v];[1:a]volume=0.16[a];[v][a]amix=inputs=2:duration=first:dropout_transition=0[m]",
             "-map","[m]","-ar","24000","-ac","1",str(mixed)])
        clips.append(clip); audios.append(mixed)
        if progress_callback:
            progress_callback(i+1,len(project["scenes"]))
    concat=outdir/"clips.txt"; concat.write_text("".join(f"file '{x.resolve().as_posix()}'\n" for x in clips))
    audio_list=outdir/"audio.txt"; audio_list.write_text("".join(f"file '{x.resolve().as_posix()}'\n" for x in audios))
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
    # Reuse the same story-specific illustration language, but stage the main
    # prop in the open centre-left area so the headline has its own clean panel.
    thumbnail_scene=dict(first_scene)
    thumbnail_scene["camera"]=""
    draw_story_details(thumb_im,td,0,0,thumbnail_scene)
    prop_prompt=scene_description(first_scene)
    draw_primary_story_prop(td,1280,720,story_prop_kind(prop_prompt),0.0,center_x=.56,center_y=.49,size_factor=.72)
    name=(first_scene.get("characters") or ["Narrator"])[0]
    color=project.get("characters",{}).get(name,{}).get("color","#34465a")
    rgb=tuple(int(color[k:k+2],16) for k in (1,3,5))
    draw_person(td,270,500,1.0,rgb,0,0,name,"observe")
    apply_house_texture(thumb_im,0)
    words=re.findall(r"[A-Za-z0-9']+",project.get("thumbnail_headline",project.get("title","STICKMAN STORY")).upper())[:4]
    headline=" ".join(words) or "STICKMAN STORY"
    td.rounded_rectangle((850,190,1225,555),radius=18,fill=(30,32,29),outline=(192,174,137),width=5)
    lines=textwrap.wrap(headline,width=9)[:3]
    td.multiline_text((875,260),"\n".join(lines),font=font(52,True),fill=(244,237,218),spacing=8,stroke_width=1,stroke_fill=INK)
    thumb_im.save(thumb,quality=92)
    project["thumbnail_path"]=str(thumb)
    # A completed project only needs its verified MP4, thumbnail and metadata.
    # Scene PNGs, per-scene WAV/MP3 files, intermediate clips and concat lists can
    # consume substantial disk space (especially for a 10-minute production).
    # Remove them only after both deliverables have been written successfully.
    shutil.rmtree(sd,ignore_errors=True)
    for temporary in (concat,audio_list,silent,voice):
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return final
