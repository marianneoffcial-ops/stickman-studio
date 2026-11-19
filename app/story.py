import math, re, uuid

HOUSE_STYLE = ("Hand-inked 2D illustrated animation with thick slightly rough black ink outlines of varying weight. "
"Characters are simple stick figures with a large perfectly round white head, small solid black oval eyes, thin curved eyebrow strokes, a single simple curved line for the mouth, no nose, and a few loose ink strokes suggesting hair across the top of the head. "
"Bodies are true stick-figure anatomy: one thin black torso line and thin articulated line limbs, with no filled torso, no jacket silhouette and no bulky clothing. Wardrobe is limited to one small flat muted neck scarf and a narrow matching diagonal sash, unchanged in every shot. "
"Backgrounds are painterly ink-wash storybook environments in a muted earthy palette of tan, sage, dusty grey and cream, with watercolor and gouache washes, visible brush texture, rough black ink contours and layered foreground, middle distance and atmosphere. Architecture and details must be historically appropriate and story-specific, not floating decorative shapes. "
"Keep the recurring character large and immediately readable; use clean negative space and only story-relevant environmental details. No decorative floating circles, icons, symbols, random dots or generic cloud marks. A fine horizontal scanline and paper-grain texture overlays the entire frame, with a soft dark vignette at the edges. "
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
 "Narrator":{"costume":"small desaturated navy neck scarf and matching narrow sash","color":"#34465a"},
 "Emperor":{"costume":"small muted olive neck scarf and matching narrow sash","color":"#737653"},
 "Herald":{"costume":"small brick-red neck scarf and matching narrow sash","color":"#9a5144"},
 "Merchant":{"costume":"small dusty navy neck scarf and matching narrow sash","color":"#536276"},
 "Architect":{"costume":"small muted sage neck scarf and matching narrow sash","color":"#737d68"},
 "Scholar":{"costume":"small muted sage neck scarf and matching narrow sash","color":"#737d68"},
 "Traveler":{"costume":"small deep navy neck scarf and matching narrow sash","color":"#34465a"},
 "Witness":{"costume":"small brick-red neck scarf and matching narrow sash","color":"#9a5144"},
 "Official":{"costume":"small charcoal neck scarf and matching narrow sash","color":"#55565a"}
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
      (("astonishing","astonished","surprised","unexpected discovery","discovers","discovered","reveals","revealed","unveils"),"reveal"),
      (("considers","considered","thinks","thinking","ponders","pondered","plans","planning","reflects","reflecting","weighs the options"),"ponder"),
      (("point","points","signals","indicates","marks"),"point"),
      (("study","studies","examines","reads","inspects","decodes","calculates","compares"),"study"),
      (("turn","turns","looks back","faces away","discovers","realizes","reveals"),"turn"),
      (("gesture","gestures","addresses","raises a hand","debates","announces","speaks"),"gesture"),
      (("present","presents","opens","places","holds up","unfolds","hands over"),"present"),
      (("watch","watches","observes","looks toward","looks down","stares","waits","listens"),"observe")
    ]
    for words,action in rules:
        if any(word in v for word in words): return action
    # Keep neutral narration visually calm; semantic cues above select active gestures.
    return "observe"


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
    # Do not invent an emotion when the narration and visual beat are neutral.
    # Semantic matches above remain responsible for expressive faces.
    return "neutral"


