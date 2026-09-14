"""Proporção e resolução de saída. target_dims é puro; um render real confirma
que a sequência sai de fato na moldura escolhida (o teste que só o FFmpeg prova)."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native


class TargetDimsTests(unittest.TestCase):
    def test_vertical_square_landscape_1080(self):
        self.assertEqual(core.target_dims('9:16'), (1080, 1920))
        self.assertEqual(core.target_dims('1:1'), (1080, 1080))
        self.assertEqual(core.target_dims('16:9'), (1920, 1080))
        self.assertEqual(core.target_dims('4:5'), (1080, 1350))

    def test_quality_720_and_480(self):
        self.assertEqual(core.target_dims('9:16', 'Média (720p)'), (720, 1280))
        self.assertEqual(core.target_dims('16:9', 'Leve (480p)'), (852, 480))

    def test_original_returns_none(self):
        self.assertIsNone(core.target_dims('Original'))
        self.assertIsNone(core.target_dims('qualquer-coisa'))

    def test_dims_are_even(self):
        for a in core.ASPECTS:
            for q in core.QUALITIES:
                w, h = core.target_dims(a, q)
                self.assertEqual((w % 2, h % 2), (0, 0), f'{a}/{q}')

    def test_validation_rejects_bad_aspect_and_quality(self):
        p = core.project()
        p.update(source='x', duration=2, width=720, height=1280,
                 ranges=[{'start': 0, 'end': 2, 'enabled': True}])
        core.validate(dict(p, aspect='1:1', quality='Média (720p)'), files=False)
        with self.assertRaises(ValueError):
            core.validate(dict(p, aspect='vertical'), files=False)
        with self.assertRaises(ValueError):
            core.validate(dict(p, quality='8K'), files=False)


class AspectRenderTests(unittest.TestCase):
    def test_square_output_is_actually_square(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = d / 'src.mp4'
            # take vertical 720x1280; a saída 1:1 tem de virar quadrada
            subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'testsrc=size=720x1280:rate=30:duration=1',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                            '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(clip)], check=True)
            p = native.project()
            p['style']['aspect'] = '1:1'; p['style']['captions_enabled'] = False
            p['clips'] = [dict(id='c1', source=str(clip), duration=1.0, width=720, height=1280,
                               **{'in': 0.0, 'out': 1.0}, words=[], thumbs=[], peaks=[], proxy='')]
            out = native.render(p, str(d / 'out.mp4'))
            info = core.probe(out)
            self.assertEqual((info['width'], info['height']), (1080, 1080))


if __name__ == '__main__':
    unittest.main()
