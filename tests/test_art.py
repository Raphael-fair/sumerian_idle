# --- Imports ---
import json
import struct
import unittest
from pathlib import Path


# --- Art Integrity Tests ---
class ArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config = json.loads((cls.root / 'config' / 'art.json').read_text())

    def test_svg_and_png_pairs(self):
        for item in ['landscape'] + [entry['image'] for entry in self.config['decorations']]:
            svg = self.root / 'data' / 'art' / 'svg' / (item + '.svg')
            png = self.root / 'data' / 'art' / 'png' / (item + '.png')
            self.assertTrue(svg.is_file())
            self.assertIn('<svg', svg.read_text())
            self.assertTrue(png.is_file())
            with png.open('rb') as handle:
                self.assertEqual(handle.read(8), b'\x89PNG\r\n\x1a\n')
                handle.read(8)
                self.assertEqual(struct.unpack('>II', handle.read(8)), (768, 520))

    def test_art_bounds_and_building_references(self):
        buildings = json.loads((self.root / 'data' / 'buildings.json').read_text())
        for item in self.config['decorations']:
            for key in ('x', 'y', 'width', 'height'):
                self.assertGreaterEqual(item[key], 0)
                self.assertLessEqual(item[key], 1)
            self.assertLessEqual(item['x'] + item['width'], 1)
            self.assertLessEqual(item['y'] + item['height'], 1)
            self.assertIn(item.get('requires'), [None] + list(buildings))

    def test_viewport_settings(self):
        scene = self.config['scene']
        self.assertGreater(scene['aspect_ratio'], 1)
        self.assertLess(scene['min_height_dp'], scene['max_height_dp'])


if __name__ == '__main__':
    unittest.main()
