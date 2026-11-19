# --- Imports ---
import json
import tempfile
import unittest
from pathlib import Path
from src.android_packaging import make_spec, write_spec
from src.layout import viewport_layout
from src.game_state import GameState


# --- Phase Ten Tests ---
class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.gui = json.loads((self.root / 'config/gui.json').read_text())
        self.build = json.loads((self.root / 'config/build.json').read_text())

    def test_narrow_short_viewport(self):
        layout = viewport_layout(320, 568, self.gui)
        self.assertEqual(layout['columns'], 1)
        self.assertEqual(layout['navigation']['Discover'], 'Explore')
        self.assertLess(layout['header_dp'], self.gui['header_height_dp'])
        self.assertLess(layout['scene_dp'], 310)

    def test_large_viewport(self):
        layout = viewport_layout(800, 1280, self.gui)
        self.assertEqual(layout['columns'], 2)
        self.assertEqual(layout['navigation']['Discover'], 'Discover')
        self.assertIsNone(layout['scene_dp'])

    def test_android_build_spec(self):
        spec = make_spec(self.build)
        for expected in ('requirements = python3,kivy', 'android.archs = arm64-v8a,armeabi-v7a',
                         'source.include_exts = py,json,png,svg,wav',
                         f"android.minapi = {self.build['android']['min_api']}",
                         'source.dir = .', 'orientation = portrait'):
            self.assertIn(expected, spec)

    def test_build_spec_validation(self):
        altered = json.loads(json.dumps(self.build))
        altered['android']['min_api'] = 99
        with self.assertRaises(ValueError):
            make_spec(altered)

    def test_build_spec_is_reproducible(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            (project / 'config').mkdir()
            (project / 'config/build.json').write_text(json.dumps(self.build))
            result = write_spec(project)
            self.assertEqual(result.read_text(), make_spec(self.build))

    def test_every_release_asset_is_included(self):
        extensions = set(self.build['packaging']['source_extensions'])
        for path in (self.root / 'data').rglob('*'):
            if path.is_file():
                self.assertIn(path.suffix.removeprefix('.'), extensions, path.name)

    def test_save_location_can_be_customized(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'private' / 'state.json'
            path.parent.mkdir()
            state = GameState(self.root, save_path=path, clock=lambda: 100000)
            state.save()
            self.assertTrue(path.is_file())
            self.assertEqual(state.save_path, path)

    def test_current_achievement_total(self):
        achievements = json.loads((self.root / 'data/achievements.json').read_text())
        self.assertEqual(len(achievements), 94)


if __name__ == '__main__':
    unittest.main()
