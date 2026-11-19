# --- Imports ---
import json
import unittest
from pathlib import Path


# --- World Configuration Tests ---
class WorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.art = json.loads((cls.root / 'config' / 'art.json').read_text())
        cls.buildings = json.loads((cls.root / 'data' / 'buildings.json').read_text())

    def test_mobile_panorama(self):
        world = self.art['world']
        self.assertGreater(world['width_multiplier'], 1)
        self.assertGreaterEqual(world['background_tiles'], 2)
        self.assertGreater(world['min_width_dp'], world['height_dp'])
        self.assertGreater(world['animation_fps'], 0)

    def test_clickable_regions_and_animation_presets(self):
        seen = set()
        for entry in self.art['decorations']:
            self.assertNotIn(entry['id'], seen)
            seen.add(entry['id'])
            self.assertLessEqual(entry['x'] + entry['width'], 1)
            self.assertLessEqual(entry['y'] + entry['height'], 1)
            self.assertIn(entry['animation'], self.art['animations'])
            if 'requires' in entry:
                self.assertIn(entry['requires'], self.buildings)

    def test_animation_is_bounded(self):
        for motion in self.art['animations'].values():
            self.assertGreater(motion['speed'], 0)
            self.assertGreaterEqual(motion['opacity_base'] - motion['opacity_range'], 0)
            self.assertLessEqual(motion['opacity_base'] + motion['opacity_range'], 1)
            self.assertGreaterEqual(motion['bob'], 0)


if __name__ == '__main__':
    unittest.main()
