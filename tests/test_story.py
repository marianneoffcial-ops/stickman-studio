import unittest

from app.story import HOUSE_STYLE, IDEAS, make_project


class StoryTimingTests(unittest.TestCase):
    def test_sixty_seconds_is_fifteen_four_second_scenes(self):
        project = make_project("A test story", 60, "9:16", " ".join(["A fact."] * 150), "\n".join([f"Scene {i}" for i in range(15)]))
        self.assertEqual(project["scene_count"], 15)
        self.assertEqual([s["duration"] for s in project["scenes"]], [4] * 15)

    def test_ninety_seconds_has_two_second_final_scene(self):
        project = make_project("A test story", 90, "16:9", " ".join(["A fact."] * 230), "\n".join([f"Scene {i}" for i in range(23)]))
        self.assertEqual(project["scene_count"], 23)
        self.assertEqual(project["scenes"][-1]["duration"], 2)
        self.assertEqual(sum(s["duration"] for s in project["scenes"]), 90)

    def test_ten_minutes_is_150_scenes(self):
        project = make_project("A test story", 600, "16:9", " ".join(["A fact."] * 1500), "\n".join([f"Scene {i}" for i in range(150)]))
        self.assertEqual(project["scene_count"], 150)
        self.assertEqual(sum(s["duration"] for s in project["scenes"]), 600)

    def test_character_is_consistent_across_scenes(self):
        project = make_project("The Disappearance of the Mary Celeste", 60, "16:9", " ".join(["A fact."] * 150), "\n".join([f"Scene {i}" for i in range(15)]))
        self.assertEqual(len({tuple(s["characters"]) for s in project["scenes"]}), 1)

    def test_every_animation_prompt_has_required_style_audio_and_closing_constraints(self):
        project = make_project("A test story", 60, "1:1", " ".join(["A fact."] * 150), "\n".join([f"Scene {i}" for i in range(15)]))
        self.assertTrue(all(HOUSE_STYLE in p for p in project["animation_prompts"]))
        self.assertTrue(all("Audio is diegetic ambient sound only — no voice, no narration, no dialogue, no music. Only the sounds present" in p for p in project["animation_prompts"]))
        self.assertTrue(all(p.endswith("no unintended characters, no on-screen text, no subtitles and no watermark.") for p in project["animation_prompts"]))
        self.assertTrue(all(project["locked_character_block"] in p for p in project["animation_prompts"]))

    def test_character_sheet_thumbnail_and_agent_instruction_are_present(self):
        project = make_project("A test story", 30, "9:16", "A concise researched story script.", "\n".join([f"Scene {i}" for i in range(8)]))
        self.assertIn("front, three-quarter, side and back", project["character_sheet_prompt"])
        self.assertIn("CONCERNED", project["character_sheet_prompt"])
        self.assertIn("TURNING AWAY", project["character_sheet_prompt"])
        self.assertIn("16:9", project["thumbnail_prompt"])
        self.assertLessEqual(len(project["thumbnail_headline"].split()), 4)
        self.assertIn("exactly 2 seconds", project["animation_agent_instruction"])

    def test_idea_pool_has_enough_fresh_topics(self):
        self.assertGreaterEqual(len(IDEAS), 20)
        self.assertEqual(len({x[0] for x in IDEAS}), len(IDEAS))


if __name__ == "__main__":
    unittest.main()
