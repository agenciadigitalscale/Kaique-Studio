"""apply_entry — a lógica única de 'aplicar um recurso ao projeto', usada pelo
clique e pelo arraste. Se divergirem, arrastar e clicar fariam coisas diferentes."""
import unittest
import core, library


def _proj():
    p = core.project()
    p.update(source='x', duration=10, width=1080, height=1920,
             ranges=[{'start': 0, 'end': 10, 'enabled': True}])
    return p


def _entry(kind, **extra):
    extra.setdefault('path', 'som.mp3')
    return dict(id='r', title='R', kind=kind, category='Outros', **extra)


class ApplyEntryTests(unittest.TestCase):
    def test_sfx_lands_at_given_time_without_mutating(self):
        p = _proj(); before = len(p['sfx'])
        out = library.apply_entry(p, _entry('Efeitos sonoros'), at_time=3.5)
        self.assertEqual(out['sfx'][-1]['time'], 3.5)
        self.assertEqual(len(p['sfx']), before)  # original intacto

    def test_negative_time_is_clamped(self):
        out = library.apply_entry(_proj(), _entry('Memes'), at_time=-9)
        self.assertEqual(out['sfx'][-1]['time'], 0.0)

    def test_overlay_uses_time_and_default_corner(self):
        out = library.apply_entry(_proj(), _entry('Imagens', path='logo.png'), at_time=2)
        ov = out['overlays'][-1]
        self.assertEqual(ov['start'], 2)
        self.assertEqual(ov['end'], 5)
        self.assertIn(ov['corner'], list(core.CORNERS))

    def test_music_lut_filter_transition_and_preset(self):
        self.assertEqual(library.apply_entry(_proj(), _entry('Músicas', path='m.mp3'))['music'], 'm.mp3')
        self.assertEqual(library.apply_entry(_proj(), _entry('LUTs', path='l.cube'))['lut'], 'l.cube')
        self.assertEqual(library.apply_entry(_proj(), _entry('Filtros', value='Sépia'))['filter'], 'Sépia')
        self.assertEqual(library.apply_entry(_proj(), _entry('Transições', value='Preto'))['transition'], 'Preto')
        pr = _entry('Presets', preset={'name': 'x', 'style': {'filter': 'Vívido'}})
        self.assertEqual(library.apply_entry(_proj(), pr)['filter'], 'Vívido')

    def test_applied_result_passes_core_validation(self):
        out = library.apply_entry(_proj(), _entry('Filtros', value='Cinema'))
        core.validate(out, files=False)  # não estoura

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            library.apply_entry(_proj(), _entry('Todos'))


if __name__ == '__main__':
    unittest.main()
