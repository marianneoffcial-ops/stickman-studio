import json
import subprocess
import unittest
from pathlib import Path

from app.story import make_project
from worker.render import render_project, dimensions


class RenderSmokeTests(unittest.TestCase):
    def test_custom_aspect_ratio_is_preserved(self):
        width, height = dimensions("4:5")
        self.assertEqual(width / height, 4 / 5)

    def test_one_scene_produces_mp4_and_thumbnail(self):
        project = make_project(
            "A quiet boat crossing",
            4,
            "16:9",
            "The small boat crossed the quiet grey sea.",
            "Wide view of a small boat crossing a calm sea at dawn."
        )
        output_dir = Path("artifacts/smoke")
        output_dir.mkdir(parents=True, exist_ok=True)
        output = render_project(project, output_dir)
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 2048)
        self.assertTrue((output_dir / "thumbnail.jpg").exists())
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=width,height,r_frame_rate,codec_type",
            "-of", "json", str(output)
        ], text=True)
        data = json.loads(probe)
        self.assertAlmostEqual(float(data["format"]["duration"]), 4.0, delta=0.12)
        video = next(x for x in data["streams"] if x["codec_type"] == "video")
        self.assertEqual((video["width"], video["height"]), (1280, 720))
        self.assertEqual(video["r_frame_rate"], "24/1")


if __name__ == "__main__":
    unittest.main()
