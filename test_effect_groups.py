"""Categorias da galeria (estilo CapCut): todo efeito tem de estar em exatamente
um grupo, senão sumiria da galeria ou apareceria duas vezes."""
import unittest
import core


def _flat(groups):
    out = []
    for names in groups.values():
        out.extend(names)
    return out


class EffectGroupsTests(unittest.TestCase):
    def test_filters_cover_all_exactly_once(self):
        flat = _flat(core.FILTER_GROUPS)
        self.assertEqual(sorted(flat), sorted(core.FILTERS))
        self.assertEqual(len(flat), len(set(flat)))  # sem duplicata

    def test_transitions_cover_all_exactly_once(self):
        flat = _flat(core.TRANSITION_GROUPS)
        self.assertEqual(sorted(flat), sorted(core.TRANSITIONS))
        self.assertEqual(len(flat), len(set(flat)))

    def test_captions_cover_all_exactly_once(self):
        flat = _flat(core.CAPTION_GROUPS)
        self.assertEqual(sorted(flat), sorted(core.CAPTION_STYLES))
        self.assertEqual(len(flat), len(set(flat)))

    def test_order_is_respected(self):
        # As categorias pedidas vêm primeiro, na ordem dada.
        cats = list(core.FILTER_GROUPS)
        self.assertEqual(cats[:len(core.FILTER_ORDER)],
                         [c for c in core.FILTER_ORDER if c in cats])

    def test_fallback_catches_unmapped(self):
        groups = core.effect_groups(['a', 'b', 'c'], {'a': 'X'}, ['X'], fallback='Mais')
        self.assertEqual(groups['X'], ['a'])
        self.assertEqual(groups['Mais'], ['b', 'c'])

    def test_no_empty_group_from_real_data(self):
        for groups in (core.FILTER_GROUPS, core.TRANSITION_GROUPS, core.CAPTION_GROUPS):
            for cat, names in groups.items():
                self.assertTrue(names, f'Categoria vazia: {cat}')


if __name__ == '__main__':
    unittest.main()
