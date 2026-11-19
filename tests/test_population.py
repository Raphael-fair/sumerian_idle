# --- Imports ---
import json
import tempfile
import unittest
from pathlib import Path
from src.game_state import GameState


# --- Population Tests ---
class PopulationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'save.json'
        self.root = Path(__file__).resolve().parents[1]
        self.now = 1000
        self.game = GameState(self.root, self.path, clock=lambda: self.now)

    def tearDown(self):
        self.folder.cleanup()

    def test_houses_expand_housing(self):
        self.assertEqual(self.game.housing_capacity(), 8)
        self.game.buildings['house'] = 2
        self.assertEqual(self.game.housing_capacity(), 16)

    def test_automatic_staffing_and_manual_override(self):
        self.game.buildings['farm'] = 2
        self.assertEqual(self.game.workforce()['farm'], 2)
        success, _ = self.game.assign_worker('farm', -1)
        self.assertTrue(success)
        self.assertEqual(self.game.workforce()['farm'], 1)
        success, _ = self.game.assign_worker('farm', 1)
        self.assertTrue(success)
        self.assertEqual(self.game.workforce()['farm'], 2)

    def test_unstaffed_building_stops_production(self):
        self.game.assign_worker('farm', -1)
        prior = self.game.resources['barley']
        self.game.advance(20)
        self.assertEqual(self.game.resources['barley'], prior)

    def test_birth_consumes_food_and_unlocks_achievement(self):
        self.game.buildings['house'] = 1
        self.game.resources['bread'] = 10
        self.game.advance(self.game.settings['growth_interval_seconds'])
        self.assertEqual(self.game.population, 9)
        self.assertIn('first_child', self.game.unlocked)
        self.assertEqual(self.game.counters['citizen_born'], 1)

    def test_save_reload_and_phase_four_compatibility(self):
        self.game.buildings['house'] = 1
        self.game.population = 9
        self.game.assignments['farm'] = 0
        self.game.save()
        restored = GameState(self.root, self.path, clock=lambda: self.now)
        self.assertEqual(restored.population, 9)
        self.assertEqual(restored.workforce()['farm'], 0)
        old = json.loads(self.path.read_text())
        for key in ('population', 'assignments', 'population_timer', 'food_timer'):
            old.pop(key)
        self.path.write_text(json.dumps(old))
        legacy = GameState(self.root, self.path, clock=lambda: self.now)
        self.assertEqual(legacy.population, 8)

    def test_offline_growth_respects_housing_and_food(self):
        self.game.buildings['house'] = 1
        self.game.buildings['bakery'] = 2
        self.game.resources['bread'] = 200
        self.game.resources['barley'] = 400
        self.game.save()
        self.now += 3600
        restored = GameState(self.root, self.path, clock=lambda: self.now)
        self.assertLessEqual(restored.population, restored.housing_capacity())
        self.assertGreater(restored.population, 8)


if __name__ == '__main__':
    unittest.main()
