"""Textos/títulos na tela — independentes da legenda da fala. ASS é texto puro
(testável sem render); um render real confirma que o FFmpeg aceita o evento."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native


def _base():
    p = core.project()
    p.update(source='x', duration=5, width=1080, height=1920,
             ranges=[{'start': 0, 'end': 5, 'enabled': True}])
    return p


class TitleValidationTests(unittest.TestCase):
    def test_valid_title_passes(self):
        p = _base(); p['titles'] = [{'text': 'ARRASTA PRA CIMA', 'start': 0, 'end': 2, 'position': 'Topo', 'size': 44}]
        core.validate(p, files=False)

    def test_rejects_empty_bad_time_position_size(self):
        for bad in [{'text': '  ', 'start': 0, 'end': 1},
                    {'text': 'x', 'start': 2, 'end': 1},
                    {'text': 'x', 'start': 0, 'end': 1, 'position': 'Diagonal'},
                    {'text': 'x', 'start': 0, 'end': 1, 'size': 500}]:
            p = _base(); p['titles'] = [bad]
            with self.assertRaises(ValueError):
                core.validate(p, files=False)


class TitleAssTests(unittest.TestCase):
    def test_title_appears_even_with_captions_off(self):
        p = _base(); p['captions_enabled'] = False
        p['titles'] = [{'text': 'PARTE 2', 'start': 0, 'end': 2, 'position': 'Centro', 'size': 40}]
        ass = core.make_ass(p)
        self.assertIn('PARTE 2', ass)
        self.assertIn(r'\an5', ass)     # centro
        self.assertIn('Dialogue:', ass)

    def test_position_maps_to_alignment(self):
        p = _base()
        p['titles'] = [{'text': 'topo', 'start': 0, 'end': 1, 'position': 'Topo'},
                       {'text': 'pe', 'start': 1, 'end': 2, 'position': 'Rodapé'}]
        ass = core.make_ass(p)
        self.assertIn(r'\an8', ass)
        self.assertIn(r'\an2', ass)

    def test_survives_native_round_trip(self):
        self.assertIn('titles', native.STYLE_KEYS)
        n = native.project(); n['style']['titles'] = [{'text': 'x', 'start': 0, 'end': 1}]
        self.assertEqual(native.legacy(n)['titles'][0]['text'], 'x')


class TitleRenderTests(unittest.TestCase):
    def test_title_renders_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = d / 'src.mp4'
            subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'testsrc=size=720x1280:rate=30:duration=1',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                            '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(clip)], check=True)
            n = native.project(); n['style']['captions_enabled'] = False
            n['style']['titles'] = [{'text': 'TOP 1 BRASIL', 'start': 0, 'end': 1, 'position': 'Centro', 'size': 48}]
            n['clips'] = [dict(id='c1', source=str(clip), duration=1.0, width=720, height=1280,
                               **{'in': 0.0, 'out': 1.0}, words=[], thumbs=[], peaks=[], proxy='')]
            out = native.render(n, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())
            self.assertGreater(Path(out).stat().st_size, 1000)


if __name__ == '__main__':
    unittest.main()
