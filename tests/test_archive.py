# --- Imports ---
import json
import tempfile
import unittest
from pathlib import Path
from src.game_state import GameState


# --- Archive Tests ---
class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(__file__).resolve().parents[1]
        self.path = Path(self.folder.name) / 'save.json'
        self.game = GameState(self.root, self.path, clock=lambda: 1000)

    def tearDown(self):
        self.folder.cleanup()

    def test_unique_tiers_and_valid_collection_requirements(self):
        ids = [item['id'] for item in self.game.achievement_data]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 60)
        for collection in self.game.collection_data:
            self.assertTrue(set(collection['required']).issubset(ids))

    def test_progress_and_points(self):
        self.game.counters['tap'] = 100
        new = self.game.check_achievements()
        self.assertIn('Hands of the River Copper', new)
        achievement = next(x for x in self.game.achievement_data if x['id'] == 'tap_copper')
        self.assertEqual(self.game.achievement_progress(achievement), (100, 100))
        self.assertGreater(self.game.legacy_points(), 0)
        self.assertEqual(self.game.check_achievements(), [])

    def test_collections_complete_once_and_grant_relic(self):
        self.game.counters['tap'] = 1
        self.game.counters['build'] = 1
        self.game.counters['build_house'] = 1
        unlocked = self.game.check_achievements()
        self.assertIn('First Foundations collection', unlocked)
        self.assertIn('founder_banner', self.game.cosmetics)
        self.assertEqual(self.game.check_achievements(), [])

    def test_save_load_preserves_relics_and_sets(self):
        self.game.counters.update({'tap':1,'build':1,'build_house':1})
        self.game.check_achievements()
        points = self.game.legacy_points()
        self.game.save()
        restored = GameState(self.root, self.path, clock=lambda: 1000)
        self.assertEqual(restored.legacy_points(), points)
        self.assertEqual(restored.completed_collections, self.game.completed_collections)
        self.assertEqual(restored.cosmetics, self.game.cosmetics)

    def test_previous_save_has_no_archive_fields(self):
        self.game.tap()
        self.game.save()
        raw = json.loads(self.path.read_text())
        raw.pop('cosmetics')
        raw.pop('completed_collections')
        self.path.write_text(json.dumps(raw))
        restored = GameState(self.root, self.path, clock=lambda: 1000)
        self.assertIn('first_harvest', restored.unlocked)
        self.assertEqual(restored.completed_collections, [])

    def test_gold_seal_awarded_once(self):
        self.game.counters['tap'] = 2000
        self.game.check_achievements()
        self.assertEqual(self.game.cosmetics.count('tap_gold_seal'), 1)
        self.game.check_achievements()
        self.assertEqual(self.game.cosmetics.count('tap_gold_seal'), 1)


if __name__ == '__main__':
    unittest.main()
