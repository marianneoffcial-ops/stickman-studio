import os,json,uuid,threading,time
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse,FileResponse
from pydantic import BaseModel,Field
from app.story import make_project,parse_production_brief
from worker.render import render_project

DATA=Path(os.getenv("DATA_DIR","/data"))
PROJECTS=DATA/"projects"
PROJECTS.mkdir(parents=True,exist_ok=True)
JOBS={}
app=FastAPI(title="Stickman Studio AI",version="2.1.0")

class Request(BaseModel):
 topic:str=Field(min_length=3,max_length=500)
 duration_seconds:int=Field(default=60,ge=15,le=int(os.getenv("MAX_VIDEO_SECONDS","600")))
 aspect_ratio:str=Field(default="16:9",pattern=r"^(16:9|9:16|1:1)$")
 narration_script:str=Field(default="",max_length=30000)
 storyboard:str=Field(default="",max_length=16000)

class ProductionRequest(BaseModel):
 production_brief:str=Field(min_length=100,max_length=60000)

def save(path,obj):
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")

def work(job_id,project):
 job=JOBS[job_id]
 job["status"]="rendering"
 try:
  folder=PROJECTS/project["project_id"]
  folder.mkdir(exist_ok=True)
  save(folder/"manifest.json",project)
  result=render_project(project,folder)
  if not result.exists() or result.stat().st_size<2048:
   raise RuntimeError("MP4 output verification failed")
  project["video_path"]=str(result)
  project["status"]="completed"
  save(folder/"project.json",project)
  job.update(status="completed",output=f"/api/jobs/{job_id}/download",output_bytes=result.stat().st_size,
              duration_seconds=project["duration_seconds"],aspect_ratio=project["aspect_ratio"])
 except Exception as e:
  job.update(status="failed",error=str(e))

def queue_project(project):
 job_id=str(uuid.uuid4())
 folder=PROJECTS/project["project_id"]
 folder.mkdir(exist_ok=True)
 save(folder/"project.json",project)
 JOBS[job_id]={"job_id":job_id,"project_id":project["project_id"],"status":"queued","created_at":time.time(),
               "title":project["title"],"duration_seconds":project["duration_seconds"],
               "aspect_ratio":project["aspect_ratio"]}
 threading.Thread(target=work,args=(job_id,project),daemon=True).start()
 return JOBS[job_id]

@app.get("/",response_class=HTMLResponse)
def home():
 return HTMLResponse((Path(__file__).parent/"static.html").read_text())

@app.get("/health")
def health():
 return {"status":"ok","renderer":"hand-inked-2d-vector-motion-comic","gpu_required":False,
         "script_and_storyboard_supported":True,"two_format_brief_parser":True}

@app.post("/api/projects")
def create(req:Request):
 p=make_project(req.topic,req.duration_seconds,req.aspect_ratio,req.narration_script,req.storyboard)
 job=queue_project(p)
 return {"project":p,"job":job}

@app.post("/api/production")
def create_production(req:ProductionRequest):
 parsed=parse_production_brief(req.production_brief)
 if len(parsed["short_script"].split())<80:
  raise HTTPException(422,"Could not find the complete 60-second voiceover script in the production brief.")
 if len(parsed["long_script"].split())<700:
  raise HTTPException(422,"Could not find the complete 10-minute narration script in the production brief.")
 if parsed["short_scene_count"]<10:
  raise HTTPException(422,"Could not find the 15 short-video scene prompts. Paste the complete production brief.")
 if parsed["long_anchor_count"]<6:
  raise HTTPException(422,"Could not find the six-act long-video storyboard anchors.")
 topic=parsed["topic"]
 short=make_project(topic,60,"9:16",parsed["short_script"],parsed["short_storyboard"])
 long=make_project(topic,600,"16:9",parsed["long_script"],parsed["long_storyboard"])
 short_job=queue_project(short)
 long_job=queue_project(long)
 return {"topic":topic,"short":{"project_id":short["project_id"],"scene_count":short["scene_count"],
          "script_word_count":short["script_word_count"],"storyboard_anchor_count":short["storyboard_anchor_count"],"job":short_job},
         "long":{"project_id":long["project_id"],"scene_count":long["scene_count"],
          "script_word_count":long["script_word_count"],"storyboard_anchor_count":long["storyboard_anchor_count"],"job":long_job}}

@app.get("/api/projects/{project_id}/thumbnail")
def thumbnail(project_id):
 path=PROJECTS/project_id/"thumbnail.jpg"
 if not path.exists():
  raise HTTPException(404,"Thumbnail not ready")
 return FileResponse(path,media_type="image/jpeg",filename="thumbnail.jpg")

@app.get("/api/jobs/{job_id}")
def status(job_id):
 if job_id not in JOBS:
  raise HTTPException(404,"Job not found")
 return JOBS[job_id]

@app.get("/api/jobs/{job_id}/download")
def download(job_id):
 job=JOBS.get(job_id)
 if not job or job["status"]!="completed":
  raise HTTPException(409,"MP4 not ready or not verified")
 project=json.loads((PROJECTS/job["project_id"]/"project.json").read_text())
 path=Path(project["video_path"])
 if not path.exists():
  raise HTTPException(404,"Output file missing")
 return FileResponse(path,media_type="video/mp4",filename=f"stickman-{project['duration_seconds']}s.mp4")
