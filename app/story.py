import math, re, uuid

HOUSE_STYLE = ("Hand-inked 2D illustrated animation with thick slightly rough black ink outlines "
"of varying weight. Characters are simple stick figures with large perfectly round white heads, "
"small solid black oval eyes, thin curved eyebrow strokes, a single simple curved line for the mouth, "
"no nose, and a few loose ink strokes suggesting hair across the top of the head. Bodies are minimal "
"with softly rounded shoulders and flat muted clothing in desaturated navy blue, brick red and olive. "
"Backgrounds are flat hand-drawn illustrated environments in muted tan, sage, dusty grey and cream, "
"outlined in the same black ink, with geometric architecture and sparse purposeful detail. Fine "
"horizontal scanline and paper-grain texture, soft dark vignette, cinematic desaturated colour grade. "
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
 "Historian":{"costume":"muted olive jacket","color":"#737653"},
 "Witness":{"costume":"brick-red scarf","color":"#9a5144"},
 "Official":{"costume":"charcoal coat","color":"#55565a"},
 "Merchant":{"costume":"dusty brown robe","color":"#89745b"},
 "Scholar":{"costume":"muted sage robe","color":"#737d68"}
}

CAMERAS = [
 "wide establishing shot, slow push-in",
 "medium two-character composition, subtle lateral track",
 "close-up of a meaningful object, slow push-in",
 "overhead illustrated map composition, gentle pan",
 "low-angle architectural view, slow tilt upward",
 "side-on tracking composition, characters crossing frame",
 "wide silhouette composition, slow pull-back",
 "interior tableau, gentle camera drift"
]

def _sentences(text):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]

def _chunk_script(script, count):
    words = re.findall(r"\\S+", script or "")
    if not words:
        return []
    # Keep sentence boundaries where possible, then balance chunks to the target count.
    sentences = _sentences(script)
    chunks, current = [], []
    target = max(1, math.ceil(len(words) / count))
    for sentence in sentences:
        sw = sentence.split()
        if current and len(current) + len(sw) > target * 1.35 and len(chunks) < count - 1:
            chunks.append(" ".join(current)); current = []
        current.extend(sw)
    if current:
        chunks.append(" ".join(current))
    # Merge excess chunks and split oversized chunks without dropping any words.
    while len(chunks) > count:
        idx = min(range(len(chunks)-1), key=lambda i: len(chunks[i].split()) + len(chunks[i+1].split()))
        chunks[idx:idx+2] = [chunks[idx] + " " + chunks[idx+1]]
    while len(chunks) < count:
        idx = max(range(len(chunks)), key=lambda i: len(chunks[i].split()))
        ws = chunks[idx].split()
        if len(ws) < 2: break
        mid = len(ws)//2
        chunks[idx:idx+1] = [" ".join(ws[:mid]), " ".join(ws[mid:])]
    return chunks

def make_project(topic, duration_seconds, aspect_ratio="16:9", narration_script=None, storyboard=None):
    topic = re.sub(r"\\s+", " ", topic).strip()[:500]
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
            narration = (f"[SCRIPT REQUIRED] Add researched narration for this moment in {topic}. "
                         "This placeholder is not publish-ready.")
        camera = CAMERAS[i % len(CAMERAS)]
        visual = anchor or f"Create a distinct visual beat about: {topic}. Avoid repeating previous compositions."
        title = (anchor[:68] if anchor else f"Scene {i+1:03d}")
        scenes.append({
            "scene_id": f"scene_{i+1:03d}",
            "title": title,
            "duration": min(4, duration-i*4),
            "narration": narration,
            "visual": visual,
            "visual_prompt": f"{HOUSE_STYLE}\\nStory context: {topic}.\\nShot: {visual}.\\nCamera: {camera}. "
              "Maintain character design, muted palette and hand-inked 2D style. Use a distinct composition "
              "and purposeful action. Do not invent readable text in the image.",
            "camera": camera,
            "characters": ["Narrator"] if i % 3 else ["Narrator", "Witness"],
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
        "DRAFT ONLY: add a researched full narration script and one storyboard anchor per key scene before publishing.")
    }
