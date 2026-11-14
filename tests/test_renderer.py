import json
import subprocess
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from app.story import make_project
from worker.render import render_project, dimensions, draw_frame, character_scale, synthesize_ambience, atmosphere_particles, draw_primary_story_prop


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

    def test_semantic_camera_motion_changes_crop_over_time(self):
        from worker.render import camera_crop_box
        width, height = 1920, 1080
        for camera in ("wide establishing shot", "close-up of a story-specific object",
                       "side-on tracking composition", "overhead view"):
            first = camera_crop_box(width, height, camera, 0, 48)
            last = camera_crop_box(width, height, camera, 47, 48)
            self.assertNotEqual(first, last, camera)
            self.assertGreaterEqual(first[0], 0)
            self.assertGreaterEqual(first[1], 0)
            self.assertLessEqual(last[2], width)
            self.assertLessEqual(last[3], height)
            self.assertGreater(first[2] - first[0], width * .90)

    def test_scene_transition_cross_dissolves_without_changing_frame_size(self):
        from worker.render import blend_scene_transition
        previous = Image.new("RGB", (32, 24), (0, 0, 0))
        current = Image.new("RGB", (32, 24), (255, 255, 255))
        first = blend_scene_transition(previous, current, 0, 3)
        middle = blend_scene_transition(previous, current, 1, 3)
        final = blend_scene_transition(previous, current, 2, 3)
        self.assertEqual(first.size, (32, 24))
        self.assertEqual(first.getpixel((0, 0)), (85, 85, 85))
        self.assertEqual(middle.getpixel((0, 0)), (170, 170, 170))
        self.assertEqual(final.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(blend_scene_transition(previous, current, 3, 3).getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(blend_scene_transition(None, current, 0, 3).getpixel((0, 0)), (255, 255, 255))

    def test_draw_person_accepts_narrative_expression_styles(self):
        from worker.render import draw_person
        from PIL import Image, ImageDraw
        for expression in ("neutral", "concerned", "surprised", "weary", "resolved"):
            image = Image.new("RGB", (240, 300), (220, 211, 190))
            draw_person(ImageDraw.Draw(image), 120, 250, .55, (52,70,90), 0.7,
                        role="Narrator", action="observe", expression=expression)
            self.assertEqual(image.size, (240, 300))

    def test_walk_cycle_alternates_foot_lift(self):
        from worker.render import draw_person
        from PIL import Image, ImageDraw, ImageChops
        grounded = Image.new("RGB", (240, 300), (220, 211, 190))
        stepping = Image.new("RGB", (240, 300), (220, 211, 190))
        draw_person(ImageDraw.Draw(grounded), 120, 120, .55, (52,70,90), 0.0,
                    role="Narrator", action="walk")
        draw_person(ImageDraw.Draw(stepping), 120, 120, .55, (52,70,90), math.pi/2,
                    role="Narrator", action="walk")
        # Lower-leg and foot region must change as the alternating step lifts.
        diff = ImageChops.difference(grounded.crop((65, 215, 190, 295)),
                                     stepping.crop((65, 215, 190, 295)))
        self.assertIsNotNone(diff.getbbox())

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

    def test_story_props_have_smooth_frame_to_frame_motion(self):
        for kind in ("compass", "lantern", "watch", "gear", "map", "letter", "key", "ledger", "satchel", "paper", "telescope", "scale"):
            first = Image.new("RGB", (640, 480), (220, 211, 190))
            later = Image.new("RGB", (640, 480), (220, 211, 190))
            draw_primary_story_prop(ImageDraw.Draw(first), 640, 480, kind, 0.0)
            draw_primary_story_prop(ImageDraw.Draw(later), 640, 480, kind, 1.2)
            self.assertNotEqual(list(first.getdata()), list(later.getdata()), kind)

    def test_atmospheric_particles_move_between_frames_and_remain_deterministic(self):
        scene = {"visual": "A storm of rain over the harbour", "scene_index": 3}
        first = atmosphere_particles(scene, 0, 48, 1280, 720)
        later = atmosphere_particles(scene, 24, 48, 1280, 720)
        repeated = atmosphere_particles(scene, 0, 48, 1280, 720)
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, later)
        self.assertEqual(len(first), 58)
        self.assertTrue(all(kind == "rain" for kind, _, _ in first))

    def test_ambience_is_scene_aware_and_fades_at_both_ends(self):
        import tempfile
        import wave
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ambience.wav"
            synthesize_ambience({"visual": "rain over a city street", "scene_index": 8}, path, .5)
            with wave.open(str(path), "rb") as audio:
                self.assertEqual(audio.getframerate(), 24000)
                self.assertEqual(audio.getnframes(), 12000)
                frames = audio.readframes(audio.getnframes())
            import array
            samples = array.array("h")
            samples.frombytes(frames)
            self.assertLess(abs(samples[0]), 20)
            self.assertLess(abs(samples[-1]), 20)
            self.assertGreater(max(samples), 0)
            self.assertLess(min(samples), 0)

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
        with Image.open(output_dir / "thumbnail.jpg") as thumbnail:
            self.assertEqual(thumbnail.size, (1280, 720))
            self.assertEqual(thumbnail.format, "JPEG")
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
