# --- Imports ---
import json
import math
import tempfile
import unittest
import wave
from pathlib import Path
from src.game_state import GameState
from src.visual_effects import make_burst, night_strength, particle_position

# --- Phase Nine Tests ---
class PolishTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.temp = tempfile.TemporaryDirectory()
        self.state = GameState(self.root, Path(self.temp.name) / "state.json", clock=lambda: 100000)

    def tearDown(self):
        self.temp.cleanup()

    def test_expedition_preserves_civilization(self):
        self.state.era_index = 2
        self.state.monuments = ["canal_gate"]
        self.state.completed_quests = ["first_commission"]
        self.state.renown = 3
        self.state.active_expedition = self.state.expedition_data[0]["id"]
        self.state.expedition_remaining = 1
        self.state._advance_expedition(2)
        self.assertEqual(self.state.era_index, 2)
        self.assertEqual(self.state.renown, 3)
        self.assertEqual(self.state.monuments, ["canal_gate"])
        self.assertEqual(self.state.completed_quests, ["first_commission"])

    def test_sound_assets(self):
        config = json.loads((self.root / "config/gui.json").read_text())
        for name in config["sound"]["effects"]:
            with wave.open(str(self.root / "data/audio" / (name + ".wav"))) as item:
                self.assertEqual(item.getnchannels(), 1)
                self.assertGreater(item.getnframes(), 500)

    def test_visual_effects_bounded_and_reproducible(self):
        settings = json.loads((self.root / "config/art.json").read_text())["effects"]
        self.assertEqual(make_burst((3, 4), settings, seed=5), make_burst((3, 4), settings, seed=5))
        self.assertLessEqual(len(make_burst((0, 0), settings)), settings["max_particles"])
        self.assertEqual(particle_position((1, 2), (3, 4), 2, 10), (7, -10))
        self.assertAlmostEqual(night_strength(0, 180, .2), 0)
        self.assertAlmostEqual(night_strength(90, 180, .2), .2)

    def test_economy_bounds_and_round_trip(self):
        self.state.buildings.update({"farm": 4, "bakery": 2, "kiln": 2, "clay_pit": 2, "reed_garden": 2})
        self.state.resources.update({"barley": 200, "clay": 150, "reeds": 100, "bread": 0, "bricks": 0})
        self.state.advance(1200, offline=True)
        self.assertTrue(all(0 <= quantity <= self.state.capacity(resource)
                            for resource, quantity in self.state.resources.items()))
        self.state.save()
        restored = GameState(self.root, self.state.save_path, clock=lambda: 100000)
        self.assertEqual(self.state.resources, restored.resources)

    def test_all_python_compiles(self):
        for folder in ("src", "tests"):
            for file in (self.root / folder).glob("*.py"):
                compile(file.read_text(), str(file), "exec")

if __name__ == "__main__":
    unittest.main()
