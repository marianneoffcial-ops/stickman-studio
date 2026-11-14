import math, re, uuid

HOUSE_STYLE = ("Hand-inked 2D illustrated animation with thick slightly rough black ink outlines of varying weight. "
"Characters are simple stick figures with a large perfectly round white head, small solid black oval eyes, thin curved eyebrow strokes, a single simple curved line for the mouth, no nose, and a few loose ink strokes suggesting hair across the top of the head. "
"Bodies are minimal with softly rounded shoulders and flat muted clothing in desaturated colours such as navy blue, brick red and olive. "
"Backgrounds are flat hand-drawn illustrated environments in a muted earthy palette of tan, sage, dusty grey and cream, outlined in the same black ink, with simple geometric architecture and sparse detail. "
"A fine horizontal scanline and paper-grain texture overlays the entire frame, with a soft dark vignette at the edges. "
"Cinematic desaturated colour grade, restrained and slightly melancholy, no bright saturated colours, no gradients, no photorealism, no 3D render, no anime, no glossy digital finish.")

IDEAS = [
 ("The Great Molasses Flood of 1919","A Boston neighbourhood was overwhelmed by an extraordinary wave of molasses."),
 ("The Disappearance of the Mary Celeste","A merchant ship was found drifting at sea with its crew missing."),
 ("The Great Escape from Alcatraz","Three prisoners vanished, leaving a mystery that still fascinates investigators."),
 ("The Cuban Missile Crisis Officer","One officer's decision during a nuclear standoff may have changed history."),
 ("The Lost City of Pompeii","Everyday Roman life was preserved beneath layers of volcanic ash."),
 ("The Man Who Sold the Eiffel Tower","A con artist persuaded businessmen that he could sell a famous landmark."),
 ("The 1914 Christmas Truce","Opposing soldiers briefly shared an extraordinary moment of peace."),
 ("The Great Emu War","Australia's campaign against crop-raiding emus became an unlikely historical episode."),
 ("The Mystery of D. B. Cooper","A hijacker parachuted from an aircraft and was never conclusively identified."),
 ("The Race to Reach the South Pole","Two expeditions crossed Antarctica in a dramatic race against time."),
 ("The Great Fire of London","A small bakery fire became a turning point in the city's history."),
 ("The Franklin Expedition","Two ships vanished in the Arctic, leaving clues that took generations to uncover."),
 ("The Great Stink of 1858","A summer heatwave exposed the crisis beneath London's streets."),
 ("The First Transatlantic Telegraph Cable","A fragile cable briefly connected messages across an ocean."),
 ("The Panama Canal","Engineers reshaped a narrow land bridge to connect two oceans."),
 ("The Apollo 13 Rescue","A damaged spacecraft forced its crew and ground teams into an improvised survival plan."),
 ("The 1904 Olympic Marathon","A chaotic race became one of the strangest episodes in Olympic history."),
 ("The Great Train Robbery of 1963","Investigators followed a trail of clues after a carefully planned railway heist."),
 ("The Isabella Stewart Gardner Museum Heist","Thieves stole priceless artworks that have never been recovered."),
 ("Operation Mincemeat","A forged identity and planted papers helped misdirect wartime planners."),
 ("The 1952 Great Smog of London","Several days of trapped pollution changed public health policy."),
 ("The Chilean Miners Rescue","Thirty-three miners waited underground while an extraordinary rescue operation took shape."),
 ("The Tunguska Event","A vast Siberian forest was flattened by an explosion in the sky."),
 ("The 1969 Moon Landing","A small crew carried out a carefully planned journey to another world."),
 ("The Great Canadian Maple Syrup Heist","Millions of dollars in maple syrup vanished from a strategic reserve."),
 ("The Han van Meegeren Art Forgery","A painter fooled experts with convincingly forged old-master works."),
 ("The Great Library of Alexandria","The library's long history is more complicated than the famous legend."),
 ("The 1906 San Francisco Earthquake","A major earthquake transformed the city and its rebuilding."),
 ("The 1972 Andes Flight Disaster","Survivors faced an extreme high-altitude ordeal and a difficult rescue."),
 ("The Race to Decode the Rosetta Stone","Scholars used one ancient inscription to unlock a lost writing system.")
]

