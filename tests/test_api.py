import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="stickman-api-tests-"))

from fastapi import HTTPException
from app.main import (
    JOBS, PROJECTS, Request, _render_work, download, health, preview, preview_frame, project_folder, queue_projects, safe_uuid,
    save_json, validate_aspect_ratio, validate_renderable_project, validate_sources,
    verify_mp4
)
from app.story import make_project


class ProductionApiTests(unittest.TestCase):
    def test_request_accepts_full_150_scene_storyboard_for_ten_minute_video(self):
        storyboard = "\\n".join(
            f"Scene {index + 1}: a distinct historical setting, a clear action, a story-specific prop, "
            "a motivated camera composition and a restrained painterly environment. "
            for index in range(150)
        )
        self.assertGreater(len(storyboard), 16000)
        request = Request(
            topic="A documented historical event",
            duration_seconds=600,
            aspect_ratio="16:9",
            narration_script="A documented fact. " * 150,
            storyboard=storyboard,
            narration_beats=[f"Beat {index + 1} contains a concise researched narration line." for index in range(150)],
        )
        self.assertEqual(request.duration_seconds, 600)
        self.assertEqual(len(request.storyboard.splitlines()), 150)
        self.assertEqual(len(request.narration_beats), 150)

    def test_health_reports_the_configured_flux_two_background_model(self):
        with patch.dict(os.environ, {
            "CLOUDFLARE_ACCOUNT_ID": "test-account",
            "CLOUDFLARE_API_TOKEN": "test-token",
        }):
            payload = health()
        self.assertTrue(payload["cloudflare_ai_backgrounds_configured"])
        self.assertEqual(
            payload["cloudflare_ai_background_model"],
            "@cf/black-forest-labs/flux-2-klein-4b",
        )

    def test_aspect_ratio_accepts_supported_custom_ratio(self):
        self.assertEqual(validate_aspect_ratio("4:5"), "4:5")
        self.assertEqual(validate_aspect_ratio("16:9"), "16:9")

    def test_aspect_ratio_rejects_zero_and_extreme_values(self):
        for ratio in ("0:9", "16:0", "99:1", "wide"):
            with self.subTest(ratio=ratio), self.assertRaises(HTTPException):
                validate_aspect_ratio(ratio)

    def test_uuid_validation_blocks_path_traversal(self):
        with self.assertRaises(HTTPException):
            safe_uuid("../../etc/passwd", "project")
        with self.assertRaises(HTTPException):
            project_folder("not-a-uuid")

    def test_project_folder_stays_inside_projects_directory(self):
        project_id = "4a5a4a5a-1111-4222-8333-123456789abc"
        self.assertEqual(project_folder(project_id).parent, PROJECTS.resolve())

    def test_sources_accept_http_links_and_reject_script_schemes(self):
        clean = validate_sources([{"title": "Source", "url": "https://example.org/page"}])
        self.assertEqual(clean[0]["url"], "https://example.org/page")
        with self.assertRaises(HTTPException):
            validate_sources([{"title": "Bad", "url": "javascript:alert(1)"}])

    def test_render_rejects_missing_scene_narration(self):
        project = make_project("A quiet boat crossing", 15, "16:9", "", "")
        with self.assertRaises(HTTPException) as raised:
            validate_renderable_project(project)
        self.assertIn("draft", raised.exception.detail)

    def test_render_accepts_complete_narration(self):
        project = make_project(
            "A quiet boat crossing", 15, "16:9",
            "A small boat crossed the quiet grey sea before dawn and reached the harbour.",
            "A boat crosses a quiet sea."
        )
        self.assertIs(validate_renderable_project(project), project)

    def test_json_writes_are_atomic_and_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "job.json"
            save_json(path, {"status": "queued", "progress": 0})
            self.assertEqual(json.loads(path.read_text()), {"status": "queued", "progress": 0})
            self.assertFalse(path.with_name("job.json.tmp").exists())

    def test_mp4_verification_checks_video_audio_duration_and_dimensions(self):
        project = {"duration_seconds": 60, "aspect_ratio": "16:9"}
        output = json.dumps({
            "format": {"duration": "60.0"},
            "streams": [
                {"codec_type": "video", "width": 1280, "height": 720, "avg_frame_rate": "24/1"},
                {"codec_type": "audio"}
            ]
        })
        with patch("app.main.shutil.which", return_value="/usr/bin/ffprobe"), \
             patch("app.main.subprocess.run", return_value=SimpleNamespace(
                 returncode=0, stdout=output, stderr=""
             )):
            result = verify_mp4(Path("final.mp4"), project)
        self.assertEqual(result["width"], 1280)
        self.assertEqual(result["height"], 720)
        self.assertTrue(result["has_audio"])
        self.assertEqual(result["duration_seconds"], 60.0)
        self.assertEqual(result["fps"], 24.0)

    def test_mp4_verification_rejects_wrong_frame_rate(self):
        project = {"duration_seconds": 60, "aspect_ratio": "16:9"}
        output = json.dumps({
            "format": {"duration": "60.0"},
            "streams": [
                {"codec_type": "video", "width": 1280, "height": 720, "avg_frame_rate": "12/1"},
                {"codec_type": "audio"}
            ]
        })
        with patch("app.main.shutil.which", return_value="/usr/bin/ffprobe"):
            with patch("app.main.subprocess.run", return_value=SimpleNamespace(
                returncode=0, stdout=output, stderr=""
            )):
                with self.assertRaisesRegex(RuntimeError, "frame-rate verification"):
                    verify_mp4(Path("final.mp4"), project)

    def test_mp4_verification_rejects_wrong_duration(self):
        project = {"duration_seconds": 60, "aspect_ratio": "16:9"}
        output = json.dumps({
            "format": {"duration": "12.0"},
            "streams": [
                {"codec_type": "video", "width": 1280, "height": 720},
                {"codec_type": "audio"}
            ]
        })
        with patch("app.main.shutil.which", return_value="/usr/bin/ffprobe"), \
             patch("app.main.subprocess.run", return_value=SimpleNamespace(
                 returncode=0, stdout=output, stderr=""
             )):
            with self.assertRaisesRegex(RuntimeError, "duration verification"):
                verify_mp4(Path("final.mp4"), project)

    def test_completed_job_has_inline_video_preview_page(self):
        project_id = "4a5a4a5a-1111-4222-8333-123456789abc"
        job_id = "5b5b5b5b-2222-4333-8444-123456789abc"
        folder = PROJECTS / project_id
        folder.mkdir(parents=True, exist_ok=True)
        video = folder / "final.mp4"
        video.write_bytes(b"test mp4")
        save_json(folder / "project.json", {
            "project_id": project_id, "duration_seconds": 15,
            "video_path": str(video)
        })
        JOBS[job_id] = {"job_id": job_id, "project_id": project_id, "status": "completed"}
        try:
            response = preview(job_id)
            self.assertIn("text/html", response.media_type)
            self.assertIn(f"/api/jobs/{job_id}/download?inline=true", response.body.decode())
            inline_file = download(job_id, inline=True)
            self.assertEqual(inline_file.headers.get("content-disposition"), "inline")
            self.assertEqual(inline_file.media_type, "video/mp4")
        finally:
            JOBS.pop(job_id, None)
            import shutil
            shutil.rmtree(folder, ignore_errors=True)

    def test_completed_job_can_extract_a_real_mp4_frame_for_visual_review(self):
        project_id = "6c6c6c6c-3333-4444-8555-123456789abc"
        job_id = "7d7d7d7d-4444-4555-8666-123456789abc"
        folder = PROJECTS / project_id
        folder.mkdir(parents=True, exist_ok=True)
        video = folder / "final.mp4"
        video.write_bytes(b"test mp4")
        save_json(folder / "project.json", {
            "project_id": project_id, "duration_seconds": 15,
            "video_path": str(video)
        })
        JOBS[job_id] = {"job_id": job_id, "project_id": project_id, "status": "completed"}

        def fake_ffmpeg(args, **kwargs):
            Path(args[-1]).write_bytes(b"jpeg frame")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        try:
            with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), \
                 patch("app.main.subprocess.run", side_effect=fake_ffmpeg) as run_ffmpeg:
                response = preview_frame(job_id, second=8.0)
            self.assertEqual(response.media_type, "image/jpeg")
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            self.assertIn("8.000", run_ffmpeg.call_args.args[0])
        finally:
            JOBS.pop(job_id, None)
            import shutil
            shutil.rmtree(folder, ignore_errors=True)

    def test_queue_persists_job_and_returns_progress_fields(self):
        project = make_project(
            "A quiet boat crossing", 15, "16:9",
            "A small boat crossed the quiet grey sea before dawn and reached the harbour.",
            "A boat crosses a quiet sea."
        )
        folder = PROJECTS / project["project_id"]
        with patch("app.main.RENDER_POOL.submit", return_value=None):
            job = queue_projects([project])[0]
        try:
            self.assertEqual(job["status"], "queued")
            self.assertEqual(job["progress"], 0)
            self.assertEqual(job["total_scenes"], project["scene_count"])
            self.assertTrue((folder / "job.json").is_file())
            self.assertTrue((folder / "project.json").is_file())
        finally:
            JOBS.pop(job["job_id"], None)
            import shutil
            shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
