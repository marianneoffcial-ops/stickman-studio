import unittest

from app.story import HOUSE_STYLE, make_project


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

    def test_each_scene_carries_the_house_style_and_action(self):
        project = make_project("A test story", 60, "1:1", " ".join(["A fact."] * 150), "\n".join([f"Scene {i}" for i in range(15)]))
        self.assertTrue(all(HOUSE_STYLE in s["visual_prompt"] for s in project["scenes"]))
        self.assertTrue(all(s["action"] for s in project["scenes"]))
        self.assertIn("character_sheet_prompt", project)
        self.assertIn("locked_character_block", project)
        self.assertEqual(len(project["animation_prompts"]), 15)
        self.assertIn("thumbnail_prompt", project)


if __name__ == "__main__":
    unittest.main()
