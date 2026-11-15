import unittest
from unittest.mock import call, patch

from app.research import research_topic


def _search_page(title, pageid, url=None):
    return {
        "title": title,
        "pageid": pageid,
        "fullurl": url or "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
    }


def _search_response(*pages):
    return {"query": {"pages": list(pages)}}


def _article_response(text, title="Example Event"):
    return {"parse": {
        "title": title,
        "text": "<div class='mw-parser-output'><p>" + text + "</p></div>",
    }}


class ResearchTests(unittest.TestCase):

    def test_research_fetches_full_text_from_selected_primary_page(self):
        unrelated = _search_page("Early fires of London", 101)
        primary = _search_page("Great Fire of London", 202)
        search = _search_response(unrelated, primary)
        article = (
            "The Great Fire of London occurred from Sunday 2 September to Wednesday "
            "5 September 1666, gutting the medieval City of London inside the old "
            "Roman city wall. The fire started in a bakery in Pudding Lane shortly "
            "after midnight and spread rapidly through the crowded streets."
        )
        with patch("app.research._api", side_effect=[search, _article_response(article, "Great Fire of London")]) as api:
            result = research_topic("The Great Fire of London", 20)
        self.assertEqual(result["topic"], "Great Fire of London")
        self.assertIn("1666", result["narration_script"])
        self.assertIn("Pudding Lane", result["narration_script"])
        self.assertIn("crowded streets.", result["narration_script"])
        self.assertTrue(result["narration_script"].endswith((".", "!", "?")))
        self.assertNotIn("2. September", result["narration_script"])
        self.assertGreaterEqual(result["script_word_count"], result["target_word_count"])
        self.assertEqual(" ".join(result["narration_beats"]), result["narration_script"])
        self.assertNotIn("Boudica", result["narration_script"])
        self.assertEqual(api.call_args_list[1].args[0]["action"], "parse")
        self.assertEqual(api.call_args_list[1].args[0]["pageid"], 202)
        self.assertEqual(result["sources"][0]["title"], "Great Fire of London")

    def test_great_fire_storyboard_uses_london_fire_specific_scenes(self):
        search = _search_response(_search_page("Great Fire of London", 303))
        article = (
            "The Great Fire of London occurred from Sunday 2 September to Wednesday "
            "5 September 1666, gutting the medieval City of London inside the old "
            "Roman city wall. The fire started in a bakery in Pudding Lane shortly "
            "after midnight and spread rapidly through the crowded streets."
        )
        with patch("app.research._api", side_effect=[search, _article_response(article, "Great Fire of London")]):
            result = research_topic("The Great Fire of London", 15)
        scenes = result["storyboard"].lower().splitlines()
        self.assertEqual(len(scenes), 4)
        self.assertTrue(all("london" in scene for scene in scenes))
        self.assertTrue(all(any(word in scene for word in ("firelight", "smoke", "fire bucket", "firebreak")) for scene in scenes))
        self.assertNotIn("archive with shelves", result["storyboard"].lower())

    def test_narration_keeps_day_and_month_together_without_fake_full_stops(self):
        search = _search_response(_search_page("Great Fire of London", 304))
        article = (
            "The Great Fire of London occurred from Sunday 2 September to Wednesday "
            "5 September 1666, gutting the medieval City of London inside the old "
            "Roman city wall. The fire started in a bakery in Pudding Lane shortly "
            "after midnight and spread rapidly through the crowded streets."
        )
        with patch("app.research._api", side_effect=[search, _article_response(article, "Great Fire of London")]):
            result = research_topic("The Great Fire of London", 15)
        self.assertIn("Sunday 2 September", result["narration_beats"][0])
        self.assertNotIn("2.", result["narration_beats"][0])
        self.assertTrue(result["narration_beats"][-1].endswith("."))

    def test_article_parser_ignores_navigation_figures_and_reference_numbers(self):
        from app.research import _extract_article_text
        markup = (
            "<div class='hatnote'><p>Wrong topic.</p></div>"
            "<figure><figcaption>Image caption only.</figcaption></figure>"
            "<p>The primary event happened in 1666.<sup>[1]</sup> It changed London.</p>"
            "<table><tr><td>Unrelated table text.</td></tr></table>"
            "<h2>Aftermath</h2><p>The city was rebuilt.</p>"
        )
        text = _extract_article_text(markup)
        self.assertIn("primary event happened in 1666", text)
        self.assertIn("Aftermath", text)
        self.assertNotIn("Wrong topic", text)
        self.assertNotIn("Image caption", text)
        self.assertNotIn("Unrelated table", text)
        self.assertNotIn("[1]", text)

    def test_exact_event_article_outranks_a_longer_article_title_about_its_monument(self):
        search = _search_response(
            _search_page("Monument to the Great Fire of London", 1),
            _search_page("Great Fire of London", 2),
        )
        article = " ".join(
            [f"Fire detail {i} describes the documented Great Fire of London in 1666." for i in range(1, 80)]
        )
        with patch("app.research._api", side_effect=[search, _article_response(article, "Great Fire of London")]):
            result = research_topic("The Great Fire of London", 15)
        self.assertEqual(result["topic"], "Great Fire of London")
        self.assertEqual(result["sources"][0]["title"], "Great Fire of London")

    def test_research_rejects_a_related_but_non_primary_monument_article(self):
        search = _search_response(_search_page("Monument to the Great Fire of London", 1))
        with patch("app.research._api", return_value=search):
            with self.assertRaisesRegex(ValueError, "clearly matching article"):
                research_topic("The Great Fire of London", 15)

    def test_research_selects_the_exact_subject_article_over_a_misleading_top_result(self):
        search = _search_response(
            _search_page("Great Plague of London", 1),
            _search_page("Great Fire of London", 2),
        )
        article = " ".join(
            [f"Fire detail {i} describes a documented event in London." for i in range(1, 80)]
        )
        with patch("app.research._api", side_effect=[search, _article_response(article, "Great Fire of London")]):
            result = research_topic("The Great Fire of London", 15)
        self.assertEqual(result["topic"], "Great Fire of London")
        self.assertEqual(result["sources"][0]["title"], "Great Fire of London")
        self.assertIn("Fire detail", result["narration_script"])

    def test_research_rejects_results_that_do_not_match_the_requested_subject(self):
        search = _search_response(_search_page("Great Plague of London", 1))
        with patch("app.research._api", return_value=search):
            with self.assertRaisesRegex(ValueError, "clearly matching article"):
                research_topic("The Great Fire of London", 15)

    def test_ten_minute_research_produces_all_150_beats(self):
        text = " ".join([
            f"Historical fact {i} describes a documented event and its wider context."
            for i in range(1, 500)
        ])
        search = _search_response(_search_page("Long Event", 99))
        with patch("app.research._api", side_effect=[search, _article_response(text, "Long Event")]) as api:
            result = research_topic("Long Event", 600)
        self.assertEqual(result["scene_count"], 150)
        self.assertEqual(len(result["narration_beats"]), 150)
        self.assertTrue(all(beat.strip() for beat in result["narration_beats"]))
        self.assertEqual(len(result["storyboard"].splitlines()), 150)
        self.assertGreaterEqual(result["script_word_count"], result["target_word_count"])
        self.assertEqual(api.call_args_list[0].args[0]["gsrlimit"], 10)
        self.assertEqual(api.call_args_list[1].args[0]["action"], "parse")

    def test_incomplete_research_is_rejected_instead_of_creating_silent_scenes(self):
        text = " ".join([
            f"Fact number {i} describes a real historical detail."
            for i in range(1, 80)
        ])
        search = _search_response(_search_page("Short Event", 11))
        with patch("app.research._api", side_effect=[search, _article_response(text, "Short Event")]):
            with self.assertRaisesRegex(ValueError, "complete 600-second narration"):
                research_topic("Short Event", 600)

    def test_research_returns_timed_beats_and_citations(self):
        text = " ".join([
            f"Fact number {i} describes a real historical detail."
            for i in range(1, 80)
        ])
        search = _search_response(_search_page("Example Event", 12))
        with patch("app.research._api", side_effect=[search, _article_response(text, "Example Event")]):
            result = research_topic("Example Event", 60)
        self.assertEqual(result["scene_count"], 15)
        self.assertEqual(len(result["narration_beats"]), 15)
        self.assertEqual(len(result["storyboard"].splitlines()), 15)
        self.assertEqual(result["sources"][0]["url"], "https://en.wikipedia.org/wiki/Example_Event")
        self.assertGreaterEqual(result["script_word_count"], 120)


if __name__ == "__main__":
    unittest.main()
