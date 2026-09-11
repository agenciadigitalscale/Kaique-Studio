"""Kit de filtros — cada string tem de ser aceita pelo FFmpeg (um filtro torto
só apareceria como erro de exportação na cara do editor)."""
import subprocess, tempfile, unittest
from pathlib import Path
import core


class FilterStringTests(unittest.TestCase):
    def test_every_filter_string_is_accepted_by_ffmpeg(self):
        exe = core.ffmpeg()
        for name, expr in core.FILTERS.items():
            if not expr:
                continue  # 'Original' é vazio de propósito
            r = subprocess.run(
                [exe, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:s=160x284:d=0.1',
                 '-vf', expr, '-frames:v', '1', '-f', 'null', '-'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            detail = r.stderr.decode(errors='replace')[:200]
            self.assertEqual(r.returncode, 0, f'Filtro {name!r} rejeitado: {detail}')

    def test_validation_accepts_new_and_rejects_unknown(self):
        base = core.project()
        base.update(source='x', duration=3, width=720, height=1280,
                    ranges=[{'start': 0, 'end': 3, 'enabled': True}])
        for name in ['Vívido', 'Sépia', 'Cinema', 'Vinheta']:
            core.validate(dict(base, filter=name), files=False)
        with self.assertRaises(ValueError):
            core.validate(dict(base, filter='Neon'), files=False)


class FilterRenderTests(unittest.TestCase):
    def test_new_filter_renders_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = d / 'src.mp4'
            subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'testsrc=size=720x1280:rate=30:duration=1',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                            '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(clip)], check=True)
            p = core.project()
            p.update(source=str(clip), duration=1, width=720, height=1280, captions_enabled=False,
                     filter='Sépia', ranges=[{'start': 0, 'end': 1, 'enabled': True}])
            out = core.render(p, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())
            self.assertGreater(Path(out).stat().st_size, 1000)


if __name__ == '__main__':
    unittest.main()
