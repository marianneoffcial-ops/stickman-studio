import math, re, uuid

HOUSE_STYLE = ("Hand-inked 2D illustrated animation with thick slightly rough black ink outlines "
"of varying weight. Characters are simple stick figures with a large perfectly round white head, "
"small solid black oval eyes, thin curved eyebrow strokes, a single simple curved line for the mouth, "
"no nose, and a few loose ink strokes suggesting hair across the top of the head. Bodies are minimal "
"with softly rounded shoulders and flat muted clothing in desaturated colours such as navy blue, "
"brick red and olive. Backgrounds are flat hand-drawn illustrated environments in a muted earthy "
"palette of tan, sage, dusty grey and cream, outlined in the same black ink, with simple geometric "
"architecture and sparse detail. A fine horizontal scanline and paper-grain texture overlays the "
"entire frame, with a soft dark vignette at the edges. Cinematic desaturated colour grade, restrained "
"and slightly melancholy, no bright saturated colours, no gradients, no photorealism, no 3D render, "
"no anime, no glossy digital finish.")

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
 "Narrator":{"costume":"navy coat","color":"#34465a"},
 "Historian":{"costume":"olive jacket","color":"#737653"},
 "Witness":{"costume":"brick-red scarf","color":"#9a5144"},
 "Official":{"costume":"charcoal coat","color":"#55565a"}
}

def make_project(topic, duration_seconds, aspect_ratio="16:9"):
    topic=re.sub(r"\\s+"," ",topic).strip()[:500]
    duration=int(duration_seconds)
    count=max(1,math.ceil(duration/4))
    # Each beat is a distinct visual moment; avoid recycling the same five-line script.
    beats=[
      ("The Hook",f"What really happened in {topic}? The answer is stranger than most people imagine."),
      ("The Setting",f"To understand {topic}, we need to return to the world as it was then."),
      ("The Background",f"The details seemed ordinary at first, but small decisions were already changing events."),
      ("The First Clue",f"Then one detail stood out, raising questions that nobody could easily answer."),
      ("The Turning Point",f"That discovery changed the situation and forced everyone to reconsider what they knew."),
      ("The Wider Story",f"Accounts, records, and eyewitness details reveal a much more complicated picture."),
      ("The Consequences",f"The consequences reached far beyond the people who first witnessed the event."),
      ("The Mystery",f"Even today, some parts remain uncertain, and the evidence deserves careful examination."),
      ("The Legacy",f"Over time, the story became a lasting reminder of how history can surprise us."),
      ("The Closing",f"And that is why {topic} still matters, long after the moment itself has passed.")
    ]
    scene_types=["wide establishing view","medium character view","illustrated map or document close-up",
      "interior with a window and long shadows","object detail with a slow camera push",
      "street or landscape tracking view","overhead composition of evidence","silhouette against distant skyline",
      "quiet character reaction","wide closing composition"]
    scenes=[]
    for i in range(count):
        beat=beats[min(i,len(beats)-1)] if count<=len(beats) else beats[i%len(beats)]
        remaining=duration-i*4
        scene_duration=min(4,remaining)
        if count>len(beats):
            narration=beat[1] if i<len(beats) else f"The next detail adds another piece to the story of {topic}."
        else:
            narration=beat[1]
        scenes.append({"scene_id":f"scene_{i+1:03d}","title":beat[0] if i<len(beats) else f"Chapter {i+1}",
          "duration":scene_duration,"narration":narration,"visual":scene_types[i%len(scene_types)],
          "characters":["Narrator"] if i%3 else ["Narrator","Witness"],"action":["walk","look","study","turn","point"][i%5],
          "visual_prompt":f"{HOUSE_STYLE} Scene: {scene_types[i%len(scene_types)]}. Topic context: {topic}. "
          "Use generic figures and symbolic objects; no real-person likenesses, graphic harm, weapons, logos, or flags."})
    return {"project_id":str(uuid.uuid4()),"title":topic[:90].title(),"topic":topic,
      "duration_seconds":duration,"aspect_ratio":aspect_ratio,"language":"English",
      "style":HOUSE_STYLE,"characters":CHARACTERS,"scenes":scenes,"status":"queued",
      "scene_count":count,"thumbnail_path":None,"voice_engine":"edge-tts neural voice (with fallback)"}
