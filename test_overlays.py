"""Múltiplas sobreposições (imagens/ícones/stickers) — validação e render real."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native


def _png(path, color='red'):
    subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    f'color=c={color}:s=100x100:d=1', '-frames:v', '1', str(path)], check=True)


def _clip(path, seconds=1):
    subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    f'testsrc=size=720x1280:rate=30:duration={seconds}',
                    '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}',
                    '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(path)], check=True)


class OverlayModelTests(unittest.TestCase):
    def test_legacy_sticker_folds_into_one_overlay(self):
        q = core.project()
        q.update(sticker='s.png', sticker_start=0, sticker_end=4)
        got = core.overlays_of(q)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]['corner'], 'Superior direito')

    def test_new_overlays_win_over_legacy_sticker(self):
        p = core.project()
        p['sticker'] = 's.png'
        p['overlays'] = [dict(path='a.png', start=0, end=1, corner='Superior esquerdo', width=120)]
        self.assertEqual(len(core.overlays_of(p)), 1)
        self.assertEqual(core.overlays_of(p)[0]['path'], 'a.png')  # o legado não entra junto

    def test_survives_native_round_trip(self):
        self.assertIn('overlays', native.STYLE_KEYS)
        p = native.project()
        p['style']['overlays'] = [dict(path='x.png', start=0, end=1, corner='Inferior direito', width=200)]
        flat = native.legacy(p)
        self.assertEqual(flat['overlays'][0]['corner'], 'Inferior direito')

    def test_validation_bounds(self):
        base = core.project()
        base.update(source='x', duration=5, width=720, height=1280,
                    ranges=[{'start': 0, 'end': 5, 'enabled': True}])
        # canto inválido
        p = dict(base, overlays=[dict(path='a', start=0, end=1, corner='Centro', width=180)])
        with self.assertRaises(ValueError):
            core.validate(p, files=False)
        # fora da duração
        p = dict(base, overlays=[dict(path='a', start=0, end=99, corner='Superior direito', width=180)])
        with self.assertRaises(ValueError):
            core.validate(p, files=False)
        # largura fora da faixa
        p = dict(base, overlays=[dict(path='a', start=0, end=1, corner='Superior direito', width=5)])
        with self.assertRaises(ValueError):
            core.validate(p, files=False)
        # mais que o limite
        p = dict(base, overlays=[dict(path='a', start=0, end=1, corner='Superior direito', width=180)] * 9)
        with self.assertRaises(ValueError):
            core.validate(p, files=False)
        # válido não estoura
        p = dict(base, overlays=[dict(path='a', start=0, end=2, corner='Superior direito', width=180),
                                 dict(path='b', start=1, end=3, corner='Inferior esquerdo', width=120)])
        core.validate(p, files=False)


class OverlayRenderTests(unittest.TestCase):
    def test_two_overlays_render(self):
        """DOIS overlays ao mesmo tempo, em cantos diferentes — o que o motor
        antigo (um sticker só) não fazia. Se a cadeia de filtros estivesse
        errada, o FFmpeg falharia aqui."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            clip = d / 'src.mp4'; _clip(clip, 1)
            a = d / 'a.png'; _png(a, 'red')
            b = d / 'b.png'; _png(b, 'blue')
            p = core.project()
            p.update(source=str(clip), duration=1, width=720, height=1280,
                     captions_enabled=False,
                     ranges=[{'start': 0, 'end': 1, 'enabled': True}],
                     overlays=[dict(path=str(a), start=0, end=1, corner='Superior direito', width=160),
                               dict(path=str(b), start=0, end=1, corner='Inferior esquerdo', width=120)])
            out = core.render(p, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())
            self.assertGreater(Path(out).stat().st_size, 1000)

    def test_legacy_sticker_still_renders(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            clip = d / 'src.mp4'; _clip(clip, 1)
            st = d / 's.png'; _png(st, 'green')
            p = core.project()
            p.update(source=str(clip), duration=1, width=720, height=1280, captions_enabled=False,
                     sticker=str(st), sticker_start=0, sticker_end=1,
                     ranges=[{'start': 0, 'end': 1, 'enabled': True}])
            out = core.render(p, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())


if __name__ == '__main__':
    unittest.main()
