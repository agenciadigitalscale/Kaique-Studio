"""Vídeo como sobreposição (b-roll/meme) — toca normal, sem -loop 1, e sem cortar
a base (shortest=0). Render real é a prova."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native


def _clip(path, seconds, size='720x1280', freq=440):
    subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    f'testsrc=size={size}:rate=30:duration={seconds}', '-f', 'lavfi', '-i',
                    f'sine=frequency={freq}:duration={seconds}', '-c:v', 'libx264', '-c:a', 'aac',
                    '-shortest', str(path)], check=True)


class VideoOverlayTests(unittest.TestCase):
    def test_video_ext_detected(self):
        self.assertIn('.mp4', core.VIDEO_EXT)
        self.assertNotIn('.png', core.VIDEO_EXT)

    def test_short_video_overlay_does_not_truncate_base(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); base = d / 'base.mp4'; broll = d / 'broll.mp4'
            _clip(base, 3); _clip(broll, 1, size='320x320', freq=660)  # b-roll de 1s numa base de 3s
            n = native.project(); n['style']['captions_enabled'] = False
            n['style']['overlays'] = [dict(path=str(broll), start=0.5, end=1.5, corner='Superior direito', width=200)]
            n['clips'] = [dict(id='c1', source=str(base), duration=3.0, width=720, height=1280,
                               **{'in': 0.0, 'out': 3.0}, words=[], thumbs=[], peaks=[], proxy='')]
            out = native.render(n, str(d / 'out.mp4'))
            # a base tem ~3s; se o shortest cortasse pelo b-roll (1s), a duração cairia
            self.assertGreater(core.probe(out)['duration'], 2.0)


if __name__ == '__main__':
    unittest.main()
