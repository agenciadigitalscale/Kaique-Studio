"""Miniaturas da galeria de efeitos — o frame tem de sair de verdade, com o efeito
aplicado e no tamanho pedido (senão a galeria abriria com quadrados quebrados)."""
import subprocess, tempfile, unittest
from pathlib import Path
import core


def _sample(d, name='src.mp4'):
    clip = Path(d) / name
    subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    'testsrc=size=720x1280:rate=30:duration=1', '-frames:v', '30',
                    str(clip)], check=True)
    return clip


def _identity_cube(d):
    cube = Path(d) / 'id.cube'
    cube.write_text('LUT_3D_SIZE 2\n' + '\n'.join(
        f'{r} {g} {b}' for b in (0, 1) for g in (0, 1) for r in (0, 1)) + '\n')
    return cube


class PreviewThumbnailTests(unittest.TestCase):
    def test_original_and_filter_render_a_real_image(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = _sample(d)
            for label, vf in [('orig', ''), ('sepia', core.FILTERS['Sépia'])]:
                dest = d / f'{label}.jpg'
                out = core.preview_thumbnail(str(clip), str(dest), vf=vf, seconds=0.5, width=320)
                self.assertTrue(Path(out).is_file())
                self.assertGreater(Path(out).stat().st_size, 500)

    def test_width_is_respected(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = _sample(d)
            dest = core.preview_thumbnail(str(clip), str(Path(d) / 't.jpg'), width=240, seconds=0.5)
            with Image.open(dest) as im:
                self.assertEqual(im.width, 240)
                self.assertEqual(im.height % 2, 0)  # altura par (scale=-2)

    def test_lut_path_is_applied(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = _sample(d)
            dest = core.preview_thumbnail(str(clip), str(Path(d) / 'lut.jpg'),
                                          lut=str(_identity_cube(d)), seconds=0.5)
            self.assertTrue(Path(dest).is_file())
            self.assertGreater(Path(dest).stat().st_size, 500)

    def test_missing_source_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                core.preview_thumbnail(str(Path(d) / 'nope.mp4'), str(Path(d) / 'x.jpg'))


class PreviewTransitionTests(unittest.TestCase):
    def test_every_transition_renders_a_mid_frame(self):
        with tempfile.TemporaryDirectory() as d:
            for name, xtype in core.XFADE_MAP.items():
                dest = Path(d) / f'{xtype}.jpg'
                core.preview_transition(xtype, str(dest), width=240, height=150)
                self.assertTrue(dest.is_file(), f'Transição {name!r} não gerou prévia')
                self.assertGreater(dest.stat().st_size, 500)

    def test_width_respected(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            dest = core.preview_transition('fade', str(Path(d) / 't.jpg'), width=200, height=120)
            with Image.open(dest) as im:
                self.assertEqual((im.width, im.height), (200, 120))


if __name__ == '__main__':
    unittest.main()