CHARACTERS = {
 "Narrator":{"costume":"desaturated navy coat","color":"#34465a"},
 "Emperor":{"costume":"muted olive robes and geometric gold crown","color":"#737653"},
 "Herald":{"costume":"brick-red tunic and tall ochre staff","color":"#9a5144"},
 "Merchant":{"costume":"dusty navy merchant robe","color":"#536276"},
 "Architect":{"costume":"muted sage robe","color":"#737d68"},
 "Scholar":{"costume":"muted sage robe","color":"#737d68"},
 "Traveler":{"costume":"deep navy desert robe","color":"#34465a"},
 "Witness":{"costume":"brick-red scarf","color":"#9a5144"},
 "Official":{"costume":"charcoal coat","color":"#55565a"}
}

CAMERAS = [
 "wide establishing shot with slow push-in",
 "medium character composition with gentle lateral pan",
 "close-up of a story-specific object with slow push-in",
 "overhead illustrated map composition with gentle pan",
 "low-angle architectural view with slow tilt upward",
 "side-on tracking composition with figures crossing frame",
 "wide silhouette composition with slow pull-back",
 "interior tableau with subtle camera drift"
]

def _sentences(text):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]

def _chunk_script(script, count):
    words = re.findall(r"\S+", script or "")
    if not words:
        return []
    sentences = _sentences(script)
    target = max(1, math.ceil(len(words) / max(1, count)))
    chunks, current = [], []
    for sentence in sentences:
        sw = sentence.split()
        if current and len(current) + len(sw) > target * 1.35 and len(chunks) < count - 1:
            chunks.append(" ".join(current))
            current = []
        current.extend(sw)
    if current:
        chunks.append(" ".join(current))
    while len(chunks) > count:
        idx = min(range(len(chunks)-1), key=lambda i: len(chunks[i].split()) + len(chunks[i+1].split()))
        chunks[idx:idx+2] = [chunks[idx] + " " + chunks[idx+1]]
    while len(chunks) < count:
        idx = max(range(len(chunks)), key=lambda i: len(chunks[i].split()))
        ws = chunks[idx].split()
        if len(ws) < 2:
            break
        mid = len(ws)//2
        chunks[idx:idx+1] = [" ".join(ws[:mid]), " ".join(ws[mid:])]
    return chunks

def _between(text, start, end):
    a = text.find(start)
    if a < 0:
        return ""
    a += len(start)
    b = text.find(end, a)
    return text[a:b].strip() if b >= 0 else text[a:].strip()

def parse_production_brief(brief):
    """Parse the user's two-part production brief into independent Shorts and long-form packages."""
    raw = (brief or "").replace("\r", "")
    short_script = _between(raw, "1. Voiceover Script", "2. Character & Asset Sheet")
    long_script = _between(raw, "Chapter Structure & Voiceover Script", "2. Character Sheet & Thumbnail")
    short_section = _between(raw, "3. Animation Prompts", "PART 2:")
    short_scenes = re.findall(r"Scene\s+\d+\s*\([^)]*\):\s*(.*?)(?=\n\s*\d+\.\s*Scene|$)", short_section, re.S)
    long_section = _between(raw, "3. Act-by-Act Visual Storyboard Prompts", "(Note:")
    long_anchors = re.findall(r"•\s*Act\s+[^:]+:\s*(.*?)(?=\n•\s*Act|$)", long_section, re.S)
    short_scenes = [re.sub(r"\s+", " ", x).strip() for x in short_scenes if x.strip()]
    long_anchors = [re.sub(r"\s+", " ", x).strip() for x in long_anchors if x.strip()]
    if not short_script:
        short_script = _between(raw, "Voiceover Script", "Character & Asset Sheet")
    short_script = re.sub(r"^\s*\([^)]*\)\s*", "", short_script)
    if not long_script:
        long_script = _between(raw, "Act I: The Hidden Empire of Gold", "2. Character Sheet & Thumbnail")
        if long_script:
            long_script = "Act I: The Hidden Empire of Gold " + long_script
    else:
        start = long_script.find("Act I: The Hidden Empire of Gold")
        if start >= 0:
            long_script = long_script[start:]
    if not long_anchors:
        long_anchors = [re.sub(r"\s+", " ", x).strip() for x in re.findall(r"•\s*Act\s+[^:]+:\s*(.*)", long_section) if x.strip()]
    combined = short_script + " " + long_script
    topic = ""
    for pattern in (r"\bHis name (?:was|is) ([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})", r"\bstory of ([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})", r"\babout ([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})"):
        match = re.search(pattern, combined)
        if match:
            topic = match.group(1).strip(" .,:;")
            break
    if not topic:
        topic = "Stickman Explainer"
    return {
        "topic": topic,
        "short_script": short_script,
        "long_script": long_script,
        "short_storyboard": "\n".join(short_scenes),
        "long_storyboard": "\n".join(long_anchors),
        "short_scene_count": len(short_scenes),
        "long_anchor_count": len(long_anchors)
    }

