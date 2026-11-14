import json
import subprocess
import unittest
from pathlib import Path
from PIL import Image

from app.story import make_project
from worker.render import render_project, dimensions, draw_frame, character_scale


class RenderSmokeTests(unittest.TestCase):
    def test_custom_aspect_ratio_is_preserved(self):
        width, height = dimensions("4:5")
        self.assertEqual(width / height, 4 / 5)

    def test_portrait_character_scale_uses_frame_height(self):
        width, height = dimensions("9:16")
        scale = character_scale(int(width * 1.5), int(height * 1.5), "medium character")
        self.assertGreater(scale, 2.5)

    def test_landscape_and_portrait_camera_scales_are_frame_aware(self):
        lw, lh = dimensions("16:9")
        pw, ph = dimensions("9:16")
        landscape = character_scale(int(lw * 1.5), int(lh * 1.5), "medium character")
        portrait = character_scale(int(pw * 1.5), int(ph * 1.5), "medium character")
        self.assertAlmostEqual(landscape, 1.5)
        self.assertGreater(portrait, landscape)
        self.assertLess(character_scale(1920, 1080, "wide silhouette"), landscape)

    def test_draw_person_accepts_narrative_expression_styles(self):
        from worker.render import draw_person
        from PIL import Image, ImageDraw
        for expression in ("neutral", "concerned", "surprised", "weary", "resolved"):
            image = Image.new("RGB", (240, 300), (220, 211, 190))
            draw_person(ImageDraw.Draw(image), 120, 250, .55, (52,70,90), 0.7,
                        role="Narrator", action="observe", expression=expression)
            self.assertEqual(image.size, (240, 300))

    def test_semantic_gesture_poses_render_distinct_silhouettes(self):
        from worker.render import draw_person
        from PIL import Image, ImageDraw, ImageChops
        poses = ("walk", "write", "carry", "raise", "point", "gesture")
        images = []
        for action in poses:
            image = Image.new("RGB", (320, 360), (220, 211, 190))
            draw_person(ImageDraw.Draw(image), 160, 280, .75, (52,70,90), 0.6,
                        role="Narrator", action=action)
            images.append(image)
        for index, image in enumerate(images[1:], 1):
            self.assertIsNotNone(ImageChops.difference(images[0], image).getbbox(),
                                 msg=f"{poses[index]} should differ visually from walk")

    def test_closeup_prioritizes_story_object_over_character(self):
        from worker.render import scene_composition
        width, height = dimensions("16:9")
        normal = scene_composition(width, height, "medium character")
        closeup = scene_composition(width, height, "close-up of a story-specific object")
        self.assertLess(closeup[0], normal[0])
        self.assertLess(closeup[1], .25)
        self.assertGreater(closeup[2], .75)

    def test_closeup_camera_crop_focuses_right_side_story_prop(self):
        from worker.render import scene_composition
        width, height = dimensions("16:9")
        scale, x_fraction, y_fraction = scene_composition(width, height, "close-up of a story-specific object")
        self.assertAlmostEqual(x_fraction, .16)
        self.assertAlmostEqual(y_fraction, .82)

    def test_story_prop_classifier_covers_distinct_objects(self):
        from worker.render import story_prop_kind
        self.assertEqual(story_prop_kind("a folded nautical chart"), "map")
        self.assertEqual(story_prop_kind("a brass compass"), "compass")
        self.assertEqual(story_prop_kind("a sealed paper letter"), "letter")
        self.assertEqual(story_prop_kind("a hanging lantern"), "lantern")
        self.assertEqual(story_prop_kind("a leather-bound journal"), "ledger")
        self.assertEqual(story_prop_kind("a weathered telescope"), "telescope")

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
        frame = output_dir / "supersampled-frame.png"
        draw_frame(project["scenes"][0], project, 0, 2, frame)
        with Image.open(frame) as image:
            self.assertEqual(image.size, (1280, 720))
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
