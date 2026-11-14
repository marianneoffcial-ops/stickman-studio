import unittest
from pathlib import Path

from app.story import make_project
from worker.render import render_project


class RenderSmokeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
