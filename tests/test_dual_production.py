import unittest
from unittest.mock import patch

from app.main import DualProductionRequest, create_dual_production


def research_result(topic, duration):
    return {
        "topic": topic,
        "narration_script": "A researched fact. " * (34 if duration == 60 else 340),
        "storyboard": "\\n".join(["A clear illustrated scene."] * (15 if duration == 60 else 150)),
        "sources": [{"title": "Example source", "url": "https://example.org"}],
    }


class DualProductionTests(unittest.TestCase):
    @patch("app.main.queue_project")
    @patch("app.main.research_topic", side_effect=research_result)
    def test_one_topic_queues_both_required_formats(self, research, queue):
        queue.side_effect = lambda project: {
            "job_id": "job-" + str(project["duration_seconds"]),
            "status": "queued",
        }

        result = create_dual_production(DualProductionRequest(topic="A documented event"))

        self.assertEqual(research.call_count, 2)
        self.assertEqual(research.call_args_list[0].args, ("A documented event", 60))
        self.assertEqual(research.call_args_list[1].args, ("A documented event", 600))
        self.assertEqual(result["short"]["duration_seconds"], 60)
        self.assertEqual(result["short"]["aspect_ratio"], "9:16")
        self.assertEqual(result["short"]["scene_count"], 15)
        self.assertEqual(result["long"]["duration_seconds"], 600)
        self.assertEqual(result["long"]["aspect_ratio"], "16:9")
        self.assertEqual(result["long"]["scene_count"], 150)
        self.assertEqual(queue.call_count, 2)


if __name__ == "__main__":
    unittest.main()
