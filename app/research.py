import html
import json
import math
import re
import urllib.parse
import urllib.request


CAMERA_SHOTS = [
    "wide establishing shot with slow push-in",
    "medium profile shot",
    "close-up of a story-specific object",
    "over-the-shoulder view",
    "high-angle environmental wide",
    "low-angle architectural view",
    "side-on tracking composition",
    "quiet interior tableau",
]


def _api(params):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "StickmanStudio/1.0 (open-source educational video maker)"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _sentences(text):
    text = re.sub(r"\[[0-9]+\]", "", html.unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 5]


def _generic_scene(sentence, index):
    value = sentence.lower()
    if any(k in value for k in ("ship", "vessel", "sail", "ocean", "sea", "captain")):
        setting = "a small merchant sailing vessel crossing a muted grey sea"
        object_name = "a folded nautical chart"
    elif any(k in value for k in ("prison", "cell", "escape", "jail", "guard")):
        setting = "a quiet stone corridor with a closed iron gate"
        object_name = "a small metal key"
    elif any(k in value for k in ("train", "railway", "station", "carriage")):
        setting = "an empty old railway platform at dusk"
        object_name = "a station clock"
    elif any(k in value for k in ("letter", "telegram", "message", "document", "paper")):
        setting = "a spare old office with a wooden writing desk"
        object_name = "a sealed paper letter"
    elif any(k in value for k in ("map", "route", "journey", "travel", "expedition")):
        setting = "a wide muted landscape with a winding distant road"
        object_name = "a hand-drawn map"
    elif any(k in value for k in ("court", "king", "queen", "emperor", "palace", "royal")):
        setting = "a quiet historic hall with simple geometric columns"
        object_name = "an empty ceremonial chair"
    elif any(k in value for k in ("market", "trade", "merchant", "coin", "money", "business")):
        setting = "a quiet old market street with simple stalls"
        object_name = "a small stack of old coins"
    elif any(k in value for k in ("storm", "rain", "flood", "water", "river")):
        setting = "a restrained old city street beside a broad river"
        object_name = "a floating wooden crate"
    elif any(k in value for k in ("machine", "engine", "factory", "invention", "clock")):
        setting = "a quiet workshop with a large hand-built mechanism"
        object_name = "a slowly turning gear"
    elif any(k in value for k in ("mountain", "snow", "ice", "antarctic", "desert", "sahara")):
        setting = "a vast empty landscape beneath a pale overcast sky"
        object_name = "a weathered travel satchel"
    elif any(k in value for k in ("city", "street", "town", "building", "house")):
        setting = "a muted historic city street with geometric buildings"
        object_name = "a closed wooden doorway"
    else:
        settings = [
            ("a quiet archive with shelves of old books", "an open ledger"),
            ("a sparse room with a wooden table and one window", "a pocket watch"),
            ("a muted town square at early morning", "a folded newspaper"),
            ("a wide landscape with distant low hills", "a weathered travel bag"),
            ("a simple office with a tall window", "a sealed envelope"),
        ]
        setting, object_name = settings[index % len(settings)]
    action = "the figure slowly turns toward the object"
    if any(k in value for k in ("walk", "travel", "cross", "arrive", "journey")):
        action = "the figure takes a few slow steps across the frame"
    elif any(k in value for k in ("open", "opened", "door", "enter")):
        action = "the figure slowly opens the closed door"
    elif any(k in value for k in ("look", "watch", "see", "discover", "find")):
        action = "the figure looks down at the object"
    elif any(k in value for k in ("build", "built", "create", "invent", "construct")):
        action = "the figure carefully places the object on the table"
    return (
        f"{setting}, early morning muted light, two or three simple inked details, "
        f"{object_name} clearly visible, one generic stick figure in period-appropriate "
        f"muted clothing; {action}. No named people or specific real locations."
    )


def research_topic(topic, duration_seconds):
    topic = re.sub(r"\s+", " ", (topic or "")).strip()
    if len(topic) < 3:
        raise ValueError("Enter a story topic with at least three characters.")
    count = max(1, math.ceil(int(duration_seconds) / 4))
    last = int(duration_seconds) - 4 * (count - 1)
    target_words = 9 * (count - 1) + max(1, round(9 * last / 4))
    data = _api({
        "action": "query",
        "generator": "search",
        "gsrsearch": topic,
        "gsrnamespace": 0,
        "gsrlimit": 10,
        "prop": "extracts|info",
        "explaintext": 1,
        "exsectionformat": "plain",
        "exchars": 45000,
        "inprop": "url",
        "format": "json",
        "formatversion": 2,
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise ValueError("No suitable Wikipedia research page was found. Try a more specific topic.")
    primary = pages[0]
    title = primary.get("title", topic)
    primary_text = primary.get("extract", "")
    sources = []
    combined = primary_text
    for page in pages:
        if page.get("title") and page.get("fullurl"):
            sources.append({"title": page["title"], "url": page["fullurl"]})
    sentences = _sentences(primary_text)
    if len(" ".join(sentences).split()) < target_words * 0.82:
        for page in pages[1:]:
            sentences.extend(_sentences(page.get("extract", "")))
            if len(" ".join(sentences).split()) >= target_words:
                break
    words = " ".join(sentences).split()
    if len(words) < target_words:
        raise ValueError(
            f"The free research sources provide only {len(words)} usable words, but a complete {duration_seconds}-second narration needs {target_words}. "
            "Choose a shorter duration or a topic with more documented material. The engine will not invent missing facts."
        )
    selected = words[:target_words]
    script = " ".join(selected)
    if script and script[-1] not in ".!?":
        script = script.rstrip(" ,;:") + "."
    # Re-segment the researched narration into one beat per animation scene.
    script_words = script.split()
    beats = []
    cursor = 0
    for index in range(count):
        beat_words = 9 if index < count - 1 else max(1, round(9 * last / 4))
        beat = script_words[cursor:cursor + beat_words]
        cursor += len(beat)
        if beat:
            beats.append(" ".join(beat).rstrip(" ,;:") + ("" if beat[-1][-1:] in ".!?" else "."))
    # Keep the beat array authoritative; the continuous script is its joined text.
    script = " ".join(beats)
    anchors = [_generic_scene(" ".join(beats[i].split()), i) for i in range(count)]
    return {
        "topic": title,
        "duration_seconds": int(duration_seconds),
        "scene_count": count,
        "target_word_count": target_words,
        "script_word_count": len(script.split()),
        "narration_script": script,
        "narration_beats": beats,
        "storyboard": "\n".join(anchors),
        "sources": sources,
        "research_note": "Narration is assembled from the retrieved encyclopedia source text. Review the citations and wording before publication.",
        "source_license": "Wikipedia text is available under CC BY-SA; attribute the linked sources when publishing adapted text."
    }
