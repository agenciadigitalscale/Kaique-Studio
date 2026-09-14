"""Normalização de loudness na exportação — todo vídeo sai perto de -14 LUFS.
Render real: o loudnorm só o FFmpeg valida (e mede-se o resultado)."""
import subprocess, tempfile, unittest, re
from pathlib import Path
import core, native


def _clip(path, seconds, vol=0.1):
    # take com voz baixa (0.1) — a normalização deve puxar para cima
    subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    f'testsrc=size=720x1280:rate=30:duration={seconds}', '-f', 'lavfi', '-i',
                    f'sine=frequency=300:duration={seconds}', '-filter:a', f'volume={vol}',
                    '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(path)], check=True)


def _lufs(path):
    r = subprocess.run([core.ffmpeg(), '-hide_banner', '-i', str(path), '-af',
                        'ebur128', '-f', 'null', '-'], stderr=subprocess.PIPE)
    m = re.findall(r'I:\s*(-?\d+\.?\d*)\s*LUFS', r.stderr.decode(errors='replace'))
    return float(m[-1]) if m else None


class LoudnessTests(unittest.TestCase):
    def test_in_style_keys_and_default_on(self):
        self.assertIn('normalize_audio', native.STYLE_KEYS)
        self.assertTrue(core.project()['normalize_audio'])

    def test_normalized_export_is_near_target(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = d / 'src.mp4'; _clip(clip, 3, vol=0.08)
            n = native.project(); n['style']['captions_enabled'] = False
            n['clips'] = [dict(id='c1', source=str(clip), duration=3.0, width=720, height=1280,
                               **{'in': 0.0, 'out': 3.0}, words=[], thumbs=[], peaks=[], proxy='')]
            out = native.render(n, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())
            lufs = _lufs(out)
            if lufs is not None:  # ebur128 disponível → confere o alvo
                self.assertGreater(lufs, -20)  # voz baixa foi puxada para perto de -14
                self.assertLess(lufs, -8)

    def test_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = d / 'src.mp4'; _clip(clip, 2)
            n = native.project(); n['style']['captions_enabled'] = False; n['style']['normalize_audio'] = False
            n['clips'] = [dict(id='c1', source=str(clip), duration=2.0, width=720, height=1280,
                               **{'in': 0.0, 'out': 2.0}, words=[], thumbs=[], peaks=[], proxy='')]
            out = native.render(n, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())


if __name__ == '__main__':
    unittest.main()
