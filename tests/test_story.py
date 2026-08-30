import unittest

from mystery.generator import generate_case
from tools import story


class TestStoryExport(unittest.TestCase):
    def test_story_contains_premise_and_cast(self):
        text = story.build_story(generate_case(21321))
        self.assertIn("Case File #21321", text)
        self.assertIn("The Case", text)
        for name in generate_case(21321).suspect_names():
            self.assertIn(name, text)
            self.assertIn("Alibi:", text)

    def test_story_lists_every_evidence_item(self):
        case = generate_case(777)
        text = story.build_story(case)
        for eid in sorted(case.evidence, key=int):
            self.assertIn(f"Evidence #{eid}", text)
            self.assertIn(case.evidence[eid].description, text)

    def test_story_has_visible_timeline_only(self):
        """The story shows only player-visible events - the hidden murder
        event itself must never leak into a printable brief."""
        case = generate_case(1)
        text = story.build_story(case)
        self.assertIn("The Timeline", text)
        self.assertNotIn("murders", text)

    def test_story_contains_solution_key(self):
        """The doc ends with a separated solution key derived from the
        hidden truth, mirroring what --solve-verbose prints."""
        case = generate_case(48291)
        text = story.build_story(case)
        self.assertIn("Solution key", text)
        self.assertIn(case.truth.killer, text)
        self.assertIn(case.truth.motive, text)
        self.assertIn(case.truth.weapon, text)

    def test_story_is_deterministic(self):
        a = story.build_story(generate_case(123))
        b = story.build_story(generate_case(123))
        self.assertEqual(a, b)

    def test_story_output_is_ascii(self):
        """Printable output must stay ASCII-only so it renders correctly
        even in a legacy Windows console."""
        text = story.build_story(generate_case(999))
        try:
            text.encode("ascii")
        except UnicodeEncodeError:
            self.fail("story output contains non-ASCII characters")


if __name__ == "__main__":
    unittest.main()