import unittest
from mystery.timeline import Timeline, Event


class TestTimeline(unittest.TestCase):
    def setUp(self):
        self.t = Timeline()
        self.t.add(Event(time=100, actor="Alice", location="Office", action="enters"))
        self.t.add(Event(time=50, actor="Bob", location="Library", action="enters"))
        self.t.add(Event(time=75, actor="Alice", location="Office", action="leaves"))
        self.t.add(Event(time=10, actor="Carl", location="Lab", action="enters", visibility="hidden"))

    def test_chronological_sorting(self):
        events = self.t.sorted_events(include_hidden=True)
        times = [e.time for e in events]
        self.assertEqual(times, sorted(times))

    def test_hidden_excluded_by_default(self):
        events = self.t.sorted_events()
        self.assertTrue(all(e.visibility == "visible" for e in events))
        self.assertEqual(len(events), 3)

    def test_query_by_actor(self):
        events = self.t.by_actor("Alice")
        self.assertEqual(len(events), 2)
        self.assertTrue(all(e.actor == "Alice" for e in events))

    def test_query_by_location(self):
        events = self.t.by_location("Office")
        self.assertEqual(len(events), 2)

    def test_time_range(self):
        events = self.t.in_range(40, 80)
        times = sorted(e.time for e in events)
        self.assertEqual(times, [50, 75])


if __name__ == "__main__":
    unittest.main()
