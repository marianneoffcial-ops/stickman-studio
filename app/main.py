import os,json,uuid,threading,time
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse,FileResponse
from pydantic import BaseModel,Field
from app.story import make_project
from worker.render import render_project
DATA=Path(os.getenv("DATA_DIR","/data")); PROJECTS=DATA/"projects"; PROJECTS.mkdir(parents=True,exist_ok=True)
JOBS={}
app=FastAPI(title="Stickman Studio AI",version="2.0.0")
class Request(BaseModel):
 topic:str=Field(min_length=3,max_length=500)
 duration_seconds:int=Field(default=60,ge=15,le=int(os.getenv("MAX_VIDEO_SECONDS","600")))
 aspect_ratio:str=Field(default="16:9",pattern=r"^(16:9|9:16|1:1)$")
def save(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
def work(job_id,project):
 job=JOBS[job_id]; job["status"]="rendering"
 try:
  folder=PROJECTS/project["project_id"]; folder.mkdir(exist_ok=True)
  save(folder/"manifest.json",project)
  result=render_project(project,folder)
  if not result.exists() or result.stat().st_size<2048: raise RuntimeError("MP4 output verification failed")
  project["video_path"]=str(result); project["status"]="completed"; save(folder/"project.json",project)
  job.update(status="completed",output=f"/api/jobs/{job_id}/download",output_bytes=result.stat().st_size)
 except Exception as e: job.update(status="failed",error=str(e))
@app.get("/",response_class=HTMLResponse)
def home(): return HTMLResponse((Path(__file__).parent/"static.html").read_text())
@app.get("/health")
def health(): return {"status":"ok","renderer":"ffmpeg-vector","gpu_required":False}
@app.post("/api/projects")
def create(req:Request):
 p=make_project(req.topic,req.duration_seconds,req.aspect_ratio); j=str(uuid.uuid4())
 folder=PROJECTS/p["project_id"]; folder.mkdir(exist_ok=True); save(folder/"project.json",p)
 JOBS[j]={"job_id":j,"project_id":p["project_id"],"status":"queued","created_at":time.time()}
 threading.Thread(target=work,args=(j,p),daemon=True).start()
 return {"project":p,"job":JOBS[j]}
@app.get("/api/jobs/{job_id}")
def status(job_id):
 if job_id not in JOBS: raise HTTPException(404,"Job not found")
 return JOBS[job_id]
@app.get("/api/jobs/{job_id}/download")
def download(job_id):
 j=JOBS.get(job_id)
 if not j or j["status"]!="completed": raise HTTPException(409,"MP4 not ready or not verified")
 p=json.loads((PROJECTS/j["project_id"]/"project.json").read_text())
 f=Path(p["video_path"])
 if not f.exists(): raise HTTPException(404,"Output file missing")
 return FileResponse(f,media_type="video/mp4",filename="stickman-video.mp4")