def _scene_action(visual, index):
    """Choose a readable, low-risk character performance from the scene beat."""
    v=(visual or "").lower()
    rules=[
      (("walk","walking","approaches","crossing","crosses","steps","moves across","travels","journey","arrives"),"walk"),
      (("writes","writing","records","recording","sketches","draws a plan","takes notes","signs the document"),"write"),
      (("carries","carrying","hauls","lifts a crate","holds a bundle","transports a case"),"carry"),
      (("celebrates","celebration","waves","signals overhead","raises both arms","cheers"),"raise"),
      (("points","pointing","indicates","marks","signals"),"point"),
      (("study","studies","examines","reads","inspects","decodes","calculates","compares"),"study"),
      (("turn","turns","looks back","faces away","discovers","realizes","reveals"),"turn"),
      (("gesture","gestures","addresses","raises a hand","debates","announces","speaks","explains"),"gesture"),
      (("present","presents","opens","places","holds up","unfolds","hands over"),"present"),
      (("watch","watches","observes","looks toward","looks down","stares","waits","listens"),"observe")
    ]
    for words,action in rules:
        if any(word in v for word in words): return action
    return ("observe","study","present","walk","turn","gesture")[index%6]


def _scene_expression(narration, visual, index=0):
    """Select a restrained facial expression from the spoken story beat."""
    text=(str(narration or "")+" "+str(visual or "")).lower()
    rules=[
      (("astonishing","astonished","shocked","surprised","unexpected","suddenly","could not believe","unbelievable"),"surprised"),
      (("danger","threat","risk","worried","fear","uncertain","anxious","missing","vanished","mystery","crisis","trouble"),"concerned"),
      (("exhausted","weary","years later","long wait","after months","after years","fatigue","tired"),"weary"),
      (("success","finally","triumph","resolved","determined","hope","rescue","recovered","rebuild","victory","decided"),"resolved")
    ]
    for terms,expression in rules:
        if any(term in text for term in terms):
            return expression
    return ("neutral","concerned","resolved","weary")[index%4]


def _scene_camera(visual, index):
    """Match framing to the story beat while retaining deliberate shot variety."""
    v=(visual or "").lower()
    rules=[
      (("map","atlas","route","chart","plan","blueprint","geography"),"overhead illustrated map composition with gentle pan"),
      (("letter","telegram","message","document","manuscript","book","ledger","key","coin","artifact","photograph","evidence","diary","compass","lantern","telescope","satchel","travel chest","journal","newspaper","timetable","gear","mechanism","balance scale"),"close-up of a story-specific object with slow push-in"),
      (("tower","palace","cathedral","monument","bridge","dam","lighthouse","skyscraper","architecture"),"low-angle architectural view with slow tilt upward"),
      (("room","office","council","meeting","court","laboratory","workshop","archive","library","interior"),"interior tableau with subtle camera drift"),
      (("walk","walking","journey","travel","crossing","crosses","escape","expedition","march","railway","train","ship","vessel","caravan"),"side-on tracking composition with figures crossing frame"),
      (("crowd","city","street","harbour","port","landscape","mountain","desert","ocean","sea","storm","flood","eruption","smog"),"wide establishing shot with slow push-in"),
      (("mystery","vanished","disappeared","unknown","aftermath","silhouette","empty"),"wide silhouette composition with slow pull-back")
    ]
    for terms,camera in rules:
        if any(term in v for term in terms):
            # A repeated shot is less useful than a fresh angle on consecutive beats.
            if index and index % 4 == 0 and camera.startswith("close-up"):
                return "medium character composition with gentle lateral pan"
            return camera
    return CAMERAS[index % len(CAMERAS)]

