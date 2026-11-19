# --- Imports ---
import tempfile
import unittest
from pathlib import Path
from src.game_state import GameState


# --- Engine Tests ---
ROOT = Path(__file__).resolve().parents[1]


class GameStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = 1000
        self.path = Path(self.temp.name) / "save.json"
        self.game = GameState(ROOT, save_path=self.path, clock=lambda: self.now)

    def tearDown(self):
        self.temp.cleanup()

    def test_starting_state(self):
        self.assertEqual(self.game.resources["barley"], 100)
        self.assertEqual(self.game.buildings["farm"], 1)

    def test_tap_unlocks_and_pays_reward_once(self):
        unlocks = self.game.tap()
        self.assertIn("First Harvest", unlocks)
        self.assertEqual(self.game.resources["barley"], 125)
        self.game.tap()
        self.assertEqual(self.game.resources["barley"], 130)

    def test_build_cost_and_production(self):
        price = self.game.cost("clay_pit")
        success, unlocks = self.game.build("clay_pit")
        self.assertTrue(success)
        self.assertIn("Foundations of Uruk", unlocks)
        self.assertEqual(self.game.resources["barley"], 100 - price["barley"])
        self.game.advance(10)
        self.assertEqual(self.game.counters["produce_clay"], 5)

    def test_insufficient_materials(self):
        self.game.resources["barley"] = 0
        success, _ = self.game.build("farm")
        self.assertFalse(success)

    def test_save_reload_offline_cap(self):
        self.game.tap()
        self.game.save()
        self.now += 50000
        restored = GameState(ROOT, save_path=self.path, clock=lambda: self.now)
        self.assertEqual(restored.counters["tap"], 1)
        self.assertAlmostEqual(restored.resources["barley"], restored.capacity("barley"))
        self.assertAlmostEqual(restored.counters["produce_barley"], 375)

    def test_corrupt_save_recovers(self):
        self.path.write_text("invalid", encoding="utf-8")
        restored = GameState(ROOT, save_path=self.path, clock=lambda: self.now)
        self.assertEqual(restored.resources["barley"], 100)


if __name__ == "__main__":
    unittest.main()
