# --- Imports ---
import tempfile
import unittest
from pathlib import Path
from src.game_state import GameState


# --- Economy Tests ---
class EconomyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "save.json"
        self.now = 1000
        self.game = GameState(Path(__file__).resolve().parents[1], save_path=self.path, clock=lambda: self.now)

    def tearDown(self):
        self.temp.cleanup()

    def test_production_chains_use_real_inputs(self):
        self.game.buildings["bakery"] = 1
        self.game.buildings["kiln"] = 1
        self.game.advance(10)
        self.assertAlmostEqual(self.game.resources["bread"], 3)
        self.assertAlmostEqual(self.game.resources["bricks"], 2)
        self.assertAlmostEqual(self.game.resources["barley"], 102)
        self.assertAlmostEqual(self.game.resources["clay"], 54)
        self.assertAlmostEqual(self.game.resources["reeds"], 38)

    def test_starved_recipe_does_not_create_output(self):
        self.game.buildings["farm"] = 0
        self.game.buildings["kiln"] = 1
        self.game.resources["clay"] = 0
        self.game.advance(100)
        self.assertEqual(self.game.resources["bricks"], 0)

    def test_storage_caps_and_granary(self):
        self.game.advance(10000)
        self.assertEqual(self.game.resources["barley"], 500)
        self.assertAlmostEqual(self.game.counters["produce_barley"], 400)
        self.game.resources.update({"barley": 500, "clay": 400, "reeds": 350})
        success, newly = self.game.build("granary")
        self.assertTrue(success)
        self.assertIn("Keeper of Stores", newly)
        self.assertEqual(self.game.capacity("barley"), 750)

    def test_saved_granary_capacity_reloads(self):
        self.game.buildings["granary"] = 2
        self.game.resources["barley"] = 850
        self.game.save()
        restored = GameState(self.game.root, save_path=self.path, clock=lambda: self.now)
        self.assertEqual(restored.resources["barley"], 850)
        self.assertEqual(restored.capacity("barley"), 1125)

    def test_offline_achievement_and_cap(self):
        self.game.buildings["granary"] = 5
        self.game.save()
        self.now += 50000
        restored = GameState(self.game.root, save_path=self.path, clock=lambda: self.now)
        self.assertLessEqual(restored.resources["barley"], restored.capacity("barley"))
        self.assertIn("silent_harvest", restored.unlocked)
        self.assertGreater(restored.offline_summary["barley"], 0)

    def test_rewards_respect_caps(self):
        self.game.resources["barley"] = self.game.capacity("barley")
        self.game.tap()
        self.assertEqual(self.game.resources["barley"], self.game.capacity("barley"))
        self.assertIn("first_harvest", self.game.unlocked)


if __name__ == "__main__":
    unittest.main()