def _lead_for_topic(topic):
    t=(topic or "").lower()
    if any(k in t for k in ("ship","mary celeste","sea","captain")): return "Merchant"
    if any(k in t for k in ("mansa","musa","sahara","caravan","desert")): return "Traveler"
    if any(k in t for k in ("1914","christmas truce","soldier","war")): return "Witness"
    if any(k in t for k in ("alcatraz","prison","escape","cooper","hijack")): return "Official"
    if any(k in t for k in ("pompeii","rome","emperor","ancient")): return "Scholar"
    return "Narrator"

def _locked_character_block(role):
    costume=CHARACTERS.get(role,CHARACTERS["Narrator"])["costume"]
    return ("One recurring simple stick figure with a large perfectly round white head, small solid black oval eyes, thin curved eyebrow strokes, one simple curved mouth, no nose, and a few loose ink hair strokes; minimal softly rounded body, wearing exactly a "+costume+", with simple dark footwear and no changing accessories or proportions.")

def make_project(topic, duration_seconds, aspect_ratio="16:9", narration_script=None, storyboard=None):
    topic = re.sub(r"\s+", " ", (topic or "Untitled story")).strip()[:500]
    duration = int(duration_seconds)
    count = max(1, math.ceil(duration / 4))
    script = (narration_script or "").strip()
    anchors = [x.strip() for x in (storyboard or "").splitlines() if x.strip()]
    chunks = _chunk_script(script, count)
    lead = _lead_for_topic(topic)
    locked = _locked_character_block(lead)
    scenes = []
    for i in range(count):
        anchor = anchors[min(len(anchors)-1, int(i * len(anchors) / count))] if anchors else ""
        narration = chunks[i] if i < len(chunks) else ""
        if not narration:
            narration = f"[SCRIPT REQUIRED] Write researched narration for this moment in {topic}. This is not publish-ready."
        visual = re.sub(r"^Aspect ratio\s+\d+:\d+\.\s*", "", anchor)
        visual = re.sub(r"\s*Hand-inked 2D.*$", "", visual)
        if not visual:
            visual = f"Distinct story beat about {topic}; show a new action, location or meaningful object."
        camera = _scene_camera(visual, i)
        action = _scene_action(visual, i)
        expression = _scene_expression(narration, visual, i)
        title = re.sub(r"^.*?shot of ", "", visual, flags=re.I)[:52].strip(" .,:;") or f"Scene {i+1:03d}"
        visual_prompt = (
            f"This is a {min(4, duration-i*4)}-second hand-inked 2D animated clip in {aspect_ratio}. "
            f"{locked} Background and story action: {visual}. Shot composition: {camera}. "
            f"One clear action: {action}. {HOUSE_STYLE} "
            "Visual safety: use generic people and places only; no real named people, flags, insignia, logos, violence, injury, death, blood or weapons being fired; "
            "use restrained objects, empty spaces, distant silhouettes or aftermath. "
            "Audio is diegetic ambient sound only — no voice, no narration, no dialogue, no music. "
            "Only the sounds present in the scene such as wind, footsteps, distant rumble, rain, machinery or room tone. "
            "The camera stays locked or moves only in a very slow push; the character design, clothing and proportions never change; "
            "the texture overlay and vignette stay consistent; no glitching, no warping, no morphing, no flickering, no extra limbs, no duplicate characters, "
            "no unintended characters, no on-screen text, no subtitles and no watermark."
        )
        scenes.append({
            "scene_id": f"scene_{i+1:03d}", "title": title, "duration": min(4, duration-i*4),
            "narration": narration, "visual": visual, "visual_prompt": visual_prompt,
            "camera": camera, "characters": [lead], "action": action, "expression": expression, "shot_type": camera.split(" composition")[0].split(" view")[0].split(" tableau")[0]
        })
    final_duration = duration - 4*(count-1)
    character_sheet_prompt = (
        f"Create one character sheet in {aspect_ratio} on a plain flat neutral background, with no environments or scenery. "
        "Top row: the recurring character in front, three-quarter, side and back full-body views, evenly spaced. "
        "Middle row: five head-only expressions labelled NEUTRAL, CONCERNED, SURPRISED, WEARY and RESOLVED. "
        "Bottom row: five full-body poses labelled STANDING, WALKING, SITTING, LOOKING UP and TURNING AWAY. "
        f"Character design: {locked} {HOUSE_STYLE} "
        "Plain flat neutral background throughout, no scenery, no props beyond what the character wears or carries, no text beyond row and pose labels, no watermark, no logos, no additional characters."
    )
    topic_key = topic.lower()
    headline_rules = [
        (("mary celeste", "empty ship"), "THE EMPTY SHIP"),
        (("cooper", "parachute"), "THE SKY MYSTERY"),
        (("alcatraz", "prison escape"), "THE GREAT ESCAPE"),
        (("molasses",), "THE STICKY FLOOD"),
        (("pompeii",), "A CITY PRESERVED"),
        (("christmas truce",), "A MOMENT OF PEACE"),
        (("south pole", "antarctic"), "RACE TO THE POLE"),
        (("eiffel tower",), "THE IMPOSSIBLE SALE"),
        (("tunguska",), "THE SKY EXPLOSION"),
    ]
    thumbnail_headline = next((headline for keys,headline in headline_rules if any(k in topic_key for k in keys)), "THE UNTOLD STORY")
    thumbnail_prompt = (
        f"Create a 16:9 YouTube thumbnail for this real story. Use the short bold all-caps headline {thumbnail_headline!r}, no more than four words, expressing the story hook without naming a real person or specific atrocity location. Place the recurring character from this locked design on one side in an expressive pose: {locked} "
        "Fill the rest with one simple illustrated story object, scene or landscape described generically. "
        "Use a short bold all-caps headline of no more than four words, heavy condensed lettering, hard contrast and large simple shapes readable at 200 pixels wide. "
        f"{HOUSE_STYLE} No small details that disappear at thumbnail size, no watermark, no logos."
    )
    last_full_scene = count if final_duration == 4 else count - 1
    agent_instruction = (
        f"You are generating {count} animated clips for one continuous film in {aspect_ratio}. "
        "A character sheet is attached showing the recurring character in multiple views, expressions and poses; use it as the visual reference in every clip. "
        f"Scenes 1 through {last_full_scene} are exactly 4 seconds each. "
        f"If the final scene is shorter, generate Scene {count} at exactly {final_duration} seconds so the complete film reaches {duration} seconds. "
        "Generate all clips autonomously, in order, without stopping or asking for confirmation. "
        "The character, ink style, colour palette, texture overlay and vignette must stay identical across every clip."
    )
    return {
      "project_id": str(uuid.uuid4()), "title": topic[:90].title(), "topic": topic,
      "duration_seconds": duration, "aspect_ratio": aspect_ratio, "language": "English",
      "style": HOUSE_STYLE, "characters": CHARACTERS, "lead_character": lead,
      "locked_character_block": locked, "character_sheet_prompt": character_sheet_prompt,
      "animation_agent_instruction": agent_instruction, "thumbnail_prompt": thumbnail_prompt,
      "thumbnail_headline": thumbnail_headline,
      "scenes": scenes, "animation_prompts": [scene["visual_prompt"] for scene in scenes],
      "status": "queued", "scene_count": count, "thumbnail_path": None,
      "script_word_count": len(script.split()), "script_supplied": bool(script),
      "storyboard_anchor_count": len(anchors),
      "quality_notice": ("Production brief supplied." if script and len(anchors) >= count else
        "DRAFT ONLY: this output is not publish-ready until every scene has researched narration and its own visual prompt.")
    }
