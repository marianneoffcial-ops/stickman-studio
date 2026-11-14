import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.research import research_topic
from app.story import IDEAS, make_project, parse_production_brief
from worker.render import dimensions, render_project

DATA = Path(os.getenv("DATA_DIR", "/data")).resolve()
PROJECTS = DATA / "projects"
PROJECTS.mkdir(parents=True, exist_ok=True)
MAX_ACTIVE_JOBS = max(2, int(os.getenv("MAX_ACTIVE_JOBS", "8")))
JOBS = {}
JOBS_LOCK = threading.RLock()
RENDER_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stickman-render")
app = FastAPI(title="Stickman Studio AI", version="3.1.0")


class Request(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    duration_seconds: int = Field(default=60, ge=15, le=int(os.getenv("MAX_VIDEO_SECONDS", "600")))
    aspect_ratio: str = Field(default="16:9", pattern=r"^\d{1,2}:\d{1,2}$")
    narration_script: str = Field(default="", max_length=30000)
    storyboard: str = Field(default="", max_length=16000)
    research_sources: list[dict] = Field(default_factory=list, max_length=12)


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    duration_seconds: int = Field(ge=15, le=int(os.getenv("MAX_VIDEO_SECONDS", "600")))


class ProductionRequest(BaseModel):
    production_brief: str = Field(min_length=100, max_length=60000)


class DualProductionRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def safe_uuid(value, label="identifier"):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(404, f"{label.capitalize()} not found")


def project_folder(project_id):
    project_id = safe_uuid(project_id, "project")
    folder = (PROJECTS / project_id).resolve()
    if folder.parent != PROJECTS.resolve():
        raise HTTPException(404, "Project not found")
    return folder


def validate_aspect_ratio(value):
    match = re.fullmatch(r"(\d{1,2}):(\d{1,2})", str(value or ""))
    if not match:
        raise HTTPException(422, "Aspect ratio must look like 16:9, 9:16, or 1:1.")
    width, height = (int(part) for part in match.groups())
    if not width or not height or width > 32 or height > 32:
        raise HTTPException(422, "Aspect ratio values must be between 1 and 32.")
    ratio = width / height
    if ratio < 0.25 or ratio > 4:
        raise HTTPException(422, "Aspect ratios narrower than 1:4 or wider than 4:1 are not supported.")
    return f"{width}:{height}"


def validate_sources(sources):
    clean = []
    for source in sources or []:
        if not isinstance(source, dict):
            raise HTTPException(422, "Each research source must be an object.")
        title = str(source.get("title", "")).strip()[:300]
        url = str(source.get("url", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise HTTPException(422, "Research source links must be valid HTTP or HTTPS URLs.")
        clean.append({"title": title or parsed.netloc, "url": url[:2000]})
    return clean[:12]


def validate_renderable_project(project):
    scenes = project.get("scenes") or []
    if not scenes:
        raise HTTPException(422, "The project has no scenes to render.")
    missing = [scene.get("scene_id", str(index + 1)) for index, scene in enumerate(scenes)
               if not str(scene.get("narration", "")).strip()
               or str(scene.get("narration", "")).startswith("[SCRIPT REQUIRED]")]
    if missing:
        raise HTTPException(
            422,
            "This is a draft, not a render-ready video. Add complete narration for every scene before rendering."
        )
    return project


def persist_job(job):
    folder = project_folder(job["project_id"])
    save_json(folder / "job.json", job)


def public_job(job):
    return dict(job)


def restore_jobs():
    """Restore job history when the app process restarts on a persistent data directory."""
    for folder in PROJECTS.iterdir():
        if not folder.is_dir():
            continue
        try:
            project_id = safe_uuid(folder.name, "project")
            job_path = folder / "job.json"
            if not job_path.is_file():
                continue
            job = json.loads(job_path.read_text(encoding="utf-8"))
            if job.get("project_id") != project_id or not job.get("job_id"):
                continue
            safe_uuid(job["job_id"], "job")
            if job.get("status") in ("queued", "rendering"):
                job.update(
                    status="failed",
                    error="Rendering was interrupted by a server restart. Submit the project again.",
                    completed_at=time.time(),
                )
            if job.get("status") == "completed":
                project_path = folder / "project.json"
                project = json.loads(project_path.read_text(encoding="utf-8"))
                output = Path(project.get("video_path", ""))
                if not output.is_file() or output.stat().st_size < 2048:
                    job.update(status="failed", error="The completed MP4 is missing or incomplete.")
            JOBS[job["job_id"]] = job
            persist_job(job)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue


def active_job_count():
    return sum(1 for job in JOBS.values() if job.get("status") in ("queued", "rendering"))


def update_job(job_id, **changes):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return
        job.update(changes)
        snapshot = dict(job)
    try:
        persist_job(snapshot)
    except OSError:
        # Keep the in-memory job usable even if an ephemeral disk is temporarily unavailable.
        pass


def verify_mp4(path, project):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe is required to verify the finished MP4.")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height",
         "-of", "json", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30
    )
    if result.returncode:
        raise RuntimeError("FFprobe could not read the finished MP4.")
    try:
        metadata = json.loads(result.stdout)
        streams = metadata.get("streams", [])
        video = next(stream for stream in streams if stream.get("codec_type") == "video")
        audio = next(stream for stream in streams if stream.get("codec_type") == "audio")
        duration = float(metadata["format"]["duration"])
    except (ValueError, KeyError, StopIteration, TypeError):
        raise RuntimeError("The MP4 is missing a valid video, audio, or duration stream.")
    expected_width, expected_height = dimensions(project["aspect_ratio"])
    if (int(video.get("width", 0)), int(video.get("height", 0))) != (expected_width, expected_height):
        raise RuntimeError("The rendered MP4 dimensions do not match the selected aspect ratio.")
    if abs(duration - float(project["duration_seconds"])) > 0.20:
        raise RuntimeError(
            f"MP4 duration verification failed: expected {project['duration_seconds']} seconds, got {duration:.2f}."
        )
    return {"duration_seconds": round(duration, 3), "width": expected_width, "height": expected_height,
            "has_audio": bool(audio)}


def _render_work(job_id, project):
    folder = project_folder(project["project_id"])
    started = time.time()
    update_job(job_id, status="rendering", started_at=started, progress=0,
               completed_scenes=0, total_scenes=len(project["scenes"]), error=None)
    try:
        save_json(folder / "manifest.json", project)

        def on_progress(completed, total):
            percent = min(95, int((completed / max(1, total)) * 95))
            update_job(job_id, progress=percent, completed_scenes=completed, total_scenes=total)

        result = render_project(project, folder, progress_callback=on_progress)
        if not result.is_file() or result.stat().st_size < 2048:
            raise RuntimeError("MP4 output verification failed: file is missing or too small.")
        verification = verify_mp4(result, project)
        project["video_path"] = str(result)
        project["status"] = "completed"
        save_json(folder / "project.json", project)
        finished = time.time()
        update_job(
            job_id, status="completed", progress=100, completed_scenes=len(project["scenes"]),
            output=f"/api/jobs/{job_id}/download", output_bytes=result.stat().st_size,
            duration_seconds=verification["duration_seconds"], aspect_ratio=project["aspect_ratio"],
            width=verification["width"], height=verification["height"], has_audio=verification["has_audio"],
            voice_engine=project.get("voice_engine"), completed_at=finished,
            elapsed_seconds=round(finished - started, 2), error=None
        )
    except Exception as exc:
        finished = time.time()
        update_job(job_id, status="failed", completed_at=finished,
                   elapsed_seconds=round(finished - started, 2), error=str(exc)[:1200])


def queue_projects(projects):
    now = time.time()
    prepared = []
    with JOBS_LOCK:
        if active_job_count() + len(projects) > MAX_ACTIVE_JOBS:
            raise HTTPException(
                429,
                f"The render queue is full ({MAX_ACTIVE_JOBS} active jobs). Wait for a video to finish, then retry."
            )
        for project in projects:
            project_id = safe_uuid(project["project_id"], "project")
            folder = project_folder(project_id)
            folder.mkdir(parents=True, exist_ok=True)
            save_json(folder / "project.json", project)
            job_id = str(uuid.uuid4())
            job = {
                "job_id": job_id, "project_id": project_id, "status": "queued",
                "created_at": now, "title": project["title"],
                "duration_seconds": project["duration_seconds"], "aspect_ratio": project["aspect_ratio"],
                "progress": 0, "completed_scenes": 0, "total_scenes": len(project["scenes"]),
                "output": None, "error": None
            }
            JOBS[job_id] = job
            persist_job(job)
            prepared.append((job_id, project, dict(job)))
    for job_id, project, _ in prepared:
        try:
            RENDER_POOL.submit(_render_work, job_id, project)
        except RuntimeError as exc:
            update_job(job_id, status="failed", error="Render worker is unavailable: " + str(exc)[:300],
                       completed_at=time.time())
    return [item[2] for item in prepared]


def queue_project(project):
    return queue_projects([project])[0]


restore_jobs()


@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse((Path(__file__).parent / "static.html").read_text(encoding="utf-8"))


@app.get("/health")
def health():
    with JOBS_LOCK:
        queued = active_job_count()
        completed = sum(1 for job in JOBS.values() if job.get("status") == "completed")
        failed = sum(1 for job in JOBS.values() if job.get("status") == "failed")
    return {
        "status": "ok", "version": app.version,
        "renderer": "deterministic-hand-inked-2d-vector-motion-comic",
        "gpu_required": False, "free_research": "Wikipedia API",
        "active_jobs": queued, "completed_jobs": completed, "failed_jobs": failed,
        "max_active_jobs": MAX_ACTIVE_JOBS
    }


@app.get("/ready")
def ready():
    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if not (shutil.which("edge-tts") or shutil.which("espeak-ng") or shutil.which("espeak")):
        missing.append("edge-tts or espeak-ng")
    if not PROJECTS.is_dir() or not os.access(PROJECTS, os.W_OK):
        missing.append("writable project directory")
    payload = {"ready": not missing, "missing": missing}
    return payload if not missing else JSONResponse(payload, status_code=503)


@app.get("/api/ideas")
def ideas():
    categories = {
        "history": {"The Lost City of Pompeii", "The Great Fire of London", "The Great Stink of 1858",
                    "The First Transatlantic Telegraph Cable", "The Panama Canal", "The Great Library of Alexandria",
                    "The Race to Decode the Rosetta Stone", "The Great Emu War"},
        "documentary": {"The Race to Reach the South Pole", "The Franklin Expedition", "The 1904 Olympic Marathon",
                        "The 1952 Great Smog of London", "The Chilean Miners Rescue",
                        "The 1906 San Francisco Earthquake", "The 1969 Moon Landing", "The Apollo 13 Rescue"},
        "true crime": {"The Great Escape from Alcatraz", "The Man Who Sold the Eiffel Tower",
                       "The Mystery of D. B. Cooper", "The Great Train Robbery of 1963",
                       "The Isabella Stewart Gardner Museum Heist", "The Han van Meegeren Art Forgery"},
        "remarkable true events": {"The Great Molasses Flood of 1919", "The Cuban Missile Crisis Officer",
                                   "The 1914 Christmas Truce", "Operation Mincemeat", "The Tunguska Event",
                                   "The 1972 Andes Flight Disaster", "The Great Canadian Maple Syrup Heist"}
    }
    result = []
    for title, hook in IDEAS:
        category = next((name for name, items in categories.items() if title in items), "history")
        result.append({"title": title, "hook": hook, "category": category})
    return {"ideas": result}


@app.post("/api/research")
def research(req: ResearchRequest):
    try:
        return research_topic(req.topic.strip(), req.duration_seconds)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        raise HTTPException(503, "Free research is temporarily unavailable. Please retry later.")


def build_request_project(req):
    topic = re.sub(r"\s+", " ", req.topic).strip()
    if len(topic) < 3:
        raise HTTPException(422, "Topic must contain at least three non-space characters.")
    ratio = validate_aspect_ratio(req.aspect_ratio)
    sources = validate_sources(req.research_sources)
    project = make_project(topic, req.duration_seconds, ratio, req.narration_script, req.storyboard)
    project["research_sources"] = sources
    return project


@app.post("/api/prepare")
def prepare(req: Request):
    return {"project": build_request_project(req)}


@app.post("/api/projects")
def create(req: Request):
    project = validate_renderable_project(build_request_project(req))
    job = queue_project(project)
    return {"project": project, "job": job}


@app.post("/api/production/topic")
def create_dual_production(req: DualProductionRequest):
    topic = re.sub(r"\s+", " ", req.topic).strip()
    if len(topic) < 3:
        raise HTTPException(422, "Topic must contain at least three non-space characters.")
    try:
        short_research = research_topic(topic, 60)
        long_research = research_topic(topic, 600)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        raise HTTPException(503, "Free research is temporarily unavailable. Please retry later.")
    topic = short_research["topic"]
    short = make_project(topic, 60, "9:16", short_research["narration_script"], short_research["storyboard"])
    long = make_project(topic, 600, "16:9", long_research["narration_script"], long_research["storyboard"])
    short["research_sources"] = validate_sources(short_research.get("sources", []))
    long["research_sources"] = validate_sources(long_research.get("sources", []))
    validate_renderable_project(short)
    validate_renderable_project(long)
    short_job, long_job = queue_projects([short, long])
    return {
        "topic": topic,
        "short": {"project_id": short["project_id"], "duration_seconds": 60, "aspect_ratio": "9:16",
                  "scene_count": short["scene_count"], "script_word_count": short["script_word_count"],
                  "thumbnail_prompt": short["thumbnail_prompt"], "job": short_job},
        "long": {"project_id": long["project_id"], "duration_seconds": 600, "aspect_ratio": "16:9",
                 "scene_count": long["scene_count"], "script_word_count": long["script_word_count"],
                 "thumbnail_prompt": long["thumbnail_prompt"], "job": long_job},
        "sources": short_research["sources"]
    }


@app.post("/api/production")
def create_production(req: ProductionRequest):
    parsed = parse_production_brief(req.production_brief)
    if len(parsed["short_script"].split()) < 80:
        raise HTTPException(422, "Could not find the complete 60-second voiceover script in the production brief.")
    if len(parsed["long_script"].split()) < 700:
        raise HTTPException(422, "Could not find the complete 10-minute narration script in the production brief.")
    if parsed["short_scene_count"] < 10:
        raise HTTPException(422, "Could not find the 15 short-video scene prompts. Paste the complete production brief.")
    if parsed["long_anchor_count"] < 6:
        raise HTTPException(422, "Could not find the six-act long-video storyboard anchors.")
    topic = parsed["topic"]
    short = make_project(topic, 60, "9:16", parsed["short_script"], parsed["short_storyboard"])
    long = make_project(topic, 600, "16:9", parsed["long_script"], parsed["long_storyboard"])
    validate_renderable_project(short)
    validate_renderable_project(long)
    short_job, long_job = queue_projects([short, long])
    return {
        "topic": topic,
        "short": {"project_id": short["project_id"], "scene_count": short["scene_count"],
                  "script_word_count": short["script_word_count"],
                  "storyboard_anchor_count": short["storyboard_anchor_count"], "job": short_job},
        "long": {"project_id": long["project_id"], "scene_count": long["scene_count"],
                 "script_word_count": long["script_word_count"],
                 "storyboard_anchor_count": long["storyboard_anchor_count"], "job": long_job}
    }


@app.get("/api/jobs")
def list_jobs(limit: int = 20, offset: int = 0):
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    with JOBS_LOCK:
        ordered = sorted(JOBS.values(), key=lambda item: item.get("created_at", 0), reverse=True)
        total = len(ordered)
        items = [public_job(job) for job in ordered[offset:offset + limit]]
    return {"jobs": items, "total": total, "limit": limit, "offset": offset}


@app.get("/api/jobs/{job_id}")
def status(job_id):
    job_id = safe_uuid(job_id, "job")
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return public_job(job)


@app.get("/api/projects/{project_id}")
def project_status(project_id):
    folder = project_folder(project_id)
    path = folder / "project.json"
    if not path.is_file():
        raise HTTPException(404, "Project not found")
    project = json.loads(path.read_text(encoding="utf-8"))
    with JOBS_LOCK:
        job = next((public_job(item) for item in JOBS.values()
                    if item.get("project_id") == str(uuid.UUID(project_id))), None)
    return {"project_id": project_id, "title": project.get("title"), "status": project.get("status"),
            "duration_seconds": project.get("duration_seconds"), "aspect_ratio": project.get("aspect_ratio"),
            "scene_count": project.get("scene_count"), "job": job}


@app.get("/api/projects/{project_id}/thumbnail")
def thumbnail(project_id):
    path = project_folder(project_id) / "thumbnail.jpg"
    if not path.is_file():
        raise HTTPException(404, "Thumbnail not ready")
    return FileResponse(path, media_type="image/jpeg", filename="thumbnail.jpg")


@app.get("/api/jobs/{job_id}/download")
def download(job_id):
    job_id = safe_uuid(job_id, "job")
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        job = public_job(job) if job else None
    if not job or job.get("status") != "completed":
        raise HTTPException(409, "MP4 not ready or not verified")
    folder = project_folder(job["project_id"])
    project_path = folder / "project.json"
    if not project_path.is_file():
        raise HTTPException(404, "Project metadata missing")
    project = json.loads(project_path.read_text(encoding="utf-8"))
    path = Path(project.get("video_path", "")).resolve()
    if path.parent != folder.resolve() or not path.is_file():
        raise HTTPException(404, "Output file missing")
    return FileResponse(path, media_type="video/mp4",
                        filename=f"stickman-{project['duration_seconds']}s.mp4")
