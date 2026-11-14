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
 ("The Race to Reach the South Pole","Two expeditions crossed Antarctica in a dramatic race against time.")
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
    v=(visual or "").lower()
    rules=[
      (("walk","walking","approaches"),"walk"),
      (("point","points","signals"),"point"),
      (("study","studies","examines","reads","inspects"),"study"),
      (("turn","turns","looks back","faces away"),"turn"),
      (("gesture","gestures","addresses","raises a hand"),"gesture"),
      (("present","presents","opens","places","holds up"),"present"),
      (("watch","watches","observes","looks toward","stares"),"observe")
    ]
    for words,action in rules:
        if any(word in v for word in words): return action
    return ("observe","walk","study","turn","gesture","point")[index%6]

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
        camera = CAMERAS[i % len(CAMERAS)]
        action = _scene_action(visual, i)
        title = re.sub(r"^.*?shot of ", "", visual, flags=re.I)[:52].strip(" .,:;") or f"Scene {i+1:03d}"
        visual_prompt = (
            f"This is a {min(4, duration-i*4)}-second hand-inked 2D animated clip in {aspect_ratio}. "
            f"{locked} Background and story action: {visual}. Shot composition: {camera}. "
            f"One clear action: {action}. {HOUSE_STYLE} "
            "Audio is diegetic ambient sound only — no voice, no narration, no dialogue, no music. "
            "Only sounds present in the scene such as wind, footsteps, distant rumble, rain, machinery or room tone. "
            "Keep the camera locked or moving only in a very slow push; character design, clothing and proportions never change; "
            "texture overlay and vignette stay consistent; no glitching, warping, morphing, flickering, extra limbs, duplicate or unintended characters, "
            "on-screen text, subtitles or watermark. Visual safety: use generic people and places only; no real named people, flags, insignia, logos, "
            "violence, injury, death, blood or weapons being fired; use restrained objects, empty spaces, distant silhouettes or aftermath."
        )
        scenes.append({
            "scene_id": f"scene_{i+1:03d}", "title": title, "duration": min(4, duration-i*4),
            "narration": narration, "visual": visual, "visual_prompt": visual_prompt,
            "camera": camera, "characters": [lead], "action": action
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
    thumbnail_prompt = (
        f"Create a 16:9 YouTube thumbnail for {topic}. Place the recurring character from this locked design on one side in an expressive pose: {locked} "
        "Fill the rest with one simple illustrated story object, scene or landscape described generically. "
        "Use a short bold all-caps headline of no more than four words, heavy condensed lettering, hard contrast and large simple shapes readable at 200 pixels wide. "
        f"{HOUSE_STYLE} No small details that disappear at thumbnail size, no watermark, no logos."
    )
    agent_instruction = (
        f"Generate {count} clips for one continuous film in {aspect_ratio}. Use the same character design, ink style, muted palette, texture and vignette in every clip. "
        f"Scenes 1 through {count-1} are exactly 4 seconds each; the final scene is exactly {final_duration} seconds so the film totals {duration} seconds. "
        "Generate every scene in order without pausing for confirmation. Keep each clip's audio to diegetic ambient sound only; narration is a separate aligned voiceover track."
    )
    return {
      "project_id": str(uuid.uuid4()), "title": topic[:90].title(), "topic": topic,
      "duration_seconds": duration, "aspect_ratio": aspect_ratio, "language": "English",
      "style": HOUSE_STYLE, "characters": CHARACTERS, "lead_character": lead,
      "locked_character_block": locked, "character_sheet_prompt": character_sheet_prompt,
      "animation_agent_instruction": agent_instruction, "thumbnail_prompt": thumbnail_prompt,
      "scenes": scenes, "animation_prompts": [scene["visual_prompt"] for scene in scenes],
      "status": "queued", "scene_count": count, "thumbnail_path": None,
      "script_word_count": len(script.split()), "script_supplied": bool(script),
      "storyboard_anchor_count": len(anchors),
      "quality_notice": ("Production brief supplied." if script and len(anchors) >= count else
        "DRAFT ONLY: this output is not publish-ready until every scene has researched narration and its own visual prompt.")
    }
