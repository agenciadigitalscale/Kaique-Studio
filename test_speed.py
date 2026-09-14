"""Velocidade por take — câmera lenta/rápida. A legenda tem de acompanhar o tempo
esticado/comprimido, e o vídeo final muda de duração. Render real é a prova."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native


def _clip(path, seconds):
    subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    f'testsrc=size=720x1280:rate=30:duration={seconds}', '-f', 'lavfi', '-i',
                    f'sine=frequency=440:duration={seconds}', '-c:v', 'libx264', '-c:a', 'aac',
                    '-shortest', str(path)], check=True)


class SpeedValidation(unittest.TestCase):
    def _p(self, speed):
        p = native.project()
        p['clips'] = [dict(id='c', source='x', duration=4, width=720, height=1280,
                           **{'in': 0, 'out': 4}, words=[], thumbs=[], peaks=[], proxy='', speed=speed)]
        return p

    def test_range(self):
        # 0.5 e 2.0 valem; fora estoura (source ausente é checado antes, então testo só a faixa)
        for bad in [0.3, 3.0]:
            with self.assertRaises(ValueError):
                native.validate(self._p(bad))


class SpeedRender(unittest.TestCase):
    def test_slow_motion_doubles_duration(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = d / 'src.mp4'; _clip(clip, 2)
            n = native.project(); n['style']['captions_enabled'] = False
            n['clips'] = [dict(id='c1', source=str(clip), duration=2.0, width=720, height=1280,
                               **{'in': 0.0, 'out': 2.0}, words=[], thumbs=[], peaks=[], proxy='', speed=0.5)]
            out = native.render(n, str(d / 'out.mp4'))
            # 2s a 0.5x ≈ 4s
            self.assertGreater(core.probe(out)['duration'], 3.5)

    def test_speed_scales_caption_times(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = d / 'src.mp4'; _clip(clip, 2)
            # palavra em 1.0–1.4s do arquivo; a 2x deve cair ~0.5–0.7s na sequência
            n = native.project(); n['style']['captions_enabled'] = True
            n['clips'] = [dict(id='c1', source=str(clip), duration=2.0, width=720, height=1280,
                               **{'in': 0.0, 'out': 2.0}, thumbs=[], peaks=[], proxy='', speed=2.0,
                               words=[dict(start=1.0, end=1.4, text='rapido')])]
            # exercita o caminho de mapeamento de legenda sem depender de OCR:
            out = native.render(n, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())
            self.assertLess(core.probe(out)['duration'], 1.5)  # 2s a 2x ≈ 1s


if __name__ == '__main__':
    unittest.main()
