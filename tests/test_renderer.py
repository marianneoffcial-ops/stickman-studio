import json
import subprocess
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from app.story import make_project
from worker.render import render_project, dimensions, draw_frame, character_scale, synthesize_ambience, atmosphere_particles, draw_primary_story_prop


class RenderSmokeTests(unittest.TestCase):
    def test_mixed_transport_keywords_choose_one_consistent_visual_motif(self):
        from worker.render import scene_transport_kind
        self.assertEqual(scene_transport_kind("A ship crosses the sea beside a railway train"), "sea")
        self.assertEqual(scene_transport_kind("A locomotive travels through a mountain pass"), "rail")
        self.assertEqual(scene_transport_kind("An aircraft flies over the coast"), "sea")
        self.assertEqual(scene_transport_kind("A quiet archive interior"), "none")

    def test_background_setting_is_dominant_and_does_not_mix_locations(self):
        from worker.render import scene_background_mode
        self.assertEqual(scene_background_mode("A ship carries a map through the sea", 0), 2)
        self.assertEqual(scene_background_mode("A manuscript is studied in an archive", 0), 3)
        self.assertEqual(scene_background_mode("A letter is opened on a desk", 0), 3)
        self.assertEqual(scene_background_mode("An old map shows a route", 0), 5)
        self.assertEqual(scene_background_mode("A caravan crosses the desert", 0), 4)
        self.assertEqual(scene_background_mode("A market street in an old city", 0), 1)
        self.assertEqual(scene_background_mode("A palace beside a mountain", 0), 0)
        self.assertEqual(scene_background_mode("An unclassified quiet scene", 5), 5)
        self.assertEqual(scene_background_mode("A 17th-century London lane with distant firelight and smoke", 0), 6)
        self.assertEqual(scene_background_mode("A bakery beside a timbered street in 1666", 0), 6)

    def test_fire_story_props_have_dedicated_illustrations(self):
        from worker.render import story_prop_kind
        self.assertEqual(story_prop_kind("a baker's wooden oven with a loaf of bread"), "oven")
        self.assertEqual(story_prop_kind("a simple leather fire bucket"), "bucket")
        self.assertEqual(story_prop_kind("a wooden water bucket"), "bucket")

    def test_london_fire_scene_uses_city_background_and_visible_fire_motifs(self):
        from worker.render import scene_background_mode, draw_story_details
        scene = {
            "visual": "A narrow 17th-century London lane at night with distant orange firelight "
                      "and smoke above timber rooftops; a baker's wooden oven is visible."
        }
        self.assertEqual(scene_background_mode(scene["visual"], 0), 6)
        image = Image.new("RGB", (640, 360), (220, 211, 190))
        draw_story_details(image, ImageDraw.Draw(image), 0, 0.7, scene)
        pixels = list(image.getdata())
        self.assertGreater(sum(pixel == (166, 92, 63) for pixel in pixels), 20)
        self.assertGreater(sum(pixel == (158, 157, 145) for pixel in pixels), 20)

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
        # The prompt-faithful renderer deliberately enlarges the recurring hero by 16%.
        self.assertAlmostEqual(landscape, 1.74)
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
        draw_person(ImageDraw.Draw(stepping), 120, 120, .55, (52,70,90), 1.57079632679,
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

    def test_scene_semantics_exclude_style_boilerplate_and_use_word_boundaries(self):
        from worker.render import scene_description, contains_any
        scene = {
            "title": "A quiet boat crossing",
            "visual": "A small boat crosses a calm sea at dawn.",
            "visual_prompt": "Background and story action: A small boat crosses a calm sea at dawn. "
                             "Shot composition: wide view. Restrained cinematic style, no photorealism."
        }
        meaning = scene_description(scene)
        self.assertNotIn("restrained", meaning)
        self.assertTrue(contains_any(meaning, ("boat", "sea")))
        self.assertFalse(contains_any(meaning, ("train", "railway", "locomotive")))

    def test_boat_scene_uses_sea_atmosphere_not_false_train_steam(self):
        from worker.render import atmosphere_particles, ambience_profile
        scene = {
            "title": "A quiet boat crossing",
            "visual": "A small boat crosses a calm sea at dawn.",
            "visual_prompt": "A restrained hand-inked illustrated scene."
        }
        particles = atmosphere_particles(scene, 0, 48, 1280, 720)
        self.assertTrue(all(kind == "dust" for kind, _, _ in particles))
        self.assertEqual(ambience_profile(scene), (430, 54, .72))

    def test_story_prop_classifier_covers_distinct_objects(self):
        from worker.render import story_prop_kind
        self.assertEqual(story_prop_kind("a folded nautical chart"), "map")
        self.assertEqual(story_prop_kind("a brass compass"), "compass")
        self.assertEqual(story_prop_kind("a sealed paper letter"), "letter")
        self.assertEqual(story_prop_kind("a hanging lantern"), "lantern")
        self.assertEqual(story_prop_kind("a leather-bound journal"), "ledger")
        self.assertEqual(story_prop_kind("a weathered telescope"), "telescope")
        self.assertEqual(story_prop_kind("a leather fire bucket"), "bucket")
        self.assertEqual(story_prop_kind("a baker's wooden oven"), "oven")

    def test_story_props_have_smooth_frame_to_frame_motion(self):
        for kind in ("compass", "lantern", "watch", "gear", "map", "letter", "key", "ledger", "satchel", "paper", "telescope", "scale", "bucket", "oven"):
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
        progress = []
        output = render_project(project, output_dir, progress_callback=lambda done, total: progress.append((done, total)))
        self.assertEqual(progress, [(1, 1)])
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 2048)
        self.assertTrue((output_dir / "thumbnail.jpg").exists())
        # Successful renders retain only the deliverables, not bulky intermediates.
        self.assertFalse((output_dir / "scenes").exists())
        for temporary in ("clips.txt", "audio.txt", "silent.mp4", "voice.wav"):
            self.assertFalse((output_dir / temporary).exists(), temporary)
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


    def test_walk_cycle_adds_subtle_upper_body_bounce(self):
        from worker.render import draw_person
        low = Image.new("RGB", (240, 300), (220, 211, 190))
        high = Image.new("RGB", (240, 300), (220, 211, 190))
        draw_person(ImageDraw.Draw(low), 120, 250, .55, (52,70,90), 0.0,
                    role="Narrator", action="walk")
        draw_person(ImageDraw.Draw(high), 120, 250, .55, (52,70,90), 0.78539816339,
                    role="Narrator", action="walk")
        self.assertNotEqual(list(low.crop((65, 35, 175, 155)).getdata()),
                            list(high.crop((65, 35, 175, 155)).getdata()))


    def test_closeup_background_is_a_clean_object_stage_not_a_second_scene(self):
        from worker.render import draw_background, PALETTE
        image = Image.new("RGB", (640, 360), (0, 0, 0))
        draw_background(image, ImageDraw.Draw(image), 0, 0.0,
                        {"visual": "A letter on a desk in an archive"},
                        closeup=True)
        # The quiet upper field stays clear for the focal prop; the horizon is
        # replaced by a single tabletop edge rather than a second set of props.
        self.assertEqual(image.getpixel((320, 90)), PALETTE[0])
        self.assertNotEqual(image.getpixel((320, 300)), PALETTE[0])


    def test_story_package_has_causal_phases_continuity_and_scene_sound(self):
        project = make_project("The Lost Telegraph Cable", 20, "16:9",
            "A cable was laid across the ocean. Storms threatened the fragile line. Engineers repaired the connection. Messages finally crossed the Atlantic. The world was suddenly closer.",
            "A ship carries cable across the sea.\nEngineers inspect a damaged cable in a workshop.\nA storm moves over the ocean.\nWorkers repair the cable at a coastal station.\nA message arrives at the telegraph office.")
        scenes = project["scenes"]
        self.assertEqual([s["story_phase"] for s in scenes], ["hook", "setup", "escalation", "turning_point", "payoff"])
        self.assertTrue(all(s["continuity"] for s in scenes))
        self.assertTrue(all(s["sound_design"] for s in scenes))
        self.assertTrue(all("visible consequence" in s["visual_prompt"] for s in scenes))
        self.assertIn("cause-and-effect", project["animation_agent_instruction"])
        self.assertEqual(project["story_arc"]["shot_count"], 5)
        self.assertEqual(len(project["reference_manifest"]), 3)
        self.assertGreaterEqual(len(project["quality_checks"]), 5)

    def test_scene_timing_and_aspect_ratio_remain_locked(self):
        project = make_project("A short history", 10, "9:16",
            "The first event happened. The next event changed everything. The final result surprised everyone.",
            "A person discovers a letter.\nA person studies the letter.\nA person shares the message.")
        self.assertEqual([scene["duration"] for scene in project["scenes"]], [4, 4, 2])
        self.assertTrue(all("in 9:16" in scene["visual_prompt"] for scene in project["scenes"]))
        self.assertIn("16:9 YouTube thumbnail", project["thumbnail_prompt"])

    def test_cloudflare_background_generation_is_opt_in(self):
        import os
        from unittest.mock import patch
        from worker.render import cloudflare_ai_configured, generate_cloudflare_background
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(cloudflare_ai_configured())
            self.assertIsNone(generate_cloudflare_background(
                {"visual": "A quiet archive"}, {"aspect_ratio": "16:9"}, "unused.jpg"
            ))

    def test_cloudflare_background_prompt_requests_environment_plate_only(self):
        from worker.render import cloudflare_background_prompt
        prompt = cloudflare_background_prompt(
            {"visual": "A ship crosses a grey sea at dawn"}, "16:9"
        )
        self.assertIn("hand-inked 2D illustrated animation", prompt)
        self.assertIn("no people", prompt)
        self.assertIn("A ship crosses a grey sea at dawn", prompt)
        self.assertIn("16:9", prompt)

    def test_cloudflare_background_decodes_and_fits_image(self):
        import base64
        import os
        import tempfile
        from io import BytesIO
        from unittest.mock import patch, MagicMock
        from worker.render import generate_cloudflare_background
        buffer = BytesIO()
        Image.new("RGB", (32, 24), (120, 130, 140)).save(buffer, format="PNG")
        payload = json.dumps({"result": {"image": base64.b64encode(buffer.getvalue()).decode("ascii")}})
        response = MagicMock()
        response.__enter__.return_value.read.return_value = payload.encode("utf-8")
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
            "CLOUDFLARE_ACCOUNT_ID": "test-account",
            "CLOUDFLARE_API_TOKEN": "test-token",
        }), patch("worker.render.urllib.request.urlopen", return_value=response) as request:
            target = Path(folder) / "background.jpg"
            result = generate_cloudflare_background(
                {"visual": "A quiet archive"}, {"aspect_ratio": "16:9"}, target
            )
            self.assertEqual(result, str(target))
            self.assertTrue(target.is_file())
            with Image.open(target) as generated:
                self.assertEqual(generated.size, dimensions("16:9"))
            self.assertIn("@cf/black-forest-labs/flux-1-schnell", request.call_args.args[0].full_url)
            sent_payload = json.loads(request.call_args.args[0].data.decode("utf-8"))
            self.assertEqual(set(sent_payload), {"prompt", "steps"})
            self.assertGreater(len(sent_payload["prompt"]), 0)
            self.assertLessEqual(len(sent_payload["prompt"]), 2048)
            self.assertGreaterEqual(sent_payload["steps"], 1)
            self.assertLessEqual(sent_payload["steps"], 8)
            self.assertEqual(request.call_args.kwargs["timeout"], 90)

    def test_background_generation_summary_reports_real_per_scene_fallbacks(self):
        from worker.render import background_generation_summary
        summary = background_generation_summary([
            {"background_generation": {"status": "generated"}},
            {"background_generation": {"status": "fallback", "error": "rate limited"}},
            {"background_generation": {"status": "fallback", "error": "invalid image"}},
        ], configured=True)
        self.assertTrue(summary["configured"])
        self.assertEqual(summary["provider"], "Cloudflare Workers AI FLUX.1 schnell")
        self.assertEqual(summary["generated_scenes"], 1)
        self.assertEqual(summary["fallback_scenes"], 2)
        self.assertEqual(summary["total_scenes"], 3)
        self.assertEqual([item["status"] for item in summary["scenes"]],
                         ["generated", "fallback", "fallback"])
        self.assertEqual(summary["scenes"][1]["error"], "rate limited")

    def test_background_generation_summary_marks_unconfigured_fallback(self):
        from worker.render import background_generation_summary
        summary = background_generation_summary([
            {"background_generation": {"status": "fallback",
                                       "error": "Cloudflare credentials are not configured."}}
        ], configured=False)
        self.assertFalse(summary["configured"])
        self.assertEqual(summary["generated_scenes"], 0)
        self.assertEqual(summary["fallback_scenes"], 1)


if __name__ == "__main__":
    unittest.main()
