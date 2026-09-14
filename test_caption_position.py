"""Posição vertical da legenda (Embaixo/Meio/Em cima) — muda o alinhamento ASS."""
import unittest
import core, native


def _p():
    p = core.project()
    p.update(source='x', duration=4, width=1080, height=1920, captions_enabled=True,
             ranges=[{'start': 0, 'end': 4, 'enabled': True}],
             words=[{'start': 0.0, 'end': 0.5, 'text': 'oi'}])
    return p


class CaptionPositionTests(unittest.TestCase):
    def test_default_is_bottom_align_2(self):
        ass = core.make_ass(_p())
        # a linha de Style termina com ...,2,24,24,90,1 (alinhamento 2 = rodapé)
        style = [l for l in ass.splitlines() if l.startswith('Style: Main')][0]
        self.assertRegex(style, r',2,24,24,90,1$')

    def test_top_uses_align_8(self):
        p = _p(); p['caption_pos'] = 'Em cima'
        style = [l for l in core.make_ass(p).splitlines() if l.startswith('Style: Main')][0]
        self.assertRegex(style, r',8,24,24,90,1$')

    def test_middle_uses_align_5(self):
        p = _p(); p['caption_pos'] = 'Meio'
        style = [l for l in core.make_ass(p).splitlines() if l.startswith('Style: Main')][0]
        self.assertRegex(style, r',5,24,24,0,1$')

    def test_validation_and_style_keys(self):
        self.assertIn('caption_pos', native.STYLE_KEYS)
        core.validate(dict(_p(), caption_pos='Meio'), files=False)
        with self.assertRaises(ValueError):
            core.validate(dict(_p(), caption_pos='Diagonal'), files=False)


if __name__ == '__main__':
    unittest.main()