def _scene_camera(visual, index):
    """Match framing to the story beat while retaining deliberate shot variety."""
    v=(visual or "").lower()
    rules=[
      (("map","atlas","route","chart","plan","blueprint","geography"),"overhead illustrated map composition with gentle pan"),
      (("letter","telegram","message","document","manuscript","book","ledger","key","coin","artifact","photograph","evidence","diary","compass","lantern","telescope","satchel","travel chest","journal","newspaper","timetable","gear","mechanism","balance scale"),"close-up of a story-specific object with slow push-in"),
      (("tower","palace","cathedral","monument","bridge","dam","lighthouse","skyscraper","architecture"),"low-angle architectural view with slow tilt upward"),
      (("room","office","council","meeting","court","laboratory","workshop","archive","library","interior"),"interior tableau with subtle camera drift"),
      (("walk","walking","journey","travel","crossing","crosses","escape","expedition","march","railway","train","ship","vessel","caravan"),"side-on tracking composition with figures crossing frame"),
      (("crowd","city","street","river","thames","boat","harbour","port","landscape","mountain","desert","ocean","sea","storm","flood","eruption","smog"),"wide establishing shot with slow push-in"),
      (("mystery","vanished","disappeared","unknown","aftermath","silhouette","empty"),"wide silhouette composition with slow pull-back")
    ]
    for terms,camera in rules:
        if any(term in v for term in terms):
            # Rotate through a small, motivated framing pattern when several adjacent
            # narration beats share one location or prop. Preserve strong semantic matches
            # for maps, object close-ups, architecture and travel in their natural slots.
            slot = index % 4
            if slot == 0:
                return camera
            if slot == 1:
                if camera.startswith("close-up"):
                    return camera
                return "medium character composition with gentle lateral pan"
            if slot == 2:
                if camera.startswith("low-angle"):
                    return camera
                return "high-angle environmental wide with a slow descending drift"
            if camera.startswith("side-on tracking"):
                return camera
            return "wide silhouette composition with slow pull-back"
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
    return ("One recurring simple stick figure with a large perfectly round white head, small solid black oval eyes, thin curved eyebrow strokes, one simple curved mouth, no nose, and a few loose ink hair strokes. The torso is one visible black ink line; arms and legs are thin articulated black lines with clear elbows and knees. Absolutely no filled body, no solid jacket, no coat silhouette and no bulky clothing. Wardrobe is exactly one small flat muted neck scarf and a narrow matching diagonal sash ("+costume+"), with simple dark shoes. Keep head size, body proportions, scarf, sash and line weight identical in every shot.")

def _story_phase(index, count):
    """Assign each shot a narrative job so the film progresses instead of repeating poses."""
    if count <= 1:
        return "payoff"
    position = index / max(1, count - 1)
    if position < 0.16:
        return "hook"
    if position < 0.36:
        return "setup"
    if position < 0.70:
        return "escalation"
    if position < 0.88:
        return "turning_point"
    return "payoff"


def _scene_sound(visual):
    """Describe a restrained diegetic bed from visible scene content."""
    v = (visual or "").lower()
    rules = [
        (("sea", "ship", "boat", "harbour", "port"), "soft wind, water movement and distant harbour room tone"),
        (("train", "railway", "locomotive"), "rail rhythm, low mechanical rumble and distant station ambience"),
        (("rain", "storm", "flood"), "steady rain or weather ambience with occasional distant rumble"),
        (("archive", "library", "letter", "document", "office", "room"), "quiet indoor room tone, paper handling and subtle movement"),
        (("street", "city", "market", "crowd"), "distant city room tone, soft footsteps and restrained crowd murmur"),
        (("desert", "sahara", "mountain", "snow", "ice"), "open-air wind and sparse environmental room tone"),
    ]
    return next((sound for terms, sound in rules if any(term in v for term in terms)),
                "soft location-appropriate wind or room tone and subtle object handling")


def _continuity_state(visual, index):
    """Record the persistent visual facts that the next beat should inherit."""
    v = (visual or "").strip().rstrip(".")
    return ("Continue from the previous shot's established location, screen direction, "
            "character wardrobe and prop state. " + (f"Keep this beat's key visual fact visible: {v}." if v else
            "Do not introduce a new location or prop without a visible story transition."))


