import html
from html.parser import HTMLParser
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
    """Turn each researched narration beat into a distinct, safe visual setup."""
    value = (sentence or "").lower()
    stages = [
        ("context", "establish the setting and the ordinary world before events changed"),
        ("preparation", "show careful preparation around a table of simple tools and papers"),
        ("journey", "show a measured journey through the environment with a clear sense of distance"),
        ("discovery", "show a quiet discovery focused on one important object"),
        ("decision", "show a small group considering a map or document around a table"),
        ("turning point", "show the key object or place that changed the course of events"),
        ("aftermath", "show the changed environment in a restrained, reflective composition"),
        ("legacy", "show a preserved record or landmark that carries the story forward"),
    ]
    stage, stage_action = stages[index % len(stages)]
    if any(k in value for k in ("discover", "found", "missing", "vanished", "empty", "mystery")):
        stage, stage_action = "discovery", "show a quiet discovery focused on one important object"
    elif any(k in value for k in ("decid", "plan", "agreement", "meeting", "official", "order")):
        stage, stage_action = "decision", "show a small group considering a map or document around a table"
    elif any(k in value for k in ("rescue", "return", "recover", "surviv", "rebuild", "aftermath")):
        stage, stage_action = "aftermath", "show the changed environment in a restrained, reflective composition"
    elif any(k in value for k in ("travel", "cross", "journey", "arriv", "expedition", "voyage")):
        stage, stage_action = "journey", "show a measured journey through the environment with a clear sense of distance"

    # Several visual locations and props per subject prevent a long film from
    # repeating the same generic backdrop for every four-second beat.
    domains = [
        (("ship", "vessel", "sail", "ocean", "sea", "captain", "boat"),
         [("a quiet harbour before departure", "a folded nautical chart"),
          ("the open deck of a small merchant vessel", "a brass compass"),
          ("a spare navigation cabin with a porthole", "a ship's logbook"),
          ("a distant coastline beneath a pale sky", "a small signal lantern"),
          ("an empty cabin with neatly arranged belongings", "a closed travel chest"),
          ("a muted grey sea with a low horizon", "a weathered telescope")]),
        (("prison", "cell", "escape", "jail", "guard", "alcatraz"),
         [("a long stone corridor with repeating doorways", "a ring of old keys"),
          ("a quiet cell with a narrow window", "a folded paper note"),
          ("a plain workshop table under a high window", "a small hand tool"),
          ("an empty exercise yard surrounded by distant walls", "a simple wall clock"),
          ("a silent shoreline seen from far away", "a small wooden boat"),
          ("an archive desk holding case records", "a thick evidence ledger")]),
        (("train", "railway", "station", "carriage", "locomotive"),
         [("an old railway platform before sunrise", "a station timetable"),
          ("a quiet signal box overlooking the tracks", "a brass signal lever"),
          ("the inside of an empty passenger carriage", "a pocket watch"),
          ("a long railway line disappearing into mist", "a small route map"),
          ("a station office with a wooden desk", "a bound railway ledger"),
          ("a distant platform after the crowds have gone", "a folded newspaper")]),
        (("letter", "telegram", "message", "document", "paper", "diary", "manuscript"),
         [("a quiet office with a writing desk", "a sealed paper letter"),
          ("an archive shelf filled with plain folders", "a bound record book"),
          ("a close view of a desk beside a window", "a fountain pen and ink bottle"),
          ("a small telegraph room with simple equipment", "a message slip"),
          ("a reading table beneath a shaded lamp", "an open manuscript"),
          ("a quiet records room with labelled drawers", "a closed document case")]),
        (("map", "route", "journey", "travel", "expedition", "atlas"),
         [("a wide muted landscape with a winding road", "a hand-drawn route map"),
          ("a small planning room with a broad table", "a brass compass"),
          ("a distant mountain pass beneath cloud", "a weathered travel satchel"),
          ("a quiet campsite on an open plain", "a folded field map"),
          ("a high viewpoint overlooking a long route", "a simple telescope"),
          ("a records table with expedition notes", "a leather-bound journal")]),
        (("court", "king", "queen", "emperor", "palace", "royal", "throne"),
         [("a quiet historic hall with geometric columns", "an empty ceremonial chair"),
          ("a private study with a large wooden desk", "a folded decree"),
          ("a formal courtyard in muted morning light", "a simple heraldic-free seal"),
          ("a treasury room with plain storage chests", "a small stack of old coins"),
          ("a long audience chamber seen from the doorway", "a ceremonial staff"),
          ("a quiet archive of historic records", "a bound royal ledger")]),
        (("market", "trade", "merchant", "coin", "money", "business", "gold"),
         [("a quiet old market street with simple stalls", "a small stack of old coins"),
          ("a merchant's counting room", "a balance scale"),
          ("a covered market at the start of the day", "a folded account ledger"),
          ("a broad trade route through a muted landscape", "a loaded travel chest"),
          ("a simple warehouse with timber shelves", "a sealed cargo crate"),
          ("an archive desk with trade records", "a brass weight")]),
        (("storm", "rain", "flood", "water", "river", "molasses"),
         [("a quiet old city street beside a broad river", "a floating wooden crate"),
          ("a riverside storehouse beneath heavy clouds", "a hanging lantern"),
          ("a stone bridge above slow-moving water", "a folded town map"),
          ("a muted street after the water has receded", "a water-marked ledger"),
          ("a small office overlooking the river", "a simple measuring gauge"),
          ("a wide river bend beneath a pale sky", "a moored wooden boat")]),
        (("machine", "engine", "factory", "invention", "clock", "cable", "telegraph"),
         [("a quiet workshop with a hand-built mechanism", "a large turning gear"),
          ("a small control room with simple instruments", "a brass dial"),
          ("a factory floor with distant machinery", "a set of mechanical plans"),
          ("a workbench beneath a high window", "a metal measuring tool"),
          ("a long cable route across an open landscape", "a simple signal insulator"),
          ("an archive shelf holding technical drawings", "a rolled blueprint")]),
        (("mountain", "snow", "ice", "antarctic", "desert", "sahara", "polar"),
         [("a vast empty landscape beneath a pale overcast sky", "a weathered travel satchel"),
          ("a small expedition camp in the distance", "a folded field map"),
          ("a narrow trail between distant ridges", "a brass compass"),
          ("a quiet shelter with a small table", "a simple pocket watch"),
          ("a high viewpoint over an empty plain", "a signal lantern"),
          ("a records table holding expedition notes", "a leather-bound journal")]),
        (("city", "street", "town", "building", "house", "fire", "smog"),
         [("a muted historic city street with geometric buildings", "a folded newspaper"),
          ("a quiet civic office with tall windows", "a bound public record"),
          ("a narrow street between old stone buildings", "a hanging street lantern"),
          ("a rooftop view across the town", "a simple city map"),
          ("a workshop where repairs are being planned", "a rolled architectural plan"),
          ("a calm public square after the event", "a small memorial-free plaque")]),
    ]
    selected = next((items for terms, items in domains if any(k in value for k in terms)), None)
    if selected is None:
        selected = [
            ("a quiet archive with shelves of old books", "an open ledger"),
            ("a sparse room with a wooden table and one window", "a pocket watch"),
            ("a muted town square at early morning", "a folded newspaper"),
            ("a wide landscape with distant low hills", "a weathered travel bag"),
            ("a simple office with a tall window", "a sealed envelope"),
            ("a workshop table beneath a shaded lamp", "a small brass instrument"),
        ]
    setting, object_name = selected[index % len(selected)]

    if stage == "journey":
        action = "the figure takes a few slow steps through the setting"
    elif stage == "discovery":
        action = "the figure leans slightly toward the clearly visible object"
    elif stage == "decision":
        action = "two generic figures quietly consider the object together"
    elif stage == "aftermath":
        action = "the figure stands still, looking across the changed environment"
    elif stage == "turning point":
        action = "the figure carefully places one hand beside the important object"
    elif stage == "legacy":
        action = "the figure studies the preserved record in a calm archive"
    elif any(k in value for k in ("build", "built", "create", "invent", "construct")):
        action = "the figure carefully arranges the tools beside the object"
    elif any(k in value for k in ("read", "study", "record", "write", "calculate")):
        action = "the figure studies the object at the table"
    else:
        action = "the figure slowly turns toward the object"

    return (
        f"{setting}, {stage} in the story, {stage_action}; "
        f"{object_name} clearly visible as the primary story prop on the right third of frame, "
        f"one generic stick figure placed on the left third in period-appropriate muted clothing; "
        f"{action}. Use a distinct camera composition and restrained early-morning light. "
        "No named people, no flags, no insignia, no logos, no violence, no injury and no weapons."
    )

