# --- Imports ---
import json
import tempfile
import unittest
from pathlib import Path
from src.game_state import GameState


# --- Discovery Tests ---
class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(__file__).resolve().parents[1]
        self.save = Path(self.temp.name) / 'save.json'
        self.now = 100000.0
        self.state = GameState(self.root, self.save, clock=lambda: self.now)

    def tearDown(self):
        self.temp.cleanup()

    def fund(self):
        self.state.resources = {name: self.state.capacity(name) for name in self.state.resources}

    def test_research_requirements_and_no_repeat(self):
        self.fund()
        self.assertFalse(self.state.research('cuneiform')[0])
        self.assertTrue(self.state.research('pottery')[0])
        self.assertFalse(self.state.research('pottery')[0])
        self.assertEqual(self.state.counters['research_completed'], 1)

    def test_research_increases_production(self):
        original = self.state.production_rates()['barley']
        self.fund()
        self.assertTrue(self.state.research('irrigation')[0])
        self.assertGreater(self.state.production_rates()['barley'], original)

    def test_expedition_completes_and_artifact_is_unique(self):
        self.fund()
        self.assertTrue(self.state.start_expedition('reed_marsh'))
        self.assertFalse(self.state.start_expedition('reed_marsh'))
        self.state.advance(45)
        self.assertIsNone(self.state.active_expedition)
        self.assertIn('marsh_seal', self.state.artifacts)
        self.assertEqual(self.state.counters['artifact_discovered'], 1)
        self.assertTrue(self.state.start_expedition('reed_marsh'))
        self.state.advance(45)
        self.assertEqual(self.state.counters['artifact_discovered'], 1)
        self.assertEqual(self.state.counters['expedition_completed'], 2)

    def test_expedition_requires_technology(self):
        self.fund()
        self.assertFalse(self.state.start_expedition('star_temple'))

    def test_save_reloads_pending_expedition_and_research(self):
        self.fund()
        self.assertTrue(self.state.research('irrigation')[0])
        self.assertTrue(self.state.start_expedition('river_delta'))
        self.state.advance(30)
        self.state.save()
        restored = GameState(self.root, self.save, clock=lambda: self.now)
        self.assertIn('irrigation', restored.researched)
        self.assertEqual(restored.active_expedition, 'river_delta')
        self.assertAlmostEqual(restored.expedition_remaining, 80)
        restored.advance(80)
        self.assertIn('river_tablet', restored.artifacts)

    def test_old_save_migration(self):
        self.state.save()
        data = json.loads(self.save.read_text())
        for key in ('researched', 'artifacts', 'active_expedition', 'expedition_remaining'):
            data.pop(key)
        self.save.write_text(json.dumps(data))
        restored = GameState(self.root, self.save, clock=lambda: self.now)
        self.assertEqual(restored.researched, [])
        self.assertEqual(restored.artifacts, [])
        self.assertIsNone(restored.active_expedition)

    def test_research_achievement_unlocks(self):
        self.fund()
        success, rewards = self.state.research('irrigation')
        self.assertTrue(success)
        self.assertIn('First Scholar', rewards)

    def test_data_integrity(self):
        ids = {item['id'] for item in self.state.research_data}
        artifacts = {item['id'] for item in self.state.artifact_data}
        for item in self.state.research_data:
            self.assertTrue(set(item['requires']) <= ids)
        for item in self.state.expedition_data:
            self.assertTrue(set(item['requires']) <= ids)
            self.assertIn(item['artifact'], artifacts)
        achievement_ids = [item['id'] for item in self.state.achievement_data]
        self.assertEqual(len(set(achievement_ids)), len(achievement_ids))


if __name__ == '__main__':
    unittest.main()
