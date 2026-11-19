# --- Imports ---
import json
import tempfile
import unittest
from pathlib import Path
from src.game_state import GameState


# --- Civilization Tests ---
class CivilizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(__file__).resolve().parents[1]
        self.save = Path(self.temp.name) / 'save.json'
        self.state = GameState(self.root, self.save, clock=lambda: 100000)

    def tearDown(self):
        self.temp.cleanup()

    def fund(self):
        self.state.resources = {key: self.state.capacity(key) for key in self.state.resources}

    def test_eras_require_buildings_research_and_resources(self):
        self.fund()
        self.assertFalse(self.state.advance_era()[0])
        self.state.researched.append('irrigation')
        self.state.buildings['house'] = 1
        self.state.buildings['clay_pit'] = 1
        ok, unlocked = self.state.advance_era()
        self.assertTrue(ok)
        self.assertEqual(self.state.era()['id'], 'town')
        self.assertIn('Era: Growing Town', unlocked)
        self.assertFalse(self.state.advance_era()[0])

    def test_monuments_have_one_time_cost_and_bonus(self):
        self.fund()
        self.state.era_index = 1
        self.state.researched.append('irrigation')
        before = self.state._research_multiplier('farm')
        ok, _ = self.state.construct_monument('canal_gate')
        self.assertTrue(ok)
        self.assertGreater(self.state._research_multiplier('farm'), before)
        after = self.state.resources.copy()
        self.assertFalse(self.state.construct_monument('canal_gate')[0])
        self.assertEqual(after, self.state.resources)

    def test_royal_commissions_award_one_time_renown(self):
        self.fund()
        self.state.counters['produce_barley'] = 200
        ok, _ = self.state.claim_quest('first_commission')
        self.assertTrue(ok)
        self.assertEqual(self.state.renown, 1)
        self.assertFalse(self.state.claim_quest('first_commission')[0])
        self.assertEqual(self.state.renown, 1)

    def test_legacy_rank_increases_output(self):
        initial = self.state._research_multiplier('farm')
        self.state.renown = self.state.settings['legacy_renown_per_rank']
        self.assertEqual(self.state.legacy_rank(), 1)
        self.assertGreater(self.state._research_multiplier('farm'), initial)

    def test_save_and_legacy_renown_reconciliation(self):
        self.fund()
        self.state.counters['produce_barley'] = 200
        self.state.claim_quest('first_commission')
        self.state.researched.append('irrigation')
        self.state.era_index = 1
        self.state.construct_monument('canal_gate')
        self.state.save()
        saved = json.loads(self.save.read_text())
        saved['renown'] = 900
        self.save.write_text(json.dumps(saved))
        restored = GameState(self.root, self.save, clock=lambda: 100000)
        self.assertEqual(restored.renown, 1)
        self.assertEqual(restored.era()['id'], 'town')
        self.assertIn('canal_gate', restored.monuments)

    def test_old_save_defaults(self):
        self.state.save()
        saved = json.loads(self.save.read_text())
        for key in ('era_index', 'monuments', 'completed_quests', 'renown'):
            saved.pop(key)
        self.save.write_text(json.dumps(saved))
        restored = GameState(self.root, self.save, clock=lambda: 100000)
        self.assertEqual(restored.era()['id'], 'village')
        self.assertEqual(restored.renown, 0)
        self.assertEqual(restored.monuments, [])

    def test_data_integrity(self):
        ids = {item['id'] for item in self.state.era_data}
        research = {item['id'] for item in self.state.research_data}
        for item in self.state.era_data:
            self.assertTrue(set(item['requires_research']) <= research)
            if item['requires_era']:
                self.assertIn(item['requires_era'], ids)
        for item in self.state.monument_data:
            self.assertIn(item['era'], ids)
            self.assertTrue(set(item['requires_research']) <= research)
        for item in self.state.quest_data:
            self.assertIn(item['era'], ids)


if __name__ == '__main__':
    unittest.main()