_TOPIC_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "from", "and", "for",
    "story", "history", "event", "true", "remarkable", "great", "lost", "city",
    "first", "man", "who", "race", "reach", "mystery", "disappearance", "case",
}


def _topic_terms(value):
    """Keep distinctive subject words; discard generic framing and dates."""
    return {
        token for token in re.findall(r"[a-z]+", (value or "").lower())
        if len(token) > 1 and token not in _TOPIC_STOPWORDS
    }


def _title_relevance(topic, title):
    """Return query coverage and title precision for ranking candidate articles."""
    terms = _topic_terms(topic)
    if not terms:
        return (1.0, 1.0)
    title_terms = _topic_terms(title)
    overlap = len(terms & title_terms)
    coverage = overlap / len(terms)
    precision = overlap / len(title_terms) if title_terms else 0.0
    return (coverage, precision)


class _ArticleTextParser(HTMLParser):
    """Extract readable article paragraphs while ignoring navigation and references."""

    BLOCK_TAGS = {"p", "h2", "h3"}
    SKIP_TAGS = {"table", "sup", "style", "script", "noscript", "nav", "aside",
                 "figure", "ol", "ul"}
    SKIP_CLASSES = {"navbox", "infobox", "metadata", "mw-references-wrap",
                    "hatnote", "ambox", "sidebar"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                 "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = []
        self._skip_stack = []
        self._active_tag = None
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if self._skip_stack:
            if tag not in self.VOID_TAGS:
                self._skip_stack.append(tag)
            return
        if tag in self.SKIP_TAGS or classes.intersection(self.SKIP_CLASSES):
            if tag not in self.VOID_TAGS:
                self._skip_stack = [tag]
            return
        if tag in self.BLOCK_TAGS:
            self._active_tag = tag
            self._buffer = []

    def handle_endtag(self, tag):
        if self._skip_stack:
            for index in range(len(self._skip_stack) - 1, -1, -1):
                if self._skip_stack[index] == tag:
                    del self._skip_stack[index:]
                    break
            return
        if tag == self._active_tag:
            value = re.sub(r"\\s+", " ", html.unescape("".join(self._buffer))).strip()
            if value:
                self.paragraphs.append(value)
            self._active_tag = None
            self._buffer = []

    def handle_data(self, data):
        if not self._skip_stack and self._active_tag:
            self._buffer.append(data)


def _extract_article_text(markup):
    parser = _ArticleTextParser()
    parser.feed(markup or "")
    parser.close()
    return "\\n".join(parser.paragraphs)


def research_topic(topic, duration_seconds):
    topic = re.sub(r"\\s+", " ", (topic or "")).strip()
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
        "prop": "info",
        "inprop": "url",
        "format": "json",
        "formatversion": 2,
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise ValueError("No suitable Wikipedia research page was found. Try a more specific topic.")
    ranked_pages = sorted(
        pages,
        key=lambda page: _title_relevance(topic, page.get("title", "")),
        reverse=True,
    )
    primary = ranked_pages[0]
    coverage, precision = _title_relevance(topic, primary.get("title", ""))
    if len(_topic_terms(topic)) >= 2 and (coverage < 0.60 or precision < 0.75):
        raise ValueError(
            "Wikipedia search did not return a clearly matching article for this topic. "
            "Try a more specific title so the video is not built from an unrelated story."
        )
    title = primary.get("title", topic)
    page_id = primary.get("pageid")
    if not page_id:
        raise ValueError("Wikipedia search did not provide a readable article identifier. Try again.")

    # Search-generator extracts are capped and may be attached to a different
    # result page. Fetch the selected primary article directly by page ID.
    parsed = _api({
        "action": "parse",
        "pageid": page_id,
        "prop": "text",
        "disableeditsection": 1,
        "disabletoc": 1,
        "format": "json",
        "formatversion": 2,
    })
    primary_text = _extract_article_text(parsed.get("parse", {}).get("text", ""))
    if not primary_text:
        raise ValueError(
            "Wikipedia returned no readable text for the selected primary article. "
            "Try another topic or retry later."
        )
    sentences = _sentences(primary_text)
    words = " ".join(sentences).split()
    if len(words) < target_words:
        raise ValueError(
            f"The primary Wikipedia article provides only {len(words)} usable words, but a complete {duration_seconds}-second narration needs {target_words}. "
            "Choose a shorter duration or a topic with a longer primary article. The engine will not fill gaps from unrelated pages or invent facts."
        )
    sources = []
    for page in ranked_pages:
        page_coverage, page_precision = _title_relevance(topic, page.get("title", ""))
        if page is primary or (page_coverage >= 0.60 and page_precision >= 0.50):
            if page.get("title") and page.get("fullurl"):
                sources.append({"title": page["title"], "url": page["fullurl"]})
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
        "storyboard": "\\n".join(anchors),
        "sources": sources,
        "research_note": "Narration is assembled from the selected primary Wikipedia article. Review the citations and wording before publication.",
        "source_license": "Wikipedia text is available under CC BY-SA; attribute the linked sources when publishing adapted text."
    }
