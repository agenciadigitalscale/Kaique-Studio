"""Organização visual do acervo — agrupamento por tipo e emojis. Lógica pura,
sem Qt (a UI só desenha o que esta função decide)."""
import unittest
import library


def _e(title, kind, category='Outros'):
    return {'id': title, 'title': title, 'kind': kind, 'category': category, 'path': 'x'}


class GroupForDisplayTests(unittest.TestCase):
    def test_groups_by_kind_with_header_and_count(self):
        rows = library.group_for_display([
            _e('Boom', 'Efeitos sonoros', 'Impacto'),
            _e('Neon', 'Presets', 'Cinemático'),
            _e('Clique', 'Efeitos sonoros', 'Interface'),
        ])
        # Presets vêm antes de Efeitos sonoros (ordem de exibição)
        self.assertEqual(rows[0], ('header', 'Presets', 1))
        self.assertEqual(rows[1][0], 'item')
        self.assertEqual(rows[2], ('header', 'Efeitos sonoros', 2))
        # dentro do tipo, ordenado por categoria: Impacto antes de Interface
        titles = [r[1]['title'] for r in rows if r[0] == 'item' and r[1]['kind'] == 'Efeitos sonoros']
        self.assertEqual(titles, ['Boom', 'Clique'])

    def test_unknown_kind_falls_to_end_alphabetically(self):
        rows = library.group_for_display([_e('x', 'Zumbido'), _e('n', 'Presets', 'Outros')])
        headers = [r[1] for r in rows if r[0] == 'header']
        self.assertEqual(headers[0], 'Presets')
        self.assertIn('Zumbido', headers)
        self.assertEqual(headers[-1], 'Zumbido')

    def test_every_known_kind_and_category_has_an_emoji(self):
        for kind in ['Memes', 'Efeitos sonoros', 'Músicas', 'Ícones', 'Imagens', 'LUTs',
                     'Transições', 'Filtros', 'Presets']:
            self.assertNotEqual(library.kind_emoji(kind), '•', kind)
        for cat in library.CATEGORIES[1:]:  # 'Todas' não é categoria real
            self.assertNotEqual(library.category_emoji(cat), '•', cat)

    def test_empty_is_empty(self):
        self.assertEqual(library.group_for_display([]), [])


if __name__ == '__main__':
    unittest.main()
