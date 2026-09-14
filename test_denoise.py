"""Limpeza de voz (highpass + afftdn) — o FFmpeg tem de aceitar a cadeia, e o
ronco de baixa frequência deve cair. Render real é a prova."""
import subprocess, tempfile, unittest, re
from pathlib import Path
import core, native


def _noisy_clip(path, seconds):
    # voz (300Hz) + ronco grave (50Hz, abaixo do corte do highpass) + chiado
    subprocess.run([core.ffmpeg(), '-v', 'error', '-y',
                    '-f', 'lavfi', '-i', f'testsrc=size=720x1280:rate=30:duration={seconds}',
                    '-f', 'lavfi', '-i', f'sine=frequency=300:duration={seconds}',
                    '-f', 'lavfi', '-i', f'sine=frequency=50:duration={seconds}',
                    '-filter_complex', '[1][2]amix=inputs=2[a]', '-map', '0:v', '-map', '[a]',
                    '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(path)], check=True)


def _energy_50hz(path):
    # mede quanta energia sobrou perto de 50Hz (o ronco) isolando essa banda
    r = subprocess.run([core.ffmpeg(), '-hide_banner', '-i', str(path),
                        '-af', 'lowpass=f=70,volumedetect', '-f', 'null', '-'],
                       stderr=subprocess.PIPE)
    m = re.findall(r'mean_volume:\s*(-?\d+\.?\d*)\s*dB', r.stderr.decode(errors='replace'))
    return float(m[-1]) if m else None


class DenoiseTests(unittest.TestCase):
    def test_in_style_keys_and_default_on(self):
        self.assertIn('denoise', native.STYLE_KEYS)
        self.assertTrue(core.project()['denoise'])

    def _render(self, denoise):
        d = Path(tempfile.mkdtemp()); clip = d / 'src.mp4'; _noisy_clip(clip, 3)
        n = native.project(); n['style']['captions_enabled'] = False; n['style']['denoise'] = denoise
        n['style']['normalize_audio'] = False  # isola o efeito do highpass, sem loudnorm
        n['clips'] = [dict(id='c1', source=str(clip), duration=3.0, width=720, height=1280,
                           **{'in': 0.0, 'out': 3.0}, words=[], thumbs=[], peaks=[], proxy='')]
        return native.render(n, str(d / 'out.mp4'))

    def test_highpass_reduces_low_rumble(self):
        with_dn = self._render(True); without = self._render(False)
        self.assertTrue(Path(with_dn).is_file())
        a, b = _energy_50hz(with_dn), _energy_50hz(without)
        if a is not None and b is not None:  # o ronco (50Hz) fica MAIS baixo com denoise
            self.assertLess(a, b)


if __name__ == '__main__':
    unittest.main()
