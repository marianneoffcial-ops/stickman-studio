import re, uuid
CHARACTERS = {
 "Arman":{"costume":"navy cloak","color":"#26354d"},
 "Mira":{"costume":"olive robe","color":"#69724b"},
 "Daren":{"costume":"brick-red scarf","color":"#9a4f3f"},
 "Watcher":{"costume":"dark hood and pale mask","color":"#33343a"}
}
def make_project(topic, duration_seconds, aspect_ratio):
 topic=re.sub(r"\s+"," ",topic).strip()[:500]
 beats=[
 ("The Omen",f"At the edge of a forgotten place, {topic[:90]} begins with a warning no one understands."),
 ("The Discovery","A lone stickman discovers a strange mark hidden beneath the dust."),
 ("The Pursuit","A shadow moves across the ruins. The companions realize they are not alone."),
 ("The Choice","They must decide whether to break the seal or leave the truth buried."),
 ("The Revelation","The mark changes shape. Something ancient has noticed them.")
 ]
 count=max(3,min(12,round(duration_seconds/12)))
 scenes=[]
 for i in range(count):
  title,line=beats[i%len(beats)]
  scenes.append({"scene_id":f"scene_{i+1:02d}","title":title,"duration":round(duration_seconds/count,2),
   "narration":line,"visual":["wide establishing shot","medium character shot","slow tracking shot","close-up of the symbol","dramatic reveal"][i%5],
   "characters":["Arman","Mira"] if i%2==0 else ["Arman","Daren"],"action":["walk","look","run","point","turn"][i%5]})
 return {"project_id":str(uuid.uuid4()),"title":topic[:90].title(),"topic":topic,"duration_seconds":duration_seconds,
  "aspect_ratio":aspect_ratio,"language":"English","style":"hand-inked 2D stickman, rough black outlines, muted cinematic palette, paper grain",
  "characters":CHARACTERS,"scenes":scenes,"status":"queued"}
