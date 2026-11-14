import math, re, uuid

HOUSE_STYLE = ("Hand-inked 2D illustrated animation with thick slightly rough black ink outlines of varying weight. "
"Characters are simple stick figures with large perfectly round white heads, small solid black oval eyes, thin curved eyebrow strokes, "
"a single simple curved line for the mouth, no nose, and a few loose ink strokes suggesting hair. Bodies are minimal with softly rounded "
"shoulders and flat muted clothing in desaturated navy blue, brick red and olive. Backgrounds are flat hand-drawn illustrated environments "
"in muted tan, sage, dusty grey and cream, outlined in the same black ink, with geometric architecture and sparse purposeful detail. "
"Fine horizontal scanline and paper-grain texture, soft dark vignette, cinematic desaturated colour grade. "
"No bright saturated colours, gradients, photorealism, 3D, anime or glossy digital finish.")

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

def make_project(topic, duration_seconds, aspect_ratio="16:9", narration_script=None, storyboard=None):
    topic = re.sub(r"\s+", " ", (topic or "Untitled story")).strip()[:500]
    duration = int(duration_seconds)
    count = max(1, math.ceil(duration / 4))
    script = (narration_script or "").strip()
    anchors = [x.strip() for x in (storyboard or "").splitlines() if x.strip()]
    chunks = _chunk_script(script, count)
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
        title = re.sub(r"^.*?shot of ", "", visual, flags=re.I)[:52].strip(" .,:;") or f"Scene {i+1:03d}"
        characters = ["Emperor", "Herald", "Merchant", "Architect", "Scholar", "Traveler"] if "mansa" in topic.lower() or "musa" in topic.lower() else ["Narrator", "Witness", "Merchant"]
        scenes.append({
            "scene_id": f"scene_{i+1:03d}", "title": title, "duration": min(4, duration-i*4),
            "narration": narration, "visual": visual,
            "visual_prompt": f"{HOUSE_STYLE}\nStory context: {topic}.\nShot: {visual}.\nCamera: {camera}. Keep every frame readable and story-specific.",
            "camera": camera, "characters": [characters[i % len(characters)]],
            "action": ["walk","look","study","turn","point","gesture","observe","present"][i % 8]
        })
    return {
      "project_id": str(uuid.uuid4()), "title": topic[:90].title(), "topic": topic,
      "duration_seconds": duration, "aspect_ratio": aspect_ratio, "language": "English",
      "style": HOUSE_STYLE, "characters": CHARACTERS, "scenes": scenes,
      "status": "queued", "scene_count": count, "thumbnail_path": None,
      "script_word_count": len(script.split()), "script_supplied": bool(script),
      "storyboard_anchor_count": len(anchors),
      "quality_notice": ("Production brief supplied." if script and anchors else
        "DRAFT ONLY: add a researched full narration script and storyboard before publishing.")
    }
