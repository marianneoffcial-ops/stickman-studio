import unittest
from unittest.mock import patch

from app.research import research_topic


class ResearchTests(unittest.TestCase):


    def test_exact_event_article_outranks_a_longer_article_title_about_its_monument(self):
        monument = " ".join([f"Monument detail {i} describes the Great Fire of London." for i in range(1, 80)])
        fire = " ".join([f"Fire detail {i} describes the Great Fire of London." for i in range(1, 80)])
        response = {"query": {"pages": [
            {"title": "Monument to the Great Fire of London", "extract": monument,
             "fullurl": "https://en.wikipedia.org/wiki/Monument_to_the_Great_Fire_of_London"},
            {"title": "Great Fire of London", "extract": fire,
             "fullurl": "https://en.wikipedia.org/wiki/Great_Fire_of_London"},
        ]}}
        with patch("app.research._api", return_value=response):
            result = research_topic("The Great Fire of London", 15)
        self.assertEqual(result["topic"], "Great Fire of London")
        self.assertEqual(result["sources"][0]["title"], "Great Fire of London")

    def test_research_rejects_a_related_but_non_primary_monument_article(self):
        text = " ".join([f"Monument detail {i} describes the Great Fire of London." for i in range(1, 80)])
        response = {"query": {"pages": [
            {"title": "Monument to the Great Fire of London", "extract": text,
             "fullurl": "https://en.wikipedia.org/wiki/Monument_to_the_Great_Fire_of_London"},
        ]}}
        with patch("app.research._api", return_value=response):
            with self.assertRaisesRegex(ValueError, "clearly matching article"):
                research_topic("The Great Fire of London", 15)

    def test_research_selects_the_exact_subject_article_over_a_misleading_top_result(self):
        plague = " ".join([f"Plague detail {i} describes a documented event in London." for i in range(1, 80)])
        fire = " ".join([f"Fire detail {i} describes a documented event in London." for i in range(1, 80)])
        response = {"query": {"pages": [
            {"title": "Great Plague of London", "extract": plague,
             "fullurl": "https://en.wikipedia.org/wiki/Great_Plague_of_London"},
            {"title": "Great Fire of London", "extract": fire,
             "fullurl": "https://en.wikipedia.org/wiki/Great_Fire_of_London"},
        ]}}
        with patch("app.research._api", return_value=response):
            result = research_topic("The Great Fire of London", 15)
        self.assertEqual(result["topic"], "Great Fire of London")
        self.assertEqual(result["sources"][0]["title"], "Great Fire of London")
        self.assertIn("Fire detail", result["narration_script"])

    def test_research_rejects_results_that_do_not_match_the_requested_subject(self):
        text = " ".join([f"Plague detail {i} describes a documented event in London." for i in range(1, 80)])
        response = {"query": {"pages": [
            {"title": "Great Plague of London", "extract": text,
             "fullurl": "https://en.wikipedia.org/wiki/Great_Plague_of_London"},
        ]}}
        with patch("app.research._api", return_value=response):
            with self.assertRaisesRegex(ValueError, "clearly matching article"):
                research_topic("The Great Fire of London", 15)

    def test_ten_minute_research_produces_all_150_beats(self):
        text = " ".join([f"Historical fact {i} describes a documented event and its wider context." for i in range(1, 500)])
        response = {"query": {"pages": [
            {"title": "Long Event", "extract": text, "fullurl": "https://en.wikipedia.org/wiki/Long_Event"}
        ]}}
        with patch("app.research._api", return_value=response) as api:
            result = research_topic("Long Event", 600)
        self.assertEqual(result["scene_count"], 150)
        self.assertEqual(len(result["narration_beats"]), 150)
        self.assertTrue(all(beat.strip() for beat in result["narration_beats"]))
        self.assertEqual(len(result["storyboard"].splitlines()), 150)
        self.assertGreaterEqual(result["script_word_count"], result["target_word_count"])
        self.assertEqual(api.call_args.args[0]["gsrlimit"], 10)

    def test_incomplete_research_is_rejected_instead_of_creating_silent_scenes(self):
        text = " ".join([f"Fact number {i} describes a real historical detail." for i in range(1, 80)])
        response = {"query": {"pages": [
            {"title": "Short Event", "extract": text, "fullurl": "https://en.wikipedia.org/wiki/Short_Event"}
        ]}}
        with patch("app.research._api", return_value=response):
            with self.assertRaisesRegex(ValueError, "complete 600-second narration"):
                research_topic("Short Event", 600)

    def test_research_returns_timed_beats_and_citations(self):
        text = " ".join([f"Fact number {i} describes a real historical detail." for i in range(1, 80)])
        response = {"query": {"pages": [
            {"title": "Example Event", "extract": text, "fullurl": "https://en.wikipedia.org/wiki/Example_Event"}
        ]}}
        with patch("app.research._api", return_value=response):
            result = research_topic("Example Event", 60)
        self.assertEqual(result["scene_count"], 15)
        self.assertEqual(len(result["narration_beats"]), 15)
        self.assertEqual(len(result["storyboard"].splitlines()), 15)
        self.assertEqual(result["sources"][0]["url"], "https://en.wikipedia.org/wiki/Example_Event")
        self.assertGreaterEqual(result["script_word_count"], 120)


if __name__ == "__main__":
    unittest.main()
