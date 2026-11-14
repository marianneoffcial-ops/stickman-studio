import unittest
from unittest.mock import patch

from app.research import research_topic


class ResearchTests(unittest.TestCase):
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
