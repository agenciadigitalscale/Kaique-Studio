"""Transição crossfade (Dissolve) — os clipes se sobrepõem, então o vídeo encurta
e os tempos das legendas/efeitos são deslocados. dissolve_shift é puro; um render
real confirma a sobreposição."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native


class DissolveShiftTests(unittest.TestCase):
    def test_shifts_by_crossings(self):
        b = [3.0, 6.0]  # duas fronteiras
        self.assertEqual(core.dissolve_shift(1.0, b, 0.4), 1.0)   # antes de tudo: sem shift
        self.assertAlmostEqual(core.dissolve_shift(4.0, b, 0.4), 3.6)  # cruzou 1
        self.assertAlmostEqual(core.dissolve_shift(7.0, b, 0.4), 6.2)  # cruzou 2
        self.assertGreaterEqual(core.dissolve_shift(0.1, b, 0.4), 0)

    def test_no_boundaries_no_shift(self):
        self.assertEqual(core.dissolve_shift(5.0, [], 0.4), 5.0)


class DissolveRenderTests(unittest.TestCase):
    def _clip(self, path, seconds, freq):
        subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        f'testsrc=size=720x1280:rate=30:duration={seconds}', '-f', 'lavfi', '-i',
                        f'sine=frequency={freq}:duration={seconds}', '-c:v', 'libx264', '-c:a', 'aac',
                        '-shortest', str(path)], check=True)

    def _two_clip_project(self, transition):
        d = Path(tempfile.mkdtemp()); a = d / 'a.mp4'; b = d / 'b.mp4'
        self._clip(a, 2, 300); self._clip(b, 2, 500)
        n = native.project(); n['style']['captions_enabled'] = False; n['style']['transition'] = transition
        n['clips'] = [dict(id='c1', source=str(a), duration=2.0, width=720, height=1280,
                           **{'in': 0.0, 'out': 2.0}, words=[], thumbs=[], peaks=[], proxy=''),
                      dict(id='c2', source=str(b), duration=2.0, width=720, height=1280,
                           **{'in': 0.0, 'out': 2.0}, words=[], thumbs=[], peaks=[], proxy='')]
        return d, n

    def test_dissolve_shortens_vs_hard_cut(self):
        d, n = self._two_clip_project('Dissolve')
        out = native.render(n, str(d / 'out.mp4'))
        d2, n2 = self._two_clip_project('Nenhuma')
        cut = native.render(n2, str(d2 / 'cut.mp4'))
        # com crossfade os 2s+2s se sobrepõem ~0.4s → mais curto que o corte seco (~4s)
        self.assertLess(core.probe(out)['duration'], core.probe(cut)['duration'] - 0.2)


if __name__ == '__main__':
    unittest.main()
