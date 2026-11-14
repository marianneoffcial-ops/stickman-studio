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
    JOBS, PROJECTS, _render_work, project_folder, queue_projects, safe_uuid,
    save_json, validate_aspect_ratio, validate_renderable_project, validate_sources,
    verify_mp4
)
from app.story import make_project


class ProductionApiTests(unittest.TestCase):
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
        with self.assertRaisesRegex(HTTPException, "draft"):
            validate_renderable_project(project)

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
                {"codec_type": "video", "width": 1280, "height": 720},
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
