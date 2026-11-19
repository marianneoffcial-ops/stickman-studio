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

    def test_repeated_storyboard_anchors_still_create_unique_scene_prompts(self):
        beats = [
            f"During scene {i+1}, the team carefully studies the evidence."
            for i in range(15)
        ]
        anchors = [
            "A narrow historic lane with timber rooftops.",
            "A broad river beside the old city.",
            "A quiet bakery room with a brick oven.",
            "A timber-framed street seen from above.",
            "A rebuilding site with stacked bricks.",
            "A calm stone street at dawn.",
        ]
        project = make_project(
            "The Great Fire of London", 60, "9:16", " ".join(beats),
            "\\n".join(anchors), beats
        )
        prompts = project["animation_prompts"]
        self.assertEqual(len(prompts), 15)
        self.assertEqual(len(set(prompts)), 15)
        self.assertTrue(all(
            f"Scene-specific beat {i+1} of 15" in prompt and beats[i] in prompt
            for i, prompt in enumerate(prompts)
        ))
        self.assertEqual(
            [scene["visual"] for scene in project["scenes"]],
            [anchors[i % len(anchors)] for i in range(15)]
        )
        self.assertGreaterEqual(
            len({scene["camera"] for scene in project["scenes"]}), 4
        )

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


    def test_researched_narration_beats_are_preserved_in_rendered_scenes(self):
        beats = ["The first nine words make one clear beat.", "The next nine words complete the second beat."]
        script = " ".join(beats)
        project = make_project("A test story", 8, "16:9", script,
                               "First visual anchor.\nSecond visual anchor.", beats)
        self.assertEqual([scene["narration"] for scene in project["scenes"]], beats)
        self.assertEqual(project["narration_beats"], beats)

    def test_great_fire_thumbnail_uses_a_story_specific_headline(self):
        project = make_project("The Great Fire of London", 15, "16:9",
                               "A documented event in 1666.", "A quiet English city street.")
        self.assertEqual(project["thumbnail_headline"], "THE GREAT FIRE")
        self.assertIn("'THE GREAT FIRE'", project["thumbnail_prompt"])

    def test_story_beats_select_distinct_reveal_and_ponder_gestures(self):
        from app.story import _scene_action
        self.assertEqual(_scene_action("The team discovers an unexpected clue.", 0), "reveal")
        self.assertEqual(_scene_action("The council considers a careful plan.", 1), "ponder")
        self.assertEqual(_scene_action("A quiet ordinary morning.", 0), "observe")
        self.assertEqual(_scene_action("The river passed beneath the old bridge.", 3), "observe")
        self.assertEqual(_scene_action("The village opened its doors at sunrise.", 5), "observe")

    def test_narrative_beats_select_distinct_facial_expressions(self):
        from app.story import _scene_expression
        self.assertEqual(_scene_expression("The discovery was astonishing.", "", 0), "surprised")
        self.assertEqual(_scene_expression("Officials feared the worst.", "", 0), "concerned")
        self.assertEqual(_scene_expression("After years of waiting, they were exhausted.", "", 0), "weary")
        self.assertEqual(_scene_expression("The team finally resolved to rebuild.", "", 0), "resolved")
        self.assertEqual(_scene_expression("A quiet ordinary morning.", "", 0), "neutral")
        self.assertEqual(_scene_expression("The village opened its doors at sunrise.", "", 1), "neutral")
        self.assertEqual(_scene_expression("The river passed beneath the old bridge.", "", 3), "neutral")

    def test_scene_expression_is_attached_to_every_rendered_beat(self):
        project = make_project("A test story", 8, "16:9",
            "The discovery was astonishing. Officials feared the worst.",
            "A sudden discovery. Officials study the evidence.")
        self.assertEqual(len(project["scenes"]), 2)
        self.assertTrue(all(scene["expression"] in {"neutral","concerned","surprised","weary","resolved"} for scene in project["scenes"]))

    def test_scene_camera_matches_story_objects_and_locations(self):
        from app.story import _scene_camera
        self.assertIn("overhead", _scene_camera("A folded map shows the expedition route.", 0))
        self.assertIn("close-up", _scene_camera("A sealed letter is opened on a desk.", 1))
        self.assertIn("low-angle", _scene_camera("The new bridge rises above the river.", 2))
        self.assertIn("tracking", _scene_camera("The crew travels across the sea.", 3))

    def test_story_props_trigger_object_closeups(self):
        from app.story import _scene_camera
        for prop in ("a brass compass", "a signal lantern", "a weathered telescope", "a folded newspaper"):
            self.assertIn("close-up", _scene_camera(prop, 1))

    def test_storyboard_beats_produce_multiple_camera_angles(self):
        project = make_project(
            "A test story", 32, "16:9", " ".join(["A fact."] * 80),
            "\n".join([
                "A folded map shows the route.",
                "A sealed letter rests on a desk.",
                "A bridge rises above the river.",
                "The crew travels across the sea.",
                "A quiet archive holds old books.",
                "A wide city street at dawn."
            ])
        )
        cameras = [scene["camera"] for scene in project["scenes"]]
        self.assertGreaterEqual(len(set(cameras)), 4)

    def test_same_topic_gets_distinct_researched_visual_locations_and_props(self):
        from app.research import _generic_scene
        scenes = [_generic_scene("The ship crossed the sea toward a distant harbour.", i) for i in range(6)]
        self.assertEqual(len(set(scenes)), 6)
        self.assertTrue(all("primary story prop on the right third" in scene for scene in scenes))
        self.assertTrue(any("nautical chart" in scene for scene in scenes))
        self.assertTrue(any("brass compass" in scene for scene in scenes))
        self.assertTrue(any("ship's logbook" in scene for scene in scenes))

    def test_research_language_changes_visual_story_stage(self):
        from app.research import _generic_scene
        discovery = _generic_scene("Investigators discovered the empty ship.", 0)
        decision = _generic_scene("Officials decided on a careful plan.", 1)
        journey = _generic_scene("The expedition travelled across the ice.", 2)
        aftermath = _generic_scene("The rescue team returned and began rebuilding.", 3)
        self.assertIn("discovery in the story", discovery)
        self.assertIn("decision in the story", decision)
        self.assertIn("journey in the story", journey)
        self.assertIn("aftermath in the story", aftermath)

    def test_storyboard_visuals_keep_safety_constraints(self):
        from app.research import _generic_scene
        scene = _generic_scene("A group studied a map before the journey.", 0)
        self.assertIn("No named people", scene)
        self.assertIn("no violence", scene)
        self.assertIn("no weapons", scene)

    def test_idea_pool_has_enough_fresh_topics(self):
        self.assertGreaterEqual(len(IDEAS), 20)
        self.assertEqual(len({x[0] for x in IDEAS}), len(IDEAS))


if __name__ == "__main__":
    unittest.main()