def make_project(topic, duration_seconds, aspect_ratio="16:9", narration_script=None, storyboard=None, narration_beats=None):
    topic = re.sub(r"\s+", " ", (topic or "Untitled story")).strip()[:500]
    duration = int(duration_seconds)
    count = max(1, math.ceil(duration / 4))
    script = (narration_script or "").strip()
    anchors = [x.strip() for x in (storyboard or "").splitlines() if x.strip()]
    provided_beats = [re.sub(r"\s+", " ", str(beat)).strip() for beat in (narration_beats or []) if str(beat).strip()]
    chunks = provided_beats if len(provided_beats) == count and " ".join(provided_beats).split() == script.split() else _chunk_script(script, count)
    lead = _lead_for_topic(topic)
    locked = _locked_character_block(lead)
    scenes = []
    for i in range(count):
        # Cycle through researched visual anchors so a short source storyboard is
        # distributed across the whole film instead of being held for several shots.
        anchor = anchors[i % len(anchors)] if anchors else ""
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
        phase = _story_phase(i, count)
        sound = _scene_sound(visual)
        continuity = _continuity_state(visual, i)
        title = re.sub(r"^.*?shot of ", "", visual, flags=re.I)[:52].strip(" .,:;") or f"Scene {i+1:03d}"
        duration_this = min(4, duration-i*4)
        visual_prompt = (
            f"This is a {duration_this}-second hand-inked 2D animated clip in {aspect_ratio}. "
            f"Scene-specific beat {i+1} of {count}; narration context only, never render words: {narration}. "
            f"Narrative job: {phase}. {locked} Background and story action: {visual}. "
            f"Shot composition and motivated camera movement: {camera}. "
            f"One readable character action: {action}; facial expression: {expression}. "
            f"Continuity from the prior beat: {continuity} "
            "Show a visible consequence of the action and leave the character and important props in a state the next shot can inherit. "
            f"Diegetic sound only: {sound}; no voice, narration, dialogue or music. " + "Audio is diegetic ambient sound only — no voice, no narration, no dialogue, no music. Only the sounds present in the scene. " + f"{HOUSE_STYLE} "
            "Visual safety: use generic people and places only; no real named people, flags, insignia, logos, violence, injury, death, blood or weapons being fired; "
            "use restrained objects, empty spaces, distant silhouettes or aftermath. "
            "Keep the chosen camera movement consistent with this shot; do not combine a continuous take with instant angle changes. "
            "Character identity, clothing, proportions, palette, lighting and texture remain consistent; no glitching, warping, morphing, flickering, extra limbs, duplicate characters, "
            "unintended characters, on-screen text, subtitles or watermark. "
            "no unintended characters, no on-screen text, no subtitles and no watermark."
        )
        scenes.append({
            "scene_id": f"scene_{i+1:03d}", "title": title, "duration": duration_this,
            "narration": narration, "visual": visual, "visual_prompt": visual_prompt,
            "camera": camera, "characters": [lead], "action": action, "expression": expression,
            "story_phase": phase, "continuity": continuity, "sound_design": sound,
            "shot_type": camera.split(" composition")[0].split(" view")[0].split(" tableau")[0]
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
        (("great fire of london",), "THE GREAT FIRE"),
        (("great stink",), "THE GREAT STINK"),
        (("transatlantic", "telegraph cable"), "ACROSS THE OCEAN"),
        (("panama canal",), "CONNECTING TWO OCEANS"),
        (("great emu war",), "THE EMU CAMPAIGN"),
        (("franklin expedition",), "LOST IN THE ARCTIC"),
        (("apollo 13",), "THE IMPOSSIBLE RESCUE"),
        (("olympic marathon",), "THE STRANGEST RACE"),
        (("great train robbery",), "THE TRAIN HEIST"),
        (("gardner museum",), "THE MISSING ART"),
        (("operation mincemeat",), "THE DECEPTION PLAN"),
        (("great smog",), "THE DEADLY FOG"),
        (("chilean miners",), "THE DEEP RESCUE"),
        (("moon landing",), "FIRST STEPS ON THE MOON"),
        (("maple syrup",), "THE SYRUP HEIST"),
        (("han van meegeren",), "THE MASTER FORGER"),
        (("great library of alexandria",), "LOST KNOWLEDGE"),
        (("san francisco earthquake",), "THE CITY SHOOK"),
        (("andes flight",), "THE ANDES SURVIVORS"),
        (("rosetta stone",), "DECODING ANCIENT EGYPT"),
        (("cuban missile crisis",), "ONE CRITICAL DECISION"),
        (("transatlantic",), "ACROSS THE OCEAN"),
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
        f"Create one coherent {duration}-second film in {aspect_ratio}, made from {count} ordered shots. "
        f"Each standard shot is exactly 4 seconds; the final shot is exactly {final_duration} seconds. "
        "Use the same recurring character identity, wardrobe, body proportions, palette and world design in every shot. The hero must remain clearly visible and occupy roughly 45–60% of frame height in normal shots; never shrink it into a tiny background extra. In close-up object shots, keep the full stickman visible beside the focal object. The body must remain unfilled line-art, with only the small muted scarf and sash as clothing accents. "
        "Build a cause-and-effect story: hook, establish the goal and obstacle, escalate through visible consequences, turn the situation, then resolve the objective. "
        "Each shot must inherit the previous shot's location, screen direction and important prop state unless a motivated transition is shown. "
        "Use motivated cuts and vary framing only when it improves story clarity; never use random montage or contradictory camera instructions. "
        "The character sheet is an identity reference, not an opening composition. Preserve the supplied visual style instead of restyling it. "
        "Generate all shots in order and do not silently omit beats. "
        "The final image must resolve the story and hold a clean readable silhouette."
    )
    return {
      "project_id": str(uuid.uuid4()), "title": topic[:90].title(), "topic": topic,
      "duration_seconds": duration, "aspect_ratio": aspect_ratio, "language": "English",
      "style": HOUSE_STYLE, "characters": CHARACTERS, "lead_character": lead,
      "locked_character_block": locked, "character_sheet_prompt": character_sheet_prompt,
      "animation_agent_instruction": agent_instruction, "thumbnail_prompt": thumbnail_prompt,
      "thumbnail_headline": thumbnail_headline,
      "scenes": scenes, "animation_prompts": [scene["visual_prompt"] for scene in scenes], "narration_beats": chunks,
      "status": "queued", "scene_count": count, "thumbnail_path": None,
      "script_word_count": len(script.split()), "script_supplied": bool(script),
      "storyboard_anchor_count": len(anchors),
      "story_arc": {
        "goal": f"Explain the central event: {topic}",
        "sequence": ["hook", "setup", "escalation", "turning_point", "payoff"],
        "continuity_rule": "Carry character identity, location, screen direction and key prop state across adjacent shots; show a transition when any changes.",
        "shot_count": count
      },
      "reference_manifest": [
        {"role": "character_identity", "asset": "character_sheet_prompt", "reuse": "same recurring character across every scene"},
        {"role": "environment", "asset": "scene-specific environment plates", "reuse": "keep one coherent time, palette and geography until a story transition"},
        {"role": "story_props", "asset": "scene-specific key objects", "reuse": "preserve object count, attachment, hand and state"}
      ],
      "quality_checks": [
        "scene count and total duration match the requested runtime",
        "each scene has narration, one readable action, a camera choice and diegetic sound",
        "character identity and wardrobe remain fixed",
        "adjacent scenes preserve location, direction and important prop state or explain a transition",
        "the final scene resolves the stated story objective",
        "the recurring stickman remains large, fully visible and visually identical across shots",
        "the torso and limbs remain open black ink lines with only small muted wardrobe accents",
        "backgrounds contain only story-relevant painted scenery, never decorative floating symbols or duplicate prop overlays",
        "thumbnail remains 16:9 with a headline of no more than four words"
      ],
      "quality_notice": ("Production brief supplied." if script and len(anchors) >= count else
        "DRAFT ONLY: this output is not publish-ready until every scene has researched narration and its own visual prompt.")
    }
