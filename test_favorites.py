import json
import tempfile
import unittest
from pathlib import Path
import favorites


class FavoritesTests(unittest.TestCase):
    def test_toggle_on_and_off(self):
        data = {}
        data, on = favorites.toggle(data, 'filters', 'Cyberpunk')
        self.assertTrue(on)
        self.assertTrue(favorites.is_favorite(data, 'filters', 'Cyberpunk'))
        data, on = favorites.toggle(data, 'filters', 'Cyberpunk')
        self.assertFalse(on)
        self.assertFalse(favorites.is_favorite(data, 'filters', 'Cyberpunk'))

    def test_toggle_does_not_mutate_input(self):
        data = {'filters': ['A']}
        favorites.toggle(data, 'filters', 'B')
        self.assertEqual(data, {'filters': ['A']})

    def test_kinds_are_independent(self):
        data = {}
        data, _ = favorites.toggle(data, 'filters', 'Noir')
        self.assertFalse(favorites.is_favorite(data, 'transitions', 'Noir'))

    def test_ordered_puts_favorites_first(self):
        names = ['A', 'B', 'C', 'D']
        self.assertEqual(favorites.ordered(names, ['C', 'A']), ['A', 'C', 'B', 'D'])

    def test_ordered_ignores_stale_favorite(self):
        # favorito que não existe mais na lista de nomes é ignorado
        self.assertEqual(favorites.ordered(['A', 'B'], ['Z']), ['A', 'B'])

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'sub' / 'favorites.json'
            favorites.save({'filters': ['Noir', 'Aqua']}, p)
            self.assertEqual(favorites.load(p), {'filters': ['Noir', 'Aqua']})

    def test_load_missing_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(favorites.load(Path(d) / 'nope.json'), {})

    def test_load_corrupt_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'favorites.json'
            p.write_text('{not json', encoding='utf-8')
            self.assertEqual(favorites.load(p), {})

    def test_load_drops_non_string_entries(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'favorites.json'
            p.write_text(json.dumps({'filters': ['A', 5, None], 'x': 'nope'}), encoding='utf-8')
            self.assertEqual(favorites.load(p), {'filters': ['A']})


if __name__ == '__main__':
    unittest.main()
